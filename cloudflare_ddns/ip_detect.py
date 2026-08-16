"""ตรวจหา IP สาธารณะของเครื่อง (IPv4 / IPv6) ผ่านหลาย provider สำรองกัน."""

import ipaddress
import random
import socket
import struct
import time
import urllib.request

from . import config as config_mod

PROVIDERS = {
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


def _http_get(url, timeout):
    request = urllib.request.Request(url, headers={"User-Agent": config_mod.user_agent()})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", "replace").strip()


def _extract_text(text, url):
    if "cdn-cgi/trace" in url:
        for line in text.splitlines():
            if line.startswith("ip="):
                return line[3:]
        return ""
    return text


def get_public_ip(version=4, timeout=8):
    """คืน IP สาธารณะ (str) ตาม version ที่ขอ หรือ None ถ้าหาไม่ได้จากทุก provider."""
    if version not in (4, 6):
        raise ValueError("version ต้องเป็น 4 หรือ 6")
    for url in PROVIDERS[version]:
        try:
            text = _http_get(url, timeout)
            ip = ipaddress.ip_address(_extract_text(text, url))
            if ip.version == version:
                return str(ip)
        except Exception:
            continue
    return None


# ---------- กัน IP ของ Cloudflare (anycast) ----------

CLOUDFLARE_IP_URLS = {
    4: "https://www.cloudflare.com/ips-v4",
    6: "https://www.cloudflare.com/ips-v6",
}
# แคชช่วง IP 24 ชม. — ถ้าโหลดไม่ได้ถือว่า "น่าสงสัย" (กันเขียน IP ผิด)
CLOUDFLARE_IP_CACHE_TTL = 24 * 3600
_cloudflare_ranges = {}  # version -> (timestamp, [ip_network])


def get_cloudflare_ranges(version, timeout=8):
    """คืน list ของ ip_network ที่เป็นของ Cloudflare (แคช 24 ชม.) หรือ None ถ้าโหลดไม่ได้."""
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


def is_cloudflare_ip(ip_str, timeout=8):
    """IP เป็นของ Cloudflare (anycast/CDN) หรือไม่.

    ถ้าโหลดช่วง IP ไม่ได้ -> คืน True (ถือว่าน่าสงสัย กันเขียน IP ผิดลง record)
    ปิดได้ด้วย reject_cloudflare_ips = false ใน config
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


def is_private_ip(ip_str):
    """IP อยู่ในช่วง private / CGNAT / loopback หรือไม่"""
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


def is_cgnat_ip(ip_str):
    """IP อยู่ในช่วง CGNAT (100.64.0.0/10) ของ ISP โดยเฉพาะ"""
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return ip.version == 4 and ip in CGNAT_NETWORKS[0]


def _stun_binding(stun_host="stun.l.google.com", port=19302, timeout=5):
    """ถาม STUN server ว่าเราเห็น mapped address (IP + port) จากนอก NAT เป็นเท่าไหร่.

    คืน (ip_str, port) หรือ None ถ้าถามไม่ได้
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


def nat_report(public_ip=None, timeout=5):
    """ตรวจสถานะ NAT ของเครื่อง.

    คืน dict:
        public_ip      - IP ที่ตรวจได้จาก provider ภายนอก
        stun_ip        - IP ที่ STUN server เห็น (mapped)
        stun_port      - mapped port
        nat_type       - 'public' | 'cg-nat' | 'private-ip' | 'mismatch' | 'unknown'
        message        - คำอธิบายภาษาไทย
    """
    if not public_ip:
        public_ip = get_public_ip(4, timeout=timeout)
    result = {
        "public_ip": public_ip or "",
        "stun_ip": "",
        "stun_port": 0,
        "nat_type": "unknown",
        "message": "ตรวจ NAT ไม่ได้",
    }
    if not public_ip:
        return result

    stun = _stun_binding(timeout=timeout)
    if stun:
        result["stun_ip"], result["stun_port"] = stun

    if is_cgnat_ip(public_ip):
        result["nat_type"] = "cg-nat"
        result["message"] = (
            "IP อยู่ในช่วง CGNAT (100.64.0.0/10) — ISP แจก IP ร่วมกันให้หลายบ้าน "
            "DDNS ไม่สามารถใช้งานได้ ควรใช้ Cloudflare Tunnel หรือ IPv6 แทน"
        )
    elif is_private_ip(public_ip):
        result["nat_type"] = "private-ip"
        result["message"] = (
            "IP ที่ตรวจได้เป็น IP ภายใน (private) — อาจต่อผ่าน VPN/proxy หรือผิดปกติ "
            "DDNS จะอัปเดต IP นี้ไป ซึ่งไม่ใช่ IP ที่คนนอกเข้าถึงได้"
        )
    elif stun and result["stun_ip"] and result["stun_ip"] != public_ip:
        result["nat_type"] = "mismatch"
        result["message"] = (
            f"IP ที่เห็นจาก provider ({public_ip}) ไม่ตรงกับที่ STUN เห็น ({result['stun_ip']}) "
            "— สัญญาณว่า IP อาจไม่เสถียร/ผ่านตัวกลางหลายชั้น ตรวจสอบเองเพิ่มเติม"
        )
    elif stun and result["stun_ip"]:
        result["nat_type"] = "public"
        result["message"] = (
            "IP สาธารณะตรงปกติ (NAT แบบ 1:1 หรือไม่มี NAT) — DDNS ใช้งานได้ตามปกติ "
            "(ถ้ามีเราเตอร์ที่บ้าน อย่าลืมตั้ง port forward สำหรับบริการภายใน)"
        )
    else:
        result["nat_type"] = "unknown"
        result["message"] = "ตรวจ STUN ไม่ได้ — IP เป็น public แต่ไม่สามารถยืนยัน NAT ได้"
    return result
