"""Share images (1200x630) for the hub and every skill page - what WhatsApp/Facebook show for a link.

Usage:  python build/og_images.py        (local only: needs Pillow + python-bidi, Windows fonts)

Writes assets/og/<name>-<hash>.jpg. The hash covers the text and the design, so a changed card gets a
NEW file name (the networks cache by URL). build.py stays stdlib-only: it just links whatever image
exists (common.og_image). Run this, then build.py, whenever a title, tagline or icon changes.
"""
import hashlib
import re
import sys

import numpy as np
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from common import CATALOG, CATEGORIES, OG_DIR, ROOT, category_of, load_internal, load_json
import render_hub

W, H = 1200, 630
BG = (15, 17, 21)
INK, MUTED, GOLD, LINE = (243, 245, 248), (176, 184, 198), (255, 211, 110), (38, 43, 52)
FONTS = r"C:\Windows\Fonts"
TITLE_FONT, BODY_FONT, EMOJI_FONT = rf"{FONTS}\Rubik-Bold.ttf", rf"{FONTS}\Rubik-Regular.ttf", rf"{FONTS}\seguiemj.ttf"
TITLE_MAX, TITLE_MIN, TAG_PT, BRAND_PT, ICON_PT = 92, 54, 38, 30, 120
TEXT_W = 1000
DESIGN = "og-v2"
BRAND = "בין קודש לקלוד · סקילים ל-Claude Code"
JPEG_Q = 90
# external skill pages (own repos) whose index.html links an image from here; end-session has its own
EXTERNAL = ("claude-video-skills", "claude-shiur-editor-skill", "school-equipment-list")


def glow(img):
    """Two soft colour fields behind the type, like the site's aurora."""
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    a = np.asarray(img, np.float32)
    for (cx, cy, r, col, k) in ((960, 40, 520, (255, 190, 80), 0.20), (180, 620, 560, (90, 120, 255), 0.14)):
        w = np.clip(1 - ((x - cx) ** 2 + (y - cy) ** 2) / r ** 2, 0, 1) ** 2 * k
        a = a * (1 - w[..., None]) + np.array(col, np.float32) * w[..., None]
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))


def wrap(text, font, width):
    lines, cur, words = [], "", []
    for word in text.split():                  # a lone dash travels with the next word
        if words and words[-1] in ("-", "·"):
            words[-1] += " " + word
        else:
            words.append(word)
    for word in words:
        trial = f"{cur} {word}".strip()
        if cur and font.getlength(get_display(trial)) > width:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    return lines + [cur] if cur else lines


def centred(draw, y, text, font, fill):
    draw.text((W / 2, y), get_display(text), font=font, fill=fill, anchor="mm")


def title_font(title):
    pt = TITLE_MAX
    while pt > TITLE_MIN and ImageFont.truetype(TITLE_FONT, pt).getlength(get_display(title)) > TEXT_W:
        pt -= 2
    return ImageFont.truetype(TITLE_FONT, pt)


def tagline_lines(tagline):
    font = ImageFont.truetype(BODY_FONT, TAG_PT)
    lines = wrap(tagline, font, TEXT_W)
    if len(lines) > 2:
        lines = lines[:2]
        lines[1] = lines[1].rstrip(" ,.-") + "..."
    return font, lines


def card(icon, title, tagline, chip):
    img = glow(Image.new("RGB", (W, H), BG))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((24, 24, W - 24, H - 24), radius=28, outline=LINE, width=2)
    d.text((W / 2, 135), icon, font=ImageFont.truetype(EMOJI_FONT, ICON_PT), embedded_color=True, anchor="mm")
    centred(d, 285, title, title_font(title), INK)
    font, lines = tagline_lines(tagline)
    for i, line in enumerate(lines):
        centred(d, 375 + i * 52, line, font, MUTED)
    brand = ImageFont.truetype(BODY_FONT, BRAND_PT)
    centred(d, 540, f"{chip}  ·  {BRAND}" if chip else BRAND, brand, GOLD)
    return img


def cards():
    out = [("hub", "🧰", "כל הסקילים ל-Claude Code", render_hub.HUB_DESC, "")]
    for p in load_internal():
        out.append((p["name"], p["icon"], p["title"], p["tagline"], CATEGORIES[category_of(p)][1]))
    for g in load_json(CATALOG).get("guides", []):
        out.append((f"guide-{g['name']}", g["icon"], g["title"], g["tagline"], "מדריך"))
    for e in load_json(CATALOG)["external"]:
        if e["repo"] in EXTERNAL:
            out.append((e["repo"], e["icon"], e["title"], e["tagline"], CATEGORIES[category_of(e)][1]))
    return out


def write(name, img, key):
    digest = hashlib.sha1(f"{DESIGN}|{key}".encode()).hexdigest()[:8]
    path = OG_DIR / f"{name}-{digest}.jpg"
    for old in OG_DIR.glob(f"{name}-*.jpg"):
        if re.fullmatch(rf"{re.escape(name)}-[0-9a-f]{{8}}\.jpg", old.name) and old != path:
            old.unlink()
    if not path.exists():
        img.save(path, quality=JPEG_Q, optimize=True)
    return path


def main():
    OG_DIR.mkdir(parents=True, exist_ok=True)
    for name, icon, title, tagline, chip in cards():
        path = write(name, card(icon, title, tagline, chip), f"{icon}|{title}|{tagline}|{chip}")
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
