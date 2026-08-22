"""ตรวจหา IP สาธารณะของเครื่อง (IPv4 / IPv6) ผ่านหลาย provider สำรองกัน."""

import ipaddress
import random
import re
import shutil
import socket
import struct
import subprocess
import time
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from . import config as config_mod
from . import i18n

PROVIDERS: Dict[int, List[str]] = {
    4: [
        "https://api.ipify.org",
        "https://ifconfig.me/ip",
        "https://ipv4.icanhazip.com",
        "https://api.cloudflare.com/cdn-cgi/trace",
    ],
    6: [
        "https://api6.ipify.org",
        "https://ifconfig.co/ip",
        "https://ipv6.icanhazip.com",
    ],
}

# ช่วง IP ที่บอกว่าเราไม่ได้มี IP สาธารณะเป็นของตัวเอง
CGNAT_NETWORKS = [ipaddress.ip_network("100.64.0.0/10")]
PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
]


def _http_get(url: str, timeout: int) -> str:
    """GET URL แล้วคืนข้อความ (ตัดช่องว่างหัวท้าย) — โยน exception เมื่อเชื่อมต่อไม่ได้.

    Args:
        url: URL ที่จะขอ
        timeout: เวลารอสูงสุด (วินาที)

    Returns:
        str: ข้อความจาก server

    Raises:
        Exception: network error / HTTP error (ปล่อยให้ caller จับ)
    """
    request = urllib.request.Request(url, headers={"User-Agent": config_mod.user_agent()})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", "replace").strip()


def _extract_text(text: str, url: str) -> str:
    """แยก IP ออกจากข้อความของ provider (กรณีพิเศษ cdn-cgi/trace).

    Args:
        text: ข้อความดิบจาก provider
        url: URL ของ provider (ใช้ดูว่าเป็น cdn-cgi/trace หรือไม่)

    Returns:
        str: IP ที่แยกได้ หรือข้อความเดิมถ้าไม่ใช่รูปแบบพิเศษ
    """
    if "cdn-cgi/trace" in url:
        for line in text.splitlines():
            if line.startswith("ip="):
                return line[3:]
        return ""
    return text


def get_public_ip(version: int = 4, timeout: int = 8, consensus: Optional[int] = None) -> Optional[str]:
    """คืน IP สาธารณะ (str) ตาม version ที่ขอ หรือ None ถ้าหาไม่ได้จากทุก provider.

    Args:
        version: ชนิด IP — 4 (IPv4) หรือ 6 (IPv6)
        timeout: เวลารอสูงสุดต่อ provider (วินาที)
        consensus: ต้องมี provider ตั้งแต่ N รายเห็น IP ตัวเดียวกันถึงจะคืน
            (กัน provider ตัวใดตัวหนึ่งตอบผิด) — ฉันทามติไม่พอ = คืน None เหมือนหาไม่เจอ

    Returns:
        str | None: IP สาธารณะ หรือ None ถ้าหาไม่ได้/ฉันทามติไม่พอ

    Raises:
        ValueError: version ไม่ใช่ 4 หรือ 6
    """
    if version not in (4, 6):
        raise ValueError("version ต้องเป็น 4 หรือ 6")
    need = max(int(consensus or 0), 0)
    votes: Dict[str, int] = {}
    first_ip = None
    for url in PROVIDERS[version]:
        try:
            text = _http_get(url, timeout)
            ip = ipaddress.ip_address(_extract_text(text, url))
            if ip.version != version:
                continue
        except Exception:
            continue
        key = str(ip)
        if first_ip is None:
            first_ip = key
        if need > 1:
            votes[key] = votes.get(key, 0) + 1
            if votes[key] >= need:
                return key
    if need > 1:
        return None  # ฉันทามติไม่พอ — ข้ามรอบนี้ (กัน IP ผิดถูกเขียนลง record)
    return first_ip


# ---------- กัน IP ของ Cloudflare (anycast) ----------

CLOUDFLARE_IP_URLS: Dict[int, str] = {
    4: "https://www.cloudflare.com/ips-v4",
    6: "https://www.cloudflare.com/ips-v6",
}
# แคชช่วง IP 24 ชม. — ถ้าโหลดไม่ได้ถือว่า "น่าสงสัย" (กันเขียน IP ผิด)
CLOUDFLARE_IP_CACHE_TTL = 24 * 3600
_cloudflare_ranges: Dict[int, Tuple[float, List[Any]]] = {}  # version -> (timestamp, [ip_network])


