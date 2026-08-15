"""Web UI: ดูสถานะ + ตั้งค่าผ่านเบราว์เซอร์ (stdlib ล้วน, one-page).

- เปิดเฉพาะ 127.0.0.1
- ถ้าตั้ง webui_password ไว้ต้องใส่รหัสก่อน (cookie แบบง่าย)
- ฟอร์มตั้งค่าสร้าง/ตรวจ config.ini ให้อัตโนมัติ (ไม่มี textarea ให้มั่ว)
"""

import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import __version__
from . import config as config_mod
from . import ddns
from . import notifier

log = logging.getLogger("cloudflare-ddns")

_tunnel_mgr = None


def _get_tunnel_mgr():
    global _tunnel_mgr
    if _tunnel_mgr is None:
        from . import tunnel as tunnel_mod

        _tunnel_mgr = tunnel_mod.TunnelManager()
    return _tunnel_mgr

# ชื่อบริการสำหรับพอร์ตที่พบบ่อย
PORT_SERVICES = {
    20: "ftp-data", 21: "ftp", 22: "ssh", 23: "telnet", 25: "smtp", 53: "dns",
    80: "http", 110: "pop3", 143: "imap", 443: "https", 445: "smb", 465: "smtps",
    587: "smtp-sub", 993: "imaps", 995: "pop3s", 1433: "mssql", 1883: "mqtt",
    3306: "mysql", 3389: "rdp", 5432: "postgres", 5900: "vnc", 6379: "redis",
    8080: "http-alt", 8443: "https-alt", 9000: "php-fpm", 27017: "mongodb",
}
DEFAULT_SCAN_PORTS = [21, 22, 23, 25, 53, 80, 110, 143, 443, 445, 993, 995, 1433, 3306, 3389, 5900, 6379, 8080, 8443, 27017]

