# AGENTS.md — คู่มือ AI Agent สำหรับโปรเจกต์ Cloudflare DDNS Updater

คู่มือนี้สำหรับ AI agent (Claude Code / opencode / Codex ฯลฯ) ที่จะทำงานในโปรเจกต์นี้ — **อ่านให้ครบก่อนแก้โค้ด** โดยเฉพาะส่วน "กับดักที่พบบ่อย" (มีประวัติเจอจริงทุกข้อ)

---

## 1. โปรเจกต์นี้คืออะไร

Cloudflare DDNS Updater: โปรแกรม Python รันเป็น **Windows Service** ตรวจหา IP สาธารณะ (IPv4/IPv6) แล้วอัปเดต DNS record บน Cloudflare อัตโนมัติเมื่อ IP เปลี่ยน + **Web UI** (localhost) ดูสถานะ/ตั้งค่า + **Telegram notify** + **Cloudflare Tunnel** (cloudflared) + สแกนพอร์ต

- ใช้ **stdlib ล้วน** (urllib, http.server, socket, configparser) + `pywin32` เท่านั้น — **ห้ามเพิ่ม dependency** (ไม่ใช้ requests/fastapi/flask)
- Build เป็น exe ไฟล์เดียวด้วย PyInstaller (`build.bat`)
- เอกสารผู้ใช้: `README.md`, `docs/` (GETTING-STARTED / USAGE / TROUBLESHOOTING), `CHANGELOG.md`
- ทุกอย่างภาษาไทย (UI + log + เอกสาร) — ศัพท์เทคนิคอังกฤษได้

## 2. โครงสร้างไฟล์

```
D:\MyCode\Cloudflare\
├── cloudflare_ddns\
│   ├── main.py            # entry: setup/run/dry-run/install/start/stop/restart/remove/status/webui/notify-test
│   ├── config.py          # Config class: อ่าน/validate/save config.ini + fqdn_name + migrate_legacy_data
│   ├── ddns.py            # DDNSEngine: loop ตรวจ IP -> เทียบ cache -> อัปเดต CF; daily report; run_forever
│   ├── ip_detect.py       # get_public_ip(4/6) + nat_report (STUN) + is_cgnat/is_private
│   ├── cloudflare_api.py  # CloudflareAPI: verify_token / zones / records CRUD (urllib ล้วน)
│   ├── notifier.py        # TelegramNotifier: notify(event) -> build_message -> queue (atomic) + flush
│   ├── tunnel.py          # TunnelManager: cloudflared download/start/stop/status (pid ใน tunnel.pid)
│   ├── service.py         # Windows Service (pywin32): SvcDoRun -> webui thread + ddns loop + tunnel async
│   └── webui.py           # Web UI ทั้งหมดในไฟล์เดียว: PAGE (HTML+CSS+JS) + handlers + wizard
├── dist\cloudflare-ddns.exe   # exe ที่ build แล้ว (ข้อมูล runtime อยู่ข้าง exe)
├── config.ini / state.json / notify_queue.json / tunnel.pid / logs\  # runtime (gitignored)
├── config.example.ini
├── build.bat / install.bat / uninstall.bat
├── ui-check.mjs / ui-verify.mjs   # เทสต์ responsive ด้วย playwright (ต้อง npm i playwright ในโฟลเดอร์แยก)
└── docs\ (GETTING-STARTED/USAGE/TROUBLESHOOTING) · CHANGELOG.md · LICENSE · PRODUCT.md · DESIGN.md
```

### webui.py — ไฟล์เดียวมี 3 ส่วน (ระวังที่สุด)
1. **PAGE** (Python triple-quote string): HTML+CSS+JS ทั้งหมด — placeholder `__LOGIN__`, `__VERSION__` (แทนด้วย `.replace()`)
2. **handlers** (`do_GET` / `do_POST`): endpoints ทั้งหมด
3. helper: `_cfg_to_dict` / `_dict_to_ini` (แปลง config <-> JSON)

> ตั้งแต่ v1.7.20+ หน้าเว็บแยกเป็นไฟล์: `webui.html` (HTML+CSS) + `webui.js` (script แยก) + `webui_login.html` (หน้า login) — PyInstaller ต้อง `--add-data` ทั้ง 3 (build.bat มีแล้ว) — แก้ JS = แก้ `webui.js` + `node --check` ตรง ๆ ไม่ต้องสกัดจาก PAGE

