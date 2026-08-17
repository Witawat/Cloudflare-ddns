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
_updates_offset = {}  # token -> offset (กันรับข้อความเดิมซ้ำ)
_last_reset_time = {}


def _tg_updates(token, offset, timeout=10):
    """เรียก getUpdates คืน list ของ updates (จัดการ webhook 409 อัตโนมัติ)"""
    url = "https://api.telegram.org/bot{}/getUpdates?timeout=0".format(token.strip())
    if offset:
        url += "&offset={}".format(int(offset))
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8", "replace"))
        return data.get("result", []) if data.get("ok") else []
    except urllib.error.HTTPError as exc:
        if exc.code == 409:
            try:
                _tg_api(token, "deleteWebhook", timeout=timeout)
            except Exception:
                pass
            return _tg_updates(token, offset, timeout)
        return []
    except Exception:
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


def check_telegram_reset(cfg, config_path=""):
    """ฟังคำสั่งกู้รหัสผ่านหน้าเว็บจาก Telegram — เฉพาะ chat_id ที่ตั้งไว้เท่านั้น.

    - เปิดด้วย telegram_allow_reset = true ใน config
    - พิมพ์ 'reset password' -> ตอบ 'yes' -> สุ่มรหัสใหม่ 12 ตัว ส่งกลับทาง Telegram
    - กันสแปม: reset ได้ 1 ครั้ง/10 นาที + log ทุกครั้ง + ข้อความจาก chat อื่นถูกละเลย
    """
    import secrets

    if not getattr(cfg, "telegram_allow_reset", False):
        return
    if not cfg.telegram_bot_token or not cfg.telegram_chat_id:
        return
    token = cfg.telegram_bot_token.strip()
    offset = _updates_offset.get(token, 0)
    updates = _tg_updates(token, offset)
    if not updates:
        return
    _updates_offset[token] = max(int(u.get("update_id", 0) or 0) + 1 for u in updates)

    notify = TelegramNotifier.from_config(cfg)

    def reply(text):
        ok, error = notify.send_raw(text)
        if not ok:
            log.warning("telegram reset: ส่งข้อความตอบไม่ได้: %s", error)

    for update in updates:
        msg = update.get("message") or {}
        chat = msg.get("chat") or {}
        if str(chat.get("id", "")) != str(cfg.telegram_chat_id):
            continue  # ข้อความจาก chat อื่น — ไม่ตอบ ไม่ log
        text = str(msg.get("text", "")).strip()
        if text.lower() == "reset password":
            _reset_state["awaiting_confirm"] = True
            _reset_state["last_ask"] = time.time()
            log.warning("Telegram: รับคำสั่ง 'reset password' — กำลังรอยืนยัน")
            reply("รหัสผ่านหน้าเว็บจะถูกสุ่มใหม่ — พิมพ์ 'yes' เพื่อยืนยัน (ภายใน 10 นาที)")
        elif text.lower() == "yes" and _reset_state["awaiting_confirm"]:
            _reset_state["awaiting_confirm"] = False
            if time.time() - _reset_state["last_ask"] > 600:
                log.warning("Telegram: คำสั่ง reset หมดเวลา (เกิน 10 นาที)")
                reply("คำสั่ง reset หมดเวลาแล้ว — พิมพ์ 'reset password' ใหม่เพื่อเริ่ม")
                continue
            if time.time() - _last_reset_time.get(token, 0) < _reset_cooldown:
                log.warning("Telegram: ข้าม reset (เพิ่งทำไปไม่นาน)")
                reply("ข้าม: เพิ่ง reset ไปเมื่อไม่นาน — รอ 10 นาทีแล้วลองใหม่")
                continue
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
