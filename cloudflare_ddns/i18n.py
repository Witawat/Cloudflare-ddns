"""i18n อย่างง่าย (stdlib ล้วน) — รองรับ 2 ภาษา (ไทย/อังกฤษ).

- t(lang, key, **vars): ดึงข้อความตาม key + แทนที่ {var} ใน template
- detect_lang(cookie, accept_language): ลำดับ cookie cfddns_lang -> Accept-Language -> th
- validate_dicts(): ตรวจว่า th/en มี key ชุดเดียวกัน (ใช้ในเทสต์กัน drift)
"""

import string

from . import lang as _lang

DEFAULT_LANG = "th"
SUPPORTED = ("th", "en")
_COOKIE_KEY = "cfddns_lang"


def supported_langs():
    return list(SUPPORTED)


def _dicts():
    return {"th": _lang.TH, "en": _lang.EN}


def normalize(code):
    """normalize locale -> 'th'/'en'/DEFAULT (รองรับ en-US, th-TH, en_US, 'en,zh-CN')"""
    code = (code or "").split(",")[0].strip().split(";")[0].strip().replace("_", "-")
    base = code.split("-")[0].lower()
    if base == "th":
        return "th"
    if base == "en":
        return "en"
    return DEFAULT_LANG


def detect_lang(cookie="", accept_language=""):
    """ลำดับภาษา: cookie cfddns_lang -> Accept-Language -> DEFAULT"""
    for part in (cookie or "").split(";"):
        key, _, value = part.strip().partition("=")
        if key == _COOKIE_KEY and value.strip() in SUPPORTED:
            return value.strip()
    return normalize(accept_language)


class _DefaultDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def t(lang, key, *args, **vars):
    """คืนข้อความตามภาษา + แทนที่ {var} (named) หรือ {} (positional).

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


def validate_dicts():
    """คืน list ของ key ที่ th/en ไม่ตรงกัน (รูปแบบ ('th'|'en', key)) — ใช้ในเทสต์"""
    mismatches = []
    th, en = _dicts()["th"], _dicts()["en"]
    for key in th:
        if key not in en:
            mismatches.append(("en", key))
    for key in en:
        if key not in th:
            mismatches.append(("th", key))
    return mismatches
