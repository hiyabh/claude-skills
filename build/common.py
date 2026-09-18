"""Shared paths, constants and small helpers for the site build."""
import hashlib
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "src"          # installable skill sources
CONTENT_DIR = ROOT / "content"  # Hebrew landing-page content, one JSON per skill
DL_DIR = ROOT / "dl"            # generated tarballs
PAGES_DIR = ROOT / "skills"     # generated per-skill pages
CATALOG = ROOT / "catalog.json"

OWNER = "hiyabh"
REPO = "claude-skills"
BASE_URL = f"https://{OWNER}.github.io/{REPO}"
REPO_URL = f"https://github.com/{OWNER}/{REPO}"
COMMUNITY_NAME = "בין קודש לקלוד"
COMMUNITY_URL = "https://chat.whatsapp.com/Hr8UI2Oy6lkJTPY3tizdSd?s=cl&p=a&mlu=1"

# Display order of the hub sections. Unknown categories fall into "other".
CATEGORIES = {
    "video": ("🎬", "וידאו ואנימציה"),
    "docs": ("📄", "מסמכים ועברית"),
    "dev": ("🛠️", "פיתוח וזרימת עבודה"),
    "research": ("🔎", "מחקר וארגון"),
    "bots": ("🤖", "בוטים"),
    "life": ("🏠", "בית ומשפחה"),
    "other": ("🧩", "עוד"),
}


def esc(text):
    """HTML-escape any value (None becomes an empty string)."""
    return html.escape("" if text is None else str(text), quote=True)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump_json(path, data):
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    Path(path).write_text(text, encoding="utf-8", newline="\n")


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def category_of(item):
    cat = item.get("category", "other")
    return cat if cat in CATEGORIES else "other"


def load_internal():
    """All skills hosted in this repo, from content/*.json, sorted by title."""
    items = []
    for path in sorted(CONTENT_DIR.glob("*.json")):
        page = load_json(path)
        page.setdefault("name", path.stem)
        page["url"] = f"skills/{page['name']}/"
        items.append(page)
    return sorted(items, key=lambda p: p.get("title", p["name"]))


def versioned(href):
    """Append a content hash so browsers refetch assets as soon as they change."""
    digest = hashlib.sha1((ROOT / "assets" / Path(href).name).read_bytes()).hexdigest()[:8]
    return f"{href}?v={digest}"


def aurora_html(dim=False):
    """Decorative drifting glow behind the hero (pure CSS, aria-hidden)."""
    cls = "aurora dim" if dim else "aurora"
    return f'<div class="{cls}" aria-hidden="true"><i></i><i></i><i></i><i></i></div>'


def page_shell(title, description, icon, css_href, body, scripts=()):
    """Wrap page body in the shared RTL document skeleton."""
    favicon = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
               "viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E"
               f"{icon}%3C/text%3E%3C/svg%3E")
    # The `js` class gates every "starts hidden" motion style, so without JS
    # (or before it loads) all content is visible and static.
    # Failsafe: if motion.js never runs (blocked, 404), un-hide everything.
    script = ("\n<script>document.documentElement.classList.add('js');"
              "setTimeout(function(){if(!window.motionReady)"
              "document.documentElement.classList.remove('js')},2500)</script>")
    script += "".join(f'\n<script src="{versioned(src)}" defer></script>' for src in scripts)
    return f"""<!doctype html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<link rel="icon" href="{favicon}">
<link rel="stylesheet" href="{versioned(css_href)}">{script}
</head>
<body>
{body}
</body>
</html>
"""


def footer_html():
    return f"""<footer class="foot">
  <p><span class="brand">👈 {COMMUNITY_NAME}</span> ·
     <a href="{esc(COMMUNITY_URL)}">הצטרפות לקבוצה</a> ·
     <a href="{REPO_URL}">הקוד ב-GitHub</a></p>
  <p>הסקילים מסופקים כמו שהם, לשימוש חופשי. מותר להעביר הלאה.</p>
</footer>"""
