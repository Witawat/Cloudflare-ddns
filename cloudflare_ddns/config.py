"""อ่าน/เขียน/ตรวจสอบ config.ini.

รูปแบบ config:

    [cloudflare]
    api_token = <API token>
    interval_seconds = 60
    use_ipv4 = true
    use_ipv6 = true
    webui_port = 8123
    webui_password =

    [record:home.example.com]
    zone = example.com
    proxied = false
    ttl = 60
    ipv4 = true
    ipv6 = true
"""

import configparser
import logging
import os
import re
import socket
import sys

from . import __version__

log = logging.getLogger("cloudflare-ddns")

if getattr(sys, "frozen", False):
    # ตอนเป็น exe: หา config.ini จากโฟลเดอร์เดียวกับตัว exe (วางข้าง ๆ กันก็ใช้ได้)
    PROJECT_DIR = os.path.dirname(sys.executable)
else:
    PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG_PATH = os.path.join(PROJECT_DIR, "config.ini")
# ข้อมูลทั้งหมด (state, queue, log) อยู่ข้าง exe เพื่อให้ย้ายโฟลเดอร์ได้ทั้งชุด
DEFAULT_DATA_DIR = PROJECT_DIR
DEFAULT_LOG_DIR = os.path.join(DEFAULT_DATA_DIR, "logs")
DEFAULT_STATE_PATH = os.path.join(DEFAULT_DATA_DIR, "state.json")
# ตำแหน่งเดิม (ก่อนย้าย) ใช้ย้ายข้อมูลให้อัตโนมัติครั้งเดียว
LEGACY_DATA_DIR = os.path.join(
    os.environ.get("PROGRAMDATA", r"C:\ProgramData"), "CloudflareDDNS"
)


def migrate_legacy_data(config_path=None):
    """ย้ายข้อมูลจากโฟลเดอร์ ProgramData เดิมมาข้าง config ที่ใช้ (ครั้งเดียว, idempotent).

    ย้าย: state.json, notify_queue.json และโฟลเดอร์ logs/ ทั้งหมด
    """
    data_dir = data_dir_for(config_path)
    if LEGACY_DATA_DIR == data_dir:
        return
    if not os.path.isdir(LEGACY_DATA_DIR):
        return
    import shutil

    for name in ("state.json", "notify_queue.json"):
        src = os.path.join(LEGACY_DATA_DIR, name)
        dst = os.path.join(data_dir, name)
        if os.path.isfile(src) and not os.path.isfile(dst):
            try:
                shutil.copy2(src, dst)
                log.info("ย้าย %s มาอยู่ข้าง exe แล้ว", name)
            except OSError as exc:
                log.warning("ย้าย %s ไม่ได้: %s", name, exc)
    src_logs = os.path.join(LEGACY_DATA_DIR, "logs")
    dst_logs = os.path.join(data_dir, "logs")
    if os.path.isdir(src_logs) and not os.path.isdir(dst_logs):
        try:
            shutil.copytree(src_logs, dst_logs)
            log.info("ย้ายโฟลเดอร์ logs มาอยู่ข้าง exe แล้ว")
        except OSError as exc:
            log.warning("ย้าย logs ไม่ได้: %s", exc)

DEFAULT_INTERVAL = 60
MIN_INTERVAL = 15


def data_dir_for(config_path=None):
    """โฟลเดอร์ข้อมูล runtime (state/queue/log) — อยู่ข้าง config.ini ที่ใช้จริง.

    config.ini ถูกวางข้าง exe เสมอ (ตามเอกสารการติดตั้ง) → data จึงอยู่ข้าง exe
    โดยอัตโนมัติ ไม่ว่า exe จะอยู่ที่ไหน — รันหลาย config = ข้อมูลแยกชุด ไม่ทับกัน.
    """
    if not config_path:
        return DEFAULT_DATA_DIR
    return os.path.dirname(os.path.abspath(config_path))


def state_path_for(config_path=None):
    return os.path.join(data_dir_for(config_path), "state.json")


