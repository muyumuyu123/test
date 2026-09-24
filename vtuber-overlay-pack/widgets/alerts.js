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
