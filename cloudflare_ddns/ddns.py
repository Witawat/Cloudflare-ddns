"""แกนหลัก DDNS: ตรวจ IP -> เทียบกับ cache -> อัปเดต Cloudflare เฉพาะเมื่อเปลี่ยน."""

import json
import logging
import os
import time
from datetime import datetime, timezone

from . import cloudflare_api
from . import config as config_mod
from . import heartbeat
from . import ip_detect
from . import notifier
from .config import fqdn_name

log = logging.getLogger("cloudflare-ddns")

RECORD_TYPES = {4: "A", 6: "AAAA"}


class _NullNotifier:
    """ตัวแทน notifier ตอน dry-run — ไม่ส่ง Telegram ไม่เขียนคิว ไม่ทำอะไรเลย"""

    enabled = False

    def notify(self, event, text):
        pass

    def flush(self):
        return 0, 0


def _is_zone_not_found(message):
    """เช็คว่า error เป็น 'zone ไม่พบ' (id cache เก่า) หรือไม่"""
    msg = str(message).lower()
    return "not found" in msg or "9109" in msg or ("404" in msg and "zone" in msg)


# แจ้ง rate limit ครั้งเดียวต่อ 10 นาที (กันสแปม Telegram)
_RATE_LIMIT_NOTIFY_INTERVAL = 600
_last_rate_limit_notify = 0.0


def _notify_rate_limit(notify, exc):
    """แจ้ง Telegram ว่าโดน rate limit — กันซ้ำภายใน 10 นาที"""
    global _last_rate_limit_notify
    now = time.time()
    if now - _last_rate_limit_notify >= _RATE_LIMIT_NOTIFY_INTERVAL:
        _last_rate_limit_notify = now
        notify.notify(notifier.EVENT_ERROR, f"โดน rate limit ของ Cloudflare — ข้ามรอบนี้ ({exc})")


