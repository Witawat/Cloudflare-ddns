"""จัดการ Cloudflare Tunnel (cloudflared): ดาวน์โหลด/เริ่ม/หยุด/สถานะ.

ใช้เมื่อต้องการให้บริการผ่าน Tunnel แทนการเปิดพอร์ต/พึ่ง IP โดยตรง
(เหมาะกับ CGNAT, ไม่อยากเปิดพอร์ต, หรือให้บริการเว็บผ่าน Cloudflare)
"""

import logging
import os
import platform
import shutil
import signal
import subprocess
import tarfile
import time
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from . import config as config_mod
from . import notifier

log = logging.getLogger("cloudflare-ddns")

DOWNLOAD_BASE_URL = "https://github.com/cloudflare/cloudflared/releases/latest/download/"

PID_FILE = "tunnel.pid"
TUNNEL_LOG = "tunnel.log"
# กันไฟล์ log บวม: ใหญ่เกินนี้ -> truncate เหลือท้าย (cloudflared เขียนต่อด้วย O_APPEND ไม่เสีย)
TUNNEL_LOG_MAX = 5 * 1024 * 1024
TUNNEL_LOG_KEEP = 1024 * 1024

_version_cache: Dict[str, Any] = {"time": 0.0, "version": ""}
_latest_cache: Dict[str, Any] = {"time": 0.0, "version": ""}


def latest_release() -> str:
    """เวอร์ชัน cloudflared ล่าสุดจาก GitHub releases (cache 6 ชม.).

    Returns:
        str: หมายเลขเวอร์ชันล่าสุด หรือ '' ถ้าเช็คไม่ได้
    """
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


def cloudflared_version(cfg: Optional["config_mod.Config"] = None) -> str:
    """เวอร์ชัน cloudflared (cache 5 นาที).

    Args:
        cfg: Config ที่อ่านแล้ว (ใช้หา path ของ cloudflared) — None = ค่า default

    Returns:
        str: เวอร์ชันที่อ่านได้ หรือ '' ถ้ายังไม่ติดตั้ง/อ่านไม่ได้
    """
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


def cloudflared_path(cfg: Optional["config_mod.Config"] = None) -> str:
    """หาตำแหน่ง cloudflared.exe (config ระบุเอง -> data dir ข้าง config -> default).

    Args:
        cfg: Config ที่อ่านแล้ว (None = ใช้ค่า default)

    Returns:
        str: path เต็มของ cloudflared.exe
    """
    if cfg and getattr(cfg, "cloudflared_path", "").strip():
        return cfg.cloudflared_path.strip()
    filename = "cloudflared.exe" if os.name == "nt" else "cloudflared"
    if cfg and getattr(cfg, "path", None):
        return os.path.join(config_mod.data_dir_for(cfg.path), filename)
    return os.path.join(config_mod.DEFAULT_DATA_DIR, filename)


def _download_asset():
    """คืน (ชื่อ asset, เป็น tgz หรือไม่) สำหรับระบบปัจจุบัน."""
    machine = platform.machine().lower()
    if os.name == "nt":
        arch = "386" if machine in ("x86", "i386", "i686") else "amd64"
        return f"cloudflared-windows-{arch}.exe", False
    if sys_platform() == "darwin":
        arch = "arm64" if machine in ("arm64", "aarch64") else "amd64"
        return f"cloudflared-darwin-{arch}.tgz", True
    raise RuntimeError("ดาวน์โหลด cloudflared อัตโนมัติรองรับ Windows และ macOS เท่านั้น")


def sys_platform():
    """แยกไว้เพื่อให้ unit test mock แพลตฟอร์มได้ง่าย."""
    import sys

    return sys.platform


def _pid_path(config_path: Optional[str] = None) -> str:
    """คืน path ของ tunnel.pid (อยู่ข้าง data dir)."""
    return os.path.join(config_mod.data_dir_for(config_path), PID_FILE)


def _log_path(config_path: Optional[str] = None) -> str:
    """คืน path ของ tunnel.log (อยู่ข้าง data dir)."""
    return os.path.join(config_mod.data_dir_for(config_path), TUNNEL_LOG)


