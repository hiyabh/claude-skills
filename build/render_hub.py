"""Render the hub page (index.html) from internal content + catalog.json."""
import json
import random

from common import (CATALOG, CATEGORIES, ROOT, aurora_html, category_of, esc,
                    footer_html, load_internal, load_json, page_shell, write_text)

HUB_TITLE = "כל הסקילים של בין קודש לקלוד"
HUB_DESC = ("מרכז אחד לכל הסקילים ל-Claude Code שבנינו בקהילת בין קודש לקלוד - "
            "וידאו, מסמכים בעברית, פיתוח, מחקר ובוטים. כל סקיל עם דף הסבר והתקנה בהדבקה אחת.")
# Kept as units: splitting "ל-Claude Code" into inline-blocks breaks bidi order.
TITLE_WORDS = ["כל", "הסקילים", "שלי", "ל-Claude Code"]
SCRIPTS = ["assets/motion.js", "assets/hero.js", "assets/filter.js"]
TICKER_SEED = 7          # fixed seeds keep the generated HTML byte-stable
CONSTELLATION_SEED = 11
CONSTELLATION_SIZE = 14
TICKER_MAX_CHARS = 44    # longer phrases wrap to 3 lines and make the hero jump
# Phrases for the external cards, which have no content/*.json of their own.
EXTERNAL_SAY = {
    "claude-shiur-editor-skill": "ערוך לי את השיעור הזה",
    "claude-end-session-skill": "סיימנו",
    "claude-video-skills": "תעשה לי סרטון מטורף על",
    "school-equipment-list": "תאחד לי את רשימות הציוד של הילדים",
}


def skill_count(item):
    """How many installable skills a card stands for (bundles count more)."""
    return int(item.get("count", 1))


def card_html(item, external):
    search = " ".join([item.get("title", ""), item.get("tagline", ""),
                       item.get("name", item.get("repo", "")), " ".join(item.get("say", []))])
    badge = f'<span class="badge">{esc(item["badge"])}</span>' if item.get("badge") else ""
    ext = '<span class="badge ext">דף נפרד ↗</span>' if external else ""
    return f"""<li class="cardwrap reveal" data-cat="{category_of(item)}" data-search="{esc(search.lower())}">
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


def chip_list(buckets, tag):
    """One row of chips. tag='a' is the real row; tag='span' is the pill copy."""
    first = {"a": ' href="#top" data-filter="all" aria-pressed="true"', "span": ""}[tag]
    chips = [f'<{tag} class="chip"{first}>הכול</{tag}>']
    for key, entries in buckets.items():
        icon, label = CATEGORIES[key]
        attrs = (f' href="#cat-{key}" data-filter="{key}" aria-pressed="false"' if tag == "a" else "")
        chips.append(f'<{tag} class="chip"{attrs}>{icon} {esc(label)} '
                     f'<span class="n">{len(entries)}</span></{tag}>')
    return "\n".join(chips)


def sections_html(buckets):
    out = []
    for key, entries in buckets.items():
        icon, label = CATEGORIES[key]
        cards = "\n".join(card_html(item, ext) for item, ext in entries)
        out.append(f"""<section class="cat" id="cat-{key}" data-cat="{key}">
<h2 class="reveal"><span aria-hidden="true">{icon}</span> {esc(label)}</h2>
<ul class="grid">
{cards}
</ul></section>""")
    return "\n".join(out)


def ticker_phrases(items):
    phrases = []
    for item, external in items:
        options = [EXTERNAL_SAY.get(item.get("repo"))] if external else item.get("say", [])
        options = [s.strip("\"'") for s in options if s and len(s) <= TICKER_MAX_CHARS]
        say = options[0] if options else None
        if say:
            phrases.append({"say": say, "title": item["title"], "url": item["url"]})
    random.Random(TICKER_SEED).shuffle(phrases)
    return phrases


def ticker_html(phrases):
    first = phrases[0]
    data = esc(json.dumps(phrases, ensure_ascii=False))
    return f"""<p class="ticker rise" data-phrases="{data}">
  <span class="ticker-label">תגיד לקלוד:</span>
  <a class="ticker-link" href="{esc(first['url'])}"><span class="ticker-say">"{esc(first['say'])}"</span>
  <span class="ticker-skill">← {esc(first['title'])}</span></a></p>"""


def constellation_html(items):
    """Skill icons scattered at fixed pseudo-random spots with a depth each."""
    rng = random.Random(CONSTELLATION_SEED)
    icons = [item.get("icon", "🧩") for item, _ in items][:CONSTELLATION_SIZE]
    stars = []
    for i, icon in enumerate(icons):
        depth = round(rng.uniform(0.35, 1.0), 2)
        x, y = rng.uniform(4, 86), rng.uniform(4, 88)
        bob = round(rng.uniform(7, 11), 1)
        stars.append(f'<span class="star" data-depth="{depth}" style="--x:{x:.1f}%;--y:{y:.1f}%;'
                     f'--depth:{depth};--bob:{bob}s;--delay:-{i * 0.7:.1f}s">'
                     f'<span>{esc(icon)}</span></span>')
    return f'<div class="constellation" aria-hidden="true">{"".join(stars)}</div>'


def hero_html(total, pages, guide, phrases):
    words = "".join(f'<span class="w" style="--i:{i}">{esc(w)}</span> '
                    for i, w in enumerate(TITLE_WORDS))
    return f"""<header class="hero" id="top">
  <p class="eyebrow rise">👈 {esc('בין קודש לקלוד')}</p>
  <h1 class="words">{words.strip()}</h1>
  <p class="sub rise">סקיל הוא "כישרון" שמוסיפים לקלוד: אחרי התקנה של דקה, אומרים לו משפט
     בעברית פשוטה - והוא יודע לבצע משימה שלמה מההתחלה ועד הסוף.</p>
  {ticker_html(phrases)}
  <div class="stats rise"><span><b data-count="{total}">{total}</b> סקילים</span>
    <span><b data-count="{pages}">{pages}</b> דפי הסבר</span><span><b>1</b> הדבקה להתקנה</span></div>
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
    <div class="chips-row">
{chip_list(buckets, "a")}
    </div>
    <div class="chips-row pill-copy" aria-hidden="true" hidden>
{chip_list(buckets, "span")}
    </div>
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
    body = "\n".join([aurora_html(), '<div class="wrap">', constellation_html(items),
                      hero_html(total, len(items), catalog["guide"], ticker_phrases(items)),
                      filterbar_html(buckets), '<main id="skills">', sections_html(buckets),
                      "</main>", footer_html(), "</div>"])
    html = page_shell(HUB_TITLE, HUB_DESC, "🧰", "assets/site.css", body, SCRIPTS)
    write_text(ROOT / "index.html", html)
    return len(items), total
