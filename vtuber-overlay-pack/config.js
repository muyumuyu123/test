// ✦ Starlight Dreams — your settings ✦
// Edit the values below, save, then right-click the source in OBS and
// choose "Refresh" (or tick "Refresh browser when scene becomes active").
// Keep the quotes and commas as they are.

window.OVERLAY_CONFIG = {
  // Color preset: "midnight" (lavender & gold), "sakura" (pink dusk), "aurora" (mint & teal)
  theme: "midnight",

  // Your name as it appears on the overlays
  name: "Nova Moonpetal",

  // Shown on the starting / ending screens and the game frame
  streamTitle: "Cozy late-night gaming ☾",

  // Up to 5 links. `label` is the small colored word, `handle` is the text next to it.
  socials: [
    { label: "twitch", handle: "twitch.tv/novamoonpetal" },
    { label: "youtube", handle: "@NovaMoonpetal" },
    { label: "x", handle: "@nova_moonpetal" },
  ],

  // Turn the animated background stars and shooting stars on/off
  stars: true,
  shootingStars: true,

  startingSoon: {
    heading: "Starting Soon",
    subheading: "grab a snack & get comfy",
    // Countdown length in minutes, counted from when the scene loads...
    countdownMinutes: 5,
    // ...or a fixed clock time like "20:00" (24h, your computer's time). Overrides the minutes.
    startAt: "",
    doneText: "any second now ✦",
  },

  brb: {
    heading: "Be Right Back",
    subheading: "the moon is taking a tiny nap",
    showAwayTimer: true,
  },

  ending: {
    heading: "Thanks for Watching!",
    subheading: "sweet dreams, see you next stream",
    // e.g. "raiding @friend next!"  — leave empty to hide
    note: "",
  },

  alerts: {
    // Seconds each alert stays on screen
    duration: 6,
    // Symbol put in front of tip amounts
    currency: "$",
    // Plays a sound from this file when an alert appears (leave "" for silent).
    // Put the file next to this config, e.g. "chime.mp3".
    sound: "",
    volume: 0.5,
    labels: {
      follow: "New Follower",
      sub: "New Subscriber",
      tip: "New Tip",
      cheer: "Cheer",
      raid: "Incoming Raid",
      member: "New Member",
    },
  },

  chat: {
    // Your Twitch channel name (lowercase, no URL). Leave "" to show demo messages.
    twitchChannel: "",
    maxMessages: 8,
    // Hide each message after this many seconds (0 = never)
    fadeAfter: 0,
    hideCommands: true, // hide messages starting with "!"
    hideUsers: ["nightbot", "streamelements", "streamlabs", "moobot"],
  },

  goal: {
    title: "Follower Goal",
    current: 742,
    target: 1000,
    // Text shown after the numbers, e.g. "followers", "subs", "$"
    unit: "",
  },
};
