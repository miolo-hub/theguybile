"""Draw the link-preview card for every verse: dist/v/<ch>-<v>.jpg (1200x630).

Run after scripts/build.py. Needs Pillow (pip install pillow).

    python3 scripts/verse_cards.py          # all verses
    python3 scripts/verse_cards.py --og     # also redraw src/og.jpg (the site-wide card)
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
W, H = 1200, 630
CREAM, GILT, INK = (244, 232, 206), (226, 194, 125), (30, 14, 8)

SERIF = [  # first one found wins
    "/usr/share/fonts/opentype/ebgaramond/EBGaramond12-Regular.otf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    "/System/Library/Fonts/Supplemental/Georgia.ttf",
]
SERIF_IT = [
    "/usr/share/fonts/opentype/ebgaramond/EBGaramond12-Italic.otf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf",
    "/System/Library/Fonts/Supplemental/Georgia Italic.ttf",
]
SERIF_B = [
    "/usr/share/fonts/opentype/ebgaramond/EBGaramond12-Bold.otf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
]


def font(paths, size):
    for p in paths:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default(size)


def backdrop():
    bg = Image.open(ROOT / "src" / "art" / "cover.webp").convert("RGB")
    s = max(W / bg.width, H / bg.height)
    bg = bg.resize((round(bg.width * s), round(bg.height * s)), Image.LANCZOS)
    x, y = (bg.width - W) // 2, (bg.height - H) // 2
    bg = bg.crop((x, y, x + W, y + H))
    shade = Image.new("RGB", (W, H), INK)
    return Image.blend(bg, shade, 0.38)


def wrap(draw, text, f, width):
    lines, line = [], ""
    for word in text.split():
        t = (line + " " + word).strip()
        if draw.textlength(t, font=f) <= width:
            line = t
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def centered(draw, y, text, f, fill):
    draw.text(((W - draw.textlength(text, font=f)) / 2, y), text, font=f, fill=fill)


def card(text, ref, chapter, base):
    im = base.copy()
    d = ImageDraw.Draw(im)
    quote = f"“{text.strip(chr(34) + chr(8220) + chr(8221))}”"
    for size in (54, 50, 46, 42, 38, 34, 31, 28, 25):
        f = font(SERIF, size)
        lines = wrap(d, quote, f, 860)
        lh = round(size * 1.32)
        if len(lines) * lh <= 330:
            break
    small = font(SERIF_IT, 28)
    label = font(SERIF_B, 30)
    block = len(lines) * lh
    y = (H - block) // 2 - 22
    for ln in lines:
        centered(d, y, ln, f, CREAM)
        y += lh
    centered(d, y + 26, f"Guybile {ref}", label, GILT)
    if chapter:
        centered(d, y + 66, chapter, small, (214, 196, 160))
    centered(d, H - 58, "theguybile.com", font(SERIF, 24), (200, 170, 110))
    return im


def site_card(base):
    im = base.copy()
    d = ImageDraw.Draw(im)
    centered(d, 175, "The Guybile", font(SERIF_B, 120), GILT)
    centered(d, 330, "The Bro Code, rewritten as scripture.", font(SERIF_IT, 40), CREAM)
    centered(d, 385, "Funny on the surface, true underneath.", font(SERIF_IT, 40), CREAM)
    centered(d, H - 78, "theguybile.com", font(SERIF, 26), (200, 170, 110))
    return im


def main():
    base = backdrop()
    if "--og" in sys.argv:
        site_card(base).save(ROOT / "src" / "og.jpg", quality=82, optimize=True, progressive=True)
        print("Wrote src/og.jpg")
    verses = json.loads((DIST / "verses.json").read_text())
    out = DIST / "v"
    out.mkdir(exist_ok=True)
    for ref, _slug, chapter, text in verses:
        card(text, ref, chapter, base).save(out / f"{ref.replace(':', '-')}.jpg",
                                             quality=60, optimize=True, progressive=True)
    print(f"Drew {len(verses)} verse cards -> dist/v/")


if __name__ == "__main__":
    main()
