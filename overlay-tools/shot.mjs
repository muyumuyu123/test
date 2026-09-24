// Quick screenshot: node shot.mjs <page relative to pack> <out.png> [w h] [waitMs]
import { chromium } from "playwright";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
const here = path.dirname(fileURLToPath(import.meta.url));
const [, , page, out, w = 1920, h = 1080, wait = 1800] = process.argv;
const browser = await chromium.launch();
const p = await browser.newPage({ viewport: { width: +w, height: +h } });
p.on("console", (m) => console.log("console:", m.text()));
p.on("pageerror", (e) => console.log("pageerror:", e.message));
const [file, query = ""] = page.split("?");
await p.goto(pathToFileURL(path.join(here, "../vtuber-overlay-pack", file)).href + (query ? "?" + query : ""));
await p.waitForTimeout(+wait);
await p.screenshot({ path: out, omitBackground: true });
await browser.close();
