"""Heartbeat monitoring: ส่ง ping ไปยัง Healthchecks.io / Uptime Kuma ทุกรอบ DDNS.

- Healthchecks.io:  URL https://hc-ping.com/<uuid> — ต่อ /fail (รอบล้มเหลว), /exit (ปิดโปรแกรม)
- Uptime Kuma:      URL push monitor — ต่อ ?status=down&msg=... เมื่อล้มเหลว/ปิด
"""

import logging
import time
import urllib.error
import urllib.request

from . import config as config_mod

log = logging.getLogger("cloudflare-ddns")

USER_AGENT = None  # ใช้ config_mod.user_agent() ที่ import ข้างล่าง
HEARTBEAT_TIMEOUT = 10
# แจ้ง warning ครั้งเดียวต่อ 10 นาที (กันสแปม log เมื่อเน็ต/บริการหลุดยาว)
_WARN_INTERVAL = 600
_last_warn_time = 0.0
# กันส่งถี่เกินไปต่อ URL (เช่น โปรแกรมรันซ้ำหลาย instance / คอนฟิกผิด) —
# ถ้าห่างจากครั้งก่อน < 30 วิ จะข้าม (Healthchecks จำกัด ping ต่อนาที)
MIN_PING_INTERVAL = 30
_last_sent = {}


def _ping(url, timeout=HEARTBEAT_TIMEOUT):
    """GET URL และคืน (ok, error) — retry 1 ครั้งเฉพาะ network error (ไม่ retry HTTP error
    เช่น 429 rate limit — ยิงซ้ำยิ่งแย่) ไม่โยน exception"""
    last_error = "unknown"
    for attempt in (1, 2):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": config_mod.user_agent()})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                response.read()
            return True, ""
        except urllib.error.HTTPError as exc:
            last_error = f"HTTP {exc.code} (บริการปลายทางปฏิเสธ)"
            break
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt == 1:
                time.sleep(1.0)
                continue
    return False, last_error


def _signal_url(url, kind):
    """แปลง URL ให้เป็น endpoint 'สัญญาณ' ตามบริการ (kind = fail | exit)"""
    url = url.strip()
    suffix = "fail" if kind == "fail" else "exit"
    if "hc-ping.com" in url:
        return url.rstrip("/") + "/" + suffix
    sep = "&" if "?" in url else "?"
    msg = "DDNS+รอบล้มเหลว" if kind == "fail" else "DDNS+หยุดทำงาน"
    return url + sep + "status=down&msg=" + msg


def send_ping(cfg, ok=True, stopped=False):
    """ส่ง heartbeat ตามสถานะ.

    ok=True  = รอบทำงานปกติ (ping URL ตรง ๆ)
    ok=False = รอบมีปัญหา (ส่งสัญญาณ fail)
    stopped  = โปรแกรมกำลังหยุด (ส่งสัญญาณ exit)
    """
    global _last_warn_time
    urls = []
    for value in (getattr(cfg, "healthchecks_url", ""), getattr(cfg, "uptimekuma_url", "")):
        if value and value.strip():
            urls.append(value.strip())
    if not urls:
        return
    for url in urls:
        target = _signal_url(url, "exit") if stopped else (_signal_url(url, "fail") if not ok else url)
        now = time.time()
        last = _last_sent.get(target, 0)
        if not stopped and now - last < MIN_PING_INTERVAL:
            log.debug("ข้าม heartbeat (ถี่เกิน %d วิ): %s", MIN_PING_INTERVAL, target)
            continue
        ok_sent, error = _ping(target)
        if ok_sent:
            _last_sent[target] = now
            log.debug("heartbeat สำเร็จ: %s", target)
            continue
        if now - _last_warn_time >= _WARN_INTERVAL:
            _last_warn_time = now
            log.warning("heartbeat ส่งไม่ได้: %s (%s)", target, error)
        else:
            log.debug("heartbeat ส่งไม่ได้ (ซ้ำ): %s (%s)", target, error)
