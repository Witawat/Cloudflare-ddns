"""เทสต์ notifier: queue (save/load/rotate), Telegram password reset"""

import os
import tempfile
import time
import unittest
import urllib.error
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


class TestBuildMessage(unittest.TestCase):
    """build_message ใช้ชื่อเครื่องที่ส่งมาหรือ fallback เป็น hostname"""

    def test_with_name(self):
        msg = notifier.build_message(notifier.EVENT_START, "running", name="เครื่องA")
        self.assertIn("· เครื่องA", msg)

    def test_without_name_falls_back_to_hostname(self):
        import socket as _socket
        msg = notifier.build_message(notifier.EVENT_START, "running")
        self.assertIn("· " + _socket.gethostname(), msg)

    def test_from_config_passes_name(self):
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        path = os.path.join(tmp.name, "config.ini")
        with open(path, "w", encoding="utf-8") as f:
            f.write(MINIMAL_INI.replace(
                "telegram_chat_id = 42",
                "telegram_chat_id = 42\ntelegram_command_name = เครื่องA",
            ))
        cfg = config_mod.Config(path)
        n = notifier.TelegramNotifier.from_config(cfg)
        self.assertEqual(n.name, "เครื่องA")
        tmp.cleanup()


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
        notifier._handled_updates.clear()
        notifier._danger_state["command"] = ""

    def tearDown(self):
        self.patcher_updates.stop()
        self.patcher_send.stop()
        self.tmp.cleanup()

    def _update(self, chat_id, text, update_id=1):
        return {
            "update_id": update_id,
            "message": {"chat": {"id": chat_id}, "text": text, "date": int(time.time())},
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
        self.mock_updates.return_value = [self._update(42, "reset password", 1)]
        notifier.check_telegram_commands(self.cfg, self.path)
        self.mock_updates.return_value = [self._update(42, "yes", 2)]
        notifier.check_telegram_commands(self.cfg, self.path)
        self.assertTrue(self.mock_send.called)
        self.assertTrue(config_mod.password_is_hash(self.cfg.webui_password))
        # รหัสใหม่ถูกส่งกลับทาง Telegram
        texts = [c.args[0] for c in self.mock_send.call_args_list]
        self.assertTrue(any("รหัสผ่านหน้าเว็บใหม่" in t for t in texts))

    def test_cooldown_blocks_second_reset(self):
        self.mock_updates.return_value = [self._update(42, "reset password", 1)]
        notifier.check_telegram_commands(self.cfg, self.path)
        self.mock_updates.return_value = [self._update(42, "yes", 2)]
        notifier.check_telegram_commands(self.cfg, self.path)
        first = self.cfg.webui_password
        self.assertTrue(first)
        # reset อีกทันที — ต้องโดนกัน cooldown
        self.mock_updates.return_value = [self._update(42, "reset password", 3)]
        notifier.check_telegram_commands(self.cfg, self.path)
        self.mock_updates.return_value = [self._update(42, "yes", 4)]
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
        notifier._handled_updates.clear()
        notifier._danger_state["command"] = ""

    def tearDown(self):
        self.patcher_updates.stop()
        self.patcher_send.stop()
        self.tmp.cleanup()

    def _update(self, chat_id, text, update_id=1):
        return {
            "update_id": update_id,
            "message": {"chat": {"id": chat_id}, "text": text, "date": int(time.time())},
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
        # /run เป็นคำสั่งอันตราย — ต้องยืนยัน yes ก่อน
        self._run("/run")
        texts = [c.args[0] for c in self.mock_send.call_args_list]
        self.assertTrue(any("เป็นคำสั่งอันตราย" in t for t in texts))
        self.assertFalse(any("กำลังรันรอบ DDNS" in t for t in texts))
        self.mock_updates.return_value = [self._update(42, "yes", 2)]
        notifier.check_telegram_commands(self.cfg, self.path)
        texts = [c.args[0] for c in self.mock_send.call_args_list]
        self.assertTrue(any("กำลังรันรอบ DDNS" in t for t in texts))

    def test_danger_expired_then_other_command_executes(self):
        """BUG: คำสั่งอันตรายหมดเวลาแล้วพิมพ์คำสั่งใหม่ — ต้องประมวลผลคำสั่งใหม่ ไม่กลืน"""
        self._run("/run")
        notifier._danger_state["expires"] = time.time() - 10  # ทำให้หมดเวลา
        self.mock_send.reset_mock()
        self.mock_updates.return_value = [self._update(42, "/status", 2)]
        notifier.check_telegram_commands(self.cfg, self.path)
        texts = [c.args[0] for c in self.mock_send.call_args_list]
        self.assertTrue(any("รอบล่าสุด" in t for t in texts), "คำสั่ง /status ควรประมวลผลต่อ")
        self.assertFalse(any("รอยืนยัน" in t for t in texts))
        self.assertEqual(notifier._danger_state["command"], "")

    def test_danger_expired_yes_does_not_execute(self):
        """BUG: ยืนยันหลังหมดเวลา — ต้องไม่รันคำสั่งอันตราย"""
        self._run("/run")
        notifier._danger_state["expires"] = time.time() - 10
        self.mock_send.reset_mock()
        self.mock_updates.return_value = [self._update(42, "yes", 2)]
        notifier.check_telegram_commands(self.cfg, self.path)
        texts = [c.args[0] for c in self.mock_send.call_args_list]
        self.assertTrue(any("หมดเวลา" in t for t in texts))
        self.assertFalse(any("กำลังรันรอบ DDNS" in t for t in texts))

    def test_danger_command_cancels_pending_reset(self):
        """BUG: พิมพ์ /run ขณะ reset ยังค้าง — ต้องยกเลิก reset (กัน yes ซ้ำไป reset เผลอ)"""
        self.mock_updates.return_value = [self._update(42, "reset password", 1)]
        notifier.check_telegram_commands(self.cfg, self.path)
        self.assertTrue(notifier._reset_state["awaiting_confirm"])
        self.mock_updates.return_value = [self._update(42, "/run", 2)]
        notifier.check_telegram_commands(self.cfg, self.path)
        self.assertFalse(notifier._reset_state["awaiting_confirm"])
        # ยืนยัน /run ด้วย yes — ต้องไม่ reset
        self.mock_send.reset_mock()
        self.mock_updates.return_value = [self._update(42, "yes", 3)]
        notifier.check_telegram_commands(self.cfg, self.path)
        texts = [c.args[0] for c in self.mock_send.call_args_list]
        self.assertTrue(any("กำลังรันรอบ DDNS" in t for t in texts))
        self.assertFalse(any("รหัสผ่านหน้าเว็บใหม่" in t for t in texts))

    def test_list_shows_ddns_and_tunnel(self):
        self.cfg.tunnel_hosts = [
            {"hostname": "app.example.com", "path": "", "protocol": "http", "service": "http://localhost:8080"}
        ]
        self._run("/list")
        texts = [c.args[0] for c in self.mock_send.call_args_list]
        self.assertTrue(any("DDNS records" in t and "home.example.com" in t for t in texts))
        self.assertTrue(any("Tunnel hostnames" in t and "app.example.com" in t for t in texts))

    def test_restart_calls_service(self):
        with mock.patch("cloudflare_ddns.service.restart_service", return_value="restarted") as m, \
             mock.patch("cloudflare_ddns.webui._in_service", return_value=False):
            self._run("/restart")
            # ยังไม่ยืนยัน — service ไม่ถูกเรียก
            m.assert_not_called()
            self.mock_updates.return_value = [self._update(42, "yes", 2)]
            notifier.check_telegram_commands(self.cfg, self.path)
            m.assert_called_once()
        texts = [c.args[0] for c in self.mock_send.call_args_list]
        self.assertTrue(any("restarted" in t for t in texts))

    def test_danger_confirm_cancel_with_no(self):
        self._run("/restart")
        self.mock_updates.return_value = [self._update(42, "no", 2)]
        notifier.check_telegram_commands(self.cfg, self.path)
        texts = [c.args[0] for c in self.mock_send.call_args_list]
        self.assertTrue(any("ยกเลิก" in t for t in texts))

    def test_tunnel_stop_requires_confirm(self):
        with mock.patch("cloudflare_ddns.tunnel.TunnelManager") as m:
            mgr = m.return_value
            mgr.stop.return_value = "stopped"
            self._run("/tunnel stop")
            mgr.stop.assert_not_called()
            self.mock_updates.return_value = [self._update(42, "yes", 2)]
            notifier.check_telegram_commands(self.cfg, self.path)
            mgr.stop.assert_called_once()

    def test_notify_toggles_and_saves(self):
        self.mock_updates.return_value = [self._update(42, "/notify error off", 1)]
        notifier.check_telegram_commands(self.cfg, self.path)
        self.assertFalse(self.cfg.notify_error)
        self.mock_updates.return_value = [self._update(42, "/notify error", 2)]
        notifier.check_telegram_commands(self.cfg, self.path)
        self.assertTrue(self.cfg.notify_error)
        self.mock_updates.return_value = [self._update(42, "/notify all off", 3)]
        notifier.check_telegram_commands(self.cfg, self.path)
        self.assertFalse(self.cfg.notify_error)
        self.assertFalse(self.cfg.notify_ip_change)

    def test_notify_unknown_event(self):
        self._run("/notify bogus")
        texts = [c.args[0] for c in self.mock_send.call_args_list]
        self.assertTrue(any("ไม่รู้จัก" in t for t in texts))

    def test_unknown_command_no_reply(self):
        self._run("/nosuch")
        self.mock_send.assert_not_called()

    def test_name_target_mismatch_ignored(self):
        """คำสั่งระบุ @ชื่อ ที่ไม่ตรงกับเครื่องนี้ -> ไม่ตอบ"""
        self.cfg.telegram_command_name = "เครื่องA"
        with mock.patch("cloudflare_ddns.ip_detect.get_public_ip", return_value="9.9.9.9") as m:
            self._run("/ip @เครื่องB")
        m.assert_not_called()
        self.mock_send.assert_not_called()

    def test_name_target_match_executes(self):
        """คำสั่งระบุ @ชื่อ ที่ตรงกับเครื่องนี้ -> ตอบปกติ"""
        self.cfg.telegram_command_name = "เครื่องA"
        with mock.patch("cloudflare_ddns.ip_detect.get_public_ip", return_value="9.9.9.9"):
            self._run("/ip @เครื่องA")
        texts = [c.args[0] for c in self.mock_send.call_args_list]
        self.assertTrue(any("9.9.9.9" in t for t in texts))

    def test_name_case_insensitive(self):
        self.cfg.telegram_command_name = "PC-SERVER-01"
        with mock.patch("cloudflare_ddns.ip_detect.get_public_ip", return_value="9.9.9.9"):
            self._run("/ip @pc-server-01")
        texts = [c.args[0] for c in self.mock_send.call_args_list]
        self.assertTrue(any("9.9.9.9" in t for t in texts))

    def test_name_fallback_to_hostname(self):
        """ไม่ตั้ง telegram_command_name -> ใช้ hostname ของระบบเป็นชื่อ"""
        import socket as _socket

        host = _socket.gethostname()
        with mock.patch("cloudflare_ddns.ip_detect.get_public_ip", return_value="9.9.9.9"):
            self._run("/ip @" + host)
        texts = [c.args[0] for c in self.mock_send.call_args_list]
        self.assertTrue(any("9.9.9.9" in t for t in texts))

    def test_reply_prefixed_with_machine_name(self):
        """คำตอบทุกข้อความขึ้นต้นด้วย [ชื่อเครื่อง] — รู้ว่ามาจากเครื่องไหน"""
        self.cfg.telegram_command_name = "เครื่องA"
        with mock.patch("cloudflare_ddns.ip_detect.get_public_ip", return_value="9.9.9.9"):
            self._run("/ip")
        texts = [c.args[0] for c in self.mock_send.call_args_list]
        self.assertTrue(any(t.startswith("[เครื่องA] ") for t in texts))

    def test_reset_with_name_mismatch_ignored(self):
        """reset password ระบุ @ชื่อไม่ตรง -> ไม่เข้ากระบวนการกู้รหัส"""
        self.cfg.telegram_command_name = "เครื่องA"
        self._run("reset password @เครื่องB")
        self.mock_send.assert_not_called()
        self.assertFalse(notifier._reset_state["awaiting_confirm"])

    def test_foreign_blocks_confirm_until_owner_takes_it(self):
        """คำสั่งของเครื่องอื่นคั่นหน้าคำสั่งของเรา -> เรายังตอบ แต่ไม่ confirm offset (กันขโมยคำสั่ง)"""
        self.cfg.telegram_command_name = "เครื่องA"
        token = "123456:TESTTOKEN"
        self.mock_updates.return_value = [
            self._update(42, "/ip @เครื่องB", 1),
            self._update(42, "/ip", 2),
        ]
        with mock.patch("cloudflare_ddns.ip_detect.get_public_ip", return_value="9.9.9.9"):
            notifier.check_telegram_commands(self.cfg, self.path)
        texts = [c.args[0] for c in self.mock_send.call_args_list]
        self.assertTrue(any("9.9.9.9" in t for t in texts))
        self.assertEqual(notifier._updates_offset.get(token, 0), 0, "ห้าม confirm ข้ามคำสั่งเครื่องอื่น")
        # รอบถัดไป ยังรับซ้ำแต่ไม่ตอบซ้ำ (dedupe) และยังไม่ confirm
        self.mock_send.reset_mock()
        notifier.check_telegram_commands(self.cfg, self.path)
        self.mock_send.assert_not_called()
        self.assertEqual(notifier._updates_offset.get(token, 0), 0)
        # เครื่อง B รับคำสั่งของตัวเองไปแล้ว -> คราวนี้ confirm ได้ (offset=3 = confirm เฉพาะ id 2)
        self.mock_updates.return_value = [self._update(42, "/ip", 2)]
        with mock.patch("cloudflare_ddns.ip_detect.get_public_ip", return_value="9.9.9.9"):
            notifier.check_telegram_commands(self.cfg, self.path)
        self.assertEqual(notifier._updates_offset.get(token, 0), 3)

    def test_own_command_before_foreign_confirms_prefix(self):
        """คำสั่งของเรามาก่อนคำสั่งเครื่องอื่น -> confirm เฉพาะส่วนของเรา ไม่ทับของเครื่องอื่น"""
        self.cfg.telegram_command_name = "เครื่องA"
        token = "123456:TESTTOKEN"
        self.mock_updates.return_value = [
            self._update(42, "/ip", 1),
            self._update(42, "/ip @เครื่องB", 2),
        ]
        with mock.patch("cloudflare_ddns.ip_detect.get_public_ip", return_value="9.9.9.9"):
            notifier.check_telegram_commands(self.cfg, self.path)
        # offset=2 = confirm เฉพาะ id 1 (confirm = update_id < offset) — id 2 ของเครื่อง B ยังรอคิวอยู่
        self.assertEqual(notifier._updates_offset.get(token, 0), 2)
        # ตรวจว่า id 2 (คำสั่งเครื่องอื่น) ยังไม่ถูก confirm — รอบหน้า poll ยังเห็น
        self.mock_updates.return_value = [self._update(42, "/ip @เครื่องB", 2)]
        notifier.check_telegram_commands(self.cfg, self.path)
        self.assertEqual(notifier._updates_offset.get(token, 0), 2, "ห้าม advance ข้ามคำสั่งเครื่องอื่น")

    def test_stale_foreign_dropped_after_timeout(self):
        """คำสั่งของเครื่องอื่นค้างเกิน 10 นาที (เครื่องเป้าออฟไลน์) -> ทิ้ง ไม่บล็อกคิว"""
        self.cfg.telegram_command_name = "เครื่องA"
        token = "123456:TESTTOKEN"
        old = int(time.time()) - 3600
        self.mock_updates.return_value = [
            {"update_id": 1, "message": {"chat": {"id": 42}, "text": "/ip @เครื่องB", "date": old}},
            self._update(42, "/ip", 2),
        ]
        with mock.patch("cloudflare_ddns.ip_detect.get_public_ip", return_value="9.9.9.9"):
            notifier.check_telegram_commands(self.cfg, self.path)
        texts = [c.args[0] for c in self.mock_send.call_args_list]
        self.assertTrue(any("9.9.9.9" in t for t in texts))
        # offset=3 = confirm ทั้ง id 1 (ทิ้งของค้าง) และ id 2 (ของเรา)
        self.assertEqual(notifier._updates_offset.get(token, 0), 3)


class TgUpdatesNetTest(unittest.TestCase):
    """เทสต์ _tg_updates ตรง ๆ (เครือข่ายจำลอง — ห้ามอยู่ในคลาสที่ patch _tg_updates)"""

    def test_409_retries_then_gives_up(self):
        """409 (bot lock) -> ลองใหม่ 2 รอบแล้วถอย ไม่ลบ webhook"""
        err = urllib.error.HTTPError("https://api.telegram.org", 409, "Conflict", {}, None)
        with mock.patch("urllib.request.urlopen", side_effect=err), \
             mock.patch.object(notifier.time, "sleep"), \
             mock.patch.object(notifier, "_tg_api", return_value={"ok": True}) as m_api:
            self.assertEqual(notifier._tg_updates("t", 0), [])
        m_api.assert_not_called()

    def test_429_backs_off(self):
        """429 flood wait -> รอตาม retry_after แล้วข้ามรอบ"""
        import io

        body = io.BytesIO(b'{"ok":false,"parameters":{"retry_after":3}}')
        err = urllib.error.HTTPError("https://api.telegram.org", 429, "Too Many Requests", {}, body)
        with mock.patch("urllib.request.urlopen", side_effect=err), \
             mock.patch.object(notifier.time, "sleep") as m_sleep:
            self.assertEqual(notifier._tg_updates("t", 0), [])
        m_sleep.assert_called_once_with(4)


class TunnelTextTest(unittest.TestCase):
    """_tg_tunnel_text: start/stop ไม่มี tuple หลุด (unpack (ok, message))"""

    def _cfg(self):
        tmp = tempfile.TemporaryDirectory()
        path = os.path.join(tmp.name, "config.ini")
        with open(path, "w", encoding="utf-8") as f:
            f.write(MINIMAL_INI)
        cfg = config_mod.Config(path)
        cfg._tmp = tmp  # เก็บไว้กัน cleanup
        return cfg

    def test_start_uses_message_not_tuple(self):
        cfg = self._cfg()
        try:
            fake = mock.Mock()
            fake.start.return_value = (True, "tunnel รันอยู่แล้ว")
            with mock.patch("cloudflare_ddns.tunnel.TunnelManager", return_value=fake):
                out = notifier._tg_tunnel_text(cfg, "start", "th")
            self.assertIn("tunnel รันอยู่แล้ว", out)
            self.assertNotIn("True", out)  # ไม่เอา tuple หลุด
        finally:
            cfg._tmp.cleanup()

    def test_stop_uses_message_not_tuple(self):
        cfg = self._cfg()
        try:
            fake = mock.Mock()
            fake.stop.return_value = (True, "หยุด tunnel แล้ว")
            with mock.patch("cloudflare_ddns.tunnel.TunnelManager", return_value=fake):
                out = notifier._tg_tunnel_text(cfg, "stop", "th")
            self.assertIn("หยุด tunnel แล้ว", out)
            self.assertNotIn("True", out)
        finally:
            cfg._tmp.cleanup()

    def test_start_en_language(self):
        cfg = self._cfg()
        try:
            fake = mock.Mock()
            fake.start.return_value = (True, "tunnel already running")
            with mock.patch("cloudflare_ddns.tunnel.TunnelManager", return_value=fake):
                out = notifier._tg_tunnel_text(cfg, "start", "en")
            self.assertIn("Start tunnel: tunnel already running", out)
        finally:
            cfg._tmp.cleanup()


if __name__ == "__main__":
    unittest.main()