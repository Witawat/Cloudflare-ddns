"""เทสต์ความปลอดภัย Web UI: Origin check, hash password, security headers, log injection"""

import os
import tempfile
import unittest
from unittest import mock

from cloudflare_ddns import config as config_mod
from cloudflare_ddns import webui

MINIMAL_INI = """[cloudflare]
api_token = test-token
interval_seconds = 60
use_ipv4 = true
use_ipv6 = true

[record:home.example.com]
zone = example.com
"""


class FakeHeaders:
    def __init__(self, values=None):
        self.values = values or {}

    def get(self, key, default=None):
        return self.values.get(key, default)


def make_handler(config_path, headers=None, cfg=None):
    handler = webui.WebUIHandler.__new__(webui.WebUIHandler)
    handler.headers = FakeHeaders(headers or {})
    handler.path = "/"
    server = mock.Mock(config_path=config_path)
    server.cfg = cfg or config_mod.Config(config_path)
    handler.server = server
    handler._read_body = mock.Mock(return_value=b"")
    handler._send_json = mock.Mock(return_value=None)
    handler.send_response = mock.Mock()
    handler.send_header = mock.Mock()
    handler.end_headers = mock.Mock()
    return handler


class OriginCheckTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "config.ini")
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write(MINIMAL_INI)

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_origin_allowed(self):
        handler = make_handler(self.path)
        self.assertTrue(handler._origin_allowed())

    def test_matching_origin_allowed(self):
        handler = make_handler(self.path, headers={"Origin": "http://127.0.0.1:8123", "Host": "127.0.0.1:8123"})
        self.assertTrue(handler._origin_allowed())

    def test_cross_origin_blocked(self):
        handler = make_handler(self.path, headers={"Origin": "http://evil.example", "Host": "127.0.0.1:8123"})
        self.assertFalse(handler._origin_allowed())

    def test_post_with_bad_origin_rejected(self):
        handler = make_handler(
            self.path,
            headers={"Origin": "http://evil.example", "Host": "127.0.0.1:8123"},
        )
        handler.path = "/save-config"
        webui._login_guard["locked_until"] = 0.0
        webui._login_guard["fails"] = 0
        handler._do_post_inner()
        handler._send_json.assert_called_once()
        args = handler._send_json.call_args[0]
        self.assertEqual(args[0], 403)


class AuthTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "config.ini")
        self.ini_with_pw = MINIMAL_INI.replace(
            "[record:home.example.com]",
            "webui_password = {}\n\n[record:home.example.com]".format(
                config_mod.password_hash("secret", self.path)
            ),
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, text):
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def test_empty_password_no_login_needed(self):
        self._write(MINIMAL_INI)
        handler = make_handler(self.path)
        self.assertTrue(handler._authed())

    def test_correct_hash_cookie_ok(self):
        self._write(self.ini_with_pw)
        handler = make_handler(self.path)
        handler.headers = FakeHeaders({"Cookie": "cfddns_session=" + config_mod.password_hash("secret", self.path)})
        self.assertTrue(handler._authed())

    def test_wrong_cookie_rejected(self):
        self._write(self.ini_with_pw)
        handler = make_handler(self.path)
        handler.headers = FakeHeaders({"Cookie": "cfddns_session=deadbeef"})
        self.assertFalse(handler._authed())

    def test_plaintext_config_still_authenticates(self):
        self._write(MINIMAL_INI.replace(
            "[record:home.example.com]",
            "webui_password = secret\n\n[record:home.example.com]",
        ))
        handler = make_handler(self.path)
        handler.headers = FakeHeaders({"Cookie": "cfddns_session=" + config_mod.password_hash("secret", self.path)})
        self.assertTrue(handler._authed())


class LoginTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "config.ini")
        self.ini_with_pw = MINIMAL_INI.replace(
            "[record:home.example.com]",
            "webui_password = {}\n\n[record:home.example.com]".format(
                config_mod.password_hash("secret", self.path)
            ),
        )
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write(self.ini_with_pw)
        webui._login_guard["locked_until"] = 0.0
        webui._login_guard["fails"] = 0

    def tearDown(self):
        webui._login_guard["locked_until"] = 0.0
        webui._login_guard["fails"] = 0
        self.tmp.cleanup()

    def test_login_with_plaintext_password(self):
        handler = make_handler(self.path)
        handler.path = "/login"
        handler._read_body.return_value = "pw=secret"
        handler._do_post_inner()
        self.assertEqual(handler.send_response.call_args[0][0], 302)
        cookie = [c.args[1] for c in handler.send_header.call_args_list if c.args[0] == "Set-Cookie"][0]
        self.assertIn("SameSite=Lax", cookie)
        self.assertIn("HttpOnly", cookie)

    def test_login_with_hash_value(self):
        handler = make_handler(self.path)
        handler.path = "/login"
        handler._read_body.return_value = "pw=" + config_mod.password_hash("secret", self.path)
        handler._do_post_inner()
        self.assertEqual(handler.send_response.call_args[0][0], 302)

    def test_login_wrong_password_no_cookie(self):
        handler = make_handler(self.path)
        handler.path = "/login"
        handler._read_body.return_value = "pw=wrong"
        handler._do_post_inner()
        cookies = [c for c in handler.send_header.call_args_list if c.args[0] == "Set-Cookie"]
        self.assertEqual(cookies, [])


