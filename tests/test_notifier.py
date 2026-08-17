"""เทสต์ notifier: queue (save/load/rotate), Telegram password reset"""

import os
import tempfile
import unittest
from unittest import mock

from cloudflare_ddns import config as config_mod
from cloudflare_ddns import notifier

MINIMAL_INI = """[cloudflare]
api_token = test-token
interval_seconds = 60
use_ipv4 = true
use_ipv6 = true
telegram_bot_token = 123456:TESTTOKEN
telegram_chat_id = 42

[record:home.example.com]
zone = example.com
"""


class QueueTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "notify_queue.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_save_load_roundtrip(self):
        notifier.save_queue(["a", "b"], self.path)
        self.assertEqual(notifier.load_queue(self.path), ["a", "b"])

    def test_same_content_does_not_touch_file(self):
        notifier.save_queue(["a"], self.path)
        before = os.path.getmtime(self.path)
        notifier.save_queue(["a"], self.path)
        self.assertEqual(os.path.getmtime(self.path), before)

    def test_changed_content_creates_backup(self):
        notifier.save_queue(["a"], self.path)
        notifier.save_queue(["a", "b"], self.path)
        self.assertTrue(os.path.isfile(self.path + ".bak"))
        notifier.save_queue(["a", "b", "c"], self.path)
        self.assertTrue(os.path.isfile(self.path + ".2.bak"))

    def test_load_empty_or_missing(self):
        self.assertEqual(notifier.load_queue(self.path), [])


class ApplyWebuiPasswordTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "config.ini")
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write(MINIMAL_INI)
        self.cfg = config_mod.Config(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_writes_hash(self):
        ok, message = notifier._apply_webui_password(self.cfg, self.path, "new-secret")
        self.assertTrue(ok, message)
        self.assertTrue(config_mod.password_is_hash(self.cfg.webui_password))
        self.assertNotEqual(self.cfg.webui_password, "new-secret")
        self.assertTrue(
            config_mod.password_hash("new-secret", self.path) == self.cfg.webui_password
        )

    def test_writes_hash_even_when_config_incomplete(self):
        # config ไม่ครบ (ไม่มี record) — กู้รหัสต้องใช้ได้เสมอ
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write("[cloudflare]\napi_token = test\n")
        ok, message = notifier._apply_webui_password(self.cfg, self.path, "new-secret")
        self.assertTrue(ok, message)
        self.assertTrue(config_mod.password_is_hash(self.cfg.webui_password))

    def test_rejects_broken_config(self):
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write("[broken\nnope")
        ok, _ = notifier._apply_webui_password(self.cfg, self.path, "x")
        self.assertFalse(ok)


class TelegramResetTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "config.ini")
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write(MINIMAL_INI.replace(
                "telegram_chat_id = 42",
                "telegram_chat_id = 42\ntelegram_allow_reset = true",
            ))
        self.cfg = config_mod.Config(self.path)
        self.patcher_updates = mock.patch.object(notifier, "_tg_updates", return_value=[])
        self.mock_updates = self.patcher_updates.start()
        self.sent = []
        self.patcher_send = mock.patch.object(notifier.TelegramNotifier, "send_raw")
        self.mock_send = self.patcher_send.start()
        self.mock_send.return_value = (True, "")
        notifier._reset_state["awaiting_confirm"] = False
        notifier._reset_state["last_ask"] = 0.0
        notifier._last_reset_time.clear()
        notifier._updates_offset.clear()

    def tearDown(self):
        self.patcher_updates.stop()
        self.patcher_send.stop()
        self.tmp.cleanup()

    def _update(self, chat_id, text, update_id=1):
        return {
            "update_id": update_id,
            "message": {"chat": {"id": chat_id}, "text": text},
        }

    def test_opt_out_does_nothing(self):
        cfg = config_mod.Config(self.path)
        cfg.telegram_allow_reset = False
        notifier.check_telegram_commands(cfg, self.path)
        self.mock_updates.assert_not_called()

    def test_other_chat_ignored(self):
        self.mock_updates.return_value = [self._update(999, "reset password")]
        notifier.check_telegram_commands(cfg=self.cfg, config_path=self.path)
        self.mock_send.assert_not_called()

    def test_confirm_changes_password(self):
        self.mock_updates.return_value = [self._update(42, "reset password")]
        notifier.check_telegram_commands(self.cfg, self.path)
        self.mock_updates.return_value = [self._update(42, "yes")]
        notifier.check_telegram_commands(self.cfg, self.path)
        self.assertTrue(self.mock_send.called)
        self.assertTrue(config_mod.password_is_hash(self.cfg.webui_password))
        # รหัสใหม่ถูกส่งกลับทาง Telegram
        texts = [c.args[0] for c in self.mock_send.call_args_list]
        self.assertTrue(any("รหัสผ่านหน้าเว็บใหม่" in t for t in texts))

    def test_cooldown_blocks_second_reset(self):
        self.mock_updates.return_value = [self._update(42, "reset password")]
        notifier.check_telegram_commands(self.cfg, self.path)
        self.mock_updates.return_value = [self._update(42, "yes")]
        notifier.check_telegram_commands(self.cfg, self.path)
        first = self.cfg.webui_password
        # reset อีกทันที — ต้องโดนกัน cooldown
        self.mock_updates.return_value = [self._update(42, "reset password")]
        notifier.check_telegram_commands(self.cfg, self.path)
        self.mock_updates.return_value = [self._update(42, "yes")]
        notifier.check_telegram_commands(self.cfg, self.path)
        self.assertEqual(self.cfg.webui_password, first)


