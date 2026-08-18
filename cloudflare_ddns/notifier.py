"""แจ้งเตือนผ่าน Telegram (Bot API) พร้อมคิวสำรองเมื่อส่งไม่สำเร็จ.

- ส่งข้อความผ่าน https://api.telegram.org/bot<token>/sendMessage
- ส่งไม่สำเร็จ -> เก็บลง notify_queue.json แล้วพยายามส่งใหม่ในรอบถัดไป
- กันสแปม: ข้อความ error ซ้ำกับรอบก่อนหน้า จะไม่ส่งซ้ำ
"""

import json
import logging
import os
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime

from . import config as config_mod
from . import i18n

log = logging.getLogger("cloudflare-ddns")

QUEUE_PATH = os.path.join(config_mod.DEFAULT_DATA_DIR, "notify_queue.json")
MAX_QUEUE = 50

# ล็อกคิว (ddns thread + webui thread อ่าน-เขียนพร้อมกันได้) + กันสแปม error ข้าม instance
_queue_lock = threading.Lock()
# error ซ้ำข้อความเดิมภายใน 10 นาที -> ไม่ส่งซ้ำ (key = event|detail ไม่รวม timestamp)
ERROR_DEDUPE_SECONDS = 600
_error_dedupe = {}

# ประเภทเหตุการณ์
EVENT_START = "start"
EVENT_STOP = "stop"
EVENT_IP_CHANGE = "ip_change"
EVENT_ERROR = "error"
EVENT_CREATED = "created"
EVENT_ROUND = "round"

API_URL = "https://api.telegram.org/bot{token}/sendMessage"


