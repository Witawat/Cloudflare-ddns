# ใช้งานบน macOS

รองรับ macOS 12 ขึ้นไปทั้ง Apple Silicon (`arm64`) และ Intel (`x86_64`) โดยรันเบื้องหลังผ่าน LaunchAgent ของ `launchd` ไม่ต้องใช้ `sudo`

## ติดตั้งจาก source

ต้องมี Python 3.9 ขึ้นไป จากนั้นรันในโฟลเดอร์โปรเจกต์:

```bash
python3 -m cloudflare_ddns.main setup
python3 -m cloudflare_ddns.main dry-run
./install-macos.sh
```

เปิด Web UI ที่ `http://127.0.0.1:8123`

## คำสั่งดูแล LaunchAgent

```bash
python3 -m cloudflare_ddns.main status
python3 -m cloudflare_ddns.main start
python3 -m cloudflare_ddns.main stop
python3 -m cloudflare_ddns.main restart
python3 -m cloudflare_ddns.main remove
```

ไฟล์ LaunchAgent อยู่ที่ `~/Library/LaunchAgents/com.makerwitawat.cloudflare-ddns.plist` และเริ่มอัตโนมัติเมื่อ user login การถอน LaunchAgent ไม่ลบ `config.ini`, state หรือ log

## Build เป็นไฟล์รันเดี่ยว

```bash
python3 -m venv .build-venv
source .build-venv/bin/activate
python -m pip install pyinstaller
PYTHON_BIN="$PWD/.build-venv/bin/python" ./build-macos.sh
./dist/cloudflare-ddns status
```

PyInstaller สร้าง binary ให้สถาปัตยกรรมเดียวกับเครื่องที่ build ถ้าต้องแจกทั้ง Apple Silicon และ Intel ให้ build บนแต่ละสถาปัตยกรรมแยกกัน

## Cloudflare Tunnel

เมื่อ `cloudflared_path` ว่าง โปรแกรมจะเลือกและดาวน์โหลด asset ทางการให้เอง:

- Apple Silicon: `cloudflared-darwin-arm64.tgz`
- Intel: `cloudflared-darwin-amd64.tgz`

ไฟล์จะถูกแตกเป็น `cloudflared` ข้าง `config.ini` และตั้ง permission ให้รันได้อัตโนมัติ

## แก้ปัญหา

- ดู log หลัก: `logs/cloudflare-ddns.log`
- ดู log จาก launchd: `logs/launchd.stdout.log` และ `logs/launchd.stderr.log`
- ถ้าพอร์ต 8123 ถูกใช้: เปลี่ยน `webui_port` ใน config แล้ว `restart`
- ถ้า macOS บล็อก binary ที่ copy มาจากเครื่องอื่น: ไปที่ System Settings → Privacy & Security แล้วอนุญาต หรือ build จาก source บนเครื่องนั้น
- LaunchAgent เป็น service ระดับ user จึงเริ่มเมื่อ login ไม่ได้รันก่อนหน้า login เหมือน LaunchDaemon
