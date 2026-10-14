# -*- coding: utf-8 -*-
"""YouTube upload settings from chapters.json + video.json "youtube":
{"title", "description", "tags": [...], "category": "Education", "playlist", "audience_kids": false}.
Writes '<title> - הגדרות יוטיוב.md' (human copy-paste) and youtube.json (machine), and checks YouTube limits."""
import json

from config import BUILD, CFG, TITLE, out_name

TITLE_MAX, DESC_MAX, TAGS_MAX = 100, 5000, 500
CHAPTER_MIN = 10          # YouTube ignores chapters shorter than 10s
CATEGORY_IDS = {"Education": 27, "People & Blogs": 22, "Nonprofits & Activism": 29}


def stamp(sec):
    sec = int(sec)
    h, m, s = sec // 3600, sec % 3600 // 60, sec % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def check(yt, chapters, desc):
    problems = []
    if len(yt["title"]) > TITLE_MAX:
        problems.append(f"title {len(yt['title'])} chars > {TITLE_MAX}")
    if len(desc) > DESC_MAX:
        problems.append(f"description {len(desc)} chars > {DESC_MAX}")
    if len(",".join(yt.get("tags", []))) > TAGS_MAX:
        problems.append(f"tags over {TAGS_MAX} chars")
    if chapters[0]["start"] != 0:
        problems.append("first chapter must start at 0:00")
    short = [c["title"] for c in chapters if c["end"] - c["start"] < CHAPTER_MIN]
    if short:
        problems.append(f"chapters under {CHAPTER_MIN}s: {short}")
    return problems


def write_md(yt, desc, out):
    md = out_name("הגדרות יוטיוב.md")
    md.write_text(f"""# {TITLE} - הגדרות יוטיוב

## קובץ הסרטון
{out['video']}

## תמונה ממוזערת
{out['thumbnail'] or 'עוד לא נוצרה - python make_thumbnail.py'}

## כותרת
{yt['title']}

## תיאור
{desc}
## תגיות
{', '.join(yt['tags'])}

## הגדרות
- קטגוריה: {yt['category']}
- שפת הסרטון וכתוביות: עברית
- מיועד לילדים: {'כן' if yt['audience_kids'] else 'לא'}
- פלייליסט: {yt.get('playlist', '-')}
""", encoding="utf-8")
    return md


def main():
    yt = {"title": TITLE, "tags": [], "category": "Education", "audience_kids": False, **CFG.get("youtube", {})}
    chapters = json.loads((BUILD / "chapters.json").read_text(encoding="utf-8"))["chapters"]
    stamps = "\n".join(f"{stamp(c['start'])} {c['title']}" for c in chapters)
    desc = f"{yt.get('description', '').strip()}\n\nפרקים:\n{stamps}\n"
    thumb = out_name("תמונה ממוזערת.jpg")
    out = {**yt, "description": desc, "category_id": CATEGORY_IDS.get(yt["category"], 27), "language": "he",
           "thumbnail": thumb.name if thumb.exists() else None, "video": out_name("סרטון השיעור.mp4").name}
    (BUILD / "youtube.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    write_md(yt, desc, out)
    problems = check(yt, chapters, desc)
    print(out_name("הגדרות יוטיוב.md").name, "written", "| PROBLEMS: " + "; ".join(problems) if problems else "| all YouTube limits OK")


if __name__ == "__main__":
    main()
