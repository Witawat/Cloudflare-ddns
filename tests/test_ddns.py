"""เทสต์ ddns: dry-run ไม่เขียน state, consensus ใน _sync_family, run_once error path"""

import os
import sys
import tempfile
import unittest
from unittest import mock

from cloudflare_ddns import cloudflare_api
from cloudflare_ddns import config as config_mod
from cloudflare_ddns import ddns

MINIMAL_INI = """[cloudflare]
api_token = test-token
interval_seconds = 60
use_ipv4 = true
use_ipv6 = true

[record:home.example.com]
zone = example.com
"""


class DryRunStateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "config.ini")
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write(MINIMAL_INI)
        self.state_path = config_mod.state_path_for(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_dry_run_does_not_write_state(self):
        engine = ddns.DDNSEngine(self.path, dry_run=True)
        engine._state = {"records": {"home.example.com|A": "1.2.3.4"}}
        engine._save_state()
        self.assertFalse(os.path.exists(self.state_path))

    def test_normal_writes_state_next_to_config(self):
        engine = ddns.DDNSEngine(self.path, dry_run=False)
        engine._state = {"records": {"home.example.com|A": "1.2.3.4"}}
        engine._save_state()
        self.assertTrue(os.path.exists(self.state_path))
        self.assertEqual(config_mod.state_path_for(self.path), self.state_path)


class SyncFamilyConsensusTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "config.ini")
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write(MINIMAL_INI)
        self.engine = ddns.DDNSEngine(self.path, dry_run=True)
        self.engine._state = {}
        self.api = mock.Mock()
        self.rec = config_mod.RecordConfig(name="home", zone="example.com")

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_ip_returns_no_ip_action(self):
        with mock.patch.object(ddns.ip_detect, "get_public_ip", return_value=None):
            result = self.engine._sync_family(
                self.api, "zone-1", self.rec, "home.example.com", 4, ddns._NullNotifier(),
                consensus=2,
            )
        self.assertEqual(result["action"], "no-ip")
        self.api.update_record.assert_not_called()

    def test_consensus_used(self):
        with mock.patch.object(ddns.ip_detect, "get_public_ip", return_value="1.2.3.4") as m:
            self.engine._sync_family(
                self.api, "zone-1", self.rec, "home.example.com", 4, ddns._NullNotifier(),
                consensus=2,
            )
        m.assert_called_once_with(4, consensus=2)


class RunOnceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "config.ini")
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write(MINIMAL_INI)
        self.engine = ddns.DDNSEngine(self.path, dry_run=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_token_returns_error_summary(self):
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write(MINIMAL_INI.replace("api_token = test-token", "api_token ="))
        summary = self.engine.run_once()
        self.assertTrue(summary)
        self.assertEqual(summary[0]["action"], "error")

    def test_zone_lookup_error_marks_record_error(self):
        api = mock.Mock()
        api.get_zone_id.side_effect = cloudflare_api.CloudflareError("boom")
        with mock.patch.object(ddns.cloudflare_api, "CloudflareAPI", return_value=api):
            summary = self.engine.run_once()
        self.assertEqual(summary[0]["action"], "error")
        self.assertIn("boom", summary[0]["message"])


class PeriodicUpdateCheckTest(unittest.TestCase):
    """เช็คเวอร์ชันใหม่ทุก 24 ชม. — รันยาว ๆ ก็รู้ว่ามีรุ่นใหม่"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "config.ini")
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write(MINIMAL_INI)
        self.cfg = config_mod.Config(self.path)
        ddns._periodic_update_at = 0.0
        # patch ฟังก์ชันจริง (ไม่ใช้ sys.modules — from . import webui คืน module จริงจาก package attr)
        self.patcher = mock.patch("cloudflare_ddns.webui._startup_update_check")
        self.mock_check = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.tmp.cleanup()

    def test_checks_on_first_call(self):
        ddns._periodic_update_check(self.cfg, self.path)
        self.mock_check.assert_called_once()

    def test_skips_within_24h(self):
        ddns._periodic_update_check(self.cfg, self.path)
        self.mock_check.reset_mock()
        ddns._periodic_update_check(self.cfg, self.path)
        self.mock_check.assert_not_called()

    def test_checks_again_after_24h(self):
        ddns._periodic_update_check(self.cfg, self.path)
        ddns._periodic_update_at = 0.0  # จำลองผ่านไป 24 ชม. (reset ค้าง)
        self.mock_check.reset_mock()
        ddns._periodic_update_check(self.cfg, self.path)
        self.mock_check.assert_called_once()


if __name__ == "__main__":
    unittest.main()