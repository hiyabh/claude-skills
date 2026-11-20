"""Render the guide pages listed under "guides" in catalog.json.

Each guide has a body fragment guides_src/<name>.html. Placeholders {{KEY}} are filled with the escaped
text of guides_src/<name>.<key>.txt, so prompts can hold any character. Output: guides/<name>/index.html.
"""
import re

from common import CATALOG, ROOT, aurora_html, esc, footer_html, load_json, page_shell, write_text

SRC_DIR = ROOT / "guides_src"
OUT_DIR = ROOT / "guides"
CSS_HREF = "../../assets/site.css"
SCRIPTS = ["../../assets/motion.js"]
PLACEHOLDER = re.compile(r"\{\{([A-Z_]+)\}\}")


def fill(name, fragment):
    def repl(match):
        path = SRC_DIR / f"{name}.{match.group(1).lower()}.txt"
        if not path.is_file():
            raise SystemExit(f"guide {name}: missing {path.name}")
        return esc(path.read_text(encoding="utf-8").strip())
    return PLACEHOLDER.sub(repl, fragment)


def render_one(guide):
    name = guide["name"]
    fragment = fill(name, (SRC_DIR / f"{name}.html").read_text(encoding="utf-8"))
    body = "\n".join([aurora_html(dim=True), '<div class="wrap">', fragment,
                      '<nav class="back"><a class="btn ghost" href="../../">→ לכל הסקילים</a></nav>',
                      footer_html(), "</div>"])
    title = f"{guide['title']} · בין קודש לקלוד"
    html = page_shell(title, guide["tagline"], guide["icon"], CSS_HREF, body, SCRIPTS,
                      page_path=f"guides/{name}/", og_name=f"guide-{name}")
    write_text(OUT_DIR / name / "index.html", html)


def render_all():
    guides = load_json(CATALOG).get("guides", [])
    for guide in guides:
        render_one(guide)
    return len(guides)
