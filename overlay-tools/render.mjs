// Renders every alert type × theme to a transparent WebM (VP9 + alpha) you can
// upload to Streamlabs, StreamElements, Twitch alerts, etc.
//   node render.mjs                 → all types, all themes
//   node render.mjs sub midnight    → just one
// Needs an ffmpeg with libvpx-vp9 on PATH (or set FFMPEG=/path/to/ffmpeg).
import { chromium } from "playwright";
import { spawn } from "node:child_process";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const pack = path.join(here, "../vtuber-overlay-pack");
const outDir = path.join(pack, "alerts-video");
const FFMPEG = process.env.FFMPEG || "ffmpeg";
const FPS = 30;
const DURATION = 6; // seconds, matches the default alerts.duration
const [W, H] = [900, 420];

const types = process.argv[2] ? [process.argv[2]] : ["follow", "sub", "tip", "cheer", "raid", "member"];
const themes = process.argv[3] ? [process.argv[3]] : ["midnight", "sakura", "aurora"];

function run(cmd, args) {
  return new Promise((resolve, reject) => {
    const p = spawn(cmd, args, { stdio: ["ignore", "ignore", "pipe"] });
    let err = "";
    p.stderr.on("data", (d) => (err += d));
    p.on("close", (code) => (code === 0 ? resolve() : reject(new Error(err.slice(-800)))));
  });
}

await fs.mkdir(outDir, { recursive: true });
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: W, height: H } });

for (const theme of themes) {
  for (const type of types) {
    const tmp = await fs.mkdtemp(path.join(os.tmpdir(), "alert-"));
    const url = pathToFileURL(path.join(pack, "widgets/alerts.html")).href + `?render=${type}&bare&theme=${theme}`;
    await page.goto(url);
    await page.evaluate(() => document.fonts.ready);
    const frames = DURATION * FPS;
    for (let f = 0; f < frames; f++) {
      const t = (f / FPS) * 1000;
      // Seek every CSS animation to the same moment so frames are exact
      await page.evaluate((ms) => {
        for (const a of document.getAnimations()) {
          a.pause();
          a.currentTime = ms;
        }
      }, t);
      await page.screenshot({ path: path.join(tmp, `f${String(f).padStart(4, "0")}.png`), omitBackground: true });
    }
    const out = path.join(outDir, `${theme}-${type}.webm`);
    await run(FFMPEG, ["-y", "-loglevel", "error", "-framerate", String(FPS), "-i", path.join(tmp, "f%04d.png"),
      "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "32", "-row-mt", "1", "-auto-alt-ref", "0", out]);
    await fs.rm(tmp, { recursive: true });
    console.log("✓", path.relative(here, out));
  }
}
await browser.close();
