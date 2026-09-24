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
