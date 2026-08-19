"""เทสต์ main: cmd_reset_password (ต้องใช้ได้แม้ config ยังตั้งไม่ครบ)"""

import contextlib
import io
import os
import tempfile
import threading
import unittest
from unittest import mock

from cloudflare_ddns import config as config_mod
from cloudflare_ddns import main


def run_reset(args):
    with contextlib.redirect_stdout(io.StringIO()):
        return main.cmd_reset_password(args)


class ResetPasswordTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "config.ini")
        # config ไม่ครบ (ไม่มี record) — จำลองลืมรหัส + config ยังไม่สมบูรณ์
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write("[cloudflare]\napi_token = test\nwebui_password = old-secret\n")

    def tearDown(self):
        self.tmp.cleanup()

    def _cfg(self):
        return config_mod.Config(self.path)

    def test_reset_sets_hash_even_when_config_incomplete(self):
        args = mock.Mock(config=self.path)
        with mock.patch("getpass.getpass", return_value="new-pw"):
            result = run_reset(args)
        self.assertEqual(result, 0)
        cfg = self._cfg()
        self.assertTrue(config_mod.password_is_hash(cfg.webui_password))
        self.assertEqual(cfg.webui_password, config_mod.password_hash("new-pw", self.path))

    def test_reset_clear_password(self):
        args = mock.Mock(config=self.path)
        with mock.patch("getpass.getpass", return_value=""):
            result = run_reset(args)
        self.assertEqual(result, 0)
        cfg = self._cfg()
        self.assertEqual(cfg.webui_password, "")

    def test_reset_mismatch_aborts(self):
        args = mock.Mock(config=self.path)
        with mock.patch("getpass.getpass", side_effect=["a", "b"]):
            result = run_reset(args)
        self.assertEqual(result, 1)
        cfg = self._cfg()
        self.assertEqual(cfg.webui_password, "old-secret")

    def test_reset_rejects_broken_ini(self):
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write("[broken\nnope")
        args = mock.Mock(config=self.path)
        with mock.patch("getpass.getpass", return_value="x"):
            result = run_reset(args)
        self.assertEqual(result, 1)


class ConsoleCloseHandlerTest(unittest.TestCase):
    """กด X (CTRL_CLOSE_EVENT) -> ต้องหยุด loop + tunnel + webui อย่างถูกต้อง"""

    def test_กดX_หยุดทุกอย่าง_และคืนTrue(self):
        stop_event = threading.Event()
        loop_thread = mock.Mock()
        tunnel_mgr = mock.Mock()
        web_ui = mock.Mock()
        registered = {}

        fake_win32api = mock.Mock()
        fake_win32api.CTRL_CLOSE_EVENT = 2
        fake_win32api.SetConsoleCtrlHandler.side_effect = lambda fn, add: registered.setdefault("fn", fn)

        with mock.patch.dict("sys.modules", {"win32api": fake_win32api}):
            ok = main._install_console_close_handler(stop_event, loop_thread, tunnel_mgr, web_ui)
        self.assertTrue(ok)
        self.assertIn("fn", registered)

        # จำลอง Windows ส่ง CTRL_CLOSE_EVENT (กด X)
        result = registered["fn"](2)
        self.assertTrue(result)
        self.assertTrue(stop_event.is_set())
        loop_thread.join.assert_called_once()
        tunnel_mgr.stop.assert_called_once()
        web_ui.stop.assert_called_once()

    def test_ไม่มีwin32api_ไม่ติดตั้ง(self):
        with mock.patch.dict("sys.modules", {"win32api": None}):
            # จำลอง import win32api ล้มเหลว
            with mock.patch("builtins.__import__", side_effect=ImportError("no win32api")):
                ok = main._install_console_close_handler(
                    threading.Event(), None, None, None
                )
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
