const $ = (id) => document.getElementById(id);

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
        throw new Error("timeout — server ไม่ตอบกลับภายใน " + (FETCH_TIMEOUT_MS / 1000) + " วิ (ลองใหม่ หรือดู log)");
      }
      throw new Error("เชื่อมต่อ server ไม่ได้ (network error) — ลองใหม่ หรือดู log");
    });
};

/* ---------- log error ฝั่งหน้าเว็บ ไปไฟล์ log (ฝั่ง server) ---------- */

function logClientError(context, err) {
  try {
    const message = String(err && err.message ? err.message : err).slice(0, 500);
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
    btn.title = "แสดง/ซ่อนรหัส";
    btn.setAttribute("aria-label", "แสดง/ซ่อนรหัส");
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
      pill.textContent = "ตั้งค่าไม่ครบ";
      pill.className = "pill warn";
    } else if (s.errors_active) {
      pill.textContent = "มีปัญหา";
      pill.className = "pill err";
    } else {
      pill.textContent = "พร้อมใช้งาน";
      pill.className = "pill ok";
    }
    const cfgErr = $("cfg-err");
    if (s.config_errors && s.config_errors.length) {
      cfgErr.hidden = false;
      cfgErr.textContent = "⚠ " + s.config_errors.join(" · ");
    } else {
      cfgErr.hidden = true;
    }
    const last = s.last_run ? new Date(s.last_run).toLocaleString("th-TH") : "ยังไม่เคยรัน";
    $("lastrun").textContent = last;
    $("verpill").textContent = "v" + (s.version || "?");

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
        const [name, type] = key.split("|");
        const t = (s.records_time || {})[key];
        const timeText = t ? new Date(t).toLocaleString("th-TH") : "—";
        const meta = escapeHtml(type || "") + (type ? " · " : "") + (err ? escapeHtml(err) : "อัปเดตล่าสุด " + timeText);
        return '<div class="record-row ' + kind + '">' +
          '<span class="rec-dot"></span>' +
          '<span class="rec-name mono clickable" title="กดเพื่อคัดลอกชื่อ" onclick="copyIp(this)">' + escapeHtml(name) + "</span>" +
          '<span class="rec-ip mono clickable" title="กดเพื่อคัดลอก IP" onclick="copyIp(this)">' + escapeHtml(ip || "ยังไม่ตั้งค่า") + "</span>" +
          '<span class="rec-meta">' + meta + "</span></div>";
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

    const api = s.api_stats || {};
    $("api-stats").textContent = "Cloudflare API: เรียก " + (api.calls || 0) + " ครั้ง · error " + (api.errors || 0) + " · โดน rate limit " + (api.rate_limited || 0) + " (นับตั้งแต่เริ่ม)";

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
          return '<tr class="' + cls + '"><td style="padding:5px 10px;color:var(--muted);white-space:nowrap">' + t + '</td><td class="mono" style="padding:5px 10px;word-break:break-all">' + escapeHtml(h.record) + " (" + escapeHtml(h.type || "") + ')</td><td style="padding:5px 10px;white-space:nowrap">' + escapeHtml(act) + '</td><td class="mono" style="padding:5px 10px;white-space:nowrap">' + escapeHtml(h.ip || "-") + "</td></tr>";
        }).join("") + "</table></div>";
    }
  } catch (e) {
    logClientError("loadStatus", e);
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

/* ---------- Windows Service ---------- */

async function loadServiceStatus() {
  try {
    const r = await fetch("/status.json");
    const s = await r.json();
    const svc = s.service || {};
    const rt = s.runtime || {};
    const ctx = $("svc-ctx");
    if (rt.in_service) ctx.textContent = "รันใน service (มีสิทธิ์ระบบ) — ติดตั้ง/ถอน/หยุดต้องใช้ .bat ภายนอก";
    else if (rt.admin) ctx.textContent = "รันแบบ standalone · มีสิทธิ์ admin — ควบคุม service ได้";
    else ctx.textContent = "รันแบบ standalone · ไม่มีสิทธิ์ admin — ปุ่มควบคุม service ใช้ไม่ได้ (เปิด exe/cmd เป็น admin)";
    const canControl = rt.admin;
    ["svcInstall", "svcUninstall", "svcStart", "svcStop", "svcRestart"].forEach(id => {
      const b = $(id);
      b.disabled = !canControl;
      b.title = canControl ? "" : "ต้องเปิด webui ด้วยสิทธิ์ admin";
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
      box.innerHTML = '<span style="color:var(--muted)">ยังไม่ได้ติดตั้ง service — กด "ติดตั้ง service" (ต้อง admin)</span>';
      return;
    }
    const stateNames = { running: "กำลังทำงาน", stopped: "หยุดอยู่", starting: "กำลังเริ่ม", stopping: "กำลังหยุด", resuming: "กำลังเริ่มต่อ", pausing: "กำลังพัก", paused: "พักอยู่" };
    const label = escapeHtml(stateNames[svc.state] || svc.state);
    box.innerHTML = svc.running
      ? '<span class="ok">ติดตั้งแล้ว — ' + label + '</span>'
      : '<span class="err">ติดตั้งแล้ว — ' + label + "</span>";
  } catch (e) {
    logClientError("loadServiceStatus", e);
    $("svc-status").textContent = "อ่านสถานะไม่ได้: " + e;
  }
}

async function svcAction(path, confirmText) {
  if (!confirm(confirmText)) return;
  try {
    const r = await fetch(path, { method: "POST" });
    const j = await r.json();
    toast(j.ok ? j.message : "ไม่สำเร็จ: " + j.message, j.ok ? "ok" : "err");
    if (j.ok) {
      loadServiceStatus();
      if (path === "/service/restart") {
        setTimeout(() => location.reload(), 16000);
      }
    }
  } catch (e) {
    toast("error: " + e, "err");
  }
}

async function ddnsRunNow() {
  const btn = $("ddnsRun");
  btn.disabled = true;
  try {
    const r = await fetch("/ddns-run", { method: "POST" });
    const j = await r.json();
    toast(j.ok ? j.message : "ไม่สำเร็จ: " + j.message, j.ok ? "ok" : "err");
    if (j.ok) {
      setTimeout(() => { loadStatus(); loadServiceStatus(); btn.disabled = false; }, 5000);
      setTimeout(loadStatus, 15000);
      return;
    }
  } catch (e) {
    toast("error: " + e, "err");
  }
  btn.disabled = false;
}

async function checkUpdate() {
  try {
    const r = await fetch("/update-check");
    const j = await r.json();
    if (!j.ok || !j.has_update) return;
    const pill = $("update-pill");
    pill.textContent = "มี v" + j.latest + " ใหม่";
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
        toast(j.message + " — คัดลอก path ลงคลิปบอร์ดแล้ว (Win+R → วาง → Enter)", "ok");
      } catch (e) {
        toast(j.message, "ok");
      }
    } else {
      toast(j.ok ? j.message : "ไม่สำเร็จ: " + j.message, j.ok ? "ok" : "err");
    }
  } catch (e) {
    logClientError("openDataFolder", e);
    toast("error: " + e, "err");
  }
}

