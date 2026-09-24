// Procedural cinematic cyberpunk city scenes, painted on <canvas>.
// Original artwork: layered buildings with aerial haze, neon signage,
// volumetric light, rain and wet reflections.
window.CITY = (function () {
  "use strict";
  const W = 1920, H = 1080;

  // ---------------------------------------------------------------- helpers
  function rng(seed) {
    let a = seed >>> 0;
    return () => {
      a = (a + 0x6d2b79f5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  const lerp = (a, b, t) => a + (b - a) * t;
  const hex = (h) => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];
  const mixc = (a, b, t) => { const A = hex(a), B = hex(b); return "#" + A.map((v, i) => Math.round(lerp(v, B[i], t)).toString(16).padStart(2, "0")).join(""); };
  const rgba = (h, a) => { const [r, g, b] = hex(h); return `rgba(${r},${g},${b},${a})`; };

  function canvas(w = W, h = H) {
    const c = document.createElement("canvas");
    c.width = w; c.height = h;
    return c;
  }

  // Neon text: coloured glow halos + bright core
  function neonText(c, text, x, y, { font, color, glow = color, blur = 26, align = "center", core = "#fff", alpha = 1 }) {
    c.save();
    c.font = font;
    c.textAlign = align;
    c.textBaseline = "middle";
    for (const [b, a] of [[blur * 2.2, 0.55], [blur, 0.8], [blur * 0.4, 1]]) {
      c.shadowColor = glow; c.shadowBlur = b;
      c.fillStyle = color;
      c.globalAlpha = alpha * a;
      c.fillText(text, x, y);
    }
    c.shadowBlur = 0;
    c.globalAlpha = alpha;
    c.fillStyle = core;
    c.fillText(text, x, y);
    c.restore();
  }

  function glowRect(c, x, y, w, h, color, blur = 30, alpha = 1) {
    c.save();
    c.globalAlpha = alpha;
    c.shadowColor = color; c.shadowBlur = blur;
    c.fillStyle = color;
    c.fillRect(x, y, w, h);
    c.restore();
  }

  // Soft additive light blob
  function bloom(c, x, y, r, color, a = 0.5) {
    const g = c.createRadialGradient(x, y, 0, x, y, r);
    g.addColorStop(0, rgba(color, a));
    g.addColorStop(1, rgba(color, 0));
    c.save();
    c.globalCompositeOperation = "lighter";
    c.fillStyle = g;
    c.fillRect(x - r, y - r, r * 2, r * 2);
    c.restore();
  }

  // Whole-frame glow: blurred bright copy screened on top
  function postBloom(c, strength = 0.45, blur = 14) {
    const t = canvas(c.canvas.width, c.canvas.height), x = t.getContext("2d");
    x.filter = `blur(${blur}px) brightness(1.15)`;
    x.drawImage(c.canvas, 0, 0);
    c.save();
    c.globalCompositeOperation = "screen";
    c.globalAlpha = strength;
    c.drawImage(t, 0, 0);
    c.restore();
  }

  function grain(c, amount = 0.07, seed = 1) {
    const r = rng(seed), w = 256, t = canvas(w, w), x = t.getContext("2d"), img = x.createImageData(w, w);
    for (let i = 0; i < img.data.length; i += 4) { const v = r() * 255; img.data[i] = img.data[i + 1] = img.data[i + 2] = v; img.data[i + 3] = 255; }
    x.putImageData(img, 0, 0);
    c.save();
    c.globalAlpha = amount;
    c.globalCompositeOperation = "overlay";
    c.fillStyle = c.createPattern(t, "repeat");
    c.fillRect(0, 0, c.canvas.width, c.canvas.height);
    c.restore();
  }

  function vignette(c, a = 0.6) {
    const g = c.createRadialGradient(W / 2, H / 2, H * 0.35, W / 2, H / 2, H * 1.05);
    g.addColorStop(0, "rgba(0,0,0,0)");
    g.addColorStop(1, `rgba(0,0,0,${a})`);
    c.fillStyle = g;
    c.fillRect(0, 0, W, H);
  }

  function rain(c, r, n, { angle = 0.18, len = [18, 46], alpha = [0.08, 0.28], color = "#cfe8ff", width = 1.2 } = {}) {
    c.save();
    c.strokeStyle = color;
    c.lineWidth = width;
    c.lineCap = "round";
    for (let i = 0; i < n; i++) {
      const x = r() * (W + 200) - 100, y = r() * H, l = lerp(len[0], len[1], r());
      c.globalAlpha = lerp(alpha[0], alpha[1], r());
      c.beginPath();
      c.moveTo(x, y);
      c.lineTo(x - l * angle, y + l);
      c.stroke();
    }
    c.restore();
  }

  // ---------------------------------------------------------------- props
  // Building: vertical light falloff, facade style, windows, crown, rim light
  function building(c, r, { x, w, top, bottom, color, haze = "#f0a36a", lift = 0.12, windows, winColors, winSize, rim, rimSide = 1, crown = true, style }) {
    const g = c.createLinearGradient(0, top, 0, bottom);
    g.addColorStop(0, mixc(color, haze, lift));
    g.addColorStop(1, color);
    c.fillStyle = g;
    c.fillRect(x, top, w, bottom - top);
    if (crown && r() < 0.6) {
      const cw = w * lerp(0.35, 0.8, r()), ch = lerp(12, 70, r()) * Math.min(2, w / 90);
      c.fillStyle = mixc(color, haze, lift * 1.2);
      c.fillRect(x + (w - cw) / 2, top - ch, cw, ch + 1);
      if (r() < 0.55) c.fillRect(x + w / 2 - 1.5, top - ch - lerp(20, 110, r()), 3, lerp(20, 110, r()));
      if (r() < 0.3) { c.fillStyle = "#ff3b3b"; c.fillRect(x + w / 2 - 2, top - ch - 4, 4, 4); }
    }
    style = style || ["grid", "bands", "fins", "grid", "glass"][Math.floor(r() * 5)];
    if (style === "fins") {
      c.fillStyle = "rgba(0,0,0,.18)";
      for (let xx = x + 4; xx < x + w; xx += 9) c.fillRect(xx, top, 3, bottom - top);
    }
    if (style === "glass") {
      const gg = c.createLinearGradient(x, 0, x + w, 0);
      gg.addColorStop(0, "rgba(255,255,255,0)"); gg.addColorStop(0.6, rgba(haze, 0.18)); gg.addColorStop(1, "rgba(255,255,255,0)");
      c.fillStyle = gg; c.fillRect(x, top, w, bottom - top);
    }
    if (windows > 0) {
      const [ww, wh, gx, gy] = winSize;
      if (style === "bands") {
        for (let y = top + gy * 2; y < bottom; y += (wh + gy) * 2) {
          if (r() < windows * 1.6) {
            c.fillStyle = winColors[Math.floor(r() * winColors.length)];
            c.globalAlpha = lerp(0.3, 0.85, r());
            c.fillRect(x + gx, y, w - gx * 2, Math.max(1, wh * 0.6));
          }
        }
      } else if (style !== "glass" || r() < 0.4) {
        for (let y = top + gy; y < bottom - wh; y += wh + gy) {
          const rowLit = r() < 0.7;
          for (let xx = x + gx; xx < x + w - ww; xx += ww + gx) {
            if (rowLit && r() < windows) {
              c.fillStyle = winColors[Math.floor(r() * winColors.length)];
              c.globalAlpha = lerp(0.3, 1, r());
              c.fillRect(xx, y, ww, wh);
            }
          }
        }
      }
      c.globalAlpha = 1;
    }
    if (rim) {
      const rw = Math.min(14, w * 0.12);
      const gr = c.createLinearGradient(rimSide > 0 ? x + w - rw : x + rw, 0, rimSide > 0 ? x + w : x, 0);
      gr.addColorStop(0, rgba(rim, 0));
      gr.addColorStop(1, rgba(rim, 0.6));
      c.fillStyle = gr;
      c.fillRect(rimSide > 0 ? x + w - rw : x, top, rw, bottom - top);
    }
  }

  // Billboard: glowing panel with scanlines + content callback
  function billboard(c, x, y, w, h, { from, to, glow, content, frame = "#0b0d12", alpha = 1 }) {
    c.save();
    c.globalAlpha = alpha;
    c.fillStyle = frame;
    c.fillRect(x - 6, y - 6, w + 12, h + 12);
    c.shadowColor = glow; c.shadowBlur = 40;
    const g = c.createLinearGradient(x, y, x + w, y + h);
    g.addColorStop(0, from); g.addColorStop(1, to);
    c.fillStyle = g;
    c.fillRect(x, y, w, h);
    c.shadowBlur = 0;
    c.save();
    c.beginPath(); c.rect(x, y, w, h); c.clip();
    if (content) content(c, x, y, w, h);
    c.globalAlpha = 0.18 * alpha;
    c.fillStyle = "#000";
    for (let yy = y; yy < y + h; yy += 4) c.fillRect(x, yy, w, 2);
    c.restore();
    c.restore();
  }

  function palm(c, x, y, h, lean, color) {
    c.save();
    c.strokeStyle = color; c.fillStyle = color; c.lineCap = "round";
    const tx = x + lean, ty = y - h;
    c.lineWidth = h * 0.03;
    c.beginPath(); c.moveTo(x, y); c.quadraticCurveTo(x + lean * 0.1, y - h * 0.55, tx, ty); c.stroke();
    for (let i = 0; i < 11; i++) {
      const a = Math.PI + (i / 10) * Math.PI + (i % 2 ? 0.08 : -0.08);
      const L = h * (0.3 + ((i * 7) % 5) * 0.03);
      const ex = tx + Math.cos(a) * L, ey = ty + Math.sin(a) * L * 0.35 + L * 0.55;
      const mx = tx + Math.cos(a) * L * 0.5, my = ty + Math.sin(a) * L * 0.5 - L * 0.12;
      c.lineWidth = h * 0.012;
      c.beginPath(); c.moveTo(tx, ty); c.quadraticCurveTo(mx, my, ex, ey); c.stroke();
      for (let k = 1; k < 9; k++) {
        const t = k / 9, px = (1 - t) * (1 - t) * tx + 2 * (1 - t) * t * mx + t * t * ex, py = (1 - t) * (1 - t) * ty + 2 * (1 - t) * t * my + t * t * ey;
        c.lineWidth = h * 0.006;
        c.beginPath(); c.moveTo(px, py); c.lineTo(px + Math.cos(a) * L * 0.06, py + L * 0.12 * (1 - t * 0.4)); c.stroke();
      }
    }
    c.beginPath(); c.arc(tx, ty + 3, h * 0.025, 0, 7); c.fill();
    c.restore();
  }

  // Low sports car, side view. (x, y) = rear wheel ground point.
  function car(c, x, y, s, color, rim, tail = "#ff2a3c") {
    c.save();
    c.translate(x, y); c.scale(s, s);
    c.fillStyle = color;
    c.beginPath();
    c.moveTo(-60, -30); c.lineTo(-54, -66); c.lineTo(-20, -74); c.lineTo(90, -80);
    c.bezierCurveTo(140, -124, 250, -128, 300, -96); c.lineTo(420, -66); c.lineTo(452, -48); c.lineTo(450, -18); c.lineTo(-60, -18); c.closePath();
    c.fill();
    c.fillRect(-70, -96, 90, 8); c.fillRect(-40, -90, 8, 20); c.fillRect(0, -90, 8, 18);
    c.fillStyle = "rgba(255,255,255,.08)";
    c.beginPath(); c.moveTo(110, -86); c.bezierCurveTo(150, -116, 240, -118, 286, -94); c.lineTo(110, -86); c.fill();
    for (const wx of [30, 360]) { c.fillStyle = "#07080b"; c.beginPath(); c.arc(wx, -20, 40, 0, 7); c.fill(); c.strokeStyle = "rgba(255,210,150,.35)"; c.lineWidth = 3; c.beginPath(); c.arc(wx, -20, 26, 0, 7); c.stroke(); }
    c.strokeStyle = rgba(rim, 0.8); c.lineWidth = 3;
    c.beginPath(); c.moveTo(-54, -68); c.lineTo(90, -80); c.bezierCurveTo(140, -124, 250, -128, 300, -96); c.lineTo(420, -66); c.stroke();
    c.restore();
    glowRect(c, x - 62 * s, y - 58 * s, 10 * s, 14 * s, tail, 24, 1);
  }

  // Giant holographic ad of the streamer's silhouette
  function hologram(c, x, y, h, color = "#ff4fd8") {
    const paths = (window.M2 && M2.MODEL_PATHS) || [];
    const s = h / 520;
    c.save();
    c.translate(x, y); c.scale(s, s);
    const p = new Path2D(); paths.forEach((d) => p.addPath(new Path2D(d)));
    c.shadowColor = color; c.shadowBlur = 50;
    c.fillStyle = rgba(color, 0.45); c.fill(p);
    c.shadowBlur = 0;
    c.clip(p);
    c.fillStyle = rgba(color, 0.7);
    for (let yy = 0; yy < 520; yy += 7) c.fillRect(-10, yy, 420, 2.5);
    c.restore();
  }

  const KANJI = ["酒", "夜市", "電脳", "ラーメン", "ホテル", "営業中", "月"];

  // ---------------------------------------------------------------- SKYLINE
  // Golden-hour megacity: warm hazy sky, sun in a gap between two tower
  // clusters, dark hero towers up front, dusty street in the foreground.
  // opts.hero(c) paints the big billboard; opts.sign(c) extra signs; opts.spill = ground light pools.
  function skyline(target, opts = {}) {
    const c = target.getContext("2d");
    const r = rng(opts.seed || 7);
    const sunX = opts.sunX || 1080, sunY = opts.sunY || 470;
    const HAZE = "#f3a468", DARK = "#10131c";

    const sky = c.createLinearGradient(0, 0, 0, 760);
    sky.addColorStop(0, "#241d36");
    sky.addColorStop(0.3, "#6e3b4f");
    sky.addColorStop(0.58, "#d37a47");
    sky.addColorStop(0.82, "#ffb46a");
    sky.addColorStop(1, "#ffd59a");
    c.fillStyle = sky;
    c.fillRect(0, 0, W, H);

    c.save();
    for (let i = 0; i < 90; i++) {
      const y = lerp(30, 520, Math.pow(r(), 1.2)), x = r() * W, rx = lerp(140, 560, r()), ry = lerp(10, 40, r());
      const lit = Math.max(0, 1 - Math.hypot(x - sunX, y - sunY) / 900);
      c.filter = `blur(${lerp(8, 22, r())}px)`;
      c.fillStyle = r() < 0.6 ? `rgba(255,${Math.round(lerp(140, 225, lit))},${Math.round(lerp(100, 170, lit))},${lerp(0.2, 0.55, r())})` : `rgba(80,38,64,${lerp(0.15, 0.35, r())})`;
      c.beginPath(); c.ellipse(x, y, rx, ry, lerp(-0.05, 0.05, r()), 0, Math.PI * 2); c.fill();
    }
    c.restore();
    bloom(c, sunX, sunY, 620, "#ffae5c", 0.5);
    bloom(c, sunX, sunY, 200, "#fff0c8", 0.9);
    bloom(c, sunX, sunY, 70, "#ffffff", 1);

    const hazeCoat = (a, top = 250, bottom = 900) => {
      const hz = c.createLinearGradient(0, top, 0, bottom);
      hz.addColorStop(0, rgba(HAZE, a * 0.35));
      hz.addColorStop(1, rgba(HAZE, a));
      c.fillStyle = hz; c.fillRect(0, 0, W, H);
    };
    const gapShape = (x, w) => { const d = Math.abs(x + w / 2 - sunX); return d < 260 ? 0.35 : d < 520 ? 0.7 : 1; };
    const signs = [];
    const cluster = (L) => {
      for (let i = 0; i < L.n; i++) {
        const w = lerp(L.wMin, L.wMax, r()), x = r() * (W + w) - w;
        const h = lerp(L.hMin, L.hMax, Math.pow(r(), 1.3)) * (L.gap ? gapShape(x, w) : 1);
        building(c, r, { x, w, top: L.base - h, bottom: H, color: L.col, haze: HAZE, lift: L.lift, windows: L.win, winColors: L.wc, winSize: L.ws, rim: L.rim, rimSide: x + w / 2 < sunX ? 1 : -1 });
        if (L.signs && r() < L.signs) signs.push({ x: x + w * 0.12, y: L.base - h + lerp(30, h * 0.45, r()), w: w * 0.76, h: lerp(26, 90, r()), a: L.signA });
        if (L.edge && r() < 0.35) glowRect(c, x + w - 2, L.base - h, 2, h * lerp(0.3, 0.8, r()), "#7ef6ff", 10, 0.7);
      }
    };
    const flushSigns = () => {
      for (const s of signs.splice(0)) {
        const pal = [["#ff2d95", "#7a1cff"], ["#00e5ff", "#1f6bff"], ["#ffd23f", "#ff7a1a"], ["#ff4d6d", "#ff9fb4"], ["#7cff6b", "#00b3a4"]][Math.floor(r() * 5)];
        billboard(c, s.x, s.y, s.w, s.h, {
          from: pal[0], to: pal[1], glow: pal[0], alpha: s.a,
          content: (c2, x, y, w, h) => {
            c2.fillStyle = "rgba(255,255,255,.6)";
            if (r() < 0.5) { c2.beginPath(); c2.arc(x + w * 0.25, y + h * 0.5, h * 0.3, 0, 7); c2.fill(); }
            for (let k = 0; k < 3; k++) c2.fillRect(x + w * 0.45, y + h * (0.22 + k * 0.22), w * lerp(0.2, 0.45, r()), h * 0.1);
          },
        });
        bloom(c, s.x + s.w / 2, s.y + s.h / 2, s.w, "#ff5fa2", 0.12 * s.a);
      }
    };
    const vsigns = (n) => {
      for (let i = 0; i < n; i++) {
        const x = r() < 0.5 ? lerp(700, 900, r()) : lerp(1250, 1440, r());
        const txt = KANJI[Math.floor(r() * KANJI.length)], fs = lerp(22, 34, r());
        const y = lerp(460, 760, r()), h = txt.length * fs * 1.15 + 16;
        const col = ["#ff2d95", "#00e5ff", "#ffd23f", "#ff4d6d"][Math.floor(r() * 4)];
        c.save();
        c.fillStyle = "#120d14"; c.fillRect(x - fs * 0.7, y - 8, fs * 1.4, h);
        c.strokeStyle = col; c.lineWidth = 2; c.shadowColor = col; c.shadowBlur = 14; c.strokeRect(x - fs * 0.7, y - 8, fs * 1.4, h);
        c.restore();
        [...txt].forEach((ch, k) => neonText(c, ch, x, y + fs * 0.6 + k * fs * 1.15, { font: `${fs}px "Dela Gothic One"`, color: col, blur: 12 }));
      }
    };
    const WC = ["#ffd79a", "#ffe9c8", "#7ef6ff", "#ffb36b"];

    // distant megastructures + sky-bridge arch across the gap
    cluster({ n: 60, base: 700, hMin: 90, hMax: 330, wMin: 30, wMax: 110, col: mixc(DARK, HAZE, 0.62), lift: 0.25, win: 0.1, wc: WC, ws: [2, 2, 4, 5], gap: true, edge: true });
    c.save(); c.strokeStyle = mixc(DARK, HAZE, 0.6); c.lineWidth = 14;
    c.beginPath(); c.moveTo(760, 560); c.quadraticCurveTo(1080, 470, 1400, 560); c.stroke();
    c.lineWidth = 4;
    for (let x = 800; x < 1380; x += 40) { c.beginPath(); c.moveTo(x, 560 - Math.sin(((x - 760) / 640) * Math.PI) * 45); c.lineTo(x, 700); c.stroke(); }
    c.restore();
    hazeCoat(0.35);
    cluster({ n: 44, base: 760, hMin: 150, hMax: 460, wMin: 50, wMax: 140, col: mixc(DARK, HAZE, 0.45), lift: 0.2, win: 0.16, wc: WC, ws: [3, 3, 5, 6], gap: true, signs: 0.4, signA: 0.65, rim: "#ffcf8a" });
    flushSigns();
    hazeCoat(0.28, 300, 900);
    cluster({ n: 26, base: 860, hMin: 260, hMax: 640, wMin: 80, wMax: 190, col: mixc(DARK, HAZE, 0.24), lift: 0.16, win: 0.2, wc: WC, ws: [4, 5, 7, 9], gap: true, signs: 0.6, signA: 0.9, rim: "#ffc27a" });
    flushSigns();
    vsigns(9);
    if (opts.holo !== false) hologram(c, opts.holoX || 1150, opts.holoY || 250, opts.holoH || 420);
    hazeCoat(0.16, 500, 950);

    // volumetric rays behind the hero towers
    c.save();
    c.globalCompositeOperation = "screen";
    c.filter = "blur(22px)";
    for (let i = 0; i < 12; i++) {
      const a = lerp(1.75, 3.05, r()), sp = lerp(0.015, 0.05, r()), len = 1900;
      c.fillStyle = `rgba(255,210,150,${lerp(0.05, 0.12, r())})`;
      c.beginPath(); c.moveTo(sunX, sunY);
      c.lineTo(sunX + Math.cos(a - sp) * len, sunY + Math.sin(a - sp) * len);
      c.lineTo(sunX + Math.cos(a + sp) * len, sunY + Math.sin(a + sp) * len);
      c.fill();
    }
    c.restore();

    // hero towers
    const NEAR = mixc(DARK, HAZE, 0.08);
    building(c, r, { x: 40, w: 640, top: 40, bottom: H, color: NEAR, haze: HAZE, lift: 0.1, windows: 0.22, winColors: WC, winSize: [6, 8, 10, 14], rim: "#ffc27a", rimSide: 1, crown: false, style: "bands" });
    building(c, r, { x: 680, w: 150, top: 380, bottom: H, color: mixc(DARK, HAZE, 0.14), haze: HAZE, lift: 0.1, windows: 0.3, winColors: WC, winSize: [5, 6, 8, 10], rim: "#ffc27a", rimSide: 1 });
    building(c, r, { x: 1450, w: 300, top: 120, bottom: H, color: NEAR, haze: HAZE, lift: 0.1, windows: 0.24, winColors: WC, winSize: [6, 8, 10, 14], rim: "#ffc27a", rimSide: -1, crown: false, style: "grid" });
    building(c, r, { x: 1750, w: 200, top: 360, bottom: H, color: mixc(DARK, HAZE, 0.12), haze: HAZE, lift: 0.1, windows: 0.3, winColors: WC, winSize: [5, 6, 8, 10], rim: "#ffc27a", rimSide: -1 });
    building(c, r, { x: 1300, w: 150, top: 560, bottom: H, color: mixc(DARK, HAZE, 0.18), haze: HAZE, lift: 0.1, windows: 0.3, winColors: WC, winSize: [4, 5, 7, 8], rim: "#ffc27a", rimSide: -1 });
    c.fillStyle = NEAR; c.fillRect(1300, 640, 460, 34);
    for (let x = 1310; x < 1750; x += 22) glowRect(c, x, 650, 12, 8, "#7ef6ff", 8, 0.8);

    if (opts.hero) opts.hero(c);
    if (opts.sign) opts.sign(c);

    // ground: dusty street, lane lines, guard rail, palms, car, lamp
    const gr = c.createLinearGradient(0, 860, 0, H);
    gr.addColorStop(0, mixc(DARK, HAZE, 0.4)); gr.addColorStop(1, "#1a1310");
    c.fillStyle = gr; c.fillRect(0, 880, W, H - 880);
    c.fillStyle = "rgba(255,190,120,.15)"; c.fillRect(0, 880, W, 3);
    for (let i = 0; i < 18; i++) { c.fillStyle = `rgba(255,200,140,${lerp(0.04, 0.12, r())})`; c.fillRect(r() * W, lerp(900, H, r()), lerp(80, 400, r()), 2); }
    c.save(); c.strokeStyle = "rgba(255,210,150,.22)"; c.lineWidth = 3; c.setLineDash([40, 30]);
    for (const k of [-1, 1]) { c.beginPath(); c.moveTo(sunX + k * 60, 882); c.lineTo(sunX + k * 900, H); c.stroke(); }
    c.restore();
    c.fillStyle = "#1a1310"; c.fillRect(0, 918, 700, 6); c.fillRect(0, 940, 700, 4);
    for (let x = 10; x < 700; x += 70) c.fillRect(x, 912, 6, 50);
    if (opts.spill) for (const [x, col, rad] of opts.spill) bloom(c, x, 940, rad, col, 0.28);
    for (const [x, h, lean] of [[860, 300, -30], [930, 240, 26], [1230, 330, 20], [1330, 260, -24]]) palm(c, x, 900, h, lean, mixc(DARK, HAZE, 0.22));
    if (opts.car !== false) car(c, opts.carX || 1210, 1040, 0.95, "#0c0d12", "#ffc27a");
    c.fillStyle = "#15100e"; c.fillRect(1850, 520, 10, 440); c.fillRect(1790, 520, 70, 8);
    bloom(c, 1796, 530, 90, "#ffd9a0", 0.8); glowRect(c, 1782, 526, 30, 8, "#fff2d6", 20, 1);

    // dust motes
    c.save();
    for (let i = 0; i < 160; i++) {
      const x = r() * W, y = lerp(200, H, r()), sz = lerp(0.8, 3.2, r());
      c.globalAlpha = lerp(0.15, 0.6, r());
      c.fillStyle = "#ffe2b0";
      c.beginPath(); c.arc(x, y, sz, 0, 7); c.fill();
    }
    c.restore();
    return { c, r, sunX, sunY };
  }

  // ---------------------------------------------------------------- STREET
  // One-point-perspective neon street at night: facades both sides with
  // shopfront bays, blade signs facing the camera, cables, lamps, people,
  // cars and a wet road reflecting every light.
  // opts: { seed, vpX, vpY, width, camH, fog, sky, tall, kanji, far(c,P,glows), overhead(c,P,glows), people, cars, rain, rainN }
  function street(target, opts = {}) {
    const c = target.getContext("2d");
    const r = rng(opts.seed || 3);
    const vpX = opts.vpX || 960, vpY = opts.vpY || 560, f = 900;
    const half = opts.width || 8, camH = opts.camH || 3.2;
    const FOG = opts.fog || "#3a1f5c", SKY = opts.sky || ["#05040c", "#1a0f33", "#4a1f5a"];
    const P = (X, Y, Z) => [vpX + (X * f) / Z, vpY + ((camH - Y) * f) / Z];
    const glows = []; // [x, y, colour, size] light sources reflected on the road

    const sky = c.createLinearGradient(0, 0, 0, vpY + 40);
    SKY.forEach((col, i) => sky.addColorStop(i / (SKY.length - 1), col));
    c.fillStyle = sky; c.fillRect(0, 0, W, H);
    bloom(c, vpX, vpY - 40, 520, FOG, 0.8);

    // far city at the end of the street
    for (let i = 0; i < 26; i++) {
      const w = lerp(20, 70, r()), x = vpX + lerp(-260, 260, r()) - w / 2, h = lerp(60, 380, Math.pow(r(), 1.3));
      building(c, r, { x, w, top: vpY - h + 20, bottom: vpY + 30, color: mixc("#0a0812", FOG, 0.55), haze: FOG, lift: 0.2, windows: 0.2, winColors: ["#ff9ad5", "#9ae8ff", "#ffe3a0"], winSize: [2, 2, 3, 4] });
    }
    c.fillStyle = rgba(FOG, 0.18); c.fillRect(0, 0, W, H);
    if (opts.far) opts.far(c, P, glows);

    // road
    const road = c.createLinearGradient(0, vpY, 0, H);
    road.addColorStop(0, mixc("#08070d", FOG, 0.5)); road.addColorStop(1, "#050409");
    c.fillStyle = road; c.fillRect(0, vpY + 20, W, H);

    // facade segments, drawn far → near
    const segs = [];
    for (const side of [-1, 1]) {
      let z = 9;
      while (z < 150) {
        const len = lerp(6, 16, r());
        segs.push({ side, z0: z, z1: z + len, h: lerp(12, 34, r()) * (opts.tall || 1), col: mixc("#0c0a14", FOG, lerp(0.05, 0.2, r())) });
        z += len;
      }
    }
    segs.sort((a, b) => b.z0 - a.z0);
    const quad = (Xa, Ya, Za, Yb, Zb) => {
      const [a1, b1] = P(Xa, Ya, Za), [, b1t] = P(Xa, Yb, Za), [a2, b2] = P(Xa, Ya, Zb), [, b2t] = P(Xa, Yb, Zb);
      c.beginPath(); c.moveTo(a1, b1); c.lineTo(a1, b1t); c.lineTo(a2, b2t); c.lineTo(a2, b2); c.closePath();
    };
    const blades = [];
    for (const s of segs) {
      const X = s.side * half;
      const [x0, y0b] = P(X, 0, s.z0), [, y0t] = P(X, s.h, s.z0);
      const [x1, y1b] = P(X, 0, s.z1), [, y1t] = P(X, s.h, s.z1);
      const fogA = Math.min(0.85, s.z0 / 170);
      const fg = c.createLinearGradient(0, Math.min(y0t, y1t), 0, y0b);
      fg.addColorStop(0, mixc(s.col, FOG, Math.min(0.9, fogA * 0.7 + 0.12)));
      fg.addColorStop(1, mixc(s.col, "#000000", 0.3));
      c.fillStyle = fg;
      c.beginPath(); c.moveTo(x0, y0b); c.lineTo(x0, y0t); c.lineTo(x1, y1t); c.lineTo(x1, y1b); c.closePath(); c.fill();
      // side wall facing the far end
      c.fillStyle = mixc(s.col, FOG, fogA * 0.5);
      const [ex] = P(X + s.side * 12, 0, s.z1);
      c.beginPath(); c.moveTo(x1, y1b); c.lineTo(x1, y1t); c.lineTo(ex, y1t); c.lineTo(ex, y1b); c.closePath(); c.fill();
      // floor lines
      c.strokeStyle = "rgba(255,255,255,.035)"; c.lineWidth = 1;
      for (let fl = 1; fl < s.h / 3; fl++) { const [a1, b1] = P(X, fl * 3, s.z0), [a2, b2] = P(X, fl * 3, s.z1); c.beginPath(); c.moveTo(a1, b1); c.lineTo(a2, b2); c.stroke(); }
      // lit windows
      for (let fl = 2; fl < s.h / 3; fl++) {
        for (let k = 0; k < 6; k++) {
          if (r() > 0.2) continue;
          const zA = lerp(s.z0, s.z1, k / 6 + 0.02), zB = lerp(s.z0, s.z1, (k + 0.6) / 6);
          c.fillStyle = rgba(["#ffcf8a", "#9ae8ff", "#ff9ad5", "#ffe6b0"][Math.floor(r() * 4)], lerp(0.12, 0.5, r()) * (1 - fogA * 0.6));
          quad(X, fl * 3 + 0.8, zA, fl * 3 + 2, zB); c.fill();
        }
      }
      // shopfronts: 2–3 bays with lit glass, interior shapes and pillars
      const bays = 2 + Math.floor(r() * 2);
      for (let k = 0; k < bays; k++) {
        const za = lerp(s.z0, s.z1, k / bays) + 0.35, zb = lerp(s.z0, s.z1, (k + 1) / bays) - 0.35;
        const tint = ["#ff2d6f", "#ffb347", "#27e1ff", "#ff5ac8", "#ffe6b0"][Math.floor(r() * 5)];
        const lit = r() < 0.75;
        const [, gy0] = P(X, 2.5, za), [, gy1] = P(X, 0.2, za);
        const gl = c.createLinearGradient(0, gy0, 0, gy1);
        gl.addColorStop(0, rgba(tint, lit ? 0.5 * (1 - fogA * 0.6) : 0.05));
        gl.addColorStop(1, rgba(tint, lit ? 0.14 : 0.02));
        c.fillStyle = gl; quad(X, 0.2, za, 2.5, zb); c.fill();
        if (lit) {
          c.fillStyle = "rgba(10,6,16,.55)";
          quad(X, 0.2, lerp(za, zb, 0.15), 1.1, lerp(za, zb, 0.45)); c.fill();
          quad(X, 0.2, lerp(za, zb, 0.6), 1.7, lerp(za, zb, 0.7)); c.fill();
        }
        c.fillStyle = mixc(s.col, "#000000", 0.4);
        quad(X, 0, zb, 3.2, zb + 0.7); c.fill();
        glows.push([...P(X, 1.2, (za + zb) / 2), tint, Math.abs(P(X, 0, zb)[0] - P(X, 0, za)[0]) * (lit ? 0.5 : 0.1)]);
      }
      // neon awning line
      const sf = ["#ff2d6f", "#ffb347", "#27e1ff", "#ff5ac8"][Math.floor(r() * 4)];
      const [s1x] = P(X, 0, s.z0 + 0.5), [s2x] = P(X, 0, s.z1 - 0.5);
      const [, a1t] = P(X, 3.0, s.z0 + 0.5), [, a2t] = P(X, 3.0, s.z1 - 0.5);
      c.save(); c.shadowColor = sf; c.shadowBlur = 12; c.strokeStyle = sf; c.lineWidth = Math.max(1, 90 / s.z0);
      c.beginPath(); c.moveTo(s1x, a1t); c.lineTo(s2x, a2t); c.stroke(); c.restore();
      glows.push([(s1x + s2x) / 2, (a1t + a2t) / 2, sf, Math.abs(s2x - s1x) * 0.3]);
      for (let k = 0; k < 2; k++) if (r() < 0.8) blades.push({ side: s.side, z: lerp(s.z0, s.z1, lerp(0.15, 0.85, r())), y: lerp(4.5, Math.min(s.h - 2, 18), r()), fogA });
    }

    // blade signs (planes facing the camera), far → near
    const WORDS = opts.kanji || ["酒", "夜市", "電脳", "ラーメン", "ホテル", "営業中", "月", "BAR", "OPEN", "24H", "CLUB"];
    const COLS = ["#ff2d6f", "#27e1ff", "#ffd23f", "#ff5ac8", "#7cff6b", "#ff8a3d"];
    blades.sort((a, b) => b.z - a.z);
    for (const b of blades) {
      const txt = WORDS[Math.floor(r() * WORDS.length)], col = COLS[Math.floor(r() * COLS.length)];
      const vertical = !/^[A-Z0-9]/.test(txt) || r() < 0.4;
      const [x, y] = P(b.side * (half - 0.3), b.y, b.z);
      const sc = f / b.z, cell = 0.9 * sc, n = [...txt].length, a = 1 - b.fogA * 0.75;
      const w = vertical ? cell * 1.3 : cell * (n * 0.8 + 0.8), h = vertical ? cell * (n * 1.1 + 0.4) : cell * 1.4;
      const bx = b.side < 0 ? x : x - w;
      c.save();
      c.globalAlpha = a;
      c.fillStyle = "#0b0810"; c.fillRect(bx, y - h, w, h);
      c.shadowColor = col; c.shadowBlur = Math.max(6, sc * 0.5);
      c.strokeStyle = col; c.lineWidth = Math.max(1, sc * 0.05); c.strokeRect(bx, y - h, w, h);
      c.restore();
      if (vertical) [...txt].forEach((ch, k) => neonText(c, ch, bx + w / 2, y - h + cell * (0.75 + k * 1.1), { font: `${cell * 0.85}px "Dela Gothic One"`, color: col, blur: Math.max(4, sc * 0.4), alpha: a }));
      else neonText(c, txt, bx + w / 2, y - h / 2, { font: `700 ${cell * 0.9}px "Chakra Petch"`, color: col, blur: Math.max(4, sc * 0.4), alpha: a });
      glows.push([bx + w / 2, y - h / 2, col, w * 1.4]);
    }

    // power cables sagging across the street
    c.save(); c.strokeStyle = "rgba(5,4,8,.9)";
    for (let i = 0; i < 9; i++) {
      const Z = lerp(12, 90, r()), Y = lerp(9, 16, r()), [ax, ay] = P(-half, Y, Z), [bx, by] = P(half, Y + lerp(-2, 2, r()), Z * lerp(0.8, 1.2, r()));
      c.lineWidth = Math.max(1, 40 / Z);
      c.beginPath(); c.moveTo(ax, ay); c.quadraticCurveTo((ax + bx) / 2, Math.max(ay, by) + (900 / Z) * 1.4, bx, by); c.stroke();
    }
    c.restore();

    if (opts.overhead) opts.overhead(c, P, glows);

    // street lamps
    for (const side of [-1, 1]) for (let z = 10; z < 120; z += 18) {
      const [bx, by] = P(side * (half - 1), 0, z), [tx, ty] = P(side * (half - 1), 6, z), [hx] = P(side * (half - 2.2), 6, z);
      c.strokeStyle = "#0a0810"; c.lineWidth = Math.max(1, (30 / z) * 3);
      c.beginPath(); c.moveTo(bx, by); c.lineTo(tx, ty); c.lineTo(hx, ty); c.stroke();
      bloom(c, hx, ty + 4, (900 / z) * 1.6, "#ffc988", 0.35);
      glowRect(c, hx - (900 / z) * 0.25, ty, (900 / z) * 0.5, Math.max(1, (900 / z) * 0.08), "#fff0d0", 10, 1);
      glows.push([hx, ty, "#ffc988", (900 / z) * 3]);
    }

    // people on the sidewalks
    const person = (X, Z, hgt) => {
      const [x, y] = P(X, 0, Z), sc = f / Z, hh = hgt * sc, ww = hh * 0.28;
      c.fillStyle = "#07060b";
      c.beginPath(); c.ellipse(x, y - hh + ww * 0.45, ww * 0.34, ww * 0.42, 0, 0, 7); c.fill();
      c.beginPath(); c.moveTo(x - ww * 0.5, y - hh * 0.8); c.lineTo(x + ww * 0.5, y - hh * 0.8); c.lineTo(x + ww * 0.36, y - hh * 0.38); c.lineTo(x + ww * 0.2, y); c.lineTo(x - ww * 0.2, y); c.lineTo(x - ww * 0.36, y - hh * 0.38); c.closePath(); c.fill();
      if (r() < 0.35) { c.fillStyle = "rgba(20,18,30,.95)"; c.beginPath(); c.ellipse(x, y - hh * 1.02, ww * 1.1, ww * 0.22, 0, Math.PI, 0); c.fill(); c.fillRect(x - 0.8, y - hh * 1.02, 1.6, hh * 0.5); }
    };
    const ppl = [];
    for (let i = 0; i < (opts.people || 40); i++) ppl.push([(r() < 0.5 ? -1 : 1) * lerp(half - 3.2, half - 0.8, r()), lerp(9, 90, Math.pow(r(), 0.8)), lerp(1.6, 1.85, r())]);
    ppl.sort((a, b) => b[1] - a[1]).forEach(([X, Z, hh]) => person(X, Z, hh));

    // cars: tail lights going away, headlights coming
    const cars = (opts.cars || [[2.5, 26, "tail"], [2.8, 55, "tail"], [-2.6, 40, "head"], [-2.4, 80, "head"], [2.2, 100, "tail"]]).slice();
    for (const [X, Z, kind] of cars.sort((a, b) => b[1] - a[1])) {
      const [x, y] = P(X, 0, Z), sc = f / Z, w = 2.0 * sc, h = 1.3 * sc;
      c.fillStyle = "#0a0910";
      c.beginPath();
      c.moveTo(x - w / 2, y - h * 0.12); c.lineTo(x - w / 2, y - h * 0.5); c.lineTo(x - w * 0.36, y - h * 0.58);
      c.lineTo(x - w * 0.28, y - h * 0.95); c.lineTo(x + w * 0.28, y - h * 0.95); c.lineTo(x + w * 0.36, y - h * 0.58);
      c.lineTo(x + w / 2, y - h * 0.5); c.lineTo(x + w / 2, y - h * 0.12); c.closePath(); c.fill();
      c.fillRect(x - w * 0.46, y - h * 0.14, w * 0.16, h * 0.14); c.fillRect(x + w * 0.3, y - h * 0.14, w * 0.16, h * 0.14);
      c.fillStyle = "rgba(160,200,255,.10)";
      c.beginPath(); c.moveTo(x - w * 0.25, y - h * 0.9); c.lineTo(x + w * 0.25, y - h * 0.9); c.lineTo(x + w * 0.31, y - h * 0.62); c.lineTo(x - w * 0.31, y - h * 0.62); c.closePath(); c.fill();
      const col = kind === "tail" ? "#ff2a3c" : "#fff4dc";
      if (kind === "tail") glowRect(c, x - w * 0.46, y - h * 0.5, w * 0.92, h * 0.05, col, sc * 0.5, 0.9);
      for (const k of [-1, 1]) glowRect(c, x + k * w * 0.36 - w * 0.09, y - h * 0.52, w * 0.18, h * 0.09, col, sc * 0.6, 1);
      bloom(c, x, y - h * 0.46, w * 0.9, col, kind === "tail" ? 0.35 : 0.5);
      glows.push([x - w * 0.36, y - h * 0.46, col, w * 0.3], [x + w * 0.36, y - h * 0.46, col, w * 0.3]);
    }

    // road markings
    c.save(); c.strokeStyle = "rgba(255,210,120,.35)";
    for (let z = 8; z < 140; z += 7) { const [a, b] = P(0, 0, z), [a2, b2] = P(0, 0, z + 3); c.lineWidth = Math.max(1, 60 / z); c.beginPath(); c.moveTo(a, b); c.lineTo(a2, b2); c.stroke(); }
    c.restore();

    // wet reflections: soft colour streaks below every light
    c.save();
    c.globalCompositeOperation = "lighter";
    c.filter = "blur(5px)";
    for (const [x, y, col, size] of glows) {
      const groundY = Math.max(vpY + 24, y);
      const len = Math.min(H - groundY, (groundY - vpY) * 2.2 + 30);
      const g = c.createLinearGradient(0, groundY, 0, groundY + len);
      g.addColorStop(0, rgba(col, 0.3)); g.addColorStop(0.5, rgba(col, 0.12)); g.addColorStop(1, rgba(col, 0));
      c.fillStyle = g;
      const sw = Math.min(size * 0.5, 120);
      c.fillRect(x - sw / 2, groundY, sw, len);
      c.fillRect(x - sw * 0.1, groundY, sw * 0.2, len * 1.2);
    }
    c.restore();

    // puddles
    c.save(); c.globalCompositeOperation = "lighter";
    for (let i = 0; i < 26; i++) {
      const Z = lerp(14, 70, r()), X = lerp(-half + 1, half - 1, r()), [x, y] = P(X, 0, Z), sc = f / Z;
      const col = ["#ff2d6f", "#27e1ff", "#ff5ac8", "#ffc988"][Math.floor(r() * 4)];
      const rx = sc * lerp(0.6, 1.8, r()), ry = sc * lerp(0.06, 0.14, r());
      const pg = c.createRadialGradient(x, y, 0, x, y, rx);
      pg.addColorStop(0, rgba(col, lerp(0.1, 0.22, r()))); pg.addColorStop(1, rgba(col, 0));
      c.fillStyle = pg;
      c.beginPath(); c.ellipse(x, y, rx, ry, 0, 0, 7); c.fill();
    }
    c.restore();

    if (opts.rain !== false) rain(c, r, opts.rainN || 900, { alpha: [0.06, 0.22] });
    return { c, r, P, glows };
  }

  return { W, H, rng, lerp, mixc, rgba, canvas, neonText, glowRect, bloom, postBloom, grain, vignette, rain, building, billboard, palm, car, hologram, skyline, street };
})();
