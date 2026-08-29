"""จัดการ background service: Windows Service (pywin32) และ macOS LaunchAgent."""

import logging
import os
import plistlib
import signal
import subprocess
import sys
import threading
import time
from logging.handlers import TimedRotatingFileHandler
from typing import Any, Dict, Optional

from . import config as config_mod
from . import ddns

SERVICE_NAME = "CloudflareDDNS"
SERVICE_DISPLAY_NAME = "Cloudflare DDNS Updater"
SERVICE_DESCRIPTION = (
    "ตรวจหา IP สาธารณะ (IPv4/IPv6) แล้วอัปเดต DNS record บน Cloudflare "
    "โดยอัตโนมัติเมื่อ IP เปลี่ยน"
)
LAUNCHD_LABEL = "com.makerwitawat.cloudflare-ddns"

log = logging.getLogger("cloudflare-ddns")


def setup_file_logging(log_dir: Optional[str] = None, detail: bool = False) -> None:
    """log ไปไฟล์รายวัน (ใช้ทั้งตอน run foreground และตอนเป็น service).

    Args:
        log_dir: โฟลเดอร์เก็บไฟล์ log (None = ค่า default)
        detail: True = ทุกบรรทัดมี pid + ระดับ INFO ละเอียดขึ้น (ใช้หาสาเหตุ —
            เช่น heartbeat เบิ้ล) — ปิด default (log สะอาด)
    """
    log_dir = log_dir or config_mod.DEFAULT_LOG_DIR
    os.makedirs(log_dir, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if detail:
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] pid=%(process)d %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    for handler in list(root.handlers):
        if isinstance(handler, TimedRotatingFileHandler):
            root.removeHandler(handler)
    handler = TimedRotatingFileHandler(
        os.path.join(log_dir, "cloudflare-ddns.log"),
        when="midnight",
        backupCount=14,
        encoding="utf-8",
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)


