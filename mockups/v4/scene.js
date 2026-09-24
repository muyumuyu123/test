// Helpers for overlays built on top of painted/AI background art.
window.SCENE = (function () {
  "use strict";

  // CSS matrix3d that maps an element of size w×h onto a quad
  // pts = [[x,y] TL, TR, BR, BL] in page pixels (projective / perspective warp).
  function quadTransform(w, h, pts) {
    const [[x0, y0], [x1, y1], [x2, y2], [x3, y3]] = pts;
    const dx1 = x1 - x2, dx2 = x3 - x2, dx3 = x0 - x1 + x2 - x3;
    const dy1 = y1 - y2, dy2 = y3 - y2, dy3 = y0 - y1 + y2 - y3;
    const den = dx1 * dy2 - dx2 * dy1;
    const g = (dx3 * dy2 - dx2 * dy3) / den;
    const hh = (dx1 * dy3 - dx3 * dy1) / den;
    const a = x1 - x0 + g * x1, b = x3 - x0 + hh * x3, c = x0;
    const d = y1 - y0 + g * y1, e = y3 - y0 + hh * y3, f = y0;
    const m = [a / w, d / w, 0, g / w, b / h, e / h, 0, hh / h, 0, 0, 1, 0, c, f, 0, 1];
    return `matrix3d(${m.map((v) => +v.toFixed(8)).join(",")})`;
  }

  // Place every [data-quad="x0,y0 x1,y1 x2,y2 x3,y3"] element onto its quad.
  function placeQuads(root = document) {
    root.querySelectorAll("[data-quad]").forEach((el) => {
      const pts = el.dataset.quad.trim().split(/\s+/).map((p) => p.split(",").map(Number));
      el.style.position = "absolute";
      el.style.left = "0";
      el.style.top = "0";
      el.style.transformOrigin = "0 0";
      el.style.transform = quadTransform(el.offsetWidth, el.offsetHeight, pts);
    });
  }

  function ready(fn) {
    const go = () => (document.fonts ? document.fonts.ready.then(fn) : fn());
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", go);
    else go();
  }

  return { quadTransform, placeQuads, ready };
})();
