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

---

## 1. ภาพรวม & องค์ประกอบ

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
- รายการ record: ชื่อ + IP + เวลาอัปเดตล่าสุด — **กดชื่อหรือ IP เพื่อคัดลอก**

### 4.3 แจ้งเตือน Telegram
- สถานะ (พร้อมใช้งาน/ยังไม่ตั้ง) + จำนวนคิวค้าง
- ปุ่ม: ส่งข้อความทดสอบ / ดูคิว (แสดงข้อความทั้งหมด) / ลองส่งใหม่ / ล้างคิว

### 4.4 Cloudflare Tunnel
- สถานะ: เปิดใช้งานไหม / cloudflared ติดตั้งไหม / รันอยู่ (pid)
- ปุ่ม: **ตั้งค่า Tunnel (wizard)** / ดู hostname ที่ผูกแล้ว (ตาราง + ลบ) / เริ่ม / หยุด / ดาวน์โหลด cloudflared
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
- ฟอร์ม: API token / interval / IPv4-6 / รหัสผ่านหน้าเว็บ + พอร์ต / ที่เก็บ log / Telegram (token, chat id, 5 เหตุการณ์, สรุปรายวัน+เวลา) / Tunnel (เปิดอัตโนมัติ, token, path) / DNS records (เพิ่ม-ลบ-แก้ทีละแถว: ชื่อ, zone, proxy, TTL, 4/6)
- โหมดไฟล์: แก้ config.ini ทั้งไฟล์ (ตรวจ syntax/ค่าก่อนบันทึก)
- **บันทึกแล้ว** → backup อัตโนมัติ (`config.ini.bak` หมุน 5) + มีผลในรอบถัดไป (ไม่ต้อง restart) — เปลี่ยนพอร์ต/รหัสผ่าน → แจ้งเตือน + ต้อง login ใหม่

### 4.9 ส่วนท้าย
- footer: เวอร์ชัน + License + ลิงก์ GitHub

## 5. แจ้งเตือน Telegram

### เหตุการณ์ (เปิด-ปิดได้ในฟอร์ม)
| เหตุการณ์ | ตัวอย่างข้อความ |
|---|---|
| เริ่ม/หยุดทำงาน | 🟢 DDNS เริ่มทำงาน / 🔴 DDNS หยุดทำงาน |
| IP เปลี่ยน | 🔄 IP เปลี่ยน / home.โดเมน.com (A) / 1.2.3.4 → 5.6.7.8 |
| สร้าง record | 🆕 สร้าง record ใหม่ / home.โดเมน.com (A) = 1.2.3.4 |
| error | ⚠️ มีปัญหา / ... (ข้อความย่อ ไม่มี JSON ยาว) |
| สรุปรายวัน | 📊 สรุปประจำวัน (ทุก record + จำนวนอัปเดตวันนี้) ตามเวลาที่ตั้ง |

### คิว (ส่งไม่สำเร็จ)
- ส่งไม่ได้ (เน็ตหลุด/token ผิด) → เก็บ `notify_queue.json` → พยายามส่งใหม่ทุก 60 วิ (สูงสุด 50 ข้อความ)
- error ซ้ำข้อความเดิมไม่ส่งซ้ำ (กันสแปม)
- จัดการในเว็บ: ดูคิว / ลองส่งใหม่ / ล้างคิว

### ตั้งค่า
- wizard หรือฟอร์ม: วาง bot token (จาก @BotFather) → chat_id หาให้อัตโนมัติ (เปิดแชทกับ bot + กด Start ก่อน)
- ทดสอบ: `notify-test` หรือปุ่มในเว็บ

## 6. Cloudflare Tunnel

### เริ่มต้น (wizard ในเว็บ 4 ขั้น)
1. **คำนำ** — Tunnel คืออะไร เหมาะกับใคร
2. **วาง token** — "เปิด Zero Trust" + "วิธีหา token" (ขั้นตอนในหน้า) → "ตรวจสอบ token" (โปรแกรมดาวน์โหลด cloudflared + ทดสอบเชื่อมต่อจริง)
3. **ผูก hostname** — ชื่อ (เช่น `app`) + โดเมน (dropdown) + บริการ (เช่น `http://localhost:8080`) → "ผูกกับ tunnel" → ตั้ง DNS + tunnel config ให้อัตโนมัติ; หรือ "เลือกจาก record ที่มีอยู่"; ดูรายการผูกแล้ว + ลบได้
4. **สรุป** — บันทึก (เปิดอัตโนมัติ) + เริ่ม tunnel