def _make_service_class() -> type:
    """สร้างคลาส service แบบ lazy เพื่อให้ import ได้แม้ยังไม่มี pywin32.

    Returns:
        type: คลาส CloudflareDDNSService (subclass ของ ServiceFramework)

    Raises:
        ImportError: ถ้าไม่มี pywin32
    """
    try:
        import win32service
        import win32serviceutil
    except ImportError as exc:
        raise ImportError(
            "ไม่พบ pywin32 รัน 'python -m pip install pywin32' ก่อน"
        ) from exc

    class CloudflareDDNSService(win32serviceutil.ServiceFramework):
        _svc_name_ = SERVICE_NAME
        _svc_display_name_ = SERVICE_DISPLAY_NAME
        _svc_description_ = SERVICE_DESCRIPTION

        def __init__(self, args) -> None:
            super().__init__(args)
            self._stop_event = threading.Event()

        def SvcStop(self) -> None:
            """SCM สั่งหยุด — ตั้ง stop event ให้ loop หยุดเอง."""
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            self._stop_event.set()

        def _start_tunnel_async(self, tunnel_mgr: Any, cfg: "config_mod.Config") -> None:
            """เริ่ม tunnel ใน thread แยก (ไม่บล็อก SCM timeout 30 วิ).

            Args:
                tunnel_mgr: TunnelManager instance
                cfg: Config ที่อ่านแล้ว
            """
            try:
                ok, message = tunnel_mgr.start(cfg)
                log.info("Cloudflare Tunnel: %s", message)
            except Exception as exc:
                log.warning("เริ่ม Cloudflare Tunnel ไม่ได้: %s", exc)

        def SvcDoRun(self) -> None:
            """main loop ของ service — เปิด webui + tunnel + run_forever (ห้ามบล็อกนาน)."""
            import servicemanager

            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, ""),
            )
            # บอก webui ว่า process นี้รันใน service (ใช้ตัดสินใจอนุญาต/ปฏิเสธปุ่มควบคุม service)
            os.environ["CFDDNS_RUNNING_AS_SERVICE"] = "1"
            cfg = config_mod.Config(config_mod.DEFAULT_CONFIG_PATH)
            setup_file_logging(cfg.log_dir, detail=cfg.detail_log)
            # กันรันซ้ำ (service + exe/run อีกตัว) — ถ้ามี instance อื่นอยู่แล้ว ไม่เริ่ม loop
            from . import instance_lock

            if not instance_lock.acquire_instance_lock(config_mod.DEFAULT_CONFIG_PATH):
                log.warning("มีโปรแกรม/service instance อื่นรันอยู่แล้ว — service ไม่เริ่ม loop ซ้ำ (กัน heartbeat ส่งเบิ้ล)")
                # แจ้ง SCM ว่า service จบแบบหยุด (กัน SCM ค้างสถานะ STARTING/ค้างคา)
                try:
                    self.ReportServiceStatus(win32service.SERVICE_STOPPED)
                except Exception:
                    pass
                return
            log.info("service เริ่มทำงาน (interval=%ss)", cfg.interval_seconds)

            # เปิด Web UI ก่อน (เร็ว ไม่บล็อก SCM timeout) - เข้าผ่าน 127.0.0.1:8123 ได้ตลอด
            web_ui = None
            try:
                from . import webui as webui_mod

                web_ui = webui_mod.WebUI(config_mod.DEFAULT_CONFIG_PATH)
                web_ui.start()
                log.info("Web UI เปิดที่ http://127.0.0.1:%d", web_ui.port)
            except Exception as exc:
                log.warning("เปิด Web UI ไม่ได้: %s", exc)

            # เริ่ม Cloudflare Tunnel (อาจต้องดาวน์โหลด cloudflared ครั้งแรก -> รันแบบ async
            # ไม่ให้บล็อกการตอบสนอง SCM เกิน 30 วิ)
            tunnel_mgr = None
            tunnel_thread = None
            try:
                if cfg.tunnel_enabled:
                    from . import tunnel as tunnel_mod

                    tunnel_mgr = tunnel_mod.TunnelManager(config_mod.DEFAULT_CONFIG_PATH)
                    tunnel_thread = threading.Thread(
                        target=lambda: self._start_tunnel_async(tunnel_mgr, cfg),
                        daemon=True,
                    )
                    tunnel_thread.start()
            except Exception as exc:
                log.warning("เริ่ม Cloudflare Tunnel ไม่ได้: %s", exc)

            try:
                ddns.run_forever(
                    config_mod.DEFAULT_CONFIG_PATH,
                    dry_run=False,
                    stop_event=self._stop_event,
                )
            finally:
                # รอ thread เริ่ม tunnel ให้เสร็จจริงก่อนหยุด (กัน cloudflared ค้าง
                # ถ้ายังอยู่ในช่วงดาวน์โหลด/start ไม่ทันบันทึก pid — รอได้สูงสุด ~60 วิ)
                if tunnel_thread is not None:
                    tunnel_thread.join(timeout=60)
                if tunnel_mgr is not None:
                    try:
                        tunnel_mgr.stop()
                    except Exception as exc:
                        log.warning("หยุด Cloudflare Tunnel ไม่ได้: %s", exc)
                if web_ui is not None:
                    try:
                        web_ui.stop()
                    except Exception as exc:
                        log.warning("หยุด Web UI ไม่ได้: %s", exc)
            log.info("service หยุดทำงาน")

    return CloudflareDDNSService


def _run_windows_service_entry() -> None:
    """entry ที่ Windows Service Control Manager เรียก (ผ่าน exe/pythonw)."""
    import servicemanager

    servicemanager.Initialize()
    cls = _make_service_class()
    if hasattr(servicemanager, "PrepareServiceHost"):
        # pywin32 รุ่นเก่า
        servicemanager.PrepareServiceHost(cls)
    else:
        # pywin32 306+ เปลี่ยนชื่อ API
        servicemanager.PrepareToHostSingle(cls)
    servicemanager.StartServiceCtrlDispatcher()


# ---- คำสั่งควบคุม service (เรียกจาก main.py) ----


def _service_util() -> Any:
    """import pywin32 service ฟังก์ชันชุดควบคุม (lazy).

    Returns:
        tuple: (win32service, win32serviceutil) modules
    """
    import win32service
    import win32serviceutil

    return win32service, win32serviceutil


