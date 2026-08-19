"""เทสต์ heartbeat: กันส่งซ้ำ (30 วิ), กันซ้ำข้าม process (state ไฟล์ + lock), instance lock กันรันซ้ำ"""

import os
import shutil
import tempfile
import types
import unittest

from cloudflare_ddns import config as config_mod
from cloudflare_ddns import heartbeat
from cloudflare_ddns import instance_lock

try:
    import msvcrt
except ImportError:
    msvcrt = None

PING_URL = "https://hc-ping.com/abc"


def _make_cfg(tmp):
    return types.SimpleNamespace(
        path=os.path.join(tmp, "config.ini"),
        language="th",
        healthchecks_url=PING_URL,
        uptimekuma_url="",
    )


class TestHeartbeatPing(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.cfg = _make_cfg(self.tmp)
        heartbeat._last_sent.clear()

    def _patch_ping(self, calls):
        orig = heartbeat._ping
        heartbeat._ping = lambda url, timeout=10: (calls.append(url), (True, ""))[1]
        self.addCleanup(setattr, heartbeat, "_ping", orig)

    def test_ส่งรอบแรกแล้ว_60วิ_ยังไม่ครบ_ข้ามซ้ำ(self):
        calls = []
        self._patch_ping(calls)
        heartbeat.send_ping(self.cfg)
        heartbeat.send_ping(self.cfg)
        self.assertEqual(len(calls), 1)

    def test_เกิน_60วิ_ส่งใหม่ได้(self):
        calls = []
        self._patch_ping(calls)
        heartbeat.send_ping(self.cfg)
        # จำลองเวลาเลย 60 วิ (instance ใหม่: memory ว่าง + state ไฟล์ลดลง)
        heartbeat._last_sent.clear()
        state = heartbeat._load_state(self.cfg.path)
        for key in state:
            state[key] -= 70
        heartbeat._save_state(self.cfg.path, state)
        heartbeat.send_ping(self.cfg)
        self.assertEqual(len(calls), 2)

    def test_กันซ้ำข้าม_process_อ่านจากstateไฟล์(self):
        """จำลอง instance อื่นส่งไปแล้ว (state ไฟล์มีเวลาล่าสุด) — instance นี้ต้องข้าม"""
        calls = []
        self._patch_ping(calls)
        heartbeat.send_ping(self.cfg)  # instance แรกส่ง + เขียน state
        heartbeat._last_sent.clear()  # instance ที่สอง (memory ใหม่)
        heartbeat.send_ping(self.cfg)  # อ่าน state ไฟล์ -> ยังไม่ครบ 30 วิ -> ข้าม
        self.assertEqual(len(calls), 1)

    def test_lock_ถูกครอบ_ข้ามรอบ(self):
        """อีก instance กำลังส่งอยู่ (lock ค้าง) — รอบนี้ต้องข้าม ไม่ส่งซ้ำ"""
        calls = []
        self._patch_ping(calls)
        lock_path = os.path.join(config_mod.data_dir_for(self.cfg.path), "heartbeat.lock")
        with instance_lock.file_lock(lock_path) as lock:
            self.assertTrue(lock.locked)
            heartbeat.send_ping(self.cfg)
        self.assertEqual(len(calls), 0)

    def test_fail_ส่งสัญญาณ_fail(self):
        calls = []
        self._patch_ping(calls)
        heartbeat.send_ping(self.cfg, ok=False)
        self.assertEqual(calls, [PING_URL + "/fail"])

    def test_stopped_ส่งสัญญาณ_exit_ไม่โดนrate_limit(self):
        calls = []
        self._patch_ping(calls)
        heartbeat.send_ping(self.cfg, stopped=True)
        heartbeat.send_ping(self.cfg, stopped=True)
        self.assertEqual(calls, [PING_URL + "/exit", PING_URL + "/exit"])

    def test_ไม่มีURLตั้งไว้_ไม่ส่ง(self):
        calls = []
        self._patch_ping(calls)
        empty = types.SimpleNamespace(
            path=self.cfg.path, language="th", healthchecks_url="", uptimekuma_url=""
        )
        heartbeat.send_ping(empty)
        self.assertEqual(len(calls), 0)

    def test_state_path_อยู่ข้างconfig(self):
        self.assertEqual(
            config_mod.heartbeat_state_path_for(self.cfg.path),
            os.path.join(self.tmp, "heartbeat_state.json"),
        )

    def test_ใช้ค่าความถี่จากconfig(self):
        """heartbeat_min_interval = 5 -> ส่งซ้ำได้เมื่อห่าง 6 วิ (ไม่ใช่ 60)"""
        cfg = _make_cfg(self.tmp)
        cfg.heartbeat_min_interval = 5
        calls = []
        self._patch_ping(calls)
        heartbeat.send_ping(cfg)
        heartbeat._last_sent.clear()
        state = heartbeat._load_state(cfg.path)
        for key in state:
            state[key] -= 6
        heartbeat._save_state(cfg.path, state)
        heartbeat.send_ping(cfg)
        self.assertEqual(len(calls), 2)

    def test_ค่าconfigต่ำกว่า5_fall_back_60(self):
        cfg = _make_cfg(self.tmp)
        cfg.heartbeat_min_interval = 1
        calls = []
        self._patch_ping(calls)
        heartbeat.send_ping(cfg)
        heartbeat.send_ping(cfg)
        self.assertEqual(len(calls), 1)


class TestInstanceLock(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.config_path = os.path.join(self.tmp, "config.ini")
        instance_lock.release_instance_lock()

    def tearDown(self):
        instance_lock.release_instance_lock()

    def test_มีinstanceอื่น_ครอบไม่ได้(self):
        if msvcrt is None:
            self.skipTest("ไม่ใช่ Windows — ไม่มี msvcrt")
        # จำลอง instance อื่นครอบ lock ไว้
        lk = instance_lock.file_lock(instance_lock.instance_lock_path(self.config_path))
        lk.__enter__()
        try:
            self.assertTrue(lk.locked)
            self.assertFalse(instance_lock.acquire_instance_lock(self.config_path))
        finally:
            lk.__exit__(None, None, None)
        # ปลดแล้ว — ครอบได้
        self.assertTrue(instance_lock.acquire_instance_lock(self.config_path))

    def test_ครอบแล้วปลด_ได้ใหม่(self):
        if msvcrt is None:
            self.skipTest("ไม่ใช่ Windows — ไม่มี msvcrt")
        self.assertTrue(instance_lock.acquire_instance_lock(self.config_path))
        instance_lock.release_instance_lock()
        self.assertTrue(instance_lock.acquire_instance_lock(self.config_path))


if __name__ == "__main__":
    unittest.main()
