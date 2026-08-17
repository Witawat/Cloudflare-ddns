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
    def __init__(self, bot_token="", chat_id="", events=None, config_path=None):
        self.bot_token = (bot_token or "").strip()
        self.chat_id = str(chat_id or "").strip()
        self.events = events or {}
        self._last_dedupe_key = ""
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
        )

    def event_enabled(self, event):
        return self.events.get(event, True)

    # ---- ส่งจริง ----

    def send_raw(self, text):
        """ส่งข้อความตรง ๆ คืน (ok, error_message) ไม่ยุ่งกับ queue."""
        if not self.enabled:
            return False, "ยังไม่ได้ตั้งค่า telegram (bot_token/chat_id)"
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
            return False, data.get("description", "sendMessage คืน ok=false")
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
        message = build_message(event, text)
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
_updates_offset = {}  # token -> offset (ยืนยันแล้ว = update_id < offset) — กันรับซ้ำ/กันขโมยคำสั่งของเครื่องอื่น
_handled_updates = {}  # token -> set(update_id ที่จัดการแล้ว) — กันตอบซ้ำตอนถูกบล็อกโดยคำสั่งเครื่องอื่น
_tg_foreign_stale = 600  # คำสั่งของเครื่องอื่นที่ค้างเกิน 10 นาที (เครื่องเป้าออฟไลน์) -> ทิ้ง ไม่บล็อกคิวทั้ง bot
_last_reset_time = {}


