"""เทสต์ tunnel: log_tail / last_error อ่านจากไฟล์ tunnel.log"""

import os
import tempfile
import unittest
from unittest import mock

from cloudflare_ddns import config as config_mod
from cloudflare_ddns import tunnel as tunnel_mod


class TunnelLogTest(unittest.TestCase):
    """log_tail / last_error อ่าน tail จากไฟล์ข้าง config (data_dir)"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg_path = os.path.join(self.tmp.name, "config.ini")
        with open(self.cfg_path, "w", encoding="utf-8") as handle:
            handle.write("[cloudflare]\napi_token = t\n\n[record:h.example.com]\nname = h\nzone = example.com\n")
        self.log_path = tunnel_mod._log_path(self.cfg_path)

    def tearDown(self):
        self.tmp.cleanup()

    def _write_log(self, lines):
        with open(self.log_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines))

    def test_log_tail_returns_last_lines(self):
        lines = [f"line {i}" for i in range(50)]
        self._write_log(lines)
        mgr = tunnel_mod.TunnelManager(self.cfg_path)
        tail = mgr.log_tail(limit=10)
        self.assertEqual(tail.splitlines()[-1], "line 49")
        self.assertEqual(len(tail.splitlines()), 10)

    def test_log_tail_empty_when_no_file(self):
        mgr = tunnel_mod.TunnelManager(self.cfg_path)
        self.assertEqual(mgr.log_tail(), "")

    def test_last_error_finds_error_line(self):
        self._write_log([
            "INFO: connected",
            "ERR Unable to establish connection with Cloudflare edge",
            "INFO: retrying",
        ])
        mgr = tunnel_mod.TunnelManager(self.cfg_path)
        err = mgr.last_error()
        self.assertIn("Unable to establish connection", err)

    def test_last_error_empty_when_no_keyword(self):
        self._write_log(["INFO: connected", "INFO: registered"])
        mgr = tunnel_mod.TunnelManager(self.cfg_path)
        self.assertEqual(mgr.last_error(), "")

    def test_last_error_returns_latest(self):
        self._write_log([
            "ERR first failure",
            "INFO: recovered",
            "ERR Invalid token",
        ])
        mgr = tunnel_mod.TunnelManager(self.cfg_path)
        self.assertIn("Invalid token", mgr.last_error())


class TunnelStatusPidTest(unittest.TestCase):
    """status() re-read tunnel.pid ทุกครั้ง (cloudflared อาจถูกเริ่มโดย process อื่น)"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg_path = os.path.join(self.tmp.name, "config.ini")
        with open(self.cfg_path, "w", encoding="utf-8") as handle:
            handle.write("[cloudflare]\napi_token = t\n\n[record:h.example.com]\nname = h\nzone = example.com\n")
        self.pid_path = tunnel_mod._pid_path(self.cfg_path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_status_reloads_pid_from_file(self):
        mgr = tunnel_mod.TunnelManager(self.cfg_path)
        self.assertIsNone(mgr._pid)
        # เขียน pid ใหม่ลงไฟล์ (จำลอง process อื่นเริ่ม cloudflared)
        os.makedirs(os.path.dirname(self.pid_path), exist_ok=True)
        with open(self.pid_path, "w", encoding="utf-8") as handle:
            handle.write("999999")
        with mock.patch.object(tunnel_mod, "_pid_alive", return_value=True):
            st = mgr.status(config_mod.Config(self.cfg_path))
        self.assertTrue(st["running"])
        self.assertEqual(st["pid"], 999999)


class TunnelLogFilterTest(unittest.TestCase):
    """log_tail only_errors + rotation กันบวม"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg_path = os.path.join(self.tmp.name, "config.ini")
        with open(self.cfg_path, "w", encoding="utf-8") as handle:
            handle.write("[cloudflare]\napi_token = t\n\n[record:h.example.com]\nname = h\nzone = example.com\n")
        self.log_path = tunnel_mod._log_path(self.cfg_path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_only_errors_filters_levels(self):
        lines = [
            '{"level":"info","message":"Registered tunnel connection"}',
            '{"level":"error","message":"Unable to establish connection"}',
            '{"level":"info","message":"precheck complete"}',
            '{"level":"warn","message":"retrying"}',
        ]
        with open(self.log_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines))
        mgr = tunnel_mod.TunnelManager(self.cfg_path)
        out = mgr.log_tail(only_errors=True)
        self.assertIn("Unable to establish", out)
        self.assertIn("retrying", out)
        self.assertNotIn("Registered tunnel connection", out)

    def test_rotation_truncates_large_file(self):
        # เขียนไฟล์ใหญ่กว่า TUNNEL_LOG_MAX -> log_tail ควรตัดเหลือเล็กกว่า
        big = ("x" * 2000 + "\n") * 3000  # ~6MB
        with open(self.log_path, "w", encoding="utf-8") as handle:
            handle.write(big)
        mgr = tunnel_mod.TunnelManager(self.cfg_path)
        mgr.log_tail()
        size = os.path.getsize(self.log_path)
        self.assertLess(size, tunnel_mod.TUNNEL_LOG_MAX)


if __name__ == "__main__":
    unittest.main()
