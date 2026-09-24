// Helpers shared by the round-2 theme mockups.
window.M2 = (function () {
  "use strict";

  function rng(seed) {
    let a = seed >>> 0;
    return function () {
      a = (a + 0x6d2b79f5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  // Stand-in "gameplay": a low-poly dusk landscape with a small game HUD.
  // Draws into <canvas class="game"> at its own pixel size.
  // opts: { minimap, bars, ammo } — set any to false to hide that HUD piece
  function game(canvas, seed = 4, opts = {}) {
    const box = canvas.getBoundingClientRect();
    const W = (canvas.width = Math.round(box.width));
    const H = (canvas.height = Math.round(box.height));
    const c = canvas.getContext("2d");
    const r = rng(seed);
    const u = W / 1920;

    const sky = c.createLinearGradient(0, 0, 0, H * 0.62);
    sky.addColorStop(0, "#1d2d5c");
    sky.addColorStop(0.55, "#b8627a");
    sky.addColorStop(1, "#f6b27a");
    c.fillStyle = sky;
    c.fillRect(0, 0, W, H);

    c.fillStyle = "rgba(255,238,200,0.95)";
    c.beginPath();
    c.arc(W * 0.66, H * 0.44, 90 * u, 0, Math.PI * 2);
    c.fill();

    const layers = [
      { base: 0.58, amp: 0.2, col: [120, 86, 150] },
      { base: 0.66, amp: 0.15, col: [80, 64, 122] },
      { base: 0.75, amp: 0.1, col: [42, 58, 92] },
    ];
    for (const L of layers) {
      const step = W / 11;
      const pts = [];
      for (let x = -step; x <= W + step; x += step) pts.push([x + (r() - 0.5) * step * 0.4, H * (L.base - L.amp * r())]);
      for (let i = 0; i < pts.length - 1; i++) {
        const [x1, y1] = pts[i];
        const [x2, y2] = pts[i + 1];
        const mx = (x1 + x2) / 2 + (r() - 0.5) * step * 0.3;
        const my = H * L.base + H * 0.06;
        for (const [ax, ay, bx, by, k] of [
          [x1, y1, mx, my, 1.08],
          [mx, my, x2, y2, 0.9],
        ]) {
          const f = k * (0.92 + r() * 0.16);
          c.fillStyle = `rgb(${L.col.map((v) => Math.min(255, Math.round(v * f))).join(",")})`;
          c.beginPath();
          c.moveTo(ax, ay);
          c.lineTo(bx, by);
          c.lineTo(i % 2 ? x1 : x2, i % 2 ? y1 : y2);
          c.closePath();
          c.fill();
        }
        c.fillStyle = `rgb(${L.col.join(",")})`;
        c.beginPath();
        c.moveTo(x1, y1);
        c.lineTo(mx, my);
        c.lineTo(x2, y2);
        c.lineTo(x2, H);
        c.lineTo(x1, H);
        c.closePath();
        c.fill();
      }
    }

    const ground = c.createLinearGradient(0, H * 0.74, 0, H);
    ground.addColorStop(0, "#2f5a4a");
    ground.addColorStop(1, "#1b3a2f");
    c.fillStyle = ground;
    c.fillRect(0, H * 0.78, W, H);

    // winding road
    c.fillStyle = "#3b3a44";
    c.beginPath();
    c.moveTo(W * 0.36, H);
    c.bezierCurveTo(W * 0.42, H * 0.9, W * 0.52, H * 0.86, W * 0.5, H * 0.79);
    c.lineTo(W * 0.515, H * 0.79);
    c.bezierCurveTo(W * 0.56, H * 0.86, W * 0.6, H * 0.92, W * 0.7, H);
    c.fill();
    c.strokeStyle = "rgba(255,230,160,0.8)";
    c.setLineDash([22 * u, 22 * u]);
    c.lineWidth = 4 * u;
    c.beginPath();
    c.moveTo(W * 0.53, H);
    c.bezierCurveTo(W * 0.5, H * 0.9, W * 0.535, H * 0.85, W * 0.508, H * 0.79);
    c.stroke();
    c.setLineDash([]);

    // low-poly trees
    for (let i = 0; i < 16; i++) {
      const x = r() * W;
      if (x > W * 0.3 && x < W * 0.75) continue;
      const y = H * (0.8 + r() * 0.16);
      const s = (40 + r() * 50) * u * (y / H);
      c.fillStyle = r() < 0.5 ? "#1f4a3a" : "#28604a";
      c.beginPath();
      c.moveTo(x, y - s * 2.2);
      c.lineTo(x + s * 0.7, y);
      c.lineTo(x - s * 0.7, y);
      c.fill();
    }

    // HUD: health/shield, ammo, minimap, crosshair
    const pad = 36 * u;
    if (opts.bars !== false) {
      c.fillStyle = "rgba(0,0,0,0.45)";
      c.fillRect(pad, H - pad - 70 * u, 360 * u, 70 * u);
      c.fillStyle = "#ff5a5a";
      c.fillRect(pad + 14 * u, H - pad - 56 * u, 300 * u * 0.8, 16 * u);
      c.fillStyle = "#5ab8ff";
      c.fillRect(pad + 14 * u, H - pad - 30 * u, 300 * u * 0.55, 12 * u);
    }
    if (opts.ammo !== false) {
      c.fillStyle = "rgba(255,255,255,0.9)";
      c.font = `700 ${40 * u}px system-ui, sans-serif`;
      c.textAlign = "right";
      c.fillText("30 / 120", W - pad, H - pad);
    }
    if (opts.minimap !== false) {
      c.fillStyle = "rgba(0,0,0,0.45)";
      c.beginPath();
      c.arc(W - pad - 90 * u, pad + 90 * u, 90 * u, 0, Math.PI * 2);
      c.fill();
      c.strokeStyle = "rgba(255,255,255,0.6)";
      c.lineWidth = 3 * u;
      c.stroke();
      c.fillStyle = "#ffe36e";
      c.beginPath();
      c.arc(W - pad - 90 * u, pad + 90 * u, 8 * u, 0, Math.PI * 2);
      c.fill();
    }
    c.strokeStyle = "rgba(255,255,255,0.85)";
    c.lineWidth = 3 * u;
    const cx = W / 2,
      cy = H / 2;
    for (const [dx, dy] of [
      [1, 0],
      [-1, 0],
      [0, 1],
      [0, -1],
    ]) {
      c.beginPath();
      c.moveTo(cx + dx * 10 * u, cy + dy * 10 * u);
      c.lineTo(cx + dx * 26 * u, cy + dy * 26 * u);
      c.stroke();
    }
  }

  const MODEL_PATHS = [
    "M128 118 C80 106 40 160 36 240 C32 316 44 372 16 434 C58 414 72 374 76 320 C80 262 98 196 134 158 Z", // twin tail L
    "M272 118 C320 106 360 160 364 240 C368 316 356 372 384 434 C342 414 328 374 324 320 C320 262 302 196 266 158 Z", // twin tail R
    "M174 304 C134 314 106 332 96 390 L84 520 L316 520 L304 390 C294 332 266 314 226 304 Z", // shoulders
    "M178 236 L222 236 L227 316 L173 316 Z", // neck
    "M118 178 C112 218 116 250 128 276 C136 258 142 236 146 212 Z", // side locks
    "M282 178 C288 218 284 250 272 276 C264 258 258 236 254 212 Z",
    "M116 165 A84 90 0 1 0 284 165 A84 90 0 1 0 116 165 Z", // head
    "M142 100 L138 44 L184 82 Z", // cat ears
    "M258 100 L262 44 L216 82 Z",
    "M198 78 C192 52 208 34 232 38 C214 46 206 58 208 80 Z", // ahoge
  ];

  // VTuber bust silhouette marking where the streamer's model goes.
  // outline: draws a clean outer stroke of `stroke` color and `width` px (in viewBox units).
  function model({ fill = "#000", stroke = "", width = 0, extra = "", cls = "" } = {}) {
    const paths = MODEL_PATHS.map((d) => `<path d="${d}"/>`).join("");
    const outline = stroke
      ? `<g fill="${stroke}" stroke="${stroke}" stroke-width="${width * 2}" stroke-linejoin="round">${paths}</g>`
      : "";
    return `<svg class="model-svg ${cls}" viewBox="0 0 400 520" preserveAspectRatio="xMidYMax meet">${outline}<g fill="${fill}">${paths}</g>${extra}</svg>`;
  }

  // Seven-segment digits ("0-9", ":", " "), returned as SVG markup.
  const SEG = { 0: "abcdef", 1: "bc", 2: "abged", 3: "abgcd", 4: "fgbc", 5: "afgcd", 6: "afgedc", 7: "abc", 8: "abcdefg", 9: "abcdfg" };
  function sevenSeg(text, { h = 120, on = "#222", off = "rgba(0,0,0,0.08)", skew = -6 } = {}) {
    const w = h * 0.52,
      t = h * 0.12,
      gap = h * 0.14;
    let x = 0,
      out = "";
    const bar = (x1, y1, horiz) => {
      const L = horiz ? w - t : h / 2 - t;
      const hs = t / 2;
      return horiz
        ? `M${x1} ${y1} l${hs} ${-hs} h${L - t} l${hs} ${hs} l${-hs} ${hs} h${-(L - t)} z`
        : `M${x1} ${y1} l${hs} ${hs} v${L - t} l${-hs} ${hs} l${-hs} ${-hs} v${-(L - t)} z`;
    };
    for (const ch of text) {
      if (ch === ":") {
        out += `<rect x="${x + t * 0.2}" y="${h * 0.28}" width="${t}" height="${t}" fill="${on}"/><rect x="${x + t * 0.2}" y="${h * 0.64}" width="${t}" height="${t}" fill="${on}"/>`;
        x += t * 1.4 + gap;
        continue;
      }
      const segs = SEG[ch] || "";
      const parts = {
        a: bar(x + t / 2, t / 2, true),
        g: bar(x + t / 2, h / 2, true),
        d: bar(x + t / 2, h - t / 2, true),
        f: bar(x + t / 2, t / 2, false),
        e: bar(x + t / 2, h / 2, false),
        b: bar(x + w - t / 2, t / 2, false),
        c: bar(x + w - t / 2, h / 2, false),
      };
      for (const [k, d] of Object.entries(parts)) out += `<path d="${d}" fill="${segs.includes(k) ? on : off}"/>`;
      x += w + gap;
    }
    return `<svg viewBox="${-t} ${-t} ${x + t} ${h + 2 * t}" height="${h}" style="transform: skewX(${skew}deg)">${out}</svg>`;
  }

  // Barcode bars for ID cards / tickets
  function barcode(n = 60, seed = 2, color = "#000", height = 60) {
    const r = rng(seed);
    let x = 0,
      out = "";
    for (let i = 0; i < n; i++) {
      const w = 1 + Math.floor(r() * 4);
      if (r() > 0.35) out += `<rect x="${x}" y="0" width="${w}" height="${height}" fill="${color}"/>`;
      x += w + 1;
    }
    return `<svg viewBox="0 0 ${x} ${height}" preserveAspectRatio="none" style="width:100%;height:100%">${out}</svg>`;
  }

  function ready(fn) {
    const go = () => (document.fonts ? document.fonts.ready.then(fn) : fn());
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", go);
    else go();
  }

  return { rng, game, model, sevenSeg, barcode, ready };
})();
