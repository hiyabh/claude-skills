# -*- coding: utf-8 -*-
"""The brief for the printer and the designer, from the spec: Markdown + an RTL Word file.

    python brief.py <cover_spec.json>

Writes "<output folder>/00 - הנחיות לבית הדפוס - <title>.md" and ".docx": the files sent, the book's
specification, every cover measurement with WHERE it came from (the bindery's drawing or our estimate),
the exact wording on the cover, fonts and colours, the technical facts of the files, and the questions
still open with the printer. Optional spec keys: "brief": {"notes": [...], "questions": [...],
"interior": "<interior pdf name>"}.
"""
import sys
from pathlib import Path

import build_cover as B
import geometry as G
import spec as S
from brief_docx import write_docx
from common import FONTS_DIR, find_icc, safe_name, warn

PANEL_NAMES = {"front": "חזית", "spine": "שדרה (מלמעלה למטה)", "back": "גב"}


def files_table(spec, pdf):
    rows = [(pdf.name, "הכריכה הפרוסה לדפוס (חזית, שדרה וגב), עם גלישה" + (" וסימני חיתוך וקיפול" if spec["marks"] else ""))]
    interior = spec.get("brief", {}).get("interior")
    if interior:
        there = (pdf.parent / interior).is_file()
        if not there:
            warn(f"קובץ הפנים '{interior}' לא נמצא בתיקייה {pdf.parent}. העתק אותו לשם לפני השליחה.")
        rows.append((interior, "פנים הספר" + ("" if there else " (עדיין לא בתיקייה)")))
    rows += [("תצוגה פרוסה עם קווי עזר.jpg (לאישור, בנפרד)", "אדום = חיתוך, תכלת = קיפול, ירוק = אזור בטוח, ורוד = ברקוד"),
             ("הדמיה.jpg (לאישור, בנפרד)", "הדמיה של הספר הסגור")]
    return rows


def spec_rows(spec):
    kind = "קשה, מודפסת בצבע מלא" if spec["binding"] == "hard" else "רכה, דבק"
    paper = S.paper_text(spec.get("paper", "")) + (f" ({spec['caliper_per_leaf']} מ\"מ לגיליון)" if spec.get("caliper_per_leaf") else "")
    direction = ("ספר עברי, נפתח מימין. בכריכה הפרוסה החזית בצד שמאל והגב בצד ימין"
                 if spec["direction"] == "rtl" else "נפתח משמאל. בכריכה הפרוסה החזית בצד ימין")
    return [("גודל דף (חיתוך)", f"{spec['trim'][0]:g}x{spec['trim'][1]:g} מ\"מ"), ("עמודים", str(spec["pages"])),
            ("כריכה", kind), ("נייר", paper or "לפי בית הדפוס"), ("כיוון", direction)]


def source(spec, key):
    return "משוער - לאשר" if any(e.startswith(key) for e in spec["estimated"]) else "לפי המפרט / בית הדפוס"


def measure_rows(spec, lay):
    rows = []
    if spec["binding"] == "hard":
        h = spec["hard"]
        rows += [("קרטון חזית וגב", f"{h['board'][0]:g}x{h['board'][1]:g} מ\"מ", source(spec, "hard.board")),
                 ("ביג (בין הקרטון לשדרה)", f"{h['joint']:g} מ\"מ", source(spec, "hard.joint")),
                 ("גלישה מסביב לקרטון", f"{h['wrap']:g} מ\"מ", source(spec, "hard.wrap"))]
    rows += [("רוחב שדרה", f"{lay.spine.w:g} מ\"מ", spec["spine_source"]),
             ("גלישה לחיתוך בקובץ", f"{spec['bleed']:g} מ\"מ", "לפי המפרט"),
             ("אזור בטוח לטקסט", f"{spec['safe']:g} מ\"מ מקצה הקרטון/הדף", "לפי המפרט"),
             ("גיליון (TrimBox)", f"{lay.width:g}x{lay.height:g} מ\"מ", "מחושב")]
    return rows


def wording(spec):
    lines = []
    for panel in ("front", "spine", "back"):
        items = [t for t in spec["text"] if t["panel"] == panel]
        if items:
            lines.append(f"### {PANEL_NAMES[panel]}")
            lines += [f"- {t['text'].replace(chr(10), ' / ')}" for t in items]
            lines.append("")
    bc = spec.get("barcode") or {}
    if bc.get("isbn"):
        lines.append(f"ברקוד בגב: מסת\"ב {bc['isbn']}, בשחור 100% על רקע לבן.")
    elif bc:
        lines.append("אזור הברקוד בגב נשאר פנוי" + (" (בית הדפוס מדביק תווית משלו)." if bc.get("fill") == "clear" else "."))
    return lines


def fonts_rows(spec):
    rows = []
    for key, path in spec["fonts"].items():
        used = sorted({PANEL_NAMES[t["panel"]].split(" ")[0] for t in spec["text"] if t["font"] == key})
        if not used:
            continue
        ours = Path(path).parent == FONTS_DIR
        licence = "OFL - מותר להטמעה ולשימוש מסחרי" if ours else "גופן מערכת או מסחרי - רישיון לשימוש בספר נמכר דורש אימות"
        rows.append((Path(path).stem, ", ".join(used), licence))
    return rows


