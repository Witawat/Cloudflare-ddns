# แผน/สถานะ: i18n ภาษาอังกฤษ + ปุ่มสลับภาษา

> สถานะ: **เฟส 1 + 2 เสร็จ + rebuild + bump v2.0.0 (ยังไม่ปล่อย release)** · อัปเดตล่าสุด: 18/08/2026
> บริบท: โปรเจกต์จะใช้สาธารณะ → ทำ i18n เต็มรูปแบบ (2 ภาษา: ไทย/อังกฤษ)

## 1. เป้าหมาย

- หน้าเว็บ + server message เป็น 2 ภาษา (ไทย/อังกฤษ) — สลับด้วยปุ่ม TH/EN ที่ header (จำด้วย localStorage + cookie `cfddns_lang`)
- auto-detect ครั้งแรกจาก `navigator.language` / `Accept-Language` → fallback ไทย
- ใช้ **stdlib ล้วน** (ไม่มี dependency ใหม่)

## 2. สถาปัตยกรรมจริง (implement แล้ว)

```
ฝั่ง Python (server):
  cloudflare_ddns/i18n.py        # t(lang, key, **vars) + detect_lang(cookie, accept_language) + validate_dicts()
  cloudflare_ddns/lang/th.py     # dict ภาษาไทย (89 keys)
  cloudflare_ddns/lang/en.py     # dict ภาษาอังกฤษ (89 keys — key ตรงกัน 100%)
  webui.py                       # self._t()/_lang() อ่าน cookie cfddns_lang -> Accept-Language -> th
                                 # helper module-level รับ lang param: _decode_tunnel_token(token, lang)
                                 # _tunnel_api_error(exc, lang), _update_check_data(lang)

ฝั่ง JS (หน้าเว็บ — แยกไฟล์):
  webui.js                       # const I18N = {th:{...}, en:{...}} (354 keys) + t(key, vars) + fmtDate(locale)
                                 # + LANG (localStorage -> navigator.language) + i18nApply() + setLang()
  webui.html                     # static ข้อความครอบ <span data-i18n="html.NNN"> (115 keys)
  webui_login.html               # LANG_DATA เล็ก + ปุ่มสลับ + อ่าน cookie cfddns_lang
```

- **key ระบบ**: `section.name` template `{var}` (กันลำดับคำสลับ th/en)
- **วันที่**: `fmtDate()` → `toLocaleString("th-TH")` / `"en-GB"` ตามภาษา
- **ปุ่มสลับ**: `localStorage.cfddns_lang` + cookie `cfddns_lang` (ให้ server รู้ภาษาเดียวกัน) + reload

## 3. สถานะเฟส

| เฟส | เนื้อหา | สถานะ |
|---|---|---|
| **1. UI หน้าเว็บ** | webui.js + webui.html + wizard 2 ตัว + toast + ตาราง | ✅ เสร็จ (354 keys th/en + 115 html.*) |
| **2. Server message** | response `message` ทุก endpoint webui.py + login | ✅ เสร็จ (89 keys th/en) |
| **3. log + Telegram** | ข้อความ log ไฟล์ + notifier/ddns/tunnel/heartbeat | ⏳ ยังไม่เริ่ม (แผนเดิม: เฟสหลัง) |

## 4. งานที่ทำแล้ว

1. ✅ สร้าง `i18n.py` + `lang/th.py` + `lang/en.py` (89 keys — ครอบ server message webui.py)
2. ✅ webui.py: `self._t()` + `self._lang()`; แทนที่ ~55 จุด message; helper module-level ส่ง `lang`
3. ✅ webui.js: `I18N` dict 354 keys + `t(key, vars)` + `fmtDate()` + ปุ่มสลับ + `i18nApply()`
4. ✅ webui.html: ครอบ static ข้อความ 115 จุด `data-i18n="html.NNN"`
5. ✅ webui_login.html: 2 ภาษา + ปุ่มสลับ + อ่าน cookie
6. ✅ เทสต์: node syntax + compileall + 101 unit tests + playwright (สลับ th/en + refresh จำได้ + locale วันที่ถูก)

## 5. กับดักที่เจอจริง (รอบนี้)

- **JS shadow `t`**: `const t = ...` (เวลา/tunnel object) บังฟังก์ชัน `t()` ใน scope เดียวกัน → `TypeError: t is not a function` (เจอใน `loadTunnelStatus`, `loadStatus` ×2) — ต้อง rename เป็น `tun`/`ts`
- **I18N dict structure**: th/en block ต้องปิด `},` ให้ถูก — ผมแทรก en ผิดที่ กลายเป็น key ซ้อน ทำ syntax error (ตรวจ `node --check` ทุกครั้งหลังแก้)
- **PowerShell heredoc**: Thai ใน `@'...'@ | python -` ถูกแปลงเป็น `?` — ต้องเขียน patch เป็นไฟล์ .py แล้วรันแทน
- **`html.NNN` ครอบ**: ต้องแยก whitespace ออกจาก span (ไม่งั้น dict เก็บ `\n` เปรียบเทียบไม่ได้) — ครอบเฉพาะ core text
- **`navigator.language` fallback**: `LANG` อ่าน localStorage ก่อน → cookie (ผู้ใช้เลือกแล้วชนะ auto-detect)
- **server vs client ภาษา**: server อ่าน cookie `cfddns_lang` เท่านั้น — ปุ่มสลับต้องตั้งทั้ง localStorage + cookie ให้ตรงกัน

## 6. เหลือทำ (ก่อน release v2.0.0)

1. ✅ **เทสต์ responsive** (ui-verify.mjs + ตรวจ i18n 2 ภาษา) 360–1920px — ผ่าน (ปุ่มภาษาไม่เบียด)
2. ✅ **rebuild exe** (build.bat) — ตรวจแล้ว exe เสิร์ฟ 2 ภาษา (webui.js 117KB + HTML data-i18n + server message en/th ตาม Accept-Language)
3. ✅ **bump v2.0.0** `__init__.py` + CHANGELOG + docs — **ยังไม่ปล่อย release** (ผู้ใช้สั่งไม่ release)
4. (เฟส 3 — แยกได้) log ไฟล์ + Telegram notify ยังคงไทย

## 7. ทางเลือกที่ตัดสินใจไว้แล้ว

- log ไฟล์ + ข้อความ Telegram: **คงไทย** (เฟส 3 ยังไม่ทำ) — log เป็นเครื่องมือ debug ควรภาษาคงที่, Telegram ใช้ notify ตาม config ภาษา
- เอกสาร (README/docs): แปลเป็นเฟสแยก (หลัง i18n โค้ดเสร็จ)
- default ภาษา: `navigator.language` (ต่างชาติได้ eng อัตโนมัติ) — fallback ไทย
