// Screenshot theme mockups → mockups/previews/<name>.jpg
//   node mock-shot.mjs [name ...]
import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
const here = path.dirname(fileURLToPath(import.meta.url));
const dir = path.join(here, "../mockups");
const names = process.argv.slice(2).length ? process.argv.slice(2)
  : (await fs.readdir(dir)).filter((f) => f.endsWith(".html") && f !== "index.html").map((f) => f.replace(".html", ""));
await fs.mkdir(path.join(dir, "previews"), { recursive: true });
const browser = await chromium.launch();
for (const n of names) {
  const p = await browser.newPage({ viewport: { width: 1920, height: 1620 } });
  p.on("pageerror", (e) => console.log(n, "pageerror:", e.message));
  await p.goto(pathToFileURL(path.join(dir, n + ".html")).href);
  await p.evaluate(() => document.fonts.ready);
  await p.waitForTimeout(1200);
  await p.screenshot({ path: path.join(dir, "previews", n + ".jpg"), type: "jpeg", quality: 86 });
  await p.close();
  console.log("✓", n);
}
await browser.close();
