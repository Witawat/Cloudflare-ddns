"""กันรันซ้ำ (single instance) — file lock ข้าม process + session.

สาเหตุ: เปิด exe/run/service ซ้ำ 2 instance พร้อมกัน → heartbeat ส่งเบิ้ลทุกนาที
(ในแต่ละ process มันกันส่งซ้ำของตัวเองได้ แต่กันข้าม process ไม่ได้)

ใช้ file lock (msvcrt) แทน named mutex เพราะ:
- file lock เห็นข้าม session (service อยู่ session 0, exe ผู้ใช้อยู่ session 1 —
  named mutex ธรรมดาเป็น per-session จะมองไม่เห็นกัน)
- ไม่ต้อง Global\\ prefix ที่ต้อง admin สร้าง
- OS ปลด lock อัตโนมัติเมื่อ process ตาย (ไม่ต้อง cleanup ค้าง)

ฟังก์ชัน:
- acquire_instance_lock(config_path)  ครอบยาวทั้ง process (กันรันซ้ำ) — คืน True/False
- release_instance_lock()             ปลด (ไม่ค่อยต้องเรียก — process ตายปลดเอง)
- file_lock(path)                     context manager ครอบสั้น ๆ (กันอ่าน-เขียนพร้อมกัน)
"""

import logging
import os

try:
    import msvcrt
except ImportError:  # ไม่ใช่ Windows (dev บน mac/linux) — ปล่อยผ่าน ไม่กัน
    msvcrt = None

from . import config as config_mod

log = logging.getLogger("cloudflare-ddns")

_log_lock_fd = None


def instance_lock_path(config_path=None):
    return os.path.join(config_mod.data_dir_for(config_path), "instance.lock")


def _lock_fd_on(fd):
    """lock 1 byte แรกของ fd (LK_NBLCK ไม่บล็อก) — โยน OSError ถ้า lock ไม่ได้"""
    if os.fstat(fd).st_size == 0:
        os.write(fd, b"\x00")
        os.fsync(fd)
    os.lseek(fd, 0, os.SEEK_SET)
    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)


def acquire_instance_lock(config_path=None):
    """ครอบ lock รันซ้ำทั้ง process — คืน True ถ้าเป็น instance แรก (ได้ lock),
    False ถ้ามี instance อื่นรันอยู่แล้ว"""
    global _log_lock_fd
    if _log_lock_fd is not None:
        return True
    if msvcrt is None:
        return True
    fd = None
    try:
        fd = os.open(instance_lock_path(config_path), os.O_CREAT | os.O_RDWR)
        _lock_fd_on(fd)
        _log_lock_fd = fd
        return True
    except OSError:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        log.warning("กันรันซ้ำ: มี instance อื่นรันอยู่แล้ว (lock ถูกครอบ) — ไม่เริ่ม loop ซ้ำ")
        return False


def release_instance_lock():
    global _log_lock_fd
    if _log_lock_fd is None:
        return
    try:
        msvcrt.locking(_log_lock_fd, msvcrt.LK_UNLCK, 1)
    except OSError:
        pass
    try:
        os.close(_log_lock_fd)
    except OSError:
        pass
    _log_lock_fd = None


class file_lock:
    """context manager — lock ไฟล์สั้น ๆ (ครอบช่วงอ่าน-เขียน) ข้าม process.
    ใช้ตรวจ `.locked` ว่าครอบได้หรือไม่ (อีก process ครอบอยู่)"""

    def __init__(self, path):
        self.path = path
        self.fd = None

    def __enter__(self):
        if msvcrt is None:
            return self
        fd = None
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_RDWR)
            _lock_fd_on(fd)
            self.fd = fd
        except OSError:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
        return self

    @property
    def locked(self):
        return self.fd is not None

    def __exit__(self, exc_type, exc, tb):
        if self.fd is not None:
            try:
                msvcrt.locking(self.fd, msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
            try:
                os.close(self.fd)
            except OSError:
                pass
            self.fd = None
        return False