## 3. คำสั่ง (ใช้ `python -m cloudflare_ddns.main <cmd>` หรือ `dist\cloudflare-ddns.exe <cmd>`)

| คำสั่ง | ความหมาย |
|---|---|
| `setup` | wizard ตั้งค่าครั้งแรก (console) — เปิดเบราว์เซอร์ + ถาม token/zone/record/Telegram |
| `run` | รัน foreground (เทสต์) |
| `dry-run` | ตรวจรอบเดียว **ไม่แตะ record/state** |
| `install` / `remove` | ติดตั้ง/ลบ Windows Service (admin) |
| `start` / `stop` / `restart` | ควบคุม service |
| `status` | สถานะ service + IP + tunnel |
| `webui` | เปิด Web UI (blocking) |
| `notify-test` | ส่งข้อความทดสอบ Telegram |
| `reset-password` | ตั้ง/ลบรหัสผ่านหน้าเว็บใหม่ (เขียน hash ตรง — ใช้ได้แม้ config ไม่ครบ) |
| (ไม่มี args) | เปิด Web UI + browser อัตโนมัติ |
| `run-service` | internal — SCM เรียก (ห้ามรันเองนอกจากเทสต์) |

## 4. Web UI endpoints (webui.py)

```
GET  /            หน้า HTML
GET  /status.json        สถานะ: records/records_time/history/record_errors/errors_active/telegram/tunnel(config_ok/config_errors/service/version/runtime/api_stats)
GET  /config.json        config เป็น JSON (ฟอร์มโหลด)
GET  /config-file        config.ini ดิบ (โหมดแก้ไฟล์)
GET  /setup-state        needs_setup (wizard หลัก auto-open)
GET  /ip-check           IP สด + NAT report
GET  /log                200 บรรทัดสุดท้าย
GET  /notify-queue       คิว Telegram
GET  /update-check       เช็คเวอร์ชันใหม่จาก GitHub Releases (cache 6 ชม.)
POST /login              cookie session (webui_password) — กันสุ่มรหัส: ผิด 5 ครั้งติด → ล็อก 5 นาที (429)
POST /save-config        บันทึกฟอร์ม (โครงสร้างเดียวกับ /config.json)
POST /save-file          บันทึกโหมดแก้ไฟล์ (validate ก่อนเขียน)
POST /verify-token       ตรวจ API token + list zones
POST /list-records       รายชื่อ record ของ zone (dropdown หลายที่)
POST /resolve-chat-id    หา chat id (getUpdates + ลบ webhook อัตโนมัติเมื่อ 409)
POST /notify-test / notify-test-raw
POST /port-scan          สแกนพอร์ต (จำกัดเฉพาะ host ใน config เท่านั้น!)
POST /notify-queue/flush|clear
POST /tunnel/test|start|stop|download|bind|hostnames|unbind|sync|zones
POST /tunnel/update-check  เช็ค cloudflared ล่าสุดจาก GitHub (cache 6 ชม.)
POST /service/install|start|stop|restart|uninstall   ควบคุม Windows Service (ต้อง admin; stop/install/uninstall ปฏิเสธเมื่อรันใน service เอง)
POST /ddns-run           รันรอบ DDNS ทันที (thread + กันซ้ำ busy)
POST /heartbeat-test     ทดสอบส่ง heartbeat ทันที (ไม่โดน rate limit รอบ)
POST /open-data-folder   เปิดโฟลเดอร์ข้อมูล (os.startfile)
```

**โครงสร้าง response:** `{"ok": true/false, "message": "ไทย", ...}` — error ใช้ HTTP 400/401/403/429

## 5. กับดักที่พบบ่อย (เจอจริงทุกข้อ — อ่านก่อนแก้!)

### Python ↔ JS ใน PAGE
- `PAGE` เป็น Python string — **ห้ามใช้ `\"` ใน JS string** (Python แปลงเป็น `"` → JS syntax error) → ใช้ **อัญประกาศไทย “ ”** หรือ `'`
- ตรวจ JS หลังแก้ทุกครั้ง: `python -c "จาก webui import PAGE; extract <script>..."` → `node --check` (ดูสคริปต์ตรวจด้านล่าง)
- **id ใน HTML ห้ามซ้ำ** (เคยเจอ: `twz-steps` ซ้ำกับ progress dots → ปุ่มกดแล้วไป toggle ผิด element)
- ใช้ `escapeHtml()` ทุกจุดที่แทรกค่าจาก server/API ลง innerHTML (wzMsg ครอบแล้ว)

