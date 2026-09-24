# overlay-tools

Seller-side tools for the Starlight Dreams overlay pack (screenshots, WebM alert renders,
StreamElements widget build). Not shipped to buyers. See `PANDUAN-JUALAN.md`.

- `node previews.mjs`: store screenshots → `previews/`
- `node render.mjs [type] [theme]`: transparent alert WebMs → `../vtuber-overlay-pack/alerts-video/`
- `node build-se.mjs`: StreamElements custom widget → `../vtuber-overlay-pack/streamelements/alerts-widget/`
- `node shot.mjs <page> <out.png> [w h wait]` / `node bg.mjs <page> <out.png> [w h]`: quick single screenshots
