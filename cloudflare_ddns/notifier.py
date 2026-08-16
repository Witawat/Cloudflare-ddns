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
    def __init__(self, bot_token="", chat_id="", events=None):
        self.bot_token = (bot_token or "").strip()
        self.chat_id = str(chat_id or "").strip()
        self.events = events or {}
        self._last_dedupe_key = ""

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
            items = load_queue()
            items.append(text)
            if len(items) > MAX_QUEUE:
                dropped = items[: len(items) - MAX_QUEUE]
                items = items[-MAX_QUEUE:]
                log.warning("คิวแจ้งเตือนเต็ม ตัดทิ้ง %d ข้อความเก่า", len(dropped))
            save_queue(items)
            log.info("เพิ่มข้อความแจ้งเตือนลงคิว (รวม %d ข้อความ)", len(items))

    # ---- queue ----

    def flush(self, max_seconds=60):
        """พยายามส่งคิวทั้งหมด (จำกัดเวลา max_seconds กัน block นาน) คืน (sent, failed)."""
        with _queue_lock:
            items = load_queue()
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
            save_queue(remaining)
            if sent:
                log.info("ส่งแจ้งเตือน Telegram สำเร็จ %d ข้อความ (คิวเหลือ %d)", sent, len(remaining))
            return sent, len(remaining)


# ---- ฟังก์ชันระดับโมดูล ----

def load_queue():
    try:
        with open(QUEUE_PATH, "r", encoding="utf-8") as handle:
            items = json.load(handle)
        return items if isinstance(items, list) else []
    except ValueError as exc:
        log.warning("อ่านคิวแจ้งเตือนไม่ได้ (ไฟล์เสีย?) — ถือว่าว่าง: %s", exc)
        return []
    except OSError:
        return []


def save_queue(items):
    os.makedirs(os.path.dirname(QUEUE_PATH), exist_ok=True)
    tmp = QUEUE_PATH + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(items, handle, ensure_ascii=False, indent=2)
        os.replace(tmp, QUEUE_PATH)
    except OSError as exc:
        log.warning("บันทึกคิวแจ้งเตือนไม่ได้: %s", exc)


def queue_size():
    return len(load_queue())


def clear_queue():
    """ล้างคิวทั้งหมด (ปุ่มใน Web UI)"""
    save_queue([])


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
