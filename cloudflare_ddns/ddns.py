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
from . import i18n
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
        notify.notify(notifier.EVENT_ERROR, i18n.t(getattr(notify, "lang", "th") or "th", "ddns.rl_skip").format(exc))


class DDNSEngine:
    """engine หนึ่งตัว = อ่าน config -> ตรวจ IP -> อัปเดต record ทุกตัว"""

    def __init__(self, config_path=config_mod.DEFAULT_CONFIG_PATH, dry_run=False):
        self.config_path = config_path
        self.dry_run = dry_run
        self._state = {}
        # state อยู่ข้าง config.ini ที่ใช้ (ข้าง exe เมื่อรัน exe) — กัน state แยกชุด
        # เมื่อรันโปรแกรมจากหลายจุด/หลาย config
        self._state_path = config_mod.state_path_for(config_path)

    # ---- state (cache IP ล่าสุด ไว้เทียบเพื่อลดการเรียก API) ----

    def _load_state(self):
        try:
            with open(self._state_path, "r", encoding="utf-8") as handle:
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
        if self.dry_run:
            return
        os.makedirs(os.path.dirname(self._state_path), exist_ok=True)
        try:
            text = json.dumps(self._state, indent=2, ensure_ascii=False)
        except TypeError:
            log.warning("บันทึก state ไม่ได้ (serialize ไม่ผ่าน)")
            return
        # เนื้อหาเหมือนเดิม = ไม่เขียน (กัน backup หมุนสะสมไร้ประโยชน์)
        try:
            with open(self._state_path, "r", encoding="utf-8") as handle:
                if handle.read() == text:
                    return
        except OSError:
            pass
        config_mod.rotate_backup(self._state_path, keep=3)
        tmp = self._state_path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as handle:
                handle.write(text)
            os.replace(tmp, self._state_path)
        except OSError as exc:
            log.warning("บันทึก state ไม่ได้: %s", exc)

    def status(self):
        """ข้อมูลสถานะสำหรับ Web UI / status command

        กรอง records/errors ตาม config ปัจจุบัน — record ที่ถูกลบออกจาก config
        แล้ว จะไม่โชว์ค้าง (cache เก่าใน state)
        """
        self._load_state()
        cfg = config_mod.Config(self.config_path)
        valid = set()
        for rec in cfg.records:
            zone = (rec.zone or "").strip().rstrip(".")
            fqdn = fqdn_name(rec.name, zone)
            for family, rtype in RECORD_TYPES.items():
                rec_enabled = rec.ipv4 if family == 4 else rec.ipv6
                global_enabled = cfg.use_ipv4 if family == 4 else cfg.use_ipv6
                if rec_enabled and global_enabled:
                    valid.add(f"{fqdn.lower()}|{rtype}")
        records = {k: v for k, v in self._state.get("records", {}).items() if k in valid}
        errors = {k: v for k, v in self._state.get("record_errors", {}).items() if k in valid}
        return {
            "last_run": self._state.get("last_run", ""),
            "records": records,
            "history": self._state.get("history", [])[-50:],
            "record_errors": errors,
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
                lang = getattr(notify, "lang", "th") or "th"
                self._set_record_error(rec, i18n.t("th", "ddns.zone_err").format(exc))
                summary.append({"record": rec.name, "family": 0, "action": "error", "message": str(exc)})
                notify.notify(notifier.EVENT_ERROR, i18n.t(lang, "ddns.zone_notify").format(rec.name, exc))
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
                    consensus=2 if cfg.ip_consensus else 0,
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

    def _sync_family(self, api, zone_id, rec, fqdn, family, notify, zone_key="", reject_cloudflare_ips=True, consensus=0):
        rtype = RECORD_TYPES[family]
        lang = getattr(notify, "lang", "th") or "th"
        key = f"{fqdn.lower()}|{rtype}"
        cached = self._state.get("records", {}).get(key, "")

        public_ip = ip_detect.get_public_ip(family, consensus=consensus)
        if not public_ip:
            log.warning("%s: หา IP สาธารณะ (IPv%d) ไม่ได้", fqdn, family)
            notify.notify(
                notifier.EVENT_ERROR,
                i18n.t(lang, "ddns.no_ip_notify").format(fqdn, family),
            )
            self._set_record_error(rec, i18n.t("th", "ddns.no_ip_err").format(family), family)
            return {"record": fqdn, "family": family, "action": "no-ip", "message": i18n.t(lang, "ddns.no_ip_msg")}

        if reject_cloudflare_ips and ip_detect.is_cloudflare_ip(public_ip):
            log.warning(
                "%s %s: IP %s เป็นของ Cloudflare (anycast) — ข้ามการอัปเดต "
                "(ปิดได้ด้วย reject_cloudflare_ips = false)",
                fqdn, rtype, public_ip,
            )
            self._set_record_error(
                rec, i18n.t("th", "ddns.cf_ip_err").format(public_ip), family
            )
            return {"record": fqdn, "family": family, "action": "skip", "message": i18n.t(lang, "ddns.cf_ip_msg")}

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
                i18n.t(lang, "ddns.read_rec_fail").format(fqdn, rtype, exc),
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
            target = i18n.t(lang, "ddns.act.update") if current else i18n.t(lang, "ddns.act.create")
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
                i18n.t(getattr(notify, "lang", "th") or "th", "ddns.err_sync").format(
                    fqdn, rtype, i18n.t(getattr(notify, "lang", "th") or "th", "ddns.act.update") if current else i18n.t(getattr(notify, "lang", "th") or "th", "ddns.act.create"), exc
                ),
            )
            return {"record": fqdn, "family": family, "action": "error", "message": str(exc)}


