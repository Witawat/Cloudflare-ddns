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

## 3. Cloudflare Tunnel (ทางเลือก — ใช้เมื่อเปิดพอร์ตไม่ได้ / ไม่อยากเปิดพอร์ต)

Tunnel ให้บริการผ่าน Cloudflare โดยไม่ต้องใช้ IP/เปิดพอร์ต — เหมาะกับ ISP ที่แจก IP แบบ CGNAT หรือให้บริการเว็บโดยไม่อยาก port forward

### ขั้นตอน (ปัจจุบัน 2026)

1. ล็อกอิน https://dash.cloudflare.com → คลิก **Zero Trust** (เมนูซ้าย)
2. ไปที่ **Networks → Tunnels** → กด **Create a tunnel**
3. ตั้งชื่อ tunnel (เช่น `home`) → เลือกวิธีติดตั้ง **Cloudflare-managed (แนะนำ)** → ต่อไป
4. หน้า "Install and run a connector": เลือก Windows → คัดลอกคำสั่งที่ได้ ซึ่งมี token อยู่ใน `--token <eyJ...>` (ยาวมาก ขึ้นต้นด้วย `eyJ`)
   - ไม่ต้องรันคำสั่งนั้นจริง — แค่เอา token ไปวางในโปรแกรม
5. เปิด **Web UI → การ์ด Cloudflare Tunnel → "ตั้งค่า Tunnel (wizard)"** → ทำตาม 4 ขั้น:
   - วาง token → **ตรวจสอบ token** (โปรแกรมดาวน์โหลด cloudflared + ทดสอบเชื่อมต่อให้)
   - **ผูก hostname**: ใส่ชื่อ (เช่น `app`) + เลือกโดเมน + บริการ (เช่น `http://localhost:8080`) → กด **"ผูกกับ tunnel"** — โปรแกรมตั้ง DNS (CNAME) + tunnel config ให้อัตโนมัติ (ไม่ต้องแตะ dashboard) หรือเลือกจาก "record ที่มีอยู่"
   - บันทึก → tunnel เริ่มทำงาน
6. เสร็จ — เข้า `https://app.โดเมน.com` ได้เลย ไม่ต้องแตะเราเตอร์/DDNS
   - ดู/ลบ hostname ที่ผูกแล้วได้ที่ปุ่ม "ดู hostname ที่ผูกแล้ว"

### Tunnel vs DDNS

| | DDNS | Tunnel |
|---|---|---|
| ใช้ได้กับ | บริการที่ต้องรับ connection ตรง (SSH, game server) | HTTP/HTTPS บริการเว็บ |
| ต้องเปิดพอร์ต | ใช่ (port forward) | ไม่ต้องเลย |
| ใช้ได้กับ CGNAT | ❌ | ✅ |
| record ชี้ไปที่ | IP บ้านคุณ | CNAME ของ Cloudflare |
| เหมาะกับ | โฮสต์ที่ต้องการ IP ตรง | เว็บ/API ผ่าน Cloudflare |

ใช้คู่กันได้ (คนละ record) — ตัวโปรแกรมจัดการทั้งคู่

### ข้อควรรู้

- **ชื่อเดียวใช้ได้อย่างใดอย่างหนึ่ง:** A/AAAA (DDNS) หรือ CNAME (tunnel) — Cloudflare ห้ามซ้ำชื่อกัน → ใช้คนละชื่อ เช่น DDNS = `home.โดเมน.com`, tunnel = `app.โดเมน.com` (โปรแกรมตรวจให้และแจ้งเตือน)
- ผูก hostname ต้องใช้ **API token ที่มีสิทธิ์ Account > Cloudflare Tunnel > Edit** — ถ้าใช้ token แบบ Zone:DNS:Edit อย่างเดียวจะ error พร้อมคำแนะนำ วิธีเพิ่มสิทธิ์: dash.cloudflare.com → My Profile → API Tokens → Edit token → เพิ่มสิทธิ์ Account → Cloudflare Tunnel → Edit
- บริการที่ผูก (เช่น `localhost:8080`) ต้องรันอยู่ ถึงจะเข้าเว็บได้ — ถ้าเข้าไม่ได้ ตรวจว่าโปรแกรม/บริการนั้นเปิดอยู่
- Tunnel รันตาม service — หยุด service = tunnel หยุด (และ hostname นั้นเข้าไม่ได้ชั่วคราว)
- tunnel token (eyJ...) ใช้ได้จนกว่าจะ revoke — ระวังอย่าแชร์
- ใช้ DDNS กับ Tunnel คู่กันได้: DDNS สำหรับ SSH/game (ต้อง IP ตรง), Tunnel สำหรับเว็บ/API — แยก subdomain กัน

---

## 4. หมายเหตุความปลอดภัย

- **Cloudflare token / Tunnel token** อยู่ใน `config.ini` (ในโฟลเดอร์เดียวกับ exe) — ห้ามแชร์ไฟล์นี้
- **Bot token** เป็นกุญแจเข้า bot — ใครได้ไปสามารถส่งข้อความปลอมในนาม bot ได้ (แต่ทำอะไรกับบัญชีของคุณไม่ได้)
- รีโวค/สร้าง token ใหม่ได้ทุกเมื่อที่หน้า Cloudflare API Tokens หรือ BotFather (`/revoke`) และหน้า Zero Trust → Tunnels
