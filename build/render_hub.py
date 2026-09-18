"""Render the hub page (index.html) from internal content + catalog.json."""
from common import (CATALOG, CATEGORIES, ROOT, category_of, esc, footer_html,
                    load_internal, load_json, page_shell, write_text)

HUB_TITLE = "כל הסקילים של בין קודש לקלוד"
HUB_DESC = ("מרכז אחד לכל הסקילים ל-Claude Code שבנינו בקהילת בין קודש לקלוד - "
            "וידאו, מסמכים בעברית, פיתוח, מחקר ובוטים. כל סקיל עם דף הסבר והתקנה בהדבקה אחת.")


def skill_count(item):
    """How many installable skills a card stands for (bundles count more)."""
    return int(item.get("count", 1))


def card_html(item, external):
    search = " ".join([item.get("title", ""), item.get("tagline", ""),
                       item.get("name", item.get("repo", "")), " ".join(item.get("say", []))])
    badge = f'<span class="badge">{esc(item["badge"])}</span>' if item.get("badge") else ""
    ext = '<span class="badge ext">דף נפרד ↗</span>' if external else ""
    return f"""<li class="cardwrap" data-cat="{category_of(item)}" data-search="{esc(search.lower())}">
  <a class="skill-card" href="{esc(item['url'])}">
    <span class="ic" aria-hidden="true">{esc(item.get('icon', '🧩'))}</span>
    <span class="t">{esc(item.get('title'))}</span>
    <span class="d">{esc(item.get('tagline'))}</span>
    <span class="meta">{badge}{ext}<span class="go" aria-hidden="true">←</span></span>
  </a>
</li>"""


def group(items):
    buckets = {key: [] for key in CATEGORIES}
    for item, external in items:
        buckets[category_of(item)].append((item, external))
    return {k: v for k, v in buckets.items() if v}


def chips_html(buckets):
    chips = ['<a class="chip" href="#top" data-filter="all" aria-pressed="true">הכול</a>']
    for key, entries in buckets.items():
        icon, label = CATEGORIES[key]
        chips.append(f'<a class="chip" href="#cat-{key}" data-filter="{key}" aria-pressed="false">'
                     f'{icon} {esc(label)} <span class="n">{len(entries)}</span></a>')
    return "\n".join(chips)


def sections_html(buckets):
    out = []
    for key, entries in buckets.items():
        icon, label = CATEGORIES[key]
        cards = "\n".join(card_html(item, ext) for item, ext in entries)
        out.append(f"""<section class="cat" id="cat-{key}" data-cat="{key}">
<h2><span aria-hidden="true">{icon}</span> {esc(label)}</h2>
<ul class="grid">
{cards}
</ul></section>""")
    return "\n".join(out)


def hero_html(total, pages, guide):
    return f"""<header class="hero" id="top">
  <p class="eyebrow rise">👈 {esc('בין קודש לקלוד')}</p>
  <h1 class="rise">כל הסקילים שלי ל-Claude Code</h1>
  <p class="sub rise">סקיל הוא "כישרון" שמוסיפים לקלוד: אחרי התקנה של דקה, אומרים לו משפט
     בעברית פשוטה - והוא יודע לבצע משימה שלמה מההתחלה ועד הסוף.</p>
  <div class="stats rise"><span><b>{total}</b> סקילים</span><span><b>{pages}</b> דפי הסבר</span>
    <span><b>1</b> הדבקה להתקנה</span></div>
  <a class="guide rise" href="{esc(guide['url'])}">
    <span class="ic" aria-hidden="true">{esc(guide['icon'])}</span>
    <span><b>{esc(guide['title'])}</b><br><span class="d">{esc(guide['tagline'])}</span></span>
    <span class="go" aria-hidden="true">←</span></a>
</header>"""


def filterbar_html(buckets):
    return f"""<div class="filterbar">
  <input class="search" type="search" placeholder="חיפוש סקיל... (למשל: וורד, בוט, יוטיוב)"
         aria-label="חיפוש סקיל" hidden>
  <nav class="chips" aria-label="סינון לפי תחום">
{chips_html(buckets)}
  </nav>
</div>
<p class="empty" hidden>לא נמצא סקיל מתאים. נסה מילה אחרת, או <a href="#top" data-filter="all">הצג הכול</a>.</p>"""


def render():
    catalog = load_json(CATALOG)
    items = [(p, False) for p in load_internal()]
    items += [(e, True) for e in catalog.get("external", [])]
    items.sort(key=lambda pair: pair[0].get("title", ""))
    buckets = group(items)
    total = sum(skill_count(item) for item, _ in items)
    body = "\n".join(['<div class="wrap">', hero_html(total, len(items), catalog["guide"]),
                      filterbar_html(buckets), '<main id="skills">', sections_html(buckets),
                      "</main>", footer_html(), "</div>"])
    html = page_shell(HUB_TITLE, HUB_DESC, "🧰", "assets/site.css", body, "assets/site.js")
    write_text(ROOT / "index.html", html)
    return len(items), total