def _install_windows_service() -> str:
    """ลงทะเบียน service เข้า Windows (ต้องรันด้วยสิทธิ์ administrator).

    - ถ้าติดตั้งไว้แล้ว จะลบ (และหยุด) อันเก่าก่อน แล้วติดตั้งใหม่ทับ
    - โหมด exe (PyInstaller frozen): ติดตั้งด้วยตัว exe เอง
    - โหมด source: ติดตั้งด้วย pythonw.exe + path ของ main.py

    Returns:
        str: ข้อความผลลัพธ์
    """
    import sys

    win32service, win32serviceutil = _service_util()
    status = _windows_service_status()
    if status.get("installed"):
        try:
            win32serviceutil.StopService(SERVICE_NAME)
        except Exception:
            pass
        win32serviceutil.RemoveService(SERVICE_NAME)
    if getattr(sys, "frozen", False):
        exe = sys.executable
        exe_args = "run-service"
    else:
        script = os.path.abspath(os.path.join(os.path.dirname(__file__), "main.py"))
        pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        exe = pythonw if os.path.isfile(pythonw) else sys.executable
        exe_args = f'"{script}" run-service'
    win32serviceutil.InstallService(
        exe,
        SERVICE_NAME,
        SERVICE_DISPLAY_NAME,
        startType=win32service.SERVICE_AUTO_START,
        description=SERVICE_DESCRIPTION,
        exeArgs=exe_args,
    )
    _configure_failure_actions(win32service)
    return f"ติดตั้ง service '{SERVICE_NAME}' เรียบร้อย (เริ่มอัตโนมัติตอน boot)"


def _configure_failure_actions(win32service: Any) -> None:
    """ตั้งค่า auto-restart เมื่อ service crash เอง (กัน service ตายเงียบ).

    ครั้งแรก crash -> restart 5 วินาที · ครั้งที่ 2 -> 30 วินาที · reset นับหลัง 24 ชม.

    Args:
        win32service: โมดูล win32service (จาก _service_util)
    """
    try:
        scm = win32service.OpenSCManager(
            None, None, win32service.SC_MANAGER_CONNECT | win32service.SC_MANAGER_CREATE_SERVICE
        )
        try:
            handle = win32service.OpenService(
                scm, SERVICE_NAME, win32service.SERVICE_CHANGE_CONFIG | win32service.SERVICE_START
            )
            try:
                info = win32service.SERVICE_FAILURE_ACTIONS(
                    dwResetPeriod=86400,
                    lpRebootMsg=None,
                    lpCommand=None,
                    lpsaActions=[
                        (win32service.SC_ACTION_RESTART, 5000),
                        (win32service.SC_ACTION_RESTART, 30000),
                        (win32service.SC_ACTION_NONE, 0),
                    ],
                )
                win32service.ChangeServiceConfig2(
                    handle, win32service.SERVICE_CONFIG_FAILURE_ACTIONS, info
                )
                log.info("ตั้งค่า auto-restart ของ service เรียบร้อย (crash -> restart 5/30 วิ)")
            finally:
                win32service.CloseServiceHandle(handle)
        finally:
            win32service.CloseServiceHandle(scm)
    except Exception as exc:
        log.warning("ตั้งค่า auto-restart ของ service ไม่ได้: %s", exc)


def _remove_windows_service() -> str:
    """ลบ service ออกจาก Windows (ต้องรันด้วยสิทธิ์ administrator).

    Returns:
        str: ข้อความผลลัพธ์
    """
    win32service, win32serviceutil = _service_util()
    try:
        win32serviceutil.StopService(SERVICE_NAME)
    except Exception:
        pass  # 1062 = service ไม่ได้ start อยู่ — ข้ามได้
    win32serviceutil.RemoveService(SERVICE_NAME)
    return f"ลบ service '{SERVICE_NAME}' เรียบร้อย"


def _start_windows_service() -> str:
    """เริ่ม service.

    Returns:
        str: ข้อความผลลัพธ์
    """
    win32service, win32serviceutil = _service_util()
    win32serviceutil.StartService(SERVICE_NAME)
    return f"เริ่ม service '{SERVICE_NAME}' แล้ว"


