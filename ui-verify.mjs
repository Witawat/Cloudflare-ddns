import { chromium } from "playwright";

const URL = "http://127.0.0.1:8123/";
const viewports = [
  { w: 360, h: 740, name: "360" },
  { w: 768, h: 900, name: "768" },
  { w: 1024, h: 800, name: "1024" },
  { w: 1920, h: 1080, name: "1920" },
];

const browser = await chromium.launch();
const page = await browser.newPage();
await page.goto(URL, { waitUntil: "networkidle" });
await page.waitForTimeout(1500);

let allOk = true;
for (const vp of viewports) {
  await page.setViewportSize({ width: vp.w, height: vp.h });
  await page.waitForTimeout(400);
  const m = await page.evaluate(() => {
    const doc = document.documentElement;
    const rec = document.querySelector(".rec-edit");
    let collision = null;
    if (rec) {
      const mini = rec.querySelector(".mini");
      const del = rec.querySelector(".btn-del");
      if (mini && del) {
        const a = mini.getBoundingClientRect();
        const b = del.getBoundingClientRect();
        const overlapW = Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left));
        const overlapH = Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
        collision = { overlapW: Math.round(overlapW), overlapH: Math.round(overlapH), miniW: Math.round(a.width), delX: Math.round(b.left - a.right) };
      }
    }
    // history table ล้นไหม
    const hist = document.getElementById("history");
    let histOverflow = null;
    if (hist) {
      const t = hist.querySelector("table");
      if (t) {
        histOverflow = Math.round(t.parentElement.scrollWidth - t.parentElement.clientWidth);
      }
    }
    const nameEl = document.querySelector(".rec-name");
    return {
      overflowX: doc.scrollWidth - innerWidth,
      collision,
      histOverflow,
      recNameClickable: nameEl ? nameEl.className.includes("clickable") : null,
    };
  });
  const ok = m.overflowX <= 0 && (!m.collision || (m.collision.overlapW * m.collision.overlapH) === 0);
  if (!ok) allOk = false;
  console.log(
    `${vp.name.padEnd(6)} | overflowX: ${m.overflowX} | × vs 6: ${m.collision ? "overlap area " + (m.collision.overlapW * m.collision.overlapH) + " (x-gap " + m.collision.delX + "px)" : "no editor"} | history scroll: ${m.histOverflow}px | name clickable: ${m.recNameClickable} ${ok ? "OK" : "** ISSUE **"}`
  );
}
await browser.close();
console.log(allOk ? "\nALL OK" : "\nHAS ISSUES");