def get_cloudflare_ranges(version: int, timeout: int = 8) -> Optional[List[Any]]:
    """คืน list ของ ip_network ที่เป็นของ Cloudflare (แคช 24 ชม.) หรือ None ถ้าโหลดไม่ได้.

    Args:
        version: ชนิด IP — 4 (IPv4) หรือ 6 (IPv6)
        timeout: เวลารอสูงสุด (วินาที)

    Returns:
        list[ip_network] | None: ช่วง IP ของ Cloudflare หรือ None ถ้าโหลดไม่ได้
    """
    cached = _cloudflare_ranges.get(version)
    now = time.time()
    if cached and now - cached[0] < CLOUDFLARE_IP_CACHE_TTL:
        return cached[1]
    try:
        text = _http_get(CLOUDFLARE_IP_URLS[version], timeout)
        nets = [
            ipaddress.ip_network(line.strip())
            for line in text.splitlines()
            if line.strip()
        ]
        _cloudflare_ranges[version] = (now, nets)
        return nets
    except Exception:
        return None


def is_cloudflare_ip(ip_str: str, timeout: int = 8) -> bool:
    """IP เป็นของ Cloudflare (anycast/CDN) หรือไม่.

    ถ้าโหลดช่วง IP ไม่ได้ -> คืน True (ถือว่าน่าสงสัย กันเขียน IP ผิดลง record)
    ปิดได้ด้วย reject_cloudflare_ips = false ใน config

    Args:
        ip_str: IP ที่จะตรวจ (IPv4 หรือ IPv6)
        timeout: เวลารอสูงสุด (วินาที)

    Returns:
        bool: True ถ้า IP อยู่ในช่วงของ Cloudflare (หรือโหลดช่วงไม่ได้)
    """
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    nets = get_cloudflare_ranges(ip.version, timeout=timeout)
    if nets is None:
        return True
    return any(ip in net for net in nets)


# ---------- ตรวจ NAT / CGNAT ----------


def is_private_ip(ip_str: str) -> bool:
    """IP อยู่ในช่วง private / CGNAT / loopback หรือไม่.

    Args:
        ip_str: IP ที่จะตรวจ

    Returns:
        bool: True ถ้าเป็น IPv4 ในช่วง private/CGNAT (IPv6 หรือค่าผิด = False)
    """
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    if not ip.version == 4:
        return False
    for net in CGNAT_NETWORKS + PRIVATE_NETWORKS:
        if ip in net:
            return True
    return False


def is_cgnat_ip(ip_str: str) -> bool:
    """IP อยู่ในช่วง CGNAT (100.64.0.0/10) ของ ISP โดยเฉพาะ.

    Args:
        ip_str: IP ที่จะตรวจ

    Returns:
        bool: True ถ้าเป็น IPv4 ในช่วง CGNAT
    """
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return ip.version == 4 and ip in CGNAT_NETWORKS[0]


def _stun_binding(stun_host: str = "stun.l.google.com", port: int = 19302, timeout: int = 5) -> Optional[Tuple[str, int]]:
    """ถาม STUN server ว่าเราเห็น mapped address (IP + port) จากนอก NAT เป็นเท่าไหร่.

    Args:
        stun_host: hostname ของ STUN server
        port: port ของ STUN server (default 19302)
        timeout: เวลารอสูงสุด (วินาที)

    Returns:
        tuple[str, int] | None: (mapped IP, mapped port) หรือ None ถ้าถามไม่ได้
    """
    # STUN Binding Request: type=0x0001, len=0, magic cookie, txid 12 bytes
    txid = random.getrandbits(96).to_bytes(12, "big")
    request = struct.pack("!HHI12s", 0x0001, 0, 0x2112A442, txid)
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        try:
            sock.sendto(request, (stun_host, port))
            data, _ = sock.recvfrom(2048)
        finally:
            sock.close()
        if len(data) < 20:
            return None
        msg_type = struct.unpack("!H", data[:2])[0]
        if msg_type != 0x0101:  # Binding Response
            return None
        # หา attribute XOR-MAPPED-ADDRESS (0x0020)
        offset = 20
        while offset + 4 <= len(data):
            attr_type, attr_len = struct.unpack("!HH", data[offset : offset + 4])
            value = data[offset + 4 : offset + 4 + attr_len]
            if attr_type == 0x0020 and len(value) >= 8:
                family = value[1]
                if family == 0x01:  # IPv4
                    xport = struct.unpack("!H", value[2:4])[0] ^ 0x2112
                    xip = struct.unpack("!I", value[4:8])[0] ^ 0x2112A442
                    return socket.inet_ntoa(struct.pack("!I", xip)), xport
                if family == 0x02 and len(value) >= 20:  # IPv6
                    xport = struct.unpack("!H", value[2:4])[0] ^ 0x2112
                    # RFC 8489: XOR-MAPPED-ADDRESS IPv6 = magic cookie (4B) + transaction id (12B)
                    mask = struct.pack("!I", 0x2112A442) + txid
                    xip_bytes = bytes(a ^ b for a, b in zip(value[4:20], mask))
                    return socket.inet_ntop(socket.AF_INET6, xip_bytes), xport
            offset += 4 + attr_len
    except Exception:
        return None
    return None


