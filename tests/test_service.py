"""เทสต์ service: กันรันซ้ำแจ้ง SCM หยุด + รอ async tunnel thread ก่อนหยุด"""

import sys
import os
import plistlib
import tempfile
import unittest
from unittest import mock

from cloudflare_ddns import service as service_mod


@unittest.skipUnless(os.name == "nt", "เทสต์ Windows Service")
class ServiceInstanceLockTest(unittest.TestCase):
    """instance lock ชน -> แจ้ง SCM STOPPED + ไม่เริ่ม loop"""

    def test_lock_ชน_รายงานSCM_STOPPED(self):
        cls = service_mod._make_service_class()
        inst = object.__new__(cls)
        inst._stop_event = mock.Mock()
        status_calls = []
        inst.ReportServiceStatus = status_calls.append
        with mock.patch.dict(sys.modules, {
            "cloudflare_ddns.instance_lock": mock.Mock(),
            "cloudflare_ddns.webui": mock.Mock(),
            "cloudflare_ddns.tunnel": mock.Mock(),
            "win32service": mock.Mock(),
        }) as mods, \
                mock.patch.object(__import__("cloudflare_ddns"), "instance_lock", mods["cloudflare_ddns.instance_lock"], create=True), \
                mock.patch.object(__import__("cloudflare_ddns"), "webui", mods["cloudflare_ddns.webui"], create=True), \
                mock.patch.object(__import__("cloudflare_ddns"), "tunnel", mods["cloudflare_ddns.tunnel"], create=True), \
                mock.patch("cloudflare_ddns.service.setup_file_logging"), \
                mock.patch("cloudflare_ddns.service.config_mod.Config") as cfg_mod:
            lock = mods["cloudflare_ddns.instance_lock"]
            lock.acquire_instance_lock.return_value = False
            fake_cfg = mock.Mock()
            fake_cfg.log_dir = "C:\\x\\logs"
            fake_cfg.interval_seconds = 60
            cfg_mod.return_value = fake_cfg
            mods["win32service"].SERVICE_STOPPED = 1
            inst.SvcDoRun()
        self.assertIn(1, status_calls)  # SERVICE_STOPPED รายงานแล้ว


@unittest.skipUnless(os.name == "nt", "เทสต์ Windows Service")
class ServiceTunnelJoinTest(unittest.TestCase):
    """หยุด service -> ต้องรอ async tunnel thread (join) ก่อน stop tunnel"""

    def test_join_thread_ก่อน_stop_tunnel(self):
        cls = service_mod._make_service_class()
        inst = object.__new__(cls)
        inst._stop_event = mock.Mock()
        inst.ReportServiceStatus = mock.Mock()
        tunnel_thread = mock.Mock()
        tunnel_mgr = mock.Mock()
        web_ui = mock.Mock()
        with mock.patch.dict(sys.modules, {
            "cloudflare_ddns.instance_lock": mock.Mock(),
            "cloudflare_ddns.webui": mock.Mock(),
            "cloudflare_ddns.tunnel": mock.Mock(),
            "win32service": mock.Mock(),
        }) as mods, \
                mock.patch.object(__import__("cloudflare_ddns"), "instance_lock", mods["cloudflare_ddns.instance_lock"], create=True), \
                mock.patch.object(__import__("cloudflare_ddns"), "webui", mods["cloudflare_ddns.webui"], create=True), \
                mock.patch.object(__import__("cloudflare_ddns"), "tunnel", mods["cloudflare_ddns.tunnel"], create=True), \
                mock.patch("cloudflare_ddns.service.setup_file_logging"), \
                mock.patch("cloudflare_ddns.service.config_mod.Config") as cfg_mod, \
                mock.patch("cloudflare_ddns.service.threading.Thread") as thread_cls, \
                mock.patch("cloudflare_ddns.service.ddns.run_forever") as run_forever:
            lock = mods["cloudflare_ddns.instance_lock"]
            lock.acquire_instance_lock.return_value = True
            tun = mods["cloudflare_ddns.tunnel"]
            tun.TunnelManager.return_value = tunnel_mgr
            webui_mod = mods["cloudflare_ddns.webui"]
            webui_mod.WebUI.return_value = web_ui
            fake_cfg = mock.Mock()
            fake_cfg.log_dir = "C:\\x\\logs"
            fake_cfg.tunnel_enabled = True
            fake_cfg.interval_seconds = 60
            fake_cfg.detail_log = False
            cfg_mod.return_value = fake_cfg
            thread_cls.return_value = tunnel_thread
            run_forever.side_effect = KeyboardInterrupt  # จบ loop ทันที
            inst._start_tunnel_async = mock.Mock()
            with mock.patch.object(cls, "_start_tunnel_async", inst._start_tunnel_async):
                with self.assertRaises(KeyboardInterrupt):
                    inst.SvcDoRun()
        # ต้อง join thread ก่อน stop tunnel (ลำดับสำคัญ)
        tunnel_thread.join.assert_called_once_with(timeout=60)
        tunnel_mgr.stop.assert_called_once()
        # ยืนยันลำดับ: join ถูกเรียกก่อน stop (ใช้ตัวนับจาก side_effect)
        order = []

        def _join(*a, **k):
            order.append("join")

        def _stop(*a, **k):
            order.append("stop")

        tunnel_thread.join.side_effect = _join
        tunnel_mgr.stop.side_effect = _stop
        # จำลอง SvcDoRun อีกครั้งเก็บลำดับ
        inst2 = object.__new__(cls)
        inst2._stop_event = mock.Mock()
        inst2.ReportServiceStatus = mock.Mock()
        with mock.patch.dict(sys.modules, {
            "cloudflare_ddns.instance_lock": mock.Mock(),
            "cloudflare_ddns.webui": mock.Mock(),
            "cloudflare_ddns.tunnel": mock.Mock(),
            "win32service": mock.Mock(),
        }) as mods, \
                mock.patch.object(__import__("cloudflare_ddns"), "instance_lock", mods["cloudflare_ddns.instance_lock"], create=True), \
                mock.patch.object(__import__("cloudflare_ddns"), "webui", mods["cloudflare_ddns.webui"], create=True), \
                mock.patch.object(__import__("cloudflare_ddns"), "tunnel", mods["cloudflare_ddns.tunnel"], create=True), \
                mock.patch("cloudflare_ddns.service.setup_file_logging"), \
                mock.patch("cloudflare_ddns.service.config_mod.Config") as cfg_mod2, \
                mock.patch("cloudflare_ddns.service.threading.Thread") as thread_cls2, \
                mock.patch("cloudflare_ddns.service.ddns.run_forever") as run2:
            mods["cloudflare_ddns.instance_lock"].acquire_instance_lock.return_value = True
            mods["cloudflare_ddns.tunnel"].TunnelManager.return_value = tunnel_mgr
            mods["cloudflare_ddns.webui"].WebUI.return_value = web_ui
            fake_cfg2 = mock.Mock()
            fake_cfg2.log_dir = "C:\\x\\logs"
            fake_cfg2.tunnel_enabled = True
            fake_cfg2.interval_seconds = 60
            fake_cfg2.detail_log = False
            cfg_mod2.return_value = fake_cfg2
            thread_cls2.return_value = tunnel_thread
            run2.side_effect = KeyboardInterrupt
            inst2._start_tunnel_async = mock.Mock()
            with mock.patch.object(cls, "_start_tunnel_async", inst2._start_tunnel_async):
                with self.assertRaises(KeyboardInterrupt):
                    inst2.SvcDoRun()
        self.assertEqual(order, ["join", "stop"])


class LaunchdServiceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.config_path = os.path.join(self.tmp.name, "config.ini")
        self.plist_path = os.path.join(self.tmp.name, "LaunchAgents", "service.plist")

    def test_install_เขียนplistพร้อมconfigและlog(self):
        with mock.patch.object(service_mod, "_launchd_plist_path", return_value=self.plist_path):
            message = service_mod._install_launchd_service(self.config_path)
        self.assertIn("LaunchAgent", message)
        with open(self.plist_path, "rb") as handle:
            data = plistlib.load(handle)
        self.assertEqual(data["Label"], service_mod.LAUNCHD_LABEL)
        self.assertTrue(data["RunAtLoad"])
        self.assertTrue(data["KeepAlive"])
        self.assertIn(self.config_path, data["ProgramArguments"])
        self.assertEqual(data["EnvironmentVariables"]["CFDDNS_RUNNING_AS_SERVICE"], "1")
        self.assertTrue(data["StandardErrorPath"].endswith("launchd.stderr.log"))

    def test_status_อ่านrunningและpidจากlaunchctl(self):
        os.makedirs(os.path.dirname(self.plist_path), exist_ok=True)
        with open(self.plist_path, "w", encoding="utf-8") as handle:
            handle.write("plist")
        result = mock.Mock(returncode=0, stdout="state = running\n\tpid = 1234\n", stderr="")
        with mock.patch.object(service_mod, "_launchd_plist_path", return_value=self.plist_path), \
                mock.patch.object(service_mod, "_launchctl", return_value=result):
            status = service_mod._launchd_service_status()
        self.assertEqual(status["state"], "running")
        self.assertEqual(status["pid"], 1234)
        self.assertEqual(status["kind"], "launchd")

    def test_run_service_เริ่มและหยุดwebuiพร้อมปลดlock(self):
        from cloudflare_ddns import instance_lock

        cfg = mock.Mock(log_dir=os.path.join(self.tmp.name, "logs"), detail_log=False)
        cfg.tunnel_enabled = False
        web_ui = mock.Mock(port=8123)
        with mock.patch.object(service_mod.config_mod, "Config", return_value=cfg), \
                mock.patch.object(service_mod, "setup_file_logging"), \
                mock.patch.object(service_mod.signal, "signal"), \
                mock.patch.object(instance_lock, "acquire_instance_lock", return_value=True), \
                mock.patch.object(instance_lock, "release_instance_lock") as release, \
                mock.patch("cloudflare_ddns.webui.WebUI", return_value=web_ui), \
                mock.patch.object(service_mod.ddns, "run_forever") as run_forever:
            result = service_mod._run_posix_service(self.config_path)
        self.assertEqual(result, 0)
        web_ui.start.assert_called_once()
        web_ui.stop.assert_called_once()
        run_forever.assert_called_once()
        release.assert_called_once()


if __name__ == "__main__":
    unittest.main()
