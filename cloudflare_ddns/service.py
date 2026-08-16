"""Windows Service wrapper (pywin32) สำหรับรัน DDNS loop เป็น service."""

import logging
import os
import threading
import time
from logging.handlers import TimedRotatingFileHandler

from . import config as config_mod
from . import ddns

SERVICE_NAME = "CloudflareDDNS"
SERVICE_DISPLAY_NAME = "Cloudflare DDNS Updater"
SERVICE_DESCRIPTION = (
    "ตรวจหา IP สาธารณะ (IPv4/IPv6) แล้วอัปเดต DNS record บน Cloudflare "
    "โดยอัตโนมัติเมื่อ IP เปลี่ยน"
)

log = logging.getLogger("cloudflare-ddns")


def setup_file_logging(log_dir=None):
    """log ไปไฟล์รายวัน (ใช้ทั้งตอน run foreground และตอนเป็น service)."""
    log_dir = log_dir or config_mod.DEFAULT_LOG_DIR
    os.makedirs(log_dir, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
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


def _make_service_class():
    """สร้างคลาส service แบบ lazy เพื่อให้ import ได้แม้ยังไม่มี pywin32."""
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

        def __init__(self, args):
            super().__init__(args)
            self._stop_event = threading.Event()

        def SvcStop(self):
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            self._stop_event.set()

        def _start_tunnel_async(self, tunnel_mgr, cfg):
            try:
                ok, message = tunnel_mgr.start(cfg)
                log.info("Cloudflare Tunnel: %s", message)
            except Exception as exc:
                log.warning("เริ่ม Cloudflare Tunnel ไม่ได้: %s", exc)

        def SvcDoRun(self):
            import servicemanager

            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, ""),
            )
            # บอก webui ว่า process นี้รันใน service (ใช้ตัดสินใจอนุญาต/ปฏิเสธปุ่มควบคุม service)
            os.environ["CFDDNS_RUNNING_AS_SERVICE"] = "1"
            cfg = config_mod.Config(config_mod.DEFAULT_CONFIG_PATH)
            setup_file_logging(cfg.log_dir)
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
            try:
                if cfg.tunnel_enabled:
                    from . import tunnel as tunnel_mod

                    tunnel_mgr = tunnel_mod.TunnelManager()
                    threading.Thread(
                        target=lambda: self._start_tunnel_async(tunnel_mgr, cfg),
                        daemon=True,
                    ).start()
            except Exception as exc:
                log.warning("เริ่ม Cloudflare Tunnel ไม่ได้: %s", exc)

            try:
                ddns.run_forever(
                    config_mod.DEFAULT_CONFIG_PATH,
                    dry_run=False,
                    stop_event=self._stop_event,
                )
            finally:
                # รอ thread เริ่ม tunnel ให้ทันก่อนหยุด (กัน cloudflared ค้าง
                # ถ้ายังอยู่ในช่วงดาวน์โหลด/start ไม่ทันบันทึก pid)
                if tunnel_mgr is not None:
                    time.sleep(1.0)
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


def run_service_entry():
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


def _service_util():
    import win32service
    import win32serviceutil

    return win32service, win32serviceutil


def install_service():
    """ลงทะเบียน service เข้า Windows (ต้องรันด้วยสิทธิ์ administrator).

    - ถ้าติดตั้งไว้แล้ว จะลบ (และหยุด) อันเก่าก่อน แล้วติดตั้งใหม่ทับ
    - โหมด exe (PyInstaller frozen): ติดตั้งด้วยตัว exe เอง
    - โหมด source: ติดตั้งด้วย pythonw.exe + path ของ main.py
    """
    import sys

    win32service, win32serviceutil = _service_util()
    status = service_status()
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
    return f"ติดตั้ง service '{SERVICE_NAME}' เรียบร้อย (เริ่มอัตโนมัติตอน boot)"


def remove_service():
    win32service, win32serviceutil = _service_util()
    try:
        win32serviceutil.StopService(SERVICE_NAME)
    except Exception:
        pass  # 1062 = service ไม่ได้ start อยู่ — ข้ามได้
    win32serviceutil.RemoveService(SERVICE_NAME)
    return f"ลบ service '{SERVICE_NAME}' เรียบร้อย"


def start_service():
    win32service, win32serviceutil = _service_util()
    win32serviceutil.StartService(SERVICE_NAME)
    return f"เริ่ม service '{SERVICE_NAME}' แล้ว"


def stop_service():
    win32service, win32serviceutil = _service_util()
    win32serviceutil.StopService(SERVICE_NAME)
    return f"หยุด service '{SERVICE_NAME}' แล้ว"


def restart_service():
    stop_service()
    start_service()
    return f"restart service '{SERVICE_NAME}' แล้ว"


def service_status():
    """คืน dict สถานะ service หรือ None ถ้ายังไม่ติดตั้ง"""
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