PAGE = """<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cloudflare DDNS</title>
<style>
:root {
  --bg: oklch(1 0 0);
  --surface: oklch(0.972 0.006 50);
  --surface-2: oklch(0.945 0.010 50);
  --border: oklch(0.90 0.012 50);
  --ink: oklch(0.24 0.03 250);
  --ink-2: oklch(0.45 0.035 250);
  --muted: oklch(0.56 0.03 250);
  --accent: oklch(0.62 0.17 45);
  --accent-ink: oklch(1 0 0);
  --accent-soft: oklch(0.945 0.05 50);
  --ok: oklch(0.5 0.11 155);
  --ok-soft: oklch(0.955 0.04 155);
  --warn: oklch(0.55 0.13 65);
  --warn-soft: oklch(0.96 0.05 70);
  --danger: oklch(0.5 0.19 28);
  --danger-soft: oklch(0.955 0.05 28);
  --z-sticky: 10;
  --z-toast: 40;
}
* { box-sizing: border-box; }
html { font-size: clamp(14px, 0.75rem + 0.55vw, 17px); }
body {
  margin: 0; background: var(--bg); color: var(--ink);
  font-family: "Segoe UI", system-ui, sans-serif; font-size: 1rem; line-height: 1.5;
}
.mono { font-family: "Cascadia Code", Consolas, monospace; }
h1 { font-size: 1.4rem; margin: 0; letter-spacing: -0.02em; }
h2 { font-size: 1.05rem; margin: 0; }
h3 { font-size: 0.9rem; margin: 26px 0 10px; color: var(--ink-2); font-weight: 600; }
p { margin: 0; }

/* header */
.topbar {
  position: sticky; top: 0; z-index: var(--z-sticky);
  display: flex; align-items: center; justify-content: space-between; gap: 16px;
  flex-wrap: wrap;
  background: color-mix(in oklch, var(--bg) 85%, transparent);
  backdrop-filter: blur(8px);
  padding: 14px 28px; border-bottom: 1px solid var(--border);
}
.brand { display: flex; align-items: center; gap: 12px; min-width: 0; }
.brand-dot {
  width: 34px; height: 34px; border-radius: 9px; flex: none;
  background: radial-gradient(circle at 35% 30%, oklch(0.74 0.15 55), oklch(0.62 0.17 45));
  box-shadow: 0 1px 3px oklch(0.62 0.17 45 / 0.35);
}
.brand .sub { font-size: 0.85rem; color: var(--muted); margin-top: 2px; }
.top-right { display: flex; align-items: center; gap: 10px; }
.pill {
  font-size: 0.85rem; font-weight: 600; padding: 5px 12px; border-radius: 999px;
  border: 1px solid var(--border); background: var(--surface); color: var(--ink-2);
  white-space: nowrap;
}
.pill.ok { color: var(--ok); background: var(--ok-soft); border-color: color-mix(in oklch, var(--ok) 30%, transparent); }
.pill.warn { color: var(--warn); background: var(--warn-soft); border-color: color-mix(in oklch, var(--warn) 30%, transparent); }
.pill.err { color: var(--danger); background: var(--danger-soft); border-color: color-mix(in oklch, var(--danger) 30%, transparent); }

main { max-width: 860px; margin: 0 auto; padding: 24px 28px 80px; }

/* panels */
.panel {
  background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
  padding: 18px 20px; margin-bottom: 16px;
}
.panel-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
.panel-head p { font-size: 0.85rem; color: var(--muted); }

/* records list */
.record-row {
  display: flex; align-items: center; gap: 14px; flex-wrap: wrap;
  padding: 10px 12px; border-radius: 8px;
}
.record-row + .record-row { margin-top: 6px; }
.record-row.ok { background: var(--ok-soft); }
.record-row.err { background: var(--danger-soft); }
.record-row.idle { background: var(--surface-2); }
.rec-dot { width: 9px; height: 9px; border-radius: 50%; flex: none; }
.ok .rec-dot { background: var(--ok); }
.err .rec-dot { background: var(--danger); }
.idle .rec-dot { background: var(--muted); }
.rec-name { font-weight: 600; min-width: 200px; }
.rec-ip { color: var(--ink-2); font-size: 0.9rem; flex: 1; min-width: 150px; word-break: break-all; }
.rec-meta { font-size: 0.85rem; color: var(--muted); text-align: right; }
.rec-ip.clickable { cursor: pointer; }
.rec-ip.clickable:hover { color: var(--accent); }

/* telegram row */
.tg-row { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
.tg-status { font-size: 0.9rem; color: var(--ink-2); flex: 1; min-width: 200px; }
.tg-status .ok { color: var(--ok); }
.tg-status .err { color: var(--danger); }

/* forms */
.grid2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 14px; }
label.field { display: block; font-size: 0.85rem; color: var(--muted); margin-bottom: 12px; }
label.field input, label.field select {
  display: block; width: 100%; margin-top: 4px;
  font-size: 0.9rem; color: var(--ink); font-family: inherit;
  padding: 8px 10px; border: 1px solid var(--border); border-radius: 8px;
  background: var(--bg);
}
label.field input:focus, label.field select:focus {
  outline: 2px solid color-mix(in oklch, var(--accent) 40%, transparent); border-color: var(--accent);
}
.toggles { display: flex; flex-wrap: wrap; gap: 8px 18px; margin: 4px 0 6px; }
.toggles label { display: inline-flex; align-items: center; gap: 7px; font-size: 0.9rem; color: var(--ink-2); cursor: pointer; }
.toggles input { accent-color: var(--accent); width: 15px; height: 15px; }
#daily_report_time {
  width: 96px; height: auto; box-sizing: border-box; margin-left: 6px;
  padding: 7px 10px; font-family: "Cascadia Code", Consolas, monospace;
  font-size: 0.9rem; border: 1px solid var(--border); border-radius: 8px;
  background: var(--bg); color: var(--ink);
}
#daily_report_time:focus { outline: 2px solid color-mix(in oklch, var(--accent) 40%, transparent); border-color: var(--accent); }

/* records editor */
.rec-edit {
  display: grid; grid-template-columns: minmax(160px, 1.4fr) minmax(130px, 1fr) 120px 100px 122px auto;
  gap: 8px; align-items: center; margin-bottom: 8px;
}
.rec-edit input[type="text"], .rec-edit input[type="number"] {
  width: 100%; font-size: 0.9rem; padding: 7px 9px;
  border: 1px solid var(--border); border-radius: 8px; background: var(--bg); color: var(--ink);
}
.rec-edit .mini {
  display: flex; gap: 8px; justify-content: flex-start; align-items: center;
  font-size: 0.85rem; color: var(--muted); white-space: nowrap;
}
.rec-edit .mini label {
  display: inline-flex; align-items: center; gap: 5px; cursor: pointer;
  padding: 5px 9px; border: 1px solid var(--border); border-radius: 7px; background: var(--bg);
}
.rec-edit .mini label:hover { border-color: var(--accent); }
.rec-edit .mini input { accent-color: var(--accent); margin: 0; }
.btn-del {
  background: transparent; border: 1px solid transparent; color: var(--danger);
  font-size: 16px; cursor: pointer; padding: 4px 6px; border-radius: 6px;
}
.btn-del:hover { background: var(--danger-soft); }

/* buttons */
.btn-primary, .btn-secondary {
  font-size: 0.9rem; font-weight: 600; padding: 8px 16px; border-radius: 8px; cursor: pointer;
  transition: filter 120ms ease-out, transform 120ms ease-out;
}
.btn-primary { background: var(--accent); color: var(--accent-ink); border: 0; }
.btn-secondary { background: var(--surface); color: var(--ink-2); border: 1px solid var(--border); }
.btn-primary:hover, .btn-secondary:hover { filter: brightness(0.96); }
.btn-primary:active, .btn-secondary:active { transform: translateY(1px); }
.btn-primary:disabled, .btn-secondary:disabled { opacity: 0.55; cursor: wait; }

/* toast */
#toast {
  position: fixed; right: 20px; bottom: 20px; z-index: var(--z-toast);
  max-width: 380px; padding: 11px 16px; border-radius: 10px; font-size: 0.9rem;
  background: var(--ink); color: oklch(0.95 0 0);
  opacity: 0; pointer-events: none;
  transform: translateY(8px);
  transition: opacity 180ms ease-out, transform 180ms ease-out;
}
#toast.show { opacity: 1; transform: translateY(0); }
#toast.ok { background: var(--ok); }
#toast.err { background: var(--danger); }

@media (max-width: 640px) {
  .topbar { padding: 12px 16px; flex-direction: column; align-items: stretch; gap: 10px; }
  .top-right { width: 100%; justify-content: space-between; }
  .brand .sub { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 62vw; }
  .brand-dot { width: 30px; height: 30px; border-radius: 8px; }
  main { padding: 16px 16px 80px; }
  .panel { padding: 14px; }
  .record-row { gap: 10px; }
  .rec-meta { width: 100%; text-align: left; }
}
/* แท็บเล็ต/จอเล็ก: record editor เปลี่ยนเป็น 2 คอลัมน์ (ชื่อ+zone / proxy+ttl / 4-6+ลบ) */
@media (max-width: 860px) {
  .rec-edit { grid-template-columns: 1fr 1fr; }
  .rec-edit .mini label { padding: 4px 6px; }
  .rec-edit .btn-del { justify-self: end; }
}
@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; animation: none !important; }
}

/* ---------- mode switch (ฟอร์ม / ไฟล์) ---------- */
.mode-switch { display: inline-flex; border: 1px solid var(--border); border-radius: 10px; padding: 3px; background: var(--surface-2); gap: 3px; }
.mode-switch button {
  border: 0; background: transparent; color: var(--ink-2); font-size: 0.85rem; font-weight: 600;
  padding: 6px 14px; border-radius: 7px; cursor: pointer;
}
.mode-switch button.active { background: var(--bg); color: var(--ink); box-shadow: 0 1px 2px oklch(0 0 0 / 0.08); }
#file-view textarea {
  width: 100%; min-height: 360px; box-sizing: border-box;
  font-family: "Cascadia Code", Consolas, monospace; font-size: 0.82rem; line-height: 1.5;
  padding: 12px; border: 1px solid var(--border); border-radius: 8px;
  background: var(--bg); color: var(--ink); resize: vertical;
}
.file-note { font-size: 0.85rem; color: var(--muted); margin: 0 0 10px; }

/* ---------- wizard ครั้งแรก ---------- */
#wizard {
  position: fixed; inset: 0; z-index: 60; overflow-y: auto;
  background: oklch(0.24 0.03 250 / 0.45); backdrop-filter: blur(3px);
  display: flex; align-items: flex-start; justify-content: center; padding: 5vh 16px 40px;
}
#wizard[hidden] { display: none; }
.wz-card {
  width: 100%; max-width: 560px; background: var(--bg);
  border: 1px solid var(--border); border-radius: 16px;
  padding: 26px 28px; box-shadow: 0 18px 50px oklch(0 0 0 / 0.18);
}
.wz-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 6px; }
.wz-head p { font-size: 0.85rem; color: var(--muted); margin-top: 4px; }
.wz-skip { border: 0; background: transparent; color: var(--muted); font-size: 0.85rem; cursor: pointer; padding: 6px; border-radius: 6px; }
.wz-skip:hover { color: var(--ink-2); }
.wz-steps { display: flex; gap: 6px; margin: 16px 0 20px; }
.wz-steps .dot { flex: 1; height: 5px; border-radius: 3px; background: var(--surface-2); }
.wz-steps .dot.on { background: var(--accent); }
.wz-step-title { font-size: 1.1rem; font-weight: 700; margin: 0 0 6px; }
.wz-step-sub { font-size: 0.9rem; color: var(--ink-2); margin: 0 0 18px; }
.wz-actions { display: flex; justify-content: space-between; gap: 10px; margin-top: 22px; }
.wz-help {
  margin-top: 12px; border: 1px solid var(--border); border-radius: 10px;
  background: var(--surface); padding: 12px 14px; font-size: 0.85rem; color: var(--ink-2);
}
.wz-help ol { margin: 8px 0 0; padding-left: 20px; }
.wz-help li { margin-bottom: 4px; }
.wz-ok-box {
  border: 1px solid color-mix(in oklch, var(--ok) 35%, transparent);
  background: var(--ok-soft); color: var(--ok); border-radius: 8px;
  padding: 8px 12px; font-size: 0.85rem; margin-top: 10px;
}
.wz-err-box {
  border: 1px solid color-mix(in oklch, var(--danger) 35%, transparent);
  background: var(--danger-soft); color: var(--danger); border-radius: 8px;
  padding: 8px 12px; font-size: 0.85rem; margin-top: 10px;
}
.wz-zone-select { width: 100%; padding: 9px 10px; font-size: 0.9rem; border: 1px solid var(--border); border-radius: 8px; background: var(--bg); color: var(--ink); }
</style>
</head>
<body>
__LOGIN__
<header class="topbar">
  <div class="brand">
    <div class="brand-dot" aria-hidden="true"></div>
    <div>
      <h1>Cloudflare DDNS</h1>
      <p class="sub">อัปเดต IP อัตโนมัติ · รอบล่าสุด <span id="lastrun" class="mono">-</span></p>
    </div>
  </div>
  <div class="top-right">
    <span id="pill" class="pill">กำลังโหลด…</span>
    <button id="refresh" class="btn-secondary">รีเฟรช</button>
  </div>
</header>

<main>
  <section class="panel">
    <div class="panel-head">
      <h2>สถานะ IP</h2>
      <p>กดที่ชื่อหรือ IP เพื่อคัดลอก</p>
    </div>
    <div id="public-ip" class="tg-row" style="margin-bottom:12px;padding:10px 12px;background:var(--surface-2);border-radius:8px">
      <span class="tg-status"><b>IP สาธารณะปัจจุบัน</b> <span class="mono" id="pub-ipv4" style="color:var(--ink-2)">ตรวจ…</span><span class="muted" style="color:var(--muted)"> · IPv6: </span><span class="mono" id="pub-ipv6" style="color:var(--muted)">ตรวจ…</span><br><span id="nat-status" style="font-size:0.85rem;color:var(--muted)"></span></span>
      <button id="recheckIp" class="btn-secondary">ตรวจใหม่</button>
    </div>
    <div id="records" class="records"><p style="color:var(--muted)">กำลังโหลด…</p></div>
  </section>

  <section class="panel">
    <div class="panel-head"><h2>แจ้งเตือน Telegram</h2></div>
    <div class="tg-row">
      <span id="tgstatus" class="tg-status">กำลังโหลด…</span>
      <button id="tgTest" class="btn-secondary">ส่งข้อความทดสอบ</button>
      <button id="tgQueueBtn" class="btn-secondary">ดูคิว</button>
      <button id="tgFlushBtn" class="btn-secondary">ลองส่งใหม่</button>
      <button id="tgClearBtn" class="btn-secondary">ล้างคิว</button>
    </div>
    <div id="tg-queue" hidden style="margin-top:10px"></div>
  </section>

  <section class="panel">
    <div class="panel-head"><h2>Cloudflare Tunnel</h2><p>ให้บริการผ่าน Tunnel แทนการเปิดพอร์ต (เหมาะกับ CGNAT / ไม่เปิดพอร์ต)</p></div>
    <div class="tg-row">
      <span id="tunnel-status" class="tg-status">กำลังโหลด…</span>
      <button id="tunnelWizard" class="btn-primary">ตั้งค่า Tunnel (wizard)</button>
      <button id="tunnelStart" class="btn-secondary">เริ่ม tunnel</button>
      <button id="tunnelStop" class="btn-secondary">หยุด tunnel</button>
      <button id="tunnelDownload" class="btn-secondary">ดาวน์โหลด cloudflared</button>
    </div>
  </section>

  <section class="panel">
    <div class="panel-head">
      <h2>สแกนพอร์ต</h2>
      <p>ตรวจบริการที่เปิดอยู่บน host ที่ตั้งไว้ (resolve IP ปัจจุบันให้อัตโนมัติ)</p>
    </div>
    <div class="tg-row">
      <select id="scan-host" class="wz-zone-select" style="max-width:280px"></select>
      <input id="scan-ports" class="mono" style="flex:1;min-width:200px;padding:8px 10px;border:1px solid var(--border);border-radius:8px;background:var(--bg);color:var(--ink);font-size:0.9rem" value="21,22,23,25,53,80,110,143,443,445,993,995,1433,3306,3389,5900,6379,8080,8443,27017">
      <button id="scanBtn" class="btn-primary">สแกน</button>
    </div>
    <div id="scan-result" style="margin-top:12px"></div>
  </section>

  <section class="panel">
    <div class="panel-head">
      <h2>ประวัติการอัปเดต</h2>
      <p>50 รายการล่าสุด</p>
    </div>
    <div id="history"><p style="color:var(--muted)">กำลังโหลด…</p></div>
  </section>

  <section class="panel">
    <div class="panel-head">
      <h2>Log ล่าสุด</h2>
      <button id="logReload" class="btn-secondary">โหลดใหม่</button>
    </div>
    <pre id="logview" style="margin:0;padding:10px 12px;background:var(--surface-2);border-radius:8px;font-family:'Cascadia Code',Consolas,monospace;font-size:0.8rem;color:var(--ink-2);max-height:280px;overflow:auto;white-space:pre-wrap;word-break:break-all">กำลังโหลด…</pre>
  </section>

  <section class="panel" id="settings-panel">
    <div class="panel-head">
      <h2>ตั้งค่า</h2>
      <div style="display:flex;gap:10px;align-items:center">
        <div class="mode-switch" role="tablist">
          <button id="mode-form" type="button" class="active" role="tab">แบบฟอร์ม</button>
          <button id="mode-file" type="button" role="tab">แก้ไขไฟล์โดยตรง</button>
        </div>
        <button id="saveBtn" class="btn-primary">บันทึกการตั้งค่า</button>
      </div>
    </div>

    <div id="form-view">
      <h3>Cloudflare</h3>
    <div class="grid2">
      <label class="field">API Token
        <input id="api_token" type="password" autocomplete="off" placeholder="cfut_... หรือ token รูปแบบอื่น">
      </label>
      <label class="field">ตรวจ IP ทุก (วินาที, ขั้นต่ำ 15)
        <input id="interval" type="number" min="15" step="5">
      </label>
    </div>
    <div class="grid2">
      <label class="field">รหัสผ่านหน้าเว็บ (เว้นว่าง = ไม่ต้องใช้)
        <input id="webui_password" type="password" autocomplete="off" placeholder="ตั้งไว้ถ้าไม่อยากให้ใครเปิดหน้าได้">
      </label>
      <label class="field">พอร์ตหน้าเว็บ
        <input id="webui_port" type="number" min="1" max="65535" placeholder="8123">
      </label>
    </div>
    <div class="grid2">
      <label class="field">ที่เก็บ log (เว้นว่าง = โฟลเดอร์เดียวกับ exe)
        <input id="log_dir" type="text" class="mono" autocomplete="off" placeholder="เช่น D:\CloudflareDDNS\logs">
      </label>
      <label class="field">ที่เก็บข้อมูล (state, คิว) — เว้นว่าง = โฟลเดอร์เดียวกับ exe
        <input id="data_dir" type="text" class="mono" autocomplete="off" placeholder="(คงที่: โฟลเดอร์เดียวกับ exe)" disabled>
      </label>
    </div>
    <div class="toggles">
      <label><input id="use_ipv4" type="checkbox"> อัปเดต IPv4 (A record)</label>
      <label><input id="use_ipv6" type="checkbox"> อัปเดต IPv6 (AAAA record)</label>
    </div>

    <h3>แจ้งเตือน Telegram</h3>
    <div class="grid2">
      <label class="field">Bot token (จาก @BotFather)
        <input id="tg_token" type="password" autocomplete="off" placeholder="123456789:AAHxxx...">
      </label>
      <label class="field">Chat ID (เว้น = wizard/notify-test หาให้)
        <input id="tg_chat" type="text" class="mono" autocomplete="off" placeholder="123456789">
      </label>
    </div>
    <div class="toggles">
      <label><input id="notify_start" type="checkbox"> เริ่มทำงาน</label>
      <label><input id="notify_stop" type="checkbox"> หยุดทำงาน</label>
      <label><input id="notify_ip_change" type="checkbox"> IP เปลี่ยน</label>
      <label><input id="notify_error" type="checkbox"> Error</label>
      <label><input id="notify_created" type="checkbox"> สร้าง record ใหม่</label>
    </div>
    <div class="toggles">
      <label><input id="daily_report" type="checkbox"> สรุปรายวันทาง Telegram</label>
      <label>เวลา (HH:MM)<input id="daily_report_time" type="text" placeholder="08:00"></label>
    </div>

    <h3>Cloudflare Tunnel (ไม่บังคับ)</h3>
    <div class="toggles">
      <label><input id="tunnel_enabled" type="checkbox"> เปิด tunnel อัตโนมัติตอน service เริ่ม</label>
    </div>
    <div class="grid2">
      <label class="field">Tunnel Token (จาก Zero Trust → Networks → Tunnels)
        <input id="tunnel_token" type="password" autocomplete="off" placeholder="eyJhIjoi...">
      </label>
      <label class="field">ที่อยู่ cloudflared.exe (เว้นว่าง = ดาวน์โหลดข้าง exe อัตโนมัติ)
        <input id="cloudflared_path" type="text" class="mono" autocomplete="off" placeholder="(อัตโนมัติ)">
      </label>
    </div>

    <h3>DNS records</h3>
    <div id="records-editor"></div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:10px">
      <button id="addRecord" class="btn-secondary" type="button">+ เพิ่ม record</button>
      <button id="loadRecords" class="btn-secondary" type="button">โหลดชื่อ record จาก Cloudflare</button>
      <select id="rec-pick" class="wz-zone-select" hidden style="max-width:280px"></select>
    </div>
    </div>

    <div id="file-view" hidden>
      <p class="file-note">แก้ไขไฟล์ config.ini ตรง ๆ ระวังรูปแบบให้ถูกต้อง (ระบบตรวจ syntax และค่าพื้นฐานก่อนบันทึก) — ตัวอย่างดูได้จาก config.example.ini</p>
      <textarea id="file-editor" spellcheck="false" aria-label="config.ini"></textarea>
      <p style="margin-top:10px"><button id="saveFileBtn" class="btn-primary" type="button">บันทึกไฟล์</button></p>
    </div>
  </section>
</main>

<footer style="text-align:center;padding:8px 16px 40px;color:var(--muted);font-size:0.8rem">
  Cloudflare DDNS Updater v__VERSION__ · MIT License ·
  <a href="https://github.com/Witawat/Cloudflare-ddns" target="_blank" rel="noopener" style="color:var(--accent)">github.com/Witawat/Cloudflare-ddns</a>
</footer>

<div id="toast" role="status"></div>

<div id="wizard" hidden>
  <div class="wz-card" role="dialog" aria-modal="true" aria-labelledby="wz-title">
    <div class="wz-head">
      <div>
        <h1 id="wz-title">ตั้งค่า Cloudflare DDNS ครั้งแรก</h1>
        <p>ทำตามทีละขั้นตอน ประมาณ 2 นาที — ตอนไหนติด กด "ดูวิธีทำ" ได้ทุกขั้น</p>
      </div>
      <button id="wz-skip" class="wz-skip" type="button">ข้ามชั่วคราว</button>
    </div>
    <div class="wz-steps" id="wz-steps">
      <span class="dot"></span><span class="dot"></span><span class="dot"></span><span class="dot"></span><span class="dot"></span>
    </div>
    <div id="wz-body"></div>
  </div>
</div>

<div id="tunnel-wizard" hidden>
  <div class="wz-card" role="dialog" aria-modal="true" aria-labelledby="twz-title">
    <div class="wz-head">
      <div>
        <h1 id="twz-title">ตั้งค่า Cloudflare Tunnel</h1>
        <p>ให้บริการเว็บผ่าน Tunnel โดยไม่ต้องเปิดพอร์ต — 4 ขั้นตอน</p>
      </div>
      <button id="twz-close" class="wz-skip" type="button">ปิด</button>
    </div>
    <div class="wz-steps" id="twz-steps">
      <span class="dot"></span><span class="dot"></span><span class="dot"></span><span class="dot"></span>
    </div>
    <div id="twz-body"></div>
  </div>
</div>

<script>
const $ = (id) => document.getElementById(id);

function toast(text, kind) {
  const t = $("toast");
  t.textContent = text;
  t.className = "show " + (kind || "");
  clearTimeout(t._timer);
  t._timer = setTimeout(() => { t.className = ""; }, 3200);
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

/* ---------- สถานะ ---------- */

async function loadStatus() {
  try {
    const r = await fetch("/status.json");
    const s = await r.json();
    const pill = $("pill");
    if (!s.config_ok) {
      pill.textContent = "ตั้งค่าไม่ครบ";
      pill.className = "pill warn";
    } else if (s.errors_active) {
      pill.textContent = "มีปัญหา";
      pill.className = "pill err";
    } else {
      pill.textContent = "พร้อมใช้งาน";
      pill.className = "pill ok";
    }
    const last = s.last_run ? new Date(s.last_run).toLocaleString("th-TH") : "ยังไม่เคยรัน";
    $("lastrun").textContent = last;

    const box = $("records");
    const entries = Object.entries(s.records || {});
    if (!entries.length) {
      const msg = s.config_ok
        ? 'ยังไม่มีข้อมูล IP (รอรอบแรกของ service)'
        : 'ยังไม่ได้ตั้งค่า config — ทำตาม wizard หรือส่วน "ตั้งค่า" ให้ครบก่อน (IP จะถูกอัปเดตให้อัตโนมัติ)';
      box.innerHTML = '<p style="color:var(--muted)">' + msg + "</p>";
    } else {
      box.innerHTML = entries.map(([key, ip]) => {
        const err = s.record_errors && s.record_errors[key];
        const kind = err ? "err" : (ip ? "ok" : "idle");
        const t = (s.records_time || {})[key];
        const timeText = t ? new Date(t).toLocaleString("th-TH") : "—";
        return '<div class="record-row ' + kind + '">' +
          '<span class="rec-dot"></span>' +
          '<span class="rec-name mono clickable" title="กดเพื่อคัดลอกชื่อ" onclick="copyIp(this)">' + escapeHtml(key) + "</span>" +
          '<span class="rec-ip mono clickable" title="กดเพื่อคัดลอก IP" onclick="copyIp(this)">' + (ip || "ยังไม่ตั้งค่า") + "</span>" +
          '<span class="rec-meta">' + (err ? escapeHtml(err) : "อัปเดตล่าสุด " + timeText) + "</span></div>";
      }).join("");
    }

    const tg = s.telegram || {};
    const tgBox = $("tgstatus");
    if (tg.enabled) {
      let html = '<span class="ok">พร้อมใช้งาน</span> (chat ' + escapeHtml(tg.chat_id) + ")";
      if (tg.queue) html += ' · <span class="err">คิวรอส่ง ' + tg.queue + " ข้อความ</span>";
      tgBox.innerHTML = html;
    } else {
      tgBox.innerHTML = '<span>ยังไม่ได้ตั้งค่า</span> · <span style="color:var(--muted)">ใส่ token ในฟอร์มด้านล่าง หรือรัน setup</span>';
    }

    const hist = s.history || [];
    const histBox = $("history");
    if (!hist.length) {
      histBox.innerHTML = '<p style="color:var(--muted)">ยังไม่มีประวัติ (รอการอัปเดตครั้งแรก)</p>';
    } else {
      histBox.innerHTML = '<div style="border:1px solid var(--border);border-radius:8px;overflow-x:auto"><table style="font-size:0.85rem;width:100%;min-width:560px">' +
        '<tr style="background:var(--surface-2)"><th style="padding:5px 10px;text-align:left;white-space:nowrap">เวลา</th><th style="padding:5px 10px;text-align:left">record</th><th style="padding:5px 10px;text-align:left;white-space:nowrap">การกระทำ</th><th style="padding:5px 10px;text-align:left;white-space:nowrap">IP</th></tr>' +
        hist.slice().reverse().map(h => {
          const t = h.time ? new Date(h.time).toLocaleString("th-TH") : "-";
          const act = { updated: "อัปเดต IP", created: "สร้าง record" }[h.action] || h.action;
          const cls = h.action === "updated" ? "" : "ok";
          return '<tr class="' + cls + '"><td style="padding:5px 10px;color:var(--muted);white-space:nowrap">' + t + '</td><td class="mono" style="padding:5px 10px;word-break:break-all">' + escapeHtml(h.record) + " (" + escapeHtml(h.type || "") + ')</td><td style="padding:5px 10px;white-space:nowrap">' + act + '</td><td class="mono" style="padding:5px 10px;white-space:nowrap">' + escapeHtml(h.ip || "-") + "</td></tr>";
        }).join("") + "</table></div>";
    }
  } catch (e) {
    $("pill").textContent = "อ่านสถานะไม่ได้";
    $("pill").className = "pill err";
  }
}

async function copyIp(el) {
  try {
    await navigator.clipboard.writeText(el.textContent);
    toast("คัดลอก " + el.textContent + " แล้ว", "ok");
  } catch (e) {
    toast("คัดลอกไม่ได้: " + e, "err");
  }
}

/* ---------- ตั้งค่า ---------- */

let recordsData = [];
let currentWebuiPassword = "";
let currentWebuiPort = 8123;

async function loadConfig() {
  try {
    const r = await fetch("/config.json");
    const c = await r.json();
    $("api_token").value = c.cloudflare.api_token;
    $("interval").value = c.cloudflare.interval_seconds;
    $("use_ipv4").checked = !!c.cloudflare.use_ipv4;
    $("use_ipv6").checked = !!c.cloudflare.use_ipv6;
    $("webui_password").value = c.cloudflare.webui_password;
    currentWebuiPassword = c.cloudflare.webui_password;
    $("webui_port").value = c.cloudflare.webui_port || 8123;
    currentWebuiPort = c.cloudflare.webui_port || 8123;
    $("log_dir").value = c.cloudflare.log_dir || "";
    $("tg_token").value = c.telegram.bot_token;
    $("tg_chat").value = c.telegram.chat_id;
    $("notify_start").checked = !!c.telegram.notify_start;
    $("notify_stop").checked = !!c.telegram.notify_stop;
    $("notify_ip_change").checked = !!c.telegram.notify_ip_change;
    $("notify_error").checked = !!c.telegram.notify_error;
    $("notify_created").checked = !!c.telegram.notify_created;
    $("daily_report").checked = !!c.telegram.daily_report;
    $("daily_report_time").value = c.telegram.daily_report_time || "08:00";
    $("tunnel_enabled").checked = !!c.tunnel.enabled;
    $("tunnel_token").value = c.tunnel.token;
    $("cloudflared_path").value = c.tunnel.cloudflared_path || "";
    recordsData = c.records.map(r => ({ ...r }));
    renderRecordsEditor();
    loadScanHosts();
  } catch (e) {
    toast("โหลด config ไม่ได้: " + e, "err");
  }
}

function renderRecordsEditor() {
  const box = $("records-editor");
  if (!recordsData.length) {
    box.innerHTML = '<p style="color:var(--muted)">ยังไม่มี record — กด "เพิ่ม record" ข้างล่าง</p>';
    return;
  }
  box.innerHTML = recordsData.map((r, i) => `
    <div class="rec-edit">
      <input type="text" data-i="${i}" data-k="name" value="${escapeHtml(r.name)}" placeholder="home (เติม .zone ให้) หรือ @">
      <input type="text" data-i="${i}" data-k="zone" value="${escapeHtml(r.zone)}" placeholder="zone (เว้น = เดาให้)">
      <div class="mini" title="ผ่าน orange cloud ของ Cloudflare">
        <label><input type="checkbox" data-i="${i}" data-k="proxied" ${r.proxied ? "checked" : ""}> proxy</label>
      </div>
      <input type="number" data-i="${i}" data-k="ttl" value="${r.ttl}" min="60" title="TTL (วินาที)">
      <div class="mini">
        <label title="IPv4"><input type="checkbox" data-i="${i}" data-k="ipv4" ${r.ipv4 ? "checked" : ""}>4</label>
        <label title="IPv6"><input type="checkbox" data-i="${i}" data-k="ipv6" ${r.ipv6 ? "checked" : ""}>6</label>
      </div>
      <button class="btn-del" type="button" data-del="${i}" title="ลบ record">×</button>
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

async function saveConfig() {
  const btn = $("saveBtn");
  btn.disabled = true;
  const keys = recordsData.map(recKey);
  const dup = keys.find((k, i) => k && keys.indexOf(k) !== i);
  if (dup) {
    toast("record ซ้ำ: " + dup + " (กรอกชื่อซ้ำกัน)", "err");
    btn.disabled = false;
    return;
  }
  const payload = {
    cloudflare: {
      api_token: $("api_token").value.trim(),
      interval_seconds: Math.max(15, Math.floor(+$("interval").value || 60)),
      use_ipv4: $("use_ipv4").checked,
      use_ipv6: $("use_ipv6").checked,
      webui_port: Math.max(1, Math.min(65535, Math.floor(+$("webui_port").value || currentWebuiPort))),
      webui_password: $("webui_password").value.trim(),
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
      daily_report: $("daily_report").checked,
      daily_report_time: $("daily_report_time").value.trim() || "08:00",
    },
    tunnel: {
      enabled: $("tunnel_enabled").checked,
      token: $("tunnel_token").value.trim(),
      cloudflared_path: $("cloudflared_path").value.trim(),
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
    toast(j.ok ? "บันทึกสำเร็จ — มีผลในรอบถัดไป" : "บันทึกไม่สำเร็จ: " + j.message, j.ok ? "ok" : "err");
    if (j.ok) {
      const pwChanged = $("webui_password").value.trim() !== currentWebuiPassword;
      const portChanged = payload.cloudflare.webui_port !== currentWebuiPort;
      loadConfig();
      loadStatus();
      if (portChanged) {
        toast("เปลี่ยนพอร์ตหน้าเว็บแล้ว — restart service (restart.bat) เพื่อให้มีผล", "ok");
      }
      if (pwChanged) {
        toast(payload.cloudflare.webui_password ? "ตั้งรหัสผ่านหน้าเว็บแล้ว — กำลังรีเฟรช ต้องเข้าสู่ระบบใหม่" : "ลบรหัสผ่านหน้าเว็บแล้ว", "ok");
        setTimeout(() => location.reload(), 1500);
      }
    }
  } catch (e) {
    toast("บันทึกไม่ได้: " + e, "err");
  }
  btn.disabled = false;
}

async function loadIp() {
  const v4 = $("pub-ipv4");
  const v6 = $("pub-ipv6");
  const nat = $("nat-status");
  v4.textContent = "ตรวจ…";
  v6.textContent = "ตรวจ…";
  nat.textContent = "";
  try {
    const r = await fetch("/ip-check");
    const j = await r.json();
    v4.textContent = j.ipv4 || "ไม่พบ (IPv4)";
    v6.textContent = j.ipv6 || "ไม่มี (IPv6)";
    if (j.nat) {
      const bad = j.nat.nat_type === "cg-nat" || j.nat.nat_type === "private-ip";
      nat.innerHTML = (bad ? '<span style="color:var(--danger)">⚠ ' : '<span style="color:var(--ok)">✓ ') + escapeHtml(j.nat.message) + "</span>";
    }
  } catch (e) {
    v4.textContent = "อ่านไม่ได้: " + e;
  }
}

async function loadCloudflareRecords() {
  const zone = recordsData.find(r => r.zone)?.zone;
  if (!zone) { toast("กรุณาใส่ zone ของ record ก่อน", "err"); return; }
  const btn = $("loadRecords");
  btn.disabled = true;
  try {
    const r = await fetch("/list-records", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ zone }),
    });
    const j = await r.json();
    if (!j.ok) { toast("โหลดไม่ได้: " + j.message, "err"); btn.disabled = false; return; }
    const sel = $("rec-pick");
    if (!j.records.length) { toast("ไม่มี A/AAAA record ใน zone นี้ (จะสร้างให้เองเมื่อมี IP)", "err"); btn.disabled = false; return; }
    sel.hidden = false;
    sel.innerHTML = '<option value="">— เลือก record ที่มีอยู่ —</option>' +
      j.records.map(n => '<option value="' + escapeHtml(n) + '">' + escapeHtml(n) + "</option>").join("");
    sel.onchange = () => {
      if (!sel.value) return;
      const row = recordsData.find(x => !x.name) || recordsData[recordsData.length - 1];
      row.name = sel.value;
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
    : '<option value="">— ยังไม่มี record ใน config —</option>';
}

async function scanPorts() {
  const host = $("scan-host").value;
  const btn = $("scanBtn");
  if (!host) { toast("ยังไม่มี host ให้สแกน (ตั้ง record ก่อน)", "err"); return; }
  btn.disabled = true;
  const box = $("scan-result");
  box.innerHTML = '<p style="color:var(--muted)">กำลังสแกน ' + escapeHtml(host) + " ...</p>";
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
      const label = { open: "เปิด", filtered: "ไม่มีตอบ (ไฟร์วอลล์?)", closed: "ปิด" }[p.status];
      return '<tr class="' + cls + '"><td class="mono">' + p.port + '</td><td class="mono">' + escapeHtml(p.service || "-") + "</td><td>" + label + "</td></tr>";
    }).join("");
    box.innerHTML =
      '<div style="border:1px solid var(--border);border-radius:8px;overflow:hidden"><table style="font-size:0.9rem;width:100%">' +
      '<tr style="background:var(--surface-2)"><th style="padding:6px 10px;text-align:left">พอร์ต</th><th style="padding:6px 10px;text-align:left">บริการ</th><th style="padding:6px 10px;text-align:left">สถานะ</th></tr>' +
      rows + "</table></div>" +
      '<p style="margin-top:8px;font-size:0.85rem;color:var(--ink-2)">' + escapeHtml(j.host) + " → " + escapeHtml(j.ip) +
      " · เปิด " + open.length + " · ปิด " + (j.ports.length - open.length - filtered.length) + " · ไม่มีตอบ " + filtered.length + "</p>";
  } catch (e) {
    box.innerHTML = '<p style="color:var(--danger)">error: ' + escapeHtml(e) + "</p>";
  }
  btn.disabled = false;
}

async function loadLog() {
  const box = $("logview");
  try {
    const r = await fetch("/log");
    box.textContent = await r.text();
    box.scrollTop = box.scrollHeight;
  } catch (e) {
    box.textContent = "อ่าน log ไม่ได้: " + e;
  }
}

async function loadTunnelStatus() {
  try {
    const r = await fetch("/status.json");
    const s = await r.json();
    const t = s.tunnel || {};
    const box = $("tunnel-status");
    const parts = [];
    if (!t.enabled) parts.push('<span style="color:var(--muted)">ปิดใช้งาน (ตั้งค่าในฟอร์มด้านล่าง)</span>');
    if (!t.installed) parts.push('<span class="err">cloudflared ยังไม่ติดตั้ง</span>');
    if (t.running) parts.push('<span class="ok">รันอยู่ (pid ' + t.pid + ")</span>");
    else if (t.enabled) parts.push('<span>ยังไม่รัน</span>');
    box.innerHTML = parts.join(" · ");
  } catch (e) {
    $("tunnel-status").textContent = "อ่านสถานะไม่ได้: " + e;
  }
}

async function tunnelAction(path, okMsg) {
  try {
    const r = await fetch(path, { method: "POST" });
    const j = await r.json();
    toast(j.ok ? okMsg + (j.message ? ": " + j.message : "") : "ไม่สำเร็จ: " + j.message, j.ok ? "ok" : "err");
    loadTunnelStatus();
  } catch (e) {
    toast("error: " + e, "err");
  }
}

async function tgTest() {
  try {
    const r = await fetch("/notify-test", { method: "POST" });
    const j = await r.json();
    toast(j.ok ? "ส่งข้อความทดสอบสำเร็จ — ตรวจใน Telegram" : "ส่งไม่สำเร็จ: " + j.message, j.ok ? "ok" : "err");
  } catch (e) {
    toast("error: " + e, "err");
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
      box.innerHTML = '<p style="color:var(--muted)">คิวว่าง — ไม่มีข้อความค้างส่ง</p>';
      return;
    }
    box.innerHTML = '<div style="border:1px solid var(--border);border-radius:8px;overflow:hidden"><table style="font-size:0.85rem;width:100%">' +
      '<tr style="background:var(--surface-2)"><th style="padding:5px 10px;text-align:left">#</th><th style="padding:5px 10px;text-align:left">ข้อความ</th></tr>' +
      items.map((m, i) => '<tr><td style="padding:5px 10px;color:var(--muted)">' + (i + 1) + '</td><td style="padding:5px 10px;white-space:pre-wrap;word-break:break-all">' + escapeHtml(m) + "</td></tr>").join("") +
      "</table></div>" +
      '<p style="margin-top:6px;font-size:0.85rem;color:var(--muted)">รวม ' + items.length + " ข้อความ — กด “ลองส่งใหม่” เพื่อส่งทันที หรือ “ล้างคิว” เพื่อทิ้ง</p>";
  } catch (e) {
    toast("อ่านคิวไม่ได้: " + e, "err");
  }
}

async function tgFlush() {
  try {
    const r = await fetch("/notify-queue/flush", { method: "POST" });
    const j = await r.json();
    toast(j.ok ? "ส่งใหม่ " + j.sent + " ข้อความ (เหลือค้าง " + j.failed + ")" : "ไม่สำเร็จ: " + j.message, j.ok ? (j.failed ? "err" : "ok") : "err");
    tgQueue();
    loadStatus();
  } catch (e) {
    toast("error: " + e, "err");
  }
}

async function tgClear() {
  if (!confirm("ล้างข้อความค้างส่งทั้งหมดในคิว?")) return;
  try {
    const r = await fetch("/notify-queue/clear", { method: "POST" });
    const j = await r.json();
    toast(j.ok ? "ล้างคิวแล้ว" : "ไม่สำเร็จ: " + j.message, j.ok ? "ok" : "err");
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
    (back ? '<button class="btn-secondary" type="button" id="twz-back">← ย้อนกลับ</button>' : "<span></span>") +
    (next ? '<button class="btn-primary" type="button" id="twz-next">' + next + "</button>" : "") +
    "</div>";

  if (twzStep === 1) {
    body.innerHTML =
      '<p class="wz-step-title">Tunnel คืออะไร ทำไมต้องใช้</p>' +
      '<p class="wz-step-sub">Cloudflare Tunnel เชื่อมต่อเครื่องของคุณกับ Cloudflare โดยตรง — คนเข้าบริการของคุณผ่าน Cloudflare โดยไม่ต้องเปิดพอร์ตที่เราเตอร์ และไม่ต้องพึ่ง IP สาธารณะ</p>' +
      '<div class="wz-help">เหมาะกับ:<ul style="margin:6px 0 0;padding-left:20px">' +
      "<li>ISP แจก IP แบบ CGNAT (DDNS ใช้ไม่ได้)</li>" +
      "<li>ไม่อยากเปิด port forward ที่เราเตอร์</li>" +
      "<li>ให้บริการเว็บ/API ผ่าน Cloudflare</li></ul></div>" +
      actions(false, "เริ่มตั้งค่า →");
    $("twz-next").addEventListener("click", () => { twzStep = 2; renderTunnelWizard(); });
  }

  else if (twzStep === 2) {
    body.innerHTML =
      '<p class="wz-step-title">ขั้นตอนที่ 1: ใส่ Tunnel Token</p>' +
      '<p class="wz-step-sub">สร้างฟรีจาก Cloudflare Zero Trust — กดปุ่มด้านล่างเพื่อเปิดหน้า และทำตามวิธีทำ:</p>' +
      '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px">' +
      '<button class="btn-secondary" type="button" id="twz-open-zt">เปิด Zero Trust ↗</button>' +
      '<button class="btn-secondary" type="button" id="twz-help">ดูวิธีหา token</button></div>' +
      '<label class="field">Tunnel Token<input id="twz-token" type="password" autocomplete="off" placeholder="eyJhIjoi..."></label>' +
      '<div id="twz-msg"></div>' +
      '<div class="wz-help" id="twz-steps" hidden><b>วิธีหา token (ทีละขั้น):</b><ol>' +
      "<li>กดปุ่ม “เปิด Zero Trust” แล้วล็อกอิน</li>" +
      "<li>เมนูซ้าย: Networks → Tunnels → Create a tunnel</li>" +
      "<li>ตั้งชื่อ (เช่น home) → เลือกวิธี Cloudflare-managed → ต่อไป</li>" +
      "<li>กดคัดลอก token จากคำสั่ง install (ส่วน --token eyJ...) — ไม่ต้องรันคำสั่งนั้นจริง</li>" +
      "<li>วาง token ในช่องด้านบน แล้วกด ตรวจสอบ token</li></ol></div>" +
      actions(true, "ตรวจสอบ token →");
    $("twz-back").addEventListener("click", () => { twzStep = 1; renderTunnelWizard(); });
    $("twz-open-zt").addEventListener("click", () => window.open("https://one.dash.cloudflare.com/?to=/:account/networks/tunnels", "_blank"));
    $("twz-help").addEventListener("click", () => {
      const h = $("twz-steps");
      h.hidden = !h.hidden;
      $("twz-help").textContent = h.hidden ? "ดูวิธีหา token" : "ซ่อนวิธีทำ";
    });
    $("twz-next").addEventListener("click", async () => {
      const token = $("twz-token").value.trim();
      if (!token) { $("twz-msg").innerHTML = wzMsg("err", "กรุณาวาง tunnel token ก่อน"); return; }
      const btn = $("twz-next");
      btn.disabled = true;
      $("twz-msg").innerHTML = wzMsg("ok", "กำลังตรวจสอบ (ดาวน์โหลด cloudflared ถ้ายังไม่มี + ทดสอบเชื่อมต่อ ~5 วิ)...");
      try {
        const r = await fetch("/tunnel/test", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token }),
        });
        const j = await r.json();
        if (!j.ok) {
          $("twz-msg").innerHTML = wzMsg("err", j.message + " (ลองกด “ดูวิธีหา token”)");
          btn.disabled = false;
          return;
        }
        twzData.token = token;
        twzData.verified = true;
        $("twz-msg").innerHTML = wzMsg("ok", "✓ " + j.message);
        twzStep = 3;
        renderTunnelWizard();
      } catch (e) {
        $("twz-msg").innerHTML = wzMsg("err", "error: " + e);
        btn.disabled = false;
      }
    });
  }

  else if (twzStep === 3) {
    body.innerHTML =
      '<p class="wz-step-title">ขั้นตอนที่ 2: ตั้ง Public Hostname (เว็บที่จะเปิด)</p>' +
      '<p class="wz-step-sub">token ตรวจผ่านแล้ว — ขั้นนี้ทำที่หน้า Zero Trust (เปิดลิงก์ด้านล่าง) แล้วกลับมากดต่อไป:</p>' +
      '<div class="wz-help"><b>วิธีตั้ง hostname:</b><ol>' +
      "<li>Zero Trust → Networks → Tunnels → กดชื่อ tunnel ของคุณ</li>" +
      "<li>แท็บ Public Hostname → Add a public hostname</li>" +
      "<li>Subdomain: เช่น app · Domain: โดเมนคุณ</li>" +
      "<li>Type: HTTP · URL: localhost:พอร์ตของบริการ (เช่น localhost:8080)</li>" +
      "<li>บันทึก แล้วเข้า https://app.โดเมน.com ได้เลย</li></ol></div>" +
      '<div style="margin-top:10px"><button class="btn-secondary" type="button" id="twz-open-zt2">เปิด Zero Trust ↗</button></div>' +
      actions(true, "ต่อไป →");
    $("twz-back").addEventListener("click", () => { twzStep = 2; renderTunnelWizard(); });
    $("twz-open-zt2").addEventListener("click", () => window.open("https://one.dash.cloudflare.com/?to=/:account/networks/tunnels", "_blank"));
    $("twz-next").addEventListener("click", () => { twzStep = 4; renderTunnelWizard(); });
  }

  else if (twzStep === 4) {
    body.innerHTML =
      '<p class="wz-step-title">ขั้นตอนที่ 3: บันทึกและเริ่ม tunnel</p>' +
      '<p class="wz-step-sub">พร้อมใช้งาน — บันทึก config และเริ่ม tunnel เลย:</p>' +
      '<div class="wz-help">' +
      "Token: ตรวจสอบผ่านแล้ว ✔<br>" +
      "cloudflared: พร้อม (ดาวน์โหลดให้อัตโนมัติถ้ายังไม่มี)<br>" +
      "เริ่มอัตโนมัติ: เปิด (ตอน service เริ่ม)" + "</div>" +
      '<div id="twz-save-msg"></div>' +
      actions(true, "บันทึกและเริ่ม tunnel");
    $("twz-back").addEventListener("click", () => { twzStep = 3; renderTunnelWizard(); });
    $("twz-next").addEventListener("click", async () => {
      const btn = $("twz-next");
      btn.disabled = true;
      $("twz-save-msg").innerHTML = wzMsg("ok", "กำลังบันทึก...");
      try {
        const r = await fetch("/config.json");
        const cfg = await r.json();
        cfg.tunnel = { enabled: true, token: twzData.token, cloudflared_path: "" };
        const s = await fetch("/save-config", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(cfg),
        });
        const sj = await s.json();
        if (!sj.ok) {
          $("twz-save-msg").innerHTML = wzMsg("err", "บันทึกไม่สำเร็จ: " + sj.message);
          btn.disabled = false;
          return;
        }
        const st = await fetch("/tunnel/start", { method: "POST" });
        const stj = await st.json();
        toast(stj.ok ? "ตั้งค่า Tunnel เสร็จ — " + stj.message : "บันทึกแล้ว แต่เริ่ม tunnel ไม่ได้: " + stj.message, stj.ok ? "ok" : "err");
        $("tunnel-wizard").hidden = true;
        loadConfig();
        loadTunnelStatus();
      } catch (e) {
        $("twz-save-msg").innerHTML = wzMsg("err", "error: " + e);
        btn.disabled = false;
      }
    });
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
    toast("โหลดไฟล์ config ไม่ได้: " + e, "err");
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
    toast(j.ok ? "บันทึกไฟล์สำเร็จ — มีผลในรอบถัดไป" : "บันทึกไม่สำเร็จ: " + j.message, j.ok ? "ok" : "err");
    if (j.ok) loadStatus();
  } catch (e) {
    toast("บันทึกไม่ได้: " + e, "err");
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
  return '<div class="' + (kind === "ok" ? "wz-ok-box" : "wz-err-box") + '">' + text + "</div>";
}

function renderWizard() {
  const dots = document.querySelectorAll("#wz-steps .dot");
  dots.forEach((d, i) => d.classList.toggle("on", i < wzStep));
  const body = $("wz-body");
  const actions = (back, next) =>
    '<div class="wz-actions">' +
    (back ? '<button class="btn-secondary" type="button" id="wz-back">← ย้อนกลับ</button>' : "<span></span>") +
    (next ? '<button class="btn-primary" type="button" id="wz-next">' + next + "</button>" : "") +
    "</div>";

  if (wzStep === 1) {
    body.innerHTML =
      '<p class="wz-step-title">ยินดีต้อนรับ</p>' +
      '<p class="wz-step-sub">โปรแกรมจะตรวจหา IP สาธารณะของคุณ แล้วอัปเดต DNS record บน Cloudflare ให้อัตโนมัติเมื่อ IP เปลี่ยน ขั้นตอนทั้งหมด 5 ขั้น สั้น ๆ แค่นี้</p>' +
      actions(false, "เริ่มตั้งค่า →");
    $("wz-next").addEventListener("click", () => { wzStep = 2; renderWizard(); });
  }

  else if (wzStep === 2) {
    body.innerHTML =
      '<p class="wz-step-title">ขั้นตอนที่ 1: ใส่ API token ของ Cloudflare</p>' +
      '<p class="wz-step-sub">token ใช้สิทธิ์แก้ DNS ของคุณเท่านั้น สร้างได้ฟรี เปิดหน้านี้แล้วทำตามขั้นด้านล่าง:</p>' +
      '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px">' +
      '<button class="btn-secondary" type="button" id="wz-open-token">เปิดหน้าสร้าง token ↗</button>' +
      '<button class="btn-secondary" type="button" id="wz-token-help">ดูวิธีหา token</button></div>' +
      '<label class="field">API Token<input id="wz-token" type="password" autocomplete="off" placeholder="cfut_..."></label>' +
      '<div id="wz-token-msg"></div>' +
      '<div class="wz-help" id="wz-token-steps" hidden><b>วิธีหา token (ทีละขั้น):</b><ol>' +
      "<li>กดปุ่ม “เปิดหน้าสร้าง token” แล้วล็อกอิน Cloudflare</li>" +
      "<li>กดปุ่มสีส้ม Create Token</li>" +
      "<li>เลือก template ชื่อ Edit zone DNS แล้วกด Use template</li>" +
      "<li>ในช่อง Zone Resources เลือก Include → Specific zone → เลือกโดเมนของคุณ</li>" +
      "<li>กด Continue to summary → Create Token</li>" +
      "<li>คัดลอก token ทันที (แสดงครั้งเดียว ขึ้นต้นด้วย cfut_) แล้ววางในช่องด้านบน</li></ol></div>" +
      actions(true, "ตรวจสอบ token →");
    $("wz-back").addEventListener("click", () => { wzStep = 1; renderWizard(); });
    $("wz-open-token").addEventListener("click", () => window.open("https://dash.cloudflare.com/profile/api-tokens", "_blank"));
    $("wz-token-help").addEventListener("click", () => {
      const h = $("wz-token-steps");
      h.hidden = !h.hidden;
      $("wz-token-help").textContent = h.hidden ? "ดูวิธีหา token" : "ซ่อนวิธีทำ";
    });
    $("wz-next").addEventListener("click", async () => {
      const token = $("wz-token").value.trim();
      if (!token) { $("wz-token-msg").innerHTML = wzMsg("err", "กรุณาวาง API token ก่อน"); return; }
      $("wz-next").disabled = true;
      $("wz-token-msg").innerHTML = wzMsg("ok", "กำลังตรวจสอบ token...");
      try {
        const r = await fetch("/verify-token", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token }),
        });
        const j = await r.json();
        if (!j.ok) {
          $("wz-token-msg").innerHTML = wzMsg("err", "ตรวจสอบไม่ผ่าน: " + j.message + " (ลองกด “ดูวิธีหา token”)");
          $("wz-next").disabled = false;
          return;
        }
        wzData.token = token;
        wzZones = j.zones || [];
        wzStep = 3;
        renderWizard();
      } catch (e) {
        $("wz-token-msg").innerHTML = wzMsg("err", "ติดต่อเซิร์ฟเวอร์ไม่ได้: " + e);
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
      '<p class="wz-step-title">ขั้นตอนที่ 2: เลือกโดเมน (zone) และ record</p>' +
      '<p class="wz-step-sub">เลือกโดเมน แล้วระบุชื่อ record — ใส่แค่ชื่อสั้น ๆ ก็ได้ (เช่น home) โปรแกรมเติม .โดเมน ให้อัตโนมัติ ส่วน @ คือหน้าหลักของโดเมน</p>' +
      '<label class="field">Zone (โดเมน)' + zoneOptions + "</label>" +
      '<div style="margin:2px 0 10px">' +
      '<button class="btn-secondary" type="button" id="wz-load-records">โหลดชื่อ record ที่มีอยู่จาก Cloudflare</button> ' +
      '<select id="wz-record-pick" class="wz-zone-select" style="margin-top:6px" hidden></select></div>' +
      '<h3 style="margin-top:16px">Record ที่จะอัปเดต</h3><div id="wz-records"></div>' +
      '<button class="btn-secondary" type="button" id="wz-add-record">+ เพิ่ม record</button>' +
      actions(true, "ต่อไป →");
    $("wz-back").addEventListener("click", () => { wzStep = 2; renderWizard(); });
    $("wz-add-record").addEventListener("click", () => {
      wzData.records.push({ name: "", proxied: false, ttl: 60 });
      renderWzRecords();
    });
    $("wz-load-records").addEventListener("click", async () => {
      const zone = ($("wz-zone").value || "").trim();
      if (!zone) { toast("เลือก zone ก่อน", "err"); return; }
      const btn = $("wz-load-records");
      btn.disabled = true;
      try {
        const r = await fetch("/list-records", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token: wzData.token, zone }),
        });
        const j = await r.json();
        if (!j.ok) { toast("โหลดไม่ได้: " + j.message, "err"); btn.disabled = false; return; }
        const sel = $("wz-record-pick");
        sel.hidden = false;
        sel.innerHTML = '<option value="">— เลือก record ที่มีอยู่ —</option>' +
          j.records.map(n => '<option value="' + escapeHtml(n) + '">' + escapeHtml(n) + "</option>").join("");
        sel.onchange = () => {
          if (!sel.value) return;
          const row = wzData.records.find(x => !x.name) || wzData.records[0];
          row.name = sel.value;
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
      if (!wzData.zone) { toast("กรุณาเลือก zone ก่อน", "err"); return; }
      const recs = wzData.records.map((r, i) => ({
        name: r.name,
        zone: wzData.zone,
        proxied: r.proxied,
        ttl: r.ttl,
        ipv4: true,
        ipv6: true,
      }));
      if (!recs.length || !recs[0].name) { toast("กรุณากรอกชื่อ record อย่างน้อย 1 ตัว", "err"); return; }
      const keys = recs.map(recKey);
      const dup = keys.find((k, i) => k && keys.indexOf(k) !== i);
      if (dup) { toast("record ซ้ำ: " + dup + " (กรอกชื่อซ้ำกัน)", "err"); return; }
      wzData.records = recs;
      wzStep = 4;
      renderWizard();
    });
  }

  else if (wzStep === 4) {
    body.innerHTML =
      '<p class="wz-step-title">ขั้นตอนที่ 3: แจ้งเตือน Telegram (ไม่บังคับ)</p>' +
      '<p class="wz-step-sub">จะให้แจ้งทาง Telegram เมื่อ IP เปลี่ยน / เกิด error ก็ใส่ตรงนี้ ถ้ายังไม่ต้องการกด "ข้าม" ได้</p>' +
      '<label class="field">Bot token (สร้างจาก @BotFather ใน Telegram)<input id="wz-tg-token" type="password" autocomplete="off" placeholder="123456789:AAHxxx..."></label>' +
      '<div id="wz-tg-msg"></div>' +
      '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px">' +
      '<button class="btn-secondary" type="button" id="wz-tg-find">ค้นหา chat id ให้อัตโนมัติ</button>' +
      '<button class="btn-secondary" type="button" id="wz-tg-test" disabled>ส่งข้อความทดสอบ</button></div>' +
      '<div class="wz-help">วิธี: เปิด Telegram ค้นหา @BotFather → ส่ง /newbot → ตั้งชื่อ → คัดลอก token มาวาง แล้วเปิดแชทกับ bot ใหม่และกด Start จากนั้นกด "ค้นหา chat id ให้อัตโนมัติ"</div>' +
      actions(true, "ข้าม →");
    $("wz-back").addEventListener("click", () => { wzStep = 3; renderWizard(); });
    let chatId = "";
    $("wz-tg-find").addEventListener("click", async () => {
      const token = $("wz-tg-token").value.trim();
      if (!token) { $("wz-tg-msg").innerHTML = wzMsg("err", "วาง bot token ก่อน"); return; }
      $("wz-tg-msg").innerHTML = wzMsg("ok", "กำลังค้นหาบทสนทนาล่าสุด...");
      try {
        const r = await fetch("/resolve-chat-id", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ bot_token: token }),
        });
        const j = await r.json();
        if (!j.ok) { $("wz-tg-msg").innerHTML = wzMsg("err", j.message); return; }
        chatId = j.chat_id;
        $("wz-tg-msg").innerHTML = wzMsg("ok", "พบ chat id: " + chatId);
        $("wz-tg-test").disabled = false;
      } catch (e) { $("wz-tg-msg").innerHTML = wzMsg("err", "error: " + e); }
    });
    $("wz-tg-test").addEventListener("click", async () => {
      const token = $("wz-tg-token").value.trim();
      try {
        const r = await fetch("/notify-test-raw", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ bot_token: token, chat_id: chatId, text: "✅ ทดสอบการแจ้งเตือนจาก Cloudflare DDNS" }),
        });
        const j = await r.json();
        $("wz-tg-msg").innerHTML = j.ok ? wzMsg("ok", "ส่งข้อความทดสอบสำเร็จ — ตรวจใน Telegram") : wzMsg("err", "ส่งไม่ได้: " + j.message);
      } catch (e) { $("wz-tg-msg").innerHTML = wzMsg("err", "error: " + e); }
    });
    $("wz-next").addEventListener("click", () => {
      wzData.tg = { token: $("wz-tg-token").value.trim(), chat_id: chatId };
      wzStep = 5;
      renderWizard();
    });
  }

  else if (wzStep === 5) {
    const tgOn = !!(wzData.tg && wzData.tg.token && wzData.tg.chat_id);
    body.innerHTML =
      '<p class="wz-step-title">ขั้นตอนที่ 4: ตรวจสอบและบันทึก</p>' +
      '<p class="wz-step-sub">สรุปสิ่งที่กำลังจะตั้งค่า:</p>' +
      '<div class="wz-help">' +
      "API token: ตรวจสอบผ่านแล้ว ✔<br>" +
      "Zone: <b>" + escapeHtml(wzData.zone) + "</b><br>" +
      "Records: " + wzData.records.length + " ตัว (" + wzData.records.map(r => escapeHtml(r.name)).join(", ") + ")<br>" +
      "Telegram: " + (tgOn ? "เปิด (chat " + escapeHtml(wzData.tg.chat_id) + ")" : "ปิด (ข้าม)") + "</div>" +
      '<div id="wz-save-msg"></div>' +
      actions(true, "บันทึกและเริ่มใช้งาน");
    $("wz-back").addEventListener("click", () => { wzStep = 4; renderWizard(); });
    $("wz-next").addEventListener("click", async () => {
      const btn = $("wz-next");
      btn.disabled = true;
      const payload = {
        cloudflare: {
          api_token: wzData.token,
          interval_seconds: 60,
          use_ipv4: true,
          use_ipv6: true,
          webui_password: "",
        },
        telegram: {
          bot_token: (wzData.tg && wzData.tg.token) || "",
          chat_id: (wzData.tg && wzData.tg.chat_id) || "",
          notify_start: true,
          notify_stop: true,
          notify_ip_change: true,
          notify_error: true,
          notify_created: true,
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
          $("wz-save-msg").innerHTML = wzMsg("err", "บันทึกไม่สำเร็จ: " + j.message);
          btn.disabled = false;
          return;
        }
        toast("ตั้งค่าเสร็จสมบูรณ์ — DDNS เริ่มทำงานแล้ว", "ok");
        closeWizard();
        loadStatus();
        loadConfig();
      } catch (e) {
        $("wz-save-msg").innerHTML = wzMsg("err", "error: " + e);
        btn.disabled = false;
      }
    });
  }
}

function renderWzRecords() {
  const box = $("wz-records");
  box.innerHTML = wzData.records.map((r, i) =>
    '<div class="rec-edit">' +
    '<input type="text" data-i="' + i + '" data-k="name" value="' + escapeHtml(r.name) + '" placeholder="home (เติม .zone ให้) หรือ @">' +
    '<div class="mini" title="ผ่าน orange cloud ของ Cloudflare"><label><input type="checkbox" data-i="' + i + '" data-k="proxied" ' + (r.proxied ? "checked" : "") + "> proxy</label></div>" +
    '<input type="number" data-i="' + i + '" data-k="ttl" value="' + r.ttl + '" min="60" title="TTL (วินาที)">' +
    '<button class="btn-del" type="button" data-del="' + i + '" title="ลบ record">×</button></div>').join("");

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
$("refresh").addEventListener("click", loadStatus);
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
$("tunnelStart").addEventListener("click", () => tunnelAction("/tunnel/start", "เริ่ม tunnel"));
$("tunnelStop").addEventListener("click", () => tunnelAction("/tunnel/stop", "หยุด tunnel"));
$("tunnelDownload").addEventListener("click", () => tunnelAction("/tunnel/download", "ดาวน์โหลด"));
$("tunnelWizard").addEventListener("click", openTunnelWizard);
$("twz-close").addEventListener("click", () => { $("tunnel-wizard").hidden = true; });

loadStatus();
loadConfig();
loadIp();
loadLog();
loadTunnelStatus();
checkSetup();
setInterval(loadStatus, 10000);
</script>
</body>
</html>
"""


