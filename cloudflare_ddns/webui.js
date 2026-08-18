const $ = (id) => document.getElementById(id);

/* ============ i18n (ไทย/อังกฤษ) ============ */

const I18N = {
  th: {
    "lang.name": "ไทย",
    "toast.timeout": "timeout — server ไม่ตอบกลับภายใน {s} วิ (ลองใหม่ หรือดู log)",
    "toast.network": "เชื่อมต่อ server ไม่ได้ (network error) — ลองใหม่ หรือดู log",
    "eye.toggle": "แสดง/ซ่อนรหัส",
    "pill.config_incomplete": "ตั้งค่าไม่ครบ",
    "pill.problem": "มีปัญหา",
    "pill.ready": "พร้อมใช้งาน",
    "status.never_run": "ยังไม่เคยรัน",
    "status.no_ip": "ยังไม่มีข้อมูล IP (รอรอบแรกของ service)",
    "status.no_config": "ยังไม่ได้ตั้งค่า config — ทำตาม wizard หรือส่วน \"ตั้งค่า\" ให้ครบก่อน (IP จะถูกอัปเดตให้อัตโนมัติ)",
    "status.unreadable": "อ่านสถานะไม่ได้",
    "record.copy_name": "กดเพื่อคัดลอกชื่อ",
    "record.copy_ip": "กดเพื่อคัดลอก IP",
    "record.not_set": "ยังไม่ตั้งค่า",
    "record.updated_at": "อัปเดตล่าสุด ",
    "tg.ready": "พร้อมใช้งาน",
    "tg.queue_waiting": "คิวรอส่ง {n} ข้อความ",
    "tg.not_set": "ยังไม่ได้ตั้งค่า",
    "tg.need_token": "ใส่ token ในฟอร์มด้านล่าง หรือรัน setup",
    "api.stats": "Cloudflare API: เรียก {calls} ครั้ง · error {errors} · โดน rate limit {rl} (นับตั้งแต่เริ่ม)",
    "history.empty": "ยังไม่มีประวัติ (รอการอัปเดตครั้งแรก)",
    "history.time": "เวลา",
    "history.record": "record",
    "history.action": "การกระทำ",
    "history.ip": "IP",
    "history.updated": "อัปเดต IP",
    "history.created": "สร้าง record",
    "copy.copied": "คัดลอก {text} แล้ว",
    "copy.failed": "คัดลอกไม่ได้: {err}",
    "svc.in_service": "รันใน service (มีสิทธิ์ระบบ) — ติดตั้ง/ถอน/หยุดต้องใช้ .bat ภายนอก",
    "svc.standalone_admin": "รันแบบ standalone · มีสิทธิ์ admin — ควบคุม service ได้",
    "svc.standalone_no_admin": "รันแบบ standalone · ไม่มีสิทธิ์ admin — ปุ่มควบคุม service ใช้ไม่ได้ (เปิด exe/cmd เป็น admin)",
    "svc.need_admin": "ต้องเปิด webui ด้วยสิทธิ์ admin",
    "svc.not_installed": "ยังไม่ได้ติดตั้ง service — กด \"ติดตั้ง service\" (ต้อง admin)",
    "svc.state.running": "กำลังทำงาน",
    "svc.state.stopped": "หยุดอยู่",
    "svc.state.starting": "กำลังเริ่ม",
    "svc.state.stopping": "กำลังหยุด",
    "svc.state.resuming": "กำลังเริ่มต่อ",
    "svc.state.pausing": "กำลังพัก",
    "svc.state.paused": "พักอยู่",
    "svc.installed_ok": "ติดตั้งแล้ว — {label}",
    "svc.unreadable": "อ่านสถานะไม่ได้: {err}",
    "fail_prefix": "ไม่สำเร็จ: {msg}",
    "err_prefix": "error: {err}",
    "update.new": "มี v{ver} ใหม่",
    "folder.copied": "{msg} — คัดลอก path ลงคลิปบอร์ดแล้ว (Win+R → วาง → Enter)",
    "cfg.load_fail": "โหลด config ไม่ได้: {err}",
    "recs.empty": "ยังไม่มี record — กด \"เพิ่ม record\" ข้างล่าง",
    "rec.placeholder_name": "home (เติม .zone ให้) / @ / *.zone (wildcard)",
    "rec.placeholder_zone": "zone (เว้น = เดาให้)",
    "rec.proxy_title": "ผ่าน orange cloud ของ Cloudflare",
    "rec.ttl_title": "TTL (วินาที)",
    "rec.del_title": "ลบ record",
    "save.dup": "record ซ้ำ: {name} (กรอกชื่อซ้ำกัน)",
    "save.ok": "บันทึกสำเร็จ — มีผลในรอบถัดไป",
    "save.pw_removed": "ลบรหัสผ่านหน้าเว็บแล้ว — เข้าเว็บได้โดยไม่ต้อง login",
    "save.pw_set": "ตั้งรหัสผ่านหน้าเว็บแล้ว — กำลังเข้าสู่ระบบใหม่",
    "save.port_changed": "เปลี่ยนพอร์ตหน้าเว็บแล้ว — ต้อง restart service (dist\\cloudflare-ddns.exe restart) เพื่อให้มีผล",
    "save.fail": "บันทึกไม่ได้: {err}",
    "ip.checking": "ตรวจ…",
    "ip.not_found4": "ไม่พบ (IPv4)",
    "ip.none6": "ไม่มี (IPv6)",
    "ip.read_fail": "อ่านไม่ได้: {err}",
    "zone.need": "กรุณาใส่ zone ของ record ก่อน",
    "load.records_fail": "โหลดไม่ได้: {msg}",
    "load.no_records": "ไม่มี A/AAAA record ใน zone นี้ (จะสร้างให้เองเมื่อมี IP)",
    "load.pick_record": "— เลือก record ที่มีอยู่ —",
    "scan.no_host": "ยังไม่มี host ให้สแกน (ตั้ง record ก่อน)",
    "scan.no_records": "— ยังไม่มี record ใน config —",
    "scan.scanning": "กำลังสแกน {host} ...",
    "scan.status_open": "เปิด",
    "scan.status_filtered": "ไม่มีตอบ (ไฟร์วอลล์?)",
    "scan.status_closed": "ปิด",
    "scan.header_port": "พอร์ต",
    "scan.header_service": "บริการ",
    "scan.header_status": "สถานะ",
    "scan.summary": "{host} → {ip} · เปิด {open} · ปิด {closed} · ไม่มีตอบ {filtered}",
    "log.session_expired": "session หมดอายุ — กดรีเฟรชหน้าเว็บ (F5/Ctrl+R) เพื่อเข้าสู่ระบบใหม่ แล้วลองอีกครั้ง",
    "log.read_fail_http": "อ่าน log ไม่ได้ (HTTP {status}) — รีเฟรชหน้าเว็บแล้วลองใหม่",
    "log.read_fail": "อ่าน log ไม่ได้: {err}",
    "log.clear_confirm": "ล้างไฟล์ log ทั้งหมด?",
    "log.clear_fail": "ล้างไม่สำเร็จ: {msg}",
    "tunnel.disabled": "ปิดใช้งาน (ตั้งค่าในฟอร์มด้านล่าง)",
    "tunnel.not_installed": "cloudflared ยังไม่ติดตั้ง",
    "tunnel.running": "รันอยู่ (pid {pid})",
    "tunnel.not_running": "ยังไม่รัน",
    "tunnel.unreadable": "อ่านสถานะไม่ได้: {err}",
    "tunnel.loading": "กำลังโหลด…",
    "tunnel.no_token": "ยังไม่ได้ตั้งค่า tunnel token (ใช้ wizard ตั้งค่า)",
    "tunnel.no_hostname": "ยังไม่มี hostname ผูกกับ tunnel — ใช้ \"ตั้งค่า Tunnel (wizard)\" หรือ \"+ เพิ่ม hostname\"",
    "tunnel.header_hostname": "hostname",
    "tunnel.header_type": "ชนิด",
    "tunnel.header_service": "บริการ",
    "tunnel.edit_title": "แก้ไข map นี้ (ผูกซ้ำ = แทนที่)",
    "tunnel.edit": "แก้ไข",
    "tunnel.unbind_title": "เลิกผูก",
    "tunnel.hint": "หลาย port ต่อชื่อเดียว: ผูก path ต่างกัน (เช่น /api → 3000, / → 8080) · TCP/UDP เลือกชนิดได้ · \"แก้ไข\" = ผูกซ้ำด้วยค่าที่ตั้งใหม่ (แทนที่ของเดิม)",
    "tunnel.unbind_confirm": "เลิกผูก {host}{path}?",
    "tunnel.loading_domains": "— กำลังโหลดโดเมน… —",
    "tunnel.no_zone_perm": "— ใส่โดเมนไม่ได้ (API token ไม่มีสิทธิ์) —",
    "tunnel.load_domains_fail": "— โหลดโดเมนไม่ได้ —",
    "tunnel.edit_msg": "แก้ไข {host}{path} — เปลี่ยนค่าด้านบนแล้วกด \"ผูกกับ tunnel\" (แทนที่ของเดิม)",
    "tunnel.no_token_bind": "ยังไม่ได้ตั้งค่า tunnel token (ใช้ wizard ก่อน)",
    "tunnel.need_name_domain": "กรุณาใส่ชื่อและโดเมน",
    "tunnel.binding": "กำลังผูก...",
    "tunnel.sync_need_token": "ยังไม่ได้ตั้งค่า tunnel token (ใช้ wizard ก่อน)",
    "tunnel.action_start": "เริ่ม tunnel",
    "tunnel.action_stop": "หยุด tunnel",
    "tunnel.action_download": "ดาวน์โหลด",
    "tunnel.show_log": "ดู log tunnel",
    "tunnel.log_title": "Log ของ cloudflared (tunnel.log)",
    "tg.test_ok": "ส่งข้อความทดสอบสำเร็จ — ตรวจใน Telegram",
    "tg.test_fail": "ส่งไม่สำเร็จ: {msg}",
    "tg.queue_empty": "คิวว่าง — ไม่มีข้อความค้างส่ง",
    "tg.queue_header_msg": "ข้อความ",
    "tg.queue_summary": "รวม {n} ข้อความ — กด \"ลองส่งใหม่\" เพื่อส่งทันที หรือ \"ล้างคิว\" เพื่อทิ้ง",
    "tg.queue_read_fail": "อ่านคิวไม่ได้: {err}",
    "tg.flush_ok": "ส่งใหม่ {sent} ข้อความ (เหลือค้าง {failed})",
    "tg.clear_confirm": "ล้างข้อความค้างส่งทั้งหมดในคิว?",
    "tg.clear_ok": "ล้างคิวแล้ว",
    "wz.back": "← ย้อนกลับ",
    "file.load_fail": "โหลดไฟล์ config ไม่ได้: {err}",
    "file.save_ok": "บันทึกไฟล์สำเร็จ — มีผลในรอบถัดไป",
    "setup.check_fail": "โหลดไม่ได้: {msg}",
    "heartbeat.test_fail": "ทดสอบ heartbeat ไม่ได้: {err}",
    "update.check_fail": "เช็คอัปเดตไม่ได้: {err}",
    "cfg.export_fail": "ดาวน์โหลด config ไม่ได้: {err}",
    "cfg.import_ok": "นำเข้า config สำเร็จ — {msg}",
    "cfg.import_fail": "นำเข้าไม่สำเร็จ: {msg}",
    "cfg.import_err": "นำเข้า config ไม่ได้: {err}",
    "svc.install_confirm": "ติดตั้ง Windows Service 'CloudflareDDNS'? (เริ่มอัตโนมัติตอน boot)",
    "svc.restart_confirm": "Restart Windows Service? — หน้าเว็บนี้จะหลุดชั่วครู่แล้วกลับมาเอง",
    "svc.start_confirm": "เริ่ม Windows Service 'CloudflareDDNS'?",
    "svc.stop_confirm": "หยุด Windows Service 'CloudflareDDNS'? (หน้าเว็บนี้จะไม่กลับมาเอง)",
    "svc.uninstall_confirm": "ถอนการติดตั้ง Windows Service 'CloudflareDDNS'?",
    "svc.uninstall_confirm2": "ยืนยันอีกครั้ง — ถอน service จริง ๆ? (config/state/ข้อมูลไม่ถูกลบ)",
    "pw.clear_hint": "จะลบรหัสผ่านเมื่อกดบันทึก — เข้าเว็บได้โดยไม่ต้อง login",
    "heartbeat.test": "Heartbeat: {msg}",
    "ddns.busy": "กำลังตรวจรอบก่อนหน้าอยู่ ยังไม่เสร็จ — รอสักครู่แล้วลองใหม่",
    "ddns.running": "กำลังตรวจ DDNS — สถานะจะอัปเดตให้อัตโนมัติ",
    "log.no_log": "(ยังไม่มีไฟล์ log: {exc})",

    "twz.title1": "Tunnel คืออะไร ทำไมต้องใช้",
    "twz.sub1": "Cloudflare Tunnel เชื่อมต่อเครื่องของคุณกับ Cloudflare โดยตรง — คนเข้าบริการของคุณผ่าน Cloudflare โดยไม่ต้องเปิดพอร์ตที่เราเตอร์ และไม่ต้องพึ่ง IP สาธารณะ",
    "twz.suit_title": "เหมาะกับ:",
    "twz.suit_li": ["ISP แจก IP แบบ CGNAT (DDNS ใช้ไม่ได้)", "ไม่อยากเปิด port forward ที่เราเตอร์", "ให้บริการเว็บ/API ผ่าน Cloudflare"],
    "twz.start": "เริ่มตั้งค่า →",
    "twz.step1_title": "ขั้นตอนที่ 1: ใส่ Tunnel Token",
    "twz.step1_sub": "สร้างฟรีจาก Cloudflare Zero Trust — กดปุ่มด้านล่างเพื่อเปิดหน้า และทำตามวิธีทำ:",
    "twz.open_zt": "เปิด Zero Trust ↗",
    "twz.how_token": "ดูวิธีหา token",
    "twz.token_label": "Tunnel Token (แสดงข้อความเต็ม ไม่ซ่อน)",
    "twz.token_ph": "eyJhIjoi... (ยาว)",
    "twz.token_steps_title": "วิธีหา token (ทีละขั้น):",
    "twz.token_step_li": ["กดปุ่ม “เปิด Zero Trust” แล้วล็อกอิน", "เมนูซ้าย: Networks → Tunnels → Create a tunnel", "ตั้งชื่อ (เช่น home) → เลือกวิธี Cloudflare-managed → ต่อไป", "กดคัดลอก token จากคำสั่ง install (ส่วน --token eyJ...) — ไม่ต้องรันคำสั่งนั้นจริง", "วาง token ในช่องด้านบน แล้วกด ตรวจสอบ token"],
    "twz.verify": "ตรวจสอบ token →",
    "twz.hide_steps": "ซ่อนวิธีทำ",
    "twz.need_paste": "กรุณาวาง tunnel token ก่อน",
    "twz.checking": "กำลังตรวจสอบ (ดาวน์โหลด cloudflared ถ้ายังไม่มี + ทดสอบเชื่อมต่อ ~5 วิ)...",
    "twz.check_fail": "{msg} (ลองกด “ดูวิธีหา token”)",
    "twz.step2_title": "ขั้นตอนที่ 2: ผูกเว็บ (hostname) กับ tunnel",
    "twz.step2_sub": "ระบุชื่อเว็บและบริการในเครื่อง — โปรแกรมตั้งค่าให้อัตโนมัติ (สร้าง DNS + ตั้ง tunnel config) ไม่ต้องไปทำที่ dashboard",
    "twz.sub_label": "ชื่อ (subdomain)",
    "twz.sub_ph": "app (ใหม่ก็ได้ เช่น nas)",
    "twz.sub_hint": "ชื่อใหม่ที่ไม่เคยมีก็ได้ — สร้าง DNS ให้อัตโนมัติ",
    "twz.domain_label": "โดเมน",
    "twz.path_label": "Path (ไม่บังคับ — ใช้หลาย port ต่อชื่อเดียว เช่น /api)",
    "twz.path_ph": "/api (เว้น = ทุก path)",
    "twz.type_label": "ชนิด",
    "twz.type_tcp": "TCP (เช่น SSH)",
    "twz.type_udp": "UDP (เช่น game/VPN)",
    "twz.service_label": "บริการ/พอร์ต",
    "twz.service_hint": "💡 เลือกชนิดให้ตรงกับบริการ: <b>HTTP</b> = เว็บธรรมดา (เช่น <span class=\"mono\">http://localhost:8080</span>) · <b>HTTPS</b> = พอร์ต SSL เช่น 443/8443 (ต้องเป็น <span class=\"mono\">https://localhost:443</span> — ถ้าผูกเป็น http จะเจอ \"Bad Request\") · <b>TCP/UDP</b> = SSH/game/VPN (เช่น <span class=\"mono\">tcp://localhost:22</span>) · ใส่ <b>IP ใน LAN</b> ได้ด้วย (private hostname — เช่น <span class=\"mono\">http://192.168.1.50:3000</span>) แต่ cloudflared ต้องอยู่ใน LAN เดียวกับ service",
    "twz.load_records": "เลือกจาก record ที่มีอยู่",
    "twz.bound_title": "ผูกกับ tunnel แล้ว",
    "twz.binding_btn": "ผูกกับ tunnel",
    "twz.example": "ตัวอย่าง: ชื่อ <b>app</b> + โดเมน <b>makerwitawat.com</b> + บริการ <b>http://localhost:8080</b> → เข้าได้ที่ <b>https://app.makerwitawat.com</b> — <b>ชื่อ subdomain ใหม่ที่ไม่เคยมีก็กรอกได้เลย</b> โปรแกรมสร้าง DNS record ให้อัตโนมัติ (ผูกแล้วแก้ภายหลังได้ในฟอร์ม/แดชบอร์ด)",
    "twz.next": "ต่อไป →",
    "twz.need_name": "กรุณาใส่ชื่อและเลือกโดเมน",
    "twz.binding": "กำลังผูก {host}{path} กับ tunnel...",
    "twz.pick_record": "— เลือก record —",
    "twz.step3_title": "ขั้นตอนที่ 3: บันทึกและเริ่ม tunnel",
    "twz.step3_sub": "พร้อมใช้งาน — บันทึก config และเริ่ม tunnel เลย:",
    "twz.token_ok": "Token: ตรวจสอบผ่านแล้ว ✔<br>",
    "twz.cf_ready": "cloudflared: พร้อม (ดาวน์โหลดให้อัตโนมัติถ้ายังไม่มี)<br>",
    "twz.autostart": "เริ่มอัตโนมัติ: เปิด (ตอน service เริ่ม)",
    "twz.save_start": "บันทึกและเริ่ม tunnel",
    "twz.saving": "กำลังบันทึก...",
    "twz.save_fail": "บันทึกไม่สำเร็จ: {msg}",
    "twz.done": "ตั้งค่า Tunnel เสร็จ — {msg}",
    "twz.save_but_start_fail": "บันทึกแล้ว แต่เริ่ม tunnel ไม่ได้: {msg}",
    "twz.no_bound": "ยังไม่มี — ผูกจากข้างบนได้เลย",

    "wz.title": "ยินดีต้อนรับ",
    "wz.sub1": "โปรแกรมจะตรวจหา IP สาธารณะของคุณ แล้วอัปเดต DNS record บน Cloudflare ให้อัตโนมัติเมื่อ IP เปลี่ยน ขั้นตอนทั้งหมด 5 ขั้น สั้น ๆ แค่นี้",
    "wz.start": "เริ่มตั้งค่า →",
    "wz.step1_title": "ขั้นตอนที่ 1: ใส่ API token ของ Cloudflare",
    "wz.step1_sub": "token ใช้สิทธิ์แก้ DNS ของคุณเท่านั้น สร้างได้ฟรี เปิดหน้านี้แล้วทำตามขั้นด้านล่าง:",
    "wz.open_token": "เปิดหน้าสร้าง token ↗",
    "wz.how_token": "ดูวิธีหา token",
    "wz.token_steps_title": "วิธีหา token (ทีละขั้น):",
    "wz.token_step_li": ["กดปุ่ม “เปิดหน้าสร้าง token” แล้วล็อกอิน Cloudflare", "กดปุ่มสีส้ม Create Token", "เลือก template ชื่อ Edit zone DNS แล้วกด Use template", "ในช่อง Zone Resources เลือก Include → Specific zone → เลือกโดเมนของคุณ", "กด Continue to summary → Create Token", "คัดลอก token ทันที (แสดงครั้งเดียว ขึ้นต้นด้วย cfut_) แล้ววางในช่องด้านบน"],
    "wz.verify": "ตรวจสอบ token →",
    "wz.hide_steps": "ซ่อนวิธีทำ",
    "wz.need_token": "กรุณาวาง API token ก่อน",
    "wz.checking_token": "กำลังตรวจสอบ token...",
    "wz.verify_fail": "ตรวจสอบไม่ผ่าน: {msg} (ลองกด “ดูวิธีหา token”)",
    "wz.server_err": "ติดต่อเซิร์ฟเวอร์ไม่ได้: {err}",
    "wz.step2_title": "ขั้นตอนที่ 2: เลือกโดเมน (zone) และ record",
    "wz.step2_sub": "เลือกโดเมน แล้วระบุชื่อ record — ใส่แค่ชื่อสั้น ๆ ก็ได้ (เช่น home) โปรแกรมเติม .โดเมน ให้อัตโนมัติ ส่วน @ คือหน้าหลักของโดเมน",
    "wz.zone_label": "Zone (โดเมน)",
    "wz.load_records": "โหลดชื่อ record ที่มีอยู่จาก Cloudflare",
    "wz.rec_title": "Record ที่จะอัปเดต",
    "wz.add_record": "+ เพิ่ม record",
    "wz.next": "ต่อไป →",
    "wz.need_zone": "กรุณาเลือก zone ก่อน",
    "wz.need_rec_name": "กรุณากรอกชื่อ record อย่างน้อย 1 ตัว",
    "wz.step3_title": "ขั้นตอนที่ 3: แจ้งเตือน Telegram (ไม่บังคับ)",
    "wz.step3_sub": "จะให้แจ้งทาง Telegram เมื่อ IP เปลี่ยน / เกิด error ก็ใส่ตรงนี้ ถ้ายังไม่ต้องการกด \"ข้าม\" ได้",
    "wz.tg_token_label": "Bot token (สร้างจาก @BotFather ใน Telegram)",
    "wz.tg_chat_label": "Chat ID (กด \"ค้นหา\" ให้อัตโนมัติ หรือกรอกเองได้ — เลข 9-10 หลัก)",
    "wz.tg_find": "ค้นหา chat id ให้อัตโนมัติ",
    "wz.tg_test": "ส่งข้อความทดสอบ",
    "wz.tg_help": "วิธี: เปิด Telegram ค้นหา @BotFather → ส่ง /newbot → ตั้งชื่อ → คัดลอก token มาวาง แล้วเปิดแชทกับ bot ใหม่และกด Start จากนั้นกด \"ค้นหา chat id ให้อัตโนมัติ\" — ถ้าหาไม่ได้ (bot เคยถูกใช้แล้ว) เปิดแชทกับ bot → มองหา ID ตัวเลขใน @userinfobot หรือกดปุ่ม Share ID ของ bot",
    "wz.skip": "ข้าม →",
    "wz.need_tg_token": "วาง bot token ก่อน",
    "wz.searching": "กำลังค้นหาบทสนทนาล่าสุด...",
    "wz.tg_manual": "{msg} — กรอก chat id เองได้ในช่องด้านบน",
    "wz.tg_found": "พบ chat id: {id}",
    "wz.tg_test_text": "✅ ทดสอบการแจ้งเตือนจาก Cloudflare DDNS",
    "wz.tg_send_fail": "ส่งไม่ได้: {msg}",
    "wz.step4_title": "ขั้นตอนที่ 4: ตรวจสอบและบันทึก",
    "wz.step4_sub": "สรุปสิ่งที่กำลังจะตั้งค่า:",
    "wz.token_ok": "API token: ตรวจสอบผ่านแล้ว ✔<br>",
    "wz.zone_line": "Zone: <b>{zone}</b><br>",
    "wz.records_line": "Records: {n} ตัว ({names})<br>",
    "wz.tg_line": "Telegram: {state}",
    "wz.tg_on": "เปิด (chat {id})",
    "wz.tg_off": "ปิด (ข้าม)",
    "wz.save_start": "บันทึกและเริ่มใช้งาน",
    "wz.done": "ตั้งค่าเสร็จสมบูรณ์ — DDNS เริ่มทำงานแล้ว",
    "wz.save_fail": "บันทึกไม่สำเร็จ: {msg}",
    "html.001": "อัปเดต IP อัตโนมัติ · รอบล่าสุด ",
    "html.002": "กำลังโหลด…",
    "html.003": "มีเวอร์ชันใหม่",
    "html.004": "รีเฟรช",
    "html.005": "สถานะ IP",
    "html.006": "กดที่ชื่อหรือ IP เพื่อคัดลอก",
    "html.007": "IP สาธารณะปัจจุบัน",
    "html.008": "ตรวจ…",
    "html.009": "ตรวจ…",
    "html.010": "ตรวจใหม่",
    "html.011": "ตรวจ DDNS ตอนนี้",
    "html.012": "กำลังโหลด…",
    "html.013": "แจ้งเตือน Telegram",
    "html.014": "กำลังโหลด…",
    "html.015": "ส่งข้อความทดสอบ",
    "html.016": "ดูคิว",
    "html.017": "ลองส่งใหม่",
    "html.018": "ล้างคิว",
    "html.019": "ให้บริการผ่าน Tunnel แทนการเปิดพอร์ต (เหมาะกับ CGNAT / ไม่เปิดพอร์ต)",
    "html.020": "กำลังโหลด…",
    "html.021": "ตั้งค่า Tunnel (wizard)",
    "html.022": "ดู hostname ที่ผูกแล้ว",
    "html.023": "+ เพิ่ม hostname",
    "html.024": "ซิงค์จาก Cloudflare",
    "html.025": "เริ่ม tunnel",
    "html.026": "หยุด tunnel",
    "html.027": "ดาวน์โหลด cloudflared",
    "html.028": "ชื่อ (subdomain)",
    "html.029": "โดเมน",
    "html.030": "Path (ไม่บังคับ)",
    "html.031": "ชนิด",
    "html.032": "บริการ/พอร์ต",
    "html.033": "💡 เลือกชนิดให้ตรงกับบริการ: ",
    "html.034": " = เว็บธรรมดา (เช่น ",
    "html.035": " = พอร์ต SSL เช่น 443/8443 (ต้องเป็น ",
    "html.036": " — ถ้าผูกเป็น http จะเจอ \"Bad Request\") · ",
    "html.037": " = SSH/game/VPN (เช่น ",
    "html.038": "ผูกกับ tunnel",
    "html.039": "ยกเลิก",
    "html.040": "ข้อควรรู้",
    "html.041": "ชื่อเดียวใช้ได้อย่างใดอย่างหนึ่ง: A/AAAA (DDNS) หรือ CNAME (tunnel) — Cloudflare ห้ามซ้ำชื่อกัน ต้องใช้คนละชื่อ (เช่น DDNS = home.โดเมน, tunnel = app.โดเมน)",
    "html.042": "Tunnel ไม่ต้องเปิดพอร์ต / ไม่พึ่ง IP — เหมาะกับ CGNAT หรือไม่อยากแตะเราเตอร์",
    "html.043": "DDNS เหมาะกับบริการที่ต้องรับ connection ตรง (SSH, game server)",
    "html.044": "บริการที่ผูก (เช่น localhost:8080) ต้องรันอยู่ ถึงจะเข้าเว็บได้",
    "html.045": "ผูก hostname ต้องใช้ API token ที่มีสิทธิ์ Account &gt; Cloudflare Tunnel &gt; Edit",
    "html.046": "tunnel รันตาม service — หยุด service = tunnel หยุด",
    "html.047": "tunnel token ใช้ได้จนกว่าจะ revoke ที่ Zero Trust",
    "html.048": "กำลังโหลด…",
    "html.049": "เริ่ม service",
    "html.050": "หยุด service",
    "html.051": "ติดตั้ง service",
    "html.052": "ถอนการติดตั้ง",
    "html.053": "ข้อควรรู้",
    "html.054": "ต้องมีสิทธิ์ admin — ถ้าหน้าเว็บนี้รันเป็น service อยู่แล้ว (เปิดเองหลัง boot) การติดตั้ง/ถอน/หยุดทำไม่ได้จากเว็บ (จะตัดการเชื่อมต่อตัวเอง) — ใช้ install.bat / uninstall.bat แทน ส่วน Restart ใช้ได้เสมอ (เว็บหลุด ~10-15 วิ แล้วกลับมา)",
    "html.055": "รันแบบ standalone (คำสั่ง webui / เปิด exe เปล่า ๆ) ต้องเปิดด้วยสิทธิ์ admin ถึงจะติดตั้ง/ควบคุม service ได้",
    "html.056": "ถอนการติดตั้งไม่ลบ config/state/ข้อมูล — แค่เอา service ออกจาก Windows",
    "html.057": "สแกนพอร์ต",
    "html.058": "ตรวจบริการที่เปิดอยู่บน host ที่ตั้งไว้ (resolve IP ปัจจุบันให้อัตโนมัติ)",
    "html.059": "สแกน",
    "html.060": "ประวัติการอัปเดต",
    "html.061": "50 รายการล่าสุด",
    "html.062": "กำลังโหลด…",
    "html.063": "Log ล่าสุด",
    "html.064": "เปิดโฟลเดอร์ข้อมูล",
    "html.065": "โหลดใหม่",
    "html.066": "ล้าง log",
    "html.067": "ตั้งค่า",
    "html.068": "แบบฟอร์ม",
    "html.069": "แก้ไขไฟล์โดยตรง",
    "html.070": "บันทึกการตั้งค่า",
    "html.071": "ดาวน์โหลด config",
    "html.072": "นำเข้า config",
    "html.073": "ตรวจ IP ทุก (วินาที, ขั้นต่ำ 15)",
    "html.074": "รหัสผ่านหน้าเว็บ (เว้นว่าง = ไม่เปลี่ยน · พิมพ์ใหม่ = เปลี่ยน)",
    "html.075": "ลบรหัส",
    "html.076": "พอร์ตหน้าเว็บ",
    "html.077": "หน้าเว็บเปิดที่ (host)",
    "html.078": "คำเตือน: 0.0.0.0 = ใครในวง LAN เข้าได้ — ตั้งรหัสผ่านด้านบนเสมอ",
    "html.079": "ที่เก็บ log (เว้นว่าง = โฟลเดอร์เดียวกับ exe)",
    "html.080": "ที่เก็บข้อมูล (state, คิว) — เว้นว่าง = โฟลเดอร์เดียวกับ exe",
    "html.081": " อัปเดต IPv4 (A record)",
    "html.082": " อัปเดต IPv6 (AAAA record)",
    "html.083": " ตรวจฉันทามติ IP (อย่างน้อย 2 provider เห็นตรงกัน)",
    "html.084": " กัน IP ของ Cloudflare (anycast)",
    "html.085": "Heartbeat (ไม่บังคับ)",
    "html.086": "ส่งสัญญาณ \"ยังทำงาน\" ทุกรอบให้บริการเฝ้าดู — รู้ว่าเครื่อง/program ตายหรือไม่จากนอกบ้าน (กรอก URL อันใดอันหนึ่งหรือทั้งคู่)",
    "html.087": "ทดสอบส่ง heartbeat",
    "html.088": "Healthchecks.io ping URL (ฟรี: healthchecks.io)",
    "html.089": "แจ้งเตือน Telegram",
    "html.090": "Bot token (จาก @BotFather)",
    "html.091": "Chat ID (เว้น = wizard/notify-test หาให้)",
    "html.092": " เริ่มทำงาน",
    "html.093": " หยุดทำงาน",
    "html.094": " IP เปลี่ยน",
    "html.095": " สร้าง record ใหม่",
    "html.096": " สรุปทุกรอบ",
    "html.097": " สรุปรายวันทาง Telegram",
    "html.098": "เวลา (HH:MM)",
    "html.099": " ควบคุม/กู้รหัสผ่านผ่าน Telegram (พิมพ์ /help ในแชท)",
    "html.100": "ชื่อเครื่องรับคำสั่ง (เว้น = ชื่อเครื่องของระบบ — ใช้ bot กลางหลายเครื่อง: พิมพ์ /status @ชื่อ)",
    "html.101": "Cloudflare Tunnel (ไม่บังคับ)",
    "html.102": " เปิด tunnel อัตโนมัติตอน service เริ่ม",
    "html.103": "เช็คอัปเดต cloudflared",
    "html.104": "Tunnel Token (ยาว — วางได้เต็มช่อง ไม่ซ่อน)",
    "html.105": "ที่อยู่ cloudflared.exe (เว้นว่าง = ดาวน์โหลดข้าง exe อัตโนมัติ)",
    "html.106": "+ เพิ่ม record",
    "html.107": "โหลดชื่อ record จาก Cloudflare",
    "html.108": "แก้ไขไฟล์ config.ini ตรง ๆ ระวังรูปแบบให้ถูกต้อง (ระบบตรวจ syntax และค่าพื้นฐานก่อนบันทึก) — ตัวอย่างดูได้จาก config.example.ini",
    "html.109": "บันทึกไฟล์",
    "html.110": "ตั้งค่า Cloudflare DDNS ครั้งแรก",
    "html.111": "ทำตามทีละขั้นตอน ประมาณ 2 นาที — ตอนไหนติด กด \"ดูวิธีทำ\" ได้ทุกขั้น",
    "html.112": "ข้ามชั่วคราว",
    "html.113": "ตั้งค่า Cloudflare Tunnel",
    "html.114": "ให้บริการเว็บผ่าน Tunnel โดยไม่ต้องเปิดพอร์ต — 4 ขั้นตอน",
    "html.115": "ปิด",

    "html.116": "ภาษา Telegram (notify + คำสั่ง)",
  },
  en: {

    "html.001": "Auto-update IP · last run",
    "html.002": "Loading…",
    "html.003": "New version available",
    "html.004": "Refresh",
    "html.005": "IP status",
    "html.006": "Click a name or IP to copy",
    "html.007": "Current public IP",
    "html.008": "Checking…",
    "html.009": "Checking…",
    "html.010": "Check again",
    "html.011": "Run DDNS now",
    "html.012": "Loading…",
    "html.013": "Telegram notifications",
    "html.014": "Loading…",
    "html.015": "Send test message",
    "html.016": "View queue",
    "html.017": "Try resend",
    "html.018": "Clear queue",
    "html.019": "Serve through a Tunnel instead of opening a port (great for CGNAT / no port forwarding)",
    "html.020": "Loading…",
    "html.021": "Set up Tunnel (wizard)",
    "html.022": "View bound hostnames",
    "html.023": "+ Add hostname",
    "html.024": "Sync from Cloudflare",
    "html.025": "Start tunnel",
    "html.026": "Stop tunnel",
    "html.027": "Download cloudflared",
    "html.028": "Name (subdomain)",
    "html.029": "Domain",
    "html.030": "Path (optional)",
    "html.031": "Type",
    "html.032": "Service/port",
    "html.033": "💡 Match the type to the service: ",
    "html.034": " = plain web (e.g. ",
    "html.035": " = SSL port like 443/8443 (must be ",
    "html.036": " — binding as http gives \"Bad Request\") · ",
    "html.037": " = SSH/game/VPN (e.g. ",
    "html.038": "Bind to tunnel",
    "html.039": "Cancel",
    "html.040": "Good to know",
    "html.041": "A name can only be one of: A/AAAA (DDNS) or CNAME (tunnel) — Cloudflare forbids duplicate names; use different names (e.g. DDNS = home.domain, tunnel = app.domain)",
    "html.042": "Tunnel needs no open ports / no public IP — great for CGNAT or if you'd rather not touch the router",
    "html.043": "DDNS suits services that need direct inbound connections (SSH, game servers)",
    "html.044": "The bound service (e.g. localhost:8080) must be running for the site to load",
    "html.045": "Binding a hostname requires an API token with Account &gt; Cloudflare Tunnel &gt; Edit permission",
    "html.046": "Tunnel runs with the service — stopping the service stops the tunnel",
    "html.047": "A tunnel token stays valid until revoked in Zero Trust",
    "html.048": "Loading…",
    "html.049": "Start service",
    "html.050": "Stop service",
    "html.051": "Install service",
    "html.052": "Uninstall",
    "html.053": "Good to know",
    "html.054": "Admin rights required — if this page runs inside the service (auto-started after boot), install/uninstall/stop cannot be done from the web (it would disconnect itself) — use install.bat / uninstall.bat instead. Restart always works (the page drops ~10-15s then returns)",
    "html.055": "Running standalone (webui command / opening the exe) requires admin rights to install/control the service",
    "html.056": "Uninstalling does NOT delete config/state/data — it only removes the service from Windows",
    "html.057": "Port scan",
    "html.058": "Check which services are open on a configured host (resolves the current IP automatically)",
    "html.059": "Scan",
    "html.060": "Update history",
    "html.061": "Latest 50 entries",
    "html.062": "Loading…",
    "html.063": "Latest log",
    "html.064": "Open data folder",
    "html.065": "Reload",
    "html.066": "Clear log",
    "html.067": "Settings",
    "html.068": "Form",
    "html.069": "Edit file directly",
    "html.070": "Save settings",
    "html.071": "Download config",
    "html.072": "Import config",
    "html.073": "Check IP every (seconds, min 15)",
    "html.074": "Web UI password (empty = keep current · type new = change)",
    "html.075": "Clear",
    "html.076": "Web UI port",
    "html.077": "Web UI bind host",
    "html.078": "Warning: 0.0.0.0 = anyone on the LAN can access — always set a password above",
    "html.079": "Log folder (empty = same folder as exe)",
    "html.080": "Data folder (state, queue) — empty = same folder as exe",
    "html.081": " Update IPv4 (A record)",
    "html.082": " Update IPv6 (AAAA record)",
    "html.083": " IP consensus (at least 2 providers agree)",
    "html.084": " Reject Cloudflare IPs (anycast)",
    "html.085": "Heartbeat (optional)",
    "html.086": "Send an \"I'm alive\" signal every round to a monitor — so you know from outside if the machine/program is dead (fill either or both URLs)",
    "html.087": "Test heartbeat",
    "html.088": "Healthchecks.io ping URL (free: healthchecks.io)",
    "html.089": "Telegram notifications",
    "html.090": "Bot token (from @BotFather)",
    "html.091": "Chat ID (empty = wizard/notify-test finds it)",
    "html.092": " On start",
    "html.093": " On stop",
    "html.094": " IP change",
    "html.095": " Record created",
    "html.096": " Every round",
    "html.097": " Daily report via Telegram",
    "html.098": "Time (HH:MM)",
    "html.099": " Control / recover password via Telegram (type /help in the chat)",
    "html.100": "Machine name for commands (empty = system hostname — shared bot across machines: type /status @name)",
    "html.101": "Cloudflare Tunnel (optional)",
    "html.102": " Auto-start tunnel when the service starts",
    "html.103": "Check cloudflared updates",
    "html.104": "Tunnel Token (long — full field, not hidden)",
    "html.105": "cloudflared.exe path (empty = auto-download next to exe)",
    "html.106": "+ Add record",
    "html.107": "Load record names from Cloudflare",
    "html.108": "Edit config.ini directly — be careful with the format (syntax and basic values are validated before saving) — see config.example.ini for examples",
    "html.109": "Save file",
    "html.110": "Set up Cloudflare DDNS for the first time",
    "html.111": "Follow the steps — about 2 minutes. Stuck? Press \"How to\" at any step.",
    "html.112": "Skip for now",
    "html.113": "Set up Cloudflare Tunnel",
    "html.114": "Serve web through a Tunnel without opening ports — 4 steps",
    "html.115": "Close",

    "html.116": "Telegram language (notify + commands)",
    "lang.name": "English",
    "toast.timeout": "timeout — server did not respond within {s}s (try again or check the log)",
    "toast.network": "Cannot connect to server (network error) — try again or check the log",
    "eye.toggle": "Show/Hide password",
    "pill.config_incomplete": "Setup incomplete",
    "pill.problem": "Has issues",
    "pill.ready": "Ready",
    "status.never_run": "Never run",
    "status.no_ip": "No IP data yet (waiting for the first service run)",
    "status.no_config": "Config is not set up — follow the wizard or complete the \"Settings\" section first (IP will be updated automatically)",
    "status.unreadable": "Cannot read status",
    "record.copy_name": "Click to copy name",
    "record.copy_ip": "Click to copy IP",
    "record.not_set": "Not set",
    "record.updated_at": "Updated ",
    "tg.ready": "Ready",
    "tg.queue_waiting": "{n} messages queued",
    "tg.not_set": "Not configured",
    "tg.need_token": "Add the token in the form below or run setup",
    "api.stats": "Cloudflare API: {calls} calls · {errors} errors · rate limited {rl} (since start)",
    "history.empty": "No history yet (waiting for the first update)",
    "history.time": "Time",
    "history.record": "record",
    "history.action": "Action",
    "history.ip": "IP",
    "history.updated": "Updated IP",
    "history.created": "Created record",
    "copy.copied": "Copied {text}",
    "copy.failed": "Could not copy: {err}",
    "svc.in_service": "Running in the service (system privileges) — install/uninstall/stop requires external .bat",
    "svc.standalone_admin": "Standalone · admin rights — can control the service",
    "svc.standalone_no_admin": "Standalone · no admin rights — service control buttons unavailable (open the exe/cmd as admin)",
    "svc.need_admin": "Requires opening the web UI as admin",
    "svc.not_installed": "Service is not installed — press \"Install service\" (requires admin)",
    "svc.state.running": "Running",
    "svc.state.stopped": "Stopped",
    "svc.state.starting": "Starting",
    "svc.state.stopping": "Stopping",
    "svc.state.resuming": "Resuming",
    "svc.state.pausing": "Pausing",
    "svc.state.paused": "Paused",
    "svc.installed_ok": "Installed — {label}",
    "svc.unreadable": "Cannot read status: {err}",
    "fail_prefix": "Failed: {msg}",
    "err_prefix": "error: {err}",
    "update.new": "New v{ver}",
    "folder.copied": "{msg} — copied the path to clipboard (Win+R → paste → Enter)",
    "cfg.load_fail": "Could not load config: {err}",
    "recs.empty": "No records yet — press \"Add record\" below",
    "rec.placeholder_name": "home (adds .zone) / @ / *.zone (wildcard)",
    "rec.placeholder_zone": "zone (leave empty = auto-detect)",
    "rec.proxy_title": "Through the Cloudflare orange cloud",
    "rec.ttl_title": "TTL (seconds)",
    "rec.del_title": "Delete record",
    "save.dup": "Duplicate record: {name} (same name entered twice)",
    "save.ok": "Saved — will take effect next round",
    "save.pw_removed": "Web UI password removed — access without login",
    "save.pw_set": "Web UI password set — logging in again",
    "save.port_changed": "Web UI port changed — restart the service (dist\\cloudflare-ddns.exe restart) to apply",
    "save.fail": "Could not save: {err}",
    "ip.checking": "Checking…",
    "ip.not_found4": "Not found (IPv4)",
    "ip.none6": "None (IPv6)",
    "ip.read_fail": "Cannot read: {err}",
    "zone.need": "Please enter a zone for the record first",
    "load.records_fail": "Could not load: {msg}",
    "load.no_records": "No A/AAAA records in this zone (will be created when an IP is found)",
    "load.pick_record": "— Pick an existing record —",
    "scan.no_host": "No host to scan (set a record first)",
    "scan.no_records": "— No records in config —",
    "scan.scanning": "Scanning {host} ...",
    "scan.status_open": "Open",
    "scan.status_filtered": "No response (firewall?)",
    "scan.status_closed": "Closed",
    "scan.header_port": "Port",
    "scan.header_service": "Service",
    "scan.header_status": "Status",
    "scan.summary": "{host} → {ip} · {open} open · {closed} closed · {filtered} filtered",
    "log.session_expired": "Session expired — refresh the page (F5/Ctrl+R) to log in again and retry",
    "log.read_fail_http": "Could not read log (HTTP {status}) — refresh the page and retry",
    "log.read_fail": "Could not read log: {err}",
    "log.clear_confirm": "Clear all log files?",
    "log.clear_fail": "Could not clear: {msg}",
    "tunnel.disabled": "Disabled (configure in the form below)",
    "tunnel.not_installed": "cloudflared not installed",
    "tunnel.running": "Running (pid {pid})",
    "tunnel.not_running": "Not running",
    "tunnel.unreadable": "Cannot read status: {err}",
    "tunnel.loading": "Loading…",
    "tunnel.no_token": "Tunnel token not set (use the wizard)",
    "tunnel.no_hostname": "No hostname bound to the tunnel — use \"Set up Tunnel (wizard)\" or \"+ Add hostname\"",
    "tunnel.header_hostname": "hostname",
    "tunnel.header_type": "Type",
    "tunnel.header_service": "Service",
    "tunnel.edit_title": "Edit this mapping (rebind = replace)",
    "tunnel.edit": "Edit",
    "tunnel.unbind_title": "Unbind",
    "tunnel.hint": "Multiple ports on one name: bind different paths (e.g. /api → 3000, / → 8080) · TCP/UDP selectable · \"Edit\" = rebind with new values (replaces old)",
    "tunnel.unbind_confirm": "Unbind {host}{path}?",
    "tunnel.loading_domains": "— Loading domains… —",
    "tunnel.no_zone_perm": "— Cannot use domain (API token lacks permission) —",
    "tunnel.load_domains_fail": "— Could not load domains —",
    "tunnel.edit_msg": "Edit {host}{path} — change the values above then press \"Bind to tunnel\" (replaces the old mapping)",
    "tunnel.no_token_bind": "Tunnel token not set (use the wizard first)",
    "tunnel.need_name_domain": "Please enter a name and domain",
    "tunnel.binding": "Binding...",
    "tunnel.sync_need_token": "Tunnel token not set (use the wizard first)",
    "tunnel.action_start": "Start tunnel",
    "tunnel.action_stop": "Stop tunnel",
    "tunnel.action_download": "Download",
    "tunnel.show_log": "View tunnel log",
    "tunnel.log_title": "cloudflared log (tunnel.log)",
    "tg.test_ok": "Test message sent — check Telegram",
    "tg.test_fail": "Could not send: {msg}",
    "tg.queue_empty": "Queue is empty — no pending messages",
    "tg.queue_header_msg": "Message",
    "tg.queue_summary": "{n} messages total — press \"Try resend\" to send now, or \"Clear queue\" to discard",
    "tg.queue_read_fail": "Could not read queue: {err}",
    "tg.flush_ok": "Resent {sent} messages ({failed} still queued)",
    "tg.clear_confirm": "Clear all pending messages in the queue?",
    "tg.clear_ok": "Queue cleared",
    "wz.back": "← Back",
    "file.load_fail": "Could not load config file: {err}",
    "file.save_ok": "File saved — will take effect next round",
    "setup.check_fail": "Could not load: {msg}",
    "heartbeat.test_fail": "Could not test heartbeat: {err}",
    "update.check_fail": "Could not check for updates: {err}",
    "cfg.export_fail": "Could not download config: {err}",
    "cfg.import_ok": "Config imported — {msg}",
    "cfg.import_fail": "Import failed: {msg}",
    "cfg.import_err": "Could not import config: {err}",
    "svc.install_confirm": "Install Windows Service 'CloudflareDDNS'? (auto-start on boot)",
    "svc.restart_confirm": "Restart Windows Service? — this page will disconnect briefly and come back",
    "svc.start_confirm": "Start Windows Service 'CloudflareDDNS'?",
    "svc.stop_confirm": "Stop Windows Service 'CloudflareDDNS'? (this page will not come back)",
    "svc.uninstall_confirm": "Uninstall Windows Service 'CloudflareDDNS'?",
    "svc.uninstall_confirm2": "Confirm again — really uninstall the service? (config/state/data are NOT deleted)",
    "pw.clear_hint": "Password will be removed when you save — access the web without login",
    "heartbeat.test": "Heartbeat: {msg}",
    "ddns.busy": "A previous check is still running — wait a moment and try again",
    "ddns.running": "Checking DDNS — status will update automatically",
    "log.no_log": "(no log file yet: {exc})",

    "twz.title1": "What is Tunnel and why use it",
    "twz.sub1": "Cloudflare Tunnel connects your machine to Cloudflare directly — people reach your service through Cloudflare without opening a router port or relying on a public IP",
    "twz.suit_title": "Good for:",
    "twz.suit_li": ["ISPs that assign CGNAT IPs (DDNS won't work)", "Don't want to open a port forward on the router", "Serving web/API through Cloudflare"],
    "twz.start": "Start setup →",
    "twz.step1_title": "Step 1: Enter Tunnel Token",
    "twz.step1_sub": "Free to create from Cloudflare Zero Trust — press the button below to open the page and follow the steps:",
    "twz.open_zt": "Open Zero Trust ↗",
    "twz.how_token": "How to find the token",
    "twz.token_label": "Tunnel Token (shown in full, not hidden)",
    "twz.token_ph": "eyJhIjoi... (long)",
    "twz.token_steps_title": "How to find the token (step by step):",
    "twz.token_step_li": ["Press \"Open Zero Trust\" and log in", "Left menu: Networks → Tunnels → Create a tunnel", "Name it (e.g. home) → choose Cloudflare-managed → continue", "Copy the token from the install command (the --token eyJ... part) — no need to actually run it", "Paste the token in the field above, then press verify token"],
    "twz.verify": "Verify token →",
    "twz.hide_steps": "Hide steps",
    "twz.need_paste": "Please paste the tunnel token first",
    "twz.checking": "Verifying (downloads cloudflared if missing + tests connection ~5s)...",
    "twz.check_fail": "{msg} (try pressing \"How to find the token\")",
    "twz.step2_title": "Step 2: Bind a web (hostname) to the tunnel",
    "twz.step2_sub": "Enter a web name and a local service — the program configures everything automatically (creates DNS + sets tunnel config), no dashboard needed",
    "twz.sub_label": "Name (subdomain)",
    "twz.sub_ph": "app (new names are fine, e.g. nas)",
    "twz.sub_hint": "A brand-new name works too — DNS is created automatically",
    "twz.domain_label": "Domain",
    "twz.path_label": "Path (optional — for multiple ports on one name, e.g. /api)",
    "twz.path_ph": "/api (empty = all paths)",
    "twz.type_label": "Type",
    "twz.type_tcp": "TCP (e.g. SSH)",
    "twz.type_udp": "UDP (e.g. game/VPN)",
    "twz.service_label": "Service/port",
    "twz.service_hint": "💡 Match the type to the service: <b>HTTP</b> = plain web (e.g. <span class=\"mono\">http://localhost:8080</span>) · <b>HTTPS</b> = SSL port like 443/8443 (must be <span class=\"mono\">https://localhost:443</span> — binding as http gives \"Bad Request\") · <b>TCP/UDP</b> = SSH/game/VPN (e.g. <span class=\"mono\">tcp://localhost:22</span>) · <b>LAN IPs</b> work too (private hostname — e.g. <span class=\"mono\">http://192.168.1.50:3000</span>) but cloudflared must be on the same LAN as the service",
    "twz.load_records": "Pick an existing record",
    "twz.bound_title": "Bound to tunnel",
    "twz.binding_btn": "Bind to tunnel",
    "twz.example": "Example: name <b>app</b> + domain <b>makerwitawat.com</b> + service <b>http://localhost:8080</b> → reachable at <b>https://app.makerwitawat.com</b> — <b>a brand-new subdomain works too</b>; the program creates the DNS record automatically (you can edit it later in the form/dashboard)",
    "twz.next": "Next →",
    "twz.need_name": "Please enter a name and choose a domain",
    "twz.binding": "Binding {host}{path} to the tunnel...",
    "twz.pick_record": "— Pick a record —",
    "twz.step3_title": "Step 3: Save and start the tunnel",
    "twz.step3_sub": "Ready to go — save the config and start the tunnel now:",
    "twz.token_ok": "Token: verified ✔<br>",
    "twz.cf_ready": "cloudflared: ready (downloaded automatically if missing)<br>",
    "twz.autostart": "Auto-start: on (when the service starts)",
    "twz.save_start": "Save and start tunnel",
    "twz.saving": "Saving...",
    "twz.save_fail": "Could not save: {msg}",
    "twz.done": "Tunnel setup complete — {msg}",
    "twz.save_but_start_fail": "Saved, but could not start the tunnel: {msg}",
    "twz.no_bound": "None yet — bind one above",

    "wz.title": "Welcome",
    "wz.sub1": "This program finds your public IP and automatically updates DNS records on Cloudflare when the IP changes. All in 5 short steps.",
    "wz.start": "Start setup →",
    "wz.step1_title": "Step 1: Enter your Cloudflare API token",
    "wz.step1_sub": "The token only needs DNS edit permission. Create one free — open the page and follow the steps below:",
    "wz.open_token": "Open create-token page ↗",
    "wz.how_token": "How to find the token",
    "wz.token_steps_title": "How to find the token (step by step):",
    "wz.token_step_li": ["Press \"Open create-token page\" and log into Cloudflare", "Press the orange Create Token button", "Choose the template named Edit zone DNS and press Use template", "In Zone Resources choose Include → Specific zone → pick your domain", "Press Continue to summary → Create Token", "Copy the token immediately (shown only once, starts with cfut_) and paste it in the field above"],
    "wz.verify": "Verify token →",
    "wz.hide_steps": "Hide steps",
    "wz.need_token": "Please paste the API token first",
    "wz.checking_token": "Verifying token...",
    "wz.verify_fail": "Verification failed: {msg} (try pressing \"How to find the token\")",
    "wz.server_err": "Cannot reach the server: {err}",
    "wz.step2_title": "Step 2: Choose a domain (zone) and record",
    "wz.step2_sub": "Pick a domain, then set a record name — a short name works (e.g. home); the program appends .domain automatically. @ is the domain root.",
    "wz.zone_label": "Zone (domain)",
    "wz.load_records": "Load existing records from Cloudflare",
    "wz.rec_title": "Records to update",
    "wz.add_record": "+ Add record",
    "wz.next": "Next →",
    "wz.need_zone": "Please choose a zone first",
    "wz.need_rec_name": "Please enter at least one record name",
    "wz.step3_title": "Step 3: Telegram notifications (optional)",
    "wz.step3_sub": "Get notified on Telegram when the IP changes / an error occurs. Skip if you don't want it.",
    "wz.tg_token_label": "Bot token (create from @BotFather in Telegram)",
    "wz.tg_chat_label": "Chat ID (press \"Find\" to auto-detect, or enter manually — 9-10 digits)",
    "wz.tg_find": "Find chat id automatically",
    "wz.tg_test": "Send test message",
    "wz.tg_help": "How: open Telegram, search @BotFather → send /newbot → name it → copy the token and paste it, then open a chat with the bot and press Start. Then press \"Find chat id automatically\" — if not found (bot was used before), open the chat → look for the numeric ID in @userinfobot or press the bot's Share ID button",
    "wz.skip": "Skip →",
    "wz.need_tg_token": "Please paste the bot token first",
    "wz.searching": "Searching for the latest conversation...",
    "wz.tg_manual": "{msg} — you can enter the chat id manually in the field above",
    "wz.tg_found": "Found chat id: {id}",
    "wz.tg_test_text": "✅ Test notification from Cloudflare DDNS",
    "wz.tg_send_fail": "Could not send: {msg}",
    "wz.step4_title": "Step 4: Review and save",
    "wz.step4_sub": "Here is what will be set up:",
    "wz.token_ok": "API token: verified ✔<br>",
    "wz.zone_line": "Zone: <b>{zone}</b><br>",
    "wz.records_line": "Records: {n} ({names})<br>",
    "wz.tg_line": "Telegram: {state}",
    "wz.tg_on": "On (chat {id})",
    "wz.tg_off": "Off (skipped)",
    "wz.save_start": "Save and start",
    "wz.done": "Setup complete — DDNS is now running",
    "wz.save_fail": "Could not save: {msg}",
  },
};

