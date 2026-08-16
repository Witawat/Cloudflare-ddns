// เทสต์ release exe จำลองผู้ใช้ใหม่: รัน exe เปล่า ๆ → wizard ครบ 5 ขั้น → ตรวจผล
// ใช้งาน: node test-release.mjs  (ต้องติดตั้ง playwright ในโฟลเดอร์นี้)
import { chromium } from "playwright";
import { readFileSync, writeFileSync } from "fs";

const DATA = JSON.parse(readFileSync(process.env.RELTEST_DATA || "reltest-data.json", "utf-8"));
const URL = process.env.RELTEST_URL || "http://127.0.0.1:8123/";
const OUT = process.env.RELTEST_OUT || "reltest-report.txt";

const lines = [];
const log = (s) => { lines.push(s); console.log(s); };

let pass = 0, fail = 0;
const check = (name, ok, extra = "") => {
  if (ok) { pass++; log(`  [PASS] ${name}`); }
  else { fail++; log(`  [FAIL] ${name} ${extra}`); }
};

const browser = await chromium.launch();
const page = await browser.newPage();
const errors = [];
page.on("console", m => {
  if (m.type() === "error") {
    let loc = "";
    try { loc = m.location().url || ""; } catch { }
    errors.push((loc ? loc + " " : "") + m.text().slice(0, 150));
  }
});
page.on("pageerror", e => errors.push("pageerror: " + String(e).slice(0, 150)));

