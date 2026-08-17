# คู่มือการใช้งาน (ฉบับละเอียด)

คู่มือนี้ครอบคลุมทุกฟีเจอร์ของ Cloudflare DDNS Updater — เริ่มจากติดตั้ง ไปจนถึงใช้งานทุกส่วนของ Web UI

## สารบัญ

1. [ภาพรวม & องค์ประกอบ](#1-ภาพรวม--องค์ประกอบ)
2. [ติดตั้ง](#2-ติดตั้ง)
3. [ตั้งค่าครั้งแรก (wizard)](#3-ตั้งค่าครั้งแรก-wizard)
4. [Web UI ทีละส่วน](#4-web-ui-ทีละส่วน)
5. [แจ้งเตือน Telegram](#5-แจ้งเตือน-telegram)
6. [Cloudflare Tunnel](#6-cloudflare-tunnel)
7. [config.ini ฉบับเต็ม](#7-configini-ฉบับเต็ม)
8. [การทำงานภายใน](#8-การทำงานภายใน)
9. [อัปเดต/ย้ายเครื่อง](#9-อัปเดตย้ายเครื่อง)
10. [ความปลอดภัย](#10-ความปลอดภัย)

---

## 1. ภาพรวม & องค์ประกอบ

> **ข้อกำหนดระบบ:** โปรเจกต์นี้เป็น Windows เท่านั้น (Windows Service + pywin32) — รองรับเต็มบน **Windows 10/11 x64** (8.1 ใช้งานได้, 7 ไม่รองรับ) — Web UI ต้องการเบราว์เซอร์ Chrome/Edge 111+ ขึ้นไป (สี CSS สมัยใหม่) — ไม่มี build สำหรับ Linux/macOS

```
โปรเจกต์/
├── cloudflare_ddns/          # โค้ดหลัก
│   ├── main.py               # คำสั่งทั้งหมด (setup/run/status/webui/...)
│   ├── config.py             # อ่าน/เขียน/ตรวจ config.ini
│   ├── ddns.py               # แกน DDNS loop + daily report
│   ├── ip_detect.py          # หา IP สาธารณะ + ตรวจ NAT (STUN)
│   ├── cloudflare_api.py     # Cloudflare API v4 (urllib ล้วน)
│   ├── notifier.py           # Telegram + คิว retry
│   ├── tunnel.py             # cloudflared (ดาวน์โหลด/เริ่ม/หยุด)
│   ├── service.py            # Windows Service wrapper
│   └── webui.py              # Web UI (หน้าเดียวครบ)
├── dist\cloudflare-ddns.exe  # exe ไฟล์เดียว (build จาก build.bat)
├── config.ini                # ตั้งค่า (อยู่ข้าง exe ในโหมด exe)
├── state.json                # IP ล่าสุด/ประวัติ/zone cache
├── notify_queue.json         # คิวข้อความ Telegram ที่ค้าง
├── tunnel.pid                # pid ของ cloudflared
├── logs\cloudflare-ddns.log  # log รายวัน (เก็บ 14 วัน)
└── cloudflared.exe           # ดาวน์โหลดอัตโนมัติเมื่อใช้ Tunnel
```

> ข้อมูล runtime ทั้งหมดอยู่**ข้าง exe/โปรเจกต์** — ย้ายโฟลเดอร์ = ย้ายทั้งชุด (ถ้าเคยใช้เวอร์ชันเก่า ระบบย้ายข้อมูลจาก ProgramData ให้อัตโนมัติครั้งเดียว)

## 2. ติดตั้ง

### แบบ Python (source)

```cmd
pip install -r requirements.txt     REM ติดตั้ง pywin32
python -m cloudflare_ddns.main setup
python -m cloudflare_ddns.main dry-run
install.bat                          REM ติดตั้ง service (double-click เอาเลย ขอ admin ให้เอง)
```

### แบบ EXE (ไม่ต้องติดตั้ง Python)

```cmd
build.bat                            REM build ครั้งเดียว (~2-3 นาที)
dist\cloudflare-ddns.exe             REM รันเปล่า = เปิด Web UI + เบราว์เซอร์ให้อัตโนมัติ
install.bat                          REM ติดตั้ง service
```

- เอา exe ไปวางที่ไหนก็ได้ เช่น `D:\CloudflareDDNS\` — ข้อมูลทั้งหมดอยู่ข้าง exe
- ตรวจสถานะ: `dist\cloudflare-ddns.exe status`
- ถอนการติดตั้ง: `uninstall.bat` หรือ `... remove`

## 3. ตั้งค่าครั้งแรก (wizard)

มี 2 แบบ:

### 3.1 wizard แบบ console (`setup`)

```cmd
python -m cloudflare_ddns.main setup
```

- เปิดเบราว์เซอร์ไปหน้าสร้าง API token ให้อัตโนมัติ
- วาง token → ตรวจให้อัตโนมัติ → เลือก zone → เพิ่ม record (ใส่สั้น ๆ ได้ เช่น `home`) → ถาม Telegram (ตอบ y → วาง bot token → หา chat id ให้ + ส่งข้อความทดสอบ)

### 3.2 wizard ในเว็บ (5 ขั้นตอน)

เปิดเว็บครั้งแรก (config ยังไม่ครบ) → wizard ขึ้นอัตโนมัติ:

1. **ยินดีต้อนรับ** — อธิบายสั้น ๆ
2. **API token** — วาง + ปุ่ม "วิธีหา token" (ขั้นตอนในหน้า) + ตรวจสอบก่อนไปต่อ
3. **Zone + record** — เลือกโดเมน (dropdown จาก token) + ใส่ชื่อ record (สั้นได้) + ปุ่ม "โหลดชื่อ record ที่มีอยู่"
4. **Telegram** — ข้ามได้; วาง bot token → "ค้นหา chat id ให้อัตโนมัติ" → "ส่งข้อความทดสอบ"
5. **สรุป** — ตรวจรายการ → "บันทึกและเริ่มใช้งาน"

> ปุ่ม "ข้ามชั่วคราว" ปิด wizard ได้ — ตั้งทีหลังในฟอร์มตั้งค่า

## 4. Web UI ทีละส่วน

เปิด `http://127.0.0.1:8123` (เปลี่ยนพอร์ตได้ใน config/ฟอร์ม) — service เปิดให้เองตลอดเวลา

### 4.1 แถบหัวหน้า
- ชื่อโปรแกรม + เวลารอบล่าสุด + **status pill** (พร้อมใช้งาน/ตั้งค่าไม่ครบ/มีปัญหา) + ปุ่มรีเฟรช

### 4.2 สถานะ IP
- **IP สาธารณะปัจจุบัน** (ตรวจสด + ปุ่มตรวจใหม่) + ผลตรวจ NAT: ✓ ปกติ หรือ ⚠ CGNAT/private (พร้อมคำแนะนำ)
- ปุ่ม **"ตรวจ DDNS ตอนนี้"**: รันรอบ DDNS ทันที (ตรวจ IP + เทียบ record + อัปเดต) ไม่ต้องรอรอบถัดไป — สถานะอัปเดตให้อัตโนมัติ (กันกดซ้ำขณะกำลังตรวจ)
- สถิติ **Cloudflare API** (นับตั้งแต่เริ่ม): เรียกทั้งหมด / error / โดน rate limit (429) — ช่วยดูว่าใช้โควตาใกล้ถึงขีดจำกัด (~1200 req/hr) หรือไม่
- รายการ record: ชื่อ + IP + เวลาอัปเดตล่าสุด (ชนิด A/AAAA แสดงแยก) — **กดชื่อหรือ IP เพื่อคัดลอก**

### 4.3 แจ้งเตือน Telegram
- สถานะ (พร้อมใช้งาน/ยังไม่ตั้ง) + จำนวนคิวค้าง
- ปุ่ม: ส่งข้อความทดสอบ / ดูคิว (แสดงข้อความทั้งหมด) / ลองส่งใหม่ / ล้างคิว

### 4.4 Windows Service
- สถานะ: ติดตั้งไหม / กำลังทำงานไหม + **context ของหน้าเว็บ** (รันใน service / standalone · admin หรือไม่ — ปุ่มที่ทำไม่ได้จะปิด)
- ปุ่ม: **เริ่ม service** / **Restart service** (เว็บหลุดชั่วครู่แล้วกลับมาเอง) / **หยุด service** / **ติดตั้ง service** (ยกระดับจากรัน standalone → service เริ่มเองตอน boot) / **ถอนการติดตั้ง** (confirm 2 ชั้น)
- ข้อควรรู้: ทุกปุ่มต้องเปิด webui ด้วยสิทธิ์ admin — ถ้าหน้าเว็บรันใน service อยู่แล้ว เริ่ม/ติดตั้ง/ถอน/หยุดทำไม่ได้จากเว็บ (กันตัดการเชื่อมต่อตัวเอง) — ใช้ install.bat / uninstall.bat แทน (Restart ใช้ได้เสมอ)

### 4.5 Cloudflare Tunnel
- สถานะ: เปิดใช้งานไหม / cloudflared ติดตั้งไหม / รันอยู่ (pid)
- ปุ่ม: **ตั้งค่า Tunnel (wizard)** / ดู hostname ที่ผูกแล้ว (ตาราง + ลบ) / เริ่ม / หยุด / ดาวน์โหลด cloudflared / **เช็คอัปเดต cloudflared** (เทียบ exe ที่ติดตั้งกับเวอร์ชันล่าสุดจาก GitHub — cache 6 ชม.)
- **ข้อควรรู้** (คลิกขยาย)

### 4.5 สแกนพอร์ต
- เลือก host (จาก record ใน config) → แก้รายการพอร์ตได้ → สแกน (TCP ขนาน) → ตาราง: พอร์ต/บริการ/สถานะ (เปิด/ปิด/ไม่มีตอบ) + สรุป
- ใช้ตรวจว่า port forward ทำงานหรือไม่

### 4.6 ประวัติการอัปเดต
- 50 รายการล่าสุด: เวลา / record / การกระทำ (อัปเดต IP, สร้าง record) / IP — เลื่อนดูได้บนจอเล็ก

### 4.7 Log ล่าสุด
- 200 บรรทัดสุดท้ายของ `logs\cloudflare-ddns.log` + ปุ่มโหลดใหม่ — ดูจากมือถือได้

### 4.8 ตั้งค่า
- สลับโหมด: **แบบฟอร์ม** | **แก้ไขไฟล์โดยตรง**
- ฟอร์ม: API token / interval / IPv4-6 / **ตรวจฉันทามติ IP (≥2 provider เห็นตรงกัน)** / **กัน IP ของ Cloudflare (anycast)** / **Heartbeat (Healthchecks.io + Uptime Kuma URL + ปุ่มทดสอบส่งทันที)** / รหัสผ่านหน้าเว็บ + พอร์ต + **host ที่เปิด (webui_host)** / ที่เก็บ log / Telegram (token, chat id, 6 เหตุการณ์รวม "สรุปทุกรอบ", สรุปรายวัน+เวลา, **กู้รหัสผ่านหน้าเว็บผ่าน Telegram**) / Tunnel (เปิดอัตโนมัติ, token แบบช่องยาวเห็นเต็ม, ที่อยู่ cloudflared, **เช็คอัปเดต**) / DNS records (เพิ่ม-ลบ-แก้ทีละแถว: ชื่อ, zone, proxy, TTL, 4/6)
- **ดาวน์โหลด config** — เก็บ config.ini เป็นไฟล์สำรอง (รหัสผ่านในไฟล์เป็น hash อยู่แล้ว) · **นำเข้า config** — เลือกไฟล์ config.ini (ตรวจสอบก่อนเขียน) แล้วหน้าเว็บ reload
- โหมดไฟล์: แก้ config.ini ทั้งไฟล์ (ตรวจ syntax/ค่าก่อนบันทึก)
- **ช่องรหัสผ่านหน้าเว็บ**: ว่างเสมอ (รหัสจริงเก็บเป็น hash — ดูค่าใน config เป็น hash ไม่ได้เป็นรหัส) — เว้นว่าง + บันทึก = **คงรหัสเดิม** · พิมพ์ใหม่ = เปลี่ยน · กด "ลบรหัส" = ลบ (เข้าเว็บได้โดยไม่ต้อง login)
- **บันทึกแล้ว** → backup อัตโนมัติ (`config.ini.bak` หมุน 5) + มีผลในรอบถัดไป (ไม่ต้อง restart) — เปลี่ยนพอร์ต/รหัสผ่าน → แจ้งเตือน + เข้าสู่ระบบใหม่ให้อัตโนมัติ

### 4.9 ส่วนท้าย
- footer: เวอร์ชัน + License + ลิงก์ GitHub

## 5. แจ้งเตือน Telegram

### เหตุการณ์ (เปิด-ปิดได้ในฟอร์ม)
| เหตุการณ์ | ตัวอย่างข้อความ |
|---|---|
| เริ่ม/หยุดทำงาน | 🟢 DDNS เริ่มทำงาน [16/08 09:12] · LAPTOP-X — บอกเครื่อง/IP/รายการ DDNS+tunnel / 🔴 หยุด — สาเหตุ + รันนานเท่าไหร่ |
| IP เปลี่ยน | 🔄 IP เปลี่ยน [เวลา] · เครื่อง — รวมหลายรายการเป็นข้อความเดียว |
| สร้าง record | 🆕 สร้าง record ใหม่ [เวลา] · เครื่อง |
| error | ⚠️ มีปัญหา [เวลา] · เครื่อง — ข้อความย่อ ไม่มี JSON ยาว |
| สรุปรายวัน | 📊 สรุปประจำวัน (ทุก record + จำนวนอัปเดตวันนี้) ตามเวลาที่ตั้ง |
| สรุปรอบ (ไม่บังคับ) | ✅ ตรวจรอบเสร็จ [เวลา] · เครื่อง — "ตรวจ X รายการ · เปลี่ยน Y · มีปัญหา Z" (`notify_round = true`) |

> **ทุกข้อความระบุชื่อเครื่อง** (`· LAPTOP-X`) — ใช้ bot กลางร่วมหลายเครื่องรู้ทันทีว่ามาจากไหน (v1.7.3+)

### คิว (ส่งไม่สำเร็จ)
- ส่งไม่ได้ (เน็ตหลุด/token ผิด) → เก็บ `notify_queue.json` → พยายามส่งใหม่ทุก 60 วิ (จำกัดส่ง 60 วิ/รอบ กันค้าง)
- **error ซ้ำข้อความเดิมไม่ส่งซ้ำภายใน 10 นาที** (กันสแปม — รวมถึงตอนหา IP ไม่ได้ซ้ำ ๆ)
- จัดการในเว็บ: ดูคิว / ลองส่งใหม่ / ล้างคิว

### ตั้งค่า
- wizard หรือฟอร์ม: วาง bot token (จาก @BotFather) → chat_id หาให้อัตโนมัติ (เปิดแชทกับ bot + กด Start ก่อน)
- ทดสอบ: `notify-test` หรือปุ่มในเว็บ

### คำสั่งผ่าน Telegram (เปิดในฟอร์ม: "ควบคุม/กู้รหัสผ่านผ่าน Telegram" — เฉพาะ chat_id ที่ตั้งไว้)

| คำสั่ง | ความหมาย |
|---|---|
| `/help` | รายการคำสั่ง |
| `/status` | สถานะ DDNS (IP ต่อ record / รอบล่าสุด / error / เวอร์ชัน / tunnel / สถิติ API) |
| `/list` | รายชื่อ DDNS records + tunnel hostnames ที่ตั้งค่าไว้ |
| `/ip` | IP สาธารณะปัจจุบัน (IPv4 + IPv6) |
| `/run` | รันรอบ DDNS ทันที (ผลสรุปตามมา — **ต้องยืนยัน `yes`**) |
| `/update` | เช็คเวอร์ชันใหม่ |
| `/tunnel` / `/tunnel start` / `/tunnel stop` | สถานะ / เริ่ม / หยุด tunnel (**stop ต้องยืนยัน `yes`**) |
| `/log` | log 30 บรรทัดสุดท้าย |
| `/notify [all\|start\|stop\|ip\|error\|created\|round\|daily] [on\|off]` | ดู/เปิด/ปิดการแจ้งเตือน — ไม่ระบุ on/off = สลับค่าปัจจุบัน |
| `/restart` / `/start` / `/stop` | ควบคุม Windows Service (รันใน service เอง: `/stop` ใช้ไม่ได้ — **restart ต้องยืนยัน `yes`**) |
| `reset password` → `yes` | กู้รหัสผ่านหน้าเว็บ (รหัสใหม่ 12 ตัวส่งกลับ — กัน 1 ครั้ง/10 นาที) |

> **คำสั่งอันตรายต้องยืนยัน 2 ขั้น**: `/run`, `/restart`, `/tunnel stop` — ระบบถาม "พิมพ์ `yes` เพื่อยืนยัน (ภายใน 2 นาที)" ก่อนรันจริง (พิมพ์ `no` เพื่อยกเลิก) กันสั่งพลาด/กดผิด

> เงื่อนไข: ตั้ง bot token + chat_id แล้ว · เปิด "ควบคุม/กู้รหัสผ่านผ่าน Telegram" · โปรแกรมอ่านข้อความใหม่ทุก ~1 นาที (ตามรอบ DDNS)

### ใช้ bot ตัวเดียวหลายเครื่อง (v1.8.1+)

**เมื่อไหร่ต้องใช้:** มีโปรแกรม DDNS หลายเครื่อง (server/VM/VPS) ใช้ bot Telegram ตัวเดียวกัน — สั่งงานทีละเครื่องผ่าน `@ชื่อ` และแยก notification ตามเครื่อง

**วิธีตั้งชื่อเครื่อง:**
- **Web UI**: ฟอร์มตั้งค่า > แจ้งเตือน Telegram > ช่อง "ชื่อเครื่องรับคำสั่ง"
- **config.ini**: `telegram_command_name = ชื่อเครื่อง` (เว้นว่าง = ชื่อเครื่องระบบ)
- ตั้งชื่อไม่ซ้ำกัน เช่น เครื่องA, เครื่องB, webserver, db01

**ผลลัพธ์:**
- สั่ง `/status @เครื่องA` → เฉพาะเครื่อง A ตอบ (คำตอบขึ้นต้น `[เครื่องA]`)
- สั่ง `/status` (ไม่ระบุ @) → ทุกเครื่องตอบ (broadcast — เหมือนเดิม)
- คำสั่งทุกประเภทรวม `reset password` รองรับ `@ชื่อ` เช่น `reset password @A` → `yes`
- การแจ้งเตือนปกติต่อท้ายชื่อเครื่องที่ตั้ง: `🔄 IP เปลี่ยน [17/08 10:00] · เครื่องA`
- คำสั่งของเครื่องอื่นที่ค้าง ไม่ confirm offset (รอคิวให้เครื่องเป้า) — ถ้าเครื่องเป้าออฟไลน์เกิน 5 นาที จะทิ้งไป ไม่บล็อกคิวทั้ง bot

## 6. Cloudflare Tunnel

> คู่มือละเอียด (สร้าง token / เลือกชนิด protocol / แก้ไข-ลบ / แก้ปัญหา): **[docs/TUNNEL.md](TUNNEL.md)**

### เริ่มต้น (wizard ในเว็บ 4 ขั้น)
1. **คำนำ** — Tunnel คืออะไร เหมาะกับใคร
2. **วาง token** — "เปิด Zero Trust" + "วิธีหา token" (ขั้นตอนในหน้า) → "ตรวจสอบ token" (โปรแกรมดาวน์โหลด cloudflared + ทดสอบเชื่อมต่อจริง)
3. **ผูก hostname** — ชื่อ (เช่น `app`) + โดเมน (dropdown) + **ชนิด** (HTTP/HTTPS/TCP/UDP) + บริการ (เช่น `http://localhost:8080` หรือ `https://localhost:443`) → "ผูกกับ tunnel" → ตั้ง DNS + tunnel config ให้อัตโนมัติ; หรือ "เลือกจาก record ที่มีอยู่"; ชื่อใหม่ที่ไม่เคยมีก็ได้ — โปรแกรมสร้าง DNS ให้อัตโนมัติ
4. **สรุป** — บันทึก (เปิดอัตโนมัติ) + เริ่ม tunnel

### จัดการภายหลัง
- การ์ด tunnel: เริ่ม/หยุด/ดาวน์โหลด cloudflared + ดู hostname ที่ผูกแล้ว (ตาราง + **ปุ่มแก้ไข** = เปลี่ยนบริการ/ชนิดแล้วผูกซ้ำแทนที่ของเดิม · ปุ่ม × = ลบ ingress + CNAME)
- ปุ่ม **"+ เพิ่ม hostname"** — ผูกด่วนโดยไม่ต้องเปิด wizard
- ปุ่ม **"ซิงค์จาก Cloudflare"** — ดึง hostname ทั้งหมดมาบันทึกลง config
- ฟอร์มตั้งค่า: `tunnel_enabled` / token (ช่องยาว เห็นข้อความเต็ม) / path
- ตอน boot: service เริ่ม tunnel อัตโนมัติถ้าเปิดไว้

### ข้อควรรู้
- ชื่อเดียวใช้ได้อย่างใดอย่างหนึ่ง (A/AAAA DDNS หรือ CNAME tunnel) — โปรแกรมตรวจชื่อชนให้
- API token ต้องมีสิทธิ์ **Account > Cloudflare Tunnel > Edit** ถึงผูก hostname ได้ (เว็บบอกวิธีเพิ่มให้เมื่อ error 403)
- **ชนิดต้องตรงกับบริการ**: พอร์ต SSL (443/8443) = HTTPS + `https://localhost:443` — ผูกเป็น http จะเจอ "Bad Request" (มีคำแนะนำในหน้าเว็บด้วย)
- บริการที่ผูกต้องรันอยู่ (localhost:port) ถึงเข้าเว็บได้
- แจ้งเตือน Telegram: tunnel เริ่ม (พร้อมรายชื่อ hostname)/หยุด/ดาวน์โหลด cloudflared — ส่งอัตโนมัติ

## 7. config.ini ฉบับเต็ม

ดู `config.example.ini` — คีย์หลัก:

```
[cloudflare]
api_token            จำเป็น - สิทธิ์ Zone > DNS > Edit (+ Account > Tunnel > Edit ถ้าใช้ tunnel)
interval_seconds     60 (ขั้นต่ำ 15)
use_ipv4/use_ipv6    เปิด-ปิดการอัปเดตแต่ละชนิด
ip_consensus          ต้องมี provider ตรวจ IP ≥ 2 รายเห็น IP เดียวกัน ถึงจะอัปเดต (false = ปิด)
reject_cloudflare_ips   กัน IP ของ Cloudflare (anycast) ถูกเขียนลง record (ค่าเริ่มต้น true)
healthchecks_url     Heartbeat: ping URL ของ Healthchecks.io (ว่าง = ปิด)
uptimekuma_url       Heartbeat: push URL ของ Uptime Kuma (ว่าง = ปิด)
webui_port           8123
webui_host           127.0.0.1 (0.0.0.0 = เข้าจากเครื่องอื่นใน LAN ได้ — ต้องตั้งรหัสผ่าน + เปิด firewall)
webui_password       ว่าง = ไม่ต้อง login (เก็บเป็น hash อัตโนมัติ — ลืม = รัน `reset-password`)
log_dir              ว่าง = logs\ ข้าง exe
telegram_bot_token   ว่าง = ไม่แจ้ง
telegram_chat_id
notify_start/stop/ip_change/error/created   true/false
notify_round         ส่งสรุปผลทุกรอบ DDNS ทาง Telegram (false = ปิด)
daily_report / daily_report_time            สรุปรายวัน (HH:MM)
telegram_allow_reset กู้รหัสผ่านหน้าเว็บผ่าน Telegram (false = ปิด — เปิดก่อนใช้ ดู "ลืมรหัส" ใน TROUBLESHOOTING)
tunnel_enabled / tunnel_token / cloudflared_path / tunnel_hosts (JSON — "ซิงค์จาก Cloudflare" เขียนให้)

[record:ชื่อ]
zone = โดเมน (เว้น = เดาให้)
proxied = true/false (orange cloud)
ttl = 60-7200
ipv4 / ipv6 = true/false
```

- ชื่อ record ใช้ wildcard ได้: `[record:*.example.com]` (หรือ `[record:*]` + zone) — ทุกซับโดเมนชี้มาบ้านนี้
- **Heartbeat**: ใส่ `healthchecks_url` (สมัครฟรีที่ healthchecks.io → สร้าง Check → คัดลอก Ping URL) หรือ `uptimekuma_url` (self-host: monitor ชนิด Push) — โปรแกรม ping ทุกรอบ DDNS; รอบมีปัญหา = สัญญาณ fail; หยุดโปรแกรม = สัญญาณ exit — ถ้าไม่มาเกินกำหนด บริการนั้นจะแจ้งเตือนให้เอง (อีเมล/Telegram/อื่น ๆ)

แก้ด้วยมือแล้วเซฟผ่านเว็บ (โหมดไฟล์) — ระบบตรวจ syntax/ค่าก่อนเขียน

## 8. การทำงานภายใน

- **ทุก interval**: อ่าน config ใหม่ → ตรวจ IP (IPv4+IPv6 ขนาน, หลาย provider) → เทียบ cache (state.json) → ถ้าเปลี่ยน: เทียบ record ใน Cloudflare → PATCH/สร้าง + บันทึกประวัติ + แจ้งเตือน
- **ประหยัด quota**: แคช zone id ข้ามรอบ, ข้ามเมื่อ IP เท่าเดิม, โดน 429 → ข้ามรอบ
- **ตรวจฉันทามติ IP** (`ip_consensus`): ต้องมี provider ≥2 รายเห็น IP ตัวเดียวกัน ถึงจะอัปเดต (กัน provider ตอบผิด/ล้าสมัย — ปิด default)
- **NAT**: ตอนเริ่ม loop ตรวจ STUN ครั้งเดียว — CGNAT/private → เตือน
- **Service**: webui เปิดใน thread เดียวกับ loop; หยุด service ภายใน ~5 วิ; tunnel หยุดพร้อมกัน; ติดตั้ง service ตั้ง auto-restart ให้ (crash → เริ่มใหม่ 5/30 วิ)
- **Dry-run**: ตรวจอย่างเดียว ไม่แตะ state/record
- **State/คิว**: เขียนแบบ atomic (temp + rename) + backup `.bak` หมุน 3 เฉพาะเมื่อเนื้อหาเปลี่ยน — กันไฟล์เสีย/สำรองกู้คืน
- **Telegram กู้รหัสผ่าน** (opt-in): ทุกรอบ loop ฟัง getUpdates — "reset password" → "yes" → สุ่มรหัสใหม่ส่งกลับ (เฉพาะ chat_id ที่ตั้ง, กัน 1 ครั้ง/10 นาที)
- **เช็คเวอร์ชันใหม่**: ตอนเริ่มโปรแกรม/service + ทุก 1 ชม. (มีเวอร์ชันใหม่ → log + แจ้ง Telegram 1 ครั้งต่อเวอร์ชัน ถ้าตั้งค่าไว้) + ทุกครั้งที่เปิดหน้าเว็บ (pill "มีเวอร์ชันใหม่")

## 9. อัปเดต/ย้ายเครื่อง

1. **ย้ายเครื่อง/โฟลเดอร์**: คัดลอกทั้งโฟลเดอร์ (exe + config.ini + state.json + logs) ไปที่ใหม่ → `install.bat` (ถ้าเป็นเครื่องใหม่) — หรือดาวน์โหลด/นำเข้า config.ini จากหน้าเว็บก็ได้
2. **อัปเดตโค้ด**: pull/build ใหม่ → หยุด service → แทนที่ exe → start
3. **หลังย้าย**: เปิดเว็บตรวจสถานะ — ประวัติ/IP เดิมยังอยู่ (state.json ติดตามไป)

## 10. ความปลอดภัย

- **Web UI เปิดเฉพาะเครื่องตัวเอง** (`127.0.0.1`) เป็นค่าเริ่มต้น — ตั้ง `webui_host = 0.0.0.0` + ตั้ง `webui_password` + เปิดพอร์ต firewall ได้ถ้าต้องการเข้าจากเครื่องอื่นใน LAN (ดู TROUBLESHOOTING)
- **รหัสผ่านหน้าเว็บ** (`webui_password`): ตั้งในฟอร์ม — **เก็บเป็น hash** (sha256 + salt จากตำแหน่ง config) ไม่มีรหัสจริงใน config.ini/cookie — ใครได้รหัสสามารถแก้ config/ควบคุม service ได้ อย่าแชร์
- **กู้รหัสผ่าน 3 ทาง**: (1) เปลี่ยนในฟอร์มตอน session ยังอยู่ (2) `cloudflare-ddns.exe reset-password` (ตั้งใหม่/ลบรหัส — ใช้ได้แม้ config ไม่ครบ) (3) กู้ผ่าน Telegram (`telegram_allow_reset = true` — "reset password" → "yes" → รหัสใหม่ 12 ตัวส่งกลับ) — รายละเอียดใน TROUBLESHOOTING
- **กันสุ่มรหัสผ่าน**: ผิด 5 ครั้งติดต่อกัน → ล็อกชั่วคราว 5 นาที (ตอบ HTTP 429) + log เตือน — นับในหน่วยความจำ (restart service = ปลดล็อกทันที)
- **กัน CSRF**: POST ทุกตัว (ยกเว้น /login) ตรวจ Origin — คำขอจากเว็บอื่นถูกบล็อก 403 + response header ความปลอดภัย (`nosniff`/`X-Frame-Options: DENY`/`no-referrer`) + cookie `SameSite=Lax`
- **สิทธิ์ admin**: ปุ่มควบคุม service (ติดตั้ง/เริ่ม/หยุด/ถอน) ต้องเปิด webui ด้วย admin — ถ้ารันใน service เอง ปุ่มที่ทำไม่ได้จะปิดอัตโนมัติ (Restart ใช้ได้เสมอ — ทำผ่าน sc.exe แยก process)
- **สถิติ Cloudflare API** (การ์ดสถานะ IP): เรียกทั้งหมด / error / โดน rate limit — ใช้ดูว่าใกล้โควตา (~1200 req/hr) หรือไม่
- **Token ต่าง ๆ** (Cloudflare API / Tunnel / Telegram bot) เก็บใน `config.ini` ข้าง exe — ห้ามแชร์ไฟล์นี้; รีโวคได้ทุกเมื่อที่หน้า API Tokens / BotFather / Zero Trust
- **User-Agent ระบุเครื่อง**: ทุกคำขอ (heartbeat/CF API/provider) ส่ง `cloudflare-ddns-updater/<เวอร์ชัน> (<ชื่อเครื่อง>)` — ฝั่งบริการดู log แล้วรู้ว่าเครื่องไหนส่ง (v1.7.6+)

---

*พบปัญหา? ดู [TROUBLESHOOTING.md](TROUBLESHOOTING.md) หรือเปิด Issue ที่ [GitHub](https://github.com/Witawat/Cloudflare-ddns)*