const LANG = (() => {
  const saved = localStorage.getItem("cfddns_lang");
  if (saved === "th" || saved === "en") return saved;
  return (navigator.language || "th").toLowerCase().startsWith("en") ? "en" : "th";
})();

function t(key, vars) {
  const dict = (I18N[LANG] && I18N[LANG][key]) ? I18N[LANG] : I18N.th;
  let s = dict[key] ?? key;
  if (Array.isArray(s)) return s; // ชุดรายการ (เช่น ขั้นตอน wizard) — caller map เอง
  if (vars) {
    for (const [k, v] of Object.entries(vars)) {
      s = s.split("{" + k + "}").join(String(v));
    }
  }
  return s;
}

function setLang(lang) {
  localStorage.setItem("cfddns_lang", lang);
  document.cookie = "cfddns_lang=" + lang + "; path=/; max-age=31536000; SameSite=Lax";
  location.reload();
}

/* แปล static ข้อความใน HTML (data-i18n) ตามภาษา */
function i18nApply() {
  document.querySelectorAll("[data-i18n]").forEach(el => {
    const key = el.dataset.i18n;
    const dict = (I18N[LANG] && I18N[LANG][key]) ? I18N[LANG] : I18N.th;
    if (dict && dict[key]) el.textContent = dict[key];
  });
}

