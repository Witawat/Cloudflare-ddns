# คู่มือหา API Key / Token (อัปเดตล่าสุด)

## 1. Cloudflare API Token

> โปรแกรม**ไม่สามารถสร้าง token ให้อัตโนมัติ**ได้ เพราะ Cloudflare ต้องให้คุณล็อกอิน + ยืนยันสิทธิ์ในหน้าเว็บ (ห้ามใครสร้างแทนได้) — แต่ขั้นตอนด้านล่างใช้เวลาน้อยกว่า 1 นาที และตัว `setup` ของโปรแกรมจะเปิดเบราว์เซอร์ไปหน้าที่ถูกต้องให้เอง

### ขั้นตอน (ปัจจุบัน 2026)

1. ล็อกอินที่ https://dash.cloudflare.com
2. เมนู **My Profile** (มุมขวาบน) → **API Tokens**
   - หรือตรง ๆ: https://dash.cloudflare.com/profile/api-tokens
3. กดปุ่มสีส้ม **Create Token**
4. ตรง "API token templates" เลื่อนหา **Edit zone DNS** → กด **Use template**
   > ใช้ template นี้ดีที่สุด: มันตั้งสิทธิ์ `Zone > DNS > Edit` ให้ครบสำหรับ DDNS อยู่แล้ว
5. **Token name**: ตั้งอะไรก็ได้ เช่น `home-ddns`
6. **Permissions** (ควรเป็นแบบนี้อยู่แล้ว ถ้าใช้ template):
   - Zone → DNS → **Edit**
7. **Zone Resources**: เลือก **Include → Specific zone → เลือกโดเมนของคุณ** (เลือกได้หลายโดเมน)
   - หรือจะเลือก `All zones` ก็ได้ถ้าสะดวก แต่เลือกเฉพาะโดเมนที่ใช้ = ปลอดภัยกว่า
8. (ไม่จำเป็น) **Client IP Address Filtering / TTL** — จำกัดได้ถ้าอยากได้ แต่ข้ามได้
9. กด **Continue to summary** → ตรวจรายการ → กด **Create Token**
10. **คัดลอก token ทันที** — หน้าแสดงครั้งเดียว! ถ้าปิดไปต้องสร้างใหม่
    - token รุ่นใหม่ขึ้นต้นด้วย `cfut_...` (ยาวประมาณ 40 ตัว)
    - **ห้ามแชร์/วางใน chat** ใครได้ token ไปสามารถแก้ DNS ของคุณได้

### ตรวจว่า token ใช้ได้ (ไม่จำเป็น — `setup` ตรวจให้เอง)

```bash
curl "https://api.cloudflare.com/client/v4/user/tokens/verify" ^
  --header "Authorization: Bearer <TOKEN>"
```

ตอบ `"success": true` + `"status": "active"` = ใช้ได้

### แก้ปัญหา

| ปัญหา | วิธีแก้ |
|---|---|
| `Invalid format for Authorization header` | token ติดช่องว่าง/ขึ้นบรรทัดใหม่ตอนคัดลอก ลองวางใหม่ |
| `token is not active` | token หมดอายุ (ถ้าตั้ง TTL ไว้) → สร้างใหม่ |
| `did not have permission` | เพิ่มสิทธิ์ `Zone > DNS > Edit` + ระบุ zone ในหน้า token |
| ไม่เห็นโดเมนในรายการ | โดเมนต้อง add เข้า Cloudflare ก่อน (หน้า Overview → Add a site) |

---

## 2. Telegram Bot (รับการแจ้งเตือน)

### ขั้นตอน

1. เปิด Telegram → ค้นหา **@BotFather** (เครื่องหมายถูกสีน้ำเงิน) → กด Start
2. ส่งคำสั่ง **`/newbot`**
3. ตั้งชื่อ bot (เช่น `Home DDNS`) → ตั้ง username (ลงท้ายด้วย `bot` เช่น `home_ddns_bot`)
4. BotFather ส่งข้อความกลับมา ที่มีบรรทัด:
   ```
   Use this token to access the HTTP API:
   1234567890:AAHxxxxx_xxxxxxxxxxxxxxxxxxxx
   ```
   → นี่คือ **Bot token** (คัดลอกไว้)
5. เปิดแชทกับ bot ใหม่ (กดที่ชื่อ bot ที่ BotFather ส่งมาให้) → กด **Start** หรือพิมพ์อะไรก็ได้
6. จากนั้นรัน:
   ```cmd
   cloudflare-ddns.exe setup
   ```
   ตอบ `y` ตรงคำถาม "ตั้งค่าแจ้งเตือน Telegram" → วาง Bot token → **โปรแกรมดึง chat_id ให้อัตโนมัติ** และส่งข้อความทดสอบให้ตรวจ

### หา chat_id เอง (ถ้าไม่ใช้ wizard)

ส่งข้อความ/กด Start กับ bot ของคุณ แล้วเปิดในเบราว์เซอร์:

```
https://api.telegram.org/bot<TOKEN>/getUpdates
```

ดูใน JSON: `"chat": {"id": <ตัวเลขนี้คือ chat_id>, ...}` (ถ้าว่าง = ยังไม่เคยส่งข้อความให้ bot — ส่งก่อนแล้วลองใหม่)

### ตรวจว่า bot ทำงาน

```cmd
cloudflare-ddns.exe notify-test
```

### แก้ปัญหา

| ปัญหา | วิธีแก้ |
|---|---|
| `chat not found` | เปิดแชทกับ bot แล้วกด Start ก่อน (bot คุยกับคุณคนแรกไม่ได้) |
| `HTTP 401 Unauthorized` | Token ผิด/ขาด — คัดลอกจาก BotFather ใหม่ (คำสั่ง `/token` เพื่อดูอีกครั้ง) |
| `Conflict: terminated by other getUpdates request` | bot มี webhook ค้าง → รัน `https://api.telegram.org/bot<TOKEN>/deleteWebhook` แล้วลองใหม่ |
| ข้อความไม่ออกแต่โปรแกรมไม่ error | ตรวจ `notify_*` ใน config ไม่ได้ปิดไว้ หรือ bot ถูก block → เปิดแชทแล้วกด Start |

---

## 3. หมายเหตุความปลอดภัย

- **Cloudflare token** อยู่ใน `config.ini` (ในโฟลเดอร์เดียวกับ exe) — ห้ามแชร์ไฟล์นี้
- **Bot token** เป็นกุญแจเข้า bot — ใครได้ไปสามารถส่งข้อความปลอมในนาม bot ได้ (แต่ทำอะไรกับบัญชีของคุณไม่ได้)
- รีโวค/สร้าง token ใหม่ได้ทุกเมื่อที่หน้า Cloudflare API Tokens หรือ BotFather (`/revoke`)