def is_installed(cfg: Optional["config_mod.Config"] = None) -> bool:
    """cloudflared.exe ถูกติดตั้งแล้วหรือไม่.

    Args:
        cfg: Config ที่อ่านแล้ว (None = ใช้ค่า default)

    Returns:
        bool: True ถ้ามีไฟล์ cloudflared.exe
    """
    return os.path.isfile(cloudflared_path(cfg))


def ensure_installed(cfg: Optional["config_mod.Config"] = None) -> Tuple[bool, str]:
    """ดาวน์โหลด cloudflared ให้ตรง OS/CPU ถ้ายังไม่มี. คืน (ok, message).

    Args:
        cfg: Config ที่อ่านแล้ว (ใช้หา path) — None = ใช้ค่า default

    Returns:
        tuple[bool, str]: (สำเร็จหรือไม่, ข้อความผลลัพธ์)
    """
    path = cloudflared_path(cfg)
    if os.path.isfile(path):
        return True, f"มี cloudflared แล้ว ({path})"
    tmp = path + ".download"
    extracted = path + ".extract"
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        asset, is_archive = _download_asset()
        log.info("กำลังดาวน์โหลด cloudflared จาก GitHub...")
        request = urllib.request.Request(
            DOWNLOAD_BASE_URL + asset, headers={"User-Agent": config_mod.user_agent()}
        )
        with urllib.request.urlopen(request, timeout=120) as response, open(tmp, "wb") as handle:
            while True:
                chunk = response.read(65536)
                if not chunk:
                    break
                handle.write(chunk)
        if is_archive:
            with tarfile.open(tmp, "r:gz") as archive:
                member = next(
                    (item for item in archive.getmembers() if os.path.basename(item.name) == "cloudflared"),
                    None,
                )
                if member is None or not member.isfile():
                    raise OSError("ไม่พบไฟล์ cloudflared ใน archive")
                source = archive.extractfile(member)
                if source is None:
                    raise OSError("อ่านไฟล์ cloudflared จาก archive ไม่ได้")
                with source, open(extracted, "wb") as handle:
                    shutil.copyfileobj(source, handle)
            os.chmod(extracted, 0o755)
            os.replace(extracted, path)
            os.remove(tmp)
        else:
            os.replace(tmp, path)
        log.info("ดาวน์โหลด cloudflared สำเร็จ: %s", path)
        return True, f"ดาวน์โหลด cloudflared สำเร็จ ({path})"
    except Exception as exc:
        log.warning("ดาวน์โหลด cloudflared ไม่ได้: %s", exc)
        try:
            for leftover in (tmp, extracted):
                if os.path.isfile(leftover):
                    os.remove(leftover)
        except OSError:
            pass
        return False, f"ดาวน์โหลด cloudflared ไม่ได้: {exc}"


def _pid_alive(pid: Optional[int]) -> bool:
    """pid ยังมี process รันอยู่หรือไม่ (os.kill(pid, 0) — ไม่ฆ่าจริง).

    Args:
        pid: process id ที่จะตรวจ

    Returns:
        bool: True ถ้า process ยังอยู่ (หรือเป็นของคนอื่น admin)
    """
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


def _process_is_cloudflared(pid: int) -> bool:
    """เช็คว่า pid นั้นเป็น cloudflared จริงหรือไม่ (กัน kill ผิด process ตอน pid reuse).

    Args:
        pid: process id ที่จะตรวจ

    Returns:
        bool: True ถ้าเป็น cloudflared (หรือตรวจไม่ได้ — ถือว่าใช่)
    """
    try:
        if os.name == "nt":
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                capture_output=True,
                timeout=10,
                text=True,
            )
            name = (result.stdout or "").strip().split(",")[0].strip('"').lower()
            return name == "cloudflared.exe"
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "comm="],
            capture_output=True,
            timeout=10,
            text=True,
        )
        return os.path.basename((result.stdout or "").strip()).lower() == "cloudflared"
    except Exception:
        return True  # ตรวจไม่ได้ -> ถือว่าใช่ (รักษาพฤติกรรมเดิม)


