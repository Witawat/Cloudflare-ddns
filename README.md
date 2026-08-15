# Cloudflare DDNS Updater

ตรวจหา IP สาธารณะของเครื่อง (IPv4 + IPv6) แล้วอัปเดต DNS record บน Cloudflare **โดยอัตโนมัติเมื่อ IP เปลี่ยน** รันเป็น **Windows Service จริง** เริ่มเองตอน boot

ใช้ Python มาตรฐานเกือบทั้งหมด — dependency มีแค่ `pywin32` ตัวเดียว (หรือใช้ **ไฟล์ exe ที่ build สำเร็จรูป ไม่ต้องติดตั้ง Python เลย** ดูหัวข้อด้านล่าง)

## วิธีใช้งาน (3 ขั้นตอน)

```cmd
pip install -r requirements.txt

python -m cloudflare_ddns.main setup          REM 1. ตั้งค่าครั้งแรก (wizard ถามทีละขั้น)
python -m cloudflare_ddns.main dry-run        REM 2. ทดสอบก่อน (ไม่แตะ record จริง)
install.bat                                    REM 3. ติดตั้งเป็น service (run as admin อัตโนมัติ)
```

หรือติดตั้ง service ด้วยมือ (เปิด cmd/PowerShell **เป็น Administrator**):

```cmd
python -m cloudflare_ddns.main install
python -m cloudflare_ddns.main start
```

เสร็จแล้ว service ชื่อ **CloudflareDDNS** จะเริ่มเองทุกครั้งที่เปิดเครื่อง และตรวจ IP ใหม่ทุก 60 วินาที

## ใช้งานแบบ EXE (ไม่ต้องติดตั้ง Python)

รัน `build.bat` ครั้งเดียวเพื่อ build เป็นไฟล์เดียว `dist\cloudflare-ddns.exe` (~9 MB) แล้วใช้ได้เลย:

```cmd
build.bat                                  REM build exe (ทำครั้งเดียว)
dist\cloudflare-ddns.exe setup             REM ตั้งค่า (วาง token + เลือก zone)
dist\cloudflare-ddns.exe dry-run           REM ทดสอบก่อน
install.bat                                REM ติดตั้ง service (ใช้ exe อัตโนมัติ ถ้าพบ)
```