def queue_path_for(config_path=None):
    return os.path.join(data_dir_for(config_path), "notify_queue.json")


def heartbeat_state_path_for(config_path=None):
    """ไฟล์จดเวลาส่ง heartbeat ล่าสุด (ข้าม process) — กันส่งเบิ้ลเมื่อรัน 2 instance"""
    return os.path.join(data_dir_for(config_path), "heartbeat_state.json")


def log_dir_for(config_path=None):
    return os.path.join(data_dir_for(config_path), "logs")

_hostname_cache = ""


def _hostname():
    """ชื่อเครื่อง (แคช) — ใช้ระบุที่มาใน User-Agent/log"""
    global _hostname_cache
    if not _hostname_cache:
        try:
            _hostname_cache = socket.gethostname() or "?"
        except Exception:
            _hostname_cache = "?"
    return _hostname_cache


def user_agent():
    """User-Agent พร้อมชื่อเครื่อง — ฝั่งบริการ (Healthchecks/Cloudflare/provider) ดู log แล้วรู้ว่าเครื่องไหนส่ง"""
    return f"cloudflare-ddns-updater/{__version__} ({_hostname()})"


def password_hash(pw, config_path=None):
    """hash รหัสผ่านหน้าเว็บ (sha256 + salt จาก path config) — กันเก็บ password ตรงใน config/cookie"""
    import hashlib

    salt = ("cfddns|" + os.path.abspath(config_path or "")).encode("utf-8")
    return hashlib.sha256(salt + str(pw).encode("utf-8")).hexdigest()


def rotate_backup(path, keep=3):
    """หมุน backup ของไฟล์ (path.bak, path.2.bak, ..., path.<keep>.bak) — เรียกก่อนเขียนทับไฟล์หลัก.

    คืน True ถ้าสำเร็จ/ไม่มีไฟล์หลัก, False ถ้าพลาด (ยังเขียนทับไฟล์หลักต่อได้)
    """
    if not os.path.isfile(path):
        return True
    try:
        for i in range(keep, 2, -1):
            src = f"{path}.{i - 1}.bak"
            if os.path.isfile(src):
                os.replace(src, f"{path}.{i}.bak")
        src = f"{path}.bak"
        if os.path.isfile(src):
            os.replace(src, f"{path}.2.bak")
        os.replace(path, f"{path}.bak")
        return True
    except OSError:
        return False


def atomic_write_text(path, text):
    """เขียนไฟล์ข้อความแบบ atomic (temp + os.replace) — คืน True/False.

    ใช้กับงานที่ต้องเขียนได้เสมอ (เช่น กู้รหัสผ่าน) — ไม่ผ่าน validate เหมือน save_text
    """
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp, path)
        return True
    except OSError:
        return False


def password_is_hash(value):
    """ค่าเป็น hash 64 hex หรือไม่ (config เก่าที่ยังเก็บ plaintext = ไม่ใช่)"""
    value = str(value or "")
    return len(value) == 64 and all(c in "0123456789abcdef" for c in value)


RECORD_SECTION_RE = re.compile(r"^record:(.+)$", re.IGNORECASE)


def fqdn_name(name, zone):
    """รวมชื่อ record กับ zone ให้เป็นชื่อเต็ม (home + example.com -> home.example.com).

    - "@" -> zone
    - ชื่อที่ลงท้ายด้วย .zone อยู่แล้ว -> ใช้ตรง
    - ชื่อสั้น -> เติม .zone ให้
    """
    name = (name or "").strip().rstrip(".")
    zone = (zone or "").strip().rstrip(".")
    if not name:
        return ""
    if not zone:
        return name
    if name == "@":
        return zone
    if name == zone or name.endswith("." + zone):
        return name
    return f"{name}.{zone}"


class ConfigError(Exception):
    """config.ini มีปัญหา"""


class RecordConfig:
    def __init__(self, name, zone="", proxied=False, ttl=60, ipv4=True, ipv6=True):
        self.name = name.strip().rstrip(".")
        self.zone = zone.strip().rstrip(".")
        self.proxied = bool(proxied)
        self.ttl = int(ttl)
        self.ipv4 = bool(ipv4)
        self.ipv6 = bool(ipv6)

    @property
    def key(self):
        return self.name.lower()


