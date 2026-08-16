# แผน: i18n ภาษาอังกฤษ + ปุ่มสลับภาษา

> สถานะ: **แผนเท่านั้น — ยังไม่เริ่ม** (ผู้ใช้สั่ง "ทำเป็นแผนเพิ่มไว้ก่อนเป็นไฟล์ .md")
> บริบท: โปรเจกต์จะใช้สาธารณะ → ควรทำ i18n เต็มรูปแบบ

## 1. เป้าหมาย

- หน้าเว็บ + server message เป็น 2 ภาษา (ไทย/อังกฤษ) — สลับด้วยปุ่มที่หัวหน้าเว็บ (จำภาษาด้วย localStorage + cookie)
- ใช้ **stdlib ล้วน** (ห้าม dependency ใหม่ ตามกฎโปรเจกต์)

## 2. สถาปัตยกรรมที่เสนอ

```
cloudflare_ddns/i18n.py        # โหลดภาษา + t(key, **vars) + ตรวจจับภาษา
cloudflare_ddns/lang/th.py     # dict ภาษาไทย (~600 keys)
cloudflare_ddns/lang/en.py     # dict ภาษาอังกฤษ (โครงสร้างเดียวกับ th)
```

- **Python (server)**: handler อ่านภาษาจาก cookie `cfddns_lang` / Accept-Language → `t()` แทน string ไทยทุกจุด (response message + log หลัก)
- **JS (หน้าเว็บ)**: ฝัง `LANG_DATA = {th: {...}, en: {...}}` ใน PAGE → ฟังก์ชัน `t(key, vars)` + ปุ่มสลับที่ header (TH/EN) + localStorage — เปลี่ยนภาษาโดย reload หน้า (ง่ายสุด)
- **key ระบบ**: `section.name` เช่น `save.ok`, `log.session_expired`, `record.no_ip` — ข้อความมีตัวแปรใช้ `{name}` template (กันลำดับคำสลับไทย/อังกฤษ)
- **auto-detect ครั้งแรก**: `navigator.language` (ค่าเริ่มต้นไทย)

## 3. ขอบเขตงาน (3 เฟส)

| เฟส | เนื้อหา | ขนาดโดยประมาณ |
|---|---|---|
| **1. UI หน้าเว็บ** | HTML/placeholder/toast/wizard/ตารางทั้งหมดใน PAGE | ~500 keys (งานหลัก) |
| **2. Server message** | response `message` ทุก endpoint (~60 จุด) + หน้า login เดี่ยว | ~80 keys |
| **3. log + Telegram** | ข้อความ log หลัก + notifier/ddns/tunnel/heartbeat | ~80 keys |

## 4. ขั้นตอน

1. สร้าง `i18n.py` + `lang/th.py` + `lang/en.py` (seed จาก string ที่สแกนได้)
2. ฝั่ง Python: แทนที่ string ไทยใน webui handlers → `t()`; เติม cookie lang ใน login/หน้าแรก
3. ฝั่ง JS: เพิ่ม `t()` + `LANG_DATA` + ปุ่มสลับภาษาใน header + ตั้ง `document.documentElement.lang`
4. สแกนซ้ำหา string ไทยที่ตกหล่น (grep ไทยใน PAGE + handlers — วิธีเดียวกับรอบตรวจบั๊ก)
5. เทสต์: ทั้ง 2 ภาษาทุกฟังก์ชันหลัก (playwright: สลับภาษา → ข้อความเปลี่ยน + จำได้หลัง refresh) + เทสต์ชุดเดิมทั้งหมด
6. bump v2.0.0 + CHANGELOG + docs + rebuild/reinstall

## 5. กับดักที่ต้องระวัง (จากประวัติบั๊ก)

- ข้อความใน JS ที่แทรกตัวแปร — ต้อง template `{x}` ไม่ใช่ต่อ string (อังกฤษสลับคำ)
- `t()` ทุกจุดที่แทรก innerHTML ยังต้อง escapeHtml (i18n ไม่แทนที่ security)
- server message ไทย ~60 จุด — ไล่ให้ครบ (เทสต์ grep ไทยค้าง)
- ปุ่มภาษา + id ซ้ำ/position ใน header responsive (360px)
- ไม่ลืม wizard 2 ตัว + login block + หน้า "ตั้งค่าไม่ครบ" error list
- ข้อความที่สร้างจากหลายส่วน (เช่น build_message หัว + detail) — ต้อง t() ทั้ง 2 ฝั่งให้ภาษาเดียวกัน

## 6. ประมาณงาน

~1-2 วันทำงานเต็ม (เฟส 1 ใหญ่สุด) + 1 รอบเทสต์ครอบคลุม — แนะนำทำทีละเฟส + release แยก (v2.0.0 = ภาษา ไม่ปนฟีเจอร์อื่น)

## 7. ทางเลือกที่ตัดสินใจไว้แล้ว

- log ไฟล์ + ข้อความ Telegram: เฟส 3 (หลัง UI+server เสร็จ) — ผู้ใช้สาธารณะเห็น UI/ข้อความตอบเป็นหลัก
- เอกสาร (README/docs): แปลเป็นเฟสแยก (หลัง i18n โค้ดเสร็จ) — ไม่นับในเฟส 1-3