class TelegramNotifier:
    def __init__(self, bot_token="", chat_id="", events=None, config_path=None, name="", lang="th"):
        self.bot_token = (bot_token or "").strip()
        self.chat_id = str(chat_id or "").strip()
        self.events = events or {}
        self._last_dedupe_key = ""
        self.name = name or ""
        self.lang = lang if lang in ("th", "en") else "th"
        # คิวอยู่ข้าง config.ini ที่ใช้ (ข้าง exe เมื่อรัน exe) — กันคิวแยกชุด
        self.queue_path = config_mod.queue_path_for(config_path)

    @property
    def enabled(self):
        return bool(self.bot_token and self.chat_id)

    @classmethod
    def from_config(cls, cfg):
        return cls(
            bot_token=cfg.telegram_bot_token,
            chat_id=cfg.telegram_chat_id,
            events={
                EVENT_START: cfg.notify_start,
                EVENT_STOP: cfg.notify_stop,
                EVENT_IP_CHANGE: cfg.notify_ip_change,
                EVENT_ERROR: cfg.notify_error,
                EVENT_CREATED: cfg.notify_created,
                EVENT_ROUND: cfg.notify_round,
            },
            config_path=getattr(cfg, "path", None),
            name=_tg_command_name(cfg),
            lang=getattr(cfg, "language", "th") or "th",
        )

    def event_enabled(self, event):
        return self.events.get(event, True)

    # ---- ส่งจริง ----

    def send_raw(self, text):
        """ส่งข้อความตรง ๆ คืน (ok, error_message) ไม่ยุ่งกับ queue."""
        if not self.enabled:
            return False, i18n.t(self.lang, "tg.not_enabled")
        payload = json.dumps(
            {"chat_id": self.chat_id, "text": text}, ensure_ascii=False
        ).encode("utf-8")
        request = urllib.request.Request(
            API_URL.format(token=self.bot_token),
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                data = json.loads(response.read().decode("utf-8", "replace"))
            if data.get("ok"):
                return True, ""
            return False, data.get("description") or "sendMessage failed"
        except urllib.error.HTTPError as exc:
            return False, f"HTTP {exc.code}"
        except Exception as exc:
            return False, str(exc)

    # ---- จุดเรียกจากภายนอก ----

    def notify(self, event, text):
        """แจ้งเหตุการณ์: สร้างข้อความ -> ตรวจ enable -> กันซ้ำ -> เก็บคิว."""
        if not self.enabled:
            return
        if not self.event_enabled(event):
            return
        message = build_message(event, text, self.name, lang=self.lang)
        if not message or not message.strip():
            # กันข้อความว่างเข้าคิว — ส่งให้ Telegram ไม่ได้ (HTTP 400) แล้วจะติดคิวซ้ำไปเรื่อย ๆ
            log.debug("ข้ามการแจ้ง (ข้อความว่าง) event=%s", event)
            return
        # กันสแปม: error ข้อความเดิม (ไม่รวม timestamp) ซ้ำภายใน 10 นาที -> ข้าม
        # เก็บที่ระดับโมดูล -> instance ใหม่ทุกรอบ/สลับเหตุการณ์ก็ยังกันได้
        dedupe_key = f"{event}|{text}"
        if event == EVENT_ERROR:
            last = _error_dedupe.get(dedupe_key, 0)
            if time.time() - last < ERROR_DEDUPE_SECONDS:
                log.debug("ข้ามการแจ้ง (ซ้ำภายใน %d นาที): %s", ERROR_DEDUPE_SECONDS // 60, message)
                return
            _error_dedupe[dedupe_key] = time.time()
        self._enqueue(message)

    def _enqueue(self, text):
        with _queue_lock:
            items = load_queue(self.queue_path)
            items.append(text)
            if len(items) > MAX_QUEUE:
                dropped = items[: len(items) - MAX_QUEUE]
                items = items[-MAX_QUEUE:]
                log.warning("คิวแจ้งเตือนเต็ม ตัดทิ้ง %d ข้อความเก่า", len(dropped))
            save_queue(items, self.queue_path)
            log.info("เพิ่มข้อความแจ้งเตือนลงคิว (รวม %d ข้อความ)", len(items))

    # ---- queue ----

    def flush(self, max_seconds=60):
        """พยายามส่งคิวทั้งหมด (จำกัดเวลา max_seconds กัน block นาน) คืน (sent, failed)."""
        with _queue_lock:
            items = load_queue(self.queue_path)
            if not items:
                return 0, 0
            sent = 0
            remaining = []
            started = time.monotonic()
            for text in items:
                if time.monotonic() - started > max_seconds:
                    log.warning("flush ถึงเวลาจำกัด (%d วิ) — เหลือ %d ข้อความไว้รอบถัดไป", max_seconds, len(items) - sent - len(remaining))
                    remaining.extend(items[sent + len(remaining):])
                    break
                ok, error = self.send_raw(text)
                if ok:
                    sent += 1
                else:
                    log.warning("ส่ง Telegram ไม่สำเร็จ (เก็บไว้ส่งใหม่): %s", error)
                    remaining.append(text)
            save_queue(remaining, self.queue_path)
            if sent:
                log.info("ส่งแจ้งเตือน Telegram สำเร็จ %d ข้อความ (คิวเหลือ %d)", sent, len(remaining))
            return sent, len(remaining)


# ---- ฟังก์ชันระดับโมดูล ----

def load_queue(path=None):
    path = path or QUEUE_PATH
    try:
        with open(path, "r", encoding="utf-8") as handle:
            items = json.load(handle)
        items = items if isinstance(items, list) else []
        # กรองข้อความว่างออก (ของเก่าจากคิวที่ migrate มา) — ส่งให้ Telegram ไม่ได้ (HTTP 400)
        cleaned = [t for t in items if t and t.strip()]
        if len(cleaned) != len(items):
            try:
                save_queue(cleaned, path)
            except Exception:
                pass
        return cleaned
    except ValueError as exc:
        log.warning("อ่านคิวแจ้งเตือนไม่ได้ (ไฟล์เสีย?) — ถือว่าว่าง: %s", exc)
        return []
    except OSError:
        return []


def save_queue(items, path=None):
    path = path or QUEUE_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        text = json.dumps(items, ensure_ascii=False, indent=2)
    except TypeError:
        log.warning("บันทึกคิวแจ้งเตือนไม่ได้ (serialize ไม่ผ่าน)")
        return
    # เนื้อหาเหมือนเดิม = ไม่เขียน (กัน backup หมุนสะสมไร้ประโยชน์)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            if handle.read() == text:
                return
    except OSError:
        pass
    config_mod.rotate_backup(path, keep=3)
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp, path)
    except OSError as exc:
        log.warning("บันทึกคิวแจ้งเตือนไม่ได้: %s", exc)


def queue_size(path=None):
    return len(load_queue(path))


def clear_queue(path=None):
    """ล้างคิวทั้งหมด (ปุ่มใน Web UI)"""
    save_queue([], path)


# ---- กู้รหัสผ่านหน้าเว็บผ่าน Telegram (opt-in: telegram_allow_reset = true) ----

_reset_cooldown = 600  # reset ได้ 1 ครั้งต่อ 10 นาที
_reset_state = {"awaiting_confirm": False, "last_ask": 0.0}

# ยืนยันคำสั่งอันตราย (/run /restart /tunnel stop) — ต้องพิมพ์ yes ภายใน 2 นาที
_danger_confirm_seconds = 120
_danger_state = {"command": "", "text": "", "expires": 0}
_updates_offset = {}  # token -> offset (ยืนยันแล้ว = update_id < offset) — กันรับซ้ำ/กันขโมยคำสั่งของเครื่องอื่น
_handled_updates = {}  # token -> set(update_id ที่จัดการแล้ว) — กันตอบซ้ำตอนถูกบล็อกโดยคำสั่งเครื่องอื่น
_tg_foreign_stale = 300  # คำสั่งของเครื่องอื่นที่ค้างเกิน 5 นาที (เครื่องเป้าออฟไลน์) -> ทิ้ง ไม่บล็อกคิวทั้ง bot
_last_reset_time = {}


def _tg_updates(token, offset, timeout=10):
    """เรียก getUpdates คืน list ของ updates (short polling — กัน bot lock หลาย instance).

    - timeout=0 (short polling): ไม่ถือ connection ค้าง -> หลายโปรแกรมใช้ bot เดียวกัน
      poll พร้อมกันได้ (long polling จะโดน Telegram ตัดด้วย 409 "terminated by other getUpdates")
    - 409: รอสักครู่แล้วลองใหม่ — ถ้ายังติดให้ข้ามรอบนี้ไปก่อน (รอรอบหน้าลองใหม่
      ไม่ไปลบ webhook เพราะอาจกระทบเครื่องอื่นที่ใช้ webhook)
    - 429: flood wait — รอตาม retry_after แล้วข้ามรอบ (ไม่ยิงซ้ำถี่)
    """
    url = "https://api.telegram.org/bot{}/getUpdates?timeout=0".format(token.strip())
    if offset:
        url += "&offset={}".format(int(offset))
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                data = json.loads(response.read().decode("utf-8", "replace"))
            return data.get("result", []) if data.get("ok") else []
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                retry_after = 5
                try:
                    body = exc.read().decode("utf-8", "replace")
                    retry_after = json.loads(body).get("parameters", {}).get("retry_after", 5)
                except Exception:
                    pass
                time.sleep(min(int(retry_after) + 1, 30))
                return []
            if exc.code == 409:
                if attempt <= 1:
                    time.sleep(2)
                    continue
                log.warning("Telegram: getUpdates ติด 409 ซ้ำ 3 รอบ — ข้ามรอบนี้")
                return []
            log.warning("Telegram: getUpdates error HTTP %s", exc.code)
            return []
        except Exception:
            return []
    return []


def _apply_webui_password(cfg, config_path, new_pw, lang="th"):
    """เขียน webui_password (hash) ใหม่ลง config — atomic + ใช้ได้แม้ config ยังตั้งไม่ครบ.

    ตรวจรูปแบบ ini ก่อน (parse ได้) แล้วเขียนตรง (ไม่ใช้ save_text เพราะ validate เต็มจะกีดกัน)
    """
    import configparser
    import io

    text = cfg.raw_text()
    if not text:
        return False, i18n.t(lang, "tg.pw.read_fail")
    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read_string(text)
    except configparser.Error as exc:
        return False, i18n.t(lang, "tg.pw.bad_format").format(exc)
    if not parser.has_section("cloudflare"):
        parser.add_section("cloudflare")
    parser.set(
        "cloudflare", "webui_password", config_mod.password_hash(new_pw, config_path)
    )
    buf = io.StringIO()
    parser.write(buf)
    if not config_mod.atomic_write_text(config_path, buf.getvalue()):
        return False, i18n.t(lang, "tg.pw.write_fail")
    cfg.reload()
    return True, i18n.t(lang, "tg.pw.ok")


# ---- คำสั่ง Telegram (เปิดด้วย telegram_allow_reset = true — เฉพาะ chat_id ที่ตั้งไว้) ----


def _tg_command_name(cfg):
    """ชื่อเครื่องที่ใช้รับคำสั่ง (telegram_command_name หรือ hostname ของระบบ)"""
    name = getattr(cfg, "telegram_command_name", "").strip()
    return name or _hostname()


def _tg_list_text(cfg, lang="th"):
    """รายชื่อ DDNS records + tunnel hostnames ที่ตั้งค่าไว้ สำหรับ /list"""
    lines = []
    records = getattr(cfg, "records", []) or []
    if records:
        lines.append(i18n.t(lang, "tg.list.records"))
        for rec in records:
            fqdn = config_mod.fqdn_name(rec.name or "", rec.zone or "")
            fam = []
            if rec.ipv4:
                fam.append("A")
            if rec.ipv6:
                fam.append("AAAA")
            lines.append(
                "• {} {}{}".format(fqdn or "?", "/".join(fam) or "-", " (proxy)" if rec.proxied else "")
            )
    else:
        lines.append(i18n.t(lang, "tg.list.records_empty"))
    hosts = getattr(cfg, "tunnel_hosts", []) or []
    if hosts:
        lines.append(i18n.t(lang, "tg.list.hosts"))
        for h in hosts:
            lines.append(
                "• {}{} → {} ({})".format(
                    h.get("hostname", "?"),
                    h.get("path", ""),
                    h.get("service", "?"),
                    h.get("protocol", "?"),
                )
            )
    else:
        lines.append(i18n.t(lang, "tg.list.hosts_empty"))
    return "\n".join(lines)


def _tg_status_text(config_path, lang="th"):
    """ข้อความสถานะสำหรับ /status (records + รอบล่าสุด + error + เวอร์ชัน + tunnel + สถิติ API)"""
    from . import cloudflare_api, ddns

    cfg = config_mod.Config(config_path)
    lines = []
    try:
        st = ddns.DDNSEngine(config_path).status()
        records = st.get("records", {})
        if records:
            for key, ip in records.items():
                lines.append("• {}: {}".format(key, ip))
        else:
            lines.append(i18n.t(lang, "tg.status.no_records"))
        lines.append(i18n.t(lang, "tg.status.last_run").format(st.get("last_run") or "—"))
        for key, err in list(st.get("record_errors", {}).items())[:3]:
            lines.append("⚠ {}: {}".format(key, str(err)[:80]))
    except Exception as exc:
        lines.append(i18n.t(lang, "tg.status.err").format(exc))
    # เวอร์ชันโปรแกรม
    try:
        from . import __version__ as ver

        lines.append(i18n.t(lang, "tg.status.program").format(ver))
    except Exception:
        pass
    # tunnel hostnames
    hosts = getattr(cfg, "tunnel_hosts", []) or []
    if hosts:
        lines.append(i18n.t(lang, "tg.status.tunnel").format(", ".join(h.get("hostname", "?") for h in hosts)))
    # สถิติ Cloudflare API (หน่วยความจำ เริ่มใหม่เมื่อ service restart)
    stats = cloudflare_api.api_stats()
    lines.append(
        i18n.t(lang, "tg.status.api").format(
            stats.get("calls", 0), stats.get("errors", 0), stats.get("rate_limited", 0)
        )
    )
    return "\n".join(lines)


# ฟิลด์การแจ้งเตือนที่ /notify ควบคุมได้ (key ใน Telegram ↔ attribute ใน config)
NOTIFY_FIELDS = {
    "start": "notify_start",
    "stop": "notify_stop",
    "ip": "notify_ip_change",
    "error": "notify_error",
    "created": "notify_created",
    "round": "notify_round",
    "daily": "daily_report",
}


def _tg_notify_text(cfg, parts, lang="th"):
    """จัดการ /notify — ดู/เปิด/ปิดการแจ้งเตือน (บันทึก config ผ่านเส้นทางเดียวกับฟอร์มเว็บ).

    รูปแบบ: /notify · /notify all on|off · /notify <event> [on|off]
    """
    def current():
        toggles = " · ".join(
            "{}={}".format(key, i18n.t(lang, "tg.notify.on") if getattr(cfg, field) else i18n.t(lang, "tg.notify.off"))
            for key, field in NOTIFY_FIELDS.items()
        )
        return i18n.t(lang, "tg.notify.current").format(toggles)

    if len(parts) < 2:
        return current()

    target = parts[1].lower()
    value = parts[2].lower() if len(parts) > 2 else ""

    if target == "all":
        if value not in ("on", "off"):
            return i18n.t(lang, "tg.notify.usage")
        for field in NOTIFY_FIELDS.values():
            setattr(cfg, field, value == "on")
    elif target in NOTIFY_FIELDS:
        field = NOTIFY_FIELDS[target]
        if value not in ("on", "off"):
            value = "off" if getattr(cfg, field) else "on"
        setattr(cfg, field, value == "on")
    else:
        return i18n.t(lang, "tg.notify.unknown").format(target, " / ".join(NOTIFY_FIELDS) + " / all")

    # บันทึกผ่านเส้นทางเดียวกับฟอร์มเว็บ (validate + เขียน atomic)
    try:
        from . import webui as webui_mod

        data = webui_mod._cfg_to_dict(cfg)
        text = webui_mod._dict_to_ini(data, cfg.path)
        ok, message = cfg.save_text(text)
    except Exception as exc:
        return i18n.t(lang, "tg.notify.save_fail").format(exc)
    if not ok:
        return i18n.t(lang, "tg.notify.save_fail").format(message)
    return current()


def _tg_ip_text(lang="th"):
    """IP สาธารณะสำหรับ /ip"""
    from . import ip_detect

    parts = []
    for family in (4, 6):
        try:
            ip = ip_detect.get_public_ip(family, timeout=6)
            parts.append("IPv{}: {}".format(family, ip or i18n.t(lang, "tg.ip.not_found")))
        except Exception:
            parts.append("IPv{}: {}".format(family, i18n.t(lang, "tg.ip.error")))
    return i18n.t(lang, "tg.ip.text").format(" · ".join(parts))


def _tg_update_text(lang="th"):
    """เช็คเวอร์ชันใหม่สำหรับ /update"""
    try:
        from . import webui as webui_mod

        data = webui_mod._update_check_data()
        if not data.get("ok"):
            return i18n.t(lang, "tg.update.fail") + (data.get("message") or "")
        if data.get("has_update"):
            return i18n.t(lang, "tg.update.has").format(
                data["latest"], webui_mod.__version__, data.get("url")
            )
        return i18n.t(lang, "tg.update.latest").format(webui_mod.__version__)
    except Exception as exc:
        return i18n.t(lang, "tg.update.fail") + str(exc)


def _tg_run_now(cfg, config_path, reply, lang="th"):
    """รันรอบ DDNS ทันที (thread แยก — กันบล็อก loop) แล้วตอบผลสรุป"""
    from . import ddns

    def work():
        try:
            summary = ddns.DDNSEngine(config_path, dry_run=False).run_once()
            if not summary:
                reply(i18n.t(lang, "tg.run.done"))
                return
            changed = sum(1 for e in summary if e.get("action") in ("updated", "created"))
            problems = sum(1 for e in summary if e.get("action") in ("error", "no-ip", "skip"))
            lines = [i18n.t(lang, "tg.run.summary").format(len(summary), changed, problems)]
            for e in summary[:8]:
                lines.append("• {}: {}".format(e.get("record") or "-", e.get("message") or e.get("action")))
            reply("\n".join(lines))
        except Exception as exc:
            reply(i18n.t(lang, "tg.run.fail").format(exc))

    threading.Thread(target=work, daemon=True).start()
    reply(i18n.t(lang, "tg.run.busy"))


def _tg_tunnel_text(cfg, action, lang="th"):
    """สถานะ/ควบคุม tunnel สำหรับ /tunnel [start|stop]"""
    try:
        from . import tunnel as tunnel_mod

        mgr = tunnel_mod.TunnelManager(config_path=cfg.path)
        if action == "start":
            return i18n.t(lang, "tg.tunnel.start").format(mgr.start(cfg))
        if action == "stop":
            return i18n.t(lang, "tg.tunnel.stop").format(mgr.stop())
        st = mgr.status(cfg)
        return i18n.t(lang, "tg.tunnel.status").format(
            i18n.t(lang, "tg.tunnel.on") if st.get("enabled") else i18n.t(lang, "tg.tunnel.off"),
            st.get("version") or i18n.t(lang, "tg.tunnel.not_installed"),
            i18n.t(lang, "tg.tunnel.yes") if st.get("running") else i18n.t(lang, "tg.tunnel.no"),
        )
    except Exception as exc:
        return i18n.t(lang, "tg.tunnel.err").format(exc)


def _tg_service_action(action, lang="th"):
    """ควบคุม Windows Service สำหรับ /restart /start /stop"""
    try:
        from . import service as service_mod
        from .webui import _in_service

        if _in_service():
            if action == "stop":
                return i18n.t(lang, "tg.svc.in_service_stop")
            if action == "start":
                return i18n.t(lang, "tg.svc.in_service_start")
        if action == "restart":
            return service_mod.restart_service()
        if action == "stop":
            return service_mod.stop_service()
        return service_mod.start_service()
    except Exception as exc:
        return i18n.t(lang, "tg.svc.fail").format(exc)


def _tg_log_tail(cfg, limit=30, lang="th"):
    """log 30 บรรทัดสุดท้ายสำหรับ /log"""
    import os

    log_path = os.path.join(cfg.log_dir, "cloudflare-ddns.log")
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
            tail = "".join(handle.readlines()[-limit:])
        if len(tail) > 3500:
            tail = "…" + tail[-3500:]
        return tail or i18n.t(lang, "tg.log.empty")
    except OSError as exc:
        return i18n.t(lang, "tg.log.read_fail").format(exc)


def check_telegram_commands(cfg, config_path=""):
    """ฟังคำสั่งจาก Telegram — เฉพาะ chat_id ที่ตั้งไว้เท่านั้น (log ทุกคำสั่ง).

    - เปิดด้วย telegram_allow_reset = true ใน config (ฟอร์ม: "ควบคุม/กู้รหัสผ่านผ่าน Telegram")
    - คำสั่ง: /status /ip /run /update /tunnel /log /restart /start /stop /help
    - ใช้ bot กลางร่วมหลายเครื่อง (รันหลายตัวพร้อมกัน): ต่อท้าย @ชื่อเครื่อง เช่น /status @เครื่องA —
      เฉพาะเครื่องที่ชื่อตรง (telegram_command_name หรือ hostname) ตอบ ที่เหลือข้ามโดย**ไม่ confirm offset**
      (คำสั่งยังรอคิวอยู่ ให้เครื่องเป้าได้รับเอง — กัน "ขโมยคำสั่ง" จาก bot ตัวเดียวกัน)
      คำสั่งของเครื่องอื่นที่ค้างเกิน 10 นาที (เครื่องเป้าออฟไลน์) จะถูกทิ้ง ไม่บล็อกคิวทั้ง bot
    - ไม่ระบุชื่อ = ส่งถึงทุกเครื่อง (ทุกตัวตอบ)
    - กู้รหัสผ่าน: 'reset password' -> ตอบ 'yes' -> สุ่มรหัสใหม่ 12 ตัว ส่งกลับ (กัน 1 ครั้ง/10 นาที)
    - ข้อความจาก chat อื่นถูกละเลย (ไม่ตอบ ไม่ log แต่ confirm ทิ้ง)
    """
    import secrets

    if not getattr(cfg, "telegram_allow_reset", False):
        return
    if not cfg.telegram_bot_token or not cfg.telegram_chat_id:
        return
    token = cfg.telegram_bot_token.strip()
    display_name = _tg_command_name(cfg)
    my_name = display_name.lower()
    cur = _updates_offset.get(token, 0)
    updates = _tg_updates(token, cur)
    if not updates:
        return

    notify = TelegramNotifier.from_config(cfg)

    lang = getattr(notify, "lang", "th") or "th"

    def reply(text):
        # ขึ้นต้นด้วย [ชื่อเครื่อง] — รู้ว่าคำตอบมาจากเครื่องไหน (ใช้ bot กลางหลายเครื่อง)
        ok, error = notify.send_raw("[{}] {}".format(display_name, text))
        if not ok:
            log.warning("telegram command: ส่งข้อความตอบไม่ได้: %s", error)

    handled = _handled_updates.setdefault(token, set())
    confirm_upto = -1  # update_id สุดท้ายที่ confirm ได้ (prefix ต่อเนื่อง ไม่มีคำสั่งเครื่องอื่นคั่น)
    blocked = False  # เจอคำสั่งของเครื่องอื่น (ยังไม่แก่) -> ต่อไปนี้หยุด confirm แต่ยังตอบคำสั่งของเรา

    def is_mine(text_lower):
        """ชื่อเครื่องจากคำสั่ง (/cmd @ชื่อ) — ว่าง = ส่งถึงทุกเครื่อง (เป็นของเรา)"""
        parts = text_lower.split()
        if len(parts) >= 2 and parts[1].startswith("@"):
            target = parts[1][1:].strip().lower()
            if target != my_name:
                log.info("Telegram: ข้ามคำสั่ง (ชื่อเครื่องไม่ตรง): เป้า=%s เครื่องนี้=%s", target, my_name)
                return False
        return True

    for update in updates:
        msg = update.get("message") or {}
        chat = msg.get("chat") or {}
        uid = int(update.get("update_id", 0) or 0)
        if uid < cur:
            handled.discard(uid)
            continue
        if str(chat.get("id", "")) != str(cfg.telegram_chat_id):
            confirm_upto = max(confirm_upto, uid)  # chat อื่น — รับทิ้ง (confirm) ไม่ตอบ ไม่ log
            continue
        text = str(msg.get("text", "")).strip()
        if not text:
            confirm_upto = max(confirm_upto, uid)
            continue
        lower = text.lower()

        if blocked:
            # มีคำสั่งเครื่องอื่นคั่นอยู่ก่อนหน้า — ตอบคำสั่งของเราได้ แต่ยังไม่ confirm
            if is_mine(lower) and uid not in handled:
                handled.add(uid)
                _dispatch_tg_command(lower, text, uid, token, cfg, config_path, reply)
            continue

        if not is_mine(lower):
            # คำสั่งของเครื่องอื่น — ต้องไม่ confirm (ไม่งั้นเครื่องเป้าไม่เห็น)
            age = time.time() - int(msg.get("date", 0) or 0)
            if age > _tg_foreign_stale:
                log.info("Telegram: ทิ้งคำสั่งค้างของเครื่องอื่น (เกิน %d วิ ไม่ตอบ): %r", _tg_foreign_stale, text[:60])
                confirm_upto = max(confirm_upto, uid)
            else:
                blocked = True
            continue

        # คำสั่งของเรา
        if uid in handled:
            # เคยจัดการแล้ว (โดนบล็อกโดยคำสั่งเครื่องอื่นรอบก่อน) — เครื่องอื่นรับไปแล้ว ไม่ตอบซ้ำ แต่ confirm ได้
            confirm_upto = max(confirm_upto, uid)
            continue
        handled.add(uid)
        confirm_upto = max(confirm_upto, uid)
        _dispatch_tg_command(lower, text, uid, token, cfg, config_path, reply)

    if confirm_upto >= 0 and confirm_upto + 1 > cur:
        _updates_offset[token] = confirm_upto + 1
        # ล้าง update_id ที่ confirm ไปแล้วออกจาก handled (กัน set โต)
        handled &= {u for u in handled if u >= _updates_offset[token]}


def _dispatch_tg_command(lower, text, uid, token, cfg, config_path, reply, confirmed=False):
    """จัดการคำสั่ง Telegram หนึ่งคำสั่ง (แยกฟังก์ชัน — ใช้จาก check_telegram_commands)

    confirmed=True ใช้เฉพาะตอน re-dispatch หลังยืนยันคำสั่งอันตราย — ข้าม gate ยืนยันซ้ำ
    """
    import secrets

    lang = getattr(cfg, "language", "th") or "th"

    log.info("Telegram: คำสั่งจาก chat_id=%s: %r", cfg.telegram_chat_id, text[:60])

    # ยืนยันคำสั่งอันตราย (/run /restart /tunnel stop) — พิมพ์ yes ภายใน 2 นาที
    if not confirmed and _danger_state["command"]:
        pending = _danger_state["command"]
        ptext = _danger_state["text"]
        expired = time.time() > _danger_state["expires"]
        if not expired:
            if lower == "yes":
                log.warning("Telegram: ยืนยันคำสั่งอันตราย: %s", pending)
                _danger_state["command"] = ""
                _reset_state["awaiting_confirm"] = False
                _dispatch_tg_command(
                    pending.lower(), ptext, uid, token, cfg, config_path, reply, confirmed=True
                )
                return
            if lower == "no":
                _danger_state["command"] = ""
                reply(i18n.t(lang, "tg.danger.cancel").format(pending))
                return
            # ข้อความอื่นที่ยังไม่ยืนยัน — คืนสถานะรอยืนยันให้
            reply(i18n.t(lang, "tg.danger.pending").format(pending))
            return
        # หมดเวลายืนยันแล้ว — ล้าง state แล้วประมวลผลคำสั่งใหม่ที่พิมพ์มา (ไม่กลืน)
        _danger_state["command"] = ""
        log.info("Telegram: ยกเลิกคำสั่งอันตรายที่หมดเวลา: %s", pending)
        if lower in ("yes", "no"):
            reply(i18n.t(lang, "tg.danger.expired").format(pending))
            return

    # กู้รหัสผ่านหน้าเว็บ (2 ขั้น)
    if lower == "reset password":
        _reset_state["awaiting_confirm"] = True
        _reset_state["last_ask"] = time.time()
        reply(i18n.t(lang, "tg.reset.ask"))
        return
    if lower == "yes" and _reset_state["awaiting_confirm"]:
        _reset_state["awaiting_confirm"] = False
        if time.time() - _reset_state["last_ask"] > 600:
            log.warning("Telegram: คำสั่ง reset หมดเวลา (เกิน 10 นาที)")
            reply(i18n.t(lang, "tg.reset.expired"))
            return
        if time.time() - _last_reset_time.get(token, 0) < _reset_cooldown:
            log.warning("Telegram: ข้าม reset (เพิ่งทำไปไม่นาน)")
            reply(i18n.t(lang, "tg.reset.cooldown"))
            return
        _last_reset_time[token] = time.time()
        new_pw = secrets.token_urlsafe(9)  # 12 ตัวอักษร
        ok, message = _apply_webui_password(cfg, config_path, new_pw, lang)
        if ok:
            log.warning("Telegram: reset รหัสผ่านหน้าเว็บสำเร็จ (ส่งรหัสใหม่ทาง Telegram)")
            reply(i18n.t(lang, "tg.reset.done").format(new_pw))
        else:
            log.warning("Telegram: reset รหัสผ่านไม่สำเร็จ: %s", message)
            reply(i18n.t(lang, "tg.reset.fail").format(message))
        return

    # คำสั่งควบคุม (ต้องมาจาก chat_id ที่ตั้งไว้เท่านั้น — กรองไว้แล้วด้านบน)
    cmd = lower.split()[0]

    # คำสั่งอันตราย -> ขอให้ยืนยันก่อน (กันสั่งพลาด / กดผิด)
    danger_cmd = ""
    if not confirmed:
        if cmd == "/run":
            danger_cmd = "/run"
        elif cmd == "/restart":
            danger_cmd = "/restart"
        elif cmd == "/tunnel" and "stop" in lower.split()[1:2]:
            danger_cmd = "/tunnel stop"
    if danger_cmd:
        _danger_state["command"] = danger_cmd
        _danger_state["text"] = text
        _danger_state["expires"] = time.time() + _danger_confirm_seconds
        # ตั้งคำสั่งอันตรายใหม่ = ยกเลิก reset รหัสที่ค้างอยู่ (กัน yes ซ้ำไป reset โดยไม่ตั้งใจ)
        _reset_state["awaiting_confirm"] = False
        reply(i18n.t(lang, "tg.danger.ask").format(danger_cmd))
        return

    if cmd == "/help":
        reply(i18n.t(lang, "tg.help"))
    elif cmd == "/status":
        reply(_tg_status_text(config_path, lang))
    elif cmd == "/list":
        reply(_tg_list_text(cfg, lang))
    elif cmd == "/ip":
        reply(_tg_ip_text(lang))
    elif cmd == "/run":
        _tg_run_now(cfg, config_path, reply, lang)
    elif cmd == "/update":
        reply(_tg_update_text(lang))
    elif cmd == "/tunnel":
        parts = lower.split()
        action = parts[1] if len(parts) > 1 else ""
        reply(_tg_tunnel_text(cfg, action, lang))
    elif cmd == "/notify":
        reply(_tg_notify_text(cfg, lower.split(), lang))
    elif cmd in ("/restart", "/start", "/stop"):
        reply(_tg_service_action(cmd[1:], lang))
    elif cmd == "/log":
        reply(_tg_log_tail(cfg, lang=lang))
    else:
        log.info("Telegram: คำสั่งไม่รู้จัก: %r", text[:60])


def _tg_api(bot_token, method, timeout=10):
    """เรียก Telegram Bot API ตรง ๆ คืน dict ที่ parse แล้ว"""
    url = "https://api.telegram.org/bot{}/{}".format(bot_token.strip(), method)
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", "replace"))


def get_chat_id(bot_token, timeout=10, lang="th"):
    """หา chat_id ล่าสุดผ่าน getUpdates (ผู้ใช้ต้องเคยส่ง /start หรือข้อความให้ bot).

    - ถ้าเจอ error 409 (มี webhook ค้าง) จะลบ webhook ให้อัตโนมัติแล้วลองใหม่
    คืน (chat_id_str หรือ "", error_message)
    """
    token = bot_token.strip()
    if not token:
        return "", i18n.t(lang, "tg.chatid.no_token")

    def fetch():
        return _tg_api(token, "getUpdates", timeout=timeout)

    try:
        data = fetch()
    except urllib.error.HTTPError as exc:
        if exc.code == 409:
            # webhook ถูกตั้งค้างอยู่ -> ลบให้แล้วลองใหม่
            log.warning("getUpdates ติด 409 (webhook ค้าง) — กำลังลบ webhook แล้วลองใหม่")
            try:
                _tg_api(token, "deleteWebhook", timeout=timeout)
                data = fetch()
            except urllib.error.HTTPError as exc2:
                return "", i18n.t(lang, "tg.chatid.webhook_err", code=exc2.code, exc=exc2)
            except Exception as exc2:
                return "", i18n.t(lang, "tg.chatid.webhook_del_fail").format(exc2)
        else:
            return "", i18n.t(lang, "tg.chatid.updates_fail").format(exc)
    except Exception as exc:
        return "", i18n.t(lang, "tg.chatid.updates_fail").format(exc)
    if not data.get("ok"):
        return "", data.get("description") or "getUpdates failed"
    updates = data.get("result", [])
    for update in reversed(updates):
        message = update.get("message") or update.get("channel_post") or update.get("my_chat_member", {})
        chat = (message or {}).get("chat")
        if chat and chat.get("id") is not None:
            return str(chat["id"]), ""
    return "", i18n.t(lang, "tg.chatid.not_found")


# ---- ข้อความแจ้งเตือน ----


def short_error(text, limit=110, lang="th"):
    """ย่อข้อความ error ให้อ่านง่าย (ตัด JSON/รายละเอียดยาว ๆ ทิ้ง)."""
    text = str(text or "").strip()
    if not text:
        return i18n.t(lang, "tg.err_unknown")
    # ตัด JSON (เช่น HTTP 400: {"success":false,...}) ทิ้ง เหลือเฉพาะข้อความหลัก
    if "{" in text:
        text = text.split("{", 1)[0].strip()
    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return text


_hostname_cache = ""


def _hostname():
    """ชื่อเครื่อง (แคช) — ระบุที่มาของข้อความในทุกการแจ้งเตือน (ใช้ bot กลางร่วมหลายเครื่อง)"""
    global _hostname_cache
    if not _hostname_cache:
        import socket as _socket

        try:
            _hostname_cache = _socket.gethostname() or "?"
        except Exception:
            _hostname_cache = "?"
    return _hostname_cache


def _now_ts():
    """เวลาปัจจุบันในรูปแบบ [dd/MM HH:MM] กำกับท้ายข้อความ"""
    return datetime.now().strftime("[%d/%m %H:%M]")


def build_message(event, detail=None, name=None, lang="th"):
    """สร้างข้อความแจ้งเตือนรูปแบบอ่านง่าย (ตามภาษา + เวลาเกิด + ชื่อเครื่อง)."""
    ts = _now_ts()
    host = name or _hostname()
    if event == EVENT_START:
        return i18n.t(lang, "tg.event.start", ts=ts, host=host) + "\n" + (detail or "")
    if event == EVENT_STOP:
        return i18n.t(lang, "tg.event.stop", ts=ts, host=host) + (f"\n{detail}" if detail else "")
    if event == EVENT_IP_CHANGE:
        return i18n.t(lang, "tg.event.ip_change", ts=ts, host=host) + "\n" + (detail or "")
    if event == EVENT_CREATED:
        return i18n.t(lang, "tg.event.created", ts=ts, host=host) + "\n" + (detail or "")
    if event == EVENT_ERROR:
        return i18n.t(lang, "tg.event.error", ts=ts, host=host) + "\n" + short_error(detail, lang=lang)
    if event == EVENT_ROUND:
        return i18n.t(lang, "tg.event.round", ts=ts, host=host) + "\n" + (detail or "")
    return detail or ""
