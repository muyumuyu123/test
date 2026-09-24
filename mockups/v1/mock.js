// Fills the component strip of a mockup from window.MOCK
(function () {
  const m = Object.assign(
    {
      theme: "",
      kind: "New Follower",
      who: "StarryMochi",
      amount: "",
      badge: '<svg viewBox="0 0 64 64"><path d="M32 56S6 40 6 22A13 13 0 0 1 32 15a13 13 0 0 1 26 7c0 18-26 34-26 34z" fill="currentColor"/></svg>',
      live: "LIVE",
      name: "Nova Moonpetal",
      goalTitle: "Follower Goal",
      goal: "742 / 1,000",
      pct: 74,
      chat: [
        ["StarryMochi", "good evening!!"],
        ["moonlit_kay", "this overlay goes so hard"],
        ["pixelpudding", "is the countdown live?"],
      ],
    },
    window.MOCK || {}
  );
  const strip = document.querySelector(".strip");
  const esc = (s) => String(s).replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c]);
  strip.innerHTML = `
    <span class="tag">Mockup · ${esc(m.theme)} · components</span>
    <div class="cell">
      <div class="m-alert">
        <div class="m-badge">${m.badge}</div>
        <div class="m-card">
          <div class="m-kind">${esc(m.kind)}</div>
          <div class="m-who">${esc(m.who)}</div>
          ${m.amount ? `<div class="m-amt">${esc(m.amount)}</div>` : ""}
        </div>
      </div>
    </div>
    <div class="cell">
      <div class="m-plate"><span class="m-live">${esc(m.live)}</span><span class="m-name">${esc(m.name)}</span></div>
      <div class="m-goal">
        <div class="m-goal-top"><span class="m-goal-title">${esc(m.goalTitle)}</span><span class="m-goal-num">${esc(m.goal)}</span></div>
        <div class="m-track"><div class="m-fill" style="width:${m.pct}%"></div></div>
      </div>
    </div>
    <div class="cell">
      <div class="m-chat">${m.chat.map(([u, t]) => `<div class="m-msg"><b>${esc(u)}</b><span>${esc(t)}</span></div>`).join("")}</div>
    </div>`;
})();
