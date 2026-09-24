# overlay-tools

Seller-side tools for the Starlight Dreams overlay pack (screenshots, WebM alert renders,
StreamElements widget build). Not shipped to buyers. See `PANDUAN-JUALAN.md`.

- `node previews.mjs`: store screenshots → `previews/`
- `node render.mjs [type] [theme]`: transparent alert WebMs → `../vtuber-overlay-pack/alerts-video/`
- `node build-se.mjs`: StreamElements custom widget → `../vtuber-overlay-pack/streamelements/alerts-widget/`
- `node shot.mjs <page> <out.png> [w h wait]` / `node bg.mjs <page> <out.png> [w h]`: quick single screenshots
- `python3 fetch-fonts.py ../mockups/v2`: download the mockup fonts locally (Japanese fonts subset to the glyphs the pages use)
- `node mock2-shot.mjs [theme ...]`: round-2 theme mockups → `../mockups/v2/previews/` (+ overview sheets with `FFMPEG` set)
