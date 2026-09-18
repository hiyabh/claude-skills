"""Render one skill landing page from content/<name>.json."""
from common import (BASE_URL, CATEGORIES, PAGES_DIR, REPO_URL, category_of,
                    esc, footer_html, page_shell, write_text)

CSS_HREF = "../../assets/site.css"
JS_SRC = "../../assets/site.js"


def install_prompt(page):
    name, title = page["name"], page["title"]
    reqs = [r["item"] for r in page.get("requires", [])]
    check = (f"בדוק אם מותקנים אצלי: {', '.join(reqs)}. אם חסר משהו - תגיד לי "
             "בדיוק מה להתקין ותציע להתקין בעצמך."
             if reqs else "ודא שהקובץ SKILL.md נמצא בתיקייה.")
    say = page.get("say") or [title]
    return (
        f'הי קלוד! התקן לי בבקשה את הסקיל "{title}" ({name}).\n'
        "1. זהה את מערכת ההפעלה שלי ואת התיקייה ~/.claude/skills/ "
        "(ב-Windows: C:\\Users\\<user>\\.claude\\skills\\). צור אותה אם אינה קיימת.\n"
        f"2. הורד את החבילה: {BASE_URL}/dl/{name}.tar.gz\n"
        f"3. חלץ ממנה את התיקייה skills/{name} אל ~/.claude/skills/{name}. "
        "אם כבר קיים סקיל בשם הזה - שאל אותי לפני שאתה דורס.\n"
        f"4. {check}\n"
        f'5. הסבר לי בקצרה איך מפעילים - למשל שאני פשוט אומר: "{say[0]}".'
    )


def header_html(page):
    icon, label = CATEGORIES[category_of(page)]
    return f"""<nav class="crumbs rise"><a href="../../">→ כל הסקילים</a>
  <span class="sep">/</span> <span>{icon} {esc(label)}</span></nav>
<header class="hero hero-skill">
  <div class="skill-icon rise" aria-hidden="true">{esc(page['icon'])}</div>
  <h1 class="rise">{esc(page['title'])}</h1>
  <p class="sub rise">{esc(page['tagline'])}</p>
  <div class="cta rise">
    <a class="btn" href="#install">איך מתקינים</a>
    <a class="btn ghost" href="{REPO_URL}/tree/main/src/{esc(page['name'])}">הקבצים ב-GitHub</a>
  </div>
</header>"""


def what_html(page):
    paras = "".join(f"<p>{esc(p)}</p>" for p in page.get("what", []))
    cases = "".join(f"<li>{esc(c)}</li>" for c in page.get("use_cases", []))
    cases_block = f"<h3>מתי זה שימושי</h3><ul class=\"checks\">{cases}</ul>" if cases else ""
    return f"""<section><h2>מה זה עושה</h2>
<div class="card prose">{paras}{cases_block}</div></section>"""


def say_html(page):
    chips = "".join(f'<li class="say">"{esc(s)}"</li>' for s in page.get("say", []))
    if not chips:
        return ""
    return f"""<section><h2>מה אומרים לקלוד</h2>
<p class="muted">אין פקודות ללמוד. אחרי ההתקנה פשוט כותבים לקלוד משפט כמו:</p>
<ul class="says">{chips}</ul></section>"""


def example_html(page):
    ex = page.get("example")
    if not ex or not ex.get("in"):
        return ""
    return f"""<section><h2>דוגמה</h2>
<div class="ba"><div class="card"><h3>מה נותנים</h3><div class="sample">{esc(ex['in'])}</div></div>
<div class="card after"><h3>מה מקבלים</h3><div class="sample">{esc(ex.get('out', ''))}</div></div></div>
</section>"""


def requires_html(page):
    rows = "".join(f"<tr><td><b>{esc(r.get('item'))}</b></td><td>{esc(r.get('note', ''))}</td></tr>"
                   for r in page.get("requires", []))
    body = (f'<table class="tbl"><tr><th>מה</th><th>למה / הערה</th></tr>{rows}</table>'
            if rows else "<p>שום דבר מעבר ל-Claude Code עצמו.</p>")
    caution = page.get("caution")
    note = f'<p class="tag"><b>לתשומת לבך:</b> {esc(caution)}</p>' if caution else ""
    return f"""<section><h2>מה צריך שיהיה מותקן</h2>
<div class="card">{body}{note}</div></section>"""


def install_html(page):
    name = esc(page["name"])
    return f"""<section id="install"><h2>התקנה בהדבקה אחת</h2>
<p>פותחים את Claude Code, מדביקים את הבלוק הבא, והוא מתקין הכול לבד:</p>
<div class="card promptbox">
  <button class="copybtn" type="button" data-copy="prompt">העתק</button>
<pre id="prompt">{esc(install_prompt(page))}</pre>
</div>
<details class="alt"><summary>מעדיף טרמינל? (Git Bash / Mac / Linux)</summary>
<div class="card promptbox">
  <button class="copybtn" type="button" data-copy="cmd">העתק</button>
<pre id="cmd" class="ltr">curl -fsSL {BASE_URL}/install.sh | bash -s -- {name}</pre>
</div>
<p class="muted">או <a href="../../dl/{name}.tar.gz">הורדה ידנית של החבילה</a> וחילוץ אל <code>~/.claude/skills/</code>.</p>
</details></section>"""


def render(page):
    body = "\n".join([
        '<div class="wrap">', header_html(page), what_html(page), say_html(page),
        example_html(page), requires_html(page), install_html(page),
        '<nav class="back"><a class="btn ghost" href="../../">→ לכל הסקילים</a></nav>',
        footer_html(), "</div>",
    ])
    title = f"{page['title']} - סקיל ל-Claude Code · בין קודש לקלוד"
    html = page_shell(title, page["tagline"], page["icon"], CSS_HREF, body, JS_SRC)
    write_text(PAGES_DIR / page["name"] / "index.html", html)