def _build_start_message(cfg, lang="th"):
    """สร้างเนื้อหาข้อความ 'เริ่มทำงาน' (หัวข้อ/เวลา/ชื่อเครื่อง build_message เติมให้):
    IP ที่ตรวจได้ / รายการ DDNS + Tunnel"""
    lines = []
    lines.append(i18n.t(lang, "ddns.start.interval").format(int(cfg.interval_seconds)))
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
        lines.append(i18n.t(lang, "ddns.start.ips").format(" · ".join(ips), len(ips)))
    else:
        lines.append(i18n.t(lang, "ddns.start.ips_fail"))

    active = [
        r for r in cfg.records
        if (r.ipv4 and cfg.use_ipv4) or (r.ipv6 and cfg.use_ipv6)
    ]
    if active:
        lines.append("")
        lines.append(i18n.t(lang, "ddns.start.ddns").format(len(active)))
        for rec in active:
            types = [
                rtype
                for fam, rtype in ((4, "A"), (6, "AAAA"))
                if (rec.ipv4 if fam == 4 else rec.ipv6)
                and (cfg.use_ipv4 if fam == 4 else cfg.use_ipv6)
            ]
            lines.append(i18n.t(lang, "ddns.start.rec").format(fqdn_name(rec.name, rec.zone), ", ".join(types)))
    else:
        lines.append("")
        lines.append(i18n.t(lang, "ddns.start.ddns_none"))

    if cfg.tunnel_enabled:
        lines.append("")
        if cfg.tunnel_hosts:
            lines.append(i18n.t(lang, "ddns.start.tunnel").format(len(cfg.tunnel_hosts)))
            for host in cfg.tunnel_hosts:
                name = host.get("hostname", "") + host.get("path", "")
                lines.append(i18n.t(lang, "ddns.start.tunnel_rec").format(name, host.get("service", "")))
        else:
            lines.append(i18n.t(lang, "ddns.start.tunnel_none"))
    return "\n".join(lines)


def _send_daily_report(engine, cfg, notify):
    """ส่งสรุปสถานะประจำวันทาง Telegram (วันละครั้ง กันซ้ำด้วยวันที่ใน state)."""
    if not notify.enabled:
        return
    lang = getattr(notify, "lang", "th") or "th"
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

    lines = [
        i18n.t(lang, "ddns.daily.title"),
        i18n.t(lang, "ddns.daily.date").format(datetime.now().strftime("%d/%m/%Y")),
        "",
    ]
    if records:
        for key, ip in records.items():
            t = records_time.get(key, "")
            time_str = datetime.fromisoformat(t).strftime("%H:%M") if t else "-"
            lines.append(i18n.t(lang, "ddns.daily.rec").format(key, ip, time_str))
    else:
        lines.append(i18n.t(lang, "ddns.daily.none"))
    lines.append("")
    lines.append(i18n.t(lang, "ddns.daily.updates").format(today_count))
    lines.append(i18n.t(lang, "ddns.daily.status").format(
        i18n.t(lang, "ddns.daily.status_ok") if cfg.validate() == [] else i18n.t(lang, "ddns.daily.status_bad")
    ))

    message = "\n".join(lines)
    ok, error = notify.send_raw(message)
    if ok:
        log.info("ส่งรายงานประจำวันสำเร็จ")
    else:
        log.warning("ส่งรายงานประจำวันไม่ได้ (เก็บคิว): %s", error)
        queue_path = config_mod.queue_path_for(engine.config_path)
        items = notifier.load_queue(queue_path)
        items.append(message)
        notifier.save_queue(items, queue_path)
    try:
        engine._state["daily_report_last"] = today
        engine._save_state()
    except Exception as exc:
        log.warning("บันทึก daily_report_last ไม่ได้: %s", exc)


