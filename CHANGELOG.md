# ประวัติการเปลี่ยนแปลง (Changelog)

รูปแบบ: [Semantic Versioning](https://semver.org/) — เวอร์ชัน 1.x.x (ยังไม่ release เป็น tag)

## [1.0.0] — 2026-08-15

### เพิ่ม (Features)

- **DDNS หลัก:** ตรวจ IP สาธารณะ IPv4/IPv6 ผ่านหลาย provider สำรอง (ipify, ifconfig.me, icanhazip, Cloudflare trace) — อัปเดต A/AAAA เฉพาะเมื่อ IP เปลี่ยน + สร้าง record ให้อัตโนมัติถ้ายังไม่มี
- **Windows Service จริง** (pywin32): เริ่มเองตอน boot, log รายวัน, แก้ config ได้ระหว่างรัน (อ่านใหม่ทุกรอบ)
- **Web UI** (stdlib ล้วน, localhost): สถานะสด + ฟอร์มตั้งค่า + โหมดแก้ไขไฟล์ตรง + wizard ครั้งแรก 5 ขั้น + responsive + ฟอนต์ scale ตามจอ
- **แจ้งเตือน Telegram**: 4 เหตุการณ์ (เริ่ม/หยุด, IP เปลี่ยน, error, สร้าง record) + สรุปรายวัน + คิว retry (ส่งใหม่ทุกรอบ, สูงสุด 50) + กันสแปม error ซ้ำ + หา chat_id อัตโนมัติ (getUpdates)
- **Cloudflare Tunnel (cloudflared)**: ดาวน์โหลดอัตโนมัติ, เริ่ม/หยุดตาม service, wizard 4 ขั้น, ผูก hostname อัตโนมัติ (decode token → ตั้ง ingress + สร้าง CNAME), ดู/ลบ hostname ที่ผูกแล้ว, ตรวจชื่อชน A/AAAA
- **ตรวจ NAT (STUN)**: ตรวจจับ CGNAT/private IP + แจ้งเตือน
- **สแกนพอร์ต** ในเว็บ (จำกัดเฉพาะ host ใน config)
- **ประวัติการอัปเดต** + **ดู log** ในเว็บ + **auto-backup config** (หมุน 5 อัน)
- **EXE ไฟล์เดียว** (PyInstaller + ไอคอน) — ใช้ได้ทุกคำสั่ง + รันเปล่า = เปิด Web UI
- เอกสาร: README, docs/GETTING-STARTED, LICENSE (MIT), PRODUCT/DESIGN

### แก้ไข/ปรับปรุง

- ข้อมูล runtime (state, queue, log) อยู่**ข้าง exe** (ย้ายจาก ProgramData ให้อัตโนมัติครั้งเดียว)
- .bat เป็นภาษาอังกฤษ + สี (chcp 65001 + CRLF)
- TTL ค่าเริ่มต้น 60 (IP ใหม่กระจายเร็วสุด)
- เขียนไฟล์ atomic (temp+rename) กันข้อมูลเสีย

### แก้บั๊ก (Fixes)

- service crash 1053: `PrepareServiceHost` → `PrepareToHostSingle` (pywin32 306) + `SvcRun` → `SvcDoRun`
- service crash หลังรอบแรก: KeyError zone_name_cache จาก zone cache ข้ามรอบ + ครอบ loop ด้วย try/except (ไม่ตายเงียบ)
- path ตรวจ token: `/user/token/verify` → `/user/tokens/verify`
- `webui_password` ถูกรีเซ็ตเมื่อบันทึกฟอร์ม (เพิ่มช่องตั้งรหัส + รักษาค่า)
- dry-run เขียน state (แก้: โหมด dry-run ไม่แตะ state)
- service หยุดช้า (รอ 60 วิ) → หยุดภายใน ~5 วิ
- getUpdates 409 (webhook ค้าง) → ลบ webhook ให้อัตโนมัติ
- rate limit 429 → ข้ามรอบ + แจ้งเตือน; แคช zone id ข้ามรอบ
- wizard tunnel: id ซ้ำ `twz-steps`, ไม่เป็น overlay (รวม CSS กับ wizard หลัก)
- ฟอร์มตั้งค่า: webui_port ซ่อน/แก้ไม่ได้, log_dir ไม่มีช่อง
- UI responsive: breakpoint 860, ช่องเวลา daily_report_time สูง 16px, คอลัมน์ record editor, คัดลอกชื่อ record, ตารางประวัติเลื่อนได้

## [0.1.0] — 2026-08-15

- ต้นฉบับ: DDNS loop + config + service + webui ฉบับแรก (ดู commit `66cf458`)