# ---------- แปลง config <-> dict ----------


def _cfg_to_dict(cfg):
    return {
        "cloudflare": {
            "api_token": cfg.api_token,
            "interval_seconds": cfg.interval_seconds,
            "use_ipv4": cfg.use_ipv4,
            "use_ipv6": cfg.use_ipv6,
            "webui_port": cfg.webui_port,
            "webui_password": cfg.webui_password,
            "log_dir": cfg.log_dir if cfg.log_dir != config_mod.DEFAULT_LOG_DIR else "",
        },
        "telegram": {
            "bot_token": cfg.telegram_bot_token,
            "chat_id": cfg.telegram_chat_id,
            "notify_start": cfg.notify_start,
            "notify_stop": cfg.notify_stop,
            "notify_ip_change": cfg.notify_ip_change,
            "notify_error": cfg.notify_error,
            "notify_created": cfg.notify_created,
            "daily_report": cfg.daily_report,
            "daily_report_time": cfg.daily_report_time,
        },
        "tunnel": {
            "enabled": cfg.tunnel_enabled,
            "token": cfg.tunnel_token,
            "cloudflared_path": cfg.cloudflared_path,
        },
        "records": [
            {
                "name": r.name,
                "zone": r.zone,
                "proxied": r.proxied,
                "ttl": r.ttl,
                "ipv4": r.ipv4,
                "ipv6": r.ipv6,
            }
            for r in cfg.records
        ],
    }