_periodic_update_at = 0.0
PERIODIC_UPDATE_INTERVAL = 3600  # เช็คเวอร์ชันใหม่ทุก 1 ชม. (รันยาว ๆ ก็รู้ว่ามีรุ่นใหม่)


def _periodic_update_check(cfg, config_path):
    """เช็คเวอร์ชันใหม่เป็นระยะ (ทุก 1 ชม.) — import ข้างใน กัน circular (webui import ddns).

    ใช้ logic เดียวกับตอนเริ่มโปรแกรม (_startup_update_check) — cache 1 ชม. + แจ้ง Telegram
    1 ครั้งต่อเวอร์ชันต่อ process (ไม่สแปม) — GitHub rate limit 60/ชม. ไม่มี token: 24 ครั้ง/วัน ปลอดภัย
    """
    global _periodic_update_at
    now = time.time()
    if now - _periodic_update_at < PERIODIC_UPDATE_INTERVAL:
        return
    _periodic_update_at = now
    try:
        from . import webui as webui_mod

        webui_mod._startup_update_check(cfg, config_path)
    except Exception as exc:
        log.debug("periodic update check: %s", exc)


_tunnel_check_at = 0.0
TUNNEL_CHECK_INTERVAL = 30  # ตรวจ tunnel ตาย/ไม่รัน ทุก 30 วิ — ตายแล้วเริ่มใหม่เอง


def _ensure_tunnel_running(cfg, config_path):
    """Cloudflare Tunnel ตาย (crash/ถูกปิดจากนอก) -> เริ่มใหม่เอง — ไม่ต้องมานั่งกดเอง

    เช็คทุก 30 วิ (ไม่ใช่ทุกรอบ loop — กันสแปม start) — ข้ามถ้าไม่ได้เปิด tunnel_enabled
    """
    global _tunnel_check_at
    if not getattr(cfg, "tunnel_enabled", False):
        return
    now = time.time()
    if now - _tunnel_check_at < TUNNEL_CHECK_INTERVAL:
        return
    _tunnel_check_at = now
    try:
        from . import tunnel as tunnel_mod

        mgr = tunnel_mod.TunnelManager(config_path)
        status = mgr.status(cfg)
        if status.get("running"):
            return
        log.warning("Cloudflare Tunnel ไม่รันอยู่ — เริ่มใหม่เอง")
        result = mgr.start(cfg)
        message = result[1] if isinstance(result, (tuple, list)) else str(result)
        log.info("Cloudflare Tunnel: %s", message)
    except Exception as exc:
        log.warning("ตรวจ/เริ่ม tunnel ใหม่ไม่ได้: %s", exc)


