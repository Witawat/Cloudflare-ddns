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
- ผิดเกิน 5 ครั้งติดต่อกัน → ล็อกชั่วคราว 5 นาที (ขึ้นข้อความ "ล็อกชั่วคราว") — รอครบเวลาแล้วลองใหม่ (restart service = ปลดล็อกทันที)

### เปลี่ยนพอร์ตแล้วเข้าเว็บไม่ได้
- webui ฟังพอร์ตเดิมจนกว่า service จะ restart — restart service หลังเปลี่ยน

### เข้าเว็บจากเครื่องอื่นในบ้านไม่ได้ (http://IPเครื่อง:8123)
- ตั้ง `webui_host = 0.0.0.0` (ฟอร์มตั้งค่า → "หน้าเว็บเปิดที่ (host)") + ตั้ง `webui_password` ก่อน
- เปิดพอร์ต firewall (cmd admin): `netsh advfirewall firewall add rule name="CloudflareDDNS WebUI" dir=in action=allow protocol=TCP localport=8123`
- restart service หลังเปลี่ยน

### กด "เปิดโฟลเดอร์ข้อมูล" แล้วไม่มีหน้าต่างโผล่
- เว็บรันใน service (SYSTEM) เปิด explorer ให้ไม่ได้ — โปรแกรม**คัดลอก path ให้อัตโนมัติ** → กด Win+R → วาง → Enter (ตั้งแต่ v1.7.0)

### ปุ่ม "โหลดใหม่" ของ log ไม่โหลด
- session หมดอายุ → กดปุ่มแล้วขึ้น "session หมดอายุ — กดรีเฟรชหน้าเว็บ" — F5 แล้ว login ใหม่ (ตั้งแต่ v1.7.2 โหลดใหม่ทำงานได้จริง)
- error อื่นที่เด้งบนเว็บ: ดูแถบ Log ล่าสุด หาบรรทัด `Web UI (JS) ...` — โปรแกรม log error ฝั่งเว็บให้อัตโนมัติ (v1.6.5+)

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

> คู่มือตั้งค่า/ใช้งาน tunnel ละเอียด: **[docs/TUNNEL.md](TUNNEL.md)**

### token ตรวจไม่ผ่าน (cloudflared ตายทันที)
- ตรวจว่า token ถูกต้อง (eyJ... จาก Zero Trust → Networks → Tunnels)
- อินเทอร์เน็ต/ไฟร์วอลล์ต้องออกไป `region1.v2.argotunnel.com` ได้ (HTTPS 7844)
- ลอง "ดาวน์โหลด cloudflared" ใหม่ (ไฟล์อาจเสีย)

### error "tunnel token ผิดรูปแบบ"
- token **รูปแบบใหม่** ของ Cloudflare เป็นแบบ 1 ส่วน (payload ล้วน) — โปรแกรมรองรับตั้งแต่ v1.7.7 → **อัปเดต exe เป็นเวอร์ชันล่าสุด** ก่อน
- ถ้า exe ใหม่แล้ว: token คัดลอกไม่ครบ/มีช่องว่าง — วางใหม่จากหน้า Zero Trust

### ผูก hostname แล้วเข้าเว็บไม่ได้
1. บริการในเครื่อง (localhost:port) ต้องรันอยู่ — ทดสอบในเครื่องก่อน
2. tunnel ต้องรันอยู่ (การ์ด → สถานะ)
3. ตรวจ "ดู hostname ที่ผูกแล้ว" — hostname + ชนิด + บริการถูกต้องไหม
4. DNS อาจยัง propagate (รอ 1-2 นาที)

### Bad Request "You're speaking plain HTTP to an SSL-enabled server port"
- ผูกพอร์ต SSL (443/8443) ด้วยชนิด **HTTP** ผิด — ต้องเลือกชนิด **HTTPS** + `https://localhost:443`
- แก้ด้วยปุ่ม **"แก้ไข"** ใน "ดู hostname ที่ผูกแล้ว" → เปลี่ยนชนิด + บริการ → "ผูกกับ tunnel" (แทนที่)

### ผูก hostname ซ้ำ (แก้ไข) แล้ว error 1056 "Bad Configuration"
- เกิดกับ exe เก่ากว่า v1.7.11 (rule 404 ซ้ำ) — **อัปเดต exe + restart**