class TelegramCommandTest(unittest.TestCase):
    """คำสั่งควบคุมผ่าน Telegram: /help /status /ip /update /log /run /tunnel /restart"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "config.ini")
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write(MINIMAL_INI.replace(
                "telegram_chat_id = 42",
                "telegram_chat_id = 42\ntelegram_allow_reset = true",
            ))
        self.cfg = config_mod.Config(self.path)
        self.patcher_updates = mock.patch.object(notifier, "_tg_updates", return_value=[])
        self.mock_updates = self.patcher_updates.start()
        self.patcher_send = mock.patch.object(notifier.TelegramNotifier, "send_raw")
        self.mock_send = self.patcher_send.start()
        self.mock_send.return_value = (True, "")
        notifier._reset_state["awaiting_confirm"] = False
        notifier._updates_offset.clear()

    def tearDown(self):
        self.patcher_updates.stop()
        self.patcher_send.stop()
        self.tmp.cleanup()

    def _update(self, chat_id, text, update_id=1):
        return {
            "update_id": update_id,
            "message": {"chat": {"id": chat_id}, "text": text},
        }

    def _run(self, text):
        self.mock_updates.return_value = [self._update(42, text)]
        notifier.check_telegram_commands(self.cfg, self.path)

    def test_help(self):
        self._run("/help")
        texts = [c.args[0] for c in self.mock_send.call_args_list]
        self.assertTrue(any("/status" in t and "/run" in t for t in texts))

    def test_status_uses_engine(self):
        with mock.patch("cloudflare_ddns.ddns.DDNSEngine") as m:
            m.return_value.status.return_value = {
                "records": {"home.example.com|A": "1.2.3.4"},
                "last_run": "2026-08-17T00:00:00",
                "record_errors": {},
            }
            self._run("/status")
        texts = [c.args[0] for c in self.mock_send.call_args_list]
        self.assertTrue(any("home.example.com|A: 1.2.3.4" in t for t in texts))

    def test_ip(self):
        with mock.patch("cloudflare_ddns.ip_detect.get_public_ip", return_value="9.9.9.9"):
            self._run("/ip")
        texts = [c.args[0] for c in self.mock_send.call_args_list]
        self.assertTrue(any("9.9.9.9" in t for t in texts))

    def test_update(self):
        with mock.patch("cloudflare_ddns.webui._update_check_data") as m:
            m.return_value = {"ok": True, "has_update": True, "latest": "9.9.9", "url": "https://x"}
            self._run("/update")
        texts = [c.args[0] for c in self.mock_send.call_args_list]
        self.assertTrue(any("9.9.9" in t for t in texts))

    def test_log(self):
        log_dir = os.path.join(self.tmp.name, "logs")
        os.makedirs(log_dir, exist_ok=True)
        with open(os.path.join(log_dir, "cloudflare-ddns.log"), "w", encoding="utf-8") as handle:
            handle.write("line1\nline2\n")
        self.cfg.log_dir = log_dir
        self._run("/log")
        texts = [c.args[0] for c in self.mock_send.call_args_list]
        self.assertTrue(any("line2" in t for t in texts))

    def test_run_starts_thread_and_replies(self):
        self._run("/run")
        texts = [c.args[0] for c in self.mock_send.call_args_list]
        self.assertTrue(any("กำลังรันรอบ DDNS" in t for t in texts))

    def test_restart_calls_service(self):
        with mock.patch("cloudflare_ddns.service.restart_service", return_value="restarted") as m, \
             mock.patch("cloudflare_ddns.webui._in_service", return_value=False):
            self._run("/restart")
        m.assert_called_once()
        texts = [c.args[0] for c in self.mock_send.call_args_list]
        self.assertTrue(any("restarted" in t for t in texts))

    def test_unknown_command_no_reply(self):
        self._run("/nosuch")
        self.mock_send.assert_not_called()


if __name__ == "__main__":
    unittest.main()