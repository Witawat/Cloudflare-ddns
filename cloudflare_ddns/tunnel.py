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

log = logging.getLogger("cloudflare-ddns")

DOWNLOAD_URL = (
    "https://github.com/cloudflare/cloudflared/releases/latest/download/"
    "cloudflared-windows-amd64.exe"
)

PID_FILE = "tunnel.pid"

_version_cache = {"time": 0.0, "version": ""}


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
    except Exception:
        pass
    return ""


def cloudflared_path(cfg=None):
    if cfg and getattr(cfg, "cloudflared_path", "").strip():
        return cfg.cloudflared_path.strip()
    return os.path.join(config_mod.DEFAULT_DATA_DIR, "cloudflared.exe")


def _pid_path():
    return os.path.join(config_mod.DEFAULT_DATA_DIR, PID_FILE)


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
            DOWNLOAD_URL, headers={"User-Agent": "cloudflare-ddns-updater/1.0"}
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


class TunnelManager:
    def __init__(self):
        self._proc = None
        self._pid = self._load_pid()

    def _load_pid(self):
        try:
            with open(_pid_path(), "r", encoding="utf-8") as handle:
                return int(handle.read().strip())
        except (OSError, ValueError):
            return None

    def _save_pid(self, pid):
        try:
            os.makedirs(config_mod.DEFAULT_DATA_DIR, exist_ok=True)
            with open(_pid_path(), "w", encoding="utf-8") as handle:
                handle.write(str(pid))
        except OSError as exc:
            log.warning("บันทึก tunnel pid ไม่ได้: %s", exc)

    def _clear_pid(self):
        try:
            if os.path.isfile(_pid_path()):
                os.remove(_pid_path())
        except OSError:
            pass

    def status(self, cfg):
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
        }

    def start(self, cfg):
        """เริ่ม cloudflared tunnel run --token คืน (ok, message)."""
        if not getattr(cfg, "tunnel_enabled", False):
            return False, "ปิดใช้งาน tunnel ใน config (tunnel_enabled = true)"
        if self.status(cfg)["running"]:
            return True, f"tunnel รันอยู่แล้ว (pid {self.status(cfg)['pid']})"
        if not getattr(cfg, "tunnel_token", "").strip():
            return False, "ไม่พบ tunnel_token (สร้างได้ที่ Zero Trust → Networks → Tunnels)"
        ok, message = ensure_installed(cfg)
        if not ok:
            return False, message
        args = [
            cloudflared_path(cfg),
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
            try:
                subprocess.run(
                    ["taskkill", "/PID", str(self._pid), "/F"],
                    capture_output=True,
                    timeout=10,
                )
                stopped = True
            except Exception:
                pass
        self._clear_pid()
        self._pid = None
        if stopped:
            log.info("หยุด Cloudflare Tunnel แล้ว")
            return True, "หยุด tunnel แล้ว"
        return True, "tunnel ไม่ได้รันอยู่"