/* แปล locale ของวันที่ตามภาษา (th-TH / en-GB) */
function fmtDate(ts) {
  try {
    return new Date(ts).toLocaleString(LANG === "en" ? "en-GB" : "th-TH");
  } catch (e) {
    return String(ts);
  }
}

function toast(text, kind) {
  const t = $("toast");
  t.textContent = text;
  t.className = "show " + (kind || "");
  clearTimeout(t._timer);
  t._timer = setTimeout(() => { t.className = ""; }, 3200);
  if (kind === "err") logClientError("toast", text);
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

/* ---------- fetch กลาง: timeout + แปล error ให้อ่านรู้เรื่อง (กัน "Failed to fetch" งง ๆ) ---------- */

const FETCH_TIMEOUT_MS = 90000; // 90 วิ (งานยาว เช่น ผูก hostname / ดาวน์โหลด cloudflared)
const _origFetch = window.fetch;
window.fetch = (url, opts) => {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), FETCH_TIMEOUT_MS);
  return _origFetch(url, { ...(opts || {}), signal: ctrl.signal })
    .then(r => { clearTimeout(timer); return r; })
    .catch(err => {
      clearTimeout(timer);
      if (err && err.name === "AbortError") {
        throw new Error(t("toast.timeout", { s: FETCH_TIMEOUT_MS / 1000 }));
      }
      throw new Error(t("toast.network"));
    });
};

