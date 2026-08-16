"""Web UI: ดูสถานะ + ตั้งค่าผ่านเบราว์เซอร์ (stdlib ล้วน, one-page).

- เปิดเฉพาะ 127.0.0.1
- ถ้าตั้ง webui_password ไว้ต้องใส่รหัสก่อน (cookie แบบง่าย)
- ฟอร์มตั้งค่าสร้าง/ตรวจ config.ini ให้อัตโนมัติ (ไม่มี textarea ให้มั่ว)
"""

import json
import logging
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import __version__
from . import config as config_mod
from . import ddns
from . import notifier

# แคชผลตรวจ NAT สำหรับ /ip-check — nat_report ตรวจเต็ม (tracert + STUN หลายรอบ) ช้า ~10 วิ
# จึงรันเต็มแค่ทุก 60 วิ ระหว่างนั้นตอบผลเดิมทันที (IP/NAT ไม่เปลี่ยนถี่ขนาดนั้น)
_nat_cache = {"at": 0.0, "result": None}
NAT_CACHE_TTL = 60.0

log = logging.getLogger("cloudflare-ddns")

_tunnel_mgr = None
_ddns_busy = {"running": False}
_update_cache = {"time": 0.0, "data": {}}

# กันสุ่มรหัสผ่านหน้า login (เก็บในหน่วยความจำ — เริ่มใหม่เมื่อ service/โปรแกรม restart)
_LOGIN_MAX_FAILS = 5
_LOGIN_LOCK_SECONDS = 300
_login_guard = {"fails": 0, "locked_until": 0.0}


def _version_newer(latest, current):
    """เปรียบเทียบ version แบบตัวเลข (1.2.3 vs 1.2.10) — คืน True ถ้า latest > current"""
    def _parts(v):
        return [int(x) for x in str(v).strip("v").split(".") if x.isdigit()][:3]

    return _parts(latest) > _parts(current)


def _is_admin():
    """ตรวจว่า process นี้มีสิทธิ์ admin หรือไม่ (LocalSystem/runas = True)"""
    try:
        import ctypes

        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _in_service():
    """webui นี้รันใน Windows Service หรือไม่ (service.py เซ็ต env ตอน SvcDoRun)"""
    import os

    return os.environ.get("CFDDNS_RUNNING_AS_SERVICE") == "1"


def _get_tunnel_mgr(config_path=None):
    global _tunnel_mgr
    if _tunnel_mgr is None:
        from . import tunnel as tunnel_mod

        _tunnel_mgr = tunnel_mod.TunnelManager(config_path)
    return _tunnel_mgr


def _decode_tunnel_token(token):
    """แยก account_id + tunnel_id จาก tunnel token. คืน (dict, error)

    รองรับ 2 รูปแบบ:
    - JWT 3 ส่วน (header.payload.signature) -> ใช้ payload (ส่วนที่ 1)
    - รูปแบบใหม่ 1 ส่วน (payload ล้วน)      -> ใช้ทั้ง token
    """
    import base64
    import json as _json

    try:
        token = token.strip()
        parts = token.split(".")
        payload_part = parts[1] if len(parts) >= 2 else parts[0]
        payload_part += "=" * (-len(payload_part) % 4)
        claims = _json.loads(base64.urlsafe_b64decode(payload_part))
        account_id = claims.get("a") or claims.get("accountID")
        tunnel_id = claims.get("t") or claims.get("tunnelID")
    except Exception:
        return None, "tunnel token ผิดรูปแบบ (ควรเป็น eyJ... ยาว ๆ จากหน้า Zero Trust)"
    if not account_id or not tunnel_id:
        return None, "tunnel token ไม่มี account/tunnel id (token ผิดรูปแบบ?)"
    return {"account_id": account_id, "tunnel_id": tunnel_id}, ""

def _tunnel_api_error(exc):
    """แปล error จากการเรียก API tunnel ให้อ่านง่าย — 403 = token ไม่มีสิทธิ์ Tunnel"""
    text = str(exc)
    if "403" in text or "10000" in text:
        return (
            "API token ไม่มีสิทธิ์จัดการ Tunnel (403) — ไปที่ dash.cloudflare.com → My Profile → API Tokens → "
            "Edit token ที่ใช้ → เพิ่มสิทธิ์ Account → Cloudflare Tunnel → Edit แล้วลองใหม่"
        )
    return text


# ชื่อบริการสำหรับพอร์ตที่พบบ่อย
PORT_SERVICES = {    20: "ftp-data", 21: "ftp", 22: "ssh", 23: "telnet", 25: "smtp", 53: "dns",
    80: "http", 110: "pop3", 143: "imap", 443: "https", 445: "smb", 465: "smtps",
    587: "smtp-sub", 993: "imaps", 995: "pop3s", 1433: "mssql", 1883: "mqtt",
    3306: "mysql", 3389: "rdp", 5432: "postgres", 5900: "vnc", 6379: "redis",
    8080: "http-alt", 8443: "https-alt", 9000: "php-fpm", 27017: "mongodb",
}
DEFAULT_SCAN_PORTS = [21, 22, 23, 25, 53, 80, 110, 143, 443, 445, 993, 995, 1433, 3306, 3389, 5900, 6379, 8080, 8443, 27017]

# ---- หน้าเว็บ (HTML/CSS/JS แยกไฟล์ — แก้ใน webui.html / webui.js) ----


def _static_path(name):
    """หาที่อยู่ไฟล์ static — ตอนเป็น exe อยู่ข้างใน bundle (--add-data)"""
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, "cloudflare_ddns", name)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), name)


def _read_static(name):
    try:
        with open(_static_path(name), "r", encoding="utf-8") as handle:
            return handle.read()
    except OSError:
        return ""


# HTML+CSS ทั้งหมด (placeholder __LOGIN__/__VERSION__ แทนที่ตอน serve)
PAGE = _read_static("webui.html")
# JavaScript ทั้งหมด (serve ผ่าน /webui.js — script src ใน PAGE)
PAGE_JS = _read_static("webui.js")
# หน้า login แยกไฟล์ — CSS ยืมจาก PAGE (placeholder __CSS__)
PAGE_LOGIN = _read_static("webui_login.html")



# ---------- แปลง config <-> dict ----------