/* ---------- ตั้งค่า ---------- */

let recordsData = [];
let tunnelHostsData = [];
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
    $("reject_cf_ips").checked = c.cloudflare.reject_cloudflare_ips !== false;
    $("hc_url").value = c.cloudflare.healthchecks_url || "";
    $("kuma_url").value = c.cloudflare.uptimekuma_url || "";
    $("webui_password").value = c.cloudflare.webui_password;
    currentWebuiPassword = c.cloudflare.webui_password;
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
    $("tunnel_enabled").checked = !!c.tunnel.enabled;
    $("tunnel_token").value = c.tunnel.token;
    $("cloudflared_path").value = c.tunnel.cloudflared_path || "";
    tunnelHostsData = c.tunnel.hosts || [];
    recordsData = c.records.map(r => ({ ...r }));
    renderRecordsEditor();
    loadScanHosts();
  } catch (e) {
    logClientError("loadConfig", e);
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
      <input type="text" data-i="${i}" data-k="name" value="${escapeHtml(r.name)}" placeholder="home (เติม .zone ให้) / @ / *.zone (wildcard)">
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
      reject_cloudflare_ips: $("reject_cf_ips").checked,
      healthchecks_url: $("hc_url").value.trim(),
      uptimekuma_url: $("kuma_url").value.trim(),
      webui_port: Math.max(1, Math.min(65535, Math.floor(+$("webui_port").value || currentWebuiPort))),
      webui_host: $("webui_host").value.trim() || "127.0.0.1",
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
      notify_round: $("notify_round").checked,
      daily_report: $("daily_report").checked,
      daily_report_time: $("daily_report_time").value.trim() || "08:00",
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
    toast(j.ok ? "บันทึกสำเร็จ — มีผลในรอบถัดไป" : "บันทึกไม่สำเร็จ: " + j.message, j.ok ? "ok" : "err");
    if (j.ok) {
      const pwChanged = $("webui_password").value.trim() !== currentWebuiPassword;
      const portChanged = payload.cloudflare.webui_port !== currentWebuiPort;
      if (pwChanged) {
        // cookie เก่าใช้ไม่ได้แล้ว — อย่าโหลด config ตอนนี้ (จะ error 401) — login ใหม่แล้ว reload
        toast(payload.cloudflare.webui_password ? "ตั้งรหัสผ่านหน้าเว็บแล้ว — กำลังเข้าสู่ระบบใหม่" : "ลบรหัสผ่านหน้าเว็บแล้ว", "ok");
        setTimeout(async () => {
          if (payload.cloudflare.webui_password) {
            try {
              await fetch("/login", { method: "POST", body: new URLSearchParams({ pw: payload.cloudflare.webui_password }) });
            } catch (e) { logClientError("auto-login หลังเปลี่ยนรหัส", e); }
          }
          location.reload();
        }, 1200);
      } else {
        loadConfig();
        loadStatus();
        if (portChanged) {
          toast("เปลี่ยนพอร์ตหน้าเว็บแล้ว — ต้อง restart service (dist\\cloudflare-ddns.exe restart) เพื่อให้มีผล", "ok");
        }
      }
    }
  } catch (e) {
    logClientError("saveConfig", e);
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
      const warn = j.nat.nat_type === "double-nat";
      const cls = bad ? "var(--danger)" : (warn ? "var(--warn)" : "var(--ok)");
      const icon = bad ? "⚠" : (warn ? "⚠" : "✓");
      nat.innerHTML = '<span style="color:' + cls + '">' + icon + " " + escapeHtml(j.nat.message) + "</span>";
    }
  } catch (e) {
    logClientError("loadIp", e);
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
      row.name = shortenName(sel.value, zone);
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
      const icon = { open: "🟢", filtered: "⚪", closed: "🔴" }[p.status] || "•";
      const label = { open: "เปิด", filtered: "ไม่มีตอบ (ไฟร์วอลล์?)", closed: "ปิด" }[p.status];
      return '<tr class="' + cls + '"><td class="mono">' + p.port + '</td><td class="mono">' + escapeHtml(p.service || "-") + '</td><td style="white-space:nowrap">' + icon + " " + label + "</td></tr>";
    }).join("");
    box.innerHTML =
      '<div style="border:1px solid var(--border);border-radius:8px;overflow-x:auto"><table style="font-size:0.9rem;width:100%;min-width:420px">' +
      '<tr style="background:var(--surface-2)"><th style="padding:6px 10px;text-align:left">พอร์ต</th><th style="padding:6px 10px;text-align:left">บริการ</th><th style="padding:6px 10px;text-align:left">สถานะ</th></tr>' +
      rows + "</table></div>" +
      '<p style="margin-top:8px;font-size:0.85rem;color:var(--ink-2)">' + escapeHtml(j.host) + " → " + escapeHtml(j.ip) +
      " · เปิด " + open.length + " · ปิด " + (j.ports.length - open.length - filtered.length) + " · ไม่มีตอบ " + filtered.length + "</p>";
  } catch (e) {
    logClientError('scanPorts', e);
    box.innerHTML = '<p style="color:var(--danger)">error: ' + escapeHtml(e) + "</p>";
  }
  btn.disabled = false;
}