/* ---------- log error ฝั่งหน้าเว็บ ไปไฟล์ log (ฝั่ง server) ---------- */

function logClientError(context, err) {
  try {
    const message = String(err && err.message ? err.message : err).slice(0, 500);
    // กรอง warning ของเบราว์เซอร์ที่ไม่ใช่ error จริง (ไม่ spam log)
    if (message.indexOf("ResizeObserver loop") !== -1) return;
    fetch("/log-event", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ context: String(context).slice(0, 120), message }),
    }).catch(() => {});
  } catch (e) { /* ไม่ต้องทำอะไร — กันลูป */ }
}

window.addEventListener("error", ev => logClientError("window.onerror", ev.message + " @" + (ev.filename || "") + ":" + (ev.lineno || "?")));
window.addEventListener("unhandledrejection", ev => logClientError("unhandledrejection", ev.reason));

/* ปรับ "บริการ/พอร์ต" ให้ตรงกับชนิดที่เลือก (ใช้พอร์ตเริ่มต้นต่อชนิด) */
function adaptServiceToProtocol(protocolSel, serviceInput) {
  const defaults = {
    http: "http://localhost:8080",
    https: "https://localhost:443",
    tcp: "tcp://localhost:22",
    udp: "udp://localhost:51820",
  };
  if (defaults[protocolSel.value]) serviceInput.value = defaults[protocolSel.value];
}

/* เพิ่มปุ่มตา (แสดง/ซ่อน) ให้ทุกช่อง password — กันซ้ำโดยใช้ data-eye */
function addEyeToggles() {
  document.querySelectorAll("input[type=password]").forEach(inp => {
    if (inp.dataset.eye) return;
    inp.dataset.eye = "1";
    const wrap = document.createElement("span");
    wrap.className = "eye-wrap";
    inp.parentNode.insertBefore(wrap, inp);
    wrap.appendChild(inp);
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "eye-toggle";
    btn.textContent = "👁";
    btn.title = t("eye.toggle");
    btn.setAttribute("aria-label", t("eye.toggle"));
    btn.addEventListener("click", () => {
      inp.type = inp.type === "password" ? "text" : "password";
      btn.textContent = inp.type === "password" ? "👁" : "🙈";
    });
    wrap.appendChild(btn);
  });
}

/* ---------- สถานะ ---------- */

async function loadStatus() {
  try {
    const r = await fetch("/status.json");
    const s = await r.json();
    const pill = $("pill");
    if (!s.config_ok) {
      pill.textContent = t("pill.config_incomplete");
      pill.className = "pill warn";
    } else if (s.errors_active) {
      pill.textContent = t("pill.problem");
      pill.className = "pill err";
    } else {
      pill.textContent = t("pill.ready");
      pill.className = "pill ok";
    }
    const cfgErr = $("cfg-err");
    if (s.config_errors && s.config_errors.length) {
      cfgErr.hidden = false;
      cfgErr.textContent = "⚠ " + s.config_errors.join(" · ");
    } else {
      cfgErr.hidden = true;
    }
    const last = s.last_run ? fmtDate(s.last_run) : t("status.never_run");
    $("lastrun").textContent = last;
    $("verpill").textContent = "v" + (s.version || "?");

    const box = $("records");
    const entries = Object.entries(s.records || {});
    if (!entries.length) {
      const msg = s.config_ok
        ? t("status.no_ip")
        : t("status.no_config");
      box.innerHTML = '<p style="color:var(--muted)">' + msg + "</p>";
    } else {
      box.innerHTML = entries.map(([key, ip]) => {
        const err = s.record_errors && s.record_errors[key];
        const kind = err ? "err" : (ip ? "ok" : "idle");
        const [name, type] = key.split("|");
        const ts = (s.records_time || {})[key];
        const timeText = ts ? fmtDate(ts) : "—";
        const meta = escapeHtml(type || "") + (type ? " · " : "") + (err ? escapeHtml(err) : t("record.updated_at") + timeText);
        return '<div class="record-row ' + kind + '">' +
          '<span class="rec-dot"></span>' +
          '<span class="rec-name mono clickable" title="' + t("record.copy_name") + '" onclick="copyIp(this)">' + escapeHtml(name) + "</span>" +
          '<span class="rec-ip mono clickable" title="' + t("record.copy_ip") + '" onclick="copyIp(this)">' + escapeHtml(ip || t("record.not_set")) + "</span>" +
          '<span class="rec-meta">' + meta + "</span></div>";
      }).join("");
    }

    const tg = s.telegram || {};
    const tgBox = $("tgstatus");
    if (tg.enabled) {
      let html = '<span class="ok">' + t("tg.ready") + '</span> (chat ' + escapeHtml(tg.chat_id) + ")";
      if (tg.queue) html += ' · <span class="err">' + t("tg.queue_waiting", { n: tg.queue }) + "</span>";
      tgBox.innerHTML = html;
    } else {
      tgBox.innerHTML = '<span>' + t("tg.not_set") + '</span> · <span style="color:var(--muted)">' + t("tg.need_token") + "</span>";
    }

    const api = s.api_stats || {};
    $("api-stats").textContent = t("api.stats", { calls: api.calls || 0, errors: api.errors || 0, rl: api.rate_limited || 0 });

    const hist = s.history || [];
    const histBox = $("history");
    if (!hist.length) {
      histBox.innerHTML = '<p style="color:var(--muted)">' + t("history.empty") + "</p>";
    } else {
      histBox.innerHTML = '<div style="border:1px solid var(--border);border-radius:8px;overflow-x:auto"><table class="tbl-w560" style="font-size:0.85rem;width:100%">' +
        '<tr style="background:var(--surface-2)"><th style="padding:5px 10px;text-align:left;white-space:nowrap">' + t("history.time") + '</th><th style="padding:5px 10px;text-align:left">' + t("history.record") + '</th><th style="padding:5px 10px;text-align:left;white-space:nowrap">' + t("history.action") + '</th><th style="padding:5px 10px;text-align:left;white-space:nowrap">' + t("history.ip") + "</th></tr>" +
        hist.slice().reverse().map(h => {
          const ts = h.time ? fmtDate(h.time) : "-";
          const act = { updated: t("history.updated"), created: t("history.created") }[h.action] || h.action;
          const cls = h.action === "updated" ? "" : "ok";
          return '<tr class="' + cls + '"><td style="padding:5px 10px;color:var(--muted);white-space:nowrap">' + ts + '</td><td class="mono" style="padding:5px 10px;word-break:break-all">' + escapeHtml(h.record) + " (" + escapeHtml(h.type || "") + ')</td><td style="padding:5px 10px;white-space:nowrap">' + escapeHtml(act) + '</td><td class="mono" style="padding:5px 10px;white-space:nowrap">' + escapeHtml(h.ip || "-") + "</td></tr>";
        }).join("") + "</table></div>";
    }
  } catch (e) {
    logClientError("loadStatus", e);
    $("pill").textContent = t("status.unreadable");
    $("pill").className = "pill err";
  }
}

async function copyIp(el) {
  try {
    await navigator.clipboard.writeText(el.textContent);
    toast(t("copy.copied", { text: el.textContent }), "ok");
  } catch (e) {
    toast(t("copy.failed", { err: e }), "err");
  }
}

/* ---------- Windows Service ---------- */

async function loadServiceStatus() {
  try {
    const r = await fetch("/status.json");
    const s = await r.json();
    const svc = s.service || {};
    const rt = s.runtime || {};
    const ctx = $("svc-ctx");
    if (rt.in_service) ctx.textContent = t("svc.in_service");
    else if (rt.admin) ctx.textContent = t("svc.standalone_admin");
    else ctx.textContent = t("svc.standalone_no_admin");
    const canControl = rt.admin;
    ["svcInstall", "svcUninstall", "svcStart", "svcStop", "svcRestart"].forEach(id => {
      const b = $(id);
      b.disabled = !canControl;
      b.title = canControl ? "" : t("svc.need_admin");
    });
    if (canControl) {
      if (rt.in_service) {
        // รันใน service: หยุด/ติดตั้ง/ถอน = ตัดการเชื่อมต่อตัวเอง (server ปฏิเสธอยู่แล้ว) — ปิดปุ่มให้ชัด
        $("svcStop").disabled = true;
        $("svcInstall").disabled = true;
        $("svcUninstall").disabled = true;
      } else {
        const running = svc.state === "running";
        $("svcStop").disabled = !running;
        $("svcStart").disabled = running;
      }
    }
    const box = $("svc-status");
    if (!svc.installed) {
      box.innerHTML = '<span style="color:var(--muted)">' + t("svc.not_installed") + "</span>";
      return;
    }
    const stateNames = { running: t("svc.state.running"), stopped: t("svc.state.stopped"), starting: t("svc.state.starting"), stopping: t("svc.state.stopping"), resuming: t("svc.state.resuming"), pausing: t("svc.state.pausing"), paused: t("svc.state.paused") };
    const label = escapeHtml(stateNames[svc.state] || svc.state);
    box.innerHTML = svc.running
      ? '<span class="ok">' + t("svc.installed_ok", { label }) + "</span>"
      : '<span class="err">' + t("svc.installed_ok", { label }) + "</span>";
  } catch (e) {
    logClientError("loadServiceStatus", e);
    $("svc-status").textContent = t("svc.unreadable", { err: e });
  }
}