def _cfg_to_dict(cfg):
    return {
        "cloudflare": {
            "api_token": cfg.api_token,
            "interval_seconds": cfg.interval_seconds,
            "use_ipv4": cfg.use_ipv4,
            "use_ipv6": cfg.use_ipv6,
            "reject_cloudflare_ips": cfg.reject_cloudflare_ips,
            "healthchecks_url": cfg.healthchecks_url,
            "uptimekuma_url": cfg.uptimekuma_url,
            "webui_port": cfg.webui_port,
            "webui_host": cfg.webui_host,
            "webui_password": cfg.webui_password,
            "log_dir": cfg.log_dir if cfg.log_dir != config_mod.DEFAULT_LOG_DIR else "",
        },
        "telegram": {
            "bot_token": cfg.telegram_bot_token,
            "chat_id": cfg.telegram_chat_id,
            "notify_start": cfg.notify_start,
            "notify_stop": cfg.notify_stop,
            "notify_ip_change": cfg.notify_ip_change,
            "notify_error": cfg.notify_error,
            "notify_created": cfg.notify_created,
            "notify_round": cfg.notify_round,
            "daily_report": cfg.daily_report,
            "daily_report_time": cfg.daily_report_time,
        },
        "tunnel": {
            "enabled": cfg.tunnel_enabled,
            "token": cfg.tunnel_token,
            "cloudflared_path": cfg.cloudflared_path,
            "hosts": cfg.tunnel_hosts,
        },
        "records": [
            {
                "name": r.name,
                "zone": r.zone,
                "proxied": r.proxied,
                "ttl": r.ttl,
                "ipv4": r.ipv4,
                "ipv6": r.ipv6,
            }
            for r in cfg.records
        ],
    }