class SecurityHeadersTest(unittest.TestCase):
    def test_send_has_security_headers(self):
        tmp = tempfile.TemporaryDirectory()
        path = os.path.join(tmp.name, "config.ini")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(MINIMAL_INI)
        handler = make_handler(path)
        handler.wfile = mock.Mock()
        handler._send(200, "hi", content_type="text/html; charset=utf-8")
        sent = {c.args[0] for c in handler.send_header.call_args_list}
        self.assertIn("X-Content-Type-Options", sent)
        self.assertIn("X-Frame-Options", sent)
        self.assertIn("Referrer-Policy", sent)
        self.assertIn("Cache-Control", sent)
        # X-Frame-Options ต้องเป็น DENY
        xfo = [c.args[1] for c in handler.send_header.call_args_list if c.args[0] == "X-Frame-Options"][0]
        self.assertEqual(xfo, "DENY")
        tmp.cleanup()


class LogEventFilterTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "config.ini")
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write(MINIMAL_INI)

    def tearDown(self):
        self.tmp.cleanup()

    def test_newline_removed_from_log_message(self):
        handler = make_handler(self.path)
        handler.path = "/log-event"
        handler._read_body.return_value = b'{"message": "oops\\n[INJECT] fake\\r\\nline"}'
        with mock.patch("cloudflare_ddns.webui.log") as mock_log:
            handler._do_post_inner()
        args = mock_log.warning.call_args.args
        joined = " ".join(str(a) for a in args)
        self.assertNotIn("\n", joined)
        self.assertNotIn("\r", joined)


class DictToIniTest(unittest.TestCase):
    """_dict_to_ini: ต้อง hash รหัสผ่านใหม่ แต่คง hash เดิม / ว่างไว้"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "config.ini")
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write(MINIMAL_INI)

    def tearDown(self):
        self.tmp.cleanup()

    def test_plaintext_gets_hashed(self):
        payload = {"cloudflare": {"webui_password": "my-secret"}, "telegram": {}, "tunnel": {}, "records": []}
        text = webui._dict_to_ini(payload, self.path)
        self.assertIn("webui_password = {}".format(config_mod.password_hash("my-secret", self.path)), text)
        self.assertNotIn("webui_password = my-secret", text)

    def test_hash_stays_as_is(self):
        h = config_mod.password_hash("old", self.path)
        payload = {"cloudflare": {"webui_password": h}, "telegram": {}, "tunnel": {}, "records": []}
        text = webui._dict_to_ini(payload, self.path)
        self.assertIn("webui_password = {}".format(h), text)

    def test_empty_stays_empty(self):
        payload = {"cloudflare": {"webui_password": ""}, "telegram": {}, "tunnel": {}, "records": []}
        text = webui._dict_to_ini(payload, self.path)
        self.assertIn("webui_password =", text)


class MigratePasswordHashTest(unittest.TestCase):
    """config เก่าที่เก็บ plaintext -> ต้องย้ายเป็น hash เสมอ (แม้ config ยังตั้งไม่ครบ)"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "config.ini")

    def tearDown(self):
        self.tmp.cleanup()

    def test_migrates_plaintext_even_when_config_incomplete(self):
        # config ไม่ครบ (ไม่มี record) — save_text เดิมจะกีดกัน แต่ migrate ต้องทำได้
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write("[cloudflare]\napi_token = test\nwebui_password = plain-old\n")
        cfg = config_mod.Config(self.path)
        webui._migrate_password_hash(cfg)
        self.assertTrue(config_mod.password_is_hash(cfg.webui_password))
        self.assertEqual(cfg.webui_password, config_mod.password_hash("plain-old", self.path))

    def test_skips_when_already_hash(self):
        h = config_mod.password_hash("secret", self.path)
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write("[cloudflare]\napi_token = test\nwebui_password = {}\n".format(h))
        cfg = config_mod.Config(self.path)
        webui._migrate_password_hash(cfg)
        self.assertEqual(cfg.webui_password, h)

    def test_skips_when_empty(self):
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write("[cloudflare]\napi_token = test\nwebui_password =\n")
        cfg = config_mod.Config(self.path)
        webui._migrate_password_hash(cfg)
        self.assertEqual(cfg.webui_password, "")


if __name__ == "__main__":
    unittest.main()