async function svcAction(path, confirmText) {
  if (!confirm(confirmText)) return;
  try {
    const r = await fetch(path, { method: "POST" });
    const j = await r.json();
    toast(j.ok ? j.message : t("fail_prefix", { msg: j.message }), j.ok ? "ok" : "err");
    if (j.ok) {
      loadServiceStatus();
      if (path === "/service/restart") {
        setTimeout(() => location.reload(), 16000);
      }
    }
  } catch (e) {
    toast(t("err_prefix", { err: e }), "err");
  }
}

async function ddnsRunNow() {
  const btn = $("ddnsRun");
  btn.disabled = true;
  try {
    const r = await fetch("/ddns-run", { method: "POST" });
    const j = await r.json();
    toast(j.ok ? j.message : t("fail_prefix", { msg: j.message }), j.ok ? "ok" : "err");
    if (j.ok) {
      setTimeout(() => { loadStatus(); loadServiceStatus(); btn.disabled = false; }, 5000);
      setTimeout(loadStatus, 15000);
      return;
    }
  } catch (e) {
    toast(t("err_prefix", { err: e }), "err");
  }
  btn.disabled = false;
}

async function checkUpdate() {
  try {
    const r = await fetch("/update-check");
    const j = await r.json();
    if (!j.ok || !j.has_update) return;
    const pill = $("update-pill");
    pill.textContent = t("update.new", { ver: j.latest });
    pill.href = j.url || "https://github.com/Witawat/Cloudflare-ddns/releases";
    pill.style.display = "";
  } catch (e) { /* ออฟไลน์/ไม่เจอ release — ไม่ต้องแสดงอะไร */ }
}

async function openDataFolder() {
  try {
    const r = await fetch("/open-data-folder", { method: "POST" });
    const j = await r.json();
    if (j.ok && j.path) {
      try {
        await navigator.clipboard.writeText(j.path);
        toast(t("folder.copied", { msg: j.message }), "ok");
      } catch (e) {
        toast(j.message, "ok");
      }
    } else {
      toast(j.ok ? j.message : t("fail_prefix", { msg: j.message }), j.ok ? "ok" : "err");
    }
  } catch (e) {
    logClientError("openDataFolder", e);
    toast(t("err_prefix", { err: e }), "err");
  }
}

/* ---------- ตั้งค่า ---------- */

let recordsData = [];
let tunnelHostsData = [];
let currentWebuiPassword = "";
let currentWebuiPort = 8123;
let pwRemove = false;

async function loadConfig() {
  try {
    const r = await fetch("/config.json");
    const c = await r.json();
    $("api_token").value = c.cloudflare.api_token;
    $("interval").value = c.cloudflare.interval_seconds;
    $("use_ipv4").checked = !!c.cloudflare.use_ipv4;
    $("use_ipv6").checked = !!c.cloudflare.use_ipv6;
    $("ip_consensus").checked = !!c.cloudflare.ip_consensus;
    $("reject_cf_ips").checked = c.cloudflare.reject_cloudflare_ips !== false;
    $("hc_url").value = c.cloudflare.healthchecks_url || "";
    $("kuma_url").value = c.cloudflare.uptimekuma_url || "";
    $("webui_password").value = "";
    currentWebuiPassword = c.cloudflare.webui_password;
    $("pwClear").style.display = currentWebuiPassword ? "" : "none";
    $("webui_port").value = c.cloudflare.webui_port || 8123;
    currentWebuiPort = c.cloudflare.webui_port || 8123;
    $("webui_host").value = c.cloudflare.webui_host || "127.0.0.1";
    $("log_dir").value = c.cloudflare.log_dir || "";
    $("tg_token").value = c.telegram.bot_token;
    $("tg_chat").value = c.telegram.chat_id;
    $("notify_start").checked = !!c.telegram.notify_start;
    $("notify_stop").checked = !!c.telegram.notify_stop;
    $("notify_ip_change").checked = !!c.telegram.notify_ip_change;
    $("notify_error").checked = !!c.telegram.notify_error;
    $("notify_created").checked = !!c.telegram.notify_created;
    $("notify_round").checked = !!c.telegram.notify_round;
    $("daily_report").checked = !!c.telegram.daily_report;
    $("daily_report_time").value = c.telegram.daily_report_time || "08:00";
    $("tg_allow_reset").checked = !!c.telegram.allow_reset;
    $("tg_cmd_name").value = c.telegram.command_name || "";
    $("tg_language").value = c.telegram.language || "th";
    $("tunnel_enabled").checked = !!c.tunnel.enabled;
    $("tunnel_token").value = c.tunnel.token;
    $("cloudflared_path").value = c.tunnel.cloudflared_path || "";
    tunnelHostsData = c.tunnel.hosts || [];
    recordsData = c.records.map(r => ({ ...r }));
    renderRecordsEditor();
    loadScanHosts();
  } catch (e) {
    logClientError("loadConfig", e);
    toast(t("cfg.load_fail", { err: e }), "err");
  }
}

function renderRecordsEditor() {
  const box = $("records-editor");
  if (!recordsData.length) {
    box.innerHTML = '<p style="color:var(--muted)">' + t("recs.empty") + "</p>";
    return;
  }
  box.innerHTML = recordsData.map((r, i) => `
    <div class="rec-edit">
      <input type="text" data-i="${i}" data-k="name" value="${escapeHtml(r.name)}" placeholder="${t("rec.placeholder_name")}">
      <input type="text" data-i="${i}" data-k="zone" value="${escapeHtml(r.zone)}" placeholder="${t("rec.placeholder_zone")}">
      <div class="mini" title="${t("rec.proxy_title")}">
        <label><input type="checkbox" data-i="${i}" data-k="proxied" ${r.proxied ? "checked" : ""}> proxy</label>
      </div>
      <input type="number" data-i="${i}" data-k="ttl" value="${r.ttl}" min="60" title="${t("rec.ttl_title")}">
      <div class="mini">
        <label title="IPv4"><input type="checkbox" data-i="${i}" data-k="ipv4" ${r.ipv4 ? "checked" : ""}>4</label>
        <label title="IPv6"><input type="checkbox" data-i="${i}" data-k="ipv6" ${r.ipv6 ? "checked" : ""}>6</label>
      </div>
      <button class="btn-del" type="button" data-del="${i}" title="${t("rec.del_title")}">×</button>
    </div>`).join("");

  box.querySelectorAll("input[data-k]").forEach(inp => {
    inp.addEventListener("change", () => {
      const i = +inp.dataset.i;
      const k = inp.dataset.k;
      if (inp.type === "checkbox") recordsData[i][k] = inp.checked;
      else if (k === "ttl") recordsData[i][k] = Math.max(60, Math.floor(+inp.value || 60));
      else recordsData[i][k] = inp.value;
    });
  });
  box.querySelectorAll("button[data-del]").forEach(btn => {
    btn.addEventListener("click", () => {
      recordsData.splice(+btn.dataset.del, 1);
      renderRecordsEditor();
    });
  });
}

function recKey(r) {
  const n = (r.name || "").trim().replace(/\.+$/, "");
  const z = (r.zone || "").trim().replace(/\.+$/, "");
  if (!n) return "";
  if (!z) return n.toLowerCase();
  if (n === "@") return z.toLowerCase();
  if (n === z || n.endsWith("." + z)) return n.toLowerCase();
  return (n + "." + z).toLowerCase();
}

/* ย่อชื่อ record เต็ม (เช่น home.example.com) ให้เหลือชื่อสั้น + zone (home) —
   ใช้ตอนเลือก record จาก dropdown "โหลดชื่อ record จาก Cloudflare" */
function shortenName(full, zone) {
  const z = (zone || "").trim().replace(/\.+$/, "").toLowerCase();
  let name = (full || "").trim().replace(/\.+$/, "");
  if (!name) return "";
  if (z && name.toLowerCase() === z) return "@";              // root ของ zone
  if (z && name.toLowerCase().endsWith("." + z)) return name.slice(0, -(z.length + 1));
  return name;
}

async function saveConfig() {
  const btn = $("saveBtn");
  btn.disabled = true;
  const keys = recordsData.map(recKey);
  const dup = keys.find((k, i) => k && keys.indexOf(k) !== i);
  if (dup) {
    toast(t("save.dup", { name: dup }), "err");
    btn.disabled = false;
    return;
  }
  let pwValue = $("webui_password").value.trim();
  if (!pwValue && !pwRemove) pwValue = currentWebuiPassword; // เว้นว่าง = คงรหัสเดิม
  const payload = {
    cloudflare: {
      api_token: $("api_token").value.trim(),
      interval_seconds: Math.max(15, Math.floor(+$("interval").value || 60)),
      use_ipv4: $("use_ipv4").checked,
      use_ipv6: $("use_ipv6").checked,
      ip_consensus: $("ip_consensus").checked,
      reject_cloudflare_ips: $("reject_cf_ips").checked,
      healthchecks_url: $("hc_url").value.trim(),
      uptimekuma_url: $("kuma_url").value.trim(),
      webui_port: Math.max(1, Math.min(65535, Math.floor(+$("webui_port").value || currentWebuiPort))),
      webui_host: $("webui_host").value.trim() || "127.0.0.1",
      webui_password: pwValue,
      log_dir: $("log_dir").value.trim(),
    },
    telegram: {
      bot_token: $("tg_token").value.trim(),
      chat_id: $("tg_chat").value.trim(),
      notify_start: $("notify_start").checked,
      notify_stop: $("notify_stop").checked,
      notify_ip_change: $("notify_ip_change").checked,
      notify_error: $("notify_error").checked,
      notify_created: $("notify_created").checked,
      notify_round: $("notify_round").checked,
      daily_report: $("daily_report").checked,
      daily_report_time: $("daily_report_time").value.trim() || "08:00",
      allow_reset: $("tg_allow_reset").checked,
      command_name: $("tg_cmd_name").value.trim(),
      language: $("tg_language").value || "th",
    },
    tunnel: {
      enabled: $("tunnel_enabled").checked,
      token: $("tunnel_token").value.trim(),
      cloudflared_path: $("cloudflared_path").value.trim(),
      hosts: tunnelHostsData,
    },
    records: recordsData,
  };
  try {
    const r = await fetch("/save-config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const j = await r.json();
    toast(j.ok ? t("save.ok") : t("fail_prefix", { msg: j.message }), j.ok ? "ok" : "err");
    if (j.ok) {
      const pwChanged = pwValue !== currentWebuiPassword;
      const portChanged = payload.cloudflare.webui_port !== currentWebuiPort;
      const removedPw = pwRemove && pwChanged;
      pwRemove = false;
      if (pwChanged) {
        // cookie เก่าใช้ไม่ได้แล้ว — อย่าโหลด config ตอนนี้ (จะ error 401) — login ใหม่แล้ว reload
        toast(removedPw ? t("save.pw_removed") : t("save.pw_set"), "ok");
        setTimeout(async () => {
          if (!removedPw && pwValue) {
            try {
              await fetch("/login", { method: "POST", body: new URLSearchParams({ pw: pwValue }) });
            } catch (e) { logClientError("auto-login หลังเปลี่ยนรหัส", e); }
          }
          location.reload();
        }, 1200);
      } else {
        loadConfig();
        loadStatus();
        if (portChanged) {
          toast(t("save.port_changed"), "ok");
        }
      }
    }
  } catch (e) {
    logClientError("saveConfig", e);
    toast(t("save.fail", { err: e }), "err");
  }
  btn.disabled = false;
}

async function loadIp() {
  const v4 = $("pub-ipv4");
  const v6 = $("pub-ipv6");
  const nat = $("nat-status");
  v4.textContent = t("ip.checking");
  v6.textContent = t("ip.checking");
  nat.textContent = "";
  try {
    const r = await fetch("/ip-check");
    const j = await r.json();
    v4.textContent = j.ipv4 || t("ip.not_found4");
    v6.textContent = j.ipv6 || t("ip.none6");
    if (j.nat) {
      // แดง = CGNAT ของ ISP / IP private (DDNS ใช้ไม่ได้จริง)
      // เขียว = NAT ส่วนตัวในบ้าน (double-nat กี่ชั้นก็ได้) / public (nat 1:1) — ใช้งานได้ปกติ
      const bad = j.nat.nat_type === "cg-nat" || j.nat.nat_type === "private-ip";
      const icon = bad ? "⚠" : "✓";
      nat.innerHTML = '<div class="nat-box ' + (bad ? "err" : "ok") + '"><span class="nat-icon">' + icon + '</span><span class="nat-text">' + escapeHtml(j.nat.message) + "</span></div>";
    }
  } catch (e) {
    logClientError("loadIp", e);
    v4.textContent = t("ip.read_fail", { err: e });
  }
}

async function loadCloudflareRecords() {
  const zone = recordsData.find(r => r.zone)?.zone;
  if (!zone) { toast(t("zone.need"), "err"); return; }
  const btn = $("loadRecords");
  btn.disabled = true;
  try {
    const r = await fetch("/list-records", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ zone }),
    });
    const j = await r.json();
    if (!j.ok) { toast(t("load.records_fail", { msg: j.message }), "err"); btn.disabled = false; return; }
    const sel = $("rec-pick");
    if (!j.records.length) { toast(t("load.no_records"), "err"); btn.disabled = false; return; }
    sel.hidden = false;
    sel.innerHTML = '<option value="">' + t("load.pick_record") + "</option>" +
      j.records.map(n => '<option value="' + escapeHtml(n) + '">' + escapeHtml(n) + "</option>").join("");
    sel.onchange = () => {
      if (!sel.value) return;
      const row = recordsData.find(x => !x.name) || recordsData[recordsData.length - 1];
      row.name = shortenName(sel.value, zone);
      row.zone = zone;
      renderRecordsEditor();
      sel.value = "";
    };
  } catch (e) {
    toast("error: " + e, "err");
  }
  btn.disabled = false;
}

/* ---------- สแกนพอร์ต ---------- */

function loadScanHosts() {
  const sel = $("scan-host");
  const hosts = [];
  for (const r of recordsData) {
    const k = recKey(r);
    if (k) hosts.push(k);
  }
  sel.innerHTML = hosts.length
    ? hosts.map(h => '<option value="' + escapeHtml(h) + '">' + escapeHtml(h) + "</option>").join("")
    : '<option value="">' + t("scan.no_records") + "</option>";
}

async function scanPorts() {
  const host = $("scan-host").value;
  const btn = $("scanBtn");
  if (!host) { toast(t("scan.no_host"), "err"); return; }
  btn.disabled = true;
  const box = $("scan-result");
  box.innerHTML = '<p style="color:var(--muted)">' + t("scan.scanning", { host: escapeHtml(host) }) + "</p>";
  try {
    const r = await fetch("/port-scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ host, ports: $("scan-ports").value.split(",").map(s => s.trim()).filter(Boolean) }),
    });
    const j = await r.json();
    if (!j.ok) { box.innerHTML = '<p style="color:var(--danger)">' + escapeHtml(j.message) + "</p>"; btn.disabled = false; return; }
    const open = j.ports.filter(p => p.status === "open");
    const filtered = j.ports.filter(p => p.status === "filtered");
    const rows = j.ports.map(p => {
      const cls = p.status === "open" ? "ok" : (p.status === "filtered" ? "" : "muted");
      const icon = { open: "🟢", filtered: "⚪", closed: "🔴" }[p.status] || "•";
      const label = { open: t("scan.status_open"), filtered: t("scan.status_filtered"), closed: t("scan.status_closed") }[p.status];
      return '<tr class="' + cls + '"><td class="mono">' + p.port + '</td><td class="mono">' + escapeHtml(p.service || "-") + '</td><td style="white-space:nowrap">' + icon + " " + label + "</td></tr>";
    }).join("");
    box.innerHTML =
      '<div style="border:1px solid var(--border);border-radius:8px;overflow-x:auto"><table class="tbl-w420" style="font-size:0.9rem;width:100%">' +
      '<tr style="background:var(--surface-2)"><th style="padding:6px 10px;text-align:left">' + t("scan.header_port") + '</th><th style="padding:6px 10px;text-align:left">' + t("scan.header_service") + '</th><th style="padding:6px 10px;text-align:left">' + t("scan.header_status") + "</th></tr>" +
      rows + "</table></div>" +
      '<p style="margin-top:8px;font-size:0.85rem;color:var(--ink-2)">' + t("scan.summary", { host: escapeHtml(j.host), ip: escapeHtml(j.ip), open: open.length, closed: j.ports.length - open.length - filtered.length, filtered: filtered.length }) + "</p>";
  } catch (e) {
    logClientError('scanPorts', e);
    box.innerHTML = '<p style="color:var(--danger)">' + t("err_prefix", { err: escapeHtml(e) }) + "</p>";
  }
  btn.disabled = false;
}

