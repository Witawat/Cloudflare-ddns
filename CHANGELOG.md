# ประวัติการเปลี่ยนแปลง (Changelog)

รูปแบบ: [Semantic Versioning](https://semver.org/) — เวอร์ชัน 1.x.x (ยังไม่ release เป็น tag)

## [1.8.0] — 2026-08-17

### เพิ่ม (Features)

- **รหัสผ่านหน้าเว็บเก็บเป็น hash** (sha256 + salt จากตำแหน่ง config) — ไม่มีรหัสจริงหลุดใน config.ini/cookie อีก (config เดิมที่เก็บ plaintext ย้ายให้อัตโนมัติครั้งเดียว)
- **กู้รหัสผ่านหน้าเว็บ 3 ทาง**: (1) เปลี่ยนในฟอร์มตอน session ยังอยู่ (2) คำสั่งใหม่ `reset-password` (ตั้งใหม่หรือลบรหัส — ใช้ได้แม้ login ไม่ได้) (3) **ผ่าน Telegram (opt-in)**: พิมพ์ `reset password` → ยืนยัน `yes` → โปรแกรมสุ่มรหัสใหม่ 12 ตัวส่งกลับ (เฉพาะ chat_id ที่ตั้งไว้ กัน 1 ครั้ง/10 นาที — เปิดในฟอร์มตั้งค่า/`telegram_allow_reset`)
- **กัน CSRF**: POST ทุกตัว (ยกเว้น /login) ตรวจ Origin — คำขอจากเว็บอื่น (เช่น เปิดหน้า 0.0.0.0 แล้วถูกเว็บโจมตี) ถูกบล็อก 403
- **security headers**: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer` + cookie ใช้ `SameSite=Lax`
- **กัน log injection**: ข้อความจากหน้าเว็บ (log-event) ที่มีขึ้นบรรทัดใหม่ถูกกรองออก
- **ตรวจฉันทามติ IP** (`ip_consensus`): ต้องมี provider ตรวจ IP ≥ 2 รายเห็น IP เดียวกัน ถึงจะอัปเดต record (กัน provider ตอบผิด/ล้าสมัย — ปิด default)
- **service auto-restart**: crash แล้ว Windows เริ่มใหม่เอง (5 วิ ครั้งแรก / 30 วิ ครั้งถัดไป) — กัน service ตายเงียบ (ตอน install)
- **state/queue backup หมุน 3**: `state.json.bak`/`.2`/`.3` + คิวเช่นกัน — เขียนเท่าที่เนื้อหาเปลี่ยน
- **ปุ่มทดสอบ heartbeat** ในฟอร์มตั้งค่า (ส่ง ping ทันที ไม่รอรอบ)
- **ปุ่มเช็คอัปเดต cloudflared** (เทียบเวอร์ชัน exe กับ GitHub releases — cache 6 ชม.)
- **ดาวน์โหลด/นำเข้า config.ini** จากหน้าเว็บ (สำรองข้อมูล/ย้ายเครื่อง — นำเข้าตรวจสอบก่อนเขียน)
- **unit tests 62 ตัว** (`tests/` — unittest stdlib: config/ip_detect/notifier/ddns/main/ความปลอดภัยเว็บ) — รัน `python -m unittest discover -s tests -v`

### แก้บั๊ก (Fixes)

- **login รับเฉพาะรหัสจริง**: เดิม session cookie เทียบกับรหัสจริงใน config — หลังเก็บ hash โค้ดทุกจุด (login/authed/migrate) รองรับทั้ง config ใหม่ (hash) และ config เก่า (plaintext) ชั่วคราว
- **กู้รหัสผ่านใช้ได้แม้ config ยังตั้งไม่ครบ**: เดิม `reset-password`/Telegram reset/migrate hash เขียนผ่าน `save_text` ซึ่ง validate config เต็มก่อนเขียน — ลืมรหัส + config ไม่สมบูรณ์ (เช่น token ว่าง) = กู้ไม่ได้ — ตอนนี้เขียนแบบ atomic ตรง (`atomic_write_text`) ยังตรวจรูปแบบ ini ก่อนเขียน

## [1.7.19] — 2026-08-16

### ปรับปรุง

- **ผลสแกนพอร์ตแสดง icon สถานะ**: 🟢 เปิด · 🔴 ปิด · ⚪ ไม่มีตอบ (ไฟร์วอลล์?) — แยกชัดเจนด้วยตา ไม่ต้องอ่านข้อความ

## [1.7.20] — 2026-08-16

### เพิ่ม (Features)

- **กด exe เปล่า ๆ (double-click) = รัน DDNS loop + Web UI พร้อมกัน** — จากเดิมเปิดแค่หน้าเว็บรอเฉย ๆ (ไม่มีอัปเดต) — ตอนนี้เปิด exe ครั้งเดียวทำงานเต็มรูปแบบ เหมือน service แต่เป็น foreground (ปิดด้วย Ctrl+C — จะแจ้ง Telegram "หยุดทำงาน" ให้)
- **กันข้อความว่างเข้าคิว Telegram**: เดิมถ้ามีเหตุการณ์ที่สร้างข้อความว่าง (เช่น คิวเก่า/ค่า config ซ้ำ) จะติดคิวและส่งไม่สำเร็จ HTTP 400 ซ้ำไม่จบ — ตอนนี้ข้ามข้อความว่างทันที (log debug)
- **ตรวจ NAT 3 ชั้น (เจอ CGNAT/double NAT ได้แม่นขึ้น)**: นอกจากการเช็ค IP จาก provider + STUN รอบเดียว — เพิ่ม (1) tracert ดูฮอปแรกหลัง WAN (เห็น 100.64/10 = CGNAT ของ ISP · เห็น IP private = NAT ซ้อนหลายชั้น) (2) STUN ซ้ำ 4 รอบเช็ค mapped port เปลี่ยนไหม (symmetric mapping) — ผลใหม่มี `tracert` + `stun_rounds` และ `nat_type` ใหม่ **`double-nat`** (DDNS อัปเดต IP ได้ แต่คนนอกเข้าไม่ถึง — ต้องเปิด port ทุกชั้นหรือใช้ Tunnel) — หน้าเว็บ: CGNAT/private = ⚠ แดง · double NAT = ⚠ เหลือง (เตือน) · ปกติ = ✓ เขียว — service เตือนผ่าน Telegram เมื่อเจอ double NAT ด้วย

## [1.7.21] — 2026-08-16

### แก้บั๊ก (Fixes)

- **ข้อมูล runtime อยู่ที่เดียวกับ exe ไม่ว่า exe อยู่ที่ไหน**: state.json/notify_queue.json/logs/tunnel.pid/cloudflared.exe คำนวณจาก **config.ini ที่ใช้จริง** (config วางข้าง exe เสมอ) — ก่อนหน้านี้ state/queue/log ผูกกับ "โฟลเดอร์ที่รันโปรแกรม" (root vs dist) ทำให้รัน exe + python/--config พร้อมกันได้ข้อมูล 2 ชุด (รอบล่าสุดไม่ตรงกัน / คิว Telegram คนละที่ / HTTP 400 ข้อความว่างซ้ำ) — ตอนนี้ `--config` อะไร → data ข้างนั้น ชุดเดียวจบ
- **`--config` ใช้ได้ทั้งหน้า/หลัง subcommand**: เดิมวางหน้า subcommand (เช่น `--config X run`) โดน argparse ทับด้วยค่าเริ่มต้นเงียบ ๆ — ตอนนี้ถูกต้องทั้ง 2 แบบ (ยังแนะนำวางหลัง เช่น `run --config X`)

### ปรับปรุง

- **กด exe เปล่า ๆ = เทียบเท่า service ครบจบ**: เพิ่มเริ่ม **Cloudflare Tunnel** ด้วย (เดิมกด exe ไม่เปิด tunnel — เปิดเฉพาะ service) — ตอนนี้ exe ครั้งเดียว = Web UI + DDNS loop + Tunnel + Telegram (หยุดครบเมื่อ Ctrl+C)
- **เปิด Web UI ชนพอร์ต → ข้อความไทยชัด** ("พอร์ต 8123 ถูกใช้งาน — ปิดตัวก่อนหรือใช้ --port") ไม่ crash เงียบ
- ล้าง state/queue/log เก่าที่แยกชุด (root) ทิ้งแล้ว — เหลือชุดเดียวข้าง exe

## [1.7.23] — 2026-08-17

### แก้บั๊ก (Fixes)

- **ตัวเช็คอัปเดตเทียบเวอร์ชัน 4 ส่วนผิด** (เช่น `1.7.22.1` โดนตัดเหลือ 3 ส่วน → เทียบเท่ากัน → ไม่แจ้งว่ามีใหม่) — แก้ให้เติม 0 ให้ความยาวเท่ากันก่อนเปรียบเทียบ

## [1.7.22] — 2026-08-16

### ปรับปรุง (Development)

- **แยก HTML/CSS และ JavaScript ออกจาก webui.py**: หน้าเว็บทั้งหมดย้ายไป `cloudflare_ddns/webui.html` (HTML+CSS) + `cloudflare_ddns/webui.js` (JS ล้วน) — webui.py เหลือแค่ Python logic (handler/endpoints) — แก้หน้าตา/JS ไม่ต้องยุ่ง Python string escape (ปัญหา `\"`/quote หายไป) · build scripts เพิ่ม `--add-data` ฝังไฟล์ทั้ง 2 เข้า exe (serve ผ่าน `/` และ `/webui.js`)
- **แยกหน้า login เป็นไฟล์ `webui_login.html`** (เดิมเป็น Python string ใน webui.py) — ยังใช้ CSS เดียวกับหน้า main · **ปุ่ม "รีเฟรช" โหลดทุกส่วนใหม่หมด** (สถานะ/IP/NAT/log/tunnel/service/config) — จากเดิมโหลดแค่สถานะ · เพิ่มเครดิต/ไลเซน + ลิงก์ GitHub ที่หน้า login (ขึ้นบรรทัดใหม่ไม่ล้นจอเล็ก)
- **exe เล็กลง 17% ด้วย UPX**: 9.7MB → 8MB — build.bat/build-install.bat บีบให้อัตโนมัติ (tools/upx.exe) — ถ้าเครื่องไม่มี UPX ข้ามได้ (ยัง build ปกติ)
- **คู่มือทดสอบ release** (`docs/RELEASE-TEST.md` + `test-release.mjs`): จำลองผู้ใช้ใหม่ (โฟลเดอร์ใหม่ + exe เปล่า ๆ) → เดิน wizard ครบ 5 ขั้นด้วย playwright 15 รายการ — ผลเทสต์ล่าสุด **15/15 (100%)**

### แก้บั๊ก (Fixes)

- **ข้อมูล runtime อยู่ที่เดียวกับ exe ไม่ว่า exe อยู่ที่ไหน**: state/queue/log/tunnel.pid/cloudflared.exe คำนวณจาก **config.ini ที่ใช้จริง** — กัน state/queue แยกชุด (root vs dist) — รอบล่าสุดไม่ตรงกัน / คิว Telegram คนละที่ / HTTP 400 ข้อความว่างซ้ำ — หมดไป (รวมไม่ifier กรองข้อความว่างในคิว + ล้างคิวขยะ ProgramData)
- **`--config` ใช้ได้ทั้งหน้า/หลัง subcommand** (เดิมวางหน้าโดน argparse ทับเงียบ ๆ)
- **เปิด Web UI ชนพอร์ต → ข้อความไทยชัด** ไม่ crash เงียบ
- **หน้าเว็บ CSS เพี้ยนหลังแยกไฟล์**: DOCTYPE หาย (quirks mode) + `<style>` ซ้อนแท็กในหน้า login — แก้ทั้ง 2
- **wizard ขั้น Telegram: เพิ่มช่องกรอก chat id ด้วยมือ** (กรณี bot ไม่มีข้อความใหม่ resolve ไม่ได้ — เดิมตั้งค่า Telegram ไม่ได้เลย)
- **เลือก record จาก Cloudflare: ตัดชื่อเต็มเป็นชื่อย่อ + เติม zone ให้อัตโนมัติ** (home.example.com → home + example.com — ทั้งฟอร์มหลักและ wizard)
- **/status.json กรอง record ที่ลบออกจาก config แล้ว** (cache เก่าไม่โชว์ค้าง)
- **ตัวตรวจ NAT แม่นขึ้น + หน้าตาใหม่**: ตรวจ 3 ชั้น (provider + tracert ฮอปแรกหลัง WAN + STUN ซ้ำ) — **NAT บ้าน (double-nat กี่ชั้นก็ได้) = เขียว "เป็น NAT ส่วนตัวในบ้าน (ซ้อน N ชั้น)"** — **CGNAT ของ ISP = แดง** — แสดงเป็นการ์ดแถบสี (ไอคอนวงกลม + พื้นหลังสีอ่อนสด) · ไม่ส่ง Telegram เตือนสำหรับ NAT บ้าน
- **จัด layout จอมือถือ**: ตารางทุกแบบบีบตามจอ (ไม่เลื่อนแนวนอน) · ปุ่มการ์ดสถานะ IP เรียงเท่ากัน · NAT box ไม่ล้น — เทสต์ 360/768/1920 ผ่าน

### ปรับปรุง

- **กด exe เปล่า ๆ = เทียบเท่า service ครบจบ**: Web UI + DDNS loop + Cloudflare Tunnel + Telegram (ปิดด้วย Ctrl+C หยุดครบ) — จากเดิมเปิดแค่หน้าเว็บรอเฉย ๆ

### แก้บั๊ก (Fixes)

- **หน้าเว็บ CSS เพี้ยนหลังแยกไฟล์**: (1) `<!DOCTYPE html>` หายจาก webui.html (ติดกับบรรทัดเดิมของ `PAGE = """`) → เบราว์เซอร์รัน quirks mode (2) หน้า login แทรก `<style>` ซ้อนแท็ก (CSS ที่สกัดมามีแท็กครบแล้ว) → variables ไม่ resolve หน้าเป็นพื้นโปร่งใส — แก้ทั้ง 2 จุด ตรวจด้วย computed style แล้วกลับมาเหมือนเดิม

## [1.7.18] — 2026-08-16

### แก้บั๊ก (Fixes)

- **ตารางล้นกรอบบนมือถือ (แสดงผลไม่ครบ)**: ตาราง "hostname ที่ผูกแล้ว", "สแกนพอร์ต" และ "คิว Telegram" เดิมใช้ `overflow:hidden` (เนื้อหายาวถูกตัด/ล้น) — เปลี่ยนเป็น **เลื่อนแนวนอนภายในตาราง** (overflow-x:auto + ความกว้างขั้นต่ำ) — บนจอเล็กเลื่อนดูได้ ไม่ล้นกรอบหน้า

## [1.7.17] — 2026-08-16

### เพิ่ม (Features)

- **ปุ่มตา 👁 ในช่อง password ทุกช่อง** (แสดง/ซ่อน): หน้า login, API token, รหัสผ่านหน้าเว็บ, Bot token (ฟอร์มหลัก + wizard) — กดแล้วเห็นข้อความ ไม่ต้องเดา
- **ปุ่ม "ล้าง log"** (ข้าง "โหลดใหม่" ในแถบ Log ล่าสุด) — ล้างไฟล์ log ทั้งหมด (พร้อม confirm) — ไม่กระทบการทำงาน

### ปรับปรุง

- **เลือกชนิด tunnel → ใช้พอร์ตเริ่มต้นต่อชนิด** (https→443, tcp→22, udp→51820, http→8080) — จากเดิมรักษาพอร์ตเดิม (ทำให้ทุกชนิดเป็น :3000 ตามค่าที่พิมพ์) — เปลี่ยนชนิดทีไรเห็นค่าที่ถูกต้องต่อชนิดทันที

## [1.7.16] — 2026-08-16

### ปรับปรุง

- **เลือกชนิด tunnel แล้ว "บริการ/พอร์ต" เปลี่ยนตามอัตโนมัติ** (ทั้ง wizard และฟอร์ม "+ เพิ่ม hostname"): เปลี่ยน scheme ให้ตรงชนิด โดย**รักษาพอร์ตที่พิมพ์ไว้** (เช่น `http://localhost:3000` → เลือก HTTPS → `https://localhost:3000`) — ถ้าค่าไม่ใช่รูปแบบ `scheme://host:port` จะใช้ค่าเริ่มต้นต่อชนิด (http→8080, https→443, tcp→22, udp→51820)

## [1.7.15] — 2026-08-16

### แก้บั๊ก (Fixes)

- **ครอบ do_GET ด้วย try/except** (เหมือน do_POST ที่ทำใน v1.7.14): error ภายในฝั่ง GET (สถานะ/config/log ฯลฯ) ไม่ตัด connection เงียบ ๆ อีก — ตอบ JSON 500 + log ละเอียด
- **fetch ฝั่งหน้าเว็บมี timeout + ข้อความไทยชัด**: ทุกคำขอมี timeout 90 วิ (กันค้างไม่มีที่สิ้นสุด) · error เปลี่ยนจาก "Failed to fetch" งง ๆ เป็น "เชื่อมต่อ server ไม่ได้ (network error) — ลองใหม่ หรือดู log" / "timeout — server ไม่ตอบกลับภายใน 90 วิ" — ทุกจุดในหน้า (ฟอร์ม/wizard/ปุ่ม) ได้ข้อความเดียวกัน (wrap ครั้งเดียวที่ window.fetch)

## [1.7.14] — 2026-08-16

### แก้บั๊ก (Fixes)

- **"Failed to fetch" ตอนผูก hostname (ทั้งที่ข้อมูลบันทึกไปแล้ว)**: ถ้า server เกิด error กลางคำสั่ง (เช่น error ที่ไม่ใช่ CloudflareError) — เดิม exception หลุด → connection ถูกตัด → เบราว์เซอร์เห็น "Failed to fetch" ไม่รู้ผล — ตอนนี้**ทุกคำสั่ง POST ถูกครอบด้วย try/except** → error ภายในตอบเป็น JSON 500 พร้อม log ละเอียด (แถบ Log ล่าสุดเห็นบรรทัด `do_POST เกิดข้อผิดพลาด`) + ข้อความเตือนว่าข้อมูลบางส่วนอาจถูกบันทึกไปแล้ว — ตรวจซ้ำได้

## [1.7.13] — 2026-08-16

### แก้บั๊ก (Fixes)

- **ปุ่ม "แก้ไข" hostname แสดงโดเมนไม่ขึ้นถ้ายังไม่เคยเปิดฟอร์ม "+ เพิ่ม hostname"**: dropdown โดเมนโหลดทีหลังค่าที่ตั้งไว้ → โดเมนหาย — ตอนนี้โหลด dropdown ก่อนแล้วค่อยเลือกโดเมนให้อัตโนมัติ (แยกฟังก์ชันโหลด dropdown ใช้ร่วมฟอร์มเพิ่ม/แก้ไข)
- **console error ตอนกดแก้ไข**: `$("th-add-form")` — id จริงคือ `tunnel-add-form` → error scrollIntoView — แก้แล้ว

## [1.7.12] — 2026-08-16

### ปรับปรุง

- **คำแนะนำเลือกชนิด protocol ใน WebUI** (ทั้ง wizard tunnel และฟอร์ม "+ เพิ่ม hostname"): HTTP = เว็บธรรมดา · HTTPS = พอร์ต SSL (443/8443 — ต้องใช้ `https://localhost:443` ไม่งั้นเจอ "Bad Request") · TCP/UDP = SSH/game/VPN

## [1.7.11] — 2026-08-16

### แก้บั๊ก (Fixes)

- **tunnel ใหม่ที่ยังไม่เคยตั้งค่า ingress ใช้ได้**: Cloudflare คืน `"config": null` สำหรับ tunnel ใหม่ → โค้ดอ่าน ingress พังทุกจุด (ดู hostname/ผูก/ลบ/ซิงค์) — ตอนนี้จัดการ `config: null` ได้ (พบจริงระหว่างทดสอบกับ tunnel ใหม่)
- **ผูก hostname ซ้ำ (แก้ไข) แล้ว validation fail 1056**: ทุกครั้งที่ผูก โค้ด append rule `http_status:404` ซ้ำกับตัวที่มีอยู่ → Cloudflare ปฏิเสธ "Rule #1 matching hostname '' ... rules after never triggered" — ตอนนี้ลบ 404 เดิมก่อนเพิ่มใหม่ (ผูกซ้ำ = แก้ไข map ได้จริง)

## [1.7.10] — 2026-08-16

### ปรับปรุง

- **ข้อความ error ตอน token ไม่มีสิทธิ์ Tunnel ชัดเจน**: ถ้าเรียก API tunnel แล้วโดน 403 จะแนะนำวิธีแก้ทันที — "API token ไม่มีสิทธิ์จัดการ Tunnel — ไปที่ dash.cloudflare.com → My Profile → API Tokens → Edit → เพิ่มสิทธิ์ Account → Cloudflare Tunnel → Edit" (ทุกจุด: ดู hostname/ผูก/ลบ/ซิงค์)
- **แก้ label "ชื่อ (subdomain)" ล้นช่อง** ใน wizard tunnel — ย่อข้อความ + หมายเหตุแยกบรรทัดใต้ช่อง

## [1.7.9] — 2026-08-16

### ปรับปรุง

- **ช่อง Tunnel Token เต็มช่องสวยเหมือน input**: เพิ่ม textarea ใน CSS ของฟอร์ม (width 100% + ขอบโค้ง + resize ได้) + ย้ายช่อง token ออกจากคอลัมน์คู่ (เต็มความกว้างทั้งบรรทัด)
- **ปุ่ม "แก้ไข" ในรายการ hostname ที่ผูกกับ tunnel**: กดแก้ไข → โหลดค่าเดิมลงฟอร์ม → เปลี่ยน service/port/path/protocol → กด "ผูกกับ tunnel" = แทนที่ของเดิม (ไม่ต้องลบแล้วเพิ่มใหม่)

## [1.7.8] — 2026-08-16

### ปรับปรุง

- **ช่อง Tunnel Token เป็น textarea (ทั้ง wizard และฟอร์มตั้งค่า)**: token ยาว ๆ วางได้เต็มช่อง เห็นข้อความทั้งหมด ไม่ถูกซ่อนด้วย dots
- **ใช้ชื่อ subdomain ใหม่ที่ไม่เคยมีได้ชัดเจนขึ้น**: wizard ระบุ "ใช้ชื่อใหม่ที่ไม่เคยมีก็ได้" — โปรแกรมสร้าง DNS record ให้อัตโนมัติ

## [1.7.7] — 2026-08-16

### แก้บั๊ก (Fixes)

- **tunnel token รูปแบบใหม่ของ Cloudflare ใช้ได้**: Zero Trust ปัจจุบันให้ token แบบ 1 ส่วน (payload ล้วน ไม่ใช่ JWT 3 ส่วน) — โค้ดตรวจรูปแบบเดิมคาดว่าเป็น 3 ส่วน (`split(".")[1]`) เลยปฏิเสธ token ที่ถูกต้อง ("tunnel token ผิดรูปแบบ") — ตอนนี้รองรับทั้ง 2 รูปแบบ

## [1.7.6] — 2026-08-16

### ปรับปรุง

- **User-Agent ระบุชื่อเครื่อง**: ทุกคำขอออกจากโปรแกรม (heartbeat, ตรวจ IP, Cloudflare API, เช็คเวอร์ชัน, ดาวน์โหลด cloudflared) ส่ง `cloudflare-ddns-updater/<เวอร์ชัน> (<ชื่อเครื่อง>)` — ฝั่งบริการ (Healthchecks.io / Cloudflare / provider) ดู log แล้วรู้ว่ามาจากเครื่องไหน

## [1.7.5] — 2026-08-16

### ปรับปรุง

- **กันส่ง heartbeat ถี่เกินไป**: ต่อ URL หนึ่ง ห่างกันน้อยกว่า 30 วิจะข้าม (กันกรณีโปรแกรมรันซ้ำหลาย instance / config ผิด — ที่ Healthchecks เห็น ping ทุก 4-5 วิ) — ยังส่งปกติ 1 ครั้ง/รอบ DDNS

## [1.7.4] — 2026-08-16

### ปรับปรุง

- **Heartbeat log ละเอียดขึ้น + กันสแปม**: เมื่อส่ง heartbeat ไม่ได้ log จะบอกสาเหตุจริง (เช่น `HTTP 429 (บริการปลายทางปฏิเสธ)` / `URLError: timed out`) — จากเดิมบอกแค่ URL · แจ้ง warning ครั้งเดียวต่อ 10 นาที (หลุดยาวไม่สแปม log) · retry 1 ครั้งเฉพาะ network error (ไม่ยิงซ้ำเมื่อเจอ 429 rate limit จากฝั่งบริการ — ยิงซ้ำยิ่งแย่)

## [1.7.3] — 2026-08-16

### ปรับปรุง

- **ทุกข้อความแจ้งเตือน Telegram ระบุชื่อเครื่อง**: หัวข้อความทุกเหตุการณ์ (เริ่ม/หยุด/IP เปลี่ยน/สร้าง record/error/สรุปรอบ) มี `· <ชื่อเครื่อง>` กำกับ เช่น `🔴 DDNS หยุดทำงาน [16/08 11:10] · LAPTOP-X` — เหมาะใช้ bot กลางร่วมกันหลายเครื่อง จะรู้ทันทีว่ามาจากเครื่องไหน

## [1.7.2] — 2026-08-16

### แก้บั๊ก (Fixes)

- **ปุ่ม "โหลดใหม่" ของ Log ทำงานจริง**: v1.7.1 เติม cache-buster (`/log?t=...`) แต่ server เปรียบเทียบ `self.path` เต็ม (รวม query) → `/log?t=...` ไม่ match → ส่งหน้า HTML แทน log — แก้โดยแยก query ออกจาก path

## [1.7.1] — 2026-08-16

### แก้บั๊ก (Fixes)

- **ปุ่ม "โหลดใหม่" ของ Log**: เติม cache-buster (`/log?t=...`) กันเบราว์เซอร์คืน log เดิม + ตรวจ response — ถ้า session หมด (401) จะแสดงข้อความชัด "session หมดอายุ — กดรีเฟรชหน้าเว็บเพื่อเข้าสู่ระบบใหม่" แทนการเงียบ/โชว์ JSON

## [1.7.0] — 2026-08-16

### แก้บั๊ก (Fixes)

- **dry-run ไม่ส่ง Telegram/ไม่เขียนคิวแจ้งเตือน**: ก่อนหน้านี้ dry-run เจอ error (หา zone/IP/record ไม่ได้) จะส่งข้อความจริง + เขียน notify_queue.json — ตอนนี้ dry-run ใช้ notifier จำลอง (ไม่แตะอะไรเลย)
- **กันสแปม error ทำงานจริง**: error ข้อความเดิมซ้ำ (หา IP ไม่ได้ตอนเน็ตหลุด ฯลฯ) จะไม่ส่งซ้ำภายใน 10 นาที — ก่อนหน้านี้ instance ใหม่ทุกรอบ + timestamp ในข้อความทำให้กันไม่ทำงาน → สแปมรายนาที
- **ส่งคิว Telegram ไม่ค้างนาน**: เดิม 50 ข้อความ × 15 วิ = ค้างได้ 12.5 นาที — ตอนนี้จำกัดส่งรวม 60 วิต่อรอบ ที่เหลือส่งรอบถัดไป
- **ปุ่ม "เปิดโฟลเดอร์ข้อมูล" ใช้ได้ตอนรันใน service**: service (SYSTEM) เปิด explorer ไม่ได้ — ตอนนี้กดปุ่มแล้วคัดลอก path ให้อัตโนมัติ (Win+R → วาง → Enter) · standalone เปิดเหมือนเดิม
- **dry-run/หน้าเว็บ**: กันสแปม error + คิว race (ddns thread + webui thread อ่าน-เขียนพร้อมกัน) ใช้ lock
- **taskkill tunnel ตรวจก่อนว่า pid เป็น cloudflared จริง** — กัน kill ผิด process (pid reuse)
- **/log ต้อง login ก่อน** (ก่อนหน้านี้ใครใน LAN ที่เข้าพอร์ตได้อ่าน log ได้) + `/log-event` เปิดเสมอตามที่ตั้งใจ
- **save-config ค่าตัวเลขผิด (เช่น interval = "abc") ไม่ 500** — fallback ค่าเดิม
- **หน้าเว็บ escape ครบทุกจุด** (IP/action/สถานะ service/pid) — กันหน้าเพี้ยน/XSS
- **Content-Length ผิดรูปแบบไม่ 500 ไร้ response**

### ปรับปรุง

- **log ละเอียดขึ้น**: NAT ตรวจไม่ได้ / daily report / notify_round / tunnel notify / tunnel version / cleanup service — ยกระดับเป็น warning พร้อมรายละเอียด (จากเดิมเงียบ/debug) · error ฝั่งเว็บทุกจุด (รวมที่แสดง textContent) ลง log ครบ · exception ในรอบ DDNS → สรุปผลรอบรายงาน "มีปัญหา" (ไม่รายงาน "ตรงทุกตัว" หลอก)
- tunnel pid file เขียนแบบ atomic · cmd_setup เขียน config แบบ atomic · cmd_notify_test เก็บคิวผ่าน lock

## [1.6.6] — 2026-08-16

### แก้บั๊ก (Fixes)

- **หน้า login แสดงหน้าหลักล่าง ๆ ตามมาด้วย**: ตอนตั้ง password แล้วเปิดเว็บ — เดิมส่งหน้า HTML หลักทั้งหน้า + แทรกกล่อง login ด้านบน → script หลักรัน → 401 → toast error "โหลด config ไม่ได้" โผล่ใต้หน้าล็อกอิน — ตอนนี้**ไม่ authed = ส่งเฉพาะหน้า login** (ไม่มี script หลัก) — เข้าสู่ระบบเสร็จค่อยโหลดหน้าหลัก

## [1.6.5] — 2026-08-16

### ปรับปรุง

- **ทุก error ที่โชว์บนหน้าเว็บ (popup/toast แดง) เขียนลงไฟล์ log อัตโนมัติ**: แก้ที่ฟังก์ชัน toast() — ครอบทุกจุดในหน้า (ฟอร์ม/wizard/ปุ่ม/สถานะ) — ดูได้ในแถบ Log ล่าสุด (`Web UI (JS) toast: <ข้อความ>`)

## [1.6.4] — 2026-08-16

### ปรับปรุง

- **แสดงรายละเอียด "ตั้งค่าไม่ครบ" ในหน้าเว็บ**: แถบหัวแสดง error ของ config ที่ขาด (เช่น "ไม่พบ record ใด ๆ") แบบเห็นชัด — ไม่ต้องเดาว่าขาดอะไร
- **log error ฝั่งหน้าเว็บครอบคลุมขึ้น**: เพิ่ม logClientError ใน loadStatus / loadIp (นอกเหนือจาก loadConfig/saveConfig/global error) — error ทุกจุดที่หน้าเว็บ ลง log หมด (ดูในแถบ Log ล่าสุด)

## [1.6.3] — 2026-08-16

### แก้บั๊ก (Fixes)

- **บันทึก password ใหม่แล้ว error "โหลด config ไม่ได้"**: หลังเปลี่ยนรหัสผ่าน session เก่าใช้ไม่ได้ทันที แต่หน้าเว็บพยายามโหลด config ต่อ → error กระพริบหายเร็ว — ตอนนี้เปลี่ยนรหัสแล้วจะ**เข้าสู่ระบบใหม่ให้อัตโนมัติ** (POST /login ด้วยรหัสใหม่) แล้ว reload — ไม่ error แล้ว

### เพิ่ม (Features)

- **บันทึก error ฝั่งหน้าเว็บลงไฟล์ log**: error จาก JavaScript (ฟอร์ม/wizard/โหลดข้อมูล) ถูกส่งไป `/log-event` → เขียนลง log ไฟล์ (ระบุว่าเกิดที่หน้าไหน) — ดูได้ในหน้าเว็บ (Log ล่าสุด) เพื่อหาสาเหตุ โดยไม่ต้องเห็น toast ทัน

## [1.6.2] — 2026-08-16

### แก้บั๊ก (Fixes)

- **บันทึก config แล้วข้อมูลอื่นหาย**: `/save-config` ตอนนี้ merge field ที่ client ไม่ได้ส่งมาจาก config ปัจจุบันก่อนเขียน — กันบันทึกจากฟอร์ม/wizard แล้วค่าเหล่านี้หาย:
  - ฟอร์มตั้งค่าไม่ส่ง `tunnel.hosts` → hostname ที่ผูกกับ tunnel หายทั้งหมด (บั๊กเก่า)
  - wizard ครั้งแรกไม่ส่ง field ใหม่ (reject_cloudflare_ips / healthchecks_url / uptimekuma_url / webui_host / notify_round) → กลับเป็นค่าเริ่มต้น
  - ตอนนี้ทั้งฟอร์มและ wizard ส่ง field ครบ + server กันซ้ำชั้น

## [1.6.1] — 2026-08-16

### แก้บั๊ก (Fixes)

- **Restart service จากปุ่มในเว็บทำงานได้จริง**: ก่อนหน้านี้ restart ถูกเรียกใน thread ของ process ตัวเอง → `stop` สำเร็จแล้ว process ตายก่อนคำสั่ง `start` รัน → service ถูกหยุดค้าง ("เหมือนจะ start ไม่ได้") — ตอนนี้สั่งผ่าน `sc.exe` (process ภายนอก อยู่รอดแม้ service หยุด) — หน้าเว็บหลุด ~15-20 วิ แล้วกลับมาเอง

## [1.6.0] — 2026-08-16

### เพิ่ม (Features)

- **แจ้งเตือน Telegram ละเอียดขึ้น**:
  - ทุกข้อความมีเวลาเกิดกำกับ (`🔄 IP เปลี่ยน [16/08 09:12]`)
  - **รวมการอัปเดตเป็นข้อความเดียว**: IP เปลี่ยน A + AAAA พร้อมกันไม่สแปม 2 ข้อความ (รวม bullet รายการที่เปลี่ยน/สร้างทั้งหมด)
  - **แจ้ง Cloudflare Tunnel**: เริ่มทำงาน (พร้อมรายชื่อ hostname ที่ผูก) / หยุด / ดาวน์โหลด cloudflared — จากเดิมเงียบสนิท
  - **หยุดทำงานบอกสาเหตุ + สรุป**: หยุดตามคำสั่ง (service stop/ปิดเครื่อง) · รันต่อเนื่องนานเท่าไหร่ · ผ่านกี่รอบ
  - **กันสแปม rate limit (429)**: แจ้งครั้งเดียวต่อ 10 นาที
  - **สรุปผลทุกรอบ** (ไม่บังคับ): `notify_round = true` — ส่ง "ตรวจ X รายการ · เปลี่ยน Y · มีปัญหา Z" ทุกครั้งที่ตรวจ (ในฟอร์มเว็บ: checkbox "สรุปทุกรอบ")

## [1.5.1] — 2026-08-16

### ปรับปรุง

- **ข้อความแจ้งเตือน Telegram ตอนเริ่มทำงานละเอียดขึ้น**: ชื่อเครื่อง (hostname) · IP สาธารณะที่ตรวจได้ (IPv4/IPv6 + จำนวน) · รายการ DDNS ที่ตั้งไว้ (ชื่อ + ชนิด A/AAAA) · รายการ hostname ที่ผูกกับ Tunnel (พร้อมบริการ) — ถ้าตรวจ IP ไม่ได้ / ยังไม่มี record/tunnel จะบอกตามจริง

## [1.5.0] — 2026-08-16

### เพิ่ม (Features)

- **เข้าหน้าเว็บจากเครื่องอื่นในเน็ตเวิร์กได้**: เพิ่ม config `webui_host` (ค่าเริ่มต้น `127.0.0.1` = เฉพาะเครื่องนี้ เดิมเหมือนเดิม) — ตั้งเป็น `0.0.0.0` แล้วเปิดพอร์ต firewall 8123 → เข้าผ่าน `http://<IPเครื่อง>:8123` จากเครื่องอื่นในบ้านได้ (ในฟอร์มตั้งค่า + config.example.ini มีคำเตือน: ต้องตั้ง `webui_password` ก่อนเปิด 0.0.0.0)

### แก้บั๊ก (Fixes)

- **กันกด "ติดตั้ง service" ซ้ำจากเว็บที่รันใน service**: ก่อนหน้านี้ถ้าเปิดเว็บผ่าน service แล้วกดติดตั้ง โปรแกรมจะลบ service ที่รันอยู่ทิ้งแล้วหยุดกลางคัน → service หายไปจาก Windows (ไม่มี error ชัดเจน) — ตอนนี้ตอบข้อความชัดเจนให้ใช้ปุ่ม Restart แทน (เช็ค `_in_service()` แบบเดียวกับปุ่ม stop/uninstall)

## [1.4.1] — 2026-08-16

### แก้บั๊ก (Fixes)

- **กันกด "ติดตั้ง service" ซ้ำจากเว็บที่รันใน service**: ก่อนหน้านี้ถ้าเปิดเว็บผ่าน service แล้วกดติดตั้ง โปรแกรมจะลบ service ที่รันอยู่ทิ้งแล้วหยุดกลางคัน → service หายไปจาก Windows (ไม่มี error ชัดเจน) — ตอนนี้ตอบข้อความชัดเจนให้ใช้ปุ่ม Restart แทน (เช็ค `_in_service()` แบบเดียวกับปุ่ม stop/uninstall)

## [1.4.0] — 2026-08-16

### เพิ่ม (Features)

- **กันเขียน IP ของ Cloudflare เอง (anycast) ลง record**: ดาวน์โหลดช่วง IP ของ Cloudflare (`cloudflare.com/ips-v4` + `ips-v6`, แคช 24 ชม.) แล้วตรวจทุก IP ที่ได้จาก provider — ถ้าอยู่ในช่วงของ CF → ข้ามการอัปเดต + จด error ในเว็บ (เปิด/ปิดด้วย `reject_cloudflare_ips`, ค่าเริ่มต้นเปิด)
- **Heartbeat monitoring**: ส่งสัญญาณ "ยังทำงาน" ทุกรอบ DDNS ให้ Healthchecks.io (`healthchecks_url`) และ/หรือ Uptime Kuma (`uptimekuma_url`) — รอบมีปัญหา → สัญญาณ fail (`/fail` หรือ `?status=down`) · หยุดโปรแกรม → สัญญาณ exit — รู้ว่าเครื่อง/โปรแกรมตายจากนอกบ้าน
- **รองรับ wildcard domain**: ใช้ `*` หรือ `*.example.com` เป็นชื่อ record — ทุกซับโดเมนชี้มาบ้านนี้ (สร้าง record เฉพาะทับได้ที่ Cloudflare)

### ปรับปรุง

- Web UI ฟอร์มตั้งค่า: เพิ่ม checkbox "กัน IP ของ Cloudflare (anycast)" + ช่อง URL Heartbeat (Healthchecks.io / Uptime Kuma)
- `config.example.ini`: เอกสาร field ใหม่ + วิธีใช้ wildcard

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