### Encoding / .bat
- `.bat` ต้องเป็น **UTF-8 ไม่มี BOM + CRLF + `chcp 65001` บรรทัด 2** ไม่งั้นภาษาไทยเพี้ยน (cmd อ่านเป็น cp874)
- ESC byte ใน .bat: ฝัง `0x1B` ตัวเดียวที่ `set "ESC="` แล้วอ้าง `%ESC%[92m` — เขียนไฟล์ด้วย Python/PowerShell ไม่งั้น write tool เขียน LF

### พอร์ต 8123 / process
- service เปิด webui เองที่ 8123 — **เทสต์ webui ด้วย port อื่น** (เช่น `WebUI(config_path, port=8126)`) ไม่งั้น request ไปโดน service เก่า → 404 งง ๆ
- `ThreadingHTTPServer` มี `allow_reuse_address` → bind ซ้ำได้ → ระวัง service เก่าค้าง
- exe onefile มี 2 process (bootloader + child) — kill ต้อง `taskkill /IM cloudflare-ddns.exe /F` หรือผ่าน service

### state / queue (เขียนจากหลาย thread)
- `state.json`, `notify_queue.json` เขียนจาก ddns loop + webui พร้อมกัน → **เขียนแบบ atomic เสมอ** (temp + `os.replace`) — ห้ามเขียนตรง ๆ
- **ข้อมูล runtime อยู่ข้าง config.ini ที่ใช้จริง** (`state_path_for/queue_path_for/log_dir_for/data_dir_for`) — config วางข้าง exe → data ข้าง exe อัตโนมัติ — **ห้ามใช้ `DEFAULT_STATE_PATH`/`QUEUE_PATH` ฮาร์ดโค้ดในโค้ดใหม่** (เคยทำให้ state/queue แยกชุด root vs dist — รอบล่าสุดไม่ตรง/คิว Telegram ปน)
- **dry-run ต้องไม่เขียน state** (`_save_state` เช็ค `self.dry_run`; `_invalidate_zone` ก็เช็ค)