async function loadLog() {
  const box = $("logview");
  try {
    const r = await fetch("/log?t=" + Date.now());
    if (!r.ok) {
      if (r.status === 401 || r.status === 403) {
        box.textContent = "session หมดอายุ — กดรีเฟรชหน้าเว็บ (F5/Ctrl+R) เพื่อเข้าสู่ระบบใหม่ แล้วลองอีกครั้ง";
      } else {
        box.textContent = "อ่าน log ไม่ได้ (HTTP " + r.status + ") — รีเฟรชหน้าเว็บแล้วลองใหม่";
      }
      return;
    }
    box.textContent = await r.text();
    box.scrollTop = box.scrollHeight;
  } catch (e) {
    logClientError('loadLog', e);
    box.textContent = "อ่าน log ไม่ได้: " + e;
  }
}

async function clearLog() {
  if (!confirm("ล้างไฟล์ log ทั้งหมด?")) return;
  try {
    const r = await fetch("/log-clear", { method: "POST" });
    const j = await r.json();
    toast(j.ok ? j.message : "ล้างไม่สำเร็จ: " + j.message, j.ok ? "ok" : "err");
    if (j.ok) loadLog();
  } catch (e) {
    logClientError("clearLog", e);
    toast("error: " + e, "err");
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
    if (t.running) parts.push('<span class="ok">รันอยู่ (pid ' + escapeHtml(String(t.pid)) + ")</span>");
    else if (t.enabled) parts.push('<span>ยังไม่รัน</span>');
    if (t.installed && t.version) parts.push('<span style="color:var(--muted)">cloudflared ' + escapeHtml(t.version) + "</span>");
    box.innerHTML = parts.join(" · ");
  } catch (e) {
    logClientError('loadTunnelStatus', e);
    $("tunnel-status").textContent = "อ่านสถานะไม่ได้: " + e;
  }
}

