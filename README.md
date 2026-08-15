# Cloudflare DDNS Updater

ตรวจหา IP สาธารณะของเครื่อง (IPv4 + IPv6) แล้วอัปเดต DNS record บน Cloudflare **โดยอัตโนมัติเมื่อ IP เปลี่ยน** รันเป็น **Windows Service จริง** เริ่มเองตอน boot — พร้อม **Web UI** สำหรับดูสถานะ/ตั้งค่า/สแกนพอร์ต และรองรับ **Cloudflare Tunnel** (ไม่ต้องเปิดพอร์ต)

> 📖 เอกสารอื่น: [คู่มือใช้งานละเอียด](docs/USAGE.md) · [เริ่มต้นใช้งาน/หา Token](docs/GETTING-STARTED.md) · [แก้ปัญหาทั่วไป](docs/TROUBLESHOOTING.md) · [ประวัติเวอร์ชัน](CHANGELOG.md)

## ความสามารถหลัก

| ฟีเจอร์ | รายละเอียด |
|---|---|
| **DDNS อัตโนมัติ** | ตรวจ IP IPv4/IPv6 (หลาย provider สำรอง) → อัปเดต A/AAAA เฉพาะเมื่อ IP เปลี่ยน + สร้าง record ให้อัตโนมัติถ้ายังไม่มี |
| **Windows Service** | รันจริงตอน boot, log รายวัน, หยุด/เริ่มเร็ว, แก้ config ได้ระหว่างรัน (มีผลรอบถัดไป) |
| **Web UI** | สถานะสด, wizard ตั้งค่าครั้งแรก 5 ขั้น, ฟอร์มตั้งค่า + โหมดแก้ไฟล์ตรง, ประวัติ, ดู log, สแกนพอร์ต, ปุ่มควบคุม Telegram/Tunnel — ใช้บนมือถือได้ |
| **แจ้งเตือน Telegram** | เริ่ม/หยุด, IP เปลี่ยน, error, สร้าง record + สรุปรายวัน — มีคิว retry + กันสแปมซ้ำ |
| **Cloudflare Tunnel** | เปิด cloudflared ตาม service, wizard 4 ขั้น, **ผูก hostname กับ tunnel อัตโนมัติ** (ตั้ง DNS + config ให้ ไม่ต้องแตะ dashboard) |
| **ตรวจ NAT** | รู้ว่า IP อยู่หลัง CGNAT หรือไม่ (STUN) — เตือนถ้า DDNS ใช้ไม่ได้ |
| **EXE ไฟล์เดียว** | build ด้วย PyInstaller — ไม่ต้องติดตั้ง Python |

## เริ่มต้นเร็ว (3 ขั้นตอน)

```cmd
pip install -r requirements.txt   REM หรือใช้ exe (ดูด้านล่าง)
python -m cloudflare_ddns.main setup     REM 1. ตั้งค่า (wizard ถามทีละขั้น + เปิดเบราว์เซอร์หา token ให้)
python -m cloudflare_ddns.main dry-run   REM 2. ทดสอบก่อน (ไม่แตะ record จริง)
install.bat                              REM 3. ติดตั้ง service (ขอ admin ให้อัตโนมัติ)
```

เสร็จแล้วเปิด `http://127.0.0.1:8123` ดูสถานะได้เลย (service เปิด Web UI ให้เอง — ครั้งแรก wizard จะขึ้นให้ตั้งค่า)

## ใช้งานแบบ EXE (ไม่ต้องติดตั้ง Python)

```cmd
build.bat                     REM build ครั้งเดียว → dist\cloudflare-ddns.exe (~9 MB)
dist\cloudflare-ddns.exe      REM รันเปล่า ๆ = เปิด Web UI + เบราว์เซอร์ให้อัตโนมัติ
install.bat                   REM ติดตั้ง service (ใช้ exe อัตโนมัติถ้าพบ)
```

- เอา exe ไปวางโฟลเดอร์ไหนก็ได้ — config.ini, log, state, คิวแจ้งเตือน **อยู่ข้าง exe ทั้งหมด** (ย้าย exe = ย้ายทั้งชุด)
- ทุกคำสั่งเหมือนโหมด Python: `setup / run / dry-run / install / start / stop / restart / remove / status / webui / notify-test`

## คำสั่งทั้งหมด

| คำสั่ง | ใช้ทำอะไร |
|---|---|
| `... setup` | ตั้งค่าครั้งแรก (wizard ถามทีละขั้น) |
| `... run` | รันแบบ foreground (ดู log จริง ๆ ตอนเทสต์) |
| `... dry-run` | ตรวจรอบเดียว ไม่แก้ record จริง |
| `... install` / `remove` | ติดตั้ง/ลบ Windows Service (ต้อง admin) |
| `... start` / `stop` / `restart` | ควบคุม service |
| `... status` | สถานะ service + IP ล่าสุด + tunnel |
| `... webui` | เปิด Web UI ที่ http://127.0.0.1:8123 |
| `... notify-test` | ส่งข้อความทดสอบ Telegram |

`install.bat` / `uninstall.bat` ครอบคำสั่ง install/remove (ขอสิทธิ์ admin ให้อัตโนมัติ)