def _as_int(value, default):
    """แปลงค่าเป็น int อย่างปลอดภัย (client ส่งค่าผิด -> ใช้ default กัน 500)"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _dict_to_ini(data):
    """สร้างข้อความ config.ini จาก dict (โครงสร้างเดียวกับ _cfg_to_dict)."""
    cf = data.get("cloudflare", {})
    tg = data.get("telegram", {})
    lines = ["[cloudflare]"]

    def kv(key, value):
        lines.append(f"{key} = {value}")

    kv("api_token", str(cf.get("api_token", "")).strip())
    kv("interval_seconds", _as_int(cf.get("interval_seconds", 60), 60))
    kv("use_ipv4", str(bool(cf.get("use_ipv4"))).lower())
    kv("use_ipv6", str(bool(cf.get("use_ipv6"))).lower())
    kv("reject_cloudflare_ips", str(bool(cf.get("reject_cloudflare_ips", True))).lower())
    kv("healthchecks_url", str(cf.get("healthchecks_url", "")).strip())
    kv("uptimekuma_url", str(cf.get("uptimekuma_url", "")).strip())
    kv("webui_port", _as_int(cf.get("webui_port", 8123), 8123))
    kv("webui_host", str(cf.get("webui_host", "127.0.0.1")).strip() or "127.0.0.1")
    kv("webui_password", str(cf.get("webui_password", "")).strip())
    kv("log_dir", str(cf.get("log_dir", "")).strip())
    kv("telegram_bot_token", str(tg.get("bot_token", "")).strip())
    kv("telegram_chat_id", str(tg.get("chat_id", "")).strip())
    kv("notify_start", str(bool(tg.get("notify_start", True))).lower())
    kv("notify_stop", str(bool(tg.get("notify_stop", True))).lower())
    kv("notify_ip_change", str(bool(tg.get("notify_ip_change", True))).lower())
    kv("notify_error", str(bool(tg.get("notify_error", True))).lower())
    kv("notify_created", str(bool(tg.get("notify_created", True))).lower())
    kv("notify_round", str(bool(tg.get("notify_round", False))).lower())
    kv("daily_report", str(bool(tg.get("daily_report", True))).lower())
    kv("daily_report_time", str(tg.get("daily_report_time", "08:00")).strip() or "08:00")
    tu = data.get("tunnel", {})
    kv("tunnel_enabled", str(bool(tu.get("enabled", False))).lower())
    kv("tunnel_token", str(tu.get("token", "")).strip())
    kv("cloudflared_path", str(tu.get("cloudflared_path", "")).strip())
    kv("tunnel_hosts", json.dumps(tu.get("hosts", []), ensure_ascii=False))
    lines.append("")
    for rec in data.get("records", []):
        name = str(rec.get("name", "")).strip().rstrip(".")
        if not name:
            continue
        lines.append(f"[record:{name}]")
        kv("zone", str(rec.get("zone", "")).strip().rstrip("."))
        kv("proxied", str(bool(rec.get("proxied", False))).lower())
        kv("ttl", max(_as_int(rec.get("ttl", 60), 60), 60))
        kv("ipv4", str(bool(rec.get("ipv4", True))).lower())
        kv("ipv6", str(bool(rec.get("ipv6", True))).lower())
        lines.append("")
    return "\n".join(lines)


class WebUIHandler(BaseHTTPRequestHandler):
    server_version = "CloudflareDDNSWebUI/2.0"

    def _load_records_time(self):
        """อ่าน records_time จาก state.json (เวลา IP ล่าสุดของแต่ละ record)"""
        try:
            import json as _json

            path = config_mod.state_path_for(self.server.config_path)
            with open(path, "r", encoding="utf-8") as handle:
                state = _json.load(handle)
            return state.get("records_time", {})
        except (OSError, ValueError):
            return {}

    @property
    def cfg(self):
        return self.server.cfg

    def log_message(self, *args):
        pass

    # ---- helpers ----

    def _send(self, code, body, content_type="text/html; charset=utf-8"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            # client ตัด connection ก่อน response เสร็จ (เช่น หน้าเว็บโหลดใหม่/ปิด หรือ /ip-check ช้า)
            # ไม่ใช่ error ของ server — เงียบ ๆ ไป ไม่ log ERROR ไม่ตอบ 500
            log.debug("client ตัด connection กลางคัน (%s)", self.path)

    def _send_json(self, code, payload):
        self._send(code, json.dumps(payload, ensure_ascii=False), "application/json; charset=utf-8")

    def _authed(self):
        password = self.cfg.webui_password
        if not password:
            return True
        cookies = self.headers.get("Cookie", "")
        for part in cookies.split(";"):
            key, _, value = part.strip().partition("=")
            if key == "cfddns_session" and value == password:
                return True
        return False

    # ---- GET ----

    def do_GET(self):
        """wrapper กัน crash: error ภายใน -> ตอบ JSON 500 + log (เหมือน do_POST)"""
        try:
            return self._do_get_inner()
        except Exception:
            log.exception("do_GET เกิดข้อผิดพลาด (%s) — ตอบ 500", self.path)
            try:
                return self._send_json(500, {"ok": False, "message": "เกิดข้อผิดพลาดภายใน — ดู log (แถบ Log ล่าสุด) เพื่อรายละเอียด"})
            except Exception:
                return None

    def _do_get_inner(self):
        if self.path == "/ip-check":
            from . import ip_detect

            import concurrent.futures

            now = time.time()
            if not _nat_cache["result"] or now - _nat_cache["at"] > NAT_CACHE_TTL:
                _nat_cache["at"] = now

                def check(version):
                    return version, ip_detect.get_public_ip(version, timeout=6)

                result = {"ipv4": "", "ipv6": "", "nat": None}
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                    futures = [pool.submit(check, 4), pool.submit(check, 6)]
                    for future in concurrent.futures.as_completed(futures):
                        version, ip = future.result()
                        result["ipv4" if version == 4 else "ipv6"] = ip or ""
                if result["ipv4"]:
                    result["nat"] = ip_detect.nat_report(result["ipv4"], timeout=5)
                _nat_cache["result"] = result
            return self._send_json(200, _nat_cache["result"])

        if self.path == "/notify-queue":
            if not self._authed():
                return self._send_json(401, {"ok": False, "message": "unauthorized"})
            return self._send_json(200, {"ok": True, "queue": notifier.load_queue(config_mod.queue_path_for(self.server.config_path))})

        if self.path.split("?", 1)[0] == "/log":
            if not self._authed():
                return self._send_json(401, {"ok": False, "message": "unauthorized"})
            import os

            log_path = os.path.join(self.cfg.log_dir, "cloudflare-ddns.log")
            try:
                with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
                    lines = handle.readlines()
                body = "".join(lines[-200:])
                return self._send(200, body, "text/plain; charset=utf-8")
            except OSError as exc:
                return self._send(200, f"(ยังไม่มีไฟล์ log: {exc})", "text/plain; charset=utf-8")

        if self.path == "/status.json":
            if not self._authed():
                return self._send_json(401, {"ok": False, "message": "unauthorized"})
            engine = ddns.DDNSEngine(self.server.config_path)
            status = engine.status()
            status["records_time"] = self._load_records_time()
            cfg_errors = self.cfg.validate()
            status["config_ok"] = not cfg_errors
            status["config_errors"] = cfg_errors
            status["errors_active"] = bool(status.get("record_errors"))
            status["record_errors"] = status.get("record_errors", {})
            notify = notifier.TelegramNotifier.from_config(self.cfg)
            status["telegram"] = {
                "enabled": notify.enabled,
                "chat_id": notify.chat_id,
                "queue": notifier.queue_size(config_mod.queue_path_for(self.server.config_path)),
            }
            status["tunnel"] = _get_tunnel_mgr(self.server.config_path).status(self.cfg)
            status["record_errors"] = status.get("record_errors", {})
            try:
                from . import service as service_mod

                _svc = service_mod.service_status()
                status["service"] = {
                    "installed": _svc.get("installed", False),
                    "state": _svc.get("state", ""),
                    "running": _svc.get("state") == "running",
                }
            except Exception:
                status["service"] = {"installed": False, "state": "", "running": False}
            status["version"] = __version__
            status["runtime"] = {
                "in_service": _in_service(),
                "admin": _is_admin(),
            }
            try:
                from . import cloudflare_api as _cf_api

                status["api_stats"] = _cf_api.api_stats()
            except Exception:
                status["api_stats"] = {"calls": 0, "errors": 0, "rate_limited": 0}
            return self._send_json(200, status)

        if self.path == "/config.json":
            if not self._authed():
                return self._send_json(401, {"ok": False, "message": "unauthorized"})
            return self._send_json(200, _cfg_to_dict(self.cfg))

        if self.path == "/config-file":
            if not self._authed():
                return self._send_json(401, {"ok": False, "message": "unauthorized"})
            return self._send(200, self.cfg.raw_text(), "text/plain; charset=utf-8")

        if self.path == "/setup-state":
            errors = self.cfg.validate()
            return self._send_json(200, {"needs_setup": bool(errors), "errors": errors})

        if self.path == "/update-check":
            """เช็คเวอร์ชันใหม่จาก GitHub Releases (cache 6 ชม.)"""
            now = time.time()
            if _update_cache["time"] and now - _update_cache["time"] < 6 * 3600:
                return self._send_json(200, _update_cache["data"])
            import urllib.error
            import urllib.request

            data = {
                "ok": False,
                "latest": "",
                "has_update": False,
                "url": "https://github.com/Witawat/Cloudflare-ddns/releases",
                "message": "",
            }
            try:
                request = urllib.request.Request(
                    "https://api.github.com/repos/Witawat/Cloudflare-ddns/releases/latest",
                    headers={"User-Agent": config_mod.user_agent(), "Accept": "application/vnd.github+json"},
                )
                with urllib.request.urlopen(request, timeout=8) as response:
                    release = json.loads(response.read().decode("utf-8", "replace"))
                latest = str(release.get("tag_name", "")).strip().lstrip("v")
                if latest:
                    data.update(ok=True, latest=latest, has_update=_version_newer(latest, __version__))
                    if release.get("html_url"):
                        data["url"] = release["html_url"]
                else:
                    data["message"] = "ไม่พบ release ล่าสุด (tag ว่าง)"
            except urllib.error.HTTPError as exc:
                data["message"] = f"GitHub ตอบ {exc.code} (ไม่มี release/rate limit)"
            except Exception as exc:
                data["message"] = f"เช็คไม่ได้: {exc}"
            _update_cache.update(time=now, data=data)
            return self._send_json(200, data)

        if self.path == "/webui.js":
            # JavaScript หน้าเว็บ (แยกไฟล์ — static ไม่ต้อง login เพราะไม่มีข้อมูลลับ)
            return self._send(200, PAGE_JS, "application/javascript; charset=utf-8")

        if not self._authed():
            # หน้า login แบบเดี่ยว (ไฟล์แยก webui_login.html) — ห้ามส่ง PAGE หลัก
            # (script หลักจะรันแล้วโชว์ error 401 ใต้หน้าล็อกอิน) — CSS ยืมจาก PAGE
            # (สกัดเฉพาะเนื้อหาใน <style> — หน้า login มี <style> ของตัวเองอยู่แล้ว)
            style_start = PAGE.index("<style>") + len("<style>")
            style_end = PAGE.index("</style>")
            css = PAGE[style_start:style_end]
            return self._send(200, PAGE_LOGIN.replace("__CSS__", css))
        return self._send(200, PAGE.replace("__LOGIN__", "").replace("__VERSION__", __version__))

    # ---- POST ----

    def _read_body(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except (TypeError, ValueError):
            length = 0
        if length < 0:
            length = 0
        return self.rfile.read(length).decode("utf-8", "replace")

    def do_POST(self):
        """wrapper กัน crash: error ภายใน -> ตอบ JSON 500 + log ละเอียด
        (เดิม exception หลุด -> connection หลุด -> client เห็น 'Failed to fetch' ทั้งที่ข้อมูลเขียนไปแล้ว)"""
        try:
            return self._do_post_inner()
        except Exception:
            log.exception("do_POST เกิดข้อผิดพลาด (%s) — ตอบ 500", self.path)
            try:
                return self._send_json(500, {"ok": False, "message": "เกิดข้อผิดพลาดภายใน — ดู log (แถบ Log ล่าสุด) เพื่อรายละเอียด (ข้อมูลบางส่วนอาจถูกบันทึกไปแล้ว — ตรวจอีกครั้ง)"})
            except Exception:
                return None

    def _do_post_inner(self):
        body = self._read_body()

        if self.path == "/login":
            import time as _t

            now = _t.time()
            if now < _login_guard["locked_until"]:
                remain = int(_login_guard["locked_until"] - now)
                log.warning("login โดนล็อกชั่วคราว (รหัสผิดบ่อย) — เหลือ %d วิ", remain)
                return self._send_json(
                    429,
                    {"ok": False, "message": f"พยายามเข้าสู่ระบบบ่อยเกินไป — ล็อกชั่วคราว รออีก {remain} วิ"},
                )
            form = dict(__import__("urllib.parse", fromlist=["parse_qsl"]).parse_qsl(body))
            if form.get("pw") == self.cfg.webui_password:
                _login_guard["fails"] = 0
                _login_guard["locked_until"] = 0.0
                self.send_response(302)
                self.send_header("Location", "/")
                self.send_header("Set-Cookie", f"cfddns_session={self.cfg.webui_password}; HttpOnly; Path=/")
                self.end_headers()
                return
            _login_guard["fails"] += 1
            _t.sleep(0.4)  # หน่วงเล็กน้อย กันยิงเร็วต่อเนื่อง
            if _login_guard["fails"] >= _LOGIN_MAX_FAILS:
                _login_guard["locked_until"] = now + _LOGIN_LOCK_SECONDS
                _login_guard["fails"] = 0
                log.warning("login ผิด %d ครั้งติดต่อกัน — ล็อกชั่วคราว %d นาที", _LOGIN_MAX_FAILS, _LOGIN_LOCK_SECONDS // 60)
            return self._send_json(401, {"ok": False, "message": "รหัสผ่านไม่ถูกต้อง"})

        if self.path == "/log-clear":
            """ล้างไฟล์ log (ผู้ใช้กดปุ่ม "ล้าง log") — ต้อง login"""
            if not self._authed():
                return self._send_json(401, {"ok": False, "message": "unauthorized"})
            import os

            log_path = os.path.join(self.cfg.log_dir, "cloudflare-ddns.log")
            try:
                with open(log_path, "w", encoding="utf-8"):
                    pass
            except OSError as exc:
                return self._send_json(400, {"ok": False, "message": f"ล้าง log ไม่ได้: {exc}"})
            log.info("ล้าง log ไฟล์แล้ว (ปุ่มล้าง log ในเว็บ)")
            return self._send_json(200, {"ok": True, "message": "ล้าง log แล้ว"})

        if self.path == "/log-event":
            """รับ error จากฝั่งหน้าเว็บ (JS) มาเขียนลงไฟล์ log — เปิดเสมอ ไม่ต้อง login"""
            try:
                data = json.loads(body) if body else {}
            except ValueError:
                data = {}
            log.warning(
                "Web UI (JS) %s: %s",
                str(data.get("context", "?")),
                str(data.get("message", ""))[:500],
            )
            return self._send_json(200, {"ok": True})

        if not self._authed():
            return self._send_json(401, {"ok": False, "message": "unauthorized"})

        if self.path == "/verify-token":
            from . import cloudflare_api

            try:
                data = json.loads(body)
            except ValueError:
                return self._send_json(400, {"ok": False, "message": "JSON ผิดรูปแบบ"})
            token = str(data.get("token", "")).strip()
            if not token:
                return self._send_json(400, {"ok": False, "message": "ไม่พบ token"})
            api = cloudflare_api.CloudflareAPI(token)
            try:
                api.verify_token()
            except cloudflare_api.CloudflareError as exc:
                return self._send_json(400, {"ok": False, "message": str(exc)})
            try:
                zones = [z["name"] for z in api.list_zones()]
            except cloudflare_api.CloudflareError as exc:
                zones = []
            return self._send_json(200, {"ok": True, "zones": zones})

        if self.path == "/resolve-chat-id":
            try:
                data = json.loads(body)
            except ValueError:
                return self._send_json(400, {"ok": False, "message": "JSON ผิดรูปแบบ"})
            token = str(data.get("bot_token", "")).strip()
            if not token:
                return self._send_json(400, {"ok": False, "message": "ไม่พบ bot token"})
            chat_id, error = notifier.get_chat_id(token)
            if not chat_id:
                return self._send_json(400, {"ok": False, "message": error})
            return self._send_json(200, {"ok": True, "chat_id": chat_id})

        if self.path == "/notify-test-raw":
            try:
                data = json.loads(body)
            except ValueError:
                return self._send_json(400, {"ok": False, "message": "JSON ผิดรูปแบบ"})
            notify = notifier.TelegramNotifier(
                str(data.get("bot_token", "")).strip(),
                str(data.get("chat_id", "")).strip(),
                config_path=self.server.config_path,
            )
            ok, error = notify.send_raw(str(data.get("text", "ทดสอบ")))
            return self._send_json(200 if ok else 400, {"ok": ok, "message": error or "ส่งสำเร็จ"})

        if self.path == "/save-file":
            try:
                data = json.loads(body)
            except ValueError:
                return self._send_json(400, {"ok": False, "message": "JSON ผิดรูปแบบ"})
            ok, message = self.cfg.save_text(str(data.get("text", "")))
            return self._send_json(200 if ok else 400, {"ok": ok, "message": message})

        if self.path == "/list-records":
            from . import cloudflare_api

            try:
                data = json.loads(body)
            except ValueError:
                return self._send_json(400, {"ok": False, "message": "JSON ผิดรูปแบบ"})
            token = str(data.get("token") or "").strip() or self.cfg.api_token
            zone = str(data.get("zone") or "").strip()
            if not token:
                return self._send_json(400, {"ok": False, "message": "ไม่พบ token (ตั้งค่า Cloudflare ก่อน)"})
            if not zone:
                return self._send_json(400, {"ok": False, "message": "ไม่พบ zone"})
            api = cloudflare_api.CloudflareAPI(token)
            try:
                zone_id = api.get_zone_id(zone)
                records = api.list_dns_records(zone_id)
            except cloudflare_api.CloudflareError as exc:
                return self._send_json(400, {"ok": False, "message": str(exc)})
            names = sorted({r["name"] for r in records})
            return self._send_json(200, {"ok": True, "records": names})

        if self.path == "/port-scan":
            import concurrent.futures
            import socket

            from .config import fqdn_name

            try:
                data = json.loads(body)
            except ValueError:
                return self._send_json(400, {"ok": False, "message": "JSON ผิดรูปแบบ"})
            host = str(data.get("host", "")).strip().rstrip(".")
            allowed = {fqdn_name(rec.name, rec.zone).lower() for rec in self.cfg.records}
            if host.lower() not in allowed:
                return self._send_json(
                    403,
                    {"ok": False, "message": "อนุญาตให้สแกนเฉพาะ host ที่ตั้งไว้ใน config เท่านั้น"},
                )
            try:
                ports = [int(p) for p in (data.get("ports") or DEFAULT_SCAN_PORTS)]
                ports = [p for p in ports if 1 <= p <= 65535]
            except (TypeError, ValueError):
                return self._send_json(400, {"ok": False, "message": "รายการพอร์ตไม่ถูกต้อง (คั่นด้วย ,)"})
            if not ports:
                return self._send_json(400, {"ok": False, "message": "ไม่มีพอร์ตให้สแกน"})
            try:
                ip = socket.gethostbyname(host)
            except socket.gaierror as exc:
                return self._send_json(400, {"ok": False, "message": f"resolve {host} ไม่ได้: {exc}"})

            def _probe(port):
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1.5)
                try:
                    result = sock.connect_ex((ip, port))
                except socket.error:
                    result = -1
                finally:
                    sock.close()
                if result == 0:
                    status = "open"
                elif result in (10060, 110, -1):
                    status = "filtered"
                else:
                    status = "closed"
                return {"port": port, "service": PORT_SERVICES.get(port, ""), "status": status}

            with concurrent.futures.ThreadPoolExecutor(max_workers=64) as pool:
                results = list(pool.map(_probe, ports))
            results.sort(key=lambda r: r["port"])
            return self._send_json(200, {"ok": True, "host": host, "ip": ip, "ports": results})

        if self.path == "/notify-queue/flush":
            if not self._authed():
                return self._send_json(401, {"ok": False, "message": "unauthorized"})
            notify = notifier.TelegramNotifier.from_config(self.cfg)
            if not notify.enabled:
                return self._send_json(400, {"ok": False, "message": "ยังไม่ได้ตั้งค่า Telegram ใน config"})
            sent, failed = notify.flush()
            return self._send_json(200, {"ok": True, "sent": sent, "failed": failed})

        if self.path == "/notify-queue/clear":
            if not self._authed():
                return self._send_json(401, {"ok": False, "message": "unauthorized"})
            notifier.clear_queue(config_mod.queue_path_for(self.server.config_path))
            return self._send_json(200, {"ok": True, "message": "ล้างคิวแล้ว"})

        if self.path == "/tunnel/test":
            import copy
            import time

            try:
                data = json.loads(body)
            except ValueError:
                return self._send_json(400, {"ok": False, "message": "JSON ผิดรูปแบบ"})
            token = str(data.get("token", "")).strip()
            if not token:
                return self._send_json(400, {"ok": False, "message": "กรุณาวาง tunnel token ก่อน"})
            test_cfg = copy.copy(self.cfg)
            test_cfg.tunnel_token = token
            test_cfg.tunnel_enabled = True
            ok, message = _get_tunnel_mgr(self.server.config_path).start(test_cfg)
            if not ok:
                return self._send_json(400, {"ok": False, "message": message})
            time.sleep(4)  # รอให้ cloudflared ตายเองถ้า token ผิด
            still_running = _get_tunnel_mgr(self.server.config_path).status(test_cfg)["running"]
            _get_tunnel_mgr(self.server.config_path).stop()
            if still_running:
                return self._send_json(200, {"ok": True, "message": "token ใช้ได้ — tunnel เชื่อมต่อ Cloudflare แล้ว (หยุดชั่วคราว รอขั้นตอนสุดท้าย)"})
            return self._send_json(
                400,
                {"ok": False, "message": "token ตรวจไม่ผ่าน — cloudflared เชื่อมต่อไม่ได้ (ตรวจ token/อินเทอร์เน็ต/ไฟร์วอลล์)"},
            )

        if self.path == "/tunnel/zones":
            from . import cloudflare_api as _cf_api

            try:
                data = json.loads(body)
            except ValueError:
                return self._send_json(400, {"ok": False, "message": "JSON ผิดรูปแบบ"})
            token = str(data.get("token") or "").strip() or self.cfg.api_token
            if not token:
                return self._send_json(400, {"ok": False, "message": "ไม่พบ API token (ตั้งค่า Cloudflare ก่อน)"})
            api = _cf_api.CloudflareAPI(token)
            try:
                zones = [z["name"] for z in api.list_zones()]
            except _cf_api.CloudflareError as exc:
                return self._send_json(400, {"ok": False, "message": str(exc)})
            return self._send_json(200, {"ok": True, "zones": zones})

        if self.path == "/tunnel/bind":
            from . import cloudflare_api as _cf_api

            try:
                data = json.loads(body)
            except ValueError:
                return self._send_json(400, {"ok": False, "message": "JSON ผิดรูปแบบ"})
            token = str(data.get("token") or "").strip()
            hostname = str(data.get("hostname") or "").strip().rstrip(".")
            path = str(data.get("path") or "").strip()
            if path and not path.startswith("/"):
                path = "/" + path
            protocol = str(data.get("protocol") or "http").strip().lower()
            if protocol not in ("http", "https", "tcp", "udp"):
                protocol = "http"
            service = str(data.get("service") or "").strip()
            if not service:
                return self._send_json(400, {"ok": False, "message": "กรุณาระบุบริการ/พอร์ต เช่น http://localhost:8080 หรือ tcp://localhost:22"})
            if not token:
                return self._send_json(400, {"ok": False, "message": "ไม่พบ tunnel token"})
            if not hostname:
                return self._send_json(400, {"ok": False, "message": "กรุณาระบุ hostname เช่น app.โดเมน.com"})

            # 1. แกะ account_id + tunnel_id จาก tunnel token (JWT payload)
            ids, error = _decode_tunnel_token(token)
            if error:
                return self._send_json(400, {"ok": False, "message": error})
            account_id, tunnel_id = ids["account_id"], ids["tunnel_id"]

            # 1.5 ตรวจชื่อชนกับ DDNS ก่อน (Cloudflare ห้าม A/AAAA กับ CNAME ซ้ำชื่อกัน)
            domain = hostname.split(".", 1)[1] if "." in hostname else ""
            if not domain:
                return self._send_json(400, {"ok": False, "message": "hostname ไม่ถูกต้อง (ต้องเป็น app.โดเมน.com)"})
            api_token = str(data.get("api_token") or "").strip() or self.cfg.api_token
            if not api_token:
                return self._send_json(400, {"ok": False, "message": "ไม่พบ API token สำหรับแก้ DNS (ตั้งค่า Cloudflare ก่อน)"})
            api = _cf_api.CloudflareAPI(api_token)
            try:
                zone_id = api.get_zone_id(domain)
                conflict = api.get_record(zone_id, hostname, "A") or api.get_record(zone_id, hostname, "AAAA")
                if conflict:
                    return self._send_json(
                        400,
                        {
                            "ok": False,
                            "message": (
                                f"ชื่อ {hostname} มี record {conflict['type']} อยู่แล้ว (น่าจะใช้กับ DDNS) — "
                                "Cloudflare ไม่อนุญาตให้มี CNAME (tunnel) ซ้ำชื่อเดียวกับ A/AAAA — "
                                "ใช้คนละชื่อ (เช่น app.โดเมน.com) หรือลบ record เดิมก่อน"
                            ),
                        },
                    )
            except _cf_api.CloudflareError as exc:
                return self._send_json(400, {"ok": False, "message": f"ตรวจ DNS record ไม่ได้: {exc}"})

            # 2. ตั้ง ingress (public hostname) ใน tunnel config
            try:
                # อ่าน ingress เดิมมาก่อน (กันทับของเก่า)
                try:
                    current = api._request("GET", f"/accounts/{account_id}/cfd_tunnel/{tunnel_id}/configurations")
                    ingress = ((current or {}).get("config") or {}).get("ingress", [])
                except _cf_api.CloudflareError:
                    ingress = []
                # ลบ rule เดิม (hostname+path เดียวกัน) แล้วเพิ่มใหม่
                ingress = [r for r in ingress if not (r.get("hostname") == hostname and (r.get("path") or "") == path)]
                # ลบ catch-all http_status:404 เดิม (rule ที่ไม่มี hostname) — จะเพิ่มใหม่ท้ายสุดเสมอ
                # (ถ้าไม่ลบ จะมี 404 ซ้ำ -> Cloudflare validation fail 1056: rule '' บัง rule หลัง)
                ingress = [r for r in ingress if r.get("hostname") or r.get("service", "") != "http_status:404"]
                rule = {"hostname": hostname, "service": service}
                if path:
                    rule["path"] = path
                ingress.append(rule)
                ingress.append({"service": "http_status:404"})
                api._request(
                    "PUT",
                    f"/accounts/{account_id}/cfd_tunnel/{tunnel_id}/configurations",
                    {"config": {"ingress": ingress}},
                )
            except _cf_api.CloudflareError as exc:
                return self._send_json(
                    400,
                    {"ok": False, "message": f"ตั้งค่า tunnel config ไม่ได้: {_tunnel_api_error(exc)}"},
                )

            # 3. สร้าง/แก้ CNAME record ชี้ไป tunnel
            try:
                existing = api.get_record(zone_id, hostname, "CNAME")
                cname_content = f"{tunnel_id}.cfargotunnel.com"
                if existing:
                    api.update_record(zone_id, existing["id"], cname_content, 1, True)
                    action = "อัปเดต"
                else:
                    api.create_record(zone_id, hostname, "CNAME", cname_content, 1, True)
                    action = "สร้าง"
            except _cf_api.CloudflareError as exc:
                return self._send_json(400, {"ok": False, "message": f"สร้าง DNS record ไม่ได้: {exc}"})

            return self._send_json(
                200,
                {
                    "ok": True,
                    "message": f"{action} record แล้ว: {hostname}{path} → {tunnel_id}.cfargotunnel.com (เข้าผ่าน https://{hostname}{path})",
                    "hostname": hostname,
                },
            )

        if self.path == "/tunnel/hostnames":
            from . import cloudflare_api as _cf_api

            try:
                data = json.loads(body)
            except ValueError:
                return self._send_json(400, {"ok": False, "message": "JSON ผิดรูปแบบ"})
            token = str(data.get("token") or "").strip()
            if not token:
                return self._send_json(400, {"ok": False, "message": "ไม่พบ tunnel token"})
            ids, error = _decode_tunnel_token(token)
            if error:
                return self._send_json(400, {"ok": False, "message": error})
            api_token = str(data.get("api_token") or "").strip() or self.cfg.api_token
            api = _cf_api.CloudflareAPI(api_token)
            try:
                result = api._request("GET", f"/accounts/{ids['account_id']}/cfd_tunnel/{ids['tunnel_id']}/configurations")
                ingress = ((result or {}).get("config") or {}).get("ingress", [])
            except _cf_api.CloudflareError as exc:
                return self._send_json(400, {"ok": False, "message": f"อ่าน tunnel config ไม่ได้: {_tunnel_api_error(exc)}"})
            hostnames = []
            for r in ingress:
                if not r.get("hostname"):
                    continue
                svc = r.get("service", "")
                protocol = svc.split("://")[0] if "://" in svc else "http"
                hostnames.append(
                    {
                        "hostname": r.get("hostname", ""),
                        "path": r.get("path", ""),
                        "service": svc,
                        "protocol": protocol,
                    }
                )
            return self._send_json(200, {"ok": True, "hostnames": hostnames})

        if self.path == "/tunnel/unbind":
            from . import cloudflare_api as _cf_api

            try:
                data = json.loads(body)
            except ValueError:
                return self._send_json(400, {"ok": False, "message": "JSON ผิดรูปแบบ"})
            token = str(data.get("token") or "").strip()
            hostname = str(data.get("hostname") or "").strip().rstrip(".")
            path = str(data.get("path") or "").strip()
            if path and not path.startswith("/"):
                path = "/" + path
            if not token:
                return self._send_json(400, {"ok": False, "message": "ไม่พบ tunnel token"})
            if not hostname:
                return self._send_json(400, {"ok": False, "message": "ไม่พบ hostname ที่จะลบ"})
            ids, error = _decode_tunnel_token(token)
            if error:
                return self._send_json(400, {"ok": False, "message": error})
            api_token = str(data.get("api_token") or "").strip() or self.cfg.api_token
            api = _cf_api.CloudflareAPI(api_token)
            try:
                result = api._request("GET", f"/accounts/{ids['account_id']}/cfd_tunnel/{ids['tunnel_id']}/configurations")
                ingress = ((result or {}).get("config") or {}).get("ingress", [])
                remaining = [
                    r for r in ingress
                    if not (r.get("hostname") == hostname and (r.get("path") or "") == path)
                ]
                if len(remaining) == len(ingress):
                    return self._send_json(400, {"ok": False, "message": f"ไม่พบ {hostname}{path} ใน tunnel config"})
                api._request(
                    "PUT",
                    f"/accounts/{ids['account_id']}/cfd_tunnel/{ids['tunnel_id']}/configurations",
                    {"config": {"ingress": remaining}},
                )
            except _cf_api.CloudflareError as exc:
                return self._send_json(400, {"ok": False, "message": f"ลบออกจาก tunnel config ไม่ได้: {_tunnel_api_error(exc)}"})
            # ลบ CNAME เฉพาะเมื่อไม่มี rule อื่นของ hostname นี้เหลืออยู่
            still_used = any(r.get("hostname") == hostname for r in remaining)
            if not still_used:
                domain = hostname.split(".", 1)[1] if "." in hostname else ""
                if domain:
                    try:
                        zone_id = api.get_zone_id(domain)
                        rec = api.get_record(zone_id, hostname, "CNAME")
                        if rec:
                            api.delete_record(zone_id, rec["id"])
                    except _cf_api.CloudflareError as exc:
                        return self._send_json(400, {"ok": False, "message": f"ลบ DNS record ไม่ได้: {exc}"})
            return self._send_json(
                200,
                {"ok": True, "message": f"เลิกผูก {hostname}{path} แล้ว" + ("" if still_used else " (ลบ CNAME record ด้วย)")},
            )

        if self.path == "/tunnel/sync":
            """ดึง hostname ที่ผูกจาก Cloudflare -> อัปเดต tunnel_hosts ใน config"""
            from . import cloudflare_api as _cf_api

            try:
                data = json.loads(body)
            except ValueError:
                return self._send_json(400, {"ok": False, "message": "JSON ผิดรูปแบบ"})
            token = str(data.get("token") or "").strip() or self.cfg.tunnel_token
            if not token:
                return self._send_json(400, {"ok": False, "message": "ไม่พบ tunnel token (ตั้งค่าในฟอร์ม/ wizard ก่อน)"})
            ids, error = _decode_tunnel_token(token)
            if error:
                return self._send_json(400, {"ok": False, "message": error})
            api = _cf_api.CloudflareAPI(self.cfg.api_token)
            try:
                result = api._request("GET", f"/accounts/{ids['account_id']}/cfd_tunnel/{ids['tunnel_id']}/configurations")
                ingress = ((result or {}).get("config") or {}).get("ingress", [])
            except _cf_api.CloudflareError as exc:
                return self._send_json(400, {"ok": False, "message": f"อ่าน tunnel config ไม่ได้: {_tunnel_api_error(exc)}"})
            hosts = []
            for r in ingress:
                if not r.get("hostname"):
                    continue
                svc = r.get("service", "")
                hosts.append(
                    {
                        "hostname": r.get("hostname", ""),
                        "path": r.get("path", ""),
                        "protocol": svc.split("://")[0] if "://" in svc else "http",
                        "service": svc,
                    }
                )
            payload = _cfg_to_dict(self.cfg)
            payload["tunnel"]["hosts"] = hosts
            ok, message = self.cfg.save_text(_dict_to_ini(payload))
            if not ok:
                return self._send_json(400, {"ok": False, "message": message})
            return self._send_json(200, {"ok": True, "message": f"ซิงค์แล้ว — บันทึก hostname {len(hosts)} รายการลง config", "hostnames": hosts})

        if self.path == "/tunnel/start":
            ok, message = _get_tunnel_mgr(self.server.config_path).start(self.cfg)
            return self._send_json(200 if ok else 400, {"ok": ok, "message": message})

        if self.path == "/tunnel/stop":
            ok, message = _get_tunnel_mgr(self.server.config_path).stop()
            return self._send_json(200 if ok else 400, {"ok": ok, "message": message})

        if self.path == "/tunnel/download":
            from . import tunnel as tunnel_mod

            ok, message = tunnel_mod.ensure_installed(self.cfg)
            return self._send_json(200 if ok else 400, {"ok": ok, "message": message})

        if self.path in ("/service/install", "/service/restart", "/service/uninstall", "/service/start", "/service/stop"):
            from . import service as service_mod

            if not _is_admin():
                return self._send_json(
                    400,
                    {
                        "ok": False,
                        "message": "ไม่มีสิทธิ์ admin — เปิด webui จาก cmd/exe ที่รันเป็น admin (หรือติดตั้งเป็น service แล้วควบคุมจากเว็บนี้)",
                    },
                )
            if self.path == "/service/install":
                if _in_service():
                    return self._send_json(
                        400,
                        {
                            "ok": False,
                            "message": (
                                "เว็บนี้รันใน service อยู่แล้ว — service กำลังทำงาน (ติดตั้งอยู่แล้ว ไม่ต้องติดตั้งใหม่) "
                                "ใช้ปุ่ม Restart แทน (ห้ามติดตั้งทับตัวเอง: จะลบ service ที่รันอยู่ทิ้งแล้วหยุดกลางคัน)"
                            ),
                        },
                    )
                if service_mod.service_status().get("installed"):
                    return self._send_json(400, {"ok": False, "message": "service ติดตั้งอยู่แล้ว — ใช้ปุ่ม Restart หรือถอนก่อนถ้าอยากติดตั้งใหม่"})
                try:
                    message = service_mod.install_service()
                except Exception as exc:
                    return self._send_json(400, {"ok": False, "message": f"ติดตั้งไม่ได้: {exc}"})
                return self._send_json(200, {"ok": True, "message": message + " — กด Restart service เพื่อเริ่ม"})
            if self.path == "/service/uninstall":
                svc = service_mod.service_status()
                if not svc.get("installed"):
                    return self._send_json(400, {"ok": False, "message": "ยังไม่ได้ติดตั้ง service"})
                if svc.get("state") in ("running", "starting", "stopping"):
                    return self._send_json(
                        400,
                        {
                            "ok": False,
                            "message": (
                                "service กำลังทำงาน — ถอนตอนนี้จะตัดการเชื่อมต่อหน้าเว็บนี้ทันที "
                                "(เพราะเว็บนี้รันใน service) — ใช้ uninstall.bat หรือรัน "
                                "dist\\cloudflare-ddns.exe stop แล้วตามด้วย remove แทน"
                            ),
                        },
                    )
                try:
                    message = service_mod.remove_service()
                except Exception as exc:
                    return self._send_json(400, {"ok": False, "message": f"ถอนไม่ได้: {exc}"})
                return self._send_json(200, {"ok": True, "message": message})
            if self.path == "/service/start":
                svc = service_mod.service_status()
                if not svc.get("installed"):
                    return self._send_json(400, {"ok": False, "message": "ยังไม่ได้ติดตั้ง service — กด 'ติดตั้ง service' ก่อน"})
                if svc.get("state") in ("running", "starting"):
                    return self._send_json(400, {"ok": False, "message": "service กำลังทำงานอยู่แล้ว"})
                try:
                    message = service_mod.start_service()
                except Exception as exc:
                    return self._send_json(400, {"ok": False, "message": f"เริ่มไม่ได้: {exc}"})
                return self._send_json(200, {"ok": True, "message": message})
            if self.path == "/service/stop":
                svc = service_mod.service_status()
                if not svc.get("installed"):
                    return self._send_json(400, {"ok": False, "message": "ยังไม่ได้ติดตั้ง service"})
                if _in_service():
                    return self._send_json(
                        400,
                        {
                            "ok": False,
                            "message": (
                                "เว็บนี้รันใน service — หยุดตอนนี้หน้าเว็บจะหายไปและไม่กลับมาเอง "
                                "(service หยุด = ไม่มีตัวเริ่มใหม่) — ให้ใช้คำสั่ง dist\\cloudflare-ddns.exe stop แทน"
                            ),
                        },
                    )
                try:
                    message = service_mod.stop_service()
                except Exception as exc:
                    return self._send_json(400, {"ok": False, "message": f"หยุดไม่ได้: {exc}"})
                return self._send_json(200, {"ok": True, "message": message})
            # restart: ต้องสั่งผ่าน process ภายนอก (cmd.exe) ทั้งชุด stop+start —
            # ถ้าเรียก stop จาก thread ในตัวเอง กระบวนการตายก่อน start รัน -> service ค้าง
            def _do_restart():
                import subprocess as _sp
                import time as _t

                _t.sleep(2)
                try:
                    sc = r"C:\Windows\System32\sc.exe"
                    cmd = (
                        f'"{sc}" stop {service_mod.SERVICE_NAME}'
                        f' & ping -n 3 127.0.0.1 >nul'
                        f' & "{sc}" start {service_mod.SERVICE_NAME}'
                    )
                    _sp.run(["cmd", "/c", cmd], capture_output=True, timeout=60)
                    log.info("restart service สำเร็จ (ผ่าน cmd/sc)")
                except Exception as exc:
                    log.warning("restart service ไม่ได้: %s", exc)

            if not service_mod.service_status().get("installed"):
                return self._send_json(400, {"ok": False, "message": "ยังไม่ได้ติดตั้ง service — กด 'ติดตั้ง service' ก่อน"})
            threading.Thread(target=_do_restart, daemon=True).start()
            return self._send_json(200, {"ok": True, "message": "กำลัง restart service — หน้าเว็บจะหลุดชั่วครู่ แล้วกลับมาเอง"})

        if self.path == "/ddns-run":
            """รันรอบ DDNS เลย (ไม่รอรอบถัดไป) — รันใน thread กัน handler ค้าง"""
            if _ddns_busy["running"]:
                return self._send_json(400, {"ok": False, "message": "กำลังตรวจรอบก่อนหน้าอยู่ ยังไม่เสร็จ — รอสักครู่แล้วลองใหม่"})
            _ddns_busy["running"] = True

            def _do_run():
                try:
                    engine = ddns.DDNSEngine(self.server.config_path)
                    engine.run_once()
                except Exception:
                    log.exception("webui: ตรวจ DDNS รอบนี้เลย error")
                finally:
                    _ddns_busy["running"] = False

            threading.Thread(target=_do_run, daemon=True).start()
            return self._send_json(200, {"ok": True, "message": "กำลังตรวจ DDNS — สถานะจะอัปเดตให้อัตโนมัติ"})

        if self.path == "/open-data-folder":
            import os

            path = config_mod.DEFAULT_DATA_DIR
            if _in_service():
                # รันใน service (SYSTEM) — startfile เปิด explorer ใน session 0 ที่ผู้ใช้มองไม่เห็น
                # -> ส่ง path กลับไปให้หน้าเว็บคัดลอก (JS จัดการคัดลอกให้อัตโนมัติ)
                return self._send_json(
                    200,
                    {
                        "ok": True,
                        "path": path,
                        "message": (
                            "เว็บนี้รันใน service — ไม่สามารถเปิดโฟลเดอร์จาก session ของคุณได้ "
                            f"คัดลอก path ให้แล้ว: {path} (กด Win+R → วาง → Enter)"
                        ),
                    },
                )
            try:
                os.startfile(path)
            except Exception as exc:
                return self._send_json(400, {"ok": False, "message": f"เปิดโฟลเดอร์ไม่ได้: {exc}"})
            return self._send_json(200, {"ok": True, "path": path, "message": f"เปิดโฟลเดอร์ข้อมูลแล้ว ({path})"})

        if self.path == "/save-config":
            try:
                data = json.loads(body)
            except ValueError:
                return self._send_json(400, {"ok": False, "message": "JSON ผิดรูปแบบ"})
            # เติม field ที่ client ไม่ได้ส่งจาก config ปัจจุบัน (กันบันทึกแล้วข้อมูลหาย
            # เช่น client/เวอร์ชันเก่า, wizard ที่ payload ไม่ครบ)
            if isinstance(data, dict):
                current = _cfg_to_dict(self.cfg)
                for section in ("cloudflare", "telegram", "tunnel"):
                    for key, value in current.get(section, {}).items():
                        data.setdefault(section, {}).setdefault(key, value)
            ini_text = _dict_to_ini(data)
            ok, message = self.cfg.save_text(ini_text)
            return self._send_json(200 if ok else 400, {"ok": ok, "message": message})

        if self.path == "/notify-test":
            notify = notifier.TelegramNotifier.from_config(self.cfg)
            if not notify.enabled:
                return self._send_json(400, {"ok": False, "message": "ยังไม่ได้ตั้งค่า Telegram ใน config"})
            ok, error = notify.send_raw("✅ ทดสอบการแจ้งเตือนจาก Cloudflare DDNS (Web UI)")
            return self._send_json(200 if ok else 500, {"ok": ok, "message": error or "ส่งสำเร็จ — ตรวจใน Telegram"})

        return self._send_json(404, {"ok": False, "message": "ไม่พบ path"})


class WebUI:
    def __init__(self, config_path=config_mod.DEFAULT_CONFIG_PATH, port=None, password=None, host=None):
        config_mod.migrate_legacy_data(config_path)
        self.config_path = config_path
        self.cfg = config_mod.Config(config_path)
        self.port = port or self.cfg.webui_port
        self.host = host or self.cfg.webui_host or "127.0.0.1"
        if password is not None:
            self.cfg.webui_password = password
        handler = type("Handler", (WebUIHandler,), {})
        try:
            self.server = ThreadingHTTPServer((self.host, self.port), handler)
        except OSError as exc:
            raise RuntimeError(
                f"เปิด Web UI ไม่ได้ — พอร์ต {self.port} ถูกใช้งานอยู่ ({exc}). "
                "อาจมี webui/service รันอยู่แล้ว — ปิดตัวนั้นก่อน หรือใช้พอร์ตอื่น (webui --port XXXX)"
            ) from exc
        self.server.cfg = self.cfg
        self.server.config_path = config_path
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def start(self):
        self.thread.start()
        log.info("Web UI เปิดที่ http://%s:%d (เข้าจากเครื่องนี้เท่านั้น)", self.host, self.port)

    def serve_forever(self):
        self.start()
        self.thread.join()

    def stop(self):
        self.server.shutdown()