def _stop_windows_service() -> str:
    """หยุด service.

    Returns:
        str: ข้อความผลลัพธ์
    """
    win32service, win32serviceutil = _service_util()
    win32serviceutil.StopService(SERVICE_NAME)
    return f"หยุด service '{SERVICE_NAME}' แล้ว"


def _restart_windows_service() -> str:
    """restart service (หยุดแล้วเริ่มใหม่).

    Returns:
        str: ข้อความผลลัพธ์
    """
    _stop_windows_service()
    _start_windows_service()
    return f"restart service '{SERVICE_NAME}' แล้ว"


def _windows_service_status() -> Dict[str, Any]:
    """คืน dict สถานะ service หรือ None ถ้ายังไม่ติดตั้ง."""
    try:
        win32service, _ = _service_util()
    except ImportError:
        return {"installed": False, "message": "pywin32 ยังไม่ติดตั้ง"}
    try:
        scm = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_CONNECT)
        try:
            handle = win32service.OpenService(scm, SERVICE_NAME, win32service.SERVICE_QUERY_STATUS)
            try:
                status = win32service.QueryServiceStatus(handle)
            finally:
                win32service.CloseServiceHandle(handle)
        finally:
            win32service.CloseServiceHandle(scm)
        states = {
            win32service.SERVICE_STOPPED: "stopped",
            win32service.SERVICE_START_PENDING: "starting",
            win32service.SERVICE_STOP_PENDING: "stopping",
            win32service.SERVICE_RUNNING: "running",
            win32service.SERVICE_CONTINUE_PENDING: "resuming",
            win32service.SERVICE_PAUSE_PENDING: "pausing",
            win32service.SERVICE_PAUSED: "paused",
        }
        return {"installed": True, "state": states.get(status[1], str(status[1]))}
    except Exception as exc:
        return {"installed": False, "message": f"ไม่พบ service: {exc}"}


# ---- macOS LaunchAgent ----


def platform_name():
    if sys.platform == "darwin":
        return "macOS"
    if os.name == "nt":
        return "Windows"
    return sys.platform


def service_kind():
    return "launchd" if sys.platform == "darwin" else "windows-service"


def can_control_service():
    """LaunchAgent เป็นของ user ไม่ต้อง admin; Windows ยังต้อง elevated token."""
    if sys.platform == "darwin":
        return True
    if os.name == "nt":
        try:
            import ctypes

            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False
    return False


def _launchd_plist_path():
    return os.path.join(os.path.expanduser("~/Library/LaunchAgents"), LAUNCHD_LABEL + ".plist")


def _getuid() -> int:
    """เลข uid ของ user (launchd domain ใช้) — fallback PID บนระบบที่ไม่มี os.getuid (Windows/test).

    Returns:
        int: uid (POSIX) หรือ PID (fallback สำหรับ machine ที่ไม่ใช่ macOS)
    """
    try:
        return os.getuid()
    except AttributeError:
        return os.getpid()


def _launchd_target():
    return f"gui/{_getuid()}/{LAUNCHD_LABEL}"


def _launchd_domain():
    return f"gui/{_getuid()}"


def _launchd_program_arguments(config_path):
    config_path = os.path.abspath(config_path or config_mod.DEFAULT_CONFIG_PATH)
    if getattr(sys, "frozen", False):
        return [sys.executable, "run-service", "--config", config_path]
    runner = os.path.join(config_mod.PROJECT_DIR, "run.py")
    if os.path.isfile(runner):
        return [sys.executable, runner, "run-service", "--config", config_path]
    return [
        sys.executable,
        "-m",
        "cloudflare_ddns.main",
        "run-service",
        "--config",
        config_path,
    ]


def _launchctl(*args, check=False):
    return subprocess.run(
        ["launchctl", *args],
        capture_output=True,
        text=True,
        timeout=30,
        check=check,
    )


