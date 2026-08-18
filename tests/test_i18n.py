"""เทสต์ i18n: t() named/positional/missing, detect_lang, validate_dicts, build_message th/en, config.language→notify.lang"""

import os
import tempfile
import unittest

from cloudflare_ddns import config as config_mod
from cloudflare_ddns import i18n
from cloudflare_ddns import notifier

MINIMAL_INI = """[cloudflare]
api_token = test-token
interval_seconds = 60
use_ipv4 = true
use_ipv6 = true

[record:home.example.com]
zone = example.com
"""


def write_ini(path, text):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return path


class TranslateTest(unittest.TestCase):
    """t() แทนที่ named/positional + missing key ไม่ crash"""

    def test_named_vars_replaced(self):
        out = i18n.t("th", "tg.event.start", ts="[18/08 12:00]", host="PC-1")
        self.assertIn("[18/08 12:00]", out)
        self.assertIn("PC-1", out)

    def test_positional_vars_replaced(self):
        out = i18n.t("th", "tg.run.summary").format(3, 1, 0)
        self.assertIn("ตรวจ 3 รายการ", out)
        self.assertIn("เปลี่ยน 1", out)

    def test_missing_key_returns_key(self):
        out = i18n.t("th", "no.such.key")
        self.assertEqual(out, "no.such.key")

    def test_missing_var_kept_untouched(self):
        # ตัวแปรที่ส่งไม่ครบ -> ไม่ crash คง {var} ไว้
        out = i18n.t("th", "tg.event.start", ts="[x]")
        self.assertIn("{host}", out)

    def test_invalid_lang_falls_back_th(self):
        out = i18n.t("fr", "login.wrong")
        self.assertIn("รหัสผ่าน", out)

    def test_en_translated(self):
        out = i18n.t("en", "login.wrong")
        self.assertIn("Incorrect password", out)


class DetectLangTest(unittest.TestCase):
    """detect_lang: cookie ชนะ Accept-Language -> fallback th"""

    def test_accept_language_en(self):
        self.assertEqual(i18n.detect_lang("", "en-US,en;q=0.9"), "en")

    def test_cookie_wins_over_accept(self):
        self.assertEqual(i18n.detect_lang("cfddns_lang=th", "en-US,en"), "th")
        self.assertEqual(i18n.detect_lang("cfddns_lang=en", "th-TH"), "en")

    def test_unknown_language_falls_back_th(self):
        self.assertEqual(i18n.detect_lang("", "fr-FR"), "th")
        self.assertEqual(i18n.detect_lang("", ""), "th")


class ValidateDictsTest(unittest.TestCase):
    """th/en มี key ชุดเดียวกัน (กัน drift)"""

    def test_no_mismatch(self):
        self.assertEqual(i18n.validate_dicts(), [])


class BuildMessageLangTest(unittest.TestCase):
    """build_message ภาษาไทย/อังกฤษ + ใช้ชื่อเครื่อง"""

    def test_th_event_header(self):
        msg = notifier.build_message(notifier.EVENT_START, "detail", name="PC", lang="th")
        self.assertIn("เริ่มทำงาน", msg)
        self.assertIn("PC", msg)

    def test_en_event_header(self):
        msg = notifier.build_message(notifier.EVENT_START, "detail", name="PC", lang="en")
        self.assertIn("started", msg)
        self.assertNotIn("เริ่มทำงาน", msg)

    def test_ip_change_th_en(self):
        self.assertIn("IP เปลี่ยน", notifier.build_message(notifier.EVENT_IP_CHANGE, "1.2.3.4", lang="th"))
        self.assertIn("IP changed", notifier.build_message(notifier.EVENT_IP_CHANGE, "1.2.3.4", lang="en"))


class ConfigLanguageToNotifierTest(unittest.TestCase):
    """config.language -> TelegramNotifier.lang"""

    def test_language_from_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "config.ini")
            write_ini(path, MINIMAL_INI.replace(
                "interval_seconds = 60", "interval_seconds = 60\nlanguage = en"
            ))
            cfg = config_mod.Config(path)
            n = notifier.TelegramNotifier.from_config(cfg)
            self.assertEqual(n.lang, "en")

    def test_default_language_th(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "config.ini")
            write_ini(path, MINIMAL_INI)
            cfg = config_mod.Config(path)
            self.assertEqual(cfg.language, "th")

    def test_invalid_language_normalized_to_th(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "config.ini")
            write_ini(path, MINIMAL_INI.replace(
                "interval_seconds = 60", "interval_seconds = 60\nlanguage = fr"
            ))
            cfg = config_mod.Config(path)
            self.assertEqual(cfg.language, "th")


if __name__ == "__main__":
    unittest.main()