### ความปลอดภัย / สถิติ
- **login กันสุ่มรหัส**: ผิด 5 ครั้งติด → ล็อก 5 นาที (`_login_guard` ในหน่วยความจำ) — **เทสต์ login ระวัง!** กดผิด 5 ครั้งจะล็อกตัวเอง — ปลดได้โดย restart service หรือเซ็ต `_login_guard["locked_until"] = 0`
- **webui_password เก็บเป็น hash** (`config.password_hash()` = sha256 + salt จาก path config — 64 hex) — `_authed()`/`/login` รองรับทั้ง hash และ plaintext เก่า (ช่วง migrate) — `/login` ต้องยอมรับ hash ตรงด้วย (webui.js re-login ส่งค่าจากฟอร์มซึ่งอาจเป็น hash) — `_dict_to_ini` hash ค่าที่ไม่ใช่ hash เอง (ส่ง config_path ด้วย!)
- **กัน CSRF**: ทุก POST ยกเว้น `/login` ตรวจ Origin (`_origin_allowed()`) — ไม่มี Origin (CLI/curl) ผ่าน, Origin ไม่ตรงกับ Host → 403 — endpoint ใหม่ที่ต้อง login วางหลัง `if not self._authed()` เสมอ
- **เขียน config งานกู้คืน (reset-password / Telegram reset / migrate hash) ต้องใช้ `config_mod.atomic_write_text()`** — `save_text()` validate config เต็มจะบล็อก (ลืมรหัส + config ไม่ครบ = กู้ไม่ได้!) — อย่าลืม `cfg.reload()` หลังเขียน
- **`api_stats`** (จำนวนเรียก Cloudflare API / error / 429) นับในหน่วยความจำของ `cloudflare_api.py` — **เริ่มใหม่ทุกครั้งที่ service restart** (ไม่ใช่สะสมข้าม restart) — อย่าทำเป็น "ยอดรวมตลอดกาล"
- `record_errors` ใน state: จด error ล่าสุดต่อ record (key `fqdn|TYPE`) — ลบเมื่อสำเร็จ/ปิด family/ลบ record (cleanup ท้าย `run_once`) — dry-run ห้ามแตะ
- Telegram reset (`notifier.check_telegram_reset`): opt-in `telegram_allow_reset = false` — ฟังเฉพาะ `telegram_chat_id`, 2 ขั้น "reset password"→"yes" ภายใน 10 นาที, cooldown 600 วิ (`_last_reset_time`), offset กันรับซ้ำ (`_updates_offset`) — เรียกทุก loop ใน `run_forever` (ไม่ dry-run) — ฟิลด์ config ต้องเพิ่มใน `__init__`/`reload()`/**ทั้ง 2 จุด parse** + `_cfg_to_dict`/`_dict_to_ini` + `webui.html`/`webui.js` + `config.example.ini`
- `ip_consensus`: ต้อง ≥2 provider เห็น IP เดียวกัน (`get_public_ip(consensus=2)`) — ส่งต่อใน `_sync_family` — ปิด default
- state/queue `.bak`: `config_mod.rotate_backup(path, keep=3)` ก่อนเขียน **เฉพาะเนื้อหาเปลี่ยน** (เทียบข้อความเดิมก่อนเขียน)
- `/update-check` เรียก GitHub API — cache 6 ชม. (`_update_cache`) — อย่าเรียกถี่ (rate limit 60/ชม. ไม่มี token)

### Service
- `service.py` ใช้ `SvcDoRun` (ไม่ใช่ SvcRun) + pywin32 306 ใช้ `PrepareToHostSingle` (ไม่มี `PrepareServiceHost` แล้ว)
- **ห้ามบล็อก SvcDoRun นาน** (SCM timeout 30 วิ) — tunnel start ต้อง async thread (เคย crash 1053)
- `run_forever` ครอบ try/except ทั้ง loop — ห้ามปล่อย exception หลุด (service ตายเงียบ)
- หยุด service ไว: `stop_event.wait(min(interval, 5))`
- `install_service()` ตั้ง auto-restart ด้วย `_configure_failure_actions()` (`ChangeServiceConfig2(SERVICE_CONFIG_FAILURE_ACTIONS)`: restart 5/30 วิ, reset 86400) — ติดตั้งใหม่แล้วถอนได้เฉพาะตอน reinstall

### build / deploy
- **build.bat จะหยุด service → build → เริ่มใหม่เอง** (อย่า build ขณะ service รันด้วยมือ — exe ถูกล็อก PermissionError)
- หลังแก้โค้ด ต้อง: `python -m compileall -q cloudflare_ddns` → rebuild → reinstall service → เทสต์
- reinstall: `dist\cloudflare-ddns.exe remove/install/start` (admin) — หรือใช้ install.bat

## 6. งานแก้ไขโค้ด — ขั้นตอนมาตรฐาน

1. **อ่านก่อน**: ไฟล์ที่เกี่ยวข้อง + กับดักข้อ 5 + `field-journal`/git log ล่าสุด (ถ้ามี)
2. แก้โค้ด → `python -m compileall -q cloudflare_ddns`
3. ถ้าแตะ JS: สกัด `<script>` จาก PAGE → `node --check`
 4. เทสต์ logic ผ่าน `python` (ใช้ state/temp แยก อย่าแตะของจริง) — `dry-run` เสมอถ้าเป็น DDNS flow
 5. รัน unit tests: `python -m unittest discover -s tests -v` (tests/ — unittest stdlib ล้วน ไม่มี CI; ใช้ tempfile + unittest.mock เท่านั้น ห้ามพึ่งเน็ต)
 6. เทสต์ Web UI ผ่าน playwright (`ui-check.mjs`/`ui-verify.mjs` — ต้อง `npm i playwright` ในโฟลเดอร์ temp แยก เพราะไม่ควรมี node_modules ในโปรเจกต์) — เทสต์ทุกขนาดจอ 360-1920
 7. **rebuild + reinstall service** (svc-stop → PyInstaller → svc-reinstall) — ตรวจ `sc query CloudflareDDNS` = RUNNING + `curl http://127.0.0.1:8123/` = 200
 8. อัปเดต docs (README/CHANGELOG) ถ้าฟีเจอร์/behavior เปลี่ยน
 9. commit: `feat:` / `fix:` / `docs:` / `ui:` / `chore:` + คำอธิบายไทยสั้นกระชับ (ดู `git log --oneline`)

## 7. แนวทางโค้ด

- **ห้าม dependency ใหม่** — ใช้ urllib/socket/http.server/configparser เท่านั้น (+ pywin32 สำหรับ service)
- ข้อความไทยทั้งหมด: UI, log, error — `sys.stdout.reconfigure(encoding="utf-8")` ที่ entry (Windows console)
- Config ใหม่: เพิ่ม field ใน `config.py` **ทั้ง 3 จุด** (`__init__` ค่า default + `reload()` + `_load_from_parser()` อ่านจาก section) + `_cfg_to_dict`/`_dict_to_ini` ใน webui + `config.example.ini` + validate
- validate config ก่อนบันทึกเสมอ (`Config.validate()` → `save_text` ใช้ validate กันเขียนไฟล์เสีย)
- Cloudflare API: จับ `CloudflareRateLimit` (429) แยกจาก `CloudflareError` — rate limit → ข้ามรอบไม่ retry
- tunnel token = JWT: `_decode_tunnel_token()` แยก `a` (account) / `t` (tunnel) จาก payload
- ข้อมูล runtime ทั้งหมดอยู่ข้าง exe (`config_mod.DEFAULT_DATA_DIR`) — `migrate_legacy_data()` ย้ายจาก ProgramData ให้ครั้งเดียว

## 8. สคริปต์ตรวจที่ควรมี

```powershell
# 1. syntax
python -m compileall -q cloudflare_ddns

# 2. JS syntax (หลังแก้ webui.py)
python -c "import sys; from cloudflare_ddns.webui import PAGE; s=PAGE.index('<script>')+8; e=PAGE.index('</script>',s); open(r'$env:TEMP\page.js','w',encoding='utf-8').write(PAGE[s:e])"
node --check "$env:TEMP\page.js"

# 3. service สถานะ + webui
sc query CloudflareDDNS
curl.exe -s -o NUL -w "%{http_code}" http://127.0.0.1:8123/

# 4. responsive (ui-verify.mjs) — ติดตั้ง playwright ในโฟลเดอร์ temp
cd $env:TEMP\pw && npm i playwright && node D:\MyCode\Cloudflare\ui-verify.mjs

# 5. rebuild + reinstall (admin UAC popup)
powershell -File <temp>\svc-stop.cmd    # stop + taskkill
python -m PyInstaller --noconfirm --clean --onefile --console --name cloudflare-ddns --icon assets\icon.ico --hidden-import servicemanager --hidden-import win32serviceutil --hidden-import win32service run.py
powershell -File <temp>\svc-reinstall.cmd # remove+install+start
```

> สคริปต์ build ทั้งคู่มี admin auto + UTF-8 ไม่มี BOM + CRLF — uild.bat เหมาะกับเครื่อง dev (ไม่ต้อง admin ถ้าไม่มี service) · uild-install.bat ใช้กับเครื่องปลายทางที่ต้องการ service

## 9. อย่าลืม

- อย่า commit: `config.ini`, `state.json`, `notify_queue.json`, `logs/`, `cloudflared.exe`, `tunnel.pid`, `*.png` (gitignore มีแล้ว)
- ไม่ push โดยไม่ได้รับคำสั่ง
- **ห้ามสร้าง GitHub release จนกว่าผู้ใช้จะสั่งโดยตรง** (เคยสั่งลบ release ไปแล้ว — อยากปล่อยเมื่อไหร่ต้องถามก่อน)
- ถ้าผู้ใช้ติดตั้ง service อยู่: หลัง rebuild **ต้อง reinstall/restart** ไม่งั้นผู้ใช้ยังใช้ exe เก่า (เว็บจะไม่เห็นฟีเจอร์ใหม่)
- อัปเดต `CHANGELOG.md` เมื่อ feature/fix สำคัญ
- **เครื่อง dev (เครื่องนี้): ห้ามติดตั้ง service** — ใช้ `build.bat` (build อย่างเดียว ไม่ต้อง admin ถ้าไม่มี service) · webui ทดสอบรันด้วย `python -m cloudflare_ddns.main webui` (ปิดด้วย Ctrl+C) — ถ้า build เจอ `PermissionError` (exe ล็อก) = มี webui/python ค้าง ต้องปิดก่อน · release แนบ exe ที่ build จากเครื่อง dev นี้ (ใช้ `build-install.bat` เฉพาะเครื่องปลายทางที่ต้องการ service)

## 10. รูปแบบข้อความ release (บังคับทุกครั้ง)

ข้อความ release (GitHub Release Notes) ต้องใช้รูปแบบด้านล่าง — เขียนเป็นไฟล์ .md ชั่วคราวแล้วใช้ `gh release create <tag> --notes-file`:

```markdown
## 🚀 v<เวอร์ชัน> — Cloudflare DDNS Updater

**วันที่:** <dd/มม/ปปปป> · **ขนาดไฟล์:** <X.X> MB

### ✨ ฟีเจอร์ใหม่
- <สั้น 1 บรรทัด เริ่มด้วยคำสำคัญ>

### 🔧 แก้บั๊ก
- <สั้น 1 บรรทัด>

### 📥 วิธีอัปเดต
**โหมดกด exe (ใช้งานตรง):**
```
1. หยุดโปรแกรม (Ctrl+C) / ปิดหน้าต่าง
2. ดาวน์โหลด cloudflare-ddns.exe ใหม่
3. วางทับไฟล์เดิม (config/state/log อยู่ข้าง exe — ไม่หาย)
4. เปิด exe ตามปกติ
```

**โหมด Windows Service (admin):**
```
cloudflare-ddns.exe stop
cloudflare-ddns.exe remove
(วาง exe ใหม่ทับ)
cloudflare-ddns.exe install
cloudflare-ddns.exe start
```
> หรือใช้ `build-install.bat` ครอบจบในตัวเดียว

### ✅ ตรวจสอบไฟล์
- SHA256: `<จาก gh release view ... --json assets --jq .assets[0].digest>`
- ดูวิธีทดสอบ exe ก่อนใช้งาน: `docs/RELEASE-TEST.md`
```

**กฎ:**
- หัวข้อสั้น เริ่มด้วย emoji (✨ ใหม่ / 🔧 แก้ / ⚠️ หมายเหตุ / 📥 วิธี / ✅ ตรวจสอบ)
- bullet สั้น 1 บรรทัด ไม่ยัดทุกอย่าง — รายละเอียดอยู่ใน CHANGELOG.md
- **"วิธีอัปเดต" ห้ามลืม** (ส่วนที่ผู้ใช้โหลดแล้วต้องทำต่อ) — ครอบทั้งโหมด exe และ service
- SHA256 ดึงจาก `gh release view <tag> --json assets --jq '.assets[0].digest'`
- exe ที่แนบ = build จาก `build.bat` (8.0 MB) — ตรวจเทสต์ release (`docs/RELEASE-TEST.md`) ผ่าน 15/15 ก่อนปล่อยทุกครั้ง

### ขั้นตอนสร้าง release (เจอจริง v1.8.0)

```text
1. bump: __version__ ใน cloudflare_ddns/__init__.py + CHANGELOG.md [x.y.z] + วันที่
2. rebuild exe (build.bat — exe ต้องมีเวอร์ชันใหม่) + ตรวจ webui เสิร์ฟ v1.8.0 จริง
3. commit bump + push
4. เขียนไฟล์ notes ด้วย write tool (UTF-8 ไม่มี BOM) — วาง <SHA256> ปลอมไว้ก่อน
5. gh release create v<tag> dist\cloudflare-ddns.exe --title "..." --notes-file <ไฟล์>
6. ดึง digest: gh release view <tag> --json assets --jq '.assets[0].digest'
7. อัปเดต SHA ใน notes แล้ว PATCH ผ่าน Python/urllib ตรง (ดูกับดักด้านล่าง)
8. ตรวจ body กลับมาไทยปกติ (หลีกเลี่ยง PowerShell pipeline — ดูกับดัก)
```

**กับดัก encoding (เจอจริง v1.8.0 — ไทยเพี้ยนทั้ง release!):**
- **ห้าม** `Set-Content -Encoding UTF8` (PS 5.1) แก้ไฟล์ notes ที่มีไทย — อ่าน UTF-8 ไม่มี BOM เป็น cp874 → mojibake
- **ห้าม** `gh release edit --notes-file` กับไฟล์ไทยบนเครื่องนี้ — gh อ่านไฟล์ด้วย cp874 → ส่ง mojibake ขึ้น GitHub
- ตรวจผล **ห้าม**ผ่าน PowerShell pipeline (`gh view | Out-File`) — PS รับ stdout ของ gh เป็น cp874 → เห็น `?`/เพี้ยนแม้ GitHub เก็บถูก
- วิธีที่ปลอดภัย: เขียนไฟล์ด้วย write tool / Python · อัปเดต SHA ด้วย **Python + urllib PATCH** (json utf-8) · ตรวจด้วย `gh api ... --jq .body | python -c "import sys; open('<path>','wb').write(sys.stdin.buffer.read())"` แล้วอ่านไฟล์