def _install_launchd_service(config_path=None):
    config_path = os.path.abspath(config_path or config_mod.DEFAULT_CONFIG_PATH)
    data_dir = config_mod.data_dir_for(config_path)
    log_dir = config_mod.log_dir_for(config_path)
    plist_path = _launchd_plist_path()
    os.makedirs(os.path.dirname(plist_path), exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)
    payload = {
        "Label": LAUNCHD_LABEL,
        "ProgramArguments": _launchd_program_arguments(config_path),
        "WorkingDirectory": data_dir,
        "RunAtLoad": True,
        "KeepAlive": True,
        "ProcessType": "Background",
        "ThrottleInterval": 10,
        "EnvironmentVariables": {
            "CFDDNS_RUNNING_AS_SERVICE": "1",
            "PYTHONUNBUFFERED": "1",
        },
        "StandardOutPath": os.path.join(log_dir, "launchd.stdout.log"),
        "StandardErrorPath": os.path.join(log_dir, "launchd.stderr.log"),
    }
    tmp = plist_path + ".tmp"
    with open(tmp, "wb") as handle:
        plistlib.dump(payload, handle, sort_keys=False)
    os.replace(tmp, plist_path)
    return (
        f"ติดตั้ง LaunchAgent '{LAUNCHD_LABEL}' แล้ว ({plist_path}) — "
        "ใช้คำสั่ง start เพื่อเริ่มทันที"
    )


def _remove_launchd_service(config_path=None):
    plist_path = _launchd_plist_path()
    if not os.path.isfile(plist_path):
        return f"ไม่พบ LaunchAgent '{LAUNCHD_LABEL}'"
    _launchctl("bootout", _launchd_target())
    os.remove(plist_path)
    return f"ลบ LaunchAgent '{LAUNCHD_LABEL}' แล้ว (config/state/log ยังอยู่)"


def _start_launchd_service(config_path=None):
    plist_path = _launchd_plist_path()
    if not os.path.isfile(plist_path):
        raise RuntimeError("ยังไม่ได้ติดตั้ง LaunchAgent — รันคำสั่ง install ก่อน")
    status = _launchd_service_status()
    if status.get("state") == "running":
        return f"LaunchAgent '{LAUNCHD_LABEL}' กำลังทำงานอยู่แล้ว"
    result = _launchctl("bootstrap", _launchd_domain(), plist_path)
    if result.returncode != 0:
        # plist อาจโหลดอยู่แต่ process หยุดชั่วคราว — kickstart ให้ launchd เริ่มใหม่
        result = _launchctl("kickstart", "-k", _launchd_target())
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "launchctl start ไม่สำเร็จ").strip())
    return f"เริ่ม LaunchAgent '{LAUNCHD_LABEL}' แล้ว"


def _stop_launchd_service(config_path=None):
    if not os.path.isfile(_launchd_plist_path()):
        raise RuntimeError("ยังไม่ได้ติดตั้ง LaunchAgent")
    result = _launchctl("bootout", _launchd_target())
    if result.returncode != 0 and "No such process" not in (result.stderr or ""):
        raise RuntimeError((result.stderr or result.stdout or "launchctl stop ไม่สำเร็จ").strip())
    return f"หยุด LaunchAgent '{LAUNCHD_LABEL}' แล้ว"


def _restart_launchd_service(config_path=None):
    if not os.path.isfile(_launchd_plist_path()):
        raise RuntimeError("ยังไม่ได้ติดตั้ง LaunchAgent")
    result = _launchctl("kickstart", "-k", _launchd_target())
    if result.returncode != 0:
        return _start_launchd_service(config_path)
    return f"restart LaunchAgent '{LAUNCHD_LABEL}' แล้ว"


def _launchd_service_status():
    plist_path = _launchd_plist_path()
    if not os.path.isfile(plist_path):
        return {"installed": False, "message": "ยังไม่ได้ติดตั้ง LaunchAgent", "kind": "launchd"}
    result = _launchctl("print", _launchd_target())
    if result.returncode != 0:
        return {"installed": True, "state": "stopped", "kind": "launchd"}
    output = result.stdout or ""
    state = "running" if "state = running" in output else "stopped"
    pid = None
    for line in output.splitlines():
        if line.strip().startswith("pid ="):
            try:
                pid = int(line.split("=", 1)[1].strip())
            except ValueError:
                pass
            break
    return {"installed": True, "state": state, "pid": pid, "kind": "launchd"}