async function tunnelHosts() {
  const box = $("tunnel-hosts");
  if (!box.hidden) { box.hidden = true; return; }
  box.hidden = false;
  box.innerHTML = '<p style="color:var(--muted)">กำลังโหลด…</p>';
  const token = $("tunnel_token").value.trim();
  if (!token) { box.innerHTML = '<p style="color:var(--muted)">ยังไม่ได้ตั้งค่า tunnel token (ใช้ wizard ตั้งค่า)</p>'; return; }
  try {
    const r = await fetch("/tunnel/hostnames", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    });
    const j = await r.json();
    if (!j.ok) { box.innerHTML = '<p style="color:var(--danger)">' + escapeHtml(j.message) + "</p>"; return; }
    if (!j.hostnames.length) {
      box.innerHTML = '<p style="color:var(--muted)">ยังไม่มี hostname ผูกกับ tunnel — ใช้ "ตั้งค่า Tunnel (wizard)" หรือ "+ เพิ่ม hostname"</p>';
      return;
    }
    box.innerHTML = '<div style="border:1px solid var(--border);border-radius:8px;overflow-x:auto"><table style="font-size:0.85rem;width:100%;min-width:480px">' +
      '<tr style="background:var(--surface-2)"><th style="padding:5px 10px;text-align:left">hostname</th><th style="padding:5px 10px;text-align:left">ชนิด</th><th style="padding:5px 10px;text-align:left">บริการ</th><th style="padding:5px 10px"></th></tr>' +
      j.hostnames.map(h =>
        '<tr><td class="mono" style="padding:5px 10px">' + escapeHtml(h.hostname) + escapeHtml(h.path || "") + '</td>' +
        '<td style="padding:5px 10px">' + escapeHtml(h.protocol || "http") + "</td>" +
        '<td class="mono" style="padding:5px 10px;color:var(--muted)">' + escapeHtml(h.service) + "</td>" +
        '<td style="padding:2px 6px;white-space:nowrap">' +
        '<button class="btn-secondary" style="padding:3px 8px;font-size:0.75rem" type="button" data-edit-host="' + escapeHtml(h.hostname) + '" data-edit-path="' + escapeHtml(h.path || "") + '" data-edit-protocol="' + escapeHtml(h.protocol || "http") + '" data-edit-service="' + escapeHtml(h.service || "") + '" title="แก้ไข map นี้ (ผูกซ้ำ = แทนที่)">แก้ไข</button> ' +
        '<button class="btn-del" type="button" data-host="' + escapeHtml(h.hostname) + '" data-path="' + escapeHtml(h.path || "") + '" title="เลิกผูก">×</button></td></tr>'
      ).join("") + "</table></div>" +
      '<p style="margin-top:6px;font-size:0.8rem;color:var(--muted)">หลาย port ต่อชื่อเดียว: ผูก path ต่างกัน (เช่น /api → 3000, / → 8080) · TCP/UDP เลือกชนิดได้ · "แก้ไข" = ผูกซ้ำด้วยค่าที่ตั้งใหม่ (แทนที่ของเดิม)</p>';
    box.querySelectorAll("button[data-host]").forEach(b => b.addEventListener("click", async () => {
      if (!confirm("เลิกผูก " + b.dataset.host + b.dataset.path + "?")) return;
      try {
        const rr = await fetch("/tunnel/unbind", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token, hostname: b.dataset.host, path: b.dataset.path }),
        });
        const jj = await rr.json();
        toast(jj.ok ? jj.message : "ไม่สำเร็จ: " + jj.message, jj.ok ? "ok" : "err");
        tunnelHosts();
      } catch (e) {
        toast("error: " + e, "err");
      }
    }));
    box.querySelectorAll("button[data-edit-host]").forEach(b => b.addEventListener("click", () => editTunnelHost(b)));
  } catch (e) {
    logClientError('tunnelHosts', e);
    box.innerHTML = '<p style="color:var(--danger)">error: ' + escapeHtml(e) + "</p>";
  }
}

