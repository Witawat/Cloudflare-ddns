"""ตรวจหา IP สาธารณะของเครื่อง (IPv4 / IPv6) ผ่านหลาย provider สำรองกัน."""

import ipaddress
import urllib.request

USER_AGENT = "cloudflare-ddns-updater/1.0"

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


def _http_get(url, timeout):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
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
