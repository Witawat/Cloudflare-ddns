"""เทสต์ main: cmd_reset_password (ต้องใช้ได้แม้ config ยังตั้งไม่ครบ)"""

import contextlib
import io
import os
import tempfile
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


if __name__ == "__main__":
    unittest.main()
