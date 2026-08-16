# คู่มือ Cloudflare Tunnel (ฉบับละเอียด)

> ใช้เมื่อต้องการให้บริการเว็บ/API ผ่าน Cloudflare **โดยไม่ต้องเปิดพอร์ต** และไม่พึ่ง IP ตรง — เหมาะกับ:
> - ISP แจก IP แบบ **CGNAT** (DDNS ใช้ไม่ได้)
> - ไม่อยากแตะเราเตอร์ / ไม่เปิด port forward
> - ให้บริการหลายเว็บจากเครื่องเดียว

---

## 1. สร้าง tunnel + หา token (ที่ Cloudflare)

1. ล็อกอิน https://dash.cloudflare.com → คลิก **Zero Trust** (เมนูซ้าย)
2. **Networks → Tunnels** → **Create a tunnel**
3. ตั้งชื่อ (เช่น `home`) → เลือก **Cloudflare-managed (แนะนำ)** → ต่อไป
4. หน้า "Install and run a connector": เลือก **Windows** → จะเห็นคำสั่งแบบ:
   ```
   cloudflared service install eyJhIjoi...
   ```
   คัดลอกเฉพาะส่วน **`eyJ...` (token ยาว ๆ)** — **ไม่ต้องรันคำสั่งนั้นจริง** แค่เอา token ไปวางในโปรแกรม
   - token ปัจจุบันของ Cloudflare เป็นแบบ **1 ส่วน** (payload ล้วน) — โปรแกรมรองรับทั้งแบบเก่า (JWT 3 ส่วน) และแบบใหม่

## 2. เตรียม API token (สำหรับผูก hostname)

การผูก hostname โปรแกรมจะตั้ง DNS (CNAME) + tunnel config ให้เองผ่าน Cloudflare API — token ต้องมีสิทธิ์:
- **Zone → DNS → Edit** (สำหรับ DDNS อยู่แล้ว)
- **Account → Cloudflare Tunnel → Edit** (เพิ่ม: dash.cloudflare.com → My Profile → API Tokens → Edit token → Add more permissions → Account → Cloudflare Tunnel → Edit)

> ถ้า token ไม่มีสิทธิ์ Tunnel — หน้าเว็บจะบอกวิธีเพิ่มให้ทันที (error 403 พร้อมคำแนะนำ)

## 3. ตั้งค่าในโปรแกรม (wizard ในเว็บ — 4 ขั้น)

เปิดหน้าเว็บ → การ์ด **Cloudflare Tunnel** → **"ตั้งค่า Tunnel (wizard)"**:

| ขั้น | ทำอะไร |
|---|---|
| 1. คำนำ | อธิบาย tunnel เหมาะกับใคร |
| 2. วาง token | วาง token จากข้อ 1 → **"ตรวจสอบ token"** (โปรแกรมดาวน์โหลด cloudflared + ทดสอบเชื่อมต่อจริง ~5-15 วิ) — ผ่าน = ไปต่อ |
| 3. ผูก hostname | ใส่ชื่อ + โดเมน + ชนิด + บริการ/พอร์ต → **"ผูกกับ tunnel"** → โปรแกรมสร้าง DNS CNAME + tunnel config ให้อัตโนมัติ |
| 4. สรุป | บันทึก config + tunnel เริ่มทำงาน |

เสร็จ — เข้า `https://ชื่อ.โดเมน.com` ได้ทันที (รอ DNS propagate 1-2 นาที)

## 4. เลือก "ชนิด" ให้ตรงกับบริการ (สำคัญ!)

| ชนิด | ใช้กับ | ตัวอย่างช่องบริการ |
|---|---|---|
| **HTTP** | เว็บธรรมดา (ไม่ใช่ SSL) | `http://localhost:8080` |
| **HTTPS** | พอร์ต SSL เช่น 443/8443 | `https://localhost:443` |
| **TCP** | SSH / RDP / game server | `tcp://localhost:22` |
| **UDP** | game / VPN (เช่น WireGuard) | `udp://localhost:51820` |

> ⚠️ **พอร์ต SSL (443/8443) ต้องเลือก HTTPS + `https://localhost:443`** — ถ้าเลือก HTTP จะเจอ:
> ```
> Bad Request — Your browser sent a request that this server could not understand.
> Reason: You're speaking plain HTTP to an SSL-enabled server port.
> ```
> (cloudflared ส่ง plain HTTP เข้าไปที่พอร์ต TLS → เซิร์ฟเวอร์ปฏิเสธ)

**หลายพอร์ตต่อชื่อเดียว** — ใช้ Path: `app.โดเมน.com` → 8080 และ `app.โดเมน.com/api` → 3000 (ผูก 2 รายการ ชื่อเดียวกัน path ต่างกัน)

## 5. จัดการ hostname หลังผูกแล้ว

การ์ด Tunnel → **"ดู hostname ที่ผูกแล้ว"** — ตารางแสดง hostname / ชนิด / บริการ:

| ปุ่ม | ทำอะไร |
|---|---|
| **แก้ไข** | โหลดค่าปัจจุบันลงฟอร์ม → เปลี่ยนชนิด/บริการ/path → กด "ผูกกับ tunnel" = **แทนที่ของเดิม** (ไม่ต้องลบแล้วเพิ่มใหม่) |
| **×** (เลิกผูก) | ลบ hostname ออกจาก tunnel + ลบ DNS CNAME ให้อัตโนมัติ |

**"ซิงค์จาก Cloudflare"** — ดึง hostname ที่ผูกทั้งหมดจาก Cloudflare มาบันทึกใน config (ใช้เมื่อผูกที่ dashboard เองแล้วอยากให้ config ตรง)

**"+ เพิ่ม hostname"** — ผูกด่วนโดยไม่ต้องเปิด wizard (ต้องมี tunnel token ใน config แล้ว)

**ชื่อ subdomain ใหม่ที่ไม่เคยมีก็กรอกได้เลย** — โปรแกรมสร้าง DNS record ให้อัตโนมัติ (ห้ามซ้ำชื่อกับ DDNS A/AAAA — โปรแกรมตรวจให้และแจ้งเตือน)

## 6. การทำงานประจำวัน

- **tunnel รันตาม service** — เปิด `tunnel_enabled = true` ในฟอร์ม → service เริ่ม = tunnel เริ่ม (เริ่มเองตอน boot)
- **สถานะ**: การ์ด Tunnel — ปิด/เปิดใช้งาน · cloudflared ติดตั้งไหม (เวอร์ชัน) · รันอยู่ (pid)
- **ปุ่ม**: เริ่ม / หยุด / ดาวน์โหลด cloudflared (ถ้าหาย)
- **แจ้งเตือน Telegram**: เริ่ม tunnel (พร้อมรายชื่อ hostname) / หยุด / ดาวน์โหลด cloudflared — ส่งอัตโนมัติ
- **log**: ดูในหน้าเว็บ (Log ล่าสุด) — ค้นหา `Cloudflare Tunnel` / `cloudflared`

## 7. Tunnel + DDNS ใช้คู่กันได้

| | DDNS | Tunnel |
|---|---|---|
| ใช้กับ | SSH / game / บริการรับ connection ตรง | เว็บ / API |
| ต้องเปิดพอร์ต | ใช่ (port forward) | ไม่ต้อง |
| CGNAT | ❌ | ✅ |
| record | A/AAAA → IP บ้าน | CNAME → tunnel |

ใช้คนละ subdomain: `ssh.โดเมน.com` (DDNS) + `app.โดเมน.com` (tunnel) — โปรแกรมจัดการทั้งคู่

## 8. แก้ปัญหาที่พบบ่อย

| อาการ | วิธีแก้ |
|---|---|
| token ตรวจไม่ผ่าน (cloudflared ตายทันที) | token ผิด/คัดลอกไม่ครบ · เน็ต/ไฟร์วอลล์ต้องออก `region1.v2.argotunnel.com:7844` ได้ · กด "ดาวน์โหลด cloudflared" ใหม่ |
| ผูกแล้วเข้าเว็บไม่ได้ | บริการ (localhost:port) ต้องรันอยู่ · tunnel กำลังรัน (การ์ด) · DNS propagate 1-2 นาที · ตรวจ "ดู hostname ที่ผูกแล้ว" ว่าชนิด/บริการถูกต้อง |
| Bad Request (SSL port) | เปลี่ยนชนิดเป็น **HTTPS** + `https://localhost:443` (ดูข้อ 4) |
| error "tunnel token ผิดรูปแบบ" | อัปเดต exe เป็นเวอร์ชันล่าสุด (โปรแกรมรองรับ token รูปแบบใหม่ 1 ส่วน) — หรือ token คัดลอกไม่ครบ |
| error สิทธิ์ (403) ตอนผูก | เพิ่มสิทธิ์ **Account → Cloudflare Tunnel → Edit** ให้ API token (ข้อ 2) |
| error "ชื่อนี้มี record A อยู่แล้ว" | ชื่อเดียวใช้ได้อย่างใดอย่างหนึ่ง — ใช้คนละชื่อหรือลบ record เดิม |
| ผูกซ้ำแล้ว error 1056 | อัปเดต exe เป็น v1.7.11+ (แก้ rule 404 ซ้ำ) |
| tunnel ไม่เริ่มตอน boot | `tunnel_enabled = true` + token ไม่ว่าง + ดู log |

## 9. หมายเหตุความปลอดภัย

- **tunnel token (eyJ...) = กุญแจเข้า tunnel** — ใครได้ไปสามารถควบคุม tunnel ของคุณได้ — อย่าแชร์ (revoke ได้ที่ Zero Trust → Tunnels → Configure → Delete/Regenerate token)
- API token ควรจำกัดสิทธิ์เฉพาะที่จำเป็น (Zone DNS + Tunnel Edit) + เฉพาะโดเมนที่ใช้
- tunnel เข้าได้เฉพาะ hostname ที่ผูกไว้เท่านั้น — ไม่มีใครเข้าถึง localhost:port ของคุณผ่าน tunnel โดยตรง

---

*อัปเดต: v1.7.12 — ดูประวัติเต็มใน [CHANGELOG](../CHANGELOG.md)*