### error "ชื่อนี้มี record A อยู่แล้ว"
- ชื่อเดียวใช้ได้อย่างใดอย่างหนึ่ง (DDNS A/AAAA หรือ tunnel CNAME) — ใช้คนละชื่อ หรือลบ record เดิมก่อน

### error สิทธิ์ตอนผูก hostname (403)
- API token ต้องมีสิทธิ์ **Account > Cloudflare Tunnel > Edit** — ไป My Profile → API Tokens → Edit token → เพิ่ม: Account → Cloudflare Tunnel → Edit (เลือก account ของคุณ)

### tunnel ไม่เริ่มตอน boot
- ตรวจ `tunnel_enabled = true` + token ไม่ว่าง (ฟอร์มตั้งค่า)
- ดู log: "Cloudflare Tunnel: ..." บอกสาเหตุ

---

## Heartbeat (Healthchecks.io / Uptime Kuma)

### log "heartbeat ส่งไม่ได้: ... (HTTP 429)"
- 429 = **ฝั่ง Healthchecks.io จำกัด ping ชั่วคราว** (rate limit) — ไม่ใช่บั๊ก — รอสักครู่/ตรวจ dashboard
- ถ้าถี่ผิดปกติ (หลายครั้งต่อนาที): มีโปรแกรมรันซ้ำหลาย instance — ตรวจ `tasklist | findstr cloudflare` ควรมีแค่ 2 process (1 instance) — ปิด exe ที่เปิดค้างให้หมด
- log ละเอียด (บอกสาเหตุจริง) + กันส่งถี่ (30 วิ) ตั้งแต่ v1.7.4/1.7.5

### log "heartbeat ส่งไม่ได้: ... (URLError: timed out)"
- เน็ต/เส้นทางไป hc-ping.com ติดขัด หรือ firewall บล็อก — ตรวจ `ping hc-ping.com` / ลองเปิด URL ในเบราว์เซอร์

---

## อื่น ๆ

### รันบน Windows 7 / Linux / macOS ได้ไหม
- **Windows 7: ไม่รองรับ** — โปรแกรม build ด้วย Python 3.12 ซึ่งตัดการสนับสนุน Win7 ทางการ (ถ้าต้องการจริงต้อง build เองด้วย Python 3.8 + pywin32 เก่า — ไม่แนะนำ)
- **Windows 8.1: ใช้งานได้** (Python 3.12 รองรับทางการ) — แต่เน้นเทสต์บน 10/11
- **Linux / macOS: ยังไม่มี build** — โปรเจกต์ออกแบบมาเป็น Windows Service (pywin32/cloudflared Windows) — บางส่วนของโค้ด (เช่น tunnel, ปุ่มเปิดโฟลเดอร์) ผูก Windows ไว้
- **ARM Windows (เช่น Surface Pro X)**: ใช้ได้ผ่าน x64 emulation — อาจช้าหน่อย

### เปิดเว็บแล้วสี/หน้าเว็บเพี้ยน
- เบราว์เซอร์เก่าเกินไป — Web UI ใช้ CSS `oklch`/`color-mix`/`backdrop-filter` ต้องการ Chrome/Edge 111+ (2023+) หรือ Firefox รุ่นใหม่

### ไฟล์ config ผิดจนโปรแกรมอ่านไม่ได้
- backup อัตโนมัติมีอยู่ (`config.ini.bak`, `.bak1`...) — กู้จากไฟล์นั้นแล้วเซฟผ่านเว็บ

### อยากลบข้อมูลทั้งหมด (factory reset)
- หยุด service → ลบ `config.ini`, `state.json`, `notify_queue.json`, `logs\` (ข้าง exe) → เปิดเว็บ = wizard ตั้งค่าใหม่

### พอร์ต 8123 ถูกโปรแกรมอื่นใช้
- เปลี่ยน `webui_port` ใน config → restart service

---

*ยังแก้ไม่ได้? เปิด Issue ที่ https://github.com/Witawat/Cloudflare-ddns พร้อมแนบ: เวอร์ชัน exe (`... --help` ดู version), log ล่าสุด, และ config (ลบ token ออกก่อนส่ง!)*
