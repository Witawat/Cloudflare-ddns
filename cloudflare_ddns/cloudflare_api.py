"""ติดต่อ Cloudflare API v4 (ใช้ urllib มาตรฐาน ไม่ต้องติดตั้ง requests)."""

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from . import config as config_mod

log = logging.getLogger("cloudflare-ddns")

API_BASE = "https://api.cloudflare.com/client/v4"

# สถิติสะสมการเรียก API (นับในหน่วยความจำ — เริ่มใหม่เมื่อโปรแกรม/service เริ่ม)
_stats: Dict[str, int] = {"calls": 0, "errors": 0, "rate_limited": 0}


def api_stats() -> Dict[str, int]:
    """สถิติสะสม: เรียกทั้งหมด / error / โดน rate limit (429).

    Returns:
        dict[str, int]: จำนวนการเรียกทั้งหมด / error / rate limit
    """
    return dict(_stats)


class CloudflareError(Exception):
    """Cloudflare API คืน error หรือเชื่อมต่อไม่ได้"""


class CloudflareRateLimit(CloudflareError):
    """โดน rate limit (HTTP 429) — ควรหยุดยิง API ชั่วคราว"""


class CloudflareAPI:
    """ตัวติดต่อ Cloudflare API v4 — CRUD zone / DNS records.

    ใช้งานผ่าน token (Bearer) ใช้ urllib ล้วน ไม่พึ่ง library ภายนอก.
    """

    def __init__(self, token: str) -> None:
        """สร้าง instance ด้วย API token.

        Args:
            token: Cloudflare API token (จะ strip ช่องว่างให้อัตโนมัติ)
        """
        self._headers = {
            "Authorization": "Bearer " + token.strip(),
            "Content-Type": "application/json",
            "User-Agent": config_mod.user_agent(),
        }

    # ---- ขั้นพื้นฐาน ----

    def _request(self, method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Any:
        """เรียก Cloudflare API หนึ่งครั้ง (กลางของทุก request).

        Args:
            method: HTTP method (GET/POST/PATCH/DELETE)
            path: path ของ API หลัง API_BASE เช่น "/zones"
            body: dict body ที่จะส่ง (POST/PATCH) — None = ไม่มี body

        Returns:
            Any: ค่า "result" จาก response ของ Cloudflare

        Raises:
            CloudflareRateLimit: โดน HTTP 429 (rate limit)
            CloudflareError: HTTP error / เชื่อมต่อไม่ได้ / ตอบกลับไม่ใช่ JSON / success=false
        """
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(
            API_BASE + path, data=data, headers=self._headers, method=method
        )
        _stats["calls"] += 1
        log.debug("CF API: %s %s", method, path)
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                raw = response.read().decode("utf-8", "replace")
            status = response.status
        except urllib.error.HTTPError as exc:
            _stats["errors"] += 1
            if exc.code == 429:
                _stats["rate_limited"] += 1
                log.warning("CF API: %s %s -> HTTP 429 (rate limit)", method, path)
                raise CloudflareRateLimit("rate limit (HTTP 429) — เกินโควตาเรียก API") from exc
            detail = ""
            try:
                detail = exc.read().decode("utf-8", "replace")[:500]
            except Exception:
                pass
            log.warning("CF API: %s %s -> HTTP %d", method, path, exc.code)
            raise CloudflareError(f"HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            _stats["errors"] += 1
            log.warning("CF API: %s %s -> เชื่อมต่อไม่ได้: %s", method, path, exc.reason)
            raise CloudflareError(f"เชื่อมต่อ Cloudflare ไม่ได้: {exc.reason}") from exc

        log.debug("CF API: %s %s -> %d", method, path, status)
        try:
            payload = json.loads(raw)
        except ValueError as exc:
            _stats["errors"] += 1
            log.warning("CF API: %s %s -> ตอบกลับไม่ใช่ JSON", method, path)
            raise CloudflareError(f"ตอบกลับมาไม่ใช่ JSON: {raw[:200]}") from exc

        if not payload.get("success"):
            _stats["errors"] += 1
            messages = [m.get("message", "") for m in payload.get("errors", [])]
            code = payload.get("errors", [{}])[0].get("code", "")
            log.warning("CF API: %s %s -> success=false (code %s)", method, path, code)
            raise CloudflareError(f"API error (code {code}): {'; '.join(messages)}")
        return payload.get("result")

    # ---- token / zone ----

    def verify_token(self) -> Any:
        """ตรวจว่า token ใช้งานได้.

        Returns:
            Any: result ของ /user/tokens/verify

        Raises:
            CloudflareError: token ไม่ถูกต้องหรือเชื่อมต่อไม่ได้
        """
        return self._request("GET", "/user/tokens/verify")

    def list_zones(self) -> List[Dict[str, Any]]:
        """คืนรายชื่อ zone ทั้งหมดที่ token นี้เข้าถึงได้ (paginate อัตโนมัติ).

        Returns:
            list[dict]: รายการ zone จาก Cloudflare
        """
        zones: List[Dict[str, Any]] = []
        page = 1
        while True:
            result = self._request("GET", f"/zones?per_page=100&page={page}")
            if not result:
                break
            zones.extend(result)
            if len(result) < 100:
                break
            page += 1
        return zones

    def get_zone_id(self, zone: str) -> str:
        """หาที่อยู่ zone_id จากชื่อ zone.

        Args:
            zone: ชื่อโดเมน/zone เช่น "example.com"

        Returns:
            str: zone_id ของ zone นั้น

        Raises:
            CloudflareError: ไม่พบ zone ที่ชื่อนี้ใน account
        """
        quoted = urllib.parse.quote(zone)
        result = self._request("GET", f"/zones?name={quoted}")
        if not result:
            raise CloudflareError(f"ไม่พบ zone ที่ชื่อ '{zone}' ใน account นี้")
        return result[0]["id"]

    def guess_zone_id(self, record_name: str) -> Tuple[str, str]:
        """เดา zone จากชื่อ record: ค่อย ๆ ตัดส่วนหน้าออกจนเจอ zone ที่ตรง.

        Args:
            record_name: ชื่อ record เต็ม เช่น "home.example.com"

        Returns:
            tuple[str, str]: (zone_name, zone_id) ที่เจอ

        Raises:
            CloudflareError: หา zone ที่ตรงกับ record ไม่ได้เลย
        """
        parts = record_name.rstrip(".").split(".")
        for start in range(len(parts) - 1):
            candidate = ".".join(parts[start:])
            try:
                return candidate, self.get_zone_id(candidate)
            except CloudflareError:
                continue
        raise CloudflareError(f"ไม่สามารถหา zone ของ record '{record_name}' ได้ ระบุ zone ใน config")

    # ---- dns records ----

    def get_record(self, zone_id: str, name: str, rtype: str) -> Optional[Dict[str, Any]]:
        """คืน record dict หรือ None ถ้ายังไม่มี.

        Args:
            zone_id: id ของ zone
            name: ชื่อ record เต็ม (จะตัด "." ท้ายให้)
            rtype: ชนิด record เช่น "A" / "AAAA"

        Returns:
            dict | None: record ตัวแรกที่เจอ หรือ None ถ้าไม่มี
        """
        query = urllib.parse.urlencode(
            {"name": name.rstrip("."), "type": rtype, "per_page": 100}, safe="*"
        )
        result = self._request("GET", f"/zones/{zone_id}/dns_records?{query}")
        return result[0] if result else None

    def list_dns_records(self, zone_id: str, types: Tuple[str, ...] = ("A", "AAAA")) -> List[Dict[str, Any]]:
        """คืน record ทั้งหมดใน zone (เฉพาะชนิด A/AAAA ตามที่ระบุ).

        Args:
            zone_id: id ของ zone
            types: tuple ของชนิด record ที่จะดึง เช่น ("A", "AAAA")

        Returns:
            list[dict]: รายการ record ทั้งหมดจากทุกหน้า
        """
        out: List[Dict[str, Any]] = []
        for rtype in types:
            page = 1
            while True:
                result = self._request(
                    "GET", f"/zones/{zone_id}/dns_records?type={rtype}&per_page=100&page={page}"
                )
                if not result:
                    break
                out.extend(result)
                if len(result) < 100:
                    break
                page += 1
        return out

    def update_record(self, zone_id: str, record_id: str, content: str, ttl: int, proxied: bool) -> Any:
        """แก้ IP ของ record ที่มีอยู่.

        Args:
            zone_id: id ของ zone
            record_id: id ของ record ที่จะแก้
            content: IP/ค่าที่จะเขียน (เช่น "1.2.3.4")
            ttl: ค่า TTL (วินาที)
            proxied: เปิด Cloudflare proxy หรือไม่

        Returns:
            Any: result ของ API

        Raises:
            CloudflareError: API error
        """
        return self._request(
            "PATCH",
            f"/zones/{zone_id}/dns_records/{record_id}",
            {"content": content, "ttl": int(ttl), "proxied": bool(proxied)},
        )

    def delete_record(self, zone_id: str, record_id: str) -> Any:
        """ลบ record.

        Args:
            zone_id: id ของ zone
            record_id: id ของ record ที่จะลบ

        Returns:
            Any: result ของ API
        """
        return self._request("DELETE", f"/zones/{zone_id}/dns_records/{record_id}")

    def create_record(self, zone_id: str, name: str, rtype: str, content: str, ttl: int, proxied: bool) -> Any:
        """สร้าง record ใหม่ (ใช้เมื่อ record ยังไม่มีใน Cloudflare).

        Args:
            zone_id: id ของ zone
            name: ชื่อ record เต็ม
            rtype: ชนิด record เช่น "A" / "AAAA"
            content: ค่า IP ที่จะเขียน
            ttl: ค่า TTL (วินาที)
            proxied: เปิด Cloudflare proxy หรือไม่

        Returns:
            Any: result ของ API
        """
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