## Cloudflare Tunnel (ทางเลือกแทน/เสริม DDNS)

ให้บริการผ่าน **Tunnel** แทนการเปิดพอร์ต/พึ่ง IP ตรง — เหมาะกับ ISP แจก IP แบบ **CGNAT** หรือไม่อยากเปิด port forward:

```ini
[cloudflare]
tunnel_enabled = true
tunnel_token = eyJhIjoi...        ; จาก Zero Trust > Networks > Tunnels
cloudflared_path =                ; เว้นว่าง = ดาวน์โหลด cloudflared.exe ข้าง exe อัตโนมัติ
```

**วิธีเริ่ม (แนะนำใช้ wizard ในเว็บ):** การ์ด Cloudflare Tunnel → "ตั้งค่า Tunnel (wizard)" → วาง token (ตรวจสอบให้จริง) → ใส่ชื่อ + โดเมน + บริการ → "ผูกกับ tunnel" — โปรแกรมตั้ง DNS (CNAME → tunnel) + tunnel config ให้เอง → เข้า `https://ชื่อ.โดเมน.com` ได้ทันที — ดู/ลบ hostname ที่ผูกแล้วได้ด้วยปุ่ม "ดู hostname ที่ผูกแล้ว"

### รองรับทุกแบบ (หลายพอร์ต/หลาย protocol)

| รูปแบบ | วิธี | ตัวอย่าง |
|---|---|---|
| **หลาย hostname → หลายพอร์ต** | ผูกซ้ำได้ (หรือปุ่ม "+ เพิ่ม hostname" ในการ์ด) | `app.โดเมน` → 8080 · `api.โดเมน` → 3000 |
| **หลายพอร์ตต่อชื่อเดียว (path)** | ระบุ Path ในฟอร์มผูก | `app.โดเมน` → 8080 · `app.โดเมน/api` → 3000 |
| **TCP** (SSH/game/RDP) | ชนิด TCP + `tcp://localhost:พอร์ต` | `ssh.โดเมน` → `tcp://localhost:22` |
| **UDP** (game/VPN) | ชนิด UDP + `udp://localhost:พอร์ต` | `vpn.โดเมน` → `udp://localhost:51820` |
| **HTTPS ภายใน** | ชนิด HTTPS + `https://localhost:พอร์ต` | `app.โดเมน` → `https://localhost:8443` |

จัดการทั้งหมดใน **การ์ด Cloudflare Tunnel**: ตาราง "ดู hostname ที่ผูกแล้ว" (hostname+path / ชนิด / บริการ + ลบ) · ปุ่ม "+ เพิ่ม hostname" (ผูกด่วน) · ปุ่ม "ซิงค์จาก Cloudflare" (ดึงจาก API → บันทึกลง config)

### ข้อควรรู้ (Tunnel)

- **ชื่อเดียวใช้ได้อย่างใดอย่างหนึ่ง:** A/AAAA (DDNS) หรือ CNAME (tunnel) — Cloudflare ห้ามซ้ำชื่อกัน → ใช้**คนละชื่อ** (โปรแกรมตรวจให้และแจ้งเตือน)
- Tunnel **ไม่ต้องเปิดพอร์ต / ไม่พึ่ง IP** — เหมาะ CGNAT / ไม่แตะเราเตอร์; DDNS เหมาะบริการที่รับ connection ตรง (SSH, game)
- บริการที่ผูก (เช่น `localhost:8080`) ต้องรันอยู่ถึงเข้าได้
- การผูก hostname ต้องใช้ API token ที่มีสิทธิ์ **Account > Cloudflare Tunnel > Edit**
- tunnel รันตาม service — หยุด service = tunnel หยุด
- tunnel token ใช้ได้จนกว่า revoke ที่ Zero Trust

## แจ้งเตือน Telegram

แจ้งเหตุการณ์: เริ่ม/หยุด, IP เปลี่ยน, error, สร้าง record + **สรุปรายวัน** (ตั้งเวลาได้) — ส่งไม่สำเร็จเก็บคิวแล้วส่งใหม่ทุกรอบ (จัดการคิวได้ในเว็บ: ดู/ลองส่งใหม่/ล้าง) — ตั้งค่าใน wizard หรือฟอร์มเว็บ (หา chat_id ให้อัตโนมัติผ่าน @BotFather + getUpdates)

## Web UI (http://127.0.0.1:8123)

