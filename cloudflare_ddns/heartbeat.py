"""Heartbeat monitoring: ส่ง ping ไปยัง Healthchecks.io / Uptime Kuma ทุกรอบ DDNS.

- Healthchecks.io:  URL https://hc-ping.com/<uuid> — ต่อ /fail (รอบล้มเหลว), /exit (ปิดโปรแกรม)
- Uptime Kuma:      URL push monitor — ต่อ ?status=down&msg=... เมื่อล้มเหลว/ปิด
"""

import json
import logging
import os
import time
import urllib.error
import urllib.request

from . import config as config_mod
from . import i18n
from . import instance_lock

log = logging.getLogger("cloudflare-ddns")

USER_AGENT = None  # ใช้ config_mod.user_agent() ที่ import ข้างล่าง
HEARTBEAT_TIMEOUT = 10
# แจ้ง warning ครั้งเดียวต่อ 10 นาที (กันสแปม log เมื่อเน็ต/บริการหลุดยาว)
_WARN_INTERVAL = 600
_last_warn_time = 0.0
# กันส่งถี่เกินไปต่อ URL (เช่น โปรแกรมรันซ้ำหลาย instance / คอนฟิกผิด) —
# ถ้าห่างจากครั้งก่อน < 60 วิ จะข้าม (Healthchecks จำกัด ping ต่อนาที —
# interval_seconds ที่สั้นกว่า 60 ก็ยังส่ง heartbeat แค่นาทีละครั้ง)
MIN_PING_INTERVAL = 60
_last_sent = {}


def _load_state(config_path):
    """อ่านเวลาส่ง heartbeat ล่าสุดจากไฟล์ (ข้าม process) — กันรันซ้ำ 2 instance ส่งเบิ้ล"""
    path = config_mod.heartbeat_state_path_for(config_path)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return {}


def _save_state(config_path, data):
    path = config_mod.heartbeat_state_path_for(config_path)
    text = json.dumps(data, ensure_ascii=False)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            if handle.read() == text:
                return
    except OSError:
        pass
    config_mod.atomic_write_text(path, text)


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


def _signal_url(url, kind, lang="th"):
    """แปลง URL ให้เป็น endpoint 'สัญญาณ' ตามบริการ (kind = fail | exit)"""
    url = url.strip()
    suffix = "fail" if kind == "fail" else "exit"
    if "hc-ping.com" in url:
        return url.rstrip("/") + "/" + suffix
    sep = "&" if "?" in url else "?"
    msg = i18n.t(lang, "hb.fail") if kind == "fail" else i18n.t(lang, "hb.exit")
    return url + sep + "status=down&msg=" + msg


def send_ping(cfg, ok=True, stopped=False):
    """ส่ง heartbeat ตามสถานะ.

    ok=True  = รอบทำงานปกติ (ping URL ตรง ๆ)
    ok=False = รอบมีปัญหา (ส่งสัญญาณ fail)
    stopped  = โปรแกรมกำลังหยุด (ส่งสัญญาณ exit)

    กันส่งซ้ำข้าม process: ครอบ file lock ช่วงตรวจ-ส่ง-เขียน (อีก instance ที่ lock
    ไม่ได้จะข้ามรอบนี้) + จดเวลาล่าสุดลง heartbeat_state.json (อ่านจากทุก process)
    """
    global _last_warn_time
    lang = getattr(cfg, "language", "th") or "th"
    # ความถี่ขั้นต่ำระหว่าง ping 2 ครั้ง (วินาที) — ตั้งได้ใน config (default 60 —
    # Healthchecks รับ ~1 ครั้ง/นาที; Kuma รับถี่กว่าได้)
    min_interval = float(getattr(cfg, "heartbeat_min_interval", 0) or MIN_PING_INTERVAL)
    if min_interval < 5:
        min_interval = MIN_PING_INTERVAL
    urls = []
    for value in (getattr(cfg, "healthchecks_url", ""), getattr(cfg, "uptimekuma_url", "")):
        if value and value.strip():
            urls.append(value.strip())
    if not urls:
        return
    # บันทึกการส่ง/ข้ามทุกครั้งเฉพาะเมื่อ detail_log เปิด (ใช้หาสาเหตุ — ปิด default)
    detail = bool(getattr(cfg, "detail_log", False))
    dlog = log.info if detail else log.debug
    config_path = getattr(cfg, "path", "") or ""
    lock_path = os.path.join(config_mod.data_dir_for(config_path), "heartbeat.lock")
    with instance_lock.file_lock(lock_path) as lock:
        if not lock.locked:
            dlog("heartbeat: ข้าม (lock ถูกครอบ — instance อื่นกำลังส่ง) — %s", urls)
            return
        state = _load_state(config_path)
        for url in urls:
            target = _signal_url(url, "exit", lang) if stopped else (_signal_url(url, "fail", lang) if not ok else url)
            now = time.time()
            last = max(state.get(target, 0), _last_sent.get(target, 0))
            if not stopped and now - last < min_interval:
                dlog("heartbeat: ข้าม %s (ส่งล่าสุดเมื่อ %.0f วิที่แล้ว — ต้องห่าง ≥%d วิ)", target, now - last, int(min_interval))
                continue
            ok_sent, error = _ping(target)
            if ok_sent:
                state[target] = now
                _last_sent[target] = now
                dlog("heartbeat: ส่ง OK — %s", target)
                continue
            if now - _last_warn_time >= _WARN_INTERVAL:
                _last_warn_time = now
                log.warning("heartbeat ส่งไม่ได้: %s (%s)", target, error)
            else:
                log.debug("heartbeat ส่งไม่ได้ (ซ้ำ): %s (%s)", target, error)
        _save_state(config_path, state)


def send_test(cfg):
    """ปุ่มทดสอบในเว็บ: ส่ง ping 1 ครั้งต่อ URL ที่ตั้งไว้ (ไม่โดน rate limit ระหว่างรอบ)"""
    results = []
    for name, value in (
        ("Healthchecks.io", getattr(cfg, "healthchecks_url", "")),
        ("Uptime Kuma", getattr(cfg, "uptimekuma_url", "")),
    ):
        if not value or not str(value).strip():
            continue
        ok_sent, error = _ping(str(value).strip())
        results.append({"name": name, "ok": ok_sent, "error": error})
    return results
