"""จัดการ Cloudflare Tunnel (cloudflared): ดาวน์โหลด/เริ่ม/หยุด/สถานะ.

ใช้เมื่อต้องการให้บริการผ่าน Tunnel แทนการเปิดพอร์ต/พึ่ง IP โดยตรง
(เหมาะกับ CGNAT, ไม่อยากเปิดพอร์ต, หรือให้บริการเว็บผ่าน Cloudflare)
"""

import logging
import os
import subprocess
import time
import urllib.request

from . import config as config_mod
from . import notifier

log = logging.getLogger("cloudflare-ddns")

DOWNLOAD_URL = (
    "https://github.com/cloudflare/cloudflared/releases/latest/download/"
    "cloudflared-windows-amd64.exe"
)

PID_FILE = "tunnel.pid"
TUNNEL_LOG = "tunnel.log"

_version_cache = {"time": 0.0, "version": ""}
_latest_cache = {"time": 0.0, "version": ""}


def latest_release():
    """เวอร์ชัน cloudflared ล่าสุดจาก GitHub releases (cache 6 ชม.) — '' ถ้าเช็คไม่ได้"""
    import json

    now = time.time()
    if _latest_cache["version"] and now - _latest_cache["time"] < 6 * 3600:
        return _latest_cache["version"]
    try:
        request = urllib.request.Request(
            "https://api.github.com/repos/cloudflare/cloudflared/releases/latest",
            headers={
                "User-Agent": config_mod.user_agent(),
                "Accept": "application/vnd.github+json",
            },
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8", "replace"))
        tag = str(data.get("tag_name", "")).lstrip("v")
        if tag:
            _latest_cache.update(time=now, version=tag)
            return tag
    except Exception as exc:
        if now - _latest_cache["time"] > 600:
            _latest_cache["time"] = now
            log.warning("เช็คเวอร์ชัน cloudflared ล่าสุดไม่ได้: %s", exc)
    return ""


def cloudflared_version(cfg=None):
    """เวอร์ชัน cloudflared (cache 5 นาที) — คืน '' ถ้ายังไม่ติดตั้ง/อ่านไม่ได้"""
    now = time.time()
    if _version_cache["version"] and now - _version_cache["time"] < 300:
        return _version_cache["version"]
    path = cloudflared_path(cfg)
    if not os.path.isfile(path):
        return ""
    try:
        result = subprocess.run(
            [path, "--version"], capture_output=True, timeout=10, text=True
        )
        text = (result.stdout or result.stderr or "").strip()
        for part in text.split():
            token = part.strip(",;")
            if token[:1].isdigit():
                _version_cache.update(time=now, version=token)
                return token
        # อ่านได้แต่หาเวอร์ชันไม่เจอ — log ครั้งเดียวต่อ 10 นาที
        if now - _version_cache["time"] > 600:
            _version_cache["time"] = now
            log.warning("อ่านเวอร์ชัน cloudflared ไม่ได้: %r", text[:120])
    except Exception as exc:
        if now - _version_cache["time"] > 600:
            _version_cache["time"] = now
            log.warning("อ่านเวอร์ชัน cloudflared ไม่ได้: %s", exc)
    return ""


def cloudflared_path(cfg=None):
    if cfg and getattr(cfg, "cloudflared_path", "").strip():
        return cfg.cloudflared_path.strip()
    if cfg and getattr(cfg, "path", None):
        return os.path.join(config_mod.data_dir_for(cfg.path), "cloudflared.exe")
    return os.path.join(config_mod.DEFAULT_DATA_DIR, "cloudflared.exe")


def _pid_path(config_path=None):
    return os.path.join(config_mod.data_dir_for(config_path), PID_FILE)


def _log_path(config_path=None):
    return os.path.join(config_mod.data_dir_for(config_path), TUNNEL_LOG)


def is_installed(cfg=None):
    return os.path.isfile(cloudflared_path(cfg))


def ensure_installed(cfg=None):
    """ดาวน์โหลด cloudflared.exe (Windows amd64) ถ้ายังไม่มี. คืน (ok, message)."""
    path = cloudflared_path(cfg)
    if os.path.isfile(path):
        return True, f"มี cloudflared แล้ว ({path})"
    tmp = path + ".download"
    try:
        log.info("กำลังดาวน์โหลด cloudflared จาก GitHub...")
        request = urllib.request.Request(
            DOWNLOAD_URL, headers={"User-Agent": config_mod.user_agent()}
        )
        with urllib.request.urlopen(request, timeout=120) as response, open(tmp, "wb") as handle:
            while True:
                chunk = response.read(65536)
                if not chunk:
                    break
                handle.write(chunk)
        os.replace(tmp, path)
        log.info("ดาวน์โหลด cloudflared สำเร็จ: %s", path)
        return True, f"ดาวน์โหลด cloudflared สำเร็จ ({path})"
    except Exception as exc:
        log.warning("ดาวน์โหลด cloudflared ไม่ได้: %s", exc)
        try:
            if os.path.isfile(tmp):
                os.remove(tmp)
        except OSError:
            pass
        return False, f"ดาวน์โหลด cloudflared ไม่ได้: {exc}"


def _pid_alive(pid):
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        # process มีอยู่แต่เป็นของ process อื่น (admin) — นับว่ายังรันอยู่
        return True
    except OSError:
        return False
    except Exception:
        return False


def _process_is_cloudflared(pid):
    """เช็คว่า pid นั้นเป็น cloudflared.exe จริงหรือไม่ (กัน kill ผิด process ตอน pid reuse)"""
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True,
            timeout=10,
            text=True,
        )
        name = (result.stdout or "").strip().split(",")[0].strip('"').lower()
        return name == "cloudflared.exe"
    except Exception:
        return True  # ตรวจไม่ได้ -> ถือว่าใช่ (รักษาพฤติกรรมเดิม)


