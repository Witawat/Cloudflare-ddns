# ประวัติการเปลี่ยนแปลง (Changelog)

รูปแบบ: [Semantic Versioning](https://semver.org/) — เวอร์ชัน 1.x.x (ยังไม่ release เป็น tag)

## [1.3.0] — 2026-08-16

### เพิ่ม (Features)

- **กันสุ่มรหัสผ่านหน้า login**: ผิด 5 ครั้งติดต่อกัน → ล็อกชั่วคราว 5 นาที (ตอบ HTTP 429 พร้อมเวลาที่เหลือ) + หน่วง 0.4 วิ หลังผิดทุกครั้ง + log เตือน — นับในหน่วยความจำ (restart = เริ่มใหม่)
- **log + สถิติการเรียก Cloudflare API**: log ทุก request (ระดับ debug) + log error/rate limit/ตอบไม่ใช่ JSON (ระดับ warning) — ตัวนับสะสม (เรียกทั้งหมด / error / 429) แสดงใน `/status.json` (`api_stats`) และ Web UI (การ์ดสถานะ IP)

### ปรับปรุง

- เอกสารระบุข้อกำหนดระบบ: Windows 10/11 x64 (รองรับเต็ม) · 8.1 ใช้งานได้ · 7 ไม่รองรับ · ไม่มี build สำหรับ Linux/macOS (โปรเจกต์ออกแบบเป็น Windows Service)

## [1.2.0] — 2026-08-16

### เพิ่ม (Features)

- **เริ่ม/หยุด service** แยกจากปุ่ม Restart (ต้อง admin; หยุดทำไม่ได้เมื่อเว็บรันใน service กันตัดการเชื่อมต่อตัวเอง)
- **บอก context ของหน้าเว็บ** ใน panel Windows Service: รันใน service / standalone · มี/ไม่มีสิทธิ์ admin — ปุ่มที่ทำไม่ได้จะปิดอัตโนมัติ
- **ปุ่ม "ตรวจ DDNS ตอนนี้"**: รันรอบ DDNS ทันที (ไม่รอรอบถัดไป) — รันแบบ async + กันซ้ำถ้ายังไม่เสร็จ
- **เช็คเวอร์ชันใหม่จาก GitHub Releases** (cache 6 ชม.): มีเวอร์ชันใหม่ → แสดง pill ในแถบบน (คลิกไปหน้า release)
- **ปุ่ม "เปิดโฟลเดอร์ข้อมูล"** (ข้าง Log): เปิดโฟลเดอร์ config/state/logs ให้ดู/แก้ด้วยมือ

## [1.1.0] — 2026-08-16

### เพิ่ม (Features)

- **ควบคุม Windows Service จาก Web UI**: ปุ่มติดตั้ง / Restart / ถอนการติดตั้ง (พร้อม confirm 2 ชั้น + ข้อควรรู้) — ต้องเปิด webui ด้วยสิทธิ์ admin; ถอนทำได้เฉพาะตอน service หยุด (กันตัดการเชื่อมต่อตัวเอง) — restart แบบ async (หน้าเว็บหลุด ~10-15 วิ แล้วกลับมาเอง)
- **แสดงเวอร์ชัน**: โปรแกรม (แถบบน + `/status.json`) และเวอร์ชัน cloudflared (การ์ด Tunnel, cache 5 นาที)

## [1.0.1] — 2026-08-16

### แก้บั๊ก (Fixes)

- Web UI แสดง error ของ record ได้จริง (ก่อนหน้านี้ `record_errors` ว่างเสมอ) + status pill "มีปัญหา" ทำงานตาม error ล่าสุด — error ถูกจดใน state และล้างอัตโนมัติเมื่อสำเร็จ/ปิด family/ลบ record
- wizard ตั้งค่าครั้งแรกไม่ทับค่าที่ตั้งไว้เดิม: `webui_port`, `log_dir`, `daily_report(เวลา)`, tunnel (token/path/hosts) — ก่อนหน้านี้ rerun wizard แล้วค่าพวกนี้กลับเป็นค่าเริ่มต้น
- wizard tunnel step สุดท้ายไม่ทำ `tunnel_hosts` ที่ "ซิงค์จาก Cloudflare" ไว้หาย
- STUN IPv6: XOR mask ผิดตาม RFC 8489 (12 → 16 ไบต์) — แก้การอ่าน mapped IPv6
- `get_record` (Cloudflare API) เพิ่ม `per_page=100` — กันพลาด record ที่อยู่หลังหน้าแรกแล้วสร้างซ้ำ
- `tunnel.pid` ตรวจ process ติด PermissionError (รันต่างสิทธิ์) — ตอนนี้นับว่ายังรันอยู่
- validate config: ตรวจ `webui_port` อยู่ในช่วง 1–65535 + clamp ตอนอ่าน (กัน Web UI bind ไม่ได้)
- status command: แผนที่สถานะ service ครบทุกสถานะ (stopping/resuming/pausing/paused)
- หน้า login: แสดง "รหัสผ่านไม่ถูกต้อง" ในหน้า (แทน alert)
- คัดลอกชื่อ record: ก่อนหน้านี้ชื่อติด `|A`/`|AAAA` (key ภายใน state) มาด้วย — ตอนนี้คัดลอกได้ชื่อล้วน และชนิด A/AAAA แสดงแยกในคอลัมน์เวลา

### ปรับปรุง

- wizard: แถว record ใน wizard ใช้ grid 4 คอลัมน์ (ก่อนหน้าว่างช่องพิเศษ)
- เอกสาร: `config.example.ini` แก้คำอธิบาย log_dir (ข้าง exe ไม่ใช่ ProgramData), USAGE.md ฟอร์ม tunnel

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