class Config:
    """ห่อ configparser พร้อมค่าที่ดึงออกมาใช้งานแล้ว"""

    def __init__(self, path=DEFAULT_CONFIG_PATH):
        self.path = path
        self.parser = configparser.ConfigParser(interpolation=None)
        self.api_token = ""
        self.interval_seconds = DEFAULT_INTERVAL
        self.use_ipv4 = True
        self.use_ipv6 = True
        self.ip_consensus = False
        self.reject_cloudflare_ips = True
        self.healthchecks_url = ""
        self.uptimekuma_url = ""
        self.heartbeat_min_interval = 60
        self.webui_port = 8123
        self.webui_host = "127.0.0.1"
        self.webui_password = ""
        self.log_dir = DEFAULT_LOG_DIR
        # log ละเอียด (pid ทุกบรรทัด + บันทึก heartbeat ส่ง/ข้าม) — ใช้หาสาเหตุ; ปิด default
        self.detail_log = False
        self.telegram_bot_token = ""
        self.telegram_chat_id = ""
        self.notify_start = True
        self.notify_stop = True
        self.notify_ip_change = True
        self.notify_error = True
        self.notify_created = True
        self.notify_round = False
        self.daily_report = True
        self.daily_report_time = "08:00"
        # อนุญาตกู้รหัสผ่านหน้าเว็บผ่าน Telegram (opt-in — ปิด default)
        self.telegram_allow_reset = False
        # ชื่อเครื่องสำหรับรับคำสั่ง Telegram (เว้นว่าง = ชื่อเครื่องของระบบ — ใช้ bot กลางหลายเครื่อง: /status @ชื่อ)
        self.telegram_command_name = ""
        # ภาษาสำหรับข้อความ Telegram (notify + คำสั่ง) — th | en (default th; log ไฟล์คงไทยเสมอ)
        self.language = "th"
        # Cloudflare Tunnel (cloudflared)
        self.tunnel_enabled = False
        self.tunnel_token = ""
        self.cloudflared_path = ""
        self.tunnel_hosts = []
        self.records = []
        self.last_error = ""
        self.reload()

    def reload(self):
        """อ่าน config จากไฟล์ใหม่ (เรียกซ้ำได้ทุก loop เพื่อรับค่าใหม่ทันที)"""
        self.parser = configparser.ConfigParser(interpolation=None)
        self.last_error = ""
        if not os.path.isfile(self.path):
            self.last_error = f"ไม่พบไฟล์ config: {self.path}"
            return self
        try:
            # utf-8-sig รองรับทั้งไฟล์ที่มี/ไม่มี BOM (ไฟล์จาก PowerShell/Notepad เก่ามี BOM)
            self.parser.read(self.path, encoding="utf-8-sig")
        except Exception as exc:
            self.last_error = f"อ่าน config ไม่ได้: {exc}"
            return self

        section = self._section("cloudflare")
        self.api_token = section.get("api_token", "").strip()
        self.interval_seconds = self._as_float(
            section, "interval_seconds", DEFAULT_INTERVAL
        )
        self.use_ipv4 = self._as_bool(section, "use_ipv4", True)
        self.use_ipv6 = self._as_bool(section, "use_ipv6", True)
        self.ip_consensus = self._as_bool(section, "ip_consensus", False)
        self.reject_cloudflare_ips = self._as_bool(section, "reject_cloudflare_ips", True)
        self.healthchecks_url = section.get("healthchecks_url", "").strip()
        self.uptimekuma_url = section.get("uptimekuma_url", "").strip()
        self.heartbeat_min_interval = self._as_float(section, "heartbeat_min_interval", 60)
        self.webui_port = max(1, min(65535, int(self._as_float(section, "webui_port", 8123))))
        self.webui_host = section.get("webui_host", "127.0.0.1").strip() or "127.0.0.1"
        self.webui_password = section.get("webui_password", "").strip()
        self.log_dir = section.get("log_dir", "").strip() or log_dir_for(self.path)
        self.detail_log = self._as_bool(section, "detail_log", False)

        # แจ้งเตือน Telegram
        self.telegram_bot_token = section.get("telegram_bot_token", "").strip()
        self.telegram_chat_id = section.get("telegram_chat_id", "").strip()
        self.notify_start = self._as_bool(section, "notify_start", True)
        self.notify_stop = self._as_bool(section, "notify_stop", True)
        self.notify_ip_change = self._as_bool(section, "notify_ip_change", True)
        self.notify_error = self._as_bool(section, "notify_error", True)
        self.notify_created = self._as_bool(section, "notify_created", True)
        self.notify_round = self._as_bool(section, "notify_round", False)
        self.daily_report = self._as_bool(section, "daily_report", True)
        self.daily_report_time = section.get("daily_report_time", "08:00").strip() or "08:00"
        self.telegram_allow_reset = self._as_bool(section, "telegram_allow_reset", False)
        self.telegram_command_name = section.get("telegram_command_name", "").strip()
        self.language = (section.get("language", "th").strip().lower() or "th")
        if self.language not in ("th", "en"):
            self.language = "th"
        self.tunnel_enabled = self._as_bool(section, "tunnel_enabled", False)
        self.tunnel_token = section.get("tunnel_token", "").strip()
        self.cloudflared_path = section.get("cloudflared_path", "").strip()
        self.tunnel_hosts = self._parse_tunnel_hosts(section.get("tunnel_hosts", ""))

        self.records = []
        for name in self.parser.sections():
            match = RECORD_SECTION_RE.match(name)
            if not match:
                continue
            rec_sec = self.parser[name]
            self.records.append(
                RecordConfig(
                    name=match.group(1),
                    zone=rec_sec.get("zone", ""),
                    proxied=self._as_bool(rec_sec, "proxied", False),
                    ttl=int(self._as_float(rec_sec, "ttl", 60)),
                    ipv4=self._as_bool(rec_sec, "ipv4", True),
                    ipv6=self._as_bool(rec_sec, "ipv6", True),
                )
            )
        return self

    def _section(self, name):
        if self.parser.has_section(name):
            return self.parser[name]
        return {}

    def _as_bool(self, section, key, default):
        if key not in section:
            return default
        return section.get(key, "").strip().lower() in ("1", "yes", "true", "on")

    def _as_float(self, section, key, default):
        try:
            return float(section.get(key, str(default)))
        except (ValueError, TypeError):
            return default

    def _parse_tunnel_hosts(self, raw):
        """parse tunnel_hosts (JSON list) -> list[dict]; คืน [] ถ้าไม่ถูกต้อง"""
        import json as _json

        raw = (raw or "").strip()
        if not raw:
            return []
        try:
            items = _json.loads(raw)
        except ValueError:
            return []
        if not isinstance(items, list):
            return []
        out = []
        for item in items:
            if isinstance(item, dict) and item.get("hostname"):
                out.append(
                    {
                        "hostname": str(item["hostname"]).strip().rstrip("."),
                        "path": str(item.get("path", "")).strip() or "",
                        "protocol": str(item.get("protocol", "http")).strip() or "http",
                        "service": str(item.get("service", "")).strip(),
                    }
                )
        return out

    def validate(self):
        """คืน list ของข้อผิดพลาด ถ้าว่าง = config ใช้ได้"""
        errors = []
        if not self.api_token:
            errors.append("ไม่พบ api_token ใน [cloudflare] (รัน setup เพื่อตั้งค่า)")
        if not self.records:
            errors.append("ไม่พบ record ใด ๆ (ต้องมี section [record:ชื่อโดเมน] อย่างน้อย 1 อัน)")
        if not (self.use_ipv4 or self.use_ipv6):
            errors.append("ปิดทั้ง use_ipv4 และ use_ipv6 แล้ว ไม่มีอะไรต้องอัปเดต")
        if self.interval_seconds < MIN_INTERVAL:
            errors.append(f"interval_seconds น้อยเกินไป (ขั้นต่ำ {MIN_INTERVAL} วินาที)")
        if self.daily_report and self.daily_report_time:
            import re as _re

            if not _re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", self.daily_report_time):
                errors.append(f"daily_report_time ต้องเป็น HH:MM (0-23:0-59) เช่น 08:00 (ตอนนี้: {self.daily_report_time})")
        if self.telegram_command_name and re.search(r"\s", self.telegram_command_name):
            errors.append("telegram_command_name ต้องไม่มีช่องว่าง (ใช้ในคำสั่ง /cmd @ชื่อ)")
        if not (1 <= self.webui_port <= 65535):
            errors.append(f"webui_port ต้องอยู่ระหว่าง 1-65535 (ตอนนี้: {self.webui_port})")
        if not re.fullmatch(r"[A-Za-z0-9.\-_\[\]:]+", self.webui_host):
            errors.append(
                f"webui_host ไม่ถูกต้อง (ต้องเป็น IP/hostname เช่น 127.0.0.1 หรือ 0.0.0.0 — ตอนนี้: {self.webui_host})"
            )
        for key, value in (
            ("healthchecks_url", self.healthchecks_url),
            ("uptimekuma_url", self.uptimekuma_url),
        ):
            if value and not value.startswith(("http://", "https://")):
                errors.append(f"{key} ต้องเป็น URL เต็ม (http/https): {value}")
        if not (5 <= self.heartbeat_min_interval <= 3600):
            errors.append(f"heartbeat_min_interval ต้องอยู่ระหว่าง 5-3600 วินาที (ตอนนี้: {self.heartbeat_min_interval})")
        if self.tunnel_hosts:
            import json as _json

            seen_hosts = set()
            for h in self.tunnel_hosts:
                key = (h["hostname"], h.get("path", ""))
                if key in seen_hosts:
                    errors.append(f"tunnel_hosts ซ้ำ: {h['hostname']}{h.get('path', '')}")
                seen_hosts.add(key)
                if h.get("protocol") not in ("http", "https", "tcp", "udp"):
                    errors.append(f"tunnel_hosts protocol ไม่รู้จัก: {h.get('protocol')} (ต้องเป็น http/https/tcp/udp)")
                if h.get("path") and not h["path"].startswith("/"):
                    errors.append(f"tunnel_hosts path ต้องเริ่มด้วย /: {h['path']}")
        seen = set()
        for rec in self.records:
            if not rec.name:
                errors.append("มี record ที่ชื่อว่างเปล่า")
                continue
            fqdn = fqdn_name(rec.name, rec.zone)
            if fqdn in seen:
                errors.append(f"record ซ้ำ: {rec.name} (= {fqdn}) กับ record อื่นในรายการ")
            seen.add(fqdn)
            if rec.ttl < 60:
                errors.append(f"ttl ของ {rec.name} น้อยกว่า 60 (ขั้นต่ำที่ Cloudflare รองรับ)")
        return errors

    def raw_text(self):
        """คืนเนื้อหา config ทั้งไฟล์ (สำหรับ Web UI)"""
        try:
            with open(self.path, "r", encoding="utf-8-sig") as handle:
                return handle.read()
        except OSError:
            return ""

    def save_text(self, text):
        """ตรวจสอบแล้วเขียน config ใหม่ทั้งไฟล์ (สำหรับ Web UI / wizard)

        คืน (ok, message) - ตรวจก่อนเขียนว่า parse ได้และ validate ผ่าน
        """
        parser = configparser.ConfigParser(interpolation=None)
        try:
            parser.read_string(text)
        except configparser.Error as exc:
            return False, f"config ไม่ถูกต้อง: {exc}"
        probe = Config.__new__(Config)
        probe.parser = parser
        probe.path = self.path
        probe._load_from_parser()
        errors = probe.validate()
        if errors:
            return False, "config ยังไม่สมบูรณ์: " + "; ".join(errors)
        # สำรองไฟล์เดิมก่อนเขียน (หมุนเก็บ 5 อัน: .bak, .bak1 ... .bak4)
        try:
            if os.path.isfile(self.path):
                for i in range(4, 0, -1):
                    src = f"{self.path}.bak{i}" if i > 1 else f"{self.path}.bak"
                    dst = f"{self.path}.bak{i + 1}" if i > 1 else f"{self.path}.bak1"
                    if os.path.isfile(src):
                        os.replace(src, dst)
                os.replace(self.path, self.path + ".bak")
        except OSError as exc:
            log.warning("สำรอง config ไม่ได้: %s", exc)

        # เขียนแบบ atomic (temp + rename) กันไฟล์เสียกลางคัน
        tmp_path = self.path + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as handle:
                handle.write(text)
            os.replace(tmp_path, self.path)
        except OSError as exc:
            return False, f"เขียนไฟล์ไม่ได้: {exc}"
        self.reload()
        return True, "บันทึก config สำเร็จ"

    def _load_from_parser(self):
        section = self._section("cloudflare")
        self.api_token = section.get("api_token", "").strip()
        self.interval_seconds = self._as_float(
            section, "interval_seconds", DEFAULT_INTERVAL
        )
        self.use_ipv4 = self._as_bool(section, "use_ipv4", True)
        self.use_ipv6 = self._as_bool(section, "use_ipv6", True)
        self.ip_consensus = self._as_bool(section, "ip_consensus", False)
        self.reject_cloudflare_ips = self._as_bool(section, "reject_cloudflare_ips", True)
        self.healthchecks_url = section.get("healthchecks_url", "").strip()
        self.uptimekuma_url = section.get("uptimekuma_url", "").strip()
        self.heartbeat_min_interval = self._as_float(section, "heartbeat_min_interval", 60)
        self.webui_port = max(1, min(65535, int(self._as_float(section, "webui_port", 8123))))
        self.webui_host = section.get("webui_host", "127.0.0.1").strip() or "127.0.0.1"
        self.webui_password = section.get("webui_password", "").strip()
        self.log_dir = section.get("log_dir", "").strip() or log_dir_for(self.path)
        self.detail_log = self._as_bool(section, "detail_log", False)

        self.telegram_bot_token = section.get("telegram_bot_token", "").strip()
        self.telegram_chat_id = section.get("telegram_chat_id", "").strip()
        self.notify_start = self._as_bool(section, "notify_start", True)
        self.notify_stop = self._as_bool(section, "notify_stop", True)
        self.notify_ip_change = self._as_bool(section, "notify_ip_change", True)
        self.notify_error = self._as_bool(section, "notify_error", True)
        self.notify_created = self._as_bool(section, "notify_created", True)
        self.notify_round = self._as_bool(section, "notify_round", False)
        self.daily_report = self._as_bool(section, "daily_report", True)
        self.daily_report_time = section.get("daily_report_time", "08:00").strip() or "08:00"
        self.telegram_allow_reset = self._as_bool(section, "telegram_allow_reset", False)
        self.telegram_command_name = section.get("telegram_command_name", "").strip()
        self.language = (section.get("language", "th").strip().lower() or "th")
        if self.language not in ("th", "en"):
            self.language = "th"
        self.tunnel_enabled = self._as_bool(section, "tunnel_enabled", False)
        self.tunnel_token = section.get("tunnel_token", "").strip()
        self.cloudflared_path = section.get("cloudflared_path", "").strip()
        self.tunnel_hosts = self._parse_tunnel_hosts(section.get("tunnel_hosts", ""))

        self.records = []
        for name in self.parser.sections():
            match = RECORD_SECTION_RE.match(name)
            if not match:
                continue
            rec_sec = self.parser[name]
            self.records.append(
                RecordConfig(
                    name=match.group(1),
                    zone=rec_sec.get("zone", ""),
                    proxied=self._as_bool(rec_sec, "proxied", False),
                    ttl=int(self._as_float(rec_sec, "ttl", 60)),
                    ipv4=self._as_bool(rec_sec, "ipv4", True),
                    ipv6=self._as_bool(rec_sec, "ipv6", True),
                )
            )
