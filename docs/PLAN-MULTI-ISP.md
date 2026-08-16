# แผน: แยก subdomain ต่อ ISP (หลาย WAN) — Ruijie EG105GW(T) + Windows 1 NIC

> สถานะ: **รอข้อมูลเพิ่มจากผู้ใช้** (ยังไม่เริ่มแก้โค้ด) — อัปเดตเมื่อทำงานต่อ

## 1. บริบทและเป้าหมาย

- บ้านมี **3 ISP** ต่อเข้า **Ruijie EG105GW(T)** (เราเตอร์ทำเน็ตบาลานซ์ / แยกวง)
- ผู้ใช้ทำ **วงแยกไว้แล้ว** (LAN แยก 3 subnet ต่อ WAN ตัวใครตัวมัน — ไม่ใช้ load balance สลับสาย)
- **Windows Server 1 เครื่อง, NIC ใบเดียว** — ตอนนี้ต่อกับ**วงแรก (ISP A)**
- ต้องการ: subdomain ละ ISP เช่น `a.โดเมน.com` → IP ของ ISP A, `b.โดเมน.com` → ISP B, `c.โดเมน.com` → ISP C
- ต้องการรองรับ **เพิ่ม/ลด ISP ในอนาคต** โดยไม่ยุ่งกับโครงสร้าง

## 2. ข้อเท็จจริง / กับดักที่ต้องรู้ (ย้ำทุกครั้ง)

1. **Windows อยู่หลัง default gateway ของวง A** → ตรวจ IP ด้วยวิธีปกติได้แค่ IP ของ ISP A เสมอ
2. **ถ้าใช้ load balance แบบสุ่ม → IP สลับไปมา → record เด้งพัง** (ผู้ใช้แยกวงแล้ว ไม่โดนข้อนี้)
3. **ถ้า ISP ตัวใดเป็น CGNAT (IP ขึ้นต้น 100.64.x.x) → DDNS ใช้ไม่ได้กับ WAN นั้น ต้องใช้ Cloudflare Tunnel ต่อ WAN แทน**
4. provider ตรวจ IP หลายเจ้าคืน IP หลายตัว (DNS round-robin) → ถ้าจะใช้ route เจาะ ต้องจับช่วง CDN ให้ได้
5. ต้องอ่าน IP จาก Ruijie (ผู้รู้ความจริงของทุก WAN) แทนการเดาจากภายนอก

## 3. แนวทางที่เลือก (หลัก): อ่าน IP ต่อ WAN จาก Ruijie + `check_url` ต่อ record

Ruijie รู้ IP สาธารณะของทั้ง 3 WAN (หน้า WAN status / API ในตัว) — ให้โปรแกรม**อ่าน IP ต่อ WAN ตรงจากเราเตอร์** แล้วอัปเดต record ต่อ WAN:

```ini
[record:a.โดเมน.com]
zone = โดเมน.com
check_url = http://192.168.1.1/...wan1...   ; endpoint ที่คืน IP ของ WAN1

[record:b.โดเมน.com]
zone = โดเมน.com
check_url = http://192.168.1.1/...wan2...

[record:c.โดเมน.com]
zone = โดเมน.com
check_url = http://192.168.1.1/...wan3...
```

- `check_url` เว้นว่าง = ใช้ provider เดิม (พฤติกรรมเดิม ไม่กระทบผู้ใช้รายอื่น)
- ข้อแลก: ต้องหา API/endpoint ของ Ruijie (reverse หน้า admin หรือ SNMP ถ้ามี)

### แนวทางสำรอง (ถ้า API Ruijie ทำไม่ได้)

1. **route เจาะ + policy routing**: Windows `route add <IP-provider> 192.168.<B|C>.1 -p` (ต้อง inter-VLAN routing เปิดที่ Ruijie) + policy ที่ Ruijie ตาม destination → WAN เป้าหมาย — เปราะ (ตาม IP provider) แต่ไม่ต้องแก้ Ruijie มาก
2. **DDNS ต่อ WAN ใน Ruijie** (ถ้า EG105GW(T) รองรับ DDNS ต่อ interface — เช็คหน้า admin) → Cloudflare ตั้ง CNAME ตาม hostname — ไม่ต้องแก้โค้ด แต่แยกการจัดการ 2 ที่
3. **CGNAT โดน** → Cloudflare Tunnel ต่อ WAN (ฟีเจอร์ tunnel ของโปรเจกต์ใช้ได้อยู่แล้ว)

## 4. ฟีเจอร์ที่จะเพิ่มในโปรแกรม (ตอนเริ่มงาน)

### 4.1 config.py
- `RecordConfig` เพิ่ม field: `check_url` (str, default "")
- อ่านจาก section `[record:...]`: `rec_sec.get("check_url", "").strip()`
- validate: ถ้ามี ต้องเริ่มด้วย http:// หรือ https://
- ไฟล์: `cloudflare_ddns/config.py` (`RecordConfig.__init__` + ทั้ง 2 จุดอ่าน record: `reload()` / `_load_from_parser()`)

