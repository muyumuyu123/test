// Screenshots for the round-2 theme mockups (mockups/v2/<theme>.html, two .screen sections each).
//   node mock2-shot.mjs [theme ...]
// Writes previews/<theme>-start.jpg, <theme>-live.jpg and, with FFMPEG set, <theme>.jpg (both stacked)
// plus overview-start.jpg / overview-live.jpg when every theme is rendered.
import { chromium } from "playwright";
import { spawnSync } from "node:child_process";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const dir = path.join(here, process.env.MOCK_DIR || "../mockups/v2");
const out = path.join(dir, "previews");
const FFMPEG = process.env.FFMPEG;
const all = (await fs.readdir(dir)).filter((f) => f.endsWith(".html") && f !== "index.html").map((f) => f.slice(0, -5)).sort();
const names = process.argv.length > 2 ? process.argv.slice(2) : all;

await fs.mkdir(out, { recursive: true });
const browser = await chromium.launch();
for (const name of names) {
  const page = await browser.newPage({ viewport: { width: 1920, height: 2160 } });
  page.on("pageerror", (e) => console.log(name, "pageerror:", e.message));
  page.on("console", (m) => m.type() === "error" && console.log(name, "console:", m.text()));
  await page.goto(pathToFileURL(path.join(dir, name + ".html")).href + "?shot", { waitUntil: "domcontentloaded", timeout: 180000 });
  await page.evaluate(() => document.fonts.ready);
  // pages that paint heavy canvas scenes set window.__done when finished
  await page.waitForFunction(() => window.__done !== false, null, { timeout: 180000 });
  await page.waitForTimeout(1500);
  // freeze every animation at its first frame so screenshots are repeatable
  await page.evaluate(() => document.getAnimations().forEach((a) => { a.currentTime = 0; a.pause(); }));
  const screens = await page.$$(".screen");
  const tags = (process.env.TAGS || "start,live").split(",");
  for (let i = 0; i < screens.length; i++) {
    await screens[i].screenshot({ path: path.join(out, `${name}-${tags[i] || i}.jpg`), type: "jpeg", quality: 88 });
  }
  await page.close();
  if (FFMPEG) {
    spawnSync(FFMPEG, ["-y", "-loglevel", "error", "-i", path.join(out, `${name}-start.jpg`), "-i", path.join(out, `${name}-live.jpg`),
      "-filter_complex", "[0][1]vstack=inputs=2,scale=1440:-1", "-q:v", "3", path.join(out, `${name}.jpg`)]);
  }
  console.log("✓", name);
}
await browser.close();

if (FFMPEG && names.length === all.length && all.length >= 2) {
  for (const tag of ["start", "live"]) {
    const inputs = all.flatMap((n) => ["-i", path.join(out, `${n}-${tag}.jpg`)]);
    const cols = Math.min(4, all.length);
    const layout = all.map((_, i) => `${(i % cols) * 480}_${Math.floor(i / cols) * 270}`).join("|");
    const scaled = all.map((_, i) => `[${i}]scale=480:270[s${i}]`).join(";");
    const stack = all.map((_, i) => `[s${i}]`).join("") + `xstack=inputs=${all.length}:layout=${layout}`;
    spawnSync(FFMPEG, ["-y", "-loglevel", "error", ...inputs, "-filter_complex", `${scaled};${stack}`, "-q:v", "3", path.join(dir, `overview-${tag}.jpg`)]);
  }
  console.log("✓ overview sheets");
}