def _dict_to_ini(data):
    """สร้างข้อความ config.ini จาก dict (โครงสร้างเดียวกับ _cfg_to_dict)."""
    cf = data.get("cloudflare", {})
    tg = data.get("telegram", {})
    lines = ["[cloudflare]"]

    def kv(key, value):
        lines.append(f"{key} = {value}")

    kv("api_token", str(cf.get("api_token", "")).strip())
    kv("interval_seconds", int(cf.get("interval_seconds", 60)))
    kv("use_ipv4", str(bool(cf.get("use_ipv4"))).lower())
    kv("use_ipv6", str(bool(cf.get("use_ipv6"))).lower())
    kv("webui_port", int(cf.get("webui_port", 8123)))
    kv("webui_password", str(cf.get("webui_password", "")).strip())
    kv("log_dir", str(cf.get("log_dir", "")).strip())
    kv("telegram_bot_token", str(tg.get("bot_token", "")).strip())
    kv("telegram_chat_id", str(tg.get("chat_id", "")).strip())
    kv("notify_start", str(bool(tg.get("notify_start", True))).lower())
    kv("notify_stop", str(bool(tg.get("notify_stop", True))).lower())
    kv("notify_ip_change", str(bool(tg.get("notify_ip_change", True))).lower())
    kv("notify_error", str(bool(tg.get("notify_error", True))).lower())
    kv("notify_created", str(bool(tg.get("notify_created", True))).lower())
    kv("daily_report", str(bool(tg.get("daily_report", True))).lower())
    kv("daily_report_time", str(tg.get("daily_report_time", "08:00")).strip() or "08:00")
    tu = data.get("tunnel", {})
    kv("tunnel_enabled", str(bool(tu.get("enabled", False))).lower())
    kv("tunnel_token", str(tu.get("token", "")).strip())
    kv("cloudflared_path", str(tu.get("cloudflared_path", "")).strip())
    lines.append("")
    for rec in data.get("records", []):
        name = str(rec.get("name", "")).strip().rstrip(".")
        if not name:
            continue
        lines.append(f"[record:{name}]")
        kv("zone", str(rec.get("zone", "")).strip().rstrip("."))
        kv("proxied", str(bool(rec.get("proxied", False))).lower())
        kv("ttl", max(int(rec.get("ttl", 60)), 60))
        kv("ipv4", str(bool(rec.get("ipv4", True))).lower())
        kv("ipv6", str(bool(rec.get("ipv6", True))).lower())
        lines.append("")
    return "\n".join(lines)