def _run_posix_service(config_path=None):
    """รัน Web UI + DDNS + Tunnel ใน foreground ให้ launchd ดูแล lifecycle."""
    from . import instance_lock

    config_path = os.path.abspath(config_path or config_mod.DEFAULT_CONFIG_PATH)
    os.environ["CFDDNS_RUNNING_AS_SERVICE"] = "1"
    cfg = config_mod.Config(config_path)
    setup_file_logging(cfg.log_dir, detail=cfg.detail_log)
    if not instance_lock.acquire_instance_lock(config_path):
        log.warning("มี instance อื่นรันอยู่แล้ว — LaunchAgent ไม่เริ่มซ้ำ")
        return 1

    stop_event = threading.Event()

    def _stop(_signum, _frame):
        stop_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, _stop)

    web_ui = None
    tunnel_mgr = None
    tunnel_thread = None
    try:
        from . import webui as webui_mod

        web_ui = webui_mod.WebUI(config_path)
        web_ui.start()
        log.info("LaunchAgent เริ่มทำงาน; Web UI: http://127.0.0.1:%d", web_ui.port)
        if cfg.tunnel_enabled:
            from . import tunnel as tunnel_mod

            tunnel_mgr = tunnel_mod.TunnelManager(config_path)
            tunnel_thread = threading.Thread(
                target=lambda: _start_tunnel_for_service(tunnel_mgr, cfg), daemon=True
            )
            tunnel_thread.start()
        ddns.run_forever(config_path, dry_run=False, stop_event=stop_event)
        return 0
    finally:
        if tunnel_thread is not None:
            tunnel_thread.join(timeout=60)
        if tunnel_mgr is not None:
            try:
                tunnel_mgr.stop()
            except Exception as exc:
                log.warning("หยุด Cloudflare Tunnel ไม่ได้: %s", exc)
        if web_ui is not None:
            try:
                web_ui.stop()
            except Exception as exc:
                log.warning("หยุด Web UI ไม่ได้: %s", exc)
        instance_lock.release_instance_lock()
        log.info("LaunchAgent หยุดทำงาน")


def _start_tunnel_for_service(tunnel_mgr, cfg):
    try:
        ok, message = tunnel_mgr.start(cfg)
        log.info("Cloudflare Tunnel: %s", message)
    except Exception as exc:
        log.warning("เริ่ม Cloudflare Tunnel ไม่ได้: %s", exc)


# ---- public cross-platform API ----


def run_service_entry(config_path=None):
    if sys.platform == "darwin":
        return _run_posix_service(config_path)
    if os.name == "nt":
        return _run_windows_service_entry()
    raise RuntimeError("โหมด service รองรับ Windows และ macOS เท่านั้น")


def install_service(config_path=None):
    if sys.platform == "darwin":
        return _install_launchd_service(config_path)
    if os.name == "nt":
        return _install_windows_service()
    raise RuntimeError("การติดตั้ง service รองรับ Windows และ macOS เท่านั้น")


def remove_service(config_path=None):
    if sys.platform == "darwin":
        return _remove_launchd_service(config_path)
    if os.name == "nt":
        return _remove_windows_service()
    raise RuntimeError("การลบ service รองรับ Windows และ macOS เท่านั้น")


def start_service(config_path=None):
    if sys.platform == "darwin":
        return _start_launchd_service(config_path)
    if os.name == "nt":
        return _start_windows_service()
    raise RuntimeError("การเริ่ม service รองรับ Windows และ macOS เท่านั้น")


def stop_service(config_path=None):
    if sys.platform == "darwin":
        return _stop_launchd_service(config_path)
    if os.name == "nt":
        return _stop_windows_service()
    raise RuntimeError("การหยุด service รองรับ Windows และ macOS เท่านั้น")


def restart_service(config_path=None):
    if sys.platform == "darwin":
        return _restart_launchd_service(config_path)
    if os.name == "nt":
        return _restart_windows_service()
    raise RuntimeError("การ restart service รองรับ Windows และ macOS เท่านั้น")


def service_status(config_path=None):
    if sys.platform == "darwin":
        return _launchd_service_status()
    if os.name == "nt":
        result = _windows_service_status()
        result["kind"] = "windows-service"
        return result
    return {"installed": False, "message": "ระบบนี้ยังไม่รองรับ service", "kind": "unsupported"}