def _tg_updates(token, offset, timeout=10):
    """เรียก getUpdates คืน list ของ updates (short polling — กัน bot lock หลาย instance).

    - timeout=0 (short polling): ไม่ถือ connection ค้าง -> หลายโปรแกรมใช้ bot เดียวกัน
      poll พร้อมกันได้ (long polling จะโดน Telegram ตัดด้วย 409 "terminated by other getUpdates")
    - 409: ลองใหม่ก่อน (instance อื่น poll พร้อมกัน) ถ้ายังติด -> ลบ webhook (ของอื่นค้าง) แล้วลองอีกรอบ
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
                if attempt == 0:
                    time.sleep(2)  # instance อื่นกำลัง poll พร้อมกัน (short polling เจอน้อย) — ลองใหม่
                    continue
                if attempt == 1:
                    # webhook ค้างจากโปรแกรมอื่น -> ลบให้แล้วลองอีกรอบ
                    try:
                        _tg_api(token, "deleteWebhook", timeout=timeout)
                    except Exception:
                        pass
                    time.sleep(2)
                    continue
                log.warning("Telegram: getUpdates ติด 409 ซ้ำ 3 รอบ — ข้ามรอบนี้")
                return []
            log.warning("Telegram: getUpdates error HTTP %s", exc.code)
            return []
        except Exception:
            return []
    return []


def _apply_webui_password(cfg, config_path, new_pw):
    """เขียน webui_password (hash) ใหม่ลง config — atomic + ใช้ได้แม้ config ยังตั้งไม่ครบ.

    ตรวจรูปแบบ ini ก่อน (parse ได้) แล้วเขียนตรง (ไม่ใช้ save_text เพราะ validate เต็มจะกีดกัน)
    """
    import configparser
    import io

    text = cfg.raw_text()
    if not text:
        return False, "อ่าน config ไม่ได้"
    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read_string(text)
    except configparser.Error as exc:
        return False, "config ผิดรูปแบบ: {}".format(exc)
    if not parser.has_section("cloudflare"):
        parser.add_section("cloudflare")
    parser.set(
        "cloudflare", "webui_password", config_mod.password_hash(new_pw, config_path)
    )
    buf = io.StringIO()
    parser.write(buf)
    if not config_mod.atomic_write_text(config_path, buf.getvalue()):
        return False, "เขียนไฟล์ไม่ได้"
    cfg.reload()
    return True, "บันทึกสำเร็จ"


# ---- คำสั่ง Telegram (เปิดด้วย telegram_allow_reset = true — เฉพาะ chat_id ที่ตั้งไว้) ----

TG_HELP_TEXT = (
    "รายการคำสั่ง (พิมพ์ในแชทนี้):\n"
    "/status — สถานะ DDNS (IP/record/รอบล่าสุด)\n"
    "/list — รายชื่อ DDNS + tunnel ที่ตั้งค่าไว้\n"
    "/ip — IP สาธารณะปัจจุบัน\n"
    "/run — รันรอบ DDNS ทันที\n"
    "/update — เช็คเวอร์ชันใหม่\n"
    "/tunnel [start|stop] — สถานะ/ควบคุม tunnel\n"
    "/log — log 30 บรรทัดสุดท้าย\n"
    "/restart /start /stop — ควบคุม Windows Service\n"
    "reset password → yes — กู้รหัสผ่านหน้าเว็บ\n"
    "ใช้ bot กลางหลายเครื่อง? ต่อท้าย @ชื่อเครื่อง "
    "(เช่น /status @เครื่องA) — เฉพาะเครื่องที่ชื่อตรงตอบ\n"
    "ทุกคำตอบขึ้นต้นด้วย [ชื่อเครื่อง] — รู้ว่ามาจากเครื่องไหน"
)


def _tg_command_name(cfg):
    """ชื่อเครื่องที่ใช้รับคำสั่ง (telegram_command_name หรือ hostname ของระบบ)"""
    name = getattr(cfg, "telegram_command_name", "").strip()
    return name or _hostname()


def _tg_list_text(cfg):
    """รายชื่อ DDNS records + tunnel hostnames ที่ตั้งค่าไว้ สำหรับ /list"""
    lines = []
    records = getattr(cfg, "records", []) or []
    if records:
        lines.append("📋 DDNS records:")
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
        lines.append("📋 DDNS records: (ไม่มี)")
    hosts = getattr(cfg, "tunnel_hosts", []) or []
    if hosts:
        lines.append("🛰 Tunnel hostnames:")
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
        lines.append("🛰 Tunnel hostnames: (ไม่มี)")
    return "\n".join(lines)


def _tg_status_text(config_path):
    """ข้อความสถานะสำหรับ /status"""
    from . import ddns

    lines = []
    try:
        st = ddns.DDNSEngine(config_path).status()
        records = st.get("records", {})
        if records:
            for key, ip in records.items():
                lines.append("• {}: {}".format(key, ip))
        else:
            lines.append("• ยังไม่มีข้อมูล record (รอรอบแรก)")
        lines.append("รอบล่าสุด: {}".format(st.get("last_run") or "—"))
        for key, err in list(st.get("record_errors", {}).items())[:3]:
            lines.append("⚠ {}: {}".format(key, str(err)[:80]))
    except Exception as exc:
        lines.append("อ่านสถานะไม่ได้: {}".format(exc))
    return "\n".join(lines)


def _tg_ip_text():
    """IP สาธารณะสำหรับ /ip"""
    from . import ip_detect

    parts = []
    for family in (4, 6):
        try:
            ip = ip_detect.get_public_ip(family, timeout=6)
            parts.append("IPv{}: {}".format(family, ip or "หาไม่ได้"))
        except Exception:
            parts.append("IPv{}: error".format(family))
    return "IP สาธารณะ: " + " · ".join(parts)


def _tg_update_text():
    """เช็คเวอร์ชันใหม่สำหรับ /update"""
    try:
        from . import webui as webui_mod

        data = webui_mod._update_check_data()
        if not data.get("ok"):
            return "เช็คเวอร์ชันไม่ได้: " + (data.get("message") or "ลองใหม่ภายหลัง")
        if data.get("has_update"):
            return "มีเวอร์ชันใหม่ v{} (ปัจจุบัน v{}) — {}".format(
                data["latest"], webui_mod.__version__, data.get("url")
            )
        return "ใช้เวอร์ชันล่าสุดแล้ว (v{})".format(webui_mod.__version__)
    except Exception as exc:
        return "เช็คเวอร์ชันไม่ได้: {}".format(exc)


def _tg_run_now(cfg, config_path, reply):
    """รันรอบ DDNS ทันที (thread แยก — กันบล็อก loop) แล้วตอบผลสรุป"""
    from . import ddns

    def work():
        try:
            summary = ddns.DDNSEngine(config_path, dry_run=False).run_once()
            if not summary:
                reply("ตรวจเสร็จ: ทุก record ตรง ไม่มีการเปลี่ยน")
                return
            changed = sum(1 for e in summary if e.get("action") in ("updated", "created"))
            problems = sum(1 for e in summary if e.get("action") in ("error", "no-ip", "skip"))
            lines = ["ตรวจ {} รายการ · เปลี่ยน {} · มีปัญหา {}".format(len(summary), changed, problems)]
            for e in summary[:8]:
                lines.append("• {}: {}".format(e.get("record") or "-", e.get("message") or e.get("action")))
            reply("\n".join(lines))
        except Exception as exc:
            reply("รันรอบไม่ได้: {}".format(exc))

    threading.Thread(target=work, daemon=True).start()
    reply("กำลังรันรอบ DDNS — ผลจะตามมาในไม่กี่วิ")


def _tg_tunnel_text(cfg, action):
    """สถานะ/ควบคุม tunnel สำหรับ /tunnel [start|stop]"""
    try:
        from . import tunnel as tunnel_mod

        mgr = tunnel_mod.TunnelManager(config_path=cfg.path)
        if action == "start":
            return "เริ่ม tunnel: " + mgr.start(cfg)
        if action == "stop":
            return "หยุด tunnel: " + mgr.stop()
        st = mgr.status(cfg)
        return "Tunnel: {} · cloudflared {} · รันอยู่: {}".format(
            "เปิด" if st.get("enabled") else "ปิด",
            st.get("version") or "ยังไม่ติดตั้ง",
            "ใช่" if st.get("running") else "ไม่",
        )
    except Exception as exc:
        return "tunnel: {}".format(exc)


def _tg_service_action(action):
    """ควบคุม Windows Service สำหรับ /restart /start /stop"""
    try:
        from . import service as service_mod
        from .webui import _in_service

        if _in_service():
            if action == "stop":
                return "รันใน service เอง — หยุดตัวเองไม่ได้ (ใช้ /restart ได้)"
            if action == "start":
                return "service กำลังรันอยู่แล้ว"
        if action == "restart":
            return service_mod.restart_service()
        if action == "stop":
            return service_mod.stop_service()
        return service_mod.start_service()
    except Exception as exc:
        return "ทำไม่ได้: {}".format(exc)


def _tg_log_tail(cfg, limit=30):
    """log 30 บรรทัดสุดท้ายสำหรับ /log"""
    import os

    log_path = os.path.join(cfg.log_dir, "cloudflare-ddns.log")
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
            tail = "".join(handle.readlines()[-limit:])
        if len(tail) > 3500:
            tail = "…" + tail[-3500:]
        return tail or "(log ว่าง)"
    except OSError as exc:
        return "อ่าน log ไม่ได้: {}".format(exc)


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


def _dispatch_tg_command(lower, text, uid, token, cfg, config_path, reply):
    """จัดการคำสั่ง Telegram หนึ่งคำสั่ง (แยกฟังก์ชัน — ใช้จาก check_telegram_commands)"""
    import secrets

    log.info("Telegram: คำสั่งจาก chat_id=%s: %r", cfg.telegram_chat_id, text[:60])

    # กู้รหัสผ่านหน้าเว็บ (2 ขั้น)
    if lower == "reset password":
        _reset_state["awaiting_confirm"] = True
        _reset_state["last_ask"] = time.time()
        reply("รหัสผ่านหน้าเว็บจะถูกสุ่มใหม่ — พิมพ์ 'yes' เพื่อยืนยัน (ภายใน 10 นาที)")
        return
    if lower == "yes" and _reset_state["awaiting_confirm"]:
        _reset_state["awaiting_confirm"] = False
        if time.time() - _reset_state["last_ask"] > 600:
            log.warning("Telegram: คำสั่ง reset หมดเวลา (เกิน 10 นาที)")
            reply("คำสั่ง reset หมดเวลาแล้ว — พิมพ์ 'reset password' ใหม่เพื่อเริ่ม")
            return
        if time.time() - _last_reset_time.get(token, 0) < _reset_cooldown:
            log.warning("Telegram: ข้าม reset (เพิ่งทำไปไม่นาน)")
            reply("ข้าม: เพิ่ง reset ไปเมื่อไม่นาน — รอ 10 นาทีแล้วลองใหม่")
            return
        _last_reset_time[token] = time.time()
        new_pw = secrets.token_urlsafe(9)  # 12 ตัวอักษร
        ok, message = _apply_webui_password(cfg, config_path, new_pw)
        if ok:
            log.warning("Telegram: reset รหัสผ่านหน้าเว็บสำเร็จ (ส่งรหัสใหม่ทาง Telegram)")
            reply(
                "รหัสผ่านหน้าเว็บใหม่: {}\n"
                "เข้าหน้าเว็บแล้วเปลี่ยนเป็นรหัสที่จำง่ายได้ในฟอร์มตั้งค่า".format(new_pw)
            )
        else:
            log.warning("Telegram: reset รหัสผ่านไม่สำเร็จ: %s", message)
            reply("reset ไม่สำเร็จ: {}".format(message))
        return

    # คำสั่งควบคุม (ต้องมาจาก chat_id ที่ตั้งไว้เท่านั้น — กรองไว้แล้วด้านบน)
    cmd = lower.split()[0]
    if cmd == "/help":
        reply(TG_HELP_TEXT)
    elif cmd == "/status":
        reply(_tg_status_text(config_path))
    elif cmd == "/list":
        reply(_tg_list_text(cfg))
    elif cmd == "/ip":
        reply(_tg_ip_text())
    elif cmd == "/run":
        _tg_run_now(cfg, config_path, reply)
    elif cmd == "/update":
        reply(_tg_update_text())
    elif cmd == "/tunnel":
        parts = lower.split()
        action = parts[1] if len(parts) > 1 else ""
        reply(_tg_tunnel_text(cfg, action))
    elif cmd in ("/restart", "/start", "/stop"):
        reply(_tg_service_action(cmd[1:]))
    elif cmd == "/log":
        reply(_tg_log_tail(cfg))
    else:
        log.info("Telegram: คำสั่งไม่รู้จัก: %r", text[:60])


def _tg_api(bot_token, method, timeout=10):
    """เรียก Telegram Bot API ตรง ๆ คืน dict ที่ parse แล้ว"""
    url = "https://api.telegram.org/bot{}/{}".format(bot_token.strip(), method)
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", "replace"))


def get_chat_id(bot_token, timeout=10):
    """หา chat_id ล่าสุดผ่าน getUpdates (ผู้ใช้ต้องเคยส่ง /start หรือข้อความให้ bot).

    - ถ้าเจอ error 409 (มี webhook ค้าง) จะลบ webhook ให้อัตโนมัติแล้วลองใหม่
    คืน (chat_id_str หรือ "", error_message)
    """
    token = bot_token.strip()
    if not token:
        return "", "ไม่พบ bot token"

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
                return "", (
                    f"ลบ webhook แล้วก็ยังติด error {exc2.code}: {exc2} "
                    "— ถ้า bot นี้กำลังรันกับโปรแกรมอื่นอยู่ ให้ปิดตัวนั้นก่อนแล้วลองใหม่"
                )
            except Exception as exc2:
                return "", f"ลบ webhook ไม่ได้: {exc2}"
        else:
            return "", f"เรียก getUpdates ไม่ได้: {exc}"
    except Exception as exc:
        return "", f"เรียก getUpdates ไม่ได้: {exc}"
    if not data.get("ok"):
        return "", data.get("description", "getUpdates คืน ok=false")
    updates = data.get("result", [])
    for update in reversed(updates):
        message = update.get("message") or update.get("channel_post") or update.get("my_chat_member", {})
        chat = (message or {}).get("chat")
        if chat and chat.get("id") is not None:
            return str(chat["id"]), ""
    return "", "ยังไม่มีข้อความจาก bot — เปิดแชทกับ bot แล้วกด /start ก่อนลองใหม่"


# ---- ข้อความแจ้งเตือน ----


def short_error(text, limit=110):
    """ย่อข้อความ error ให้อ่านง่าย (ตัด JSON/รายละเอียดยาว ๆ ทิ้ง)."""
    text = str(text or "").strip()
    if not text:
        return "ไม่ทราบสาเหตุ"
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


def build_message(event, detail=None):
    """สร้างข้อความแจ้งเตือนรูปแบบอ่านง่าย (ภาษาไทย สั้น กระชับ + เวลาเกิด + ชื่อเครื่อง)."""
    ts = _now_ts()
    host = _hostname()
    if event == EVENT_START:
        return f"🟢 DDNS เริ่มทำงาน {ts} · {host}\n" + (detail or "")
    if event == EVENT_STOP:
        return f"🔴 DDNS หยุดทำงาน {ts} · {host}" + (f"\n{detail}" if detail else "")
    if event == EVENT_IP_CHANGE:
        return f"🔄 IP เปลี่ยน {ts} · {host}\n" + (detail or "")
    if event == EVENT_CREATED:
        return f"🆕 สร้าง record ใหม่ {ts} · {host}\n" + (detail or "")
    if event == EVENT_ERROR:
        return f"⚠️ มีปัญหา {ts} · {host}\n" + short_error(detail)
    if event == EVENT_ROUND:
        return f"✅ ตรวจรอบเสร็จ {ts} · {host}\n" + (detail or "")
    return detail or ""
