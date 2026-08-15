# แก้ปัญหาทั่วไป (Troubleshooting)

รวบรวมอาการ + วิธีแก้ — ถ้าแก้ไม่ได้ ให้ดู log (`logs\cloudflare-ddns.log` หรือปุ่ม "Log ล่าสุด" ในเว็บ) แล้วเปิด Issue ที่ [GitHub](https://github.com/Witawat/Cloudflare-ddns)

---

## ติดตั้ง / Service

### ติดตั้ง service ไม่ได้ (permission denied)
- ต้องรันด้วยสิทธิ์ Administrator — double-click `install.bat` จะขอสิทธิ์ให้อัตโนมัติ หรือเปิด cmd เป็น admin แล้วรัน `python -m cloudflare_ddns.main install`

### service ติดตั้งแล้วแต่ start ไม่ขึ้น / หยุดเอง
- ตรวจ: `python -m cloudflare_ddns.main status` + log ล่าสุด
- สาเหตุที่พบบ่อย: config ไม่ครบ (เตือน "ตั้งค่าไม่ครบ") หรือ crash จากข้อผิดพลาดภายใน — ดู log ถ้ามี "เกิดข้อผิดพลาดไม่คาดคิด" แจ้ง log นั้นมา
- ลอง: restart service (`... restart`) — ถ้ายังอยู่ ให้ reinstall (`uninstall.bat` → `install.bat`)

### service หยุดช้า/ค้างตอน stop
- ระบบแก้แล้วให้หยุดภายใน ~5 วิ — ถ้ายังค้าง ตรวจว่า cloudflared/tunnel ไม่ค้าง (`... status` → tunnel)

### error 1053 (The service did not respond...)
- เกิดตอนติดตั้ง exe เก่าบน pywin32 ใหม่ — อัปเดตเป็น exe ล่าสุดแล้ว reinstall (`uninstall.bat` → `install.bat`)

---

## Cloudflare API / DDNS

### token error ระหว่าง setup
- ตรวจว่าสร้าง token ด้วยสิทธิ์ **Zone > DNS > Edit** จริง (หน้า My Profile → API Tokens → Create Token → template "Edit zone DNS")
- token รุ่นใหม่ขึ้นต้น `cfut_` — คัดลอกครั้งเดียว หน้าแสดงครั้งเดียว
- error "Could not route to /user/tokens/verify" = path ฝั่งเราผิด (อัปเดต exe) หรือ token ไม่ใช่ API token

### หา IP สาธารณะไม่ได้ (log: "หา IP สาธารณะไม่ได้")
- เช็คอินเทอร์เน็ต — เครื่องต้องออก HTTPS ไปยัง `api.ipify.org` / `ifconfig.me` / `icanhazip.com` ได้
- ไฟร์วอลล์/โปรแกรมปิดกั้น? ทดสอบ: `python -c "from cloudflare_ddns.ip_detect import get_public_ip; print(get_public_ip(4))"`
- IPv6 "ไม่มี" = ISP ไม่ให้ IPv6 — ปกติ ตั้ง `use_ipv6 = false` ได้

### DDNS อัปเดตแล้วแต่เข้าเว็บไม่ได้
- ตรวจ IP จริงตอนนี้ (การ์ด "IP สาธารณะปัจจุบัน") — ถ้าเป็น CGNAT (100.64.x.x) DDNS ใช้ไม่ได้ ต้องใช้ Tunnel
- ตรวจ port forward ที่เราเตอร์ (ถ้าบริการในเครื่อง) + ทดสอบด้วย "สแกนพอร์ต" ในเว็บ
- DNS cache: `ipconfig /flushdns` + รอ TTL (60 วิ = เร็วสุด)

### error rate limit (HTTP 429)
- โปรแกรมข้ามรอบให้อัตโนมัติ + แจ้งเตือน — ถ้าเจอบ่อย: ลดจำนวน record หรือเพิ่ม interval (โควตา ~1200 req/hr)

### record ถูกสร้าง/อัปเดตผิดชื่อ
- โปรแกรมเติม `.zone` ให้อัตโนมัติ (ใส่ `home` → `home.โดเมน.com`, `@` = root) — ถ้าใส่เต็มแล้วไม่ซ้ำกับ zone จะใช้ตรง
- ตรวจชื่อที่ใช้จริงในตารางสถานะ IP

---

## Web UI

### เปิดเว็บแล้วเข้าไม่ได้ (เชื่อมต่อไม่ได้)
- service ต้องรันอยู่: `... status` → ต้อง RUNNING
- พอร์ตเปลี่ยน? ตรวจ `webui_port` ใน config (เปลี่ยนแล้วต้อง restart service)
- ถ้ารัน `webui` แบบ standalone: ปิด service ก่อน (พอร์ตชนกัน)

### หน้าเว็บขึ้น wizard ซ้ำ ๆ
- wizard ขึ้นเองเมื่อ config ไม่ครบ (ไม่มี token/record) — ตั้งค่าให้ครบ หรือกด "ข้ามชั่วคราว"

### ตั้งรหัสผ่านแล้ว login ไม่ได้
- รหัสคือค่าที่ตั้งในฟอร์ม (`webui_password`) — ลืม = แก้ config.ini (โหมดไฟล์/เปิดไฟล์) ลบ `webui_password =` ออก แล้ว restart

### เปลี่ยนพอร์ตแล้วเข้าเว็บไม่ได้
- webui ฟังพอร์ตเดิมจนกว่า service จะ restart — restart service หลังเปลี่ยน

### หน้าจอแสดงผลเละ/ไม่สวย
- รีเฟรชแรง ๆ (Ctrl+F5) — ถ้ายังเป็น ตรวจว่าใช้ exe ล่าสุด (build ใหม่)

---

## Telegram

### error 409 Conflict (getUpdates)
- bot มี webhook ค้าง — โปรแกรม**ลบให้อัตโนมัติ**แล้วลองใหม่ (กด "ค้นหา chat id" อีกครั้ง)
- ถ้ายัง: bot กำลังรันกับโปรแกรมอื่น (bot framework) — ปิดตัวนั้นก่อน

### "chat not found"
- เปิดแชทกับ bot แล้วกด Start ก่อน (bot คุยกับคุณคนแรกไม่ได้)

### HTTP 401 Unauthorized
- Bot token ผิด/ขาด — คัดลอกใหม่จาก @BotFather (คำสั่ง `/token`)

### ข้อความค้างในคิวไม่ส่งสักที
- ตรวจว่า bot token + chat id ถูกต้อง (การ์ด Telegram → "ดูคิว" เห็นข้อความที่ค้าง)
- กด "ลองส่งใหม่" — ถ้ายัง fail: แก้ token → "ล้างคิว" ทิ้งข้อความเก่า

### อยากปิดการแจ้งเตือน
- ฟอร์มตั้งค่า → เอา tick ออกจากเหตุการณ์ที่ต้องการ หรือลบ `telegram_bot_token` ทิ้ง

---

## Cloudflare Tunnel

### token ตรวจไม่ผ่าน (cloudflared ตายทันที)
- ตรวจว่า token ถูกต้อง (eyJ... จาก Zero Trust → Networks → Tunnels)
- อินเทอร์เน็ต/ไฟร์วอลล์ต้องออกไป `region1.v2.argotunnel.com` ได้ (HTTPS 7844)
- ลอง "ดาวน์โหลด cloudflared" ใหม่ (ไฟล์อาจเสีย)

### ผูก hostname แล้วเข้าเว็บไม่ได้
1. บริการในเครื่อง (localhost:port) ต้องรันอยู่ — ทดสอบในเครื่องก่อน
2. tunnel ต้องรันอยู่ (การ์ด → สถานะ)
3. ตรวจ "ดู hostname ที่ผูกแล้ว" — hostname + บริการถูกต้องไหม
4. DNS อาจยัง propagate (รอ 1-2 นาที)

### error "ชื่อนี้มี record A อยู่แล้ว"
- ชื่อเดียวใช้ได้อย่างใดอย่างหนึ่ง (DDNS A/AAAA หรือ tunnel CNAME) — ใช้คนละชื่อ หรือลบ record เดิมก่อน

### error สิทธิ์ตอนผูก hostname
- API token ต้องมีสิทธิ์ **Account > Cloudflare Tunnel > Edit** — ไป My Profile → API Tokens → Edit token → เพิ่ม: Account → Cloudflare Tunnel → Edit (เลือก account ของคุณ)

### tunnel ไม่เริ่มตอน boot
- ตรวจ `tunnel_enabled = true` + token ไม่ว่าง (ฟอร์มตั้งค่า)
- ดู log: "Cloudflare Tunnel: ..." บอกสาเหตุ

---

## อื่น ๆ

### ไฟล์ config ผิดจนโปรแกรมอ่านไม่ได้
- backup อัตโนมัติมีอยู่ (`config.ini.bak`, `.bak1`...) — กู้จากไฟล์นั้นแล้วเซฟผ่านเว็บ

### อยากลบข้อมูลทั้งหมด (factory reset)
- หยุด service → ลบ `config.ini`, `state.json`, `notify_queue.json`, `logs\` (ข้าง exe) → เปิดเว็บ = wizard ตั้งค่าใหม่

### พอร์ต 8123 ถูกโปรแกรมอื่นใช้
- เปลี่ยน `webui_port` ใน config → restart service

---

*ยังแก้ไม่ได้? เปิด Issue ที่ https://github.com/Witawat/Cloudflare-ddns พร้อมแนบ: เวอร์ชัน exe (`... --help` ดู version), log ล่าสุด, และ config (ลบ token ออกก่อนส่ง!)*
