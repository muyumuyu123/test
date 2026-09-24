"""Download Google Fonts (all OFL) into a local folder + write fonts.css.

    python3 fetch-fonts.py ../mockups/v2

Local copies keep mockups/screenshots working offline. Japanese families are
subset with Google's `text=` parameter to just the characters the pages use.
"""
import hashlib
import os
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
KEEP_SUBSETS = {"latin", "latin-ext", "arabic"}

SPECS = [
    ("family=Chakra+Petch:wght@500;700&family=Share+Tech+Mono", False),
    ("family=Archivo:ital,wdth,wght@0,62..125,100..900;1,62..125,100..900", False),
    ("family=UnifrakturMaguntia&family=IM+Fell+English:ital@0;1&family=IM+Fell+English+SC", False),
    ("family=Reem+Kufi:wght@400..700&family=Readex+Pro:wght@300..700", False),
    ("family=Silkscreen:wght@400;700", False),
    ("family=Caveat+Brush&family=Patrick+Hand&family=Special+Elite", False),
    ("family=Playfair+Display+SC:wght@700;900&family=Oswald:wght@400..700&family=Space+Mono:wght@400;700", False),
    # Japanese: subset to the glyphs used by the pages (plus ASCII)
    ("family=Dela+Gothic+One&family=Rampart+One&family=M+PLUS+Rounded+1c:wght@500;800&family=DotGothic16", True),
]


def used_text(root: Path) -> str:
    chars = set(chr(c) for c in range(0x20, 0x7F))
    for page in root.glob("*.html"):
        chars.update(ch for ch in page.read_text(encoding="utf-8") if ord(ch) > 0x2000)
    return "".join(sorted(chars))


def main(root: Path) -> None:
    out_dir = root / "fonts"
    out_dir.mkdir(parents=True, exist_ok=True)
    faces = []
    for query, subset in SPECS:
        url = f"https://fonts.googleapis.com/css2?{query}&display=block"
        if subset:
            url += "&text=" + urllib.parse.quote(used_text(root))
        css = subprocess.run(["curl", "-sS", "-A", UA, url], capture_output=True, text=True, check=True).stdout
        for comment, block in re.findall(r"(/\*[^*]*\*/\s*)?(@font-face\s*{[^}]*})", css):
            name = (comment or "").strip("/* \n")
            # text= responses have no subset label; everything else must be a kept subset
            if not subset and name not in KEEP_SUBSETS:
                continue
            src = re.search(r"url\((https:[^)]*)\)", block).group(1)
            file = hashlib.md5(src.encode()).hexdigest()[:10] + ".woff2"
            if not (out_dir / file).exists():
                subprocess.run(["curl", "-sS", "-o", str(out_dir / file), src], check=True)
            faces.append(block.replace(src, file))
    (out_dir / "fonts.css").write_text("/* Google Fonts (SIL OFL), stored locally */\n" + "\n".join(faces) + "\n")
    print(f"{len(faces)} faces → {out_dir}")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "."))