### จัดการภายหลัง
- การ์ด tunnel: เริ่ม/หยุด/ดาวน์โหลด cloudflared + ดู hostname ที่ผูกแล้ว (ลบ = ลบ ingress + CNAME)
- ฟอร์มตั้งค่า: `tunnel_enabled` / token / path
- ตอน boot: service เริ่ม tunnel อัตโนมัติถ้าเปิดไว้

### ข้อควรรู้
- ชื่อเดียวใช้ได้อย่างใดอย่างหนึ่ง (A/AAAA DDNS หรือ CNAME tunnel) — โปรแกรมตรวจชื่อชนให้
- API token ต้องมีสิทธิ์ **Account > Cloudflare Tunnel > Edit** ถึงผูก hostname ได้
- บริการที่ผูกต้องรันอยู่ (localhost:port) ถึงเข้าเว็บได้

## 7. config.ini ฉบับเต็ม

ดู `config.example.ini` — คีย์หลัก:

```
[cloudflare]
api_token            จำเป็น - สิทธิ์ Zone > DNS > Edit
interval_seconds     60 (ขั้นต่ำ 15)
use_ipv4/use_ipv6    เปิด-ปิดการอัปเดตแต่ละชนิด
webui_port           8123
webui_password       ว่าง = ไม่ต้อง login
log_dir              ว่าง = logs\ ข้าง exe
telegram_bot_token   ว่าง = ไม่แจ้ง
telegram_chat_id
notify_start/stop/ip_change/error/created   true/false
daily_report / daily_report_time            สรุปรายวัน (HH:MM)
tunnel_enabled / tunnel_token / cloudflared_path

[record:ชื่อ]
zone = โดเมน (เว้น = เดาให้)
proxied = true/false (orange cloud)
ttl = 60-7200
ipv4 / ipv6 = true/false
```

แก้ด้วยมือแล้วเซฟผ่านเว็บ (โหมดไฟล์) — ระบบตรวจ syntax/ค่าก่อนเขียน

## 8. การทำงานภายใน

- **ทุก interval**: อ่าน config ใหม่ → ตรวจ IP (IPv4+IPv6 ขนาน, หลาย provider) → เทียบ cache (state.json) → ถ้าเปลี่ยน: เทียบ record ใน Cloudflare → PATCH/สร้าง + บันทึกประวัติ + แจ้งเตือน
- **ประหยัด quota**: แคช zone id ข้ามรอบ, ข้ามเมื่อ IP เท่าเดิม, โดน 429 → ข้ามรอบ
- **NAT**: ตอนเริ่ม loop ตรวจ STUN ครั้งเดียว — CGNAT/private → เตือน
- **Service**: webui เปิดใน thread เดียวกับ loop; หยุด service ภายใน ~5 วิ; tunnel หยุดพร้อมกัน
- **Dry-run**: ตรวจอย่างเดียว ไม่แตะ state/record

## 9. อัปเดต/ย้ายเครื่อง

1. **ย้ายเครื่อง/โฟลเดอร์**: คัดลอกทั้งโฟลเดอร์ (exe + config.ini + state.json + logs) ไปที่ใหม่ → `install.bat` (ถ้าเป็นเครื่องใหม่)
2. **อัปเดตโค้ด**: pull/build ใหม่ → หยุด service → แทนที่ exe → start
3. **หลังย้าย**: เปิดเว็บตรวจสถานะ — ประวัติ/IP เดิมยังอยู่ (state.json ติดตามไป)

---

*พบปัญหา? ดู [TROUBLESHOOTING.md](TROUBLESHOOTING.md) หรือเปิด Issue ที่ [GitHub](https://github.com/Witawat/Cloudflare-ddns)*