class TunnelManager:
    def __init__(self, config_path=None):
        self.config_path = config_path
        self._proc = None
        self._pid = self._load_pid()

    def _load_pid(self):
        try:
            with open(_pid_path(self.config_path), "r", encoding="utf-8") as handle:
                return int(handle.read().strip())
        except (OSError, ValueError):
            return None

    def _save_pid(self, pid):
        try:
            os.makedirs(config_mod.data_dir_for(self.config_path), exist_ok=True)
            tmp = _pid_path(self.config_path) + ".tmp"
            with open(tmp, "w", encoding="utf-8") as handle:
                handle.write(str(pid))
            os.replace(tmp, _pid_path(self.config_path))
        except OSError as exc:
            log.warning("บันทึก tunnel pid ไม่ได้: %s", exc)

    def _clear_pid(self):
        try:
            if os.path.isfile(_pid_path(self.config_path)):
                os.remove(_pid_path(self.config_path))
        except OSError:
            pass

    def status(self, cfg):
        # re-read pid จากไฟล์ทุกครั้ง — cloudflared อาจถูกเริ่ม/หยุดโดย process อื่น
        # (service restart / webui รอบอื่น / command line) — กันเห็นสถานะค้างเก่า
        self._pid = self._load_pid()
        running = False
        pid = self._pid
        if self._proc is not None and self._proc.poll() is None:
            running = True
            pid = self._proc.pid
        elif _pid_alive(self._pid):
            running = True
        return {
            "enabled": bool(getattr(cfg, "tunnel_enabled", False)),
            "installed": is_installed(cfg),
            "running": running,
            "pid": pid if running else None,
            "path": cloudflared_path(cfg),
            "version": cloudflared_version(cfg),
            "log_exists": os.path.isfile(_log_path(self.config_path)),
            "last_error": self.last_error(),
        }

    def log_tail(self, limit=30, max_bytes=4096):
        """อ่าน tail ของ cloudflared log (ท้ายไฟล์ max_bytes — กันอ่านไฟล์ใหญ่ทั้งไฟล์)."""
        path = _log_path(self.config_path)
        try:
            size = os.path.getsize(path)
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                if size > max_bytes:
                    handle.seek(size - max_bytes)
                    # ตัดบรรทัดแรกที่อาจขาดครึ่ง (ลากไปขึ้นบรรทัดใหม่)
                    handle.readline()
                lines = handle.readlines()
            return "".join(lines[-limit:])
        except OSError:
            return ""

    def last_error(self, limit=60):
        """หาบรรทัด error ล่าสุดจาก cloudflared log (เช่น token ผิด/เชื่อมต่อไม่ได้)."""
        tail = self.log_tail(limit=limit)
        if not tail:
            return ""
        keywords = ("ERR", "ERROR", "Unable", "Invalid", "failed", "Failed", "error", "Error")
        last = ""
        for line in tail.splitlines():
            if any(k in line for k in keywords):
                last = line.strip()
        return last[:300]

    def start(self, cfg):
        """เริ่ม cloudflared tunnel run --token คืน (ok, message)."""
        if not getattr(cfg, "tunnel_enabled", False):
            return False, "ปิดใช้งาน tunnel ใน config (tunnel_enabled = true)"
        if self.status(cfg)["running"]:
            return True, f"tunnel รันอยู่แล้ว (pid {self.status(cfg)['pid']})"
        if not getattr(cfg, "tunnel_token", "").strip():
            return False, "ไม่พบ tunnel_token (สร้างได้ที่ Zero Trust → Networks → Tunnels)"
        was_installed = is_installed(cfg)
        ok, message = ensure_installed(cfg)
        if not ok:
            return False, message
        if not was_installed:
            self._notify(
                cfg,
                notifier.EVENT_START,
                f"⬇️ ดาวน์โหลด cloudflared สำเร็จ (เวอร์ชัน {cloudflared_version(cfg) or '?'})",
            )
        args = [
            cloudflared_path(cfg),
            # --logfile/--loglevel เป็น global flag — ต้องอยู่ก่อน subcommand tunnel run
            "--logfile",
            _log_path(self.config_path),
            "--loglevel",
            "info",
            "tunnel",
            "run",
            "--token",
            cfg.tunnel_token.strip(),
        ]
        try:
            self._proc = subprocess.Popen(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except OSError as exc:
            return False, f"เริ่ม cloudflared ไม่ได้: {exc}"
        self._save_pid(self._proc.pid)
        log.info("เริ่ม Cloudflare Tunnel แล้ว (pid %s)", self._proc.pid)
        hosts = getattr(cfg, "tunnel_hosts", [])
        lines = [f"🌐 Tunnel เริ่มทำงาน (pid {self._proc.pid})"]
        if hosts:
            lines.append("")
            lines.append(f"ผูก {len(hosts)} hostname:")
            for host in hosts:
                name = host.get("hostname", "") + host.get("path", "")
                lines.append(f"• {name} → {host.get('service', '')}")
        else:
            lines.append("")
            lines.append("ยังไม่มี hostname ที่ผูก (ตั้งในเว็บ: การ์ด Cloudflare Tunnel)")
        self._notify(cfg, notifier.EVENT_START, "\n".join(lines))
        return True, f"เริ่ม tunnel แล้ว (pid {self._proc.pid})"

    def stop(self):
        """หยุด cloudflared คืน (ok, message)."""
        stopped = False
        if self._proc is not None and self._proc.poll() is None:
            try:
                self._proc.terminate()
                stopped = True
            except OSError:
                pass
            self._proc = None
        if _pid_alive(self._pid):
            if not _process_is_cloudflared(self._pid):
                log.warning(
                    "pid %s ไม่ใช่ cloudflared (pid reuse?) — ข้าม taskkill กัน kill ผิด process",
                    self._pid,
                )
            else:
                try:
                    subprocess.run(
                        ["taskkill", "/PID", str(self._pid), "/F"],
                        capture_output=True,
                        timeout=10,
                    )
                    stopped = True
                except Exception as exc:
                    log.warning("taskkill cloudflared (pid %s) ไม่ได้: %s", self._pid, exc)
        self._clear_pid()
        self._pid = None
        if stopped:
            log.info("หยุด Cloudflare Tunnel แล้ว")
            self._notify(
                config_mod.Config(self.config_path), notifier.EVENT_STOP, "🌐 Tunnel หยุดทำงาน"
            )
            return True, "หยุด tunnel แล้ว"
        return True, "tunnel ไม่ได้รันอยู่"

    def _notify(self, cfg, event, text):
        """ส่งแจ้งเตือน Telegram (ถ้าตั้งค่าไว้) — ไม่ล้มเหลวถ้า Telegram พัง"""
        try:
            from .notifier import TelegramNotifier

            notifier_obj = TelegramNotifier.from_config(cfg)
            notifier_obj.notify(event, text)
            notifier_obj.flush()
        except Exception as exc:
            log.warning("แจ้งเตือน tunnel ไม่ได้: %s", exc)
