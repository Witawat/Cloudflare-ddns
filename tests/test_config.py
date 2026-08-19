"""เทสต์ config: password_hash, rotate_backup, field ใหม่ (telegram_allow_reset/ip_consensus), validate"""

import os
import tempfile
import unittest

from cloudflare_ddns import config as config_mod


def write_ini(path, text):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return path


MINIMAL_INI = """[cloudflare]
api_token = test-token
interval_seconds = 60
use_ipv4 = true
use_ipv6 = true

[record:home.example.com]
zone = example.com
"""


class PasswordHashTest(unittest.TestCase):
    def test_hash_is_64_hex(self):
        value = config_mod.password_hash("secret", r"C:\cfg\config.ini")
        self.assertEqual(len(value), 64)
        self.assertTrue(config_mod.password_is_hash(value))

    def test_hash_deterministic_same_path(self):
        a = config_mod.password_hash("secret", r"C:\cfg\config.ini")
        b = config_mod.password_hash("secret", r"C:\cfg\config.ini")
        self.assertEqual(a, b)

    def test_hash_differs_by_path_and_password(self):
        a = config_mod.password_hash("secret", r"C:\cfg\config.ini")
        b = config_mod.password_hash("secret", r"C:\other\config.ini")
        c = config_mod.password_hash("other", r"C:\cfg\config.ini")
        self.assertNotEqual(a, b)
        self.assertNotEqual(a, c)

    def test_password_is_hash(self):
        self.assertFalse(config_mod.password_is_hash("secret"))
        self.assertFalse(config_mod.password_is_hash(""))
        self.assertTrue(config_mod.password_is_hash("a" * 64))


class NewFieldsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "config.ini")
        self.ini_with_fields = MINIMAL_INI.replace(
            "[record:home.example.com]",
            "telegram_allow_reset = true\nip_consensus = true\n\n[record:home.example.com]",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_new_fields_default_false(self):
        write_ini(self.path, MINIMAL_INI)
        cfg = config_mod.Config(self.path)
        self.assertFalse(cfg.telegram_allow_reset)
        self.assertFalse(cfg.ip_consensus)

    def test_new_fields_read_from_file(self):
        write_ini(self.path, self.ini_with_fields)
        cfg = config_mod.Config(self.path)
        self.assertTrue(cfg.telegram_allow_reset)
        self.assertTrue(cfg.ip_consensus)

    def test_validate_ok(self):
        write_ini(self.path, self.ini_with_fields)
        cfg = config_mod.Config(self.path)
        self.assertEqual(cfg.validate(), [])

    def test_validate_daily_report_time(self):
        write_ini(self.path, """[cloudflare]
api_token = test-token
interval_seconds = 60
use_ipv4 = true
use_ipv6 = true
daily_report = true
daily_report_time = 25:99

[record:home.example.com]
zone = example.com
""")
        cfg = config_mod.Config(self.path)
        self.assertTrue(any("daily_report_time" in e for e in cfg.validate()))

    def test_heartbeat_min_interval_default_60(self):
        write_ini(self.path, MINIMAL_INI)
        cfg = config_mod.Config(self.path)
        self.assertEqual(cfg.heartbeat_min_interval, 60)

    def test_heartbeat_min_interval_read_from_file(self):
        write_ini(self.path, MINIMAL_INI.replace(
            "[cloudflare]", "[cloudflare]\nheartbeat_min_interval = 15"
        ))
        cfg = config_mod.Config(self.path)
        self.assertEqual(cfg.heartbeat_min_interval, 15)

    def test_heartbeat_min_interval_out_of_range_fails_validate(self):
        write_ini(self.path, MINIMAL_INI.replace(
            "[cloudflare]", "[cloudflare]\nheartbeat_min_interval = 1"
        ))
        cfg = config_mod.Config(self.path)
        self.assertTrue(any("heartbeat_min_interval" in e for e in cfg.validate()))

    def test_detail_log_default_false(self):
        write_ini(self.path, MINIMAL_INI)
        cfg = config_mod.Config(self.path)
        self.assertFalse(cfg.detail_log)

    def test_detail_log_read_from_file(self):
        write_ini(self.path, MINIMAL_INI.replace(
            "[cloudflare]", "[cloudflare]\ndetail_log = true"
        ))
        cfg = config_mod.Config(self.path)
        self.assertTrue(cfg.detail_log)

    def test_tunnel_protocol_default_auto(self):
        write_ini(self.path, MINIMAL_INI)
        cfg = config_mod.Config(self.path)
        self.assertEqual(cfg.tunnel_protocol, "auto")

    def test_tunnel_protocol_read_from_file(self):
        write_ini(self.path, MINIMAL_INI.replace(
            "[cloudflare]", "[cloudflare]\ntunnel_protocol = http2"
        ))
        cfg = config_mod.Config(self.path)
        self.assertEqual(cfg.tunnel_protocol, "http2")

    def test_tunnel_protocol_invalid_fails_validate(self):
        write_ini(self.path, MINIMAL_INI.replace(
            "[cloudflare]", "[cloudflare]\ntunnel_protocol = tcp"
        ))
        cfg = config_mod.Config(self.path)
        self.assertTrue(any("tunnel_protocol" in e for e in cfg.validate()))


class RotateBackupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "state.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_file_no_error(self):
        self.assertTrue(config_mod.rotate_backup(self.path, keep=3))

    def test_rotates_and_keeps(self):
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write("v0")
        for i in range(1, 6):
            config_mod.rotate_backup(self.path, keep=3)
            with open(self.path, "w", encoding="utf-8") as handle:
                handle.write(f"v{i}")
        self.assertTrue(os.path.isfile(self.path + ".bak"))
        self.assertTrue(os.path.isfile(self.path + ".2.bak"))
        self.assertTrue(os.path.isfile(self.path + ".3.bak"))
        self.assertFalse(os.path.isfile(self.path + ".4.bak"))
        with open(self.path + ".3.bak", encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "v2")
        with open(self.path + ".bak", encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "v4")
        with open(self.path, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "v5")


class SaveTextTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "config.ini")
        write_ini(self.path, MINIMAL_INI)

    def tearDown(self):
        self.tmp.cleanup()

    def test_save_text_keeps_file(self):
        cfg = config_mod.Config(self.path)
        ok, message = cfg.save_text(MINIMAL_INI + "\ntelegram_allow_reset = true\n")
        self.assertTrue(ok, message)
        self.assertTrue(os.path.isfile(self.path))

    def test_save_text_rejects_broken_ini(self):
        cfg = config_mod.Config(self.path)
        ok, _ = cfg.save_text("not = ini\n[broken")
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()