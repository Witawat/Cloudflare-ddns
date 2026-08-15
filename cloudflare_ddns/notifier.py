"""แจ้งเตือนผ่าน Telegram (Bot API) พร้อมคิวสำรองเมื่อส่งไม่สำเร็จ.

- ส่งข้อความผ่าน https://api.telegram.org/bot<token>/sendMessage
- ส่งไม่สำเร็จ -> เก็บลง notify_queue.json แล้วพยายามส่งใหม่ในรอบถัดไป
- กันสแปม: ข้อความ error ซ้ำกับรอบก่อนหน้า จะไม่ส่งซ้ำ
"""

import json
import logging
import os
import urllib.error
import urllib.request

from . import config as config_mod

log = logging.getLogger("cloudflare-ddns")

QUEUE_PATH = os.path.join(config_mod.DEFAULT_DATA_DIR, "notify_queue.json")
MAX_QUEUE = 50

# ประเภทเหตุการณ์
EVENT_START = "start"
EVENT_STOP = "stop"
EVENT_IP_CHANGE = "ip_change"
EVENT_ERROR = "error"
EVENT_CREATED = "created"

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
        """แจ้งเหตุการณ์: ตรวจ enable -> กันซ้ำ -> ส่ง หรือเก็บคิวถ้าส่งไม่ได้."""
        if not self.enabled:
            return
        if not self.event_enabled(event):
            return
        # กันสแปม: error ข้อความเดิมซ้ำกับรอบก่อน ไม่ส่งซ้ำ
        dedupe_key = f"{event}|{text}"
        if event == EVENT_ERROR and dedupe_key == self._last_dedupe_key:
            log.debug("ข้ามการแจ้ง (ซ้ำ): %s", text)
            return
        self._last_dedupe_key = dedupe_key
        self._enqueue(text)

    def _enqueue(self, text):
        items = load_queue()
        items.append(text)
        if len(items) > MAX_QUEUE:
            dropped = items[: len(items) - MAX_QUEUE]
            items = items[-MAX_QUEUE:]
            log.warning("คิวแจ้งเตือนเต็ม ตัดทิ้ง %d ข้อความเก่า", len(dropped))
        save_queue(items)
        log.info("เพิ่มข้อความแจ้งเตือนลงคิว (รวม %d ข้อความ)", len(items))

    # ---- queue ----

    def flush(self):
        """พยายามส่งคิวทั้งหมด คืน (sent, failed)."""
        items = load_queue()
        if not items:
            return 0, 0
        sent = 0
        remaining = []
        for text in items:
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
    except (OSError, ValueError):
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


# ---- ตัวอย่างข้อความ ----

def build_message(event, detail=None):
    if event == EVENT_START:
        return "🟢 Cloudflare DDNS เริ่มทำงาน" + (f"\n{detail}" if detail else "")
    if event == EVENT_STOP:
        return "🔴 Cloudflare DDNS หยุดทำงาน" + (f"\n{detail}" if detail else "")
    if event == EVENT_IP_CHANGE:
        return f"🔄 IP เปลี่ยน: {detail}"
    if event == EVENT_CREATED:
        return f"🆕 สร้าง record ใหม่: {detail}"
    if event == EVENT_ERROR:
        return f"⚠️ เกิดปัญหา: {detail}"
    return detail or ""