class DDNSEngine:
    """engine หนึ่งตัว = อ่าน config -> ตรวจ IP -> อัปเดต record ทุกตัว"""

    def __init__(self, config_path=config_mod.DEFAULT_CONFIG_PATH, dry_run=False):
        self.config_path = config_path
        self.dry_run = dry_run
        self._state = {}

    # ---- state (cache IP ล่าสุด ไว้เทียบเพื่อลดการเรียก API) ----

    def _load_state(self):
        try:
            with open(config_mod.DEFAULT_STATE_PATH, "r", encoding="utf-8") as handle:
                self._state = json.load(handle)
        except (OSError, ValueError):
            self._state = {}

    def _invalidate_zone(self, zone_key):
        """ลบ zone cache เมื่อ id ไม่ถูกต้องแล้ว (เปลี่ยน token/ลบ zone) — รอบถัดไปจะหาใหม่"""
        zones = self._state.get("zones", {})
        if zone_key in zones:
            del zones[zone_key]
            log.info("ลบ zone cache ของ %s (id ไม่ถูกต้องแล้ว) — จะหาใหม่รอบถัดไป", zone_key)
            if not self.dry_run:
                try:
                    self._save_state()
                except Exception as exc:
                    log.warning("บันทึก state หลังลบ zone cache ไม่ได้: %s", exc)

    def _save_state(self):
        os.makedirs(os.path.dirname(config_mod.DEFAULT_STATE_PATH), exist_ok=True)
        tmp = config_mod.DEFAULT_STATE_PATH + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as handle:
                json.dump(self._state, handle, indent=2, ensure_ascii=False)
            os.replace(tmp, config_mod.DEFAULT_STATE_PATH)
        except OSError as exc:
            log.warning("บันทึก state ไม่ได้: %s", exc)

    def status(self):
        """ข้อมูลสถานะสำหรับ Web UI / status command"""
        self._load_state()
        return {
            "last_run": self._state.get("last_run", ""),
            "records": self._state.get("records", {}),
            "history": self._state.get("history", [])[-50:],
            "record_errors": self._state.get("record_errors", {}),
            "dry_run": self.dry_run,
        }

    # ---- หลัก ----

    def run_once(self):
        """รันรอบเดียว: อ่าน config ล่าสุด แล้วอัปเดต record ทั้งหมด.

        คืน summary (list ของ dict) สำหรับเอาไป log / แสดงผล
        """
        cfg = config_mod.Config(self.config_path)
        errors = cfg.validate()
        if errors:
            for msg in errors:
                log.warning("config: %s", msg)
            if not self.dry_run:
                heartbeat.send_ping(cfg, ok=False)
            return [{"record": "", "family": 0, "action": "error", "message": "; ".join(errors)}]

        self._load_state()
        records_cache = self._state.setdefault("records", {})
        zone_cache = self._state.setdefault("zones", {})

        api = cloudflare_api.CloudflareAPI(cfg.api_token)
        # dry-run: ไม่ส่ง Telegram จริง (กันส่งข้อความ/เขียนคิวโดยไม่ตั้งใจ)
        notify = _NullNotifier() if self.dry_run else notifier.TelegramNotifier.from_config(cfg)
        zone_name_cache = {}
        summary = []
        rate_limited = False

        for rec in cfg.records:
            if rate_limited:
                summary.append({"record": rec.name, "family": 0, "action": "skip", "message": "ข้าม (rate limit)"})
                continue
            try:
                zone_id = zone_cache.get(rec.zone.lower())
                if not zone_id:
                    if rec.zone:
                        zone_id = api.get_zone_id(rec.zone)
                        zone_name_cache[rec.zone.lower()] = rec.zone
                    else:
                        resolved_zone, zone_id = api.guess_zone_id(rec.name)
                        log.info("เดา zone ของ %s ได้เป็น %s", rec.name, resolved_zone)
                        zone_name_cache[rec.zone.lower()] = resolved_zone
                    zone_cache[rec.zone.lower()] = zone_id
            except cloudflare_api.CloudflareRateLimit as exc:
                rate_limited = True
                log.warning("rate limit ระหว่างหา zone: %s", exc)
                _notify_rate_limit(notify, exc)
                summary.append({"record": rec.name, "family": 0, "action": "skip", "message": str(exc)})
                continue
            except cloudflare_api.CloudflareError as exc:
                log.warning("%s: หา zone ไม่ได้: %s", rec.name, exc)
                self._invalidate_zone(rec.zone.lower())
                self._set_record_error(rec, f"หา zone ไม่ได้ ({exc})")
                summary.append({"record": rec.name, "family": 0, "action": "error", "message": str(exc)})
                notify.notify(notifier.EVENT_ERROR, f"{rec.name}: หา zone ไม่ได้ ({exc})")
                continue

            zone_name = rec.zone.strip().rstrip(".") or zone_name_cache.get(rec.zone.lower(), "")
            fqdn = fqdn_name(rec.name, zone_name)
            if fqdn != rec.name:
                log.debug("ใช้ชื่อเต็ม %s (จาก %s + %s)", fqdn, rec.name, zone_name)

            for family in (4, 6):
                enabled = rec.ipv4 if family == 4 else rec.ipv6
                if not enabled or not (cfg.use_ipv4 if family == 4 else cfg.use_ipv6):
                    continue
                entry = self._sync_family(
                    api, zone_id, rec, fqdn, family, notify,
                    zone_key=rec.zone.lower(), reject_cloudflare_ips=cfg.reject_cloudflare_ips,
                )
                if entry:
                    if entry.get("action") == "skip":
                        rate_limited = True
                    summary.append(entry)

        # ลบ error ค้างของ record/family ที่ไม่มีการตั้งค่าแล้ว (กันโชว์ของเก่าค้างในเว็บ)
        errs = self._state.setdefault("record_errors", {})
        valid_keys = set()
        for rec in cfg.records:
            for fam, rtype in RECORD_TYPES.items():
                rec_enabled = rec.ipv4 if fam == 4 else rec.ipv6
                global_enabled = cfg.use_ipv4 if fam == 4 else cfg.use_ipv6
                if rec_enabled and global_enabled:
                    valid_keys.add(f"{rec.name.lower()}|{rtype}")
        for stale in [k for k in errs if k not in valid_keys]:
            del errs[stale]

        self._state["last_run"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        if not self.dry_run:
            self._save_state()
        # ส่งข้อความสรุปการอัปเดตเป็นข้อความเดียว (IP เปลี่ยน A+AAAA พร้อมกันไม่สแปม 2 อัน)
        changes = [e for e in summary if e.get("action") in ("updated", "created")]
        if changes:
            lines = []
            for entry in changes:
                rtype = RECORD_TYPES.get(entry.get("family", 0), "")
                prefix = "🆕 " if entry.get("action") == "created" else ""
                lines.append(f"• {prefix}{entry['record']} ({rtype}): {entry['message']}")
            event = (
                notifier.EVENT_CREATED
                if all(e.get("action") == "created" for e in changes)
                else notifier.EVENT_IP_CHANGE
            )
            notify.notify(event, "\n".join(lines))
        notify.flush()
        if not self.dry_run:
            bad = any(e.get("action") in ("error", "no-ip", "skip") for e in summary)
            heartbeat.send_ping(cfg, ok=not bad)
        return summary

    def _set_record_error(self, rec, message, family=None):
        """จด error ล่าสุดของ record ไว้ใน state (แสดงผลใน Web UI) — ลบเมื่อสำเร็จ"""
        errs = self._state.setdefault("record_errors", {})
        if family:
            rtype = RECORD_TYPES.get(family, "")
            errs[f"{rec.name.lower()}|{rtype}"] = message
        else:
            for fam, rtype in RECORD_TYPES.items():
                errs[f"{rec.name.lower()}|{rtype}"] = message
        if not self.dry_run:
            self._save_state()

    def _clear_record_error(self, rec, family=None):
        errs = self._state.setdefault("record_errors", {})
        if family:
            rtype = RECORD_TYPES.get(family, "")
            errs.pop(f"{rec.name.lower()}|{rtype}", None)
        else:
            for fam, rtype in RECORD_TYPES.items():
                errs.pop(f"{rec.name.lower()}|{rtype}", None)

    def _sync_family(self, api, zone_id, rec, fqdn, family, notify, zone_key="", reject_cloudflare_ips=True):
        rtype = RECORD_TYPES[family]
        key = f"{fqdn.lower()}|{rtype}"
        cached = self._state.get("records", {}).get(key, "")

        public_ip = ip_detect.get_public_ip(family)
        if not public_ip:
            log.warning("%s: หา IP สาธารณะ (IPv%d) ไม่ได้", fqdn, family)
            notify.notify(
                notifier.EVENT_ERROR,
                f"{fqdn}: หา IP สาธารณะ (IPv{family}) ไม่ได้",
            )
            self._set_record_error(rec, f"ไม่พบ IP สาธารณะ (IPv{family})", family)
            return {"record": fqdn, "family": family, "action": "no-ip", "message": "ไม่พบ IP สาธารณะ"}

        if reject_cloudflare_ips and ip_detect.is_cloudflare_ip(public_ip):
            log.warning(
                "%s %s: IP %s เป็นของ Cloudflare (anycast) — ข้ามการอัปเดต "
                "(ปิดได้ด้วย reject_cloudflare_ips = false)",
                fqdn, rtype, public_ip,
            )
            self._set_record_error(
                rec, f"IP {public_ip} เป็นของ Cloudflare (anycast) — ข้าม (กันเขียน record ผิด)", family
            )
            return {"record": fqdn, "family": family, "action": "skip", "message": "IP เป็นของ Cloudflare (anycast) — ข้าม"}

        if cached == public_ip:
            log.debug("%s %s: IP ไม่เปลี่ยน (%s)", fqdn, rtype, public_ip)
            return None

        try:
            current = api.get_record(zone_id, fqdn, rtype)
        except cloudflare_api.CloudflareRateLimit as exc:
            log.warning("%s %s: rate limit: %s", fqdn, rtype, exc)
            _notify_rate_limit(notify, exc)
            return {"record": fqdn, "family": family, "action": "skip", "message": str(exc)}
        except cloudflare_api.CloudflareError as exc:
            log.warning("%s %s: อ่าน record ไม่ได้: %s", fqdn, rtype, exc)
            if zone_key and _is_zone_not_found(str(exc)):
                self._invalidate_zone(zone_key)
            self._set_record_error(rec, str(exc), family)
            notify.notify(
                notifier.EVENT_ERROR,
                f"{fqdn} ({rtype}): อ่าน record ไม่ได้ ({exc})",
            )
            return {"record": fqdn, "family": family, "action": "error", "message": str(exc)}

        if current and current.get("content") == public_ip:
            now = datetime.now(timezone.utc).isoformat(timespec="seconds")
            self._state["records"][key] = public_ip
            self._state.setdefault("records_time", {})[key] = now
            self._clear_record_error(rec, family)
            log.info("%s %s: record ตรงอยู่แล้ว (%s) อัปเดต cache", fqdn, rtype, public_ip)
            return None

        if self.dry_run:
            target = "อัปเดต" if current else "สร้าง"
            log.info("[dry-run] %s %s: %s %s -> %s", fqdn, rtype, target, current.get("content") if current else "(ไม่มี)", public_ip)
            return {"record": fqdn, "family": family, "action": "dry-run", "message": f"{target} {public_ip}"}

        try:
            if current:
                api.update_record(zone_id, current["id"], public_ip, rec.ttl, rec.proxied)
                action = "updated"
                message = f"{current.get('content', '(เดิม)')} -> {public_ip}"
            else:
                api.create_record(zone_id, fqdn, rtype, public_ip, rec.ttl, rec.proxied)
                action = "created"
                message = public_ip
            self._state["records"][key] = public_ip
            self._state.setdefault("records_time", {})[key] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            self._clear_record_error(rec, family)
            self._state.setdefault("history", []).append(
                {
                    "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "record": fqdn,
                    "type": rtype,
                    "action": action,
                    "ip": public_ip,
                }
            )
            self._state["history"] = self._state["history"][-50:]
            log.info("%s %s: %s (%s)", fqdn, rtype, action, message)
            return {"record": fqdn, "family": family, "action": action, "message": message}
        except cloudflare_api.CloudflareRateLimit as exc:
            log.warning("%s %s: rate limit: %s", fqdn, rtype, exc)
            _notify_rate_limit(notify, exc)
            return {"record": fqdn, "family": family, "action": "skip", "message": str(exc)}
        except cloudflare_api.CloudflareError as exc:
            log.warning("%s %s: %s ล้มเหลว: %s", fqdn, rtype, "อัปเดต" if current else "สร้าง", exc)
            if zone_key and _is_zone_not_found(str(exc)):
                self._invalidate_zone(zone_key)
            notify.notify(
                notifier.EVENT_ERROR,
                f"{fqdn} ({rtype}): {'อัปเดต' if current else 'สร้าง'} ล้มเหลว ({exc})",
            )
            return {"record": fqdn, "family": family, "action": "error", "message": str(exc)}


def _build_start_message(cfg):
    """สร้างเนื้อหาข้อความ 'เริ่มทำงาน' (หัวข้อ/เวลา/ชื่อเครื่อง build_message เติมให้):
    IP ที่ตรวจได้ / รายการ DDNS + Tunnel"""
    lines = []
    lines.append(f"ตรวจทุก {int(cfg.interval_seconds)} วิ")
    lines.append("")

    ips = []
    for family in (4, 6):
        try:
            ip = ip_detect.get_public_ip(family, timeout=6)
        except Exception:
            ip = None
        if ip:
            ips.append(f"{ip} (IPv{family})")
    if ips:
        lines.append(f"IP สาธารณะ: {' · '.join(ips)} — รวม {len(ips)}")
    else:
        lines.append("IP สาธารณะ: ตรวจไม่ได้ (เช็คเน็ต/ไฟร์วอลล์)")

    active = [
        r for r in cfg.records
        if (r.ipv4 and cfg.use_ipv4) or (r.ipv6 and cfg.use_ipv6)
    ]
    if active:
        lines.append("")
        lines.append(f"📋 DDNS ({len(active)}):")
        for rec in active:
            types = [
                rtype
                for fam, rtype in ((4, "A"), (6, "AAAA"))
                if (rec.ipv4 if fam == 4 else rec.ipv6)
                and (cfg.use_ipv4 if fam == 4 else cfg.use_ipv6)
            ]
            lines.append(f"• {fqdn_name(rec.name, rec.zone)} — {', '.join(types)}")
    else:
        lines.append("")
        lines.append("📋 DDNS: ยังไม่มี record")

    if cfg.tunnel_enabled:
        lines.append("")
        if cfg.tunnel_hosts:
            lines.append(f"🌐 Tunnel ({len(cfg.tunnel_hosts)}):")
            for host in cfg.tunnel_hosts:
                name = host.get("hostname", "") + host.get("path", "")
                lines.append(f"• {name} → {host.get('service', '')}")
        else:
            lines.append("🌐 Tunnel: เปิดอยู่ (ยังไม่มี hostname)")
    return "\n".join(lines)


def _send_daily_report(engine, cfg, notify):
    """ส่งสรุปสถานะประจำวันทาง Telegram (วันละครั้ง กันซ้ำด้วยวันที่ใน state)."""
    if not notify.enabled:
        return
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        engine._load_state()
        if engine._state.get("daily_report_last") == today:
            return
    except Exception:
        return

    records = engine._state.get("records", {})
    records_time = engine._state.get("records_time", {})
    history = engine._state.get("history", [])
    today_count = sum(1 for h in history if (h.get("time") or "").startswith(today))

    lines = ["📊 สรุปประจำวัน Cloudflare DDNS", f"วันที่ {datetime.now().strftime('%d/%m/%Y')}", ""]
    if records:
        for key, ip in records.items():
            t = records_time.get(key, "")
            time_str = datetime.fromisoformat(t).strftime("%H:%M") if t else "-"
            lines.append(f"• {key}: {ip} (อัปเดต {time_str})")
    else:
        lines.append("• ยังไม่มี IP ในระบบ")
    lines.append("")
    lines.append(f"อัปเดตวันนี้: {today_count} ครั้ง")
    lines.append(f"สถานะ: {'ใช้งานปกติ' if cfg.validate() == [] else 'ตั้งค่าไม่ครบ'}")

    message = "\n".join(lines)
    ok, error = notify.send_raw(message)
    if ok:
        log.info("ส่งรายงานประจำวันสำเร็จ")
    else:
        log.warning("ส่งรายงานประจำวันไม่ได้ (เก็บคิว): %s", error)
        items = notifier.load_queue()
        items.append(message)
        notifier.save_queue(items)
    try:
        engine._state["daily_report_last"] = today
        engine._save_state()
    except Exception as exc:
        log.warning("บันทึก daily_report_last ไม่ได้: %s", exc)


def run_forever(config_path=config_mod.DEFAULT_CONFIG_PATH, dry_run=False, stop_event=None):
    """ลูปหลัก: รันทุก interval ตาม config (อ่าน config ใหม่ทุกรอบ)."""
    log.info("เริ่ม DDNS loop (dry_run=%s)", dry_run)
    config_mod.migrate_legacy_data()
    cfg0 = config_mod.Config(config_path)
    notify = notifier.TelegramNotifier.from_config(cfg0)
    if not dry_run:
        # ตรวจ NAT ครั้งเดียวตอนเริ่ม: ถ้าเป็น CGNAT/private เตือนทันที (DDNS จะไม่เวิร์ก)
        try:
            nat = ip_detect.nat_report(timeout=6)
            if nat["nat_type"] in ("cg-nat", "private-ip"):
                log.warning("NAT: %s", nat["message"])
                notify.notify(notifier.EVENT_ERROR, nat["message"])
            else:
                log.info("NAT: %s", nat["message"])
        except Exception as exc:
            log.warning("ตรวจ NAT ไม่ได้: %s", exc)
        notify.notify(
            notifier.EVENT_START,
            _build_start_message(cfg0),
        )
        notify.flush()
        heartbeat.send_ping(cfg0, ok=True)
    loop_started = time.monotonic()
    round_count = 0
    while True:
        started = time.monotonic()
        try:
            engine = DDNSEngine(config_path, dry_run=dry_run)
            result = engine.run_once()
        except Exception:
            result = [{"record": "", "family": 0, "action": "error", "message": "exception ใน loop"}]
            log.exception("เกิดข้อผิดพลาดไม่คาดคิดในรอบ DDNS (รันรอบถัดไปต่อ)")
            try:
                notify.notify(notifier.EVENT_ERROR, "เกิดข้อผิดพลาดใน DDNS loop ดู log ไฟล์เพิ่มเติม")
                notify.flush()
                heartbeat.send_ping(config_mod.Config(config_path), ok=False)
            except Exception as exc:
                log.warning("แจ้งเตือน/ส่ง heartbeat หลัง error ล้มเหลว: %s", exc)
        cfg = config_mod.Config(config_path)
        round_count += 1
        interval = max(cfg.interval_seconds, config_mod.MIN_INTERVAL)
        elapsed = time.monotonic() - started

        # สรุปผลทุกรอบ (ไม่บังคับ — เปิดด้วย notify_round = true)
        try:
            if not dry_run and cfg.notify_round:
                changed = sum(1 for e in result if e.get("action") in ("updated", "created"))
                problems = sum(1 for e in result if e.get("action") in ("error", "no-ip", "skip"))
                total = len(result)
                if not result:
                    text = "ตรวจ record ทั้งหมดตรง ไม่มีการเปลี่ยน"
                else:
                    text = f"ตรวจ {total} รายการ · เปลี่ยน {changed} · มีปัญหา {problems}"
                notify.notify(notifier.EVENT_ROUND, text)
        except Exception as exc:
            log.warning("notify_round error: %s", exc)

        # รายงานสรุปประจำวัน (ส่งครั้งเดียวต่อวัน ตามเวลาที่ตั้งใน config)
        try:
            if not dry_run and cfg.daily_report and cfg.daily_report_time:
                now_hm = datetime.now().strftime("%H:%M")
                if now_hm == cfg.daily_report_time and engine._state.get("last_run"):
                    _send_daily_report(engine, cfg, notify)
        except Exception as exc:
            log.warning("daily report error: %s", exc)

        wait = max(min(interval - elapsed, 5), 1)
        if stop_event is not None:
            if stop_event.wait(wait):
                log.info("หยุด loop ตามคำสั่ง")
                if not dry_run:
                    duration = time.monotonic() - loop_started
                    hours, rem = divmod(int(duration), 3600)
                    minutes = rem // 60
                    notify.notify(
                        notifier.EVENT_STOP,
                        f"สาเหตุ: หยุดตามคำสั่ง (service stop/ปิดเครื่อง)\n"
                        f"รันต่อเนื่อง: {hours} ชม. {minutes} นาที · ผ่าน {round_count} รอบ",
                    )
                    notify.flush()
                    heartbeat.send_ping(config_mod.Config(config_path), ok=False, stopped=True)
                break
        else:
            time.sleep(wait)