def bookpod_questions(spec):
    return [f"בטופס ההעלאה: סוג נייר {S.paper_text(spec.get('paper', 'white-80'))} (הטופס פותח על 80 גרם - לשנות), "
            f"מספר עמודים {spec['pages']}, למינציה מט או מבריקה.",
            "בפנים הספר: לסמן 'יש גלישה' (3.2 מ\"מ).",
            "בתצוגה המקדימה של הכריכה: לוודא שהגלישה מוצגת כ-3.2 מ\"מ מכל צד ושתווית הברקוד לא מסתירה טקסט.",
            "להזמין עותק ניסיון אחד לפני הפרסום."]


def questions(spec):
    q = list(spec.get("brief", {}).get("questions", []))
    if spec["printer"] == "bookpod":
        return q + bookpod_questions(spec)
    if spec["estimated"]:
        q.append("מידות סופיות (שרטוט כריכה): " + "; ".join(S.estimate_text(e) for e in spec["estimated"]) +
                 " - אלה הערכות שלנו.")
    q += ["עובי הנייר בפועל (מ\"מ לגיליון) - הוא שקובע את רוחב השדרה.",
          "פרופיל הצבע וסוג ה-PDF שאתם מקבלים (Fogra39 / Fogra51, PDF/X-1a או X-4).",
          "גימור: למינציה מט או מבריקה; הטבעת זהב או לכה סלקטיבית (דורשים שכבה נפרדת).",
          "הדפסת ניסיון של כריכה אחת ועותק שמש של הפנים לפני הריצה המלאה."]
    if spec["binding"] == "hard":
        q.append("נייר פורזץ (הדף שמחבר את הכריכה לספר): לבן או צבעוני.")
    q.append("כפולת עמודים בקונטרס (16 או 32) והאם נדרשת גלישה גם בפנים הספר.")
    return q


def markdown(spec, lay, pdf, icc_note):
    title = spec.get("title", "ספר")
    md = [f"# הנחיות לבית הדפוס - {title}", "",
          "המסמך מלווה את קובצי הדפוס. הוא מרכז את המידות, את הנוסח המדויק של הכריכה, את הדרישות הטכניות "
          "ואת השאלות שצריך לסגור לפני ההדפסה.", "", "## מה מצורף", "", table(("קובץ", "מה יש בו"), files_table(spec, pdf)),
          "## מפרט הספר", "", table(("פרט", "ערך"), spec_rows(spec)),
          "## מידות הכריכה הפרוסה", "", table(("רכיב", "ערך", "מקור"), measure_rows(spec, lay)),
          "## הנוסח המדויק של הכריכה", ""] + wording(spec)
    md += ["", "כל הכיתוב על הכריכה הוא טקסט וקטורי בגופן מוטמע, ולא חלק מתמונה.", "",
           "## גופנים", "", table(("שם", "קובץ", "רישיון"), fonts_rows(spec)),
           "## דרישות טכניות שהקבצים עומדים בהן", "",
           f"- תמונת הרקע ב-{spec['dpi']}dpi בגודל מלא, בצבע {spec['colour'].upper()} ({icc_note}).",
           "- תיבת החיתוך (TrimBox) ותיבת הגלישה (BleedBox) מוגדרות בקובץ." +
           (" סימני חיתוך וקיפול מחוץ לגלישה, ושורת מידע בתחתית." if spec["marks"] else " בלי סימני חיתוך."),
           "- כל הגופנים מוטמעים. הקבצים אינם PDF/X; אם נדרש, ההמרה נעשית אצלכם או לפי בקשתכם.", "",
           "## שאלות לבית הדפוס", ""] + [f"{i}. {q}" for i, q in enumerate(questions(spec), 1)]
    notes = spec.get("brief", {}).get("notes", [])
    if notes:
        md += ["", "## הערות", ""] + [f"- {n}" for n in notes]
    return "\n".join(md).replace("—", "-").replace("–", "-") + "\n"


def table(head, rows):
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    lines += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(lines) + "\n"


def main():
    if len(sys.argv) != 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0 if len(sys.argv) == 2 else 1)
    spec = S.load(sys.argv[1])
    lay = G.layout(spec)
    pdf = B.out_paths(spec)[0]
    icc_note = "פרופיל " + (Path(find_icc(spec["icc"])[0]).stem if spec["colour"] == "cmyk" else "sRGB")
    md = markdown(spec, lay, pdf, icc_note)
    stem = str(pdf.parent / safe_name(f"00 - הנחיות לבית הדפוס - {spec.get('title', 'ספר')}"))
    Path(stem + ".md").write_text(md, encoding="utf-8")
    write_docx(md, stem + ".docx")
    print(f"נוצר: {stem}.md")
    print(f"נוצר: {stem}.docx")


if __name__ == "__main__":
    main()