### 4.2 ip_detect.py
- ฟังก์ชัน `get_public_ip_from_url(url, version, timeout=8)` — GET URL แล้ว parse:
  - text ล้วนที่เป็น IP (trim)
  - JSON (คีย์ `ip`, `address`, `result`... ไล่ลำดับที่รู้จัก)
  - รูปแบบ `cdn-cgi/trace` style (บรรทัด `ip=...`)
- ตรวจ `ipaddress.ip_address()` + ตรง version ก่อนคืน
- กันลูป: URL ต้องเป็น http/https เท่านั้น (validate ไว้ที่ config แล้ว)

### 4.3 ddns.py
- `_sync_family(...)` รับ/ใช้ `rec.check_url`:
  - `check_url` ว่าง → `ip_detect.get_public_ip(family)` (เดิม)
  - มีค่า → `ip_detect.get_public_ip_from_url(rec.check_url, family)`
- ไหลต่อที่เหลือเหมือนเดิม (reject CF IP / cache / PATCH / notify / heartbeat)

### 4.4 webui.py
- `_cfg_to_dict` / `_dict_to_ini`: เพิ่ม `check_url` ใน records
- JS `renderRecordsEditor()`: input `check_url` ต่อแถว (placeholder: "URL ตรวจ IP (เว้น = อัตโนมัติ)")
- ตรวจ id ซ้ำ / ใช้ escapeHtml เหมือนเดิม

### 4.5 config.example.ini + docs
- ตัวอย่าง `[record:b...]` + `check_url` + คำอธิบายหลาย ISP

## 5. ข้อมูลที่ต้องรอจากผู้ใช้ (ยังค้างอยู่)

- [ ] **screenshot หน้า WAN status / หน้า admin ของ Ruijie EG105GW(T)** — ดูว่าแต่ละ WAN แสดง IP ตรงไหน, มี API/SNMP ไหม
- [ ] **ยืนยันว่า 3 ISP เป็น public IP จริง** (หน้า WAN status — ถ้า IP ขึ้นต้น `100.64.` = CGNAT)
- [ ] **IP/subnet ของวง B และ C** (เช่น 192.168.2.0/24, 192.168.3.0/24) + gateway ของแต่ละวง
- [ ] ยืนยันชื่อ subdomain ที่จะใช้ (`a.` `b.` `c.` หรือชื่อจริง)

## 6. ขั้นตอนการทำงาน (todo — ทำทีละข้อเมื่อข้อมูลครบ)

- [ ] 1. วิเคราะห์ API Ruijie: login → session → endpoint คืน IP ต่อ WAN (หรือ SNMP) — เทสต์ด้วย curl
- [ ] 2. เช็ค CGNAT ของทั้ง 3 ISP (หน้า WAN status ของ Ruijie)
- [ ] 3. config.py: เพิ่ม `check_url` ต่อ record + validate
- [ ] 4. ip_detect.py: `get_public_ip_from_url()` (text/JSON/trace style)
- [ ] 5. ddns.py: `_sync_family` ใช้ `check_url` เมื่อระบุ
- [ ] 6. webui.py: field `check_url` ในตัวแก้ record + dict/ini roundtrip
- [ ] 7. ทดสอบ: `python -m compileall -q cloudflare_ddns` + node --check JS
- [ ] 8. เทสต์ logic: mock + `dry-run` กับ config ชั่วคราว (ไม่แตะ record จริง)
- [ ] 9. เทสต์จริง: dry-run กับ `check_url` ที่อ่านจาก Ruijie → ตรวจว่า IP ตรงกับหน้า WAN status
- [ ] 10. rebuild + reinstall service (`svc-stop.cmd` → PyInstaller → `svc-reinstall.cmd`) → `sc query` = RUNNING + webui 200
- [ ] 11. docs: README / CHANGELOG / config.example.ini

## 7. การเพิ่ม/ลด ISP ในอนาคต

- **เพิ่ม ISP:** ต่อ WAN ใหม่ที่ Ruijie (วงใหม่) → หา endpoint ตรวจ IP ของ WAN นั้น → เพิ่ม `[record:d.โดเมน.com]` + `check_url` → บันทึกผ่านเว็บ — จบ ไม่แตะของเดิม
- **ลด ISP:** ลบ record นั้น (หรือปิด `ipv4/ipv6 = false`) → ปลด WAN ที่ Ruijie

## 8. หมายเหตุ

- โปรเจกต์นี้ใช้ stdlib ล้วน + pywin32 — ฟีเจอร์ใหม่ห้ามเพิ่ม dependency
- ข้อมูล runtime อยู่ข้าง exe — ไม่กระทบ
- ถ้าทำเสร็จ อัปเดต CHANGELOG เป็น 1.5.0