async function loadLog() {
  const box = $("logview");
  try {
    const r = await fetch("/log?t=" + Date.now());
    if (!r.ok) {
      if (r.status === 401 || r.status === 403) {
        box.textContent = t("log.session_expired");
      } else {
        box.textContent = t("log.read_fail_http", { status: r.status });
      }
      return;
    }
    box.textContent = await r.text();
    box.scrollTop = box.scrollHeight;
  } catch (e) {
    logClientError('loadLog', e);
    box.textContent = t("log.read_fail", { err: e });
  }
}

async function clearLog() {
  if (!confirm(t("log.clear_confirm"))) return;
  try {
    const r = await fetch("/log-clear", { method: "POST" });
    const j = await r.json();
    toast(j.ok ? j.message : t("log.clear_fail", { msg: j.message }), j.ok ? "ok" : "err");
    if (j.ok) loadLog();
  } catch (e) {
    logClientError("clearLog", e);
    toast(t("err_prefix", { err: e }), "err");
  }
}

async function loadTunnelStatus() {
  try {
    const r = await fetch("/status.json");
    const s = await r.json();
    const tun = s.tunnel || {};
    const box = $("tunnel-status");
    const parts = [];
    if (!tun.enabled) parts.push('<span style="color:var(--muted)">' + t("tunnel.disabled") + "</span>");
    if (!tun.installed) parts.push('<span class="err">' + t("tunnel.not_installed") + "</span>");
    if (tun.running) parts.push('<span class="ok">' + t("tunnel.running", { pid: escapeHtml(String(tun.pid)) }) + "</span>");
    else if (tun.enabled) parts.push('<span>' + t("tunnel.not_running") + "</span>");
    if (tun.installed && tun.version) parts.push('<span style="color:var(--muted)">cloudflared ' + escapeHtml(tun.version) + "</span>");
    box.innerHTML = parts.join(" · ");
    const errBox = $("tunnel-err");
    if (tun.enabled && !tun.running && tun.last_error) {
      errBox.hidden = false;
      errBox.textContent = "⚠ " + tun.last_error;
    } else {
      errBox.hidden = true;
    }
  } catch (e) {
    logClientError('loadTunnelStatus', e);
    $("tunnel-status").textContent = t("tunnel.unreadable", { err: e });
  }
}

async function tunnelLog() {
  const box = $("tunnel-logview");
  const pre = $("tunnel-logpre");
  if (!box.hidden) { box.hidden = true; return; }
  box.hidden = false;
  pre.textContent = t("tunnel.loading");
  try {
    const r = await fetch("/tunnel/log?t=" + Date.now());
    pre.textContent = await r.text();
    pre.scrollTop = pre.scrollHeight;
  } catch (e) {
    pre.textContent = t("log.read_fail", { err: e });
  }
}

async function tunnelHosts() {
  const box = $("tunnel-hosts");
  if (!box.hidden) { box.hidden = true; return; }
  box.hidden = false;
  box.innerHTML = '<p style="color:var(--muted)">' + t("tunnel.loading") + "</p>";
  const token = $("tunnel_token").value.trim();
  if (!token) { box.innerHTML = '<p style="color:var(--muted)">' + t("tunnel.no_token") + "</p>"; return; }
  try {
    const r = await fetch("/tunnel/hostnames", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    });
    const j = await r.json();
    if (!j.ok) { box.innerHTML = '<p style="color:var(--danger)">' + escapeHtml(j.message) + "</p>"; return; }
    if (!j.hostnames.length) {
      box.innerHTML = '<p style="color:var(--muted)">' + t("tunnel.no_hostname") + "</p>";
      return;
    }
    box.innerHTML = '<div style="border:1px solid var(--border);border-radius:8px;overflow-x:auto"><table class="tbl-w480" style="font-size:0.85rem;width:100%">' +
      '<tr style="background:var(--surface-2)"><th style="padding:5px 10px;text-align:left">' + t("tunnel.header_hostname") + '</th><th style="padding:5px 10px;text-align:left">' + t("tunnel.header_type") + '</th><th style="padding:5px 10px;text-align:left">' + t("tunnel.header_service") + '</th><th style="padding:5px 10px"></th></tr>' +
      j.hostnames.map(h =>
        '<tr><td class="mono" style="padding:5px 10px">' + escapeHtml(h.hostname) + escapeHtml(h.path || "") + '</td>' +
        '<td style="padding:5px 10px">' + escapeHtml(h.protocol || "http") + "</td>" +
        '<td class="mono" style="padding:5px 10px;color:var(--muted)">' + escapeHtml(h.service) + "</td>" +
        '<td style="padding:2px 6px;white-space:nowrap">' +
        '<button class="btn-secondary" style="padding:3px 8px;font-size:0.75rem" type="button" data-edit-host="' + escapeHtml(h.hostname) + '" data-edit-path="' + escapeHtml(h.path || "") + '" data-edit-protocol="' + escapeHtml(h.protocol || "http") + '" data-edit-service="' + escapeHtml(h.service || "") + '" title="' + t("tunnel.edit_title") + '">' + t("tunnel.edit") + "</button> " +
        '<button class="btn-del" type="button" data-host="' + escapeHtml(h.hostname) + '" data-path="' + escapeHtml(h.path || "") + '" title="' + t("tunnel.unbind_title") + '">×</button></td></tr>'
      ).join("") + "</table></div>" +
      '<p style="margin-top:6px;font-size:0.8rem;color:var(--muted)">' + t("tunnel.hint") + "</p>";
    box.querySelectorAll("button[data-host]").forEach(b => b.addEventListener("click", async () => {
      if (!confirm(t("tunnel.unbind_confirm", { host: b.dataset.host, path: b.dataset.path }))) return;
      try {
        const rr = await fetch("/tunnel/unbind", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token, hostname: b.dataset.host, path: b.dataset.path }),
        });
        const jj = await rr.json();
        toast(jj.ok ? jj.message : t("fail_prefix", { msg: jj.message }), jj.ok ? "ok" : "err");
        tunnelHosts();
      } catch (e) {
        toast(t("err_prefix", { err: e }), "err");
      }
    }));
    box.querySelectorAll("button[data-edit-host]").forEach(b => b.addEventListener("click", () => editTunnelHost(b)));
  } catch (e) {
    logClientError('tunnelHosts', e);
    box.innerHTML = '<p style="color:var(--danger)">' + t("err_prefix", { err: escapeHtml(e) }) + "</p>";
  }
}

// โหลด dropdown โดเมน (ครั้งแรกเท่านั้น) — ใช้ร่วมกับฟอร์มเพิ่ม/แก้ไข hostname
async function ensureTunnelDomainLoaded() {
  const domainSel = $("th-domain");
  if (domainSel.options.length) return;
  domainSel.innerHTML = '<option value="">' + t("tunnel.loading_domains") + "</option>";
  try {
    const r = await fetch("/tunnel/zones", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}) });
    const j = await r.json();
    if (j.ok && j.zones.length) {
      domainSel.innerHTML = j.zones.map(z => '<option value="' + escapeHtml(z) + '">' + escapeHtml(z) + "</option>").join("");
      await fillSubList("th-sub", "th-domain", "th-sub-list");
    } else {
      domainSel.innerHTML = '<option value="">' + t("tunnel.no_zone_perm") + "</option>";
    }
  } catch (e) {
    logClientError('ensureTunnelDomainLoaded', e);
    domainSel.innerHTML = '<option value="">' + t("tunnel.load_domains_fail") + "</option>";
  }
  domainSel.onchange = loadSubSuggestions;
}

// แก้ไข map hostname: โหลดค่าปัจจุบันลงฟอร์ม "+ เพิ่ม hostname" แล้วผูกซ้ำ (server แทนที่ให้)
async function editTunnelHost(btn) {
  const form = $("tunnel-add-form");
  form.hidden = false;
  // โหลด dropdown โดเมนก่อน (ถ้ายังไม่เคยโหลด — กันตั้งค่าโดเมนไม่ทันแล้วหาย)
  await ensureTunnelDomainLoaded();
  const hostname = btn.dataset.editHost;
  const path = btn.dataset.editPath || "";
  const protocol = btn.dataset.editProtocol || "http";
  const service = btn.dataset.editService || "";
  const dot = hostname.indexOf(".");
  $("th-sub").value = dot > 0 ? hostname.slice(0, dot) : "@";
  $("th-domain").value = hostname.slice(dot + 1);
  $("th-path").value = path;
  $("th-protocol").value = protocol;
  $("th-service").value = service;
  const msg = $("th-msg");
  msg.innerHTML = '<p style="color:var(--ok)">' + t("tunnel.edit_msg", { host: escapeHtml(hostname), path: escapeHtml(path || "") }) + "</p>";
  $("tunnel-add-form").scrollIntoView({ behavior: "smooth", block: "center" });
}

async function tunnelAddHost() {
  const form = $("tunnel-add-form");
  form.hidden = !form.hidden;
  if (form.hidden) return;
  const msg = $("th-msg");
  msg.innerHTML = "";
  await ensureTunnelDomainLoaded();
}

async function fillSubList(subId, domainId, listId) {
  const sub = $(subId);
  const domain = $(domainId).value.trim();
  const list = $(listId);
  list.innerHTML = "";
  if (!domain) return;
  try {
    const r = await fetch("/list-records", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ zone: domain }) });
    const j = await r.json();
    if (!j.ok || !j.records.length) return;
    const names = j.records.map(n => {
      const dot = n.indexOf(".");
      return { full: n, sub: dot > 0 ? n.slice(0, dot) : "@" };
    });
    const subs = [...new Set(names.map(x => x.sub))];
    list.innerHTML = subs.map(s => '<option value="' + escapeHtml(s) + '">' + escapeHtml(s + "." + domain) + "</option>").join("");
  } catch (e) { /* ไม่มีคำแนะนำ ไม่เป็นไร */ }
}

async function loadSubSuggestions() {
  await fillSubList("th-sub", "th-domain", "th-sub-list");
}

async function thBind() {
  const token = $("tunnel_token").value.trim();
  const msg = $("th-msg");
  if (!token) { msg.innerHTML = '<p style="color:var(--danger)">' + t("tunnel.no_token_bind") + "</p>"; return; }
  const sub = $("th-sub").value.trim().replace(/^\.+|\.+$/g, "");
  const domain = $("th-domain").value.trim();
  if (!sub || !domain) { msg.innerHTML = '<p style="color:var(--danger)">' + t("tunnel.need_name_domain") + "</p>"; return; }
  const hostname = sub === "@" ? domain : sub + "." + domain;
  msg.innerHTML = '<p style="color:var(--ok)">' + t("tunnel.binding") + "</p>";
  try {
    const r = await fetch("/tunnel/bind", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        token,
        hostname,
        path: $("th-path").value.trim(),
        protocol: $("th-protocol").value,
        service: $("th-service").value.trim(),
      }),
    });
    const j = await r.json();
    msg.innerHTML = j.ok ? '<p style="color:var(--ok)">✓ ' + escapeHtml(j.message) + "</p>" : '<p style="color:var(--danger)">' + escapeHtml(j.message) + "</p>";
    if (j.ok) { tunnelHosts(); loadTunnelStatus(); }
  } catch (e) {
    logClientError('thBind', e);
    msg.innerHTML = '<p style="color:var(--danger)">error: ' + escapeHtml(e) + "</p>";
  }
}

async function tunnelSync() {
  const token = $("tunnel_token").value.trim();
  if (!token) { toast(t("tunnel.sync_need_token"), "err"); return; }
  try {
    const r = await fetch("/tunnel/sync", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    });
    const j = await r.json();
    toast(j.ok ? j.message : t("fail_prefix", { msg: j.message }), j.ok ? "ok" : "err");
    if (j.ok) loadConfig();
  } catch (e) {
    toast(t("err_prefix", { err: e }), "err");
  }
}

async function tunnelAction(path, okMsg) {
  try {
    const r = await fetch(path, { method: "POST" });
    const j = await r.json();
    toast(j.ok ? okMsg + (j.message ? ": " + j.message : "") : t("fail_prefix", { msg: j.message }), j.ok ? "ok" : "err");
    loadTunnelStatus();
  } catch (e) {
    toast(t("err_prefix", { err: e }), "err");
  }
}

async function tgTest() {
  try {
    const r = await fetch("/notify-test", { method: "POST" });
    const j = await r.json();
    toast(j.ok ? t("tg.test_ok") : t("tg.test_fail", { msg: j.message }), j.ok ? "ok" : "err");
  } catch (e) {
    toast(t("err_prefix", { err: e }), "err");
  }
}

async function tgQueue() {
  const box = $("tg-queue");
  if (!box.hidden) { box.hidden = true; return; }
  try {
    const r = await fetch("/notify-queue");
    const j = await r.json();
    const items = j.queue || [];
    box.hidden = false;
    if (!items.length) {
      box.innerHTML = '<p style="color:var(--muted)">' + t("tg.queue_empty") + "</p>";
      return;
    }
    box.innerHTML = '<div style="border:1px solid var(--border);border-radius:8px;overflow-x:auto"><table class="tbl-w480" style="font-size:0.85rem;width:100%">' +
      '<tr style="background:var(--surface-2)"><th style="padding:5px 10px;text-align:left">#</th><th style="padding:5px 10px;text-align:left">' + t("tg.queue_header_msg") + "</th></tr>" +
      items.map((m, i) => '<tr><td style="padding:5px 10px;color:var(--muted)">' + (i + 1) + '</td><td style="padding:5px 10px;white-space:pre-wrap;word-break:break-all">' + escapeHtml(m) + "</td></tr>").join("") +
      "</table></div>" +
      '<p style="margin-top:6px;font-size:0.85rem;color:var(--muted)">' + t("tg.queue_summary", { n: items.length }) + "</p>";
  } catch (e) {
    toast(t("tg.queue_read_fail", { err: e }), "err");
  }
}

async function tgFlush() {
  try {
    const r = await fetch("/notify-queue/flush", { method: "POST" });
    const j = await r.json();
    toast(j.ok ? t("tg.flush_ok", { sent: j.sent, failed: j.failed }) : t("fail_prefix", { msg: j.message }), j.ok ? (j.failed ? "err" : "ok") : "err");
    tgQueue();
    loadStatus();
  } catch (e) {
    toast(t("err_prefix", { err: e }), "err");
  }
}

async function tgClear() {
  if (!confirm(t("tg.clear_confirm"))) return;
  try {
    const r = await fetch("/notify-queue/clear", { method: "POST" });
    const j = await r.json();
    toast(j.ok ? t("tg.clear_ok") : t("fail_prefix", { msg: j.message }), j.ok ? "ok" : "err");
    tgQueue();
    loadStatus();
  } catch (e) {
    toast("error: " + e, "err");
  }
}

/* ---------- wizard Tunnel ---------- */

let twzStep = 1;
const twzData = { token: "", verified: false };

function openTunnelWizard() {
  $("tunnel-wizard").hidden = false;
  twzStep = 1;
  renderTunnelWizard();
}

