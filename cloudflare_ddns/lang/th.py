"""ภาษาไทย — flat dict (key เดียวกันกับ en.py)."""

TH = {
    # ---- ข้อความทั่ว ๆ ไป / 500 ----
    "err.internal": "เกิดข้อผิดพลาดภายใน — ดู log (แถบ Log ล่าสุด) เพื่อรายละเอียด",
    "err.internal_partial": "เกิดข้อผิดพลาดภายใน — ดู log (แถบ Log ล่าสุด) เพื่อรายละเอียด (ข้อมูลบางส่วนอาจถูกบันทึกไปแล้ว — ตรวจอีกครั้ง)",
    "err.unauthorized": "unauthorized",
    "err.not_found": "ไม่พบ path",
    "err.csrf": "คำขอถูกปฏิเสธ (Origin ของเบราว์เซอร์ไม่ตรงกับหน้าเว็บนี้)",
    "err.json_bad": "JSON ผิดรูปแบบ",

    # ---- login ----
    "login.locked": "พยายามเข้าสู่ระบบบ่อยเกินไป — ล็อกชั่วคราว รออีก {remain} วิ",
    "login.wrong": "รหัสผ่านไม่ถูกต้อง",

    # ---- log ----
    "log.clear_ok": "ล้าง log แล้ว",
    "log.clear_fail": "ล้าง log ไม่ได้: {exc}",
    "log.none": "(ยังไม่มีไฟล์ log: {exc})",

    # ---- cloudflare / token / zone ----
    "token.missing": "ไม่พบ token",
    "token.missing_bot": "ไม่พบ bot token",
    "token.missing_api": "ไม่พบ API token (ตั้งค่า Cloudflare ก่อน)",
    "token.missing_api_dns": "ไม่พบ API token สำหรับแก้ DNS (ตั้งค่า Cloudflare ก่อน)",
    "zone.missing": "ไม่พบ zone",
    "records.none": "ไม่มี A/AAAA record ใน zone นี้ (จะสร้างให้เองเมื่อมี IP)",

    # ---- verify-token ----
    "verify.bad": "{exc}",
    "verify.no_zones": "{exc}",

    # ---- resolve-chat-id ----
    "chatid.error": "{error}",
    "chatid.notify_sent": "ส่งสำเร็จ",
    "chatid.test_default": "ทดสอบ",

    # ---- heartbeat-test ----
    "heartbeat.not_set": "ยังไม่ได้ตั้งค่า Healthchecks/Kuma URL — ตั้งในฟอร์มก่อนแล้วลองใหม่",
    "heartbeat.detail_ok": "{name}: สำเร็จ",
    "heartbeat.detail_fail": "{name}: ล้มเหลว ({error})",

    # ---- update-check (เว็บ) ----
    "update.tunnel_latest": "cloudflared เป็นเวอร์ชันล่าสุดแล้ว ({latest})",
    "update.tunnel_new": "มีเวอร์ชันใหม่: {current} → {latest} (กด 'อัปเดต cloudflared' ในหน้านี้)",
    "update.tunnel_none": "ยังไม่ได้ติดตั้ง cloudflared — เวอร์ชันล่าสุด: {latest}",
    "update.check_fail": "เช็คเวอร์ชันล่าสุดไม่ได้ (เน็ต?) — ลองใหม่ภายหลัง",
    "update.no_release": "ไม่พบ release ล่าสุด (tag ว่าง)",
    "update.github_err": "GitHub ตอบ {code} (ไม่มี release/rate limit)",
    "update.check_err": "เช็คไม่ได้: {exc}",

    # ---- port-scan ----
    "port.scan_forbidden": "อนุญาตให้สแกนเฉพาะ host ที่ตั้งไว้ใน config เท่านั้น",
    "port.bad_list": "รายการพอร์ตไม่ถูกต้อง (คั่นด้วย ,)",
    "port.none": "ไม่มีพอร์ตให้สแกน",
    "port.resolve_fail": "resolve {host} ไม่ได้: {exc}",
    "port.detail": "{name}",

    # ---- notify-queue ----
    "queue.telegram_not_set": "ยังไม่ได้ตั้งค่า Telegram ใน config",
    "queue.clear_ok": "ล้างคิวแล้ว",

    # ---- tunnel ----
    "tunnel.token_missing": "ไม่พบ tunnel token",
    "tunnel.token_paste_first": "กรุณาวาง tunnel token ก่อน",
    "tunnel.token_bad_format": "tunnel token ผิดรูปแบบ (ควรเป็น eyJ... ยาว ๆ จากหน้า Zero Trust)",
    "tunnel.token_no_ids": "tunnel token ไม่มี account/tunnel id (token ผิดรูปแบบ?)",
    "tunnel.api_token_no_tunnel_perm": "API token ไม่มีสิทธิ์จัดการ Tunnel (403) — ไปที่ dash.cloudflare.com → My Profile → API Tokens → Edit token ที่ใช้ → เพิ่มสิทธิ์ Account → Cloudflare Tunnel → Edit แล้วลองใหม่",
    "tunnel.need_service": "กรุณาระบุบริการ/พอร์ต เช่น http://localhost:8080 หรือ tcp://localhost:22",
    "tunnel.need_hostname": "กรุณาระบุ hostname เช่น app.โดเมน.com",
    "tunnel.hostname_invalid": "hostname ไม่ถูกต้อง (ต้องเป็น app.โดเมน.com)",
    "tunnel.conflict": "ชื่อ {hostname} มี record {rtype} อยู่แล้ว (น่าจะใช้กับ DDNS) — Cloudflare ไม่อนุญาตให้มี CNAME (tunnel) ซ้ำชื่อเดียวกับ A/AAAA — ใช้คนละชื่อ (เช่น app.โดเมน.com) หรือลบ record เดิมก่อน",
    "tunnel.conflict_check_fail": "ตรวจ DNS record ไม่ได้: {exc}",
    "tunnel.config_write_fail": "ตั้งค่า tunnel config ไม่ได้: {error}",
    "tunnel.record_create_fail": "สร้าง DNS record ไม่ได้: {exc}",
    "tunnel.record_update": "อัปเดต",
    "tunnel.record_create": "สร้าง",
    "tunnel.bound_ok": "{action} record แล้ว: {hostname}{path} → {tunnel_id}.cfargotunnel.com (เข้าผ่าน https://{hostname}{path})",
    "tunnel.read_fail": "อ่าน tunnel config ไม่ได้: {error}",
    "tunnel.unbind_no_hostname": "ไม่พบ hostname ที่จะลบ",
    "tunnel.unbind_not_found": "ไม่พบ {hostname}{path} ใน tunnel config",
    "tunnel.unbind_fail": "ลบออกจาก tunnel config ไม่ได้: {error}",
    "tunnel.unbind_dns_fail": "ลบ DNS record ไม่ได้: {exc}",
    "tunnel.unbound_ok": "เลิกผูก {hostname}{path} แล้ว",
    "tunnel.unbound_ok_del_cname": "เลิกผูก {hostname}{path} แล้ว (ลบ CNAME record ด้วย)",
    "tunnel.test_ok": "token ใช้ได้ — tunnel เชื่อมต่อ Cloudflare แล้ว (หยุดชั่วคราว รอขั้นตอนสุดท้าย)",
    "tunnel.test_fail": "token ตรวจไม่ผ่าน — cloudflared เชื่อมต่อไม่ได้ (ตรวจ token/อินเทอร์เน็ต/ไฟร์วอลล์)",
    "tunnel.sync_ok": "ซิงค์แล้ว — บันทึก hostname {count} รายการลง config",
    "tunnel.token_needs_setup": "ไม่พบ tunnel token (ตั้งค่าในฟอร์ม/ wizard ก่อน)",

    # ---- service ----
    "service.no_admin": "ไม่มีสิทธิ์ admin — เปิด webui จาก cmd/exe ที่รันเป็น admin (หรือติดตั้งเป็น service แล้วควบคุมจากเว็บนี้)",
    "service.running_inside": "เว็บนี้รันใน service อยู่แล้ว — service กำลังทำงาน (ติดตั้งอยู่แล้ว ไม่ต้องติดตั้งใหม่) ใช้ปุ่ม Restart แทน (ห้ามติดตั้งทับตัวเอง: จะลบ service ที่รันอยู่ทิ้งแล้วหยุดกลางคัน)",
    "service.already_installed": "service ติดตั้งอยู่แล้ว — ใช้ปุ่ม Restart หรือถอนก่อนถ้าอยากติดตั้งใหม่",
    "service.install_fail": "ติดตั้งไม่ได้: {exc}",
    "service.install_ok": "{message} — กด Restart service เพื่อเริ่ม",
    "service.not_installed": "ยังไม่ได้ติดตั้ง service",
    "service.not_installed_start": "ยังไม่ได้ติดตั้ง service — กด 'ติดตั้ง service' ก่อน",
    "service.uninstall_running": "service กำลังทำงาน — ถอนตอนนี้จะตัดการเชื่อมต่อหน้าเว็บนี้ทันที (เพราะเว็บนี้รันใน service) — ใช้ uninstall.bat หรือรัน dist\\cloudflare-ddns.exe stop แล้วตามด้วย remove แทน",
    "service.remove_fail": "ถอนไม่ได้: {exc}",
    "service.remove_ok": "{message}",
    "service.already_running": "service กำลังทำงานอยู่แล้ว",
    "service.start_fail": "เริ่มไม่ได้: {exc}",
    "service.start_ok": "{message}",
    "service.stop_fail": "หยุดไม่ได้: {exc}",
    "service.stop_ok": "{message}",
    "service.stop_inside": "เว็บนี้รันใน service — หยุดตอนนี้หน้าเว็บจะหายไปและไม่กลับมาเอง (service หยุด = ไม่มีตัวเริ่มใหม่) — ให้ใช้คำสั่ง dist\\cloudflare-ddns.exe stop แทน",
    "service.restart_started": "กำลัง restart service — หน้าเว็บจะหลุดชั่วครู่ แล้วกลับมาเอง",

    # ---- ddns-run ----
    "ddns.busy": "กำลังตรวจรอบก่อนหน้าอยู่ ยังไม่เสร็จ — รอสักครู่แล้วลองใหม่",
    "ddns.running": "กำลังตรวจ DDNS — สถานะจะอัปเดตให้อัตโนมัติ",

    # ---- open-data-folder ----
    "folder.inside_service": "เว็บนี้รันใน service — ไม่สามารถเปิดโฟลเดอร์จาก session ของคุณได้ คัดลอก path ให้แล้ว: {path} (กด Win+R → วาง → Enter)",
    "folder.open_fail": "เปิดโฟลเดอร์ไม่ได้: {exc}",
    "folder.open_ok": "เปิดโฟลเดอร์ข้อมูลแล้ว ({path})",

    # ---- notify-test ----
    "notify_test.text": "✅ ทดสอบการแจ้งเตือนจาก Cloudflare DDNS (Web UI)",
    "notify_test.sent": "ส่งสำเร็จ — ตรวจใน Telegram",

    # ---- nat report (ip_detect) ----
    "nat.unknown": "ตรวจ NAT ไม่ได้",
    "nat.cgnat_ip": "IP อยู่ในช่วง CGNAT (100.64.0.0/10) — ISP แจก IP ร่วมกันให้หลายบ้าน DDNS ไม่สามารถใช้งานได้ ควรใช้ Cloudflare Tunnel หรือ IPv6 แทน",
    "nat.private_ip": "IP ที่ตรวจได้เป็น IP ภายใน (private) — อาจต่อผ่าน VPN/proxy หรือผิดปกติ DDNS จะอัปเดต IP นี้ไป ซึ่งไม่ใช่ IP ที่คนนอกเข้าถึงได้",
    "nat.cgnat_trace": "tracert เห็น 100.64.0.0/10 หลัง WAN ของเราโดยตรง — อยู่หลัง CGNAT ของ ISP DDNS ไม่สามารถใช้งานได้ ควรใช้ Cloudflare Tunnel หรือ IPv6 แทน",
    "nat.double_nat": "เป็น NAT ส่วนตัวในบ้าน (ซ้อน {layers} ชั้น) — DDNS ใช้งานได้ตามปกติ",
    "nat.mismatch": "IP ที่เห็นจาก provider ({public}) ไม่ตรงกับที่ STUN เห็น ({stun}) — สัญญาณว่า IP อาจไม่เสถียร/ผ่านตัวกลางหลายชั้น ตรวจสอบเองเพิ่มเติม",
    "nat.mismatch_dyn": " และ mapped port เปลี่ยนทุกครั้ง (NAT แบบ dynamic)",
    "nat.public": "IP สาธารณะตรงปกติ (ไม่มี NAT ซ้อน หรือ NAT แบบ 1:1) — DDNS ใช้งานได้ตามปกติ (ถ้ามีเราเตอร์ที่บ้าน อย่าลืมตั้ง port forward สำหรับบริการภายใน)",
    "nat.public_symmetric": " หมายเหตุ: mapped port เปลี่ยนทุกครั้ง (symmetric mapping) — port forward ต้องตั้ง static mapping ที่เราเตอร์",
    "nat.unknown_stun": "ตรวจ STUN ไม่ได้ — IP เป็น public แต่ไม่สามารถยืนยัน NAT ได้",
}
