# Design

Mood: "เช้าที่บ้าน เปิดแล็ปท็อปดูสถานะ DDNS กลางแสงธรรมชาติ หน้าสว่างสะอาด อ่านทีเดียวรู้เรื่อง มีส้ม Cloudflare จุดเดียว"

## Palette (OKLCH)

| Token | Value | ใช้กับ |
|---|---|---|
| `--bg` | `oklch(1 0 0)` | พื้นหลังหน้า (ขาวจริง ไม่มี warmth ซ่อน) |
| `--surface` | `oklch(0.972 0.006 50)` | การ์ด/แถว (tint ส้ม 0.006 ตาม brand hue) |
| `--surface-2` | `oklch(0.945 0.010 50)` | แถว hover / อินพุต |
| `--border` | `oklch(0.90 0.012 50)` | เส้นขอบ |
| `--ink` | `oklch(0.24 0.03 250)` | ตัวหนังสือหลัก (น้ำเงิน-เทาเข้ม ไม่ดำทื่อ) |
| `--ink-2` | `oklch(0.45 0.035 250)` | ตัวหนังสือรอง |
| `--muted` | `oklch(0.56 0.03 250)` | ป้ายกำกับ/ตัวช่วย (ผ่าน AA 4.5 บน bg) |
| `--accent` | `oklch(0.62 0.17 45)` | ปุ่มหลัก/จุดสำคัญ (ส้ม Cloudflare) |
| `--accent-ink` | `oklch(1 0 0)` | ตัวหนังสือบนปุ่มส้ม |
| `--accent-soft` | `oklch(0.945 0.05 50)` | พื้นหลัง highlight ส้มจาง |
| `--ok` | `oklch(0.5 0.11 155)` | สถานะปกติ |
| `--ok-soft` | `oklch(0.955 0.04 155)` | พื้นหลังสถานะปกติ |
| `--warn` | `oklch(0.55 0.13 65)` | คำเตือน |
| `--warn-soft` | `oklch(0.96 0.05 70)` | พื้นหลังเตือน |
| `--danger` | `oklch(0.5 0.19 28)` | error |
| `--danger-soft` | `oklch(0.955 0.05 28)` | พื้นหลัง error |

สี status: มีทั้ง fill (จุด/พื้นหลังจาง) และคำกำกับภาษาไทยเสมอ ไม่พึ่งสีอย่างเดียว

## Typography

- UI: system stack `Segoe UI, system-ui, sans-serif` (Windows native, สบายตา)
- Mono (IP/ค่าทางเทคนิค): `Cascadia Code, Consolas, monospace`
- ขนาด: 13/14/16/20 (ตาราง/ตัวช่วย / ตัวหลัก / หัวข้อเล็ก / หัวหน้า) อัตรา ≥1.25 ระหว่างชั้น
- ตัวพิมพ์ใหญ่ใช้กับ badge สั้น ๆ เท่านั้น

## Layout & Components

- **แถบหัวหน้า**: ชื่อ + status pill รวม (พร้อม / ไม่พร้อม / มีปัญหา) + pill เวอร์ชัน (เล็ก 0.75rem) + pill "มีเวอร์ชันใหม่" (โทน warn, ลิงก์ไป release) + ปุ่ม Refresh
- **ส่วนสถานะ**: รายการ record (ไม่ใช่การ์ดซ้อน): แต่ละแถว = จุดสี + ชื่อ record (mono, คัดลอกได้, ไม่ติด `|A`) + IP (mono, คัดลอกได้) + badge เวลาอัปเดตล่าสุดพร้อมชนิด (A/AAAA); ถ้า error แถวนั้นเป็นโทน error + บรรทัดสถิติ Cloudflare API (เรียก/error/429, muted, ขนาดเล็ก)
- **ส่วน Windows Service**: หนึ่งแถว: สถานะติดตั้ง/รัน + ปุ่มเริ่ม/หยุด/Restart/ติดตั้ง/ถอน (ปุ่มที่ทำไม่ได้จากบริบทปัจจุบัน — ไม่ admin หรือรันใน service — disabled พร้อม title อธิบาย) + บรรทัด context ("รันใน service (มีสิทธิ์ระบบ)" / "standalone · admin ✓/✗") + details "ข้อควรรู้"
- **ส่วน Telegram**: หนึ่งแถว: สถานะพร้อมใช้งาน/ยังไม่ได้ตั้ง/คิวรอ N + ปุ่ม "ส่งข้อความทดสอบ"
- **ส่วนตั้งค่า (ฟอร์ม)**: กลุ่ม Cloudflare (token, interval, toggles), กลุ่ม Telegram (token, chat_id, toggles เหตุการณ์), กลุ่ม records (แต่ละแถวมีฟอร์ม + ปุ่มลบ, ปุ่ม "เพิ่ม record")
- Toast ด้านล่างขวา (fixed, z-index สูงสุด) สำหรับผลบันทึก/error
- Motion: เฉพาะ hover transition ≤120ms + toast เข้า (fade+translateY 8px) ไม่ง่าย ๆ; `prefers-reduced-motion: reduce` → ทุกอย่าง instant
- z-index scale: sticky-header 10, wizard/tunnel-wizard overlay 60, toast 40

## หมายเหตุ

- ไม่มีกราฟ, ไม่มี gradient text, ไม่มี side-stripe border, ไม่มี hero metric
- ปุ่ม: พื้นส้ม + ตัวขาว (primary) / พื้น surface + ขอบ border (secondary) / สีไม่ใช้ปุ่ม
- ทุกสถานะมี 3 ระดับ: ปรกติ / ตั้งค่าไม่ครบ / มีปัญหา (soft bg + เส้นขอบไม่เกิน 1px)