- **สถานะ IP**: IP ล่าสุดต่อ record + เวลาอัปเดต + กดคัดลอกชื่อ/IP ได้ + ตรวจ NAT (STUN) + ตรวจ IP สด
- **แถบสถานะ**หัวหน้า: พร้อมใช้งาน / ตั้งค่าไม่ครบ / มีปัญหา
- **Telegram**: สถานะ + คิว + ส่งข้อความทดสอบ + ดูคิว/ลองส่งใหม่/ล้างคิว
- **Cloudflare Tunnel**: สถานะ + wizard ตั้งค่า + ดู hostname ที่ผูกแล้ว + เริ่ม/หยุด/ดาวน์โหลด cloudflared
- **สแกนพอร์ต**: สแกน host ใน config (resolve IP ปัจจุบัน) แสดงพอร์ตเปิด/ปิด + ชื่อบริการ
- **ประวัติการอัปเดต**: 50 รายการล่าสุด (เวลา/record/การกระทำ/IP)
- **Log ล่าสุด**: 200 บรรทัด + ปุ่มโหลดใหม่
- **ตั้งค่า**: ฟอร์ม (token/interval/password/พอร์ต/log/Tunnel/Telegram/records) + โหมด "แก้ไขไฟล์โดยตรง" (textarea + ตรวจ syntax) + auto-backup config (เก็บ 5 อัน)
- **wizard ครั้งแรก** ขึ้นเองอัตโนมัติเมื่อ config ไม่ครบ + wizard Tunnel แยก
- ตั้ง `webui_password` ได้ในฟอร์ม (ต้อง login หลังตั้ง) · responsive มือถือ

## config.ini

สร้างโดย wizard/เว็บ หรือแก้เองตาม `config.example.ini`:

```ini
[cloudflare]
api_token = ................................
interval_seconds = 60
use_ipv4 = true
use_ipv6 = true
webui_port = 8123
webui_password =
log_dir =

telegram_bot_token =
telegram_chat_id =
notify_start = true
notify_ip_change = true
notify_error = true
notify_created = true
daily_report = true
daily_report_time = 08:00

tunnel_enabled = false
tunnel_token =
cloudflared_path =

[record:home.example.com]
zone = example.com
proxied = false
ttl = 60
ipv4 = true
ipv6 = true
```

- `[record:ชื่อ]` ใส่ได้หลายตัว — ชื่อสั้นได้ (เช่น `home`) โปรแกรมเติม `.zone` ให้อัตโนมัติ; `@` = หน้าหลัก
- `ttl`: 60–7200 (ใช้ 60 = IP ใหม่กระจายเร็วสุด)
- บันทึกทุกครั้งผ่านเว็บ/ฟอร์ม → backup อัตโนมัติ (`config.ini.bak` หมุน 5 อัน)

## log / ข้อมูล

- log รายวัน: `logs\cloudflare-ddns.log` (ข้าง exe, เก็บ 14 วัน) — ดูในเว็บได้ (Log ล่าสุด)
- state/คิว/pid: `state.json`, `notify_queue.json`, `tunnel.pid` — ข้าง exe เช่นกัน

## การทำงาน

```
ทุก interval ─▶ หา IP (IPv4/IPv6, หลาย provider สำรอง)
     │
     ├─ NAT ตรวจ (STUN) ─ CGNAT/private ─▶ เตือนครั้งเดียว (Telegram + log)
     └─ เทียบ cache ──เท่าเดิม──▶ ข้าม (ไม่แตะ API)
          └─ ต่าง ──▶ เทียบ record ใน Cloudflare ──ตรง──▶ อัปเดต cache
                              └─ ต่าง ──▶ PATCH/สร้าง record + แจ้งเตือน
```

- แคช zone id ข้ามรอบ + เจอ HTTP 429 (rate limit) → ข้ามรอบทันที + แจ้งเตือน
- แก้ config ระหว่างรันได้เลย — service อ่านใหม่ทุกรอบ ไม่ต้อง restart

## แก้ปัญหาทั่วไป

| อาการ | วิธีแก้ |
|---|---|
| `ไม่พบ pywin32` | `python -m pip install pywin32` |
| ติดตั้ง service ไม่ได้ | ต้อง admin — double-click `install.bat` จัดการให้ |
| token error ระหว่าง setup | ตรวจสิทธิ์ `Zone > DNS > Edit` จริง |
| หา IP ไม่ได้ | เช็ค internet/ไฟร์วอลล์ (ต้องออก HTTPS ได้) |
| IPv6 ไม่อัปเดต | ISP อาจยังไม่ให้ IPv6 — ตั้ง `use_ipv6 = false` |
| error 409 getUpdates | โปรแกรมลบ webhook ให้อัตโนมัติแล้วลองใหม่ |
| ข้อความ Telegram ค้าง | ตรวจ token/chat id + ปุ่ม "ลองส่งใหม่"/"ล้างคิว" ในเว็บ |
| ผูก tunnel แล้วเข้าไม่ได้ | บริการ (localhost:port) ต้องรันอยู่ + tunnel กำลังรัน (การ์ด) |

**เต็มฉบับ: [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)**

## เครดิต & License

- **ผู้พัฒนา:** Witawat (XSoFTz) · [github.com/Witawat/Cloudflare-ddns](https://github.com/Witawat/Cloudflare-ddns)
- **License:** [MIT](LICENSE) — ใช้ แก้ไข แจกจ่ายได้ฟรี (แจ้งที่มาด้วยก็ดี)
- **ไอคอน exe:** icons8 ([icons8.com](https://icons8.com))
- **เครื่องมือ:** Cloudflare API v4, Telegram Bot API, PyInstaller, pywin32, Pillow, Playwright (ทดสอบ UI)
- **ประวัติการเปลี่ยนแปลง:** [CHANGELOG.md](CHANGELOG.md)