def _tracert_hops(target: str = "8.8.8.8", max_hops: int = 5, wait_ms: int = 250, timeout: int = 20) -> Optional[List[str]]:
    """เรียก tracert.exe (Windows) แล้วคืน list IP ของแต่ละฮอป ตามลำดับ (เรียงจากใกล้สุด).

    ใช้ UDP TTL เองบน Windows ไม่ได้ (ICMP ถูก drop เข้า UDP socket -> err 10052)
    จึงพึ่ง tracert.exe — ทำงานได้โดยไม่ต้อง admin.

    Args:
        target: IP ปลายทางที่ tracert ไปหา
        max_hops: จำนวนฮอปสูงสุด (-h)
        wait_ms: เวลารอต่อฮอปเป็น ms (-w)
        timeout: เวลารอสูงสุดของ process ทั้งหมด (วินาที)

    Returns:
        list[str] | None: IP ของแต่ละฮอป (ไม่รวม target) หรือ None ถ้าเรียกไม่ได้
    """
    exe = shutil.which("tracert")
    if not exe:
        return None
    try:
        proc = subprocess.run(
            [exe, "-d", "-h", str(max_hops), "-w", str(wait_ms), target],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    pattern = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
    hops: List[str] = []
    for line in proc.stdout.splitlines():
        m = pattern.search(line)
        if not m:
            continue
        ip = m.group(0)
        if ip == target:
            continue
        hops.append(ip)
    return hops or None


def _trace_verdict(hops: Optional[List[str]]) -> Optional[str]:
    """ตีความผล tracert: จุดแรกที่ข้าม router บ้าน (ฮอป 2 หรือฮอปเดียวสุดท้าย) เป็น IP แบบไหน.

    Args:
        hops: list IP ต่อฮอปจาก _tracert_hops (อาจเป็น None)

    Returns:
        str | None: "cg-nat" | "double-nat" | "public-route" | None (ตัดสินไม่ได้)

        - เห็น 100.64/10 ที่ฮอปใด -> CGNAT ของ ISP (หลัง WAN ตรง ๆ)
        - ฮอป 2 เป็น private -> มี NAT ซ้อน (double NAT — inbound ต้อง forward ทีละชั้น)
        - ฮอป 2 เป็น public -> ไม่มีชั้น private คั่น (ต่อตรงหรือ NAT 1:1)
    """
    if not hops:
        return None
    if any(is_cgnat_ip(ip) for ip in hops):
        return "cg-nat"
    probe = hops[1] if len(hops) > 1 else hops[0]
    if is_private_ip(probe):
        if len(hops) == 1:
            return None
        return "double-nat"
    return "public-route"


def _stun_stability(rounds: int = 4, timeout: int = 5, delay: float = 0.3) -> Optional[Dict[str, Any]]:
    """ถาม STUN ซ้ำหลายรอบ ดูว่า mapped IP/port เปลี่ยนไหม (สัญญาณ NAT แบบ dynamic).

    Args:
        rounds: จำนวนรอบที่ถามซ้ำ
        timeout: เวลารอสูงสุดต่อรอบ (วินาที)
        delay: เวลารอระหว่างรอบ (วินาที)

    Returns:
        dict | None: {"ips": list, "ports": list, "count": int} หรือ None ถ้าถามไม่ได้เลย
    """
    ips, ports = set(), set()
    n = 0
    for _ in range(rounds):
        r = _stun_binding(timeout=timeout)
        if r:
            n += 1
            ips.add(r[0])
            ports.add(r[1])
        time.sleep(delay)
    if not n:
        return None
    return {"ips": sorted(ips), "ports": sorted(ports), "count": n}


def nat_report(public_ip: Optional[str] = None, timeout: int = 5, trace: bool = True, stun_rounds: int = 4, lang: str = "th") -> Dict[str, Any]:
    """ตรวจสถานะ NAT ของเครื่อง 3 ชั้น: provider IP + tracert (ฮอปแรกหลัง WAN) + STUN ซ้ำ.

    Args:
        public_ip: IP สาธารณะที่รู้อยู่แล้ว (None = ให้ตรวจเอง)
        timeout: เวลารอสูงสุดต่อการตรวจ (วินาที)
        trace: เปิดใช้ tracert วิเคราะห์ฮอปหรือไม่
        stun_rounds: จำนวนรอบ STUN ที่จะถามซ้ำ (0 = ข้ามส่วนนี้)
        lang: รหัสภาษา (เลือกข้อความอธิบาย)

    Returns:
        dict: ผลการตรวจ — ประกอบด้วย:
            - public_ip: IP ที่ตรวจได้จาก provider ภายนอก
            - stun_ip: IP ที่ STUN server เห็น (mapped)
            - stun_port: mapped port
            - tracert: list IP ต่อฮอป (Windows tracert) หรือ [] ถ้าใช้ไม่ได้
            - stun_rounds: dict จาก _stun_stability หรือ None
            - nat_type: "public" | "cg-nat" | "private-ip" | "double-nat" | "mismatch" | "unknown"
            - message: คำอธิบายตามภาษา (lang)
    """
    if not public_ip:
        public_ip = get_public_ip(4, timeout=timeout)
    result: Dict[str, Any] = {
        "public_ip": public_ip or "",
        "stun_ip": "",
        "stun_port": 0,
        "tracert": [],
        "stun_rounds": None,
        "nat_type": "unknown",
        "message": i18n.t(lang, "nat.unknown"),
    }
    if not public_ip:
        return result

    stun = _stun_binding(timeout=timeout)
    if stun:
        result["stun_ip"], result["stun_port"] = stun

    trace_v = None
    hops: Optional[List[str]] = []
    if trace:
        hops = _tracert_hops()
        result["tracert"] = hops or []
        trace_v = _trace_verdict(hops)
    stuns = _stun_stability(rounds=stun_rounds, timeout=timeout) if stun_rounds else None
    result["stun_rounds"] = stuns
    port_flips = bool(stuns and len(stuns["ports"]) > 1)

    if is_cgnat_ip(public_ip):
        result["nat_type"] = "cg-nat"
        result["message"] = i18n.t(lang, "nat.cgnat_ip")
    elif is_private_ip(public_ip):
        result["nat_type"] = "private-ip"
        result["message"] = i18n.t(lang, "nat.private_ip")
    elif trace_v == "cg-nat":
        result["nat_type"] = "cg-nat"
        result["message"] = i18n.t(lang, "nat.cgnat_trace")
    elif trace_v == "double-nat":
        # นับชั้น NAT ส่วนตัวในบ้าน (private IP ต่อเนื่องตั้งแต่ฮอปแรก — ไม่นับ core ISP หลัง public)
        layers = 1
        for ip in (hops or [])[1:]:
            if is_private_ip(ip):
                layers += 1
            else:
                break
        result["nat_type"] = "double-nat"
        result["nat_layers"] = layers
        result["message"] = i18n.t(lang, "nat.double_nat", layers=layers)
    elif stun and result["stun_ip"] and result["stun_ip"] != public_ip:
        result["nat_type"] = "mismatch"
        result["message"] = i18n.t(lang, "nat.mismatch", public=public_ip, stun=result["stun_ip"])
        if port_flips:
            result["message"] += i18n.t(lang, "nat.mismatch_dyn")
    elif stun and result["stun_ip"]:
        result["nat_type"] = "public"
        result["message"] = i18n.t(lang, "nat.public")
        if port_flips:
            result["message"] += i18n.t(lang, "nat.public_symmetric")
    else:
        result["nat_type"] = "unknown"
        result["message"] = i18n.t(lang, "nat.unknown_stun")
    return result