class WebUIHandler(BaseHTTPRequestHandler):
    server_version = "CloudflareDDNSWebUI/2.0"

    def _load_records_time(self):
        """อ่าน records_time จาก state.json (เวลา IP ล่าสุดของแต่ละ record)"""
        try:
            import json as _json
            import os

            path = os.path.join(config_mod.DEFAULT_DATA_DIR, "state.json")
            with open(path, "r", encoding="utf-8") as handle:
                state = _json.load(handle)
            return state.get("records_time", {})
        except (OSError, ValueError):
            return {}

    @property
    def cfg(self):
        return self.server.cfg

    def log_message(self, *args):
        pass

    # ---- helpers ----

    def _send(self, code, body, content_type="text/html; charset=utf-8"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, code, payload):
        self._send(code, json.dumps(payload, ensure_ascii=False), "application/json; charset=utf-8")

    def _authed(self):
        password = self.cfg.webui_password
        if not password:
            return True
        cookies = self.headers.get("Cookie", "")
        for part in cookies.split(";"):
            key, _, value = part.strip().partition("=")
            if key == "cfddns_session" and value == password:
                return True
        return False

    def _login_block(self):
        return """<div style="display:flex;min-height:100vh;align-items:center;justify-content:center">
<div class="panel" style="width:320px;margin:0">
  <h2 style="margin-bottom:14px">เข้าสู่ระบบ</h2>
  <form onsubmit="doLogin(event)">
    <input id="pw" type="password" placeholder="รหัสผ่าน webui_password" style="width:100%;padding:9px 10px;border:1px solid var(--border);border-radius:8px;font-size:14px;background:var(--bg)">
    <p style="margin-top:12px"><button class="btn-primary" type="submit" style="width:100%">เข้าสู่ระบบ</button></p>
  </form>
</div></div>
<script>
async function doLogin(ev) {
  ev.preventDefault();
  const r = await fetch("/login", { method: "POST", body: new URLSearchParams({ pw: document.getElementById("pw").value }) });
  if (r.ok) location.reload(); else alert("รหัสผ่านไม่ถูกต้อง");
}
</script>"""

    # ---- GET ----

    def do_GET(self):
        if self.path == "/ip-check":
            from . import ip_detect

            import concurrent.futures

            def check(version):
                return version, ip_detect.get_public_ip(version, timeout=6)

            result = {"ipv4": "", "ipv6": "", "nat": None}
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(check, 4), pool.submit(check, 6)]
                for future in concurrent.futures.as_completed(futures):
                    version, ip = future.result()
                    result["ipv4" if version == 4 else "ipv6"] = ip or ""
            if result["ipv4"]:
                result["nat"] = ip_detect.nat_report(result["ipv4"], timeout=5)
            return self._send_json(200, result)

        if self.path == "/notify-queue":
            if not self._authed():
                return self._send_json(401, {"ok": False, "message": "unauthorized"})
            return self._send_json(200, {"ok": True, "queue": notifier.load_queue()})

        if self.path == "/log":
            import os

            log_path = os.path.join(self.cfg.log_dir, "cloudflare-ddns.log")
            try:
                with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
                    lines = handle.readlines()
                body = "".join(lines[-200:])
                return self._send(200, body, "text/plain; charset=utf-8")
            except OSError as exc:
                return self._send(200, f"(ยังไม่มีไฟล์ log: {exc})", "text/plain; charset=utf-8")

        if self.path == "/status.json":
            if not self._authed():
                return self._send_json(401, {"ok": False, "message": "unauthorized"})
            engine = ddns.DDNSEngine(self.server.config_path)
            status = engine.status()
            status["records_time"] = self._load_records_time()
            cfg_errors = self.cfg.validate()
            status["config_ok"] = not cfg_errors
            status["config_errors"] = cfg_errors
            notify = notifier.TelegramNotifier.from_config(self.cfg)
            status["telegram"] = {
                "enabled": notify.enabled,
                "chat_id": notify.chat_id,
                "queue": notifier.queue_size(),
            }
            status["tunnel"] = _get_tunnel_mgr().status(self.cfg)
            status["record_errors"] = {}
            return self._send_json(200, status)

        if self.path == "/config.json":
            if not self._authed():
                return self._send_json(401, {"ok": False, "message": "unauthorized"})
            return self._send_json(200, _cfg_to_dict(self.cfg))

        if self.path == "/config-file":
            if not self._authed():
                return self._send_json(401, {"ok": False, "message": "unauthorized"})
            return self._send(200, self.cfg.raw_text(), "text/plain; charset=utf-8")

        if self.path == "/setup-state":
            errors = self.cfg.validate()
            return self._send_json(200, {"needs_setup": bool(errors), "errors": errors})

        if not self._authed():
            return self._send(200, PAGE.replace("__LOGIN__", self._login_block()).replace("__VERSION__", __version__))
        return self._send(200, PAGE.replace("__LOGIN__", "").replace("__VERSION__", __version__))

    # ---- POST ----

    def _read_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(length).decode("utf-8", "replace")

    def do_POST(self):
        body = self._read_body()

        if self.path == "/login":
            form = dict(__import__("urllib.parse", fromlist=["parse_qsl"]).parse_qsl(body))
            if form.get("pw") == self.cfg.webui_password:
                self.send_response(302)
                self.send_header("Location", "/")
                self.send_header("Set-Cookie", f"cfddns_session={self.cfg.webui_password}; HttpOnly; Path=/")
                self.end_headers()
                return
            return self._send_json(401, {"ok": False, "message": "รหัสผ่านไม่ถูกต้อง"})

        if not self._authed():
            return self._send_json(401, {"ok": False, "message": "unauthorized"})

        if self.path == "/verify-token":
            from . import cloudflare_api

            try:
                data = json.loads(body)
            except ValueError:
                return self._send_json(400, {"ok": False, "message": "JSON ผิดรูปแบบ"})
            token = str(data.get("token", "")).strip()
            if not token:
                return self._send_json(400, {"ok": False, "message": "ไม่พบ token"})
            api = cloudflare_api.CloudflareAPI(token)
            try:
                api.verify_token()
            except cloudflare_api.CloudflareError as exc:
                return self._send_json(400, {"ok": False, "message": str(exc)})
            try:
                zones = [z["name"] for z in api.list_zones()]
            except cloudflare_api.CloudflareError as exc:
                zones = []
            return self._send_json(200, {"ok": True, "zones": zones})

        if self.path == "/resolve-chat-id":
            try:
                data = json.loads(body)
            except ValueError:
                return self._send_json(400, {"ok": False, "message": "JSON ผิดรูปแบบ"})
            token = str(data.get("bot_token", "")).strip()
            if not token:
                return self._send_json(400, {"ok": False, "message": "ไม่พบ bot token"})
            chat_id, error = notifier.get_chat_id(token)
            if not chat_id:
                return self._send_json(400, {"ok": False, "message": error})
            return self._send_json(200, {"ok": True, "chat_id": chat_id})

        if self.path == "/notify-test-raw":
            try:
                data = json.loads(body)
            except ValueError:
                return self._send_json(400, {"ok": False, "message": "JSON ผิดรูปแบบ"})
            notify = notifier.TelegramNotifier(
                str(data.get("bot_token", "")).strip(),
                str(data.get("chat_id", "")).strip(),
            )
            ok, error = notify.send_raw(str(data.get("text", "ทดสอบ")))
            return self._send_json(200 if ok else 400, {"ok": ok, "message": error or "ส่งสำเร็จ"})

        if self.path == "/save-file":
            try:
                data = json.loads(body)
            except ValueError:
                return self._send_json(400, {"ok": False, "message": "JSON ผิดรูปแบบ"})
            ok, message = self.cfg.save_text(str(data.get("text", "")))
            return self._send_json(200 if ok else 400, {"ok": ok, "message": message})

        if self.path == "/list-records":
            from . import cloudflare_api

            try:
                data = json.loads(body)
            except ValueError:
                return self._send_json(400, {"ok": False, "message": "JSON ผิดรูปแบบ"})
            token = str(data.get("token") or "").strip() or self.cfg.api_token
            zone = str(data.get("zone") or "").strip()
            if not token:
                return self._send_json(400, {"ok": False, "message": "ไม่พบ token (ตั้งค่า Cloudflare ก่อน)"})
            if not zone:
                return self._send_json(400, {"ok": False, "message": "ไม่พบ zone"})
            api = cloudflare_api.CloudflareAPI(token)
            try:
                zone_id = api.get_zone_id(zone)
                records = api.list_dns_records(zone_id)
            except cloudflare_api.CloudflareError as exc:
                return self._send_json(400, {"ok": False, "message": str(exc)})
            names = sorted({r["name"] for r in records})
            return self._send_json(200, {"ok": True, "records": names})

        if self.path == "/port-scan":
            import concurrent.futures
            import socket

            from .config import fqdn_name

            try:
                data = json.loads(body)
            except ValueError:
                return self._send_json(400, {"ok": False, "message": "JSON ผิดรูปแบบ"})
            host = str(data.get("host", "")).strip().rstrip(".")
            allowed = {fqdn_name(rec.name, rec.zone).lower() for rec in self.cfg.records}
            if host.lower() not in allowed:
                return self._send_json(
                    403,
                    {"ok": False, "message": "อนุญาตให้สแกนเฉพาะ host ที่ตั้งไว้ใน config เท่านั้น"},
                )
            try:
                ports = [int(p) for p in (data.get("ports") or DEFAULT_SCAN_PORTS)]
                ports = [p for p in ports if 1 <= p <= 65535]
            except (TypeError, ValueError):
                return self._send_json(400, {"ok": False, "message": "รายการพอร์ตไม่ถูกต้อง (คั่นด้วย ,)"})
            if not ports:
                return self._send_json(400, {"ok": False, "message": "ไม่มีพอร์ตให้สแกน"})
            try:
                ip = socket.gethostbyname(host)
            except socket.gaierror as exc:
                return self._send_json(400, {"ok": False, "message": f"resolve {host} ไม่ได้: {exc}"})

            def _probe(port):
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1.5)
                try:
                    result = sock.connect_ex((ip, port))
                except socket.error:
                    result = -1
                finally:
                    sock.close()
                if result == 0:
                    status = "open"
                elif result in (10060, 110, -1):
                    status = "filtered"
                else:
                    status = "closed"
                return {"port": port, "service": PORT_SERVICES.get(port, ""), "status": status}

            with concurrent.futures.ThreadPoolExecutor(max_workers=64) as pool:
                results = list(pool.map(_probe, ports))
            results.sort(key=lambda r: r["port"])
            return self._send_json(200, {"ok": True, "host": host, "ip": ip, "ports": results})

        if self.path == "/notify-queue/flush":
            if not self._authed():
                return self._send_json(401, {"ok": False, "message": "unauthorized"})
            notify = notifier.TelegramNotifier.from_config(self.cfg)
            if not notify.enabled:
                return self._send_json(400, {"ok": False, "message": "ยังไม่ได้ตั้งค่า Telegram ใน config"})
            sent, failed = notify.flush()
            return self._send_json(200, {"ok": True, "sent": sent, "failed": failed})

        if self.path == "/notify-queue/clear":
            if not self._authed():
                return self._send_json(401, {"ok": False, "message": "unauthorized"})
            notifier.clear_queue()
            return self._send_json(200, {"ok": True, "message": "ล้างคิวแล้ว"})

        if self.path == "/tunnel/test":
            import copy
            import time

            try:
                data = json.loads(body)
            except ValueError:
                return self._send_json(400, {"ok": False, "message": "JSON ผิดรูปแบบ"})
            token = str(data.get("token", "")).strip()
            if not token:
                return self._send_json(400, {"ok": False, "message": "กรุณาวาง tunnel token ก่อน"})
            test_cfg = copy.copy(self.cfg)
            test_cfg.tunnel_token = token
            test_cfg.tunnel_enabled = True
            ok, message = _get_tunnel_mgr().start(test_cfg)
            if not ok:
                return self._send_json(400, {"ok": False, "message": message})
            time.sleep(4)  # รอให้ cloudflared ตายเองถ้า token ผิด
            still_running = _get_tunnel_mgr().status(test_cfg)["running"]
            _get_tunnel_mgr().stop()
            if still_running:
                return self._send_json(200, {"ok": True, "message": "token ใช้ได้ — tunnel เชื่อมต่อ Cloudflare แล้ว (หยุดชั่วคราว รอขั้นตอนสุดท้าย)"})
            return self._send_json(
                400,
                {"ok": False, "message": "token ตรวจไม่ผ่าน — cloudflared เชื่อมต่อไม่ได้ (ตรวจ token/อินเทอร์เน็ต/ไฟร์วอลล์)"},
            )

        if self.path == "/tunnel/start":
            ok, message = _get_tunnel_mgr().start(self.cfg)
            return self._send_json(200 if ok else 400, {"ok": ok, "message": message})

        if self.path == "/tunnel/stop":
            ok, message = _get_tunnel_mgr().stop()
            return self._send_json(200 if ok else 400, {"ok": ok, "message": message})

        if self.path == "/tunnel/download":
            from . import tunnel as tunnel_mod

            ok, message = tunnel_mod.ensure_installed(self.cfg)
            return self._send_json(200 if ok else 400, {"ok": ok, "message": message})

        if self.path == "/save-config":
            try:
                data = json.loads(body)
            except ValueError:
                return self._send_json(400, {"ok": False, "message": "JSON ผิดรูปแบบ"})
            ini_text = _dict_to_ini(data)
            ok, message = self.cfg.save_text(ini_text)
            return self._send_json(200 if ok else 400, {"ok": ok, "message": message})

        if self.path == "/notify-test":
            notify = notifier.TelegramNotifier.from_config(self.cfg)
            if not notify.enabled:
                return self._send_json(400, {"ok": False, "message": "ยังไม่ได้ตั้งค่า Telegram ใน config"})
            ok, error = notify.send_raw("✅ ทดสอบการแจ้งเตือนจาก Cloudflare DDNS (Web UI)")
            return self._send_json(200 if ok else 500, {"ok": ok, "message": error or "ส่งสำเร็จ — ตรวจใน Telegram"})

        return self._send_json(404, {"ok": False, "message": "ไม่พบ path"})


class WebUI:
    def __init__(self, config_path=config_mod.DEFAULT_CONFIG_PATH, port=None, password=None):
        config_mod.migrate_legacy_data()
        self.config_path = config_path
        self.cfg = config_mod.Config(config_path)
        self.port = port or self.cfg.webui_port
        if password is not None:
            self.cfg.webui_password = password
        handler = type("Handler", (WebUIHandler,), {})
        self.server = ThreadingHTTPServer(("127.0.0.1", self.port), handler)
        self.server.cfg = self.cfg
        self.server.config_path = config_path
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def start(self):
        self.thread.start()
        log.info("Web UI เปิดที่ http://127.0.0.1:%d", self.port)

    def serve_forever(self):
        self.start()
        self.thread.join()

    def stop(self):
        self.server.shutdown()