- เอา exe ไปวางไว้โฟลเดอร์ไหนก็ได้ (เช่น `D:\CloudflareDDNS\`) — exe จะอ่าน `config.ini` จากโฟลเดอร์เดียวกับตัว exe
- คำสั่งทุกคำสั่งเหมือนโหมด Python ทุกอย่าง (`setup / run / dry-run / install / start / stop / restart / remove / status / webui`)
- `install.bat` / `uninstall.bat` เลือกใช้ exe อัตโนมัติถ้ามี `dist\cloudflare-ddns.exe` ไม่ก็สลับไปโหมด Python
- exe ใช้ได้ทั้ง wizard (มี console) และเป็น service (SCM เรียกด้วย `run-service` เอง)

## สร้าง API Token

1. ไปที่ https://dash.cloudflare.com/profile/api-tokens → **Create Token**
2. ใช้ template **Edit zone DNS** (หรือ Custom token)
3. ตั้งสิทธิ์: `Zone > DNS > Edit` + เลือก zone ที่ต้องการ
4. คัดลอก token ไปวางตอนรัน `setup`

## คำสั่งทั้งหมด

> ใช้ `python -m cloudflare_ddns.main` ในโหมด source หรือ `cloudflare-ddns.exe` ในโหมด exe — คำสั่งเหมือนกันทุกตัว

| คำสั่ง | ใช้ทำอะไร |
|---|---|
| `... setup` | ตั้งค่าครั้งแรก (สร้าง config.ini) |
| `... run` | รันแบบ foreground (ดู log จริง ๆ ตอนเทสต์) |
| `... dry-run` | ตรวจรอบเดียว ไม่แก้ record จริง |
| `... install` | ติดตั้งเป็น Windows Service (ต้อง admin) |
| `... start` / `stop` / `restart` | ควบคุม service |
| `... remove` | ลบ service ออกจาก Windows |
| `... status` | ดูสถานะ service + IP ล่าสุด |
| `... webui` | เปิด Web UI ที่ http://127.0.0.1:8123 |
| `... notify-test` | ส่งข้อความทดสอบผ่าน Telegram (ยืนยันการตั้งค่า) |

`install.bat` / `uninstall.bat` ครอบคำสั่งด้านบน (ขอสิทธิ์ admin ให้อัตโนมัติ และใช้ exe อัตโนมัติถ้ามี)

## แจ้งเตือน Telegram

แจ้งเหตุการณ์ผ่าน Telegram Bot — ตั้งค่าได้ใน `setup` (ตอบ `y` ตรงคำถาม Telegram) หรือแก้ config.ini เอง:

```ini
[cloudflare]
telegram_bot_token = 1234567890:AAHxxx...
telegram_chat_id = 123456789
notify_start = true      ; แจ้งเมื่อเริ่ม/หยุดทำงาน
notify_stop = true
notify_ip_change = true  ; แจ้งเมื่อ IP เปลี่ยน (หัวใจหลัก)
notify_error = true      ; แจ้งเมื่อเกิดปัญหา
notify_created = true    ; แจ้งเมื่อสร้าง record ใหม่
```

- สร้าง bot ผ่าน **@BotFather** (`/newbot`) แล้ววาง token ใน `setup` — **chat_id หาให้อัตโนมัติ** (ดู [docs/GETTING-STARTED.md](docs/GETTING-STARTED.md) สำหรับขั้นตอนเต็ม)
- ส่งไม่สำเร็จ (เช่น เน็ตหลุด) → ข้อความเก็บในคิว `%PROGRAMDATA%\CloudflareDDNS\notify_queue.json` แล้ว**ส่งใหม่ในรอบถัดไปอัตโนมัติ** (สูงสุด 50 ข้อความ)
- error ซ้ำแบบเดิมไม่ส่งซ้ำทุก 60 วิ (กันสแปม)
- ทดสอบได้ด้วย `... notify-test` หรือปุ่ม "ส่งข้อความทดสอบ" ใน Web UI
- **วิธีหา Cloudflare token + Telegram bot ฉบับอัปเดตล่าสุด: [docs/GETTING-STARTED.md](docs/GETTING-STARTED.md)**

## Web UI

รัน `python -m cloudflare_ddns.main webui` แล้วเปิด `http://127.0.0.1:8123`

- **สถานะ IP**: ดู IP ล่าสุดของแต่ละ record + เวลารอบล่าสุด (refresh อัตโนมัติทุก 10 วิ) กดที่ IP เพื่อคัดลอก
- **แถบสถานะ**บนหัวหน้า: พร้อมใช้งาน / ตั้งค่าไม่ครบ / มีปัญหา มองครั้งเดียวรู้เรื่อง
- **แจ้งเตือน Telegram**: สถานะ + จำนวนคิวรอส่ง + ปุ่ม "ส่งข้อความทดสอบ"
- **ฟอร์มตั้งค่า** (ไม่ต้องแตะไฟล์ config.ini): API token, interval, เปิด/ปิด IPv4/IPv6, Telegram bot, เพิ่ม/ลบ/edit record ทีละแถว — บันทึกแล้วโปรแกรมตรวจสอบความถูกต้องให้ก่อนเขียนไฟล์ มีผลในรอบถัดไป ไม่ต้อง restart service
- ถ้าตั้ง `webui_password` ใน config จะต้องใส่รหัสก่อนเข้า
- ใช้งานบนโทรศัพท์ในบ้านได้ (responsive)

## config.ini

สร้างโดย wizard (`setup`) หรือแก้ด้วยมือตาม `config.example.ini`:

```ini
[cloudflare]
api_token = ................................
interval_seconds = 60
use_ipv4 = true
use_ipv6 = true
webui_port = 8123
webui_password =
telegram_bot_token =
telegram_chat_id =
notify_start = true
notify_ip_change = true
notify_error = true
notify_created = true

[record:home.example.com]
zone = example.com
proxied = false
ttl = 120
ipv4 = true
ipv6 = true
```

- `[record:ชื่อ]` ใส่ได้หลายตัว คัดลอก section เพิ่มเรื่อย ๆ ได้เลย
- `zone`: ชื่อ zone ใน Cloudflare (ถ้าเว้นไว้จะพยายามเดาจากชื่อ record)
- `proxied`: `true` = ผ่าน orange cloud ของ Cloudflare
- `ttl`: 120–7200 วินาที
- `ipv4` / `ipv6`: เปิด/ปิดการอัปเดต A / AAAA ของ record นั้น
- `interval_seconds`: ความถี่ในการตรวจ (ขั้นต่ำ 15)

## log

- Service/foreground เขียน log รายวันที่ `%PROGRAMDATA%\CloudflareDDNS\logs\cloudflare-ddns.log` (เก็บ 14 วัน)
- เปลี่ยนที่เก็บได้ผ่าน `log_dir` ใน config

## การทำงาน

```
ทุก interval ──▶ หา IP สาธารณะ (IPv4/IPv6 ผ่านหลาย provider สำรองกัน)
        │
        └─▶ เทียบกับ cache ภายใน ──เท่าเดิม──▶ ข้ามไป (ไม่แตะ API)
                    │
                    └─ต่างกัน──▶ เทียบ record ใน Cloudflare ──ตรงแล้ว──▶ อัปเดต cache
                                        │
                                        └─ต่าง──▶ PATCH (หรือสร้าง record ใหม่ถ้ายังไม่มี)
```

- ตรวจ IP จาก: `api.ipify.org` → `ifconfig.me` → `icanhazip.com` → Cloudflare trace (IPv4) และ `api6.ipify.org` → `ifconfig.co` (IPv6)
- อัปเดตเฉพาะเมื่อ IP เปลี่ยนจริง ลดการใช้ API quota
- ถ้า record ยังไม่มีใน Cloudflare จะ **สร้างให้อัตโนมัติ**
- แก้ config ระหว่างรันได้เลย — service อ่าน config ใหม่ทุกรอบ

## แก้ปัญหาทั่วไป

| อาการ | วิธีแก้ |
|---|---|
| `ไม่พบ pywin32` | `python -m pip install pywin32` |
| `ติดตั้ง service ไม่ได้` | ต้องรันด้วยสิทธิ์ Administrator (double-click `install.bat` จัดการให้) |
| token error ระหว่าง `setup` | ตรวจว่าสร้าง token ด้วยสิทธิ์ `Zone > DNS > Edit` จริง |
| `หา IP สาธารณะไม่ได้` | เช็ค internet/ไฟร์วอลล์ (เครื่องต้องออก HTTPS ไปยัง provider ข้างบนได้) |
| IPv6 ไม่ถูกอัปเดต | ผู้ให้บริการอินเทอร์เน็ตอาจยังไม่ให้ IPv6 — ตั้ง `use_ipv6 = false` ได้ |
| อยากให้ IP เปลี่ยนเร็วขึ้น | ลด `interval_seconds` (ขั้นต่ำ 15) |
