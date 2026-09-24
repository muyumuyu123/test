// Product screenshots for your store listing → overlay-tools/previews/*.jpg
//   node previews.mjs
import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const pack = path.join(here, "../vtuber-overlay-pack");
const outDir = path.join(here, "previews");

// Stand-in gameplay behind transparent overlays
const BACKDROP = `html{background:
  radial-gradient(circle at 25% 30%, rgba(255,255,255,.35) 0 6%, transparent 7%),
  linear-gradient(180deg,#7ec8f0 0%,#bfe6f7 45%,#79b865 46%,#4d8f45 70%,#3b6d36 100%)}`;

const SHOTS = [
  { name: "starting-soon", file: "scenes/starting-soon.html", size: [1920, 1080], themes: ["midnight", "sakura", "aurora"] },
  { name: "brb", file: "scenes/brb.html", size: [1920, 1080] },
  { name: "ending", file: "scenes/ending.html", size: [1920, 1080] },
  { name: "game-frame", file: "overlays/game-frame.html", size: [1920, 1080], backdrop: true },
  { name: "alert-tip", file: "widgets/alerts.html", query: "render=tip", size: [900, 560], backdrop: true, wait: 2200 },
  { name: "chat", file: "widgets/chat.html", size: [360, 520], backdrop: true },
  { name: "goal", file: "widgets/goal.html", size: [800, 170], backdrop: true, wait: 2500 },
  { name: "gallery", file: "index.html", size: [1440, 2300], wait: 4000 },
];

await fs.mkdir(outDir, { recursive: true });
const browser = await chromium.launch();
for (const shot of SHOTS) {
  for (const theme of shot.themes || ["midnight"]) {
    const page = await browser.newPage({ viewport: { width: shot.size[0], height: shot.size[1] } });
    const q = new URLSearchParams(shot.query || "");
    q.set("theme", theme);
    q.set("still", "");
    await page.goto(pathToFileURL(path.join(pack, shot.file)).href + "?" + q);
    if (shot.backdrop) await page.addStyleTag({ content: BACKDROP });
    await page.waitForTimeout(shot.wait || 1800);
    const out = path.join(outDir, `${shot.name}${shot.themes ? "-" + theme : ""}.jpg`);
    await page.screenshot({ path: out, type: "jpeg", quality: 88 });
    await page.close();
    console.log("✓", path.relative(here, out));
  }
}
await browser.close();
