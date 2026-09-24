// Builds a StreamElements "Custom Widget" version of the alert box from the
// same source files, into vtuber-overlay-pack/streamelements/alerts-widget/.
//   node build-se.mjs
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const pack = path.join(here, "../vtuber-overlay-pack");
const out = path.join(pack, "streamelements/alerts-widget");
const read = (f) => fs.readFile(path.join(pack, f), "utf8");

// StreamElements can't see local files, so fonts come from Google Fonts instead
const theme = (await read("assets/theme.css")).replace(/@font-face\s*{[^}]*}\s*/g, "");
const css = [
  "@import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@400..700&family=Nunito:wght@400..900&display=block');",
  theme,
  await read("widgets/alerts.css"),
  "html, body { background: transparent; }",
].join("\n\n");

const html = `<!-- Starlight Dreams alert box — StreamElements custom widget -->\n<div id="stage"></div>\n`;

const js = [
  "// Starlight Dreams alert box — built from widgets/alerts.js. Settings live in the Fields panel.",
  "window.OVERLAY_CONFIG = { theme: 'midnight' };",
  await read("assets/core.js"),
  await read("widgets/alerts.js"),
].join("\n\n");

const fields = {
  theme: { type: "dropdown", label: "Color theme", value: "midnight", options: { midnight: "Midnight", sakura: "Sakura", aurora: "Aurora" } },
  duration: { type: "number", label: "Seconds on screen", value: 6, min: 3, max: 20 },
  currency: { type: "text", label: "Currency symbol", value: "$" },
  sound: { type: "sound-input", label: "Alert sound (optional)", value: "" },
  volume: { type: "slider", label: "Sound volume", value: 50, min: 0, max: 100, step: 1 },
  label_follow: { type: "text", label: "Follow label", value: "New Follower" },
  label_sub: { type: "text", label: "Subscriber label", value: "New Subscriber" },
  label_tip: { type: "text", label: "Tip label", value: "New Tip" },
  label_cheer: { type: "text", label: "Cheer label", value: "Cheer" },
  label_raid: { type: "text", label: "Raid label", value: "Incoming Raid" },
  label_member: { type: "text", label: "YouTube member label", value: "New Member" },
};

await fs.mkdir(out, { recursive: true });
await fs.writeFile(path.join(out, "HTML.html"), html);
await fs.writeFile(path.join(out, "CSS.css"), css);
await fs.writeFile(path.join(out, "JS.js"), js);
await fs.writeFile(path.join(out, "FIELDS.json"), JSON.stringify(fields, null, 2) + "\n");
console.log("✓ built", path.relative(process.cwd(), out));
