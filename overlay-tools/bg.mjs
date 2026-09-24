// Screenshot a transparent overlay composited over a sample "gameplay" backdrop.
// node bg.mjs <page> <out.png> [w h]
import { chromium } from "playwright";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
const here = path.dirname(fileURLToPath(import.meta.url));
const [, , page, out, w = 1920, h = 1080] = process.argv;
const browser = await chromium.launch();
const p = await browser.newPage({ viewport: { width: +w, height: +h } });
p.on("pageerror", (e) => console.log("pageerror:", e.message));
const [file, query = ""] = page.split("?");
await p.goto(pathToFileURL(path.join(here, "../vtuber-overlay-pack", file)).href + (query ? "?" + query : ""));
// Fake "gameplay" behind the transparent overlay
await p.addStyleTag({ content: `html{background:
  radial-gradient(circle at 25% 30%, rgba(255,255,255,.35) 0 6%, transparent 7%),
  linear-gradient(180deg,#7ec8f0 0%,#bfe6f7 45%,#79b865 46%,#4d8f45 70%,#3b6d36 100%)}` });
await p.waitForTimeout(2500);
await p.screenshot({ path: out });
await browser.close();