try {
  // ---------- 1) เปิดหน้า — wizard ควรโผล่อัตโนมัติ ----------
  log("== 1) เปิด webui ครั้งแรก (ผู้ใช้ใหม่) ==");
  await page.goto(URL, { waitUntil: "networkidle", timeout: 30000 });
  await page.waitForTimeout(1200);
  const wizardVisible = await page.locator("#wizard").isVisible().catch(() => false);
  check("wizard เปิดอัตโนมัติเมื่อยังไม่ตั้งค่า", wizardVisible);

  // ---------- 2) ขั้น 1: ต้อนรับ → เริ่มตั้งค่า ----------
  log("== 2) ขั้นที่ 1: ยินดีต้อนรับ ==");
  const wTitle = await page.locator("#wz-title").textContent().catch(() => "");
  check("หน้า wizard แสดงหัวข้อ", String(wTitle).includes("ตั้งค่า"));
  await page.locator("#wz-next").click();

  // ---------- 3) ขั้น 2: ใส่ API token → ตรวจสอบ ----------
  log("== 3) ขั้นที่ 2: ใส่ API token ==");
  const tokenField = await page.locator("#wz-token").isVisible().catch(() => false);
  check("ช่อง token ปรากฏ", tokenField);
  await page.locator("#wz-token").fill(DATA.api_token);
  await page.locator("#wz-next").click();
  await page.waitForTimeout(3500); // รอ /verify-token + ข้ามขั้น
  const step3 = await page.locator("#wz-zone").isVisible().catch(() => false);
  check("token ตรวจผ่าน → ไปขั้นเลือก zone", step3, "(token ผิด? ดู wz-token-msg)");

  // ---------- 4) ขั้น 3: เลือก zone + record ----------
  log("== 4) ขั้นที่ 3: เลือก zone + record ==");
  if (step3) {
    const zoneSel = page.locator("#wz-zone");
    const zoneCount = await zoneSel.locator("option").count().catch(() => 0);
    check("dropdown zone มีรายการจาก Cloudflare", zoneCount > 0, `(${zoneCount} zone)`);
    await zoneSel.selectOption({ label: DATA.zone }).catch(() => zoneSel.fill(DATA.zone));
    // record: ใช้ชื่อทดสอบ (release-test) — ใส่ในช่องแรก
    const nameInput = page.locator("#wz-records input:first-of-type, #wz-records .rec-edit input[type=text]").first();
    await nameInput.fill(DATA.record);
    // ทดสอบปุ่ม "+ เพิ่ม record" แล้วลบ? — กดเพิ่ม 1 ตัวเพื่อทดสอบปุ่ม แล้วลบแถวหลัง
    const addBtn = page.locator("#wz-add-record");
    if (await addBtn.isVisible().catch(() => false)) {
      await addBtn.click();
      await page.waitForTimeout(400);
      const rowCount = await page.locator("#wz-records .rec-edit").count();
      check("ปุ่ม + เพิ่ม record เพิ่มแถวได้", rowCount >= 2, `(${rowCount} แถว)`);
      // ลบแถวที่ 2 (กด × ที่แถว 2) — กลับเหลือ 1
      await page.locator("#wz-records .rec-edit").nth(1).locator(".btn-del").click();
      await page.waitForTimeout(300);
    }
    await page.locator("#wz-next").click();
    await page.waitForTimeout(600);
    const tgField = await page.locator("#wz-tg-token").isVisible().catch(() => false);
    check("ไปขั้น Telegram", tgField);
  }

  // ---------- 5) ขั้น 4: Telegram (ครบ — ไม่ข้าม) ----------
  log("== 5) ขั้นที่ 4: Telegram ==");
  const tgField = page.locator("#wz-tg-token");
  if (await tgField.isVisible().catch(() => false)) {
    await tgField.fill(DATA.tg_bot);
    await page.locator("#wz-tg-find").click();
    await page.waitForTimeout(3000); // /resolve-chat-id
    const tgMsg = await page.locator("#wz-tg-msg").textContent().catch(() => "");
    if (String(tgMsg).includes("พบ chat id")) {
      pass++; log("  [PASS] ค้นหา chat id สำเร็จ (อัตโนมัติ)");
    } else {
      // getUpdates คืนว่างถ้า bot ไม่มีข้อความใหม่ (พฤติกรรม Telegram API) —
      // เทสต์ช่องกรอก chat id ด้วยมือแทน
      log(`  [WARN] resolve-chat-id: ${tgMsg.slice(0, 60)}`);
      const chatInput = page.locator("#wz-tg-chat");
      if (await chatInput.isVisible().catch(() => false)) {
        await chatInput.fill(DATA.tg_chat);
        pass++; log("  [PASS] กรอก chat id ด้วยมือได้ (ช่องใหม่)");
      } else {
        fail++; log("  [FAIL] ไม่มีช่องกรอก chat id ด้วยมือ");
      }
    }
    const testBtn = page.locator("#wz-tg-test");
    const testEnabled = await testBtn.isEnabled().catch(() => false);
    check("ปุ่มส่งข้อความทดสอบ active หลังได้ chat id", testEnabled);
    if (testEnabled) {
      await testBtn.click();
      await page.waitForTimeout(2500); // /notify-test-raw
      const testMsg = await page.locator("#wz-tg-msg").textContent().catch(() => "");
      check("ส่งข้อความทดสอบสำเร็จ", String(testMsg).includes("สำเร็จ"), `(${testMsg.slice(0, 60)})`);
    }
    await page.locator("#wz-next").click(); // "ข้าม →" = ไปขั้น 5
    await page.waitForTimeout(500);
  }

  // ---------- 6) ขั้น 5: สรุป + บันทึก ----------
  log("== 6) ขั้นที่ 5: บันทึก ==");
  const saveBtn = page.locator("#wz-next");
  if (await saveBtn.isVisible().catch(() => false)) {
    const summary = await page.locator("#wz-body").textContent().catch(() => "");
    check("สรุปก่อนบันทึกมี zone/record", summary.includes(DATA.zone) && summary.includes(DATA.record));
    await saveBtn.click();
    // รอ save-config + reload หน้า
    await page.waitForTimeout(4000);
    const reloaded = await page.locator("#public-ip, #wz-title").first().isVisible().catch(() => false);
    check("บันทึกแล้วหน้าตอบสนอง", reloaded);
  }

  // ---------- 7) ตรวจผลหลังบันทึก ----------
  log("== 7) ตรวจผลหลังบันทึก ==");
  await page.goto(URL, { waitUntil: "networkidle", timeout: 30000 });
  await page.waitForTimeout(1500);
  const wizardGone = !(await page.locator("#wizard").isVisible().catch(() => true));
  check("wizard ปิดแล้ว (ตั้งค่าเสร็จ)", wizardGone);
  const cfgErrors = await page.locator("#cfg-err").isHidden().catch(() => true);
  check("ไม่มีข้อผิดพลาด config บนหน้า", cfgErrors);
  const pill = await page.locator("#pill").textContent().catch(() => "");
  log(`     pill สถานะ: ${pill}`);

  const consoleErrors = errors.filter(e => !e.includes("401") && !e.includes("/resolve-chat-id"));
  check("ไม่มี JS error ใน console", consoleErrors.length === 0, consoleErrors.join(" | "));
} catch (e) {
  fail++;
  log("  [FAIL] exception: " + String(e).slice(0, 300));
} finally {
  await browser.close();
}

const total = pass + fail;
const pct = total ? Math.round((pass / total) * 100) : 0;
log("");
log(`===== สรุป: ผ่าน ${pass}/${total} (${pct}%) =====`);
const report = lines.join("\n");
writeFileSync(OUT, report, "utf-8");
