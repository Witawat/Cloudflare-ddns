"""Heartbeat monitoring: ส่ง ping ไปยัง Healthchecks.io / Uptime Kuma ทุกรอบ DDNS.

- Healthchecks.io:  URL https://hc-ping.com/<uuid> — ต่อ /fail (รอบล้มเหลว), /exit (ปิดโปรแกรม)
- Uptime Kuma:      URL push monitor — ต่อ ?status=down&msg=... เมื่อล้มเหลว/ปิด
"""

import logging
import urllib.request

log = logging.getLogger("cloudflare-ddns")

USER_AGENT = "cloudflare-ddns-updater/1.0"


def _ping(url, timeout=8):
    """GET URL และคืนว่าได้ HTTP 200 หรือไม่ (ไม่โยน exception ให้ลูปหลัก)"""
    try:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read()
        return True
    except Exception as exc:
        log.debug("heartbeat ping %s ไม่ได้: %s", url, exc)
        return False


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
    urls = []
    for value in (getattr(cfg, "healthchecks_url", ""), getattr(cfg, "uptimekuma_url", "")):
        if value and value.strip():
            urls.append(value.strip())
    if not urls:
        return
    for url in urls:
        target = _signal_url(url, "exit") if stopped else (_signal_url(url, "fail") if not ok else url)
        if _ping(target):
            log.debug("heartbeat สำเร็จ: %s", target)
        else:
            log.warning("heartbeat ส่งไม่ได้: %s", target)