function renderTunnelWizard() {
  const dots = document.querySelectorAll("#twz-steps .dot");
  dots.forEach((d, i) => d.classList.toggle("on", i < twzStep));
  const body = $("twz-body");
  const actions = (back, next) =>
    '<div class="wz-actions">' +
    (back ? '<button class="btn-secondary" type="button" id="twz-back">' + t("wz.back") + "</button>" : "<span></span>") +
    (next ? '<button class="btn-primary" type="button" id="twz-next">' + next + "</button>" : "") +
    "</div>";

  if (twzStep === 1) {
    body.innerHTML =
      '<p class="wz-step-title">' + t("twz.title1") + "</p>" +
      '<p class="wz-step-sub">' + t("twz.sub1") + "</p>" +
      '<div class="wz-help">' + t("twz.suit_title") + '<ul style="margin:6px 0 0;padding-left:20px">' +
      t("twz.suit_li").map(x => "<li>" + x + "</li>").join("") +
      "</ul></div>" +
      actions(false, t("twz.start"));
    $("twz-next").addEventListener("click", () => { twzStep = 2; renderTunnelWizard(); });
  }

  else if (twzStep === 2) {
    body.innerHTML =
      '<p class="wz-step-title">' + t("twz.step1_title") + "</p>" +
      '<p class="wz-step-sub">' + t("twz.step1_sub") + "</p>" +
      '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px">' +
      '<button class="btn-secondary" type="button" id="twz-open-zt">' + t("twz.open_zt") + "</button>" +
      '<button class="btn-secondary" type="button" id="twz-help">' + t("twz.how_token") + "</button></div>" +
      '<label class="field">' + t("twz.token_label") + '<textarea id="twz-token" rows="3" class="mono" spellcheck="false" autocomplete="off" placeholder="' + t("twz.token_ph") + '"></textarea></label>' +
      '<div id="twz-msg"></div>' +
      '<div class="wz-help" id="twz-token-steps" hidden><b>' + t("twz.token_steps_title") + "</b><ol>" +
      t("twz.token_step_li").map(x => "<li>" + x + "</li>").join("") +
      "</ol></div>" +
      actions(true, t("twz.verify"));
    $("twz-back").addEventListener("click", () => { twzStep = 1; renderTunnelWizard(); });
    $("twz-open-zt").addEventListener("click", () => window.open("https://one.dash.cloudflare.com/?to=/:account/networks/tunnels", "_blank"));
    $("twz-help").addEventListener("click", () => {
      const h = $("twz-token-steps");
      h.hidden = !h.hidden;
      $("twz-help").textContent = h.hidden ? t("twz.how_token") : t("twz.hide_steps");
    });
    $("twz-next").addEventListener("click", async () => {
      const token = $("twz-token").value.trim();
      if (!token) { $("twz-msg").innerHTML = wzMsg("err", t("twz.need_paste")); return; }
      const btn = $("twz-next");
      btn.disabled = true;
      $("twz-msg").innerHTML = wzMsg("ok", t("twz.checking"));
      try {
        const r = await fetch("/tunnel/test", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token }),
        });
        const j = await r.json();
        if (!j.ok) {
          $("twz-msg").innerHTML = wzMsg("err", t("twz.check_fail", { msg: j.message }));
          btn.disabled = false;
          return;
        }
        twzData.token = token;
        twzData.verified = true;
        $("twz-msg").innerHTML = wzMsg("ok", "✓ " + j.message);
        twzStep = 3;
        renderTunnelWizard();
      } catch (e) {
    logClientError('renderTunnelWizard', e);
        $("twz-msg").innerHTML = wzMsg("err", t("err_prefix", { err: e }));
        btn.disabled = false;
      }
    });
  }

  else if (twzStep === 3) {
    body.innerHTML =
      '<p class="wz-step-title">' + t("twz.step2_title") + "</p>" +
      '<p class="wz-step-sub">' + t("twz.step2_sub") + "</p>" +
      '<div class="grid2">' +
      '<label class="field">' + t("twz.sub_label") + '<input id="twz-sub" type="text" placeholder="' + t("twz.sub_ph") + '" class="mono" list="twz-sub-list"><datalist id="twz-sub-list"></datalist><span style="font-size:0.78rem;color:var(--muted)">' + t("twz.sub_hint") + "</span></label>" +
      '<label class="field">' + t("twz.domain_label") + '<select id="twz-domain" class="wz-zone-select"></select></label></div>' +
      '<label class="field">' + t("twz.path_label") + '<input id="twz-path" type="text" class="mono" placeholder="' + t("twz.path_ph") + '"></label>' +
      '<div class="grid2">' +
      '<label class="field">' + t("twz.type_label") + '<select id="twz-protocol" class="wz-zone-select">' +
      '<option value="http">HTTP</option><option value="https">HTTPS</option><option value="tcp">' + t("twz.type_tcp") + '</option><option value="udp">' + t("twz.type_udp") + "</option>" +
      "</select></label>" +
      '<label class="field">' + t("twz.service_label") + '<input id="twz-service" type="text" class="mono" value="http://localhost:8080"></label></div>' +
      '<p style="margin:2px 0 10px;font-size:0.8rem;color:var(--muted);line-height:1.5">' + t("twz.service_hint") + "</p>" +
      '<div style="margin:8px 0">' +
      '<button class="btn-secondary" type="button" id="twz-load-records">' + t("twz.load_records") + "</button> " +
      '<select id="twz-record-pick" class="wz-zone-select" style="margin-top:6px" hidden></select></div>' +
      '<h3 style="margin-top:14px">' + t("twz.bound_title") + '</h3><div id="twz-bound"><p style="color:var(--muted)">' + t("tunnel.loading") + "</p></div>" +
      '<div id="twz-bind-msg"></div>' +
      '<div style="margin-top:10px"><button class="btn-primary" type="button" id="twz-bind">' + t("twz.binding_btn") + "</button></div>" +
      '<div class="wz-help">' + t("twz.example") + "</div>" +
      actions(true, t("twz.next"));
    $("twz-back").addEventListener("click", () => { twzStep = 2; renderTunnelWizard(); });
    $("twz-next").addEventListener("click", () => { twzStep = 4; renderTunnelWizard(); });

    // โหลดรายชื่อโดเมน (จาก API token หลัก)
    (async () => {
      const sel = $("twz-domain");
      try {
        const r = await fetch("/tunnel/zones", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}) });
        const j = await r.json();
        if (j.ok && j.zones.length) {
          sel.innerHTML = j.zones.map(z => '<option value="' + escapeHtml(z) + '">' + escapeHtml(z) + "</option>").join("");
          await fillSubList("twz-sub", "twz-domain", "twz-sub-list");
        } else {
          sel.innerHTML = '<option value="">' + t("tunnel.no_zone_perm") + "</option>";
        }
      } catch (e) {
    logClientError('renderTunnelWizard', e);
        sel.innerHTML = '<option value="">' + t("tunnel.load_domains_fail") + "</option>";
      }
      sel.onchange = () => fillSubList("twz-sub", "twz-domain", "twz-sub-list");
    })();

    $("twz-protocol").addEventListener("change", () => adaptServiceToProtocol($("twz-protocol"), $("twz-service")));
    $("twz-bind").addEventListener("click", async () => {
      const sub = $("twz-sub").value.trim().replace(/^\.+|\.+$/g, "");
      const domain = $("twz-domain").value.trim();
      const path = $("twz-path").value.trim();
      const protocol = $("twz-protocol").value;
      const service = $("twz-service").value.trim();
      const msg = $("twz-bind-msg");
      if (!sub || !domain) { msg.innerHTML = wzMsg("err", t("twz.need_name")); return; }
      const hostname = sub === "@" ? domain : sub + "." + domain;
      const btn = $("twz-bind");
      btn.disabled = true;
      msg.innerHTML = wzMsg("ok", t("twz.binding", { host: hostname, path: path || "" }));
      try {
        const r = await fetch("/tunnel/bind", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token: twzData.token, hostname, path, protocol, service }),
        });
        const j = await r.json();
        msg.innerHTML = j.ok ? wzMsg("ok", "✓ " + j.message) : wzMsg("err", j.message);
        if (j.ok) loadTwzBound();
      } catch (e) {
    logClientError('renderTunnelWizard', e);
        msg.innerHTML = wzMsg("err", t("err_prefix", { err: e }));
      }
      btn.disabled = false;
    });

    // เลือกชื่อจาก record ที่มีอยู่ (รายการ DNS ปัจจุบัน)
    $("twz-load-records").addEventListener("click", async () => {
      const domain = $("twz-domain").value.trim();
      if (!domain) { toast(t("wz.need_zone"), "err"); return; }
      const btn = $("twz-load-records");
      btn.disabled = true;
      try {
        const r = await fetch("/list-records", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ zone: domain }),
        });
        const j = await r.json();
        if (!j.ok) { toast(t("load.records_fail", { msg: j.message }), "err"); btn.disabled = false; return; }
        const sel = $("twz-record-pick");
        sel.hidden = false;
        sel.innerHTML = '<option value="">' + t("twz.pick_record") + "</option>" +
          j.records.map(n => '<option value="' + escapeHtml(n) + '">' + escapeHtml(n) + "</option>").join("");
        sel.onchange = () => {
          const h = sel.value;
          if (!h) return;
          const dot = h.indexOf(".");
          $("twz-sub").value = dot > 0 ? h.slice(0, dot) : "@";
          $("twz-domain").value = h.slice(dot + 1);
        };
      } catch (e) {
        toast("error: " + e, "err");
      }
      btn.disabled = false;
    });

    loadTwzBound();
  }

  else if (twzStep === 4) {
    body.innerHTML =
      '<p class="wz-step-title">' + t("twz.step3_title") + "</p>" +
      '<p class="wz-step-sub">' + t("twz.step3_sub") + "</p>" +
      '<div class="wz-help">' +
      t("twz.token_ok") +
      t("twz.cf_ready") +
      t("twz.autostart") + "</div>" +
      '<div id="twz-save-msg"></div>' +
      actions(true, t("twz.save_start"));
    $("twz-back").addEventListener("click", () => { twzStep = 3; renderTunnelWizard(); });
    $("twz-next").addEventListener("click", async () => {
      const btn = $("twz-next");
      btn.disabled = true;
      $("twz-save-msg").innerHTML = wzMsg("ok", t("twz.saving"));
      try {
        const r = await fetch("/config.json");
        const cfg = await r.json();
        const oldTun = cfg.tunnel || {};
        cfg.tunnel = { enabled: true, token: twzData.token, cloudflared_path: oldTun.cloudflared_path || "", hosts: oldTun.hosts || [] };
        const s = await fetch("/save-config", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(cfg),
        });
        const sj = await s.json();
        if (!sj.ok) {
          $("twz-save-msg").innerHTML = wzMsg("err", t("twz.save_fail", { msg: sj.message }));
          btn.disabled = false;
          return;
        }
        const st = await fetch("/tunnel/start", { method: "POST" });
        const stj = await st.json();
        toast(stj.ok ? t("twz.done", { msg: stj.message }) : t("twz.save_but_start_fail", { msg: stj.message }), stj.ok ? "ok" : "err");
        $("tunnel-wizard").hidden = true;
        loadConfig();
        loadTunnelStatus();
      } catch (e) {
    logClientError('renderTunnelWizard', e);
        $("twz-save-msg").innerHTML = wzMsg("err", t("err_prefix", { err: e }));
        btn.disabled = false;
      }
    });
  }
}

async function loadTwzBound() {
  const box = $("twz-bound");
  if (!box) return;
  try {
    const r = await fetch("/tunnel/hostnames", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: twzData.token }),
    });
    const j = await r.json();
    if (!j.ok) { box.innerHTML = '<p style="color:var(--danger)">' + escapeHtml(j.message) + "</p>"; return; }
    if (!j.hostnames.length) {
      box.innerHTML = '<p style="color:var(--muted)">' + t("twz.no_bound") + "</p>";
      return;
    }
    box.innerHTML = j.hostnames.map(h =>
      '<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;padding:6px 10px;background:var(--surface-2);border-radius:8px;margin-bottom:6px;flex-wrap:wrap">' +
      '<span class="mono">' + escapeHtml(h.hostname) + escapeHtml(h.path || "") + '</span>' +
      '<span style="color:var(--muted);font-size:0.8rem">' + escapeHtml((h.protocol || "http") + "://" + (h.service || "").split("://").pop()) + "</span>" +
      '<button class="btn-del" type="button" data-host="' + escapeHtml(h.hostname) + '" data-path="' + escapeHtml(h.path || "") + '" title="' + t("tunnel.unbind_title") + '">×</button></div>'
    ).join("");
    box.querySelectorAll("button[data-host]").forEach(b => b.addEventListener("click", async () => {
      if (!confirm(t("tunnel.unbind_confirm", { host: b.dataset.host, path: b.dataset.path }))) return;
      try {
        const rr = await fetch("/tunnel/unbind", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token: twzData.token, hostname: b.dataset.host, path: b.dataset.path }),
        });
        const jj = await rr.json();
        toast(jj.ok ? jj.message : t("fail_prefix", { msg: jj.message }), jj.ok ? "ok" : "err");
        loadTwzBound();
      } catch (e) {
        toast(t("err_prefix", { err: e }), "err");
      }
    }));
  } catch (e) {
    logClientError('loadTwzBound', e);
    box.innerHTML = '<p style="color:var(--danger)">' + t("err_prefix", { err: escapeHtml(e) }) + "</p>";
  }
}

/* ---------- โหมดแก้ไขไฟล์โดยตรง ---------- */

let fileLoaded = false;

function setMode(mode) {
  const isForm = mode === "form";
  $("form-view").hidden = !isForm;
  $("file-view").hidden = isForm;
  $("mode-form").classList.toggle("active", isForm);
  $("mode-file").classList.toggle("active", !isForm);
  $("saveBtn").style.display = isForm ? "" : "none";
  $("saveFileBtn").style.display = isForm ? "none" : "";
  if (!isForm && !fileLoaded) {
    loadFileMode();
  }
}

async function loadFileMode() {
  try {
    const r = await fetch("/config-file");
    $("file-editor").value = await r.text();
    fileLoaded = true;
  } catch (e) {
    toast(t("file.load_fail", { err: e }), "err");
  }
}

async function saveFileMode() {
  const btn = $("saveFileBtn");
  btn.disabled = true;
  try {
    const r = await fetch("/save-file", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: $("file-editor").value }),
    });
    const j = await r.json();
    toast(j.ok ? t("file.save_ok") : t("fail_prefix", { msg: j.message }), j.ok ? "ok" : "err");
    if (j.ok) loadStatus();
  } catch (e) {
    toast(t("save.fail", { err: e }), "err");
  }
  btn.disabled = false;
}

/* ---------- wizard ตั้งค่าครั้งแรก ---------- */

let wzStep = 1;
let wzZones = [];
const wzData = { token: "", zone: "", records: [] };

async function checkSetup() {
  try {
    const r = await fetch("/setup-state");
    const s = await r.json();
    if (s.needs_setup) {
      $("wizard").hidden = false;
      wzStep = 1;
      renderWizard();
    }
  } catch (e) { /* ยังไม่พร้อม ค่อยเช็คใหม่ */ }
}

function closeWizard() {
  $("wizard").hidden = true;
}

function wzMsg(kind, text) {
  return '<div class="' + (kind === "ok" ? "wz-ok-box" : "wz-err-box") + '">' + escapeHtml(text) + "</div>";
}