// โหลด dropdown โดเมน (ครั้งแรกเท่านั้น) — ใช้ร่วมกับฟอร์มเพิ่ม/แก้ไข hostname
async function ensureTunnelDomainLoaded() {
  const domainSel = $("th-domain");
  if (domainSel.options.length) return;
  domainSel.innerHTML = '<option value="">— กำลังโหลดโดเมน… —</option>';
  try {
    const r = await fetch("/tunnel/zones", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}) });
    const j = await r.json();
    if (j.ok && j.zones.length) {
      domainSel.innerHTML = j.zones.map(z => '<option value="' + escapeHtml(z) + '">' + escapeHtml(z) + "</option>").join("");
      await fillSubList("th-sub", "th-domain", "th-sub-list");
    } else {
      domainSel.innerHTML = '<option value="">— ใส่โดเมนไม่ได้ (API token ไม่มีสิทธิ์) —</option>';
    }
  } catch (e) {
    logClientError('ensureTunnelDomainLoaded', e);
    domainSel.innerHTML = '<option value="">— โหลดโดเมนไม่ได้ —</option>';
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
  msg.innerHTML = '<p style="color:var(--ok)">แก้ไข ' + escapeHtml(hostname) + (path || "") + ' — เปลี่ยนค่าด้านบนแล้วกด "ผูกกับ tunnel" (แทนที่ของเดิม)</p>';
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
  if (!token) { msg.innerHTML = '<p style="color:var(--danger)">ยังไม่ได้ตั้งค่า tunnel token (ใช้ wizard ก่อน)</p>'; return; }
  const sub = $("th-sub").value.trim().replace(/^\.+|\.+$/g, "");
  const domain = $("th-domain").value.trim();
  if (!sub || !domain) { msg.innerHTML = '<p style="color:var(--danger)">กรุณาใส่ชื่อและโดเมน</p>'; return; }
  const hostname = sub === "@" ? domain : sub + "." + domain;
  msg.innerHTML = '<p style="color:var(--ok)">กำลังผูก...</p>';
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
  if (!token) { toast("ยังไม่ได้ตั้งค่า tunnel token (ใช้ wizard ก่อน)", "err"); return; }
  try {
    const r = await fetch("/tunnel/sync", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    });
    const j = await r.json();
    toast(j.ok ? j.message : "ไม่สำเร็จ: " + j.message, j.ok ? "ok" : "err");
    if (j.ok) loadConfig();
  } catch (e) {
    toast("error: " + e, "err");
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
    box.innerHTML = '<div style="border:1px solid var(--border);border-radius:8px;overflow-x:auto"><table style="font-size:0.85rem;width:100%;min-width:480px">' +
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
      '<label class="field">Tunnel Token (แสดงข้อความเต็ม ไม่ซ่อน)<textarea id="twz-token" rows="3" class="mono" spellcheck="false" autocomplete="off" placeholder="eyJhIjoi... (ยาว)"></textarea></label>' +
      '<div id="twz-msg"></div>' +
      '<div class="wz-help" id="twz-token-steps" hidden><b>วิธีหา token (ทีละขั้น):</b><ol>' +
      "<li>กดปุ่ม “เปิด Zero Trust” แล้วล็อกอิน</li>" +
      "<li>เมนูซ้าย: Networks → Tunnels → Create a tunnel</li>" +
      "<li>ตั้งชื่อ (เช่น home) → เลือกวิธี Cloudflare-managed → ต่อไป</li>" +
      "<li>กดคัดลอก token จากคำสั่ง install (ส่วน --token eyJ...) — ไม่ต้องรันคำสั่งนั้นจริง</li>" +
      "<li>วาง token ในช่องด้านบน แล้วกด ตรวจสอบ token</li></ol></div>" +
      actions(true, "ตรวจสอบ token →");
    $("twz-back").addEventListener("click", () => { twzStep = 1; renderTunnelWizard(); });
    $("twz-open-zt").addEventListener("click", () => window.open("https://one.dash.cloudflare.com/?to=/:account/networks/tunnels", "_blank"));
    $("twz-help").addEventListener("click", () => {
      const h = $("twz-token-steps");
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
    logClientError('renderTunnelWizard', e);
        $("twz-msg").innerHTML = wzMsg("err", "error: " + e);
        btn.disabled = false;
      }
    });
  }

  else if (twzStep === 3) {
    body.innerHTML =
      '<p class="wz-step-title">ขั้นตอนที่ 2: ผูกเว็บ (hostname) กับ tunnel</p>' +
      '<p class="wz-step-sub">ระบุชื่อเว็บและบริการในเครื่อง — โปรแกรมตั้งค่าให้อัตโนมัติ (สร้าง DNS + ตั้ง tunnel config) ไม่ต้องไปทำที่ dashboard</p>' +
      '<div class="grid2">' +
      '<label class="field">ชื่อ (subdomain)<input id="twz-sub" type="text" placeholder="app (ใหม่ก็ได้ เช่น nas)" class="mono" list="twz-sub-list"><datalist id="twz-sub-list"></datalist><span style="font-size:0.78rem;color:var(--muted)">ชื่อใหม่ที่ไม่เคยมีก็ได้ — สร้าง DNS ให้อัตโนมัติ</span></label>' +
      '<label class="field">โดเมน<select id="twz-domain" class="wz-zone-select"></select></label></div>' +
      '<label class="field">Path (ไม่บังคับ — ใช้หลาย port ต่อชื่อเดียว เช่น /api)<input id="twz-path" type="text" class="mono" placeholder="/api (เว้น = ทุก path)"></label>' +
      '<div class="grid2">' +
      '<label class="field">ชนิด<select id="twz-protocol" class="wz-zone-select">' +
      '<option value="http">HTTP</option><option value="https">HTTPS</option><option value="tcp">TCP (เช่น SSH)</option><option value="udp">UDP (เช่น game/VPN)</option>' +
      "</select></label>" +
      '<label class="field">บริการ/พอร์ต<input id="twz-service" type="text" class="mono" value="http://localhost:8080"></label></div>' +
      '<p style="margin:2px 0 10px;font-size:0.8rem;color:var(--muted);line-height:1.5">💡 เลือกชนิดให้ตรงกับบริการ: <b>HTTP</b> = เว็บธรรมดา (เช่น <span class="mono">http://localhost:8080</span>) · <b>HTTPS</b> = พอร์ต SSL เช่น 443/8443 (ต้องเป็น <span class="mono">https://localhost:443</span> — ถ้าผูกเป็น http จะเจอ "Bad Request") · <b>TCP/UDP</b> = SSH/game/VPN (เช่น <span class="mono">tcp://localhost:22</span>)</p>' +
      '<div style="margin:8px 0">' +
      '<button class="btn-secondary" type="button" id="twz-load-records">เลือกจาก record ที่มีอยู่</button> ' +
      '<select id="twz-record-pick" class="wz-zone-select" style="margin-top:6px" hidden></select></div>' +
      '<h3 style="margin-top:14px">ผูกกับ tunnel แล้ว</h3><div id="twz-bound"><p style="color:var(--muted)">กำลังโหลด…</p></div>' +
      '<div id="twz-bind-msg"></div>' +
      '<div style="margin-top:10px"><button class="btn-primary" type="button" id="twz-bind">ผูกกับ tunnel</button></div>' +
      '<div class="wz-help">ตัวอย่าง: ชื่อ <b>app</b> + โดเมน <b>makerwitawat.com</b> + บริการ <b>http://localhost:8080</b> → เข้าได้ที่ <b>https://app.makerwitawat.com</b> — <b>ชื่อ subdomain ใหม่ที่ไม่เคยมีก็กรอกได้เลย</b> โปรแกรมสร้าง DNS record ให้อัตโนมัติ (ผูกแล้วแก้ภายหลังได้ในฟอร์ม/แดชบอร์ด)</div>' +
      actions(true, "ต่อไป →");
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
          sel.innerHTML = '<option value="">— ใส่เองไม่ได้ (API token ไม่มีสิทธิ์) —</option>';
        }
      } catch (e) {
    logClientError('renderTunnelWizard', e);
        sel.innerHTML = '<option value="">— โหลดโดเมนไม่ได้ —</option>';
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
      if (!sub || !domain) { msg.innerHTML = wzMsg("err", "กรุณาใส่ชื่อและเลือกโดเมน"); return; }
      const hostname = sub === "@" ? domain : sub + "." + domain;
      const btn = $("twz-bind");
      btn.disabled = true;
      msg.innerHTML = wzMsg("ok", "กำลังผูก " + hostname + (path || "") + " กับ tunnel...");
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
        msg.innerHTML = wzMsg("err", "error: " + e);
      }
      btn.disabled = false;
    });

    // เลือกชื่อจาก record ที่มีอยู่ (รายการ DNS ปัจจุบัน)
    $("twz-load-records").addEventListener("click", async () => {
      const domain = $("twz-domain").value.trim();
      if (!domain) { toast("เลือกโดเมนก่อน", "err"); return; }
      const btn = $("twz-load-records");
      btn.disabled = true;
      try {
        const r = await fetch("/list-records", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ zone: domain }),
        });
        const j = await r.json();
        if (!j.ok) { toast("โหลดไม่ได้: " + j.message, "err"); btn.disabled = false; return; }
        const sel = $("twz-record-pick");
        sel.hidden = false;
        sel.innerHTML = '<option value="">— เลือก record —</option>' +
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
        const oldTun = cfg.tunnel || {};
        cfg.tunnel = { enabled: true, token: twzData.token, cloudflared_path: oldTun.cloudflared_path || "", hosts: oldTun.hosts || [] };
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
    logClientError('renderTunnelWizard', e);
        $("twz-save-msg").innerHTML = wzMsg("err", "error: " + e);
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
      box.innerHTML = '<p style="color:var(--muted)">ยังไม่มี — ผูกจากข้างบนได้เลย</p>';
      return;
    }
    box.innerHTML = j.hostnames.map(h =>
      '<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;padding:6px 10px;background:var(--surface-2);border-radius:8px;margin-bottom:6px;flex-wrap:wrap">' +
      '<span class="mono">' + escapeHtml(h.hostname) + escapeHtml(h.path || "") + '</span>' +
      '<span style="color:var(--muted);font-size:0.8rem">' + escapeHtml((h.protocol || "http") + "://" + (h.service || "").split("://").pop()) + "</span>" +
      '<button class="btn-del" type="button" data-host="' + escapeHtml(h.hostname) + '" data-path="' + escapeHtml(h.path || "") + '" title="เลิกผูก">×</button></div>'
    ).join("");
    box.querySelectorAll("button[data-host]").forEach(b => b.addEventListener("click", async () => {
      if (!confirm("เลิกผูก " + b.dataset.host + b.dataset.path + "?")) return;
      try {
        const rr = await fetch("/tunnel/unbind", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token: twzData.token, hostname: b.dataset.host, path: b.dataset.path }),
        });
        const jj = await rr.json();
        toast(jj.ok ? jj.message : "ไม่สำเร็จ: " + jj.message, jj.ok ? "ok" : "err");
        loadTwzBound();
      } catch (e) {
        toast("error: " + e, "err");
      }
    }));
  } catch (e) {
    logClientError('loadTwzBound', e);
    box.innerHTML = '<p style="color:var(--danger)">error: ' + escapeHtml(e) + "</p>";
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
  return '<div class="' + (kind === "ok" ? "wz-ok-box" : "wz-err-box") + '">' + escapeHtml(text) + "</div>";
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
    logClientError('renderWizard', e);
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
      '<label class="field">Chat ID (กด "ค้นหา" ให้อัตโนมัติ หรือกรอกเองได้ — เลข 9-10 หลัก)<input id="wz-tg-chat" type="text" class="mono" autocomplete="off" placeholder="123456789"></label>' +
      '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px">' +
      '<button class="btn-secondary" type="button" id="wz-tg-find">ค้นหา chat id ให้อัตโนมัติ</button>' +
      '<button class="btn-secondary" type="button" id="wz-tg-test" disabled>ส่งข้อความทดสอบ</button></div>' +
      '<div class="wz-help">วิธี: เปิด Telegram ค้นหา @BotFather → ส่ง /newbot → ตั้งชื่อ → คัดลอก token มาวาง แล้วเปิดแชทกับ bot ใหม่และกด Start จากนั้นกด "ค้นหา chat id ให้อัตโนมัติ" — ถ้าหาไม่ได้ (bot เคยถูกใช้แล้ว) เปิดแชทกับ bot → มองหา ID ตัวเลขใน @userinfobot หรือกดปุ่ม Share ID ของ bot</div>' +
      actions(true, "ข้าม →");
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
      if (!token) { $("wz-tg-msg").innerHTML = wzMsg("err", "วาง bot token ก่อน"); return; }
      $("wz-tg-msg").innerHTML = wzMsg("ok", "กำลังค้นหาบทสนทนาล่าสุด...");
      try {
        const r = await fetch("/resolve-chat-id", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ bot_token: token }),
        });
        const j = await r.json();
        if (!j.ok) { $("wz-tg-msg").innerHTML = wzMsg("err", j.message + " — กรอก chat id เองได้ในช่องด้านบน"); return; }
        setChat(j.chat_id);
        $("wz-tg-msg").innerHTML = wzMsg("ok", "พบ chat id: " + j.chat_id);
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
      wzData.tg = { token: $("wz-tg-token").value.trim(), chat_id: chatId || $("wz-tg-chat").value.trim() };
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
          $("wz-save-msg").innerHTML = wzMsg("err", "บันทึกไม่สำเร็จ: " + j.message);
          btn.disabled = false;
          return;
        }
        toast("ตั้งค่าเสร็จสมบูรณ์ — DDNS เริ่มทำงานแล้ว", "ok");
        closeWizard();
        loadStatus();
        loadConfig();
      } catch (e) {
    logClientError('renderWizard', e);
        $("wz-save-msg").innerHTML = wzMsg("err", "error: " + e);
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
$("tunnelStart").addEventListener("click", () => tunnelAction("/tunnel/start", "เริ่ม tunnel"));
$("tunnelStop").addEventListener("click", () => tunnelAction("/tunnel/stop", "หยุด tunnel"));
$("tunnelDownload").addEventListener("click", () => tunnelAction("/tunnel/download", "ดาวน์โหลด"));
$("tunnelWizard").addEventListener("click", openTunnelWizard);
$("tunnelHostsBtn").addEventListener("click", tunnelHosts);
$("tunnelAddHost").addEventListener("click", tunnelAddHost);
$("tunnelSync").addEventListener("click", tunnelSync);
$("th-bind").addEventListener("click", thBind);
$("th-cancel").addEventListener("click", () => { $("tunnel-add-form").hidden = true; });
$("twz-close").addEventListener("click", () => { $("tunnel-wizard").hidden = true; });
$("svcInstall").addEventListener("click", () => svcAction("/service/install", "ติดตั้ง Windows Service 'CloudflareDDNS'? (เริ่มอัตโนมัติตอน boot)"));
$("svcRestart").addEventListener("click", () => svcAction("/service/restart", "Restart Windows Service? — หน้าเว็บนี้จะหลุดชั่วครู่แล้วกลับมาเอง"));
$("svcStart").addEventListener("click", () => svcAction("/service/start", "เริ่ม Windows Service 'CloudflareDDNS'?"));
$("svcStop").addEventListener("click", () => svcAction("/service/stop", "หยุด Windows Service 'CloudflareDDNS'? (หน้าเว็บนี้จะไม่กลับมาเอง)"));
$("svcUninstall").addEventListener("click", () => {
  if (!confirm("ถอนการติดตั้ง Windows Service 'CloudflareDDNS'?")) return;
  svcAction("/service/uninstall", "ยืนยันอีกครั้ง — ถอน service จริง ๆ? (config/state/ข้อมูลไม่ถูกลบ)");
});
$("ddnsRun").addEventListener("click", ddnsRunNow);
$("openFolder").addEventListener("click", openDataFolder);
$("refresh").addEventListener("click", refreshAll);

/* โหลดทุกส่วนใหม่หมด (ปุ่มรีเฟรช) — เหมือนตอนเปิดหน้าแรก */
function refreshAll() {
  loadStatus();
  loadConfig();
  loadIp();
  loadLog();
  loadTunnelStatus();
  loadServiceStatus();
}

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
