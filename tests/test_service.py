"""เทสต์ service: กันรันซ้ำแจ้ง SCM หยุด + รอ async tunnel thread ก่อนหยุด"""

import sys
import unittest
from unittest import mock

from cloudflare_ddns import service as service_mod


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


if __name__ == "__main__":
    unittest.main()
