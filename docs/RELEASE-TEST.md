# คู่มือทดสอบ exe ก่อน release (Release Test)

ใช้ทดสอบว่า exe ที่จะปล่อย **คนอื่นเอาไปใช้จริงได้ไหม** — จำลองผู้ใช้ใหม่ 100% (โฟลเดอร์ใหม่ ไม่มี config ไม่มี state)

## วิธีใช้

```powershell
# 1) สร้างโฟลเดอร์ใหม่ + คัดลอก exe (จำลองผู้ใช้ใหม่ — ไม่มี config/state)
New-Item -ItemType Directory -Path D:\CFDDNS-Release-Test
Copy-Item dist\cloudflare-ddns.exe D:\CFDDNS-Release-Test\

# 2) รัน exe แบบปกติ (กดเปล่า ๆ — เทียบเท่าผู้ใช้ double-click)
#    ต้องไม่มี webui/service รันค้างที่พอร์ต 8123 ก่อน!
Start-Process D:\CFDDNS-Release-Test\cloudflare-ddns.exe -WorkingDirectory D:\CFDDNS-Release-Test

# 3) ตรวจว่า wizard ขึ้นอัตโนมัติ (ยังไม่ตั้งค่า)
curl http://127.0.0.1:8123/setup-state   # ต้อง {"needs_setup":true}

# 4) รันเทสต์ wizard อัตโนมัติ (playwright — ติดตั้งในโฟลเดอร์แยก)
$env:RELTEST_DATA = "D:\CFDDNS-Release-Test\..\reltest-data.json"   # ข้อมูลเทสต์ (token/zone/record/bot/chat)
$env:RELTEST_OUT  = "reltest-report.txt"
node test-release.mjs
```

## ข้อมูลเทสต์ (`reltest-data.json`)

สร้างจาก config ที่ใช้งานจริง (หรือข้อมูลทดสอบใหม่ — ควรใช้ token/zone จริง เพื่อตรวจว่าคนอื่นใช้ได้จริง):

```json
{
  "api_token": "cfut_...",
  "zone": "example.com",
  "record": "release-test",
  "tg_bot": "123456789:AAHxxx",
  "tg_chat": "123456789"
}
```

> ระวัง: record ชื่อ `release-test` จะถูกสร้างจริงที่ Cloudflare ระหว่างเทสต์ — ลบทิ้งหลังเทสต์
> (ดูหัวข้อ "ล้างของหลังเทสต์")

## สิ่งที่เทสต์ (15 รายการ)

| # | ขั้นตอน | ตรวจ |
|---|---|---|
| 1 | เปิด webui ครั้งแรก | wizard เปิดอัตโนมัติเมื่อยังไม่ตั้งค่า |
| 2 | ขั้น 1 ยินดีต้อนรับ | หน้า wizard แสดง |
| 3 | ขั้น 2 ใส่ API token | ช่อง token + `/verify-token` ผ่าน → ข้ามขั้น |
| 4 | ขั้น 3 เลือก zone | dropdown มี zone จาก Cloudflare จริง |
| 5 | ขั้น 3 ปุ่ม + เพิ่ม record | เพิ่ม/ลบแถว record ได้ |
| 6 | ขั้น 3 ต่อไป | ไปขั้น Telegram |
| 7 | ขั้น 4 ค้นหา chat id | resolve อัตโนมัติ (ถ้า bot ไม่มีข้อความใหม่ → ใช้ช่องกรอกมือแทน) |
| 8 | ขั้น 4 **กรอก chat id ด้วยมือ** | ช่องกรอกใช้งานได้ (กรณี resolve ไม่ได้) |
| 9 | ขั้น 4 ปุ่มส่งข้อความทดสอบ | active เมื่อมี chat id |
| 10 | ขั้น 4 ส่งข้อความทดสอบ | `/notify-test-raw` → Telegram เด้งจริง |
| 11 | ขั้น 5 สรุป | สรุปมี zone/record ที่เลือก |
| 12 | ขั้น 5 บันทึก | `/save-config` ผ่าน → หน้าตอบสนอง |
| 13 | หลังบันทึก | wizard ปิด (ตั้งค่าเสร็จ) |
| 14 | หลังบันทึก | ไม่มีข้อผิดพลาด config บนหน้า · pill = พร้อมใช้งาน |
| 15 | console | ไม่มี JS error |

## ตรวจผลเพิ่ม (นอกสคริปต์)

```powershell
# config ที่ wizard สร้าง — chat_id ต้องติดค่า
Get-Content D:\CFDDNS-Release-Test\config.ini

# DDNS ทำงานจริง: record ถูกสร้างที่ Cloudflare + state อัปเดต
Get-Content D:\CFDDNS-Release-Test\state.json          # ต้องมี release-test|A = <IP> + last_run ล่าสุด
python -c "..."   # เรียก Cloudflare API ดู record (หรือเปิดเว็บ DNS)

# Telegram: ข้อความ "เริ่มทำงาน" + "สร้าง record" เด้งในแชท
Select-String -Path D:\CFDDNS-Release-Test\logs\cloudflare-ddns.log -Pattern "Telegram สำเร็จ"
```

## ล้างของหลังเทสต์ (สำคัญ)

```powershell
# 1) ปิด exe ที่เทสต์
taskkill /F /IM cloudflare-ddns.exe
taskkill /F /IM cloudflared.exe

# 2) ลบ record ทดสอบที่ Cloudflare (release-test.<zone>)
python -c "จาก cloudflare_ddns.cloudflare_api... delete_record"

# 3) ลบโฟลเดอร์เทสต์ (หรือเก็บไว้ดู — ไม่มีผลต่อของจริง)
Remove-Item D:\CFDDNS-Release-Test -Recurse -Force
```

## เกณฑ์ผ่าน

- **15/15 (100%)** = พร้อม release
- ข้อควรรู้ (ไม่ถือเป็น fail):
  - `resolve-chat-id` คืน "ยังไม่มีข้อความจาก bot" — พฤติกรรม Telegram API ปกติเมื่อ bot ไม่มีข้อความใหม่ — ใช้ช่องกรอกมือแทน
  - console error 400 ของ `/resolve-chat-id` — เป็น error response ตาม design (ไม่มี update ใหม่)
  - IPv6 "หา IP ไม่ได้" — ปกติเมื่อเน็ตไม่มี IPv6

## ผลการทดสอบรอบล่าสุด

ดู `reltest-report.txt` (output ของ `node test-release.mjs`) — ผลรอบสุดท้าย: **15/15 (100%)**