class TunnelManager:
    """จัดการ cycle ชีวิตของ cloudflared: เริ่ม/หยุด/สถานะ/pid/log."""

    def __init__(self, config_path: Optional[str] = None) -> None:
        """สร้าง manager พร้อมอ่าน pid ล่าสุดจากไฟล์.

        Args:
            config_path: path ของ config.ini (ใช้หาตำแหน่ง pid/log)
        """
        self.config_path = config_path
        self._proc: Optional[subprocess.Popen] = None
        self._pid: Optional[int] = self._load_pid()

    def _load_pid(self) -> Optional[int]:
        """อ่าน pid จาก tunnel.pid.

        Returns:
            int | None: pid ที่อ่านได้ หรือ None ถ้าไม่มีไฟล์/ค่าผิด
        """
        try:
            with open(_pid_path(self.config_path), "r", encoding="utf-8") as handle:
                return int(handle.read().strip())
        except (OSError, ValueError):
            return None

    def _save_pid(self, pid: int) -> None:
        """เขียน pid ลง tunnel.pid แบบ atomic.

        Args:
            pid: process id ของ cloudflared
        """
        try:
            os.makedirs(config_mod.data_dir_for(self.config_path), exist_ok=True)
            tmp = _pid_path(self.config_path) + ".tmp"
            with open(tmp, "w", encoding="utf-8") as handle:
                handle.write(str(pid))
            os.replace(tmp, _pid_path(self.config_path))
        except OSError as exc:
            log.warning("บันทึก tunnel pid ไม่ได้: %s", exc)

    def _clear_pid(self) -> None:
        """ลบ tunnel.pid (ตอนหยุด)."""
        try:
            if os.path.isfile(_pid_path(self.config_path)):
                os.remove(_pid_path(self.config_path))
        except OSError:
            pass

    def status(self, cfg: "config_mod.Config") -> Dict[str, Any]:
        """สถานะปัจจุบันของ tunnel.

        Args:
            cfg: Config ที่อ่านแล้ว

        Returns:
            dict: สถานะ — enabled/installed/running/pid/path/version/log_exists/last_error
        """
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

    def log_tail(self, limit: int = 30, max_bytes: int = 16384, only_errors: bool = False) -> str:
        """อ่าน tail ของ cloudflared log — จำกัดขนาด (กันไฟล์ใหญ่) + กรองเฉพาะ error ได้.

        Args:
            limit: จำนวนบรรทัดสูงสุดที่จะคืน
            max_bytes: ขนาดสูงสุดที่จะอ่านจากท้ายไฟล์ (bytes)
            only_errors: True = อ่านท้าย 64KB แล้วกรองเฉพาะบรรทัด level error/warn

        Returns:
            str: ข้อความ log ที่อ่านได้ (หรือ '' เมื่ออ่านไม่ได้)

        หมายเหตุ:
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
                err_lines: List[str] = []
                for line in lines:
                    low = line.lower()
                    if ('"level":"error"' in low or '"level":"warn"' in low
                            or "err" in low or "unable" in low or "failed" in low or "invalid" in low):
                        err_lines.append(line)
                return "".join(err_lines[-limit:])
            return "".join(lines[-limit:])
        except OSError:
            return ""

    def last_error(self, limit: int = 60) -> str:
        """หาบรรทัด error ล่าสุดจาก cloudflared log (เช่น token ผิด/เชื่อมต่อไม่ได้).

        Args:
            limit: จำนวนบรรทัดที่จะตรวจ (ผ่าน log_tail)

        Returns:
            str: ข้อความ error บรรทัดล่าสุด (จำกัด 300 ตัวอักษร) หรือ ''
        """
        tail = self.log_tail(limit=limit)
        if not tail:
            return ""
        keywords = ("ERR", "ERROR", "Unable", "Invalid", "failed", "Failed", "error", "Error")
        last = ""
        for line in tail.splitlines():
            if any(k in line for k in keywords):
                last = line.strip()
        return last[:300]

    def start(self, cfg: "config_mod.Config") -> Tuple[bool, str]:
        """เริ่ม cloudflared tunnel run --token.

        ถ้ามี cloudflared เก่าค้าง (pid ค้าง/service restart ไม่ทันตาย) -> ฆ่าทิ้งก่อน
        แล้วเริ่มใหม่ — กันสถานะ running ค้างทำให้ tunnel ไม่กลับมาหลัง restart service.

        Args:
            cfg: Config ที่อ่านแล้ว

        Returns:
            tuple[bool, str]: (เริ่มสำเร็จหรือไม่, ข้อความผลลัพธ์)
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
        popen_kwargs = {
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }
        if os.name == "nt":
            popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        else:
            popen_kwargs["start_new_session"] = True
        try:
            self._proc = subprocess.Popen(args, **popen_kwargs)
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

    def _find_stale_cloudflared(self, cfg: Optional["config_mod.Config"] = None) -> List[int]:
        """หา pid ของ cloudflared ที่ค้างอยู่ (pid ไฟล์ + process list).

        Args:
            cfg: Config ที่อ่านแล้ว (ไม่ค่อยใช้ — กัน forward compat)

        Returns:
            list[int]: list ของ pid ที่ควรฆ่าก่อนเริ่มใหม่
        """
        found: List[int] = []
        # 1. pid จากไฟล์ (ถ้ายัง alive และเป็น cloudflared จริง)
        pid = self._load_pid()
        if pid and _pid_alive(pid) and _process_is_cloudflared(pid):
            found.append(pid)
        # 2. Windows รุ่นเดิมค้นทุก process; macOS จำกัดเฉพาะ pid ที่โปรแกรมบันทึกไว้
        # เพื่อไม่ฆ่า cloudflared instance อื่นของผู้ใช้โดยไม่ตั้งใจ
        if os.name != "nt":
            return found
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

    def _kill_pid(self, pid: int) -> None:
        """หยุด process ตาม pid (เรียกหลังตรวจว่าเป็น cloudflared แล้วเท่านั้น).

        Args:
            pid: process id ที่จะ kill
        """
        try:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/F"],
                    capture_output=True,
                    timeout=10,
                )
            else:
                os.kill(pid, signal.SIGTERM)
                deadline = time.time() + 3
                while _pid_alive(pid) and time.time() < deadline:
                    time.sleep(0.1)
                if _pid_alive(pid):
                    os.kill(pid, signal.SIGKILL)
        except Exception as exc:
            log.warning("หยุด pid %s ไม่ได้: %s", pid, exc)

    def stop(self, wait: bool = True) -> Tuple[bool, str]:
        """หยุด cloudflared.

        Args:
            wait: True = รอ process ตายจริง (สูงสุด ~6 วิ) ก่อนล้าง pid —
                กัน restart ไวเกินแล้ว cloudflared เก่ายังค้าง -> tunnel ซ้อน/ไม่กลับมา

        Returns:
            tuple[bool, str]: (สำเร็จหรือไม่, ข้อความผลลัพธ์)
        """
        stopped = False
        proc_pid = self._proc.pid if self._proc is not None else None
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
        # ฆ่า process ที่เราสร้างเองถ้ายังไม่ตาย (self._proc.pid — เชื่อถือได้ว่าเป็น cloudflared)
        if proc_pid and _pid_alive(proc_pid):
            self._kill_pid(proc_pid)
            stopped = True
        if self._proc is not None:
            self._proc = None
        # pid จากไฟล์ (รอบก่อน/process อื่น) — ตรวจก่อน kill กัน pid reuse ผิดตัว
        if _pid_alive(self._pid):
            if not _process_is_cloudflared(self._pid):
                log.warning(
                    "pid %s ไม่ใช่ cloudflared (pid reuse?) — ข้าม taskkill กัน kill ผิด process",
                    self._pid,
                )
            else:
                self._kill_pid(self._pid)
                stopped = True
        if wait and stopped:
            # รอให้ process ตายจริง (กัน service restart ไวเกิน -> เก่ายังค้าง)
            deadline = time.time() + 6
            while time.time() < deadline:
                if not _pid_alive(self._pid) and not (proc_pid and _pid_alive(proc_pid)):
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

    def _notify(self, cfg: "config_mod.Config", event: str, text: str) -> None:
        """ส่งแจ้งเตือน Telegram (ถ้าตั้งค่าไว้) — ไม่ล้มเหลวถ้า Telegram พัง.

        Args:
            cfg: Config ที่อ่านแล้ว
            event: ประเภทเหตุการณ์ (EVENT_START/EVENT_STOP ฯลฯ)
            text: ข้อความที่จะส่ง
        """
        try:
            from .notifier import TelegramNotifier

            notifier_obj = TelegramNotifier.from_config(cfg)
            notifier_obj.notify(event, text)
            notifier_obj.flush()
        except Exception as exc:
            log.warning("แจ้งเตือน tunnel ไม่ได้: %s", exc)
