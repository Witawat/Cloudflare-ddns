// ตรวจ Responsive UI ของ Web UI ทุกขนาดจอ (ต้องรัน service/webui ก่อน)
// วิธีใช้: cd temp && npm i playwright && node ui-check.mjs
import { chromium } from "playwright";

const URL = "http://127.0.0.1:8123/";
const viewports = [
  { w: 360, h: 740, name: "มือถือเล็ก" },
  { w: 390, h: 740, name: "มือถือ" },
  { w: 768, h: 900, name: "แท็บเล็ต" },
  { w: 860, h: 800, name: "breakpoint 860" },
  { w: 1024, h: 800, name: "แล็ปท็อปเล็ก" },
  { w: 1920, h: 1080, name: "จอใหญ่" },
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
    const recCs = rec ? getComputedStyle(rec) : null;
    const dt = document.getElementById("daily_report_time");
    const dtRect = dt ? dt.getBoundingClientRect() : null;
    return {
      overflowX: doc.scrollWidth - innerWidth,
      recCols: recCs ? recCs.gridTemplateColumns.split(" ").length : 0,
      recWidth: rec ? Math.round(rec.getBoundingClientRect().width) : 0,
      dailyTime: dtRect ? { w: Math.round(dtRect.width), h: Math.round(dtRect.height) } : null,
      topbarH: Math.round(document.querySelector(".topbar").getBoundingClientRect().height),
    };
  });
  const ok = m.overflowX <= 0;
  if (!ok) allOk = false;
  console.log(
    `${vp.name.padEnd(12)} ${String(vp.w).padStart(4)}px | overflowX: ${m.overflowX} | recEdit: ${m.recCols} cols (${m.recWidth}px) | daily_time: ${m.dailyTime ? m.dailyTime.w + "x" + m.dailyTime.h : "-"} | topbar: ${m.topbarH}px ${ok ? "OK" : "** OVERFLOW **"}`
  );
}
await browser.close();
console.log(allOk ? "\nALL VIEWPORTS OK" : "\nHAS PROBLEMS");
