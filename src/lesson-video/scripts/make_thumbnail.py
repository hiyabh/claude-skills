# -*- coding: utf-8 -*-
"""YouTube thumbnail: thumb template + hero illustration + short Hebrew title, rendered by the browser (RTL-safe),
saved as '<title> - תמונה ממוזערת.jpg' (1280x720, under 2MB).
video.json "thumb": {"img": "<scene name>", "title": "2-5 words, *gold word*", "kicker": "...", "sub": "...", "badge": "..."}"""
import html
import re
import shutil
import subprocess
from pathlib import Path

from PIL import Image

from config import BUILD, CFG, CLIP, out_name

TEMPLATE = Path(__file__).resolve().parent / "thumb_template.html"
HF = ["npx", "--yes", "hyperframes@0.8.106"]
SIZE = (1280, 720)
MAX_BYTES = 2 * 1024 * 1024
QUALITIES = (92, 86, 80, 72)


def fill(t):
    title = re.sub(r"\*([^*]+)\*", r"<b>\1</b>", html.escape(t["title"]))
    page = TEMPLATE.read_text(encoding="utf-8")
    for key, val in (("__IMG__", t["img"]), ("__KICKER__", html.escape(t.get("kicker", ""))), ("__TITLE__", title),
                     ("__SUB__", html.escape(t.get("sub", ""))), ("__BADGE__", html.escape(t.get("badge", "")))):
        page = page.replace(key, val)
    return page


def stage(t):
    proj = BUILD / "thumb"
    (proj / "assets" / "img").mkdir(parents=True, exist_ok=True)
    shutil.copytree(CLIP / "assets" / "fonts", proj / "assets" / "fonts", dirs_exist_ok=True)
    shutil.copy2(CLIP / "assets" / "img" / f"{t['img']}.png", proj / "assets" / "img")
    (proj / "index.html").write_text(fill(t), encoding="utf-8")
    shutil.copy2(CLIP / "package.json", proj)
    return proj


def main():
    t = CFG["thumb"]
    proj = stage(t)
    subprocess.run(HF + ["snapshot", "--at", "0.5", "-o", "shot"], cwd=proj, check=True, shell=True)
    png = sorted((proj / "shot").glob("frame-*.png"))[0]
    out = out_name("תמונה ממוזערת.jpg")
    img = Image.open(png).convert("RGB").resize(SIZE, Image.LANCZOS)
    for quality in QUALITIES:
        img.save(out, "JPEG", quality=quality, optimize=True)
        if out.stat().st_size < MAX_BYTES:
            break
    print(f"{out.name}: {img.size[0]}x{img.size[1]}, {out.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
