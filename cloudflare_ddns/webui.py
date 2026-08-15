"""Web UI: ดูสถานะ + ตั้งค่าผ่านเบราว์เซอร์ (stdlib ล้วน, one-page).

- เปิดเฉพาะ 127.0.0.1
- ถ้าตั้ง webui_password ไว้ต้องใส่รหัสก่อน (cookie แบบง่าย)
- ฟอร์มตั้งค่าสร้าง/ตรวจ config.ini ให้อัตโนมัติ (ไม่มี textarea ให้มั่ว)
"""

import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import config as config_mod
from . import ddns
from . import notifier

log = logging.getLogger("cloudflare-ddns")

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

/* records editor */
.rec-edit {
  display: grid; grid-template-columns: minmax(150px, 1.4fr) minmax(120px, 1fr) 88px 76px 52px auto;
  gap: 8px; align-items: center; margin-bottom: 8px;
}
.rec-edit input[type="text"], .rec-edit input[type="number"] {
  width: 100%; font-size: 0.9rem; padding: 7px 9px;
  border: 1px solid var(--border); border-radius: 8px; background: var(--bg); color: var(--ink);
}
.rec-edit .mini { display: flex; gap: 10px; justify-content: center; font-size: 0.85rem; color: var(--muted); }
.rec-edit .mini input { accent-color: var(--accent); }
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
  .rec-edit { grid-template-columns: 1fr 1fr; }
  .panel { padding: 14px; }
  .record-row { gap: 10px; }
  .rec-meta { width: 100%; text-align: left; }
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
      <p>กดที่ IP เพื่อคัดลอก</p>
    </div>
    <div id="records" class="records"><p style="color:var(--muted)">กำลังโหลด…</p></div>
  </section>

  <section class="panel">
    <div class="panel-head"><h2>แจ้งเตือน Telegram</h2></div>
    <div class="tg-row">
      <span id="tgstatus" class="tg-status">กำลังโหลด…</span>
      <button id="tgTest" class="btn-secondary">ส่งข้อความทดสอบ</button>
    </div>
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

    <h3>DNS records</h3>
    <div id="records-editor"></div>
    <button id="addRecord" class="btn-secondary" type="button">+ เพิ่ม record</button>
    </div>

    <div id="file-view" hidden>
      <p class="file-note">แก้ไขไฟล์ config.ini ตรง ๆ ระวังรูปแบบให้ถูกต้อง (ระบบตรวจ syntax และค่าพื้นฐานก่อนบันทึก) — ตัวอย่างดูได้จาก config.example.ini</p>
      <textarea id="file-editor" spellcheck="false" aria-label="config.ini"></textarea>
      <p style="margin-top:10px"><button id="saveFileBtn" class="btn-primary" type="button">บันทึกไฟล์</button></p>
    </div>
  </section>
