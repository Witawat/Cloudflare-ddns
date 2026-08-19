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
# กันไฟล์ log บวม: ใหญ่เกินนี้ -> truncate เหลือท้าย (cloudflared เขียนต่อด้วย O_APPEND ไม่เสีย)
TUNNEL_LOG_MAX = 5 * 1024 * 1024
TUNNEL_LOG_KEEP = 1024 * 1024

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

    def log_tail(self, limit=30, max_bytes=16384, only_errors=False):
        """อ่าน tail ของ cloudflared log — จำกัดขนาด (กันไฟล์ใหญ่) + กรองเฉพาะ error ได้.

        - ไฟล์ > TUNNEL_LOG_MAX -> truncate เหลือ TUNNEL_LOG_KEEP (กันบวม ขณะ cloudflared เขียนต่อ)
        - only_errors=True -> อ่านท้าย 64KB แล้วกรองเฉพาะบรรทัด level error/warn
        """
        path = _log_path(self.config_path)
        try:
            size = os.path.getsize(path)
        except OSError:
            return ""
        # rotation กันบวม: ตัดเหลือท้าย (เขียนทับ — cloudflared ใช้ O_APPEND ต่อท้ายใหม่ได้)
        try:
            if size > TUNNEL_LOG_MAX:
                with open(path, "r", encoding="utf-8", errors="replace") as handle:
                    handle.seek(size - TUNNEL_LOG_KEEP)
                    handle.readline()
                    tail_text = handle.read()
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(tail_text)
                size = len(tail_text.encode("utf-8", "replace"))
        except OSError:
            pass
        try:
            read_bytes = 65536 if only_errors else max_bytes
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                if size > read_bytes:
                    handle.seek(size - read_bytes)
                    handle.readline()
                lines = handle.readlines()
            if only_errors:
                # cloudflared log เป็น JSON ต่อบรรทัด — กรอง level error/warn + ข้อความ error ตรง
                err_lines = []
                for line in lines:
                    low = line.lower()
                    if ('"level":"error"' in low or '"level":"warn"' in low
                            or "err" in low or "unable" in low or "failed" in low or "invalid" in low):
                        err_lines.append(line)
                return "".join(err_lines[-limit:])
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
        """เริ่ม cloudflared tunnel run --token คืน (ok, message).

        ถ้ามี cloudflared เก่าค้าง (pid ค้าง/service restart ไม่ทันตาย) -> ฆ่าทิ้งก่อน
        แล้วเริ่มใหม่ — กันสถานะ running ค้างทำให้ tunnel ไม่กลับมาหลัง restart service
        """
        if not getattr(cfg, "tunnel_enabled", False):
            return False, "ปิดใช้งาน tunnel ใน config (tunnel_enabled = true)"
        # ฆ่า cloudflared เก่าที่ค้างทุกตัว (pid ไฟล์ + process จริง) ก่อนเริ่มใหม่
        # — เดิม return "รันอยู่แล้ว" ทิ้งไว้ -> restart service แล้ว tunnel ไม่กลับมา
        stale = self._find_stale_cloudflared(cfg)
        if stale:
            log.warning("พบ cloudflared ค้าง %s ตัว — ฆ่าก่อนเริ่มใหม่: %s", len(stale), stale)
            for pid in stale:
                self._kill_pid(pid)
            time.sleep(1.0)
        if not getattr(cfg, "tunnel_token", "").strip():
            return False, "ไม่พบ tunnel_token (สร้างได้ที่ Zero Trust → Networks → Tunnels)"
        was_installed = is_installed(cfg)
        ok, message = ensure_installed(cfg)
        if not ok:
            return False, message
        # ลบ log เก่าของรอบก่อน (cloudflared append ต่อไฟล์) — กันดู log เก่าเข้าใจผิดว่าเป็นรอบนี้
        try:
            if os.path.isfile(_log_path(self.config_path)):
                os.remove(_log_path(self.config_path))
        except OSError:
            pass
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
        # เลือกโปรโตคอลเชื่อม Cloudflare (กัน QUIC/UDP ถูกบล็อก -> ใช้ http2 แทน)
        protocol = str(getattr(cfg, "tunnel_protocol", "") or "").strip().lower()
        if protocol in ("quic", "http2"):
            args.extend(["--protocol", protocol])
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
        log.info("เริ่ม Cloudflare Tunnel แล้ว (pid %s, protocol=%s)", self._proc.pid, protocol or "auto")
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

    def _find_stale_cloudflared(self, cfg=None):
        """หา pid ของ cloudflared.exe ที่ค้างอยู่ (pid ไฟล์ + tasklist) —
        คืน list ของ pid ที่ควรฆ่าก่อนเริ่มใหม่"""
        found = []
        # 1. pid จากไฟล์ (ถ้ายัง alive และเป็น cloudflared จริง)
        pid = self._load_pid()
        if pid and _pid_alive(pid) and _process_is_cloudflared(pid):
            found.append(pid)
        # 2. tasklist หา cloudflared.exe ที่รันอยู่ (กัน pid reuse/ซ่อน)
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq cloudflared.exe", "/FO", "CSV", "/NH"],
                capture_output=True,
                timeout=10,
                text=True,
            )
            for line in (result.stdout or "").splitlines():
                parts = [p.strip().strip('"') for p in line.split(",")]
                if len(parts) >= 2 and parts[0].lower() == "cloudflared.exe" and parts[1].isdigit():
                    p = int(parts[1])
                    if p not in found and p != (self._proc.pid if self._proc else None):
                        found.append(p)
        except Exception:
            pass
        return found

    def _kill_pid(self, pid):
        """taskkill ตาม pid (ไม่ตรวจว่าเป็น cloudflared ซ้ำ — เรียกจาก _find_stale เท่านั้น)"""
        try:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/F"],
                capture_output=True,
                timeout=10,
            )
        except Exception as exc:
            log.warning("taskkill pid %s ไม่ได้: %s", pid, exc)

    def stop(self, wait=True):
        """หยุด cloudflared คืน (ok, message).

        wait=True (default): รอ process ตายจริง (สูงสุด ~6 วิ) ก่อนล้าง pid —
        กัน restart ไวเกินแล้ว cloudflared เก่ายังค้าง -> tunnel ซ้อน/ไม่กลับมา
        """
        stopped = False
        if self._proc is not None and self._proc.poll() is None:
            try:
                self._proc.terminate()
                stopped = True
            except OSError:
                pass
            if wait:
                try:
                    self._proc.wait(timeout=6)
                except Exception:
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
        if wait and stopped:
            # รอให้ process ตายจริง (กัน service restart ไวเกิน -> เก่ายังค้าง)
            deadline = time.time() + 6
            while time.time() < deadline:
                if not _pid_alive(self._pid):
                    break
                time.sleep(0.5)
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
