# ✦ Starlight Dreams — Animated VTuber Overlay Pack ✦

A cozy night-sky overlay pack: twinkling stars, shooting stars, a sleepy crescent moon and soft drifting clouds. Everything is animated in real time, fully editable, and comes in three color themes.

| Theme | Colors |
|---|---|
| **Midnight** | deep indigo, lavender, moon gold |
| **Sakura** | dusk plum, cherry pink, peach |
| **Aurora** | night teal, mint, ice blue |

## What's inside

| File | What it is | Browser Source size |
|---|---|---|
| `scenes/starting-soon.html` | Starting screen with a live countdown | 1920 × 1080 |
| `scenes/brb.html` | Be Right Back with a snoozing moon and an "away for" timer | 1920 × 1080 |
| `scenes/ending.html` | Thanks for watching, socials, optional raid note | 1920 × 1080 |
| `overlays/game-frame.html` | Transparent frame: game window, chat box, name plate, rotating socials | 1920 × 1080 |
| `widgets/alerts.html` | Animated alerts: follow, sub, tip, cheer, raid, member | 900 × 560 |
| `widgets/chat.html` | Twitch chat bubbles with emotes, no login needed | 360 × 520 |
| `widgets/goal.html` | Goal bar with a sparkle at the tip | 800 × 170 |
| `alerts-video/*.webm` | 18 transparent alert animations (6 types × 3 themes) for any alert service | 900 × 420 |
| `streamelements/alerts-widget/` | The alert box as a StreamElements Custom Widget (live events) | — |
| `index.html` | Preview of everything. Double-click it to open it in your browser | — |

## Quick start (OBS Studio)

1. **Unzip** the pack somewhere permanent, e.g. `Documents/Overlays/starlight-dreams`. Keep the folders together.
2. **Personalize it:** open `config.js` in any text editor (Notepad works) and change your name, socials, stream title and theme. Save.
3. In OBS, click **+** under *Sources* and choose **Browser**.
4. Tick **Local file** and pick one of the `.html` files.
5. Set **Width** and **Height** from the table above.
6. Recommended: tick **Refresh browser when scene becomes active**. The countdown then restarts every time you switch to the Starting Soon scene.

To see a change you made in `config.js`, right-click the source and choose **Refresh**.

### Game Frame layout

The game frame is drawn for a 1920 × 1080 canvas:

- **Game capture:** position `40, 40`, size `1440 × 810`
- **Chat widget:** position `1520, 40`, size `360 × 520`
- **Your model:** bottom-right corner. A soft moonlit glow sits behind it.

Put the frame **above** your game capture and **below** your model in the Sources list.

## Alerts, three ways

**A. WebM animations (works with any service).** Upload a file from `alerts-video/` (for example `midnight-follow.webm`) as the alert image/video in Streamlabs, StreamElements or any alert service that accepts WebM. Each clip shows the badge and label with transparency. Let your alert service draw the username underneath; the fonts **Fredoka** and **Nunito** match the pack.

**B. StreamElements Custom Widget (live, full animation with names).**
1. In StreamElements go to *Streaming tools → Overlays*, create a 1920 × 1080 overlay, then *Add widget → Static/Custom → Custom widget*.
2. Click *Open Editor*. Paste the contents of the files in `streamelements/alerts-widget/` into the matching tabs: `HTML.html` → HTML, `CSS.css` → CSS, `JS.js` → JS, `FIELDS.json` → FIELDS.
3. Click *Done*, resize the widget to about 900 × 560, then pick your theme, labels, currency and sound in the left panel.
4. Use StreamElements' *Emulate* button to test.

**C. Local preview.** `widgets/alerts.html` shows the alerts but receives no live events by itself. Add `?demo` to the address (untick *Local file* and use `file:///…/alerts.html?demo`) to watch them cycle.

## Chat

Set `chat.twitchChannel` in `config.js` to your channel name, e.g. `"novamoonpetal"`. The widget reads your public Twitch chat anonymously, with no login and no keys. It supports emotes, `/me` messages, mod/host/VIP tags, hides bots and `!commands`, and removes messages when a mod deletes them.

With no channel set, it plays demo messages so you can position it.
*YouTube chat isn't supported by this widget. Use your chat tool's own overlay and place it inside the frame's chat box.*

## Goal bar

Edit `goal` in `config.js`, or put numbers in the address: `goal.html?current=812&target=1000`.

## Customizing further

- **Colors:** every color comes from the variables at the top of `assets/theme.css`. Copy one `[data-theme="…"]` block, rename it, change the colors and set `theme` in `config.js` to the new name.
- **Text:** all wording is in `config.js`.
- **Stars off:** set `stars: false` or `shootingStars: false` in `config.js` to save a little CPU.
- **Any page, any theme:** add `?theme=sakura` to its address.

## Troubleshooting

- **Blank or white source:** make sure *Local file* is ticked and the folders are still next to each other (the pages load `../config.js` and `../assets/`).
- **config.js change did nothing:** a missing quote or comma breaks the file. Compare with the original, then Refresh.
- **Countdown already at zero:** `startingSoon.startAt` is set to a time that has passed. Clear it (`""`) to use `countdownMinutes`.

## Credits

Fonts: [Fredoka](https://fonts.google.com/specimen/Fredoka) and [Nunito](https://fonts.google.com/specimen/Nunito), SIL Open Font License 1.1 (licenses in `assets/fonts/`).