def run_forever(config_path=config_mod.DEFAULT_CONFIG_PATH, dry_run=False, stop_event=None):
    """ลูปหลัก: รันทุก interval ตาม config (อ่าน config ใหม่ทุกรอบ)."""
    import os as _os

    log.info(
        "เริ่ม DDNS loop (pid=%d, config=%s, interval=%ds, dry_run=%s)",
        _os.getpid(), config_path, int(config_mod.Config(config_path).interval_seconds), dry_run,
    )
    config_mod.migrate_legacy_data()
    cfg0 = config_mod.Config(config_path)
    notify = notifier.TelegramNotifier.from_config(cfg0)
    if not dry_run:
        # ตรวจ NAT ครั้งเดียวตอนเริ่ม: ถ้าเป็น CGNAT/private เตือนทันที (DDNS จะไม่เวิร์ก)
        try:
            nat_lang = getattr(notify, "lang", "th") or "th"
            nat = ip_detect.nat_report(timeout=6, lang=nat_lang)
            if nat["nat_type"] in ("cg-nat", "private-ip"):
                log.warning("NAT: %s", nat["message"])
                notify.notify(notifier.EVENT_ERROR, nat["message"])
            else:
                log.info("NAT: %s", nat["message"])
        except Exception as exc:
            log.warning("ตรวจ NAT ไม่ได้: %s", exc)
        notify.notify(
            notifier.EVENT_START,
            _build_start_message(cfg0, getattr(notify, "lang", "th") or "th"),
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
            result = [{"record": "", "family": 0, "action": "error", "message": i18n.t(getattr(notify, "lang", "th") or "th", "ddns.loop_exc")}]
            log.exception("เกิดข้อผิดพลาดไม่คาดคิดในรอบ DDNS (รันรอบถัดไปต่อ)")
            try:
                notify.notify(notifier.EVENT_ERROR, i18n.t(getattr(notify, "lang", "th") or "th", "ddns.loop_err"))
                notify.flush()
                heartbeat.send_ping(config_mod.Config(config_path), ok=False)
            except Exception as exc:
                log.warning("แจ้งเตือน/ส่ง heartbeat หลัง error ล้มเหลว: %s", exc)
        cfg = config_mod.Config(config_path)
        round_count += 1
        interval = max(cfg.interval_seconds, config_mod.MIN_INTERVAL)
        elapsed = time.monotonic() - started

        # ฟังคำสั่ง Telegram (opt-in: telegram_allow_reset) — /status /run /restart ฯลฯ + กู้รหัสผ่าน
        if not dry_run:
            try:
                notifier.check_telegram_commands(cfg, config_path)
            except Exception as exc:
                log.debug("telegram commands: ตรวจคำสั่งไม่ได้: %s", exc)

        # เช็คเวอร์ชันใหม่เป็นระยะ (ทุก 24 ชม.) — service รันยาว ๆ ก็รู้ว่ามีรุ่นใหม่
        if not dry_run:
            _periodic_update_check(cfg, config_path)

        # tunnel ตาย -> เริ่มใหม่เอง (ทุก 30 วิ) — ไม่ต้องมานั่งกดเริ่มเองตอน service restart
        if not dry_run:
            _ensure_tunnel_running(cfg, config_path)

        # สรุปผลทุกรอบ (ไม่บังคับ — เปิดด้วย notify_round = true)
        try:
            if not dry_run and cfg.notify_round:
                lang = getattr(notify, "lang", "th") or "th"
                changed = sum(1 for e in result if e.get("action") in ("updated", "created"))
                problems = sum(1 for e in result if e.get("action") in ("error", "no-ip", "skip"))
                total = len(result)
                if not result:
                    text = i18n.t(lang, "ddns.round_none")
                else:
                    text = i18n.t(lang, "ddns.round_summary").format(total, changed, problems)
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

        wait = max(interval - elapsed, 1)
        stopped = False
        if stop_event is not None:
            # รอจนครบ interval จริง (เดิม min(...,5) ทำให้วน run_once ทุก 5 วิ =
            # heartbeat เบิ้ล 2 ครั้ง/นาที) — แต่เช็ค stop_event ทุก ≤5 วิ
            # เพื่อให้ service หยุดไว (ไม่บล็อก SCM 30 วิ)
            deadline = time.monotonic() + wait
            while True:
                left = deadline - time.monotonic()
                if left <= 0:
                    break
                if stop_event.wait(min(left, 5.0)):
                    stopped = True
                    break
        else:
            time.sleep(wait)

        if stopped:
            log.info("หยุด loop ตามคำสั่ง")
            if not dry_run:
                duration = time.monotonic() - loop_started
                hours, rem = divmod(int(duration), 3600)
                minutes = rem // 60
                notify.notify(
                    notifier.EVENT_STOP,
                    i18n.t(getattr(notify, "lang", "th") or "th", "ddns.stop_msg").format(
                        hours, minutes, round_count
                    ),
                )
                notify.flush()
                heartbeat.send_ping(config_mod.Config(config_path), ok=False, stopped=True)
            break
