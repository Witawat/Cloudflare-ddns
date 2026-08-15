"""แกนหลัก DDNS: ตรวจ IP -> เทียบกับ cache -> อัปเดต Cloudflare เฉพาะเมื่อเปลี่ยน."""

import json
import logging
import os
import time
from datetime import datetime, timezone

from . import cloudflare_api
from . import config as config_mod
from . import ip_detect
from . import notifier

log = logging.getLogger("cloudflare-ddns")

RECORD_TYPES = {4: "A", 6: "AAAA"}


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

    def _save_state(self):
        os.makedirs(os.path.dirname(config_mod.DEFAULT_STATE_PATH), exist_ok=True)
        try:
            with open(config_mod.DEFAULT_STATE_PATH, "w", encoding="utf-8") as handle:
                json.dump(self._state, handle, indent=2, ensure_ascii=False)
        except OSError as exc:
            log.warning("บันทึก state ไม่ได้: %s", exc)

    def status(self):
        """ข้อมูลสถานะสำหรับ Web UI / status command"""
        self._load_state()
        return {
            "last_run": self._state.get("last_run", ""),
            "records": self._state.get("records", {}),
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
            return [{"record": "", "family": 0, "action": "error", "message": "; ".join(errors)}]

        self._load_state()
        records_cache = self._state.setdefault("records", {})

        api = cloudflare_api.CloudflareAPI(cfg.api_token)
        notify = notifier.TelegramNotifier.from_config(cfg)
        zone_cache = {}
        summary = []

        for rec in cfg.records:
            try:
                zone_id = zone_cache.get(rec.zone.lower())
                if not zone_id:
                    if rec.zone:
                        zone_id = api.get_zone_id(rec.zone)
                    else:
                        resolved_zone, zone_id = api.guess_zone_id(rec.name)
                        log.info("เดา zone ของ %s ได้เป็น %s", rec.name, resolved_zone)
                    zone_cache[rec.zone.lower()] = zone_id
            except cloudflare_api.CloudflareError as exc:
                log.warning("%s: หา zone ไม่ได้: %s", rec.name, exc)
                summary.append({"record": rec.name, "family": 0, "action": "error", "message": str(exc)})
                notify.notify(notifier.EVENT_ERROR, f"{rec.name}: หา zone ไม่ได้ ({exc})")
                continue

            for family in (4, 6):
                enabled = rec.ipv4 if family == 4 else rec.ipv6
                if not enabled or not (cfg.use_ipv4 if family == 4 else cfg.use_ipv6):
                    continue
                entry = self._sync_family(api, zone_id, rec, family, notify)
                if entry:
                    summary.append(entry)

        self._state["last_run"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self._save_state()
        notify.flush()
        return summary

    def _sync_family(self, api, zone_id, rec, family, notify):
        rtype = RECORD_TYPES[family]
        key = f"{rec.name.lower()}|{rtype}"
        cached = self._state.get("records", {}).get(key, "")

        public_ip = ip_detect.get_public_ip(family)
        if not public_ip:
            log.warning("%s: หา IP สาธารณะ (IPv%d) ไม่ได้", rec.name, family)
            notify.notify(
                notifier.EVENT_ERROR,
                f"{rec.name}: หา IP สาธารณะ (IPv{family}) ไม่ได้",
            )
            return {"record": rec.name, "family": family, "action": "no-ip", "message": "ไม่พบ IP สาธารณะ"}

        if cached == public_ip:
            log.debug("%s %s: IP ไม่เปลี่ยน (%s)", rec.name, rtype, public_ip)
            return None

        try:
            current = api.get_record(zone_id, rec.name, rtype)
        except cloudflare_api.CloudflareError as exc:
            log.warning("%s %s: อ่าน record ไม่ได้: %s", rec.name, rtype, exc)
            notify.notify(
                notifier.EVENT_ERROR,
                f"{rec.name} ({rtype}): อ่าน record ไม่ได้ ({exc})",
            )
            return {"record": rec.name, "family": family, "action": "error", "message": str(exc)}

        if current and current.get("content") == public_ip:
            self._state["records"][key] = public_ip
            log.info("%s %s: record ตรงอยู่แล้ว (%s) อัปเดต cache", rec.name, rtype, public_ip)
            return None

        if self.dry_run:
            target = "อัปเดต" if current else "สร้าง"
            log.info("[dry-run] %s %s: %s %s -> %s", rec.name, rtype, target, current.get("content") if current else "(ไม่มี)", public_ip)
            return {"record": rec.name, "family": family, "action": "dry-run", "message": f"{target} {public_ip}"}

        try:
            if current:
                api.update_record(zone_id, current["id"], public_ip, rec.ttl, rec.proxied)
                action = "updated"
                message = f"{current.get('content', '(เดิม)')} -> {public_ip}"
            else:
                api.create_record(zone_id, rec.name, rtype, public_ip, rec.ttl, rec.proxied)
                action = "created"
                message = public_ip
            self._state["records"][key] = public_ip
            self._state.setdefault("history", []).append(
                {
                    "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "record": rec.name,
                    "type": rtype,
                    "action": action,
                    "ip": public_ip,
                }
            )
            self._state["history"] = self._state["history"][-50:]
            log.info("%s %s: %s (%s)", rec.name, rtype, action, message)
            if action == "updated":
                notify.notify(
                    notifier.EVENT_IP_CHANGE,
                    f"{rec.name} ({rtype})\n{message}",
                )
            elif action == "created":
                notify.notify(
                    notifier.EVENT_CREATED,
                    f"{rec.name} ({rtype}) = {public_ip}",
                )
            return {"record": rec.name, "family": family, "action": action, "message": message}
        except cloudflare_api.CloudflareError as exc:
            log.warning("%s %s: %s ล้มเหลว: %s", rec.name, rtype, "อัปเดต" if current else "สร้าง", exc)
            notify.notify(
                notifier.EVENT_ERROR,
                f"{rec.name} ({rtype}): {'อัปเดต' if current else 'สร้าง'} ล้มเหลว ({exc})",
            )
            return {"record": rec.name, "family": family, "action": "error", "message": str(exc)}


def run_forever(config_path=config_mod.DEFAULT_CONFIG_PATH, dry_run=False, stop_event=None):
    """ลูปหลัก: รันทุก interval ตาม config (อ่าน config ใหม่ทุกรอบ)."""
    log.info("เริ่ม DDNS loop (dry_run=%s)", dry_run)
    cfg0 = config_mod.Config(config_path)
    notify = notifier.TelegramNotifier.from_config(cfg0)
    if not dry_run:
        notify.notify(
            notifier.EVENT_START,
            f"ตรวจ IP ทุก {int(cfg0.interval_seconds)} วิ · {len(cfg0.records)} records",
        )
        notify.flush()
    while True:
        started = time.monotonic()
        engine = DDNSEngine(config_path, dry_run=dry_run)
        engine.run_once()
        cfg = config_mod.Config(config_path)
        interval = max(cfg.interval_seconds, config_mod.MIN_INTERVAL)
        elapsed = time.monotonic() - started
        wait = max(interval - elapsed, 1)
        if stop_event is not None:
            if stop_event.wait(wait):
                log.info("หยุด loop ตามคำสั่ง")
                if not dry_run:
                    notify.notify(notifier.EVENT_STOP, "")
                    notify.flush()
                break
        else:
            time.sleep(wait)
