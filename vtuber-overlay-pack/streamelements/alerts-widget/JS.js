// Starlight Dreams alert box — built from widgets/alerts.js. Settings live in the Fields panel.

window.OVERLAY_CONFIG = { theme: 'midnight' };

// Starlight Dreams — shared runtime. Loaded after config.js by every page.
// Exposes window.SD with helpers the individual scenes/widgets use.
(function () {
  "use strict";

  const DEFAULTS = {
    theme: "midnight",
    name: "",
    streamTitle: "",
    socials: [],
    stars: true,
    shootingStars: true,
    startingSoon: { heading: "Starting Soon", subheading: "", countdownMinutes: 5, startAt: "", doneText: "any second now" },
    brb: { heading: "Be Right Back", subheading: "", showAwayTimer: true },
    ending: { heading: "Thanks for Watching!", subheading: "", note: "" },
    alerts: {
      duration: 6,
      currency: "$",
      sound: "",
      volume: 0.5,
      labels: { follow: "New Follower", sub: "New Subscriber", tip: "New Tip", cheer: "Cheer", raid: "Incoming Raid", member: "New Member" },
    },
    chat: { twitchChannel: "", maxMessages: 8, fadeAfter: 0, hideCommands: true, hideUsers: [] },
    goal: { title: "Goal", current: 0, target: 100, unit: "" },
  };

  function merge(base, over) {
    if (Array.isArray(base) || typeof base !== "object" || base === null) {
      return over === undefined ? base : over;
    }
    const out = { ...base };
    for (const key of Object.keys(over || {})) {
      out[key] = key in base ? merge(base[key], over[key]) : over[key];
    }
    return out;
  }

  const cfg = merge(DEFAULTS, window.OVERLAY_CONFIG || {});
  const params = new URLSearchParams(location.search);

  // URL parameters win over config.js, e.g. starting-soon.html?theme=sakura
  if (params.get("theme")) cfg.theme = params.get("theme");
  if (params.get("name")) cfg.name = params.get("name");
  if (params.get("channel")) cfg.chat.twitchChannel = params.get("channel");
  if (params.get("minutes")) cfg.startingSoon.countdownMinutes = Number(params.get("minutes"));

  document.documentElement.dataset.theme = cfg.theme;

  // "still" freezes random layout + disables shooting stars, used for product screenshots
  const still = params.has("still");

  function get(path) {
    return path.split(".").reduce((obj, key) => (obj == null ? undefined : obj[key]), cfg);
  }

  // <span data-cfg="brb.heading"></span> is filled from the config.
  // Empty values hide the element, or its nearest [data-cfg-group] wrapper.
  function bindText(root = document) {
    root.querySelectorAll("[data-cfg]").forEach((el) => {
      const value = get(el.dataset.cfg);
      el.textContent = value == null ? "" : String(value);
      (el.closest("[data-cfg-group]") || el).classList.toggle("is-empty", !value);
    });
  }

  function renderSocials(container, list = cfg.socials) {
    container.textContent = "";
    for (const s of list.slice(0, 5)) {
      const pill = document.createElement("span");
      pill.className = "pill";
      const label = document.createElement("span");
      label.className = "label";
      label.textContent = s.label;
      const handle = document.createElement("span");
      handle.textContent = s.handle;
      pill.append(label, handle);
      container.append(pill);
    }
  }

  function pad(n) {
    return String(n).padStart(2, "0");
  }

  function formatTime(totalSeconds) {
    const s = Math.max(0, Math.floor(totalSeconds));
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    return h > 0 ? `${h}:${pad(m)}:${pad(sec)}` : `${pad(m)}:${pad(sec)}`;
  }

  // Small deterministic RNG so layouts look the same on every load
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

  function cssVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  // Twinkling stars + the occasional shooting star, drawn on a <canvas>.
  function starfield(canvas, opts = {}) {
    if (!cfg.stars) {
      canvas.remove();
      return;
    }
    const ctx = canvas.getContext("2d");
    const W = (canvas.width = opts.width || 1920);
    const H = (canvas.height = opts.height || 1080);
    const rand = rng(opts.seed || 7);
    const count = opts.count || 220;
    const starColor = cssVar("--star") || "#fff";
    const accent = cssVar("--accent") || "#ffd98a";

    const stars = Array.from({ length: count }, () => {
      const big = rand() < 0.07;
      return {
        x: rand() * W,
        y: Math.pow(rand(), 1.3) * H * (opts.maxY || 0.85),
        r: big ? 2.2 + rand() * 1.6 : 0.5 + rand() * 1.2,
        big,
        phase: rand() * Math.PI * 2,
        speed: 0.6 + rand() * 1.8,
        color: big && rand() < 0.5 ? accent : starColor,
      };
    });

    let shooting = null;
    let nextShot = 2 + rand() * 4;

    function drawSparkle(x, y, r, alpha, color) {
      ctx.globalAlpha = alpha;
      ctx.fillStyle = color;
      ctx.beginPath();
      const len = r * 4;
      ctx.moveTo(x, y - len);
      ctx.quadraticCurveTo(x, y, x + len, y);
      ctx.quadraticCurveTo(x, y, x, y + len);
      ctx.quadraticCurveTo(x, y, x - len, y);
      ctx.quadraticCurveTo(x, y, x, y - len);
      ctx.fill();
      ctx.globalAlpha = alpha * 0.35;
      ctx.beginPath();
      ctx.arc(x, y, r * 2.2, 0, Math.PI * 2);
      ctx.fill();
    }

    function frame(ms) {
      const t = ms / 1000;
      ctx.clearRect(0, 0, W, H);
      for (const s of stars) {
        const tw = 0.55 + 0.45 * Math.sin(t * s.speed + s.phase);
        if (s.big) {
          drawSparkle(s.x, s.y, s.r, tw, s.color);
        } else {
          ctx.globalAlpha = 0.25 + tw * 0.75;
          ctx.fillStyle = s.color;
          ctx.beginPath();
          ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
          ctx.fill();
        }
      }

      if (cfg.shootingStars && !still) {
        if (!shooting && t > nextShot) {
          shooting = {
            x: W * (0.2 + Math.random() * 0.7),
            y: H * Math.random() * 0.3,
            vx: -(900 + Math.random() * 500),
            vy: 380 + Math.random() * 220,
            born: t,
            life: 0.9 + Math.random() * 0.5,
          };
        }
        if (shooting) {
          const age = t - shooting.born;
          if (age > shooting.life) {
            shooting = null;
            nextShot = t + 5 + Math.random() * 9;
          } else {
            const hx = shooting.x + shooting.vx * age;
            const hy = shooting.y + shooting.vy * age;
            const tail = 0.18;
            const tx = hx - shooting.vx * tail;
            const ty = hy - shooting.vy * tail;
            const fade = Math.sin((age / shooting.life) * Math.PI);
            const grad = ctx.createLinearGradient(hx, hy, tx, ty);
            grad.addColorStop(0, starColor);
            grad.addColorStop(1, "rgba(255,255,255,0)");
            ctx.globalAlpha = fade;
            ctx.strokeStyle = grad;
            ctx.lineWidth = 2.5;
            ctx.lineCap = "round";
            ctx.beginPath();
            ctx.moveTo(hx, hy);
            ctx.lineTo(tx, ty);
            ctx.stroke();
            drawSparkle(hx, hy, 1.4, fade, starColor);
          }
        }
      }
      ctx.globalAlpha = 1;
      requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  // Standard cloud band markup, shared by the three full-screen scenes
  function clouds(container) {
    container.innerHTML = `
      <svg viewBox="0 0 2300 320" preserveAspectRatio="none" aria-hidden="true">
        <path class="back" d="M0 200 C120 120 260 150 330 190 C400 110 560 100 640 180 C720 120 880 110 960 190 C1060 100 1220 120 1290 190 C1380 110 1540 110 1620 190 C1700 130 1860 120 1940 190 C2020 120 2200 130 2300 190 L2300 320 L0 320 Z"/>
        <path class="front" d="M0 250 C100 190 240 200 300 240 C380 170 520 180 580 245 C660 185 800 180 880 245 C960 180 1120 190 1180 250 C1260 180 1420 185 1480 245 C1560 190 1700 185 1780 245 C1860 190 2020 190 2080 250 C2160 200 2260 205 2300 240 L2300 320 L0 320 Z"/>
      </svg>`;
  }

  function onReady(fn) {
    const run = () => (document.fonts ? document.fonts.ready.then(fn) : fn());
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", run);
    else run();
  }

  window.SD = { cfg, params, still, get, bindText, renderSocials, formatTime, rng, cssVar, starfield, clouds, onReady };
})();


// Starlight Dreams — alert box logic.
// Alerts can come from:
//   • StreamElements (when pasted into a Custom Widget) via onEventReceived
//   • the demo loop:           alerts.html?demo
//   • your own code:           window.showAlert({ type: "tip", name: "Mika", amount: 5, message: "hi!" })
//   • render mode (one frozen alert for exporting video): alerts.html?render=follow
(function () {
  "use strict";
  const { cfg, params, rng } = SD;
  const opts = cfg.alerts;
  let duration = Number(opts.duration) || 6;

  const ICONS = {
    heart: '<path d="M32 56S6 40 6 22A13 13 0 0 1 32 15a13 13 0 0 1 26 7c0 18-26 34-26 34z"/>',
    moon: '<path d="M40 6a26 26 0 1 0 18 44A22 22 0 0 1 40 6z"/>',
    star: '<path d="M32 4l8.2 17.5 19 2.3-14 13.1 3.7 18.9L32 46.4 15.1 55.8l3.7-18.9-14-13.1 19-2.3z"/>',
    sparkle: '<path d="M32 2C34 22 42 30 62 32 42 34 34 42 32 62 30 42 22 34 2 32 22 30 30 22 32 2z"/>',
    comet: '<circle cx="42" cy="22" r="14"/><path d="M32 12 4 60 52 32z"/>',
    crown: '<path d="M6 20l14 12 12-20 12 20 14-12-6 32H12z"/><rect x="12" y="54" width="40" height="6" rx="2"/>',
  };

  // 5 → "5", 4.5 → "4.50", 25000 → "25,000"
  function money(n) {
    return Number.isInteger(n) ? n.toLocaleString() : n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  const TYPES = {
    follow: { icon: "heart" },
    sub: { icon: "moon", amount: (n) => (n > 1 ? `${n} months` : "") },
    member: { icon: "crown", amount: (n) => (n > 1 ? `${n} months` : "") },
    tip: { icon: "star", amount: (n) => (n ? `${opts.currency}${money(Number(n))}` : "") },
    cheer: { icon: "sparkle", amount: (n) => (n ? `${n} bits` : "") },
    raid: { icon: "comet", amount: (n) => (n ? `${n} raiders` : "") },
  };

  const stage = document.getElementById("stage");
  const queue = [];
  let busy = false;

  function el(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text != null) node.textContent = text;
    return node;
  }

  function build(evt) {
    const type = TYPES[evt.type] ? evt.type : "follow";
    const def = TYPES[type];
    const root = el("div", `alert type-${type}`);
    root.style.setProperty("--dur", `${duration}s`);

    const badge = el("div", "badge");
    badge.innerHTML = `<svg viewBox="0 0 64 64" aria-hidden="true">${ICONS[def.icon]}</svg>`;

    const card = el("div", "panel starred card");
    const kind = el("div", "kind");
    kind.append(el("i", "sparkle"), el("span", "", opts.labels[type] || type), el("i", "sparkle"));
    card.append(kind);
    card.append(el("div", "who display shimmer-text", evt.name || "Someone"));
    const amount = def.amount ? def.amount(evt.amount) : "";
    if (amount) card.append(el("div", "amount", amount));
    if (evt.message) card.append(el("div", "msg", evt.message));

    // Sparkle burst, same pattern every time
    const burst = el("div", "burst");
    const rand = rng(3);
    for (let i = 0; i < 16; i++) {
      const a = (i / 16) * Math.PI * 2 + rand() * 0.3;
      const dist = 130 + rand() * 170;
      const s = el("i");
      s.style.setProperty("--x", `${Math.cos(a) * dist * 1.4}px`);
      s.style.setProperty("--y", `${Math.sin(a) * dist}px`);
      s.style.setProperty("--s", `${10 + rand() * 18}px`);
      s.style.setProperty("--d", `${0.15 + rand() * 0.25}s`);
      if (i % 3 === 0) s.style.setProperty("--c", "var(--primary)");
      burst.append(s);
    }

    root.append(badge, card, burst);
    return root;
  }

  function playSound() {
    if (!opts.sound) return;
    const src = /^(https?:|file:|\/)/.test(opts.sound) ? opts.sound : `../${opts.sound}`;
    const audio = new Audio(src);
    audio.volume = Math.max(0, Math.min(1, Number(opts.volume)));
    audio.play().catch(() => {});
  }

  function next() {
    const evt = queue.shift();
    if (!evt) {
      busy = false;
      return;
    }
    busy = true;
    const node = build(evt);
    stage.append(node);
    playSound();
    setTimeout(() => {
      node.remove();
      setTimeout(next, 400);
    }, duration * 1000);
  }

  function showAlert(evt) {
    queue.push(evt);
    if (!busy) next();
  }
  window.showAlert = showAlert;

  // --- StreamElements custom widget events ---
  const SE_TYPES = {
    "follower-latest": "follow",
    "subscriber-latest": "sub",
    "tip-latest": "tip",
    "cheer-latest": "cheer",
    "raid-latest": "raid",
    "sponsor-latest": "member", // YouTube members
  };
  window.addEventListener("onEventReceived", (obj) => {
    const { listener, event } = obj.detail || {};
    const type = SE_TYPES[listener];
    if (!type || !event) return;
    showAlert({ type, name: event.name, amount: event.amount, message: event.message });
  });
  window.addEventListener("onWidgetLoad", (obj) => {
    const f = (obj.detail && obj.detail.fieldData) || {};
    if (f.theme) document.documentElement.dataset.theme = f.theme;
    if (f.duration) duration = Number(f.duration);
    if (f.currency) opts.currency = f.currency;
    if (f.sound) opts.sound = f.sound;
    if (f.volume != null) opts.volume = Number(f.volume) / 100;
    for (const key of Object.keys(opts.labels)) {
      if (f[`label_${key}`]) opts.labels[key] = f[`label_${key}`];
    }
  });

  // --- Demo / render modes ---
  const SAMPLES = [
    { type: "follow", name: "StarryMochi" },
    { type: "sub", name: "moonlit_kay", amount: 6, message: "six months already?! love these cozy streams" },
    { type: "tip", name: "Hanabi", amount: 5, message: "for your tea fund ☕" },
    { type: "cheer", name: "pixelpudding", amount: 500, message: "Cheer500 goodnight!" },
    { type: "raid", name: "CometCat", amount: 42 },
    { type: "member", name: "Sora Nakamura" },
  ];

  const render = params.get("render");
  if (render) {
    document.body.classList.toggle("bare", params.has("bare"));
    const sample = SAMPLES.find((s) => s.type === render) || { type: render, name: "Username" };
    stage.append(build(sample));
  } else if (params.has("demo")) {
    let i = 0;
    const loop = () => {
      showAlert(SAMPLES[i++ % SAMPLES.length]);
      setTimeout(loop, (duration + 1.5) * 1000);
    };
    loop();
  }
})();
