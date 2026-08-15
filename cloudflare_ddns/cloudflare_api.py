"""ติดต่อ Cloudflare API v4 (ใช้ urllib มาตรฐาน ไม่ต้องติดตั้ง requests)."""

import json
import urllib.error
import urllib.parse
import urllib.request

API_BASE = "https://api.cloudflare.com/client/v4"
USER_AGENT = "cloudflare-ddns-updater/1.0"


class CloudflareError(Exception):
    """Cloudflare API คืน error หรือเชื่อมต่อไม่ได้"""


class CloudflareAPI:
    def __init__(self, token):
        self._headers = {
            "Authorization": "Bearer " + token.strip(),
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        }

    # ---- ขั้นพื้นฐาน ----

    def _request(self, method, path, body=None):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(
            API_BASE + path, data=data, headers=self._headers, method=method
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                raw = response.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", "replace")[:500]
            except Exception:
                pass
            raise CloudflareError(f"HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise CloudflareError(f"เชื่อมต่อ Cloudflare ไม่ได้: {exc.reason}") from exc

        try:
            payload = json.loads(raw)
        except ValueError as exc:
            raise CloudflareError(f"ตอบกลับมาไม่ใช่ JSON: {raw[:200]}") from exc

        if not payload.get("success"):
            messages = [m.get("message", "") for m in payload.get("errors", [])]
            code = payload.get("errors", [{}])[0].get("code", "")
            raise CloudflareError(f"API error (code {code}): {'; '.join(messages)}")
        return payload.get("result")

    # ---- token / zone ----

    def verify_token(self):
        """ตรวจว่า token ใช้งานได้"""
        return self._request("GET", "/user/token/verify")

    def list_zones(self):
        """คืนรายชื่อ zone ทั้งหมดที่ token นี้เข้าถึงได้"""
        zones, page = [], 1
        while True:
            result = self._request("GET", f"/zones?per_page=100&page={page}")
            if not result:
                break
            zones.extend(result)
            if len(result) < 100:
                break
            page += 1
        return zones

    def get_zone_id(self, zone):
        """หาที่อยู่ zone_id จากชื่อ zone"""
        quoted = urllib.parse.quote(zone)
        result = self._request("GET", f"/zones?name={quoted}")
        if not result:
            raise CloudflareError(f"ไม่พบ zone ที่ชื่อ '{zone}' ใน account นี้")
        return result[0]["id"]

    def guess_zone_id(self, record_name):
        """เดา zone จากชื่อ record: ค่อย ๆ ตัดส่วนหน้าออกจนเจอ zone ที่ตรง"""
        parts = record_name.rstrip(".").split(".")
        for start in range(len(parts) - 1):
            candidate = ".".join(parts[start:])
            try:
                return candidate, self.get_zone_id(candidate)
            except CloudflareError:
                continue
        raise CloudflareError(f"ไม่สามารถหา zone ของ record '{record_name}' ได้ ระบุ zone ใน config")

    # ---- dns records ----

    def get_record(self, zone_id, name, rtype):
        """คืน record dict หรือ None ถ้ายังไม่มี"""
        query = urllib.parse.urlencode({"name": name.rstrip("."), "type": rtype})
        result = self._request("GET", f"/zones/{zone_id}/dns_records?{query}")
        return result[0] if result else None

    def update_record(self, zone_id, record_id, content, ttl, proxied):
        """แก้ IP ของ record ที่มีอยู่"""
        return self._request(
            "PATCH",
            f"/zones/{zone_id}/dns_records/{record_id}",
            {"content": content, "ttl": int(ttl), "proxied": bool(proxied)},
        )

    def create_record(self, zone_id, name, rtype, content, ttl, proxied):
        """สร้าง record ใหม่ (ใช้เมื่อ record ยังไม่มีใน Cloudflare)"""
        return self._request(
            "POST",
            f"/zones/{zone_id}/dns_records",
            {
                "type": rtype,
                "name": name.rstrip("."),
                "content": content,
                "ttl": int(ttl),
                "proxied": bool(proxied),
            },
        )
