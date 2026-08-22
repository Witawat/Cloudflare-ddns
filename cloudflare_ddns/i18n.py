"""i18n อย่างง่าย (stdlib ล้วน) — รองรับ 2 ภาษา (ไทย/อังกฤษ).

- t(lang, key, **vars): ดึงข้อความตาม key + แทนที่ {var} ใน template
- detect_lang(cookie, accept_language): ลำดับ cookie cfddns_lang -> Accept-Language -> th
- validate_dicts(): ตรวจว่า th/en มี key ชุดเดียวกัน (ใช้ในเทสต์กัน drift)
"""

"""i18n อย่างง่าย (stdlib ล้วน) — รองรับ 2 ภาษา (ไทย/อังกฤษ).

- t(lang, key, **vars): ดึงข้อความตาม key + แทนที่ {var} ใน template
- detect_lang(cookie, accept_language): ลำดับ cookie cfddns_lang -> Accept-Language -> th
- validate_dicts(): ตรวจว่า th/en มี key ชุดเดียวกัน (ใช้ในเทสต์กัน drift)
"""

from typing import Any, Dict, List, Tuple

import string

from . import lang as _lang

DEFAULT_LANG = "th"
SUPPORTED = ("th", "en")
_COOKIE_KEY = "cfddns_lang"


def supported_langs() -> List[str]:
    """คืนรายชื่อภาษาที่รองรับทั้งหมด.

    Returns:
        list[str]: รายชื่อภาษา เช่น ["th", "en"]
    """
    return list(SUPPORTED)


def _dicts() -> Dict[str, Dict[str, str]]:
    """คืน dict ของข้อความทั้งหมดแยกตามภาษา."""
    return {"th": _lang.TH, "en": _lang.EN}


def normalize(code: str) -> str:
    """normalize locale -> 'th'/'en'/DEFAULT (รองรับ en-US, th-TH, en_US, 'en,zh-CN').

    Args:
        code: ค่า locale ที่ส่งมา เช่น "en-US", "th-TH", "en,zh-CN" (อาจเป็น None)

    Returns:
        str: "th" / "en" / DEFAULT_LANG เมื่อระบุไม่ได้
    """
    code = (code or "").split(",")[0].strip().split(";")[0].strip().replace("_", "-")
    base = code.split("-")[0].lower()
    if base == "th":
        return "th"
    if base == "en":
        return "en"
    return DEFAULT_LANG


def detect_lang(cookie: str = "", accept_language: str = "") -> str:
    """ลำดับภาษา: cookie cfddns_lang -> Accept-Language -> DEFAULT.

    Args:
        cookie: ค่า Cookie header จาก request (อาจว่าง)
        accept_language: ค่า Accept-Language header จาก request (อาจว่าง)

    Returns:
        str: รหัสภาษาที่จะใช้ ("th" หรือ "en")
    """
    for part in (cookie or "").split(";"):
        key, _, value = part.strip().partition("=")
        if key == _COOKIE_KEY and value.strip() in SUPPORTED:
            return value.strip()
    return normalize(accept_language)


class _DefaultDict(dict):
    """dict ที่คืน {key} เป็นค่า default เมื่อไม่เจอ key (กัน crash จาก missing var)."""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def t(lang: str, key: str, *args: Any, **vars: Any) -> str:
    """คืนข้อความตามภาษา + แทนที่ {var} (named) หรือ {} (positional).

    Args:
        lang: รหัสภาษา (th/en)
        key: คีย์ของข้อความใน dict ภาษา
        *args: ค่าที่จะแทนที่ในตำแหน่ง {} ของ template
        **vars: ค่าที่จะแทนที่ใน {var} ของ template

    Returns:
        str: ข้อความที่แทนที่ค่าแล้ว

    หมายเหตุ:
        - ไม่เจอ key -> คืน key (ช่วย debug ว่าลืมเพิ่ม)
        - missing var -> คง {var} ไว้ในข้อความ (ไม่ crash)
    """
    d = _dicts().get(normalize(lang), _dicts()[DEFAULT_LANG])
    text = d.get(key)
    if text is None:
        return key
    try:
        return string.Formatter().vformat(text, args, _DefaultDict(vars))
    except (ValueError, KeyError, IndexError):
        return text


def validate_dicts() -> List[Tuple[str, str]]:
    """คืน list ของ key ที่ th/en ไม่ตรงกัน (รูปแบบ ('th'|'en', key)) — ใช้ในเทสต์.

    Returns:
        list[tuple[str, str]]: คู่ (ภาษา, key) ที่มีในภาษาหนึ่งแต่อีกภาษาหนึ่งไม่มี
    """
    mismatches: List[Tuple[str, str]] = []
    th, en = _dicts()["th"], _dicts()["en"]
    for key in th:
        if key not in en:
            mismatches.append(("en", key))
    for key in en:
        if key not in th:
            mismatches.append(("th", key))
    return mismatches