function renderWizard() {
  const dots = document.querySelectorAll("#wz-steps .dot");
  dots.forEach((d, i) => d.classList.toggle("on", i < wzStep));
  const body = $("wz-body");
  const actions = (back, next) =>
    '<div class="wz-actions">' +
    (back ? '<button class="btn-secondary" type="button" id="wz-back">' + t("wz.back") + "</button>" : "<span></span>") +
    (next ? '<button class="btn-primary" type="button" id="wz-next">' + next + "</button>" : "") +
    "</div>";

  if (wzStep === 1) {
    body.innerHTML =
      '<p class="wz-step-title">' + t("wz.title") + "</p>" +
      '<p class="wz-step-sub">' + t("wz.sub1") + "</p>" +
      actions(false, t("wz.start"));
    $("wz-next").addEventListener("click", () => { wzStep = 2; renderWizard(); });
  }

  else if (wzStep === 2) {
    body.innerHTML =
      '<p class="wz-step-title">' + t("wz.step1_title") + "</p>" +
      '<p class="wz-step-sub">' + t("wz.step1_sub") + "</p>" +
      '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px">' +
      '<button class="btn-secondary" type="button" id="wz-open-token">' + t("wz.open_token") + "</button>" +
      '<button class="btn-secondary" type="button" id="wz-token-help">' + t("wz.how_token") + "</button></div>" +
      '<label class="field">API Token<input id="wz-token" type="password" autocomplete="off" placeholder="cfut_..."></label>' +
      '<div id="wz-token-msg"></div>' +
      '<div class="wz-help" id="wz-token-steps" hidden><b>' + t("wz.token_steps_title") + "</b><ol>" +
      t("wz.token_step_li").map(x => "<li>" + x + "</li>").join("") +
      "</ol></div>" +
      actions(true, t("wz.verify"));
    $("wz-back").addEventListener("click", () => { wzStep = 1; renderWizard(); });
    $("wz-open-token").addEventListener("click", () => window.open("https://dash.cloudflare.com/profile/api-tokens", "_blank"));
    $("wz-token-help").addEventListener("click", () => {
      const h = $("wz-token-steps");
      h.hidden = !h.hidden;
      $("wz-token-help").textContent = h.hidden ? t("wz.how_token") : t("wz.hide_steps");
    });
    $("wz-next").addEventListener("click", async () => {
      const token = $("wz-token").value.trim();
      if (!token) { $("wz-token-msg").innerHTML = wzMsg("err", t("wz.need_token")); return; }
      $("wz-next").disabled = true;
      $("wz-token-msg").innerHTML = wzMsg("ok", t("wz.checking_token"));
      try {
        const r = await fetch("/verify-token", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token }),
        });
        const j = await r.json();
        if (!j.ok) {
          $("wz-token-msg").innerHTML = wzMsg("err", t("wz.verify_fail", { msg: j.message }));
          $("wz-next").disabled = false;
          return;
        }
        wzData.token = token;
        wzZones = j.zones || [];
        wzStep = 3;
        renderWizard();
      } catch (e) {
    logClientError('renderWizard', e);
        $("wz-token-msg").innerHTML = wzMsg("err", t("wz.server_err", { err: e }));
        $("wz-next").disabled = false;
      }
    });
  }

  else if (wzStep === 3) {
    if (!wzData.records.length) {
      wzData.records = [{ name: "", proxied: false, ttl: 60 }];
    }
    const zoneOptions = wzZones.length
      ? '<select id="wz-zone" class="wz-zone-select">' + wzZones.map(z => '<option value="' + escapeHtml(z) + '">' + escapeHtml(z) + "</option>").join("") + "</select>"
      : '<input id="wz-zone" type="text" class="wz-zone-select" placeholder="example.com">';
    body.innerHTML =
      '<p class="wz-step-title">' + t("wz.step2_title") + "</p>" +
      '<p class="wz-step-sub">' + t("wz.step2_sub") + "</p>" +
      '<label class="field">' + t("wz.zone_label") + zoneOptions + "</label>" +
      '<div style="margin:2px 0 10px">' +
      '<button class="btn-secondary" type="button" id="wz-load-records">' + t("wz.load_records") + "</button> " +
      '<select id="wz-record-pick" class="wz-zone-select" style="margin-top:6px" hidden></select></div>' +
      '<h3 style="margin-top:16px">' + t("wz.rec_title") + '</h3><div id="wz-records"></div>' +
      '<button class="btn-secondary" type="button" id="wz-add-record">' + t("wz.add_record") + "</button>" +
      actions(true, t("wz.next"));
    $("wz-back").addEventListener("click", () => { wzStep = 2; renderWizard(); });
    $("wz-add-record").addEventListener("click", () => {
      wzData.records.push({ name: "", proxied: false, ttl: 60 });
      renderWzRecords();
    });
    $("wz-load-records").addEventListener("click", async () => {
      const zone = ($("wz-zone").value || "").trim();
      if (!zone) { toast(t("wz.need_zone"), "err"); return; }
      const btn = $("wz-load-records");
      btn.disabled = true;
      try {
        const r = await fetch("/list-records", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token: wzData.token, zone }),
        });
        const j = await r.json();
        if (!j.ok) { toast(t("load.records_fail", { msg: j.message }), "err"); btn.disabled = false; return; }
        const sel = $("wz-record-pick");
        sel.hidden = false;
        sel.innerHTML = '<option value="">' + t("load.pick_record") + "</option>" +
          j.records.map(n => '<option value="' + escapeHtml(n) + '">' + escapeHtml(n) + "</option>").join("");
        sel.onchange = () => {
          if (!sel.value) return;
          const row = wzData.records.find(x => !x.name) || wzData.records[0];
          row.name = shortenName(sel.value, $("wz-zone").value);
          renderWzRecords();
          sel.value = "";
        };
      } catch (e) {
        toast("error: " + e, "err");
      }
      btn.disabled = false;
    });
    renderWzRecords();
    $("wz-next").addEventListener("click", () => {
      const zoneSel = $("wz-zone");
      wzData.zone = (zoneSel.value || "").trim();
      if (!wzData.zone) { toast(t("wz.need_zone"), "err"); return; }
      const recs = wzData.records.map((r, i) => ({
        name: r.name,
        zone: wzData.zone,
        proxied: r.proxied,
        ttl: r.ttl,
        ipv4: true,
        ipv6: true,
      }));
      if (!recs.length || !recs[0].name) { toast(t("wz.need_rec_name"), "err"); return; }
      const keys = recs.map(recKey);
      const dup = keys.find((k, i) => k && keys.indexOf(k) !== i);
      if (dup) { toast(t("save.dup", { name: dup }), "err"); return; }
      wzData.records = recs;
      wzStep = 4;
      renderWizard();
    });
  }

  else if (wzStep === 4) {
    body.innerHTML =
      '<p class="wz-step-title">' + t("wz.step3_title") + "</p>" +
      '<p class="wz-step-sub">' + t("wz.step3_sub") + "</p>" +
      '<label class="field">' + t("wz.tg_token_label") + '<input id="wz-tg-token" type="password" autocomplete="off" placeholder="123456789:AAHxxx..."></label>' +
      '<div id="wz-tg-msg"></div>' +
      '<label class="field">' + t("wz.tg_chat_label") + '<input id="wz-tg-chat" type="text" class="mono" autocomplete="off" placeholder="123456789"></label>' +
      '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px">' +
      '<button class="btn-secondary" type="button" id="wz-tg-find">' + t("wz.tg_find") + "</button>" +
      '<button class="btn-secondary" type="button" id="wz-tg-test" disabled>' + t("wz.tg_test") + "</button></div>" +
      '<div class="wz-help">' + t("wz.tg_help") + "</div>" +
      actions(true, t("wz.skip"));
    $("wz-back").addEventListener("click", () => { wzStep = 3; renderWizard(); });
    let chatId = "";
    const setChat = (id) => {
      chatId = id;
      $("wz-tg-chat").value = id;
      $("wz-tg-test").disabled = !(id && $("wz-tg-token").value.trim());
    };
    $("wz-tg-chat").addEventListener("input", () => {
      const id = $("wz-tg-chat").value.trim();
      chatId = id;
      $("wz-tg-test").disabled = !(id && $("wz-tg-token").value.trim());
    });
    $("wz-tg-find").addEventListener("click", async () => {
      const token = $("wz-tg-token").value.trim();
      if (!token) { $("wz-tg-msg").innerHTML = wzMsg("err", t("wz.need_tg_token")); return; }
      $("wz-tg-msg").innerHTML = wzMsg("ok", t("wz.searching"));
      try {
        const r = await fetch("/resolve-chat-id", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ bot_token: token }),
        });
        const j = await r.json();
        if (!j.ok) { $("wz-tg-msg").innerHTML = wzMsg("err", t("wz.tg_manual", { msg: j.message })); return; }
        setChat(j.chat_id);
        $("wz-tg-msg").innerHTML = wzMsg("ok", t("wz.tg_found", { id: j.chat_id }));
      } catch (e) { $("wz-tg-msg").innerHTML = wzMsg("err", t("err_prefix", { err: e })); }
    });
    $("wz-tg-test").addEventListener("click", async () => {
      const token = $("wz-tg-token").value.trim();
      try {
        const r = await fetch("/notify-test-raw", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ bot_token: token, chat_id: chatId, text: t("wz.tg_test_text") }),
        });
        const j = await r.json();
        $("wz-tg-msg").innerHTML = j.ok ? wzMsg("ok", t("tg.test_ok")) : wzMsg("err", t("wz.tg_send_fail", { msg: j.message }));
      } catch (e) { $("wz-tg-msg").innerHTML = wzMsg("err", t("err_prefix", { err: e })); }
    });
    $("wz-next").addEventListener("click", () => {
      wzData.tg = { token: $("wz-tg-token").value.trim(), chat_id: chatId || $("wz-tg-chat").value.trim() };
      wzStep = 5;
      renderWizard();
    });
  }

  else if (wzStep === 5) {
    const tgOn = !!(wzData.tg && wzData.tg.token && wzData.tg.chat_id);
    body.innerHTML =
      '<p class="wz-step-title">' + t("wz.step4_title") + "</p>" +
      '<p class="wz-step-sub">' + t("wz.step4_sub") + "</p>" +
      '<div class="wz-help">' +
      t("wz.token_ok") +
      t("wz.zone_line", { zone: escapeHtml(wzData.zone) }) +
      t("wz.records_line", { n: wzData.records.length, names: wzData.records.map(r => escapeHtml(r.name)).join(", ") }) +
      t("wz.tg_line", { state: tgOn ? t("wz.tg_on", { id: escapeHtml(wzData.tg.chat_id) }) : t("wz.tg_off") }) + "</div>" +
      '<div id="wz-save-msg"></div>' +
      actions(true, t("wz.save_start"));
    $("wz-back").addEventListener("click", () => { wzStep = 4; renderWizard(); });
    $("wz-next").addEventListener("click", async () => {
      const btn = $("wz-next");
      btn.disabled = true;
      // เก็บค่าที่ตั้งไว้เดิม (webui_port/log_dir/tunnel/daily_report ฯลฯ) — กัน wizard ทับของเก่า
      let existing = { cloudflare: {}, telegram: {}, tunnel: { hosts: [] } };
      try {
        existing = await (await fetch("/config.json")).json();
      } catch (e) { /* config ยังไม่มี -> ใช้ค่าเริ่มต้น */ }
      const tgl = existing.telegram || {};
      const tun = existing.tunnel || {};
      const payload = {
        cloudflare: {
          api_token: wzData.token,
          interval_seconds: existing.cloudflare.interval_seconds || 60,
          use_ipv4: existing.cloudflare.use_ipv4 !== false,
          use_ipv6: existing.cloudflare.use_ipv6 !== false,
          ip_consensus: existing.cloudflare.ip_consensus === true,
          reject_cloudflare_ips: existing.cloudflare.reject_cloudflare_ips !== false,
          healthchecks_url: existing.cloudflare.healthchecks_url || "",
          uptimekuma_url: existing.cloudflare.uptimekuma_url || "",
          webui_port: existing.cloudflare.webui_port || 8123,
          webui_host: existing.cloudflare.webui_host || "127.0.0.1",
          webui_password: existing.cloudflare.webui_password || "",
          log_dir: existing.cloudflare.log_dir || "",
        },
        telegram: {
          bot_token: (wzData.tg && wzData.tg.token) || tgl.bot_token || "",
          chat_id: (wzData.tg && wzData.tg.chat_id) || tgl.chat_id || "",
          notify_start: tgl.notify_start !== false,
          notify_stop: tgl.notify_stop !== false,
          notify_ip_change: tgl.notify_ip_change !== false,
          notify_error: tgl.notify_error !== false,
          notify_created: tgl.notify_created !== false,
          notify_round: tgl.notify_round === true,
          daily_report: tgl.daily_report !== false,
          daily_report_time: tgl.daily_report_time || "08:00",
          allow_reset: tgl.allow_reset === true,
          command_name: tgl.command_name || "",
          language: tgl.language || "th",
        },
        tunnel: {
          enabled: !!tun.enabled,
          token: tun.token || "",
          cloudflared_path: tun.cloudflared_path || "",
          hosts: tun.hosts || [],
        },
        records: wzData.records,
      };
      try {
        const r = await fetch("/save-config", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const j = await r.json();
        if (!j.ok) {
          $("wz-save-msg").innerHTML = wzMsg("err", t("wz.save_fail", { msg: j.message }));
          btn.disabled = false;
          return;
        }
        toast(t("wz.done"), "ok");
        closeWizard();
        loadStatus();
        loadConfig();
      } catch (e) {
    logClientError('renderWizard', e);
        $("wz-save-msg").innerHTML = wzMsg("err", t("err_prefix", { err: e }));
        btn.disabled = false;
      }
    });
  }
  addEyeToggles();
}

function renderWzRecords() {
  const box = $("wz-records");
  box.innerHTML = wzData.records.map((r, i) =>
    '<div class="rec-edit">' +
    '<input type="text" data-i="' + i + '" data-k="name" value="' + escapeHtml(r.name) + '" placeholder="' + t("rec.placeholder_name") + '">' +
    '<div class="mini" title="' + t("rec.proxy_title") + '"><label><input type="checkbox" data-i="' + i + '" data-k="proxied" ' + (r.proxied ? "checked" : "") + "> proxy</label></div>" +
    '<input type="number" data-i="' + i + '" data-k="ttl" value="' + r.ttl + '" min="60" title="' + t("rec.ttl_title") + '">' +
    '<button class="btn-del" type="button" data-del="' + i + '" title="' + t("rec.del_title") + '">×</button></div>').join("");

  box.querySelectorAll("input[data-k]").forEach(inp => {
    inp.addEventListener("change", () => {
      const i = +inp.dataset.i;
      const k = inp.dataset.k;
      if (inp.type === "checkbox") wzData.records[i][k] = inp.checked;
      else if (k === "ttl") wzData.records[i][k] = Math.max(60, Math.floor(+inp.value || 60));
      else wzData.records[i][k] = inp.value;
    });
  });
  box.querySelectorAll("button[data-del]").forEach(btn => {
    btn.addEventListener("click", () => {
      if (wzData.records.length > 1) {
        wzData.records.splice(+btn.dataset.del, 1);
        renderWzRecords();
      }
    });
  });
}

$("mode-form").addEventListener("click", () => setMode("form"));
$("mode-file").addEventListener("click", () => setMode("file"));
$("saveFileBtn").addEventListener("click", saveFileMode);
$("loadRecords").addEventListener("click", loadCloudflareRecords);
$("wz-skip").addEventListener("click", closeWizard);

$("logReload").addEventListener("click", loadLog);
$("logClear").addEventListener("click", clearLog);
$("recheckIp").addEventListener("click", loadIp);
$("scanBtn").addEventListener("click", scanPorts);
$("saveBtn").addEventListener("click", saveConfig);
$("addRecord").addEventListener("click", () => {
  recordsData.push({ name: "", zone: "", proxied: false, ttl: 60, ipv4: true, ipv6: true });
  renderRecordsEditor();
});
$("tgTest").addEventListener("click", tgTest);
$("tgQueueBtn").addEventListener("click", tgQueue);
$("tgFlushBtn").addEventListener("click", tgFlush);
$("tgClearBtn").addEventListener("click", tgClear);
$("tunnelStart").addEventListener("click", () => tunnelAction("/tunnel/start", t("tunnel.action_start")));
$("tunnelStop").addEventListener("click", () => tunnelAction("/tunnel/stop", t("tunnel.action_stop")));
$("tunnelDownload").addEventListener("click", () => tunnelAction("/tunnel/download", t("tunnel.action_download")));
$("tunnelWizard").addEventListener("click", openTunnelWizard);
$("tunnelHostsBtn").addEventListener("click", tunnelHosts);
$("tunnelLogBtn").addEventListener("click", tunnelLog);
$("tunnelAddHost").addEventListener("click", tunnelAddHost);
$("tunnelSync").addEventListener("click", tunnelSync);
$("th-bind").addEventListener("click", thBind);
$("th-cancel").addEventListener("click", () => { $("tunnel-add-form").hidden = true; });
$("twz-close").addEventListener("click", () => { $("tunnel-wizard").hidden = true; });
$("svcInstall").addEventListener("click", () => svcAction("/service/install", t("svc.install_confirm")));
$("svcRestart").addEventListener("click", () => svcAction("/service/restart", t("svc.restart_confirm")));
$("svcStart").addEventListener("click", () => svcAction("/service/start", t("svc.start_confirm")));
$("svcStop").addEventListener("click", () => svcAction("/service/stop", t("svc.stop_confirm")));
$("svcUninstall").addEventListener("click", () => {
  if (!confirm(t("svc.uninstall_confirm"))) return;
  svcAction("/service/uninstall", t("svc.uninstall_confirm2"));
});
$("ddnsRun").addEventListener("click", ddnsRunNow);
$("openFolder").addEventListener("click", openDataFolder);
$("refresh").addEventListener("click", refreshAll);
$("heartbeatTest").addEventListener("click", heartbeatTest);
$("tunnelUpdateCheck").addEventListener("click", tunnelUpdateCheck);
$("exportCfg").addEventListener("click", exportConfig);
$("pwClear").addEventListener("click", () => {
  pwRemove = true;
  $("webui_password").value = "";
  $("pwClear").style.display = "none";
  toast(t("pw.clear_hint"), "ok");
});
$("webui_password").addEventListener("input", () => {
  pwRemove = false;
  $("pwClear").style.display = currentWebuiPassword ? "" : "none";
});
$("importCfg").addEventListener("click", () => $("importCfgFile").click());
$("importCfgFile").addEventListener("change", importConfigFile);

function heartbeatTest() {
  fetch("/heartbeat-test", { method: "POST" })
    .then(r => r.json())
    .then(j => toast(t("heartbeat.test", { msg: j.message }), j.ok ? "ok" : "err"))
    .catch(e => toast(t("heartbeat.test_fail", { err: e }), "err"));
}

function tunnelUpdateCheck() {
  fetch("/tunnel/update-check", { method: "POST" })
    .then(r => r.json())
    .then(j => toast(j.message, j.ok ? "ok" : "err"))
    .catch(e => toast(t("update.check_fail", { err: e }), "err"));
}

async function exportConfig() {
  try {
    const r = await fetch("/config-file");
    const text = await r.text();
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "config.ini";
    a.click();
    URL.revokeObjectURL(a.href);
  } catch (e) {
    toast(t("cfg.export_fail", { err: e }), "err");
  }
}

async function importConfigFile(event) {
  const file = event.target.files && event.target.files[0];
  event.target.value = "";
  if (!file) return;
  const text = await file.text();
  try {
    const r = await fetch("/save-file", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    const j = await r.json();
    toast(j.ok ? t("cfg.import_ok", { msg: j.message }) : t("cfg.import_fail", { msg: j.message }), j.ok ? "ok" : "err");
    if (j.ok) setTimeout(() => location.reload(), 1200);
  } catch (e) {
    toast(t("cfg.import_err", { err: e }), "err");
  }
}

/* โหลดทุกส่วนใหม่หมด (ปุ่มรีเฟรช) — เหมือนตอนเปิดหน้าแรก */
function refreshAll() {
  loadStatus();
  loadConfig();
  loadIp();
  loadLog();
  loadTunnelStatus();
  loadServiceStatus();
}

/* ============ ภาษา (ปุ่มสลับ TH/EN) ============ */

document.documentElement.lang = LANG;
i18nApply();
(function initLangSwitch() {
  const sw = $("lang-switch");
  if (!sw) return;
  sw.querySelectorAll("button.lang-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.lang === LANG);
    btn.addEventListener("click", () => { if (btn.dataset.lang !== LANG) setLang(btn.dataset.lang); });
  });
})();

loadStatus();
loadConfig();
loadIp();
loadLog();
loadTunnelStatus();
loadServiceStatus();
checkUpdate();
checkSetup();
addEyeToggles();
setInterval(loadStatus, 10000);
setInterval(loadServiceStatus, 10000);