</main>

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
      box.innerHTML = '<p style="color:var(--muted)">ยังไม่มีข้อมูล IP (รอรอบแรกของ service)</p>';
    } else {
      box.innerHTML = entries.map(([key, ip]) => {
        const err = s.record_errors && s.record_errors[key];
        const kind = err ? "err" : (ip ? "ok" : "idle");
        return '<div class="record-row ' + kind + '">' +
          '<span class="rec-dot"></span>' +
          '<span class="rec-name mono">' + escapeHtml(key) + "</span>" +
          '<span class="rec-ip mono clickable" title="กดเพื่อคัดลอก" onclick="copyIp(this)">' + (ip || "ยังไม่ตั้งค่า") + "</span>" +
          '<span class="rec-meta">' + (err ? escapeHtml(err) : "อัปเดตล่าสุด") + "</span></div>";
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

async function loadConfig() {
  try {
    const r = await fetch("/config.json");
    const c = await r.json();
    $("api_token").value = c.cloudflare.api_token;
    $("interval").value = c.cloudflare.interval_seconds;
    $("use_ipv4").checked = !!c.cloudflare.use_ipv4;
    $("use_ipv6").checked = !!c.cloudflare.use_ipv6;
    $("tg_token").value = c.telegram.bot_token;
    $("tg_chat").value = c.telegram.chat_id;
    $("notify_start").checked = !!c.telegram.notify_start;
    $("notify_stop").checked = !!c.telegram.notify_stop;
    $("notify_ip_change").checked = !!c.telegram.notify_ip_change;
    $("notify_error").checked = !!c.telegram.notify_error;
    $("notify_created").checked = !!c.telegram.notify_created;
    recordsData = c.records.map(r => ({ ...r }));
    renderRecordsEditor();
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
      <input type="text" data-i="${i}" data-k="name" value="${escapeHtml(r.name)}" placeholder="home.example.com">
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
      else if (k === "ttl") recordsData[i][k] = Math.max(60, Math.floor(+inp.value || 120));
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

async function saveConfig() {
  const btn = $("saveBtn");
  btn.disabled = true;
  const payload = {
    cloudflare: {
      api_token: $("api_token").value.trim(),
      interval_seconds: Math.max(15, Math.floor(+$("interval").value || 60)),
      use_ipv4: $("use_ipv4").checked,
      use_ipv6: $("use_ipv6").checked,
      webui_password: "",
    },
    telegram: {
      bot_token: $("tg_token").value.trim(),
      chat_id: $("tg_chat").value.trim(),
      notify_start: $("notify_start").checked,
      notify_stop: $("notify_stop").checked,
      notify_ip_change: $("notify_ip_change").checked,
      notify_error: $("notify_error").checked,
      notify_created: $("notify_created").checked,
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
      loadConfig();
      loadStatus();
    }
  } catch (e) {
    toast("บันทึกไม่ได้: " + e, "err");
  }
  btn.disabled = false;
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
      wzData.records = [{ name: "", proxied: false, ttl: 120 }];
    }
    const zoneOptions = wzZones.length
      ? '<select id="wz-zone" class="wz-zone-select">' + wzZones.map(z => '<option value="' + escapeHtml(z) + '">' + escapeHtml(z) + "</option>").join("") + "</select>"
      : '<input id="wz-zone" type="text" class="wz-zone-select" placeholder="example.com">';
    body.innerHTML =
      '<p class="wz-step-title">ขั้นตอนที่ 2: เลือกโดเมน (zone) และ record</p>' +
      '<p class="wz-step-sub">เลือกโดเมน แล้วระบุชื่อ record ที่ต้องการให้อัปเดต IP ให้ (เช่น home.example.com หรือ @ สำหรับหน้าหลัก)</p>' +
      '<label class="field">Zone (โดเมน)' + zoneOptions + "</label>" +
      '<h3 style="margin-top:16px">Record ที่จะอัปเดต</h3><div id="wz-records"></div>' +
      '<button class="btn-secondary" type="button" id="wz-add-record">+ เพิ่ม record</button>' +
      actions(true, "ต่อไป →");
    $("wz-back").addEventListener("click", () => { wzStep = 2; renderWizard(); });
    $("wz-add-record").addEventListener("click", () => {
      wzData.records.push({ name: "", proxied: false, ttl: 120 });
      renderWzRecords();
    });
    renderWzRecords();
    $("wz-next").addEventListener("click", () => {
      const zoneSel = $("wz-zone");
      wzData.zone = (zoneSel.value || "").trim();
      const recs = wzData.records.map((r, i) => ({
        name: r.name,
        zone: wzData.zone,
        proxied: r.proxied,
        ttl: r.ttl,
        ipv4: true,
        ipv6: true,
      }));
      if (!wzData.zone) { toast("กรุณาเลือก zone ก่อน", "err"); return; }
      if (!recs.length || !recs[0].name) { toast("กรุณากรอกชื่อ record อย่างน้อย 1 ตัว", "err"); return; }
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
    '<input type="text" data-i="' + i + '" data-k="name" value="' + escapeHtml(r.name) + '" placeholder="home.example.com หรือ @">' +
    '<div class="mini" title="ผ่าน orange cloud ของ Cloudflare"><label><input type="checkbox" data-i="' + i + '" data-k="proxied" ' + (r.proxied ? "checked" : "") + "> proxy</label></div>" +
    '<input type="number" data-i="' + i + '" data-k="ttl" value="' + r.ttl + '" min="60" title="TTL (วินาที)">' +
    '<button class="btn-del" type="button" data-del="' + i + '" title="ลบ record">×</button></div>').join("");

  box.querySelectorAll("input[data-k]").forEach(inp => {
    inp.addEventListener("change", () => {
      const i = +inp.dataset.i;
      const k = inp.dataset.k;
      if (inp.type === "checkbox") wzData.records[i][k] = inp.checked;
      else if (k === "ttl") wzData.records[i][k] = Math.max(60, Math.floor(+inp.value || 120));
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
$("wz-skip").addEventListener("click", closeWizard);

$("refresh").addEventListener("click", loadStatus);
$("saveBtn").addEventListener("click", saveConfig);
$("addRecord").addEventListener("click", () => {
  recordsData.push({ name: "", zone: "", proxied: false, ttl: 120, ipv4: true, ipv6: true });
  renderRecordsEditor();
});
$("tgTest").addEventListener("click", tgTest);

loadStatus();
loadConfig();
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
        },
        "telegram": {
            "bot_token": cfg.telegram_bot_token,
            "chat_id": cfg.telegram_chat_id,
            "notify_start": cfg.notify_start,
            "notify_stop": cfg.notify_stop,
            "notify_ip_change": cfg.notify_ip_change,
            "notify_error": cfg.notify_error,
            "notify_created": cfg.notify_created,
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
    kv("telegram_bot_token", str(tg.get("bot_token", "")).strip())
    kv("telegram_chat_id", str(tg.get("chat_id", "")).strip())
    kv("notify_start", str(bool(tg.get("notify_start", True))).lower())
    kv("notify_stop", str(bool(tg.get("notify_stop", True))).lower())
    kv("notify_ip_change", str(bool(tg.get("notify_ip_change", True))).lower())
    kv("notify_error", str(bool(tg.get("notify_error", True))).lower())
    kv("notify_created", str(bool(tg.get("notify_created", True))).lower())
    lines.append("")
    for rec in data.get("records", []):
        name = str(rec.get("name", "")).strip().rstrip(".")
        if not name:
            continue
        lines.append(f"[record:{name}]")
        kv("zone", str(rec.get("zone", "")).strip().rstrip("."))
        kv("proxied", str(bool(rec.get("proxied", False))).lower())
        kv("ttl", max(int(rec.get("ttl", 120)), 60))
        kv("ipv4", str(bool(rec.get("ipv4", True))).lower())
        kv("ipv6", str(bool(rec.get("ipv6", True))).lower())
        lines.append("")
    return "\n".join(lines)


class WebUIHandler(BaseHTTPRequestHandler):
    server_version = "CloudflareDDNSWebUI/2.0"

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
        if self.path == "/status.json":
            if not self._authed():
                return self._send_json(401, {"ok": False, "message": "unauthorized"})
            engine = ddns.DDNSEngine(self.server.config_path)
            status = engine.status()
            cfg_errors = self.cfg.validate()
            status["config_ok"] = not cfg_errors
            status["config_errors"] = cfg_errors
            notify = notifier.TelegramNotifier.from_config(self.cfg)
            status["telegram"] = {
                "enabled": notify.enabled,
                "chat_id": notify.chat_id,
                "queue": notifier.queue_size(),
            }
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
            return self._send(200, PAGE.replace("__LOGIN__", self._login_block()))
        return self._send(200, PAGE.replace("__LOGIN__", ""))

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
