---
name: geulah
description: >-
  Extract structured data from Hebrew handwritten/scanned PDF reports (especially
  Ministry of Education grant reports — דוחות ביצוע מענקי שכר לימוד), payslips,
  BDO accountant approvals, and merge into RTL Excel summaries. Triggers — "דוחות
  ביצוע", "מענק שכר לימוד", "תלוש שכר עברי", "סריקה בכתב יד", "אקסל מענקים",
  "OCR עברי", "geulah", "גאולה". Use when user has a folder of mixed Hebrew PDFs
  (signed/unsigned reports, scanned tables with handwritten teacher rows, payslip
  PDFs with digital text) and needs a single tabular summary.
metadata:
  version: 1.0.0
  tags:
    he: [גאולה, מענקי, שכר, לימוד, ביצוע, OCR, תלושים, מוסדות-חינוך]
    en: [hebrew-ocr, gemini-vision, ministry-education, payslips, rtl-excel]
---

# Skill: גאולה — חילוץ נתונים מקבצי PDF עבריים מורכבים

מטרת הסקיל: לעבד תיקייה של עשרות PDFs בעברית (סריקות עם כתב יד + תלושי שכר דיגיטליים + מכתבי אישור) ולהפיק קובץ Excel RTL מסודר. נבנה מתוך פרויקט "גאולה" (מאי 2026) שעיבד 36 PDFs וייצר טבלה של 128 מורים מ-4 מטפלים שונים.

## מתי להפעיל

- המשתמש מבקש "תבנה אקסל מהקבצים בתיקייה" כשיש PDFs עבריים
- מסמכי משרד החינוך (דוחות ביצוע מענק החזר שכר לימוד, אישורי תשלום)
- תלושי שכר ממערכת מיכפל 2000
- אישורי רואי חשבון BDO לעמותות
- כל קבוצת PDFs עברית עם נתונים פיננסיים מובנים שצריך לאחד לטבלה

## אסטרטגיית עיבוד — 5 שלבים

### שלב 1: סקירה ראשונית
```bash
ls -la "$DIR" | sort -k5 -n   # מיון לפי גודל
python -c "
import fitz, os
for f in sorted(os.listdir('.')):
    if not f.endswith('.pdf'): continue
    doc = fitz.open(f)
    chars = sum(len(p.get_text()) for p in doc)
    print(f'{len(doc):3}p  {chars:6} chars  {f}')
"
```
- **chars > 1000** → טקסטואלי, חילוץ דרך `fitz` ישירות
- **chars = 0** → סריקה, צריך OCR ויזואלי
- **שמירה לJSON UTF-8** (ולא דרך bash stdout — זה משבר עברית)

### שלב 2: רינדור סריקות לתמונות
מסמכים מ-scanner-mobile מגיעים לרוב מסובבים landscape או mirrored. הקוד הסטנדרטי:
```python
import fitz, os
from PIL import Image, ImageOps
import io

# Test rotations on first page to find correct orientation
doc = fitz.open(file)
page = doc[0]
pix = page.get_pixmap(dpi=300)
img = Image.open(io.BytesIO(pix.tobytes('png')))
# Try: orig, rotate 90/180/270, mirror, mirror+rotate
# Use Read tool to inspect each variant — the readable one wins
```

**דפוסים מוכרים מ-scanner-mobile ישראלי:**
- "ביצוע שכל" + טפסי משרד החינוך → **rotate 90°** מתקן
- אישור BDO → **rotate 180°**
- חלק מטפסי "אישור מענק" pages 1 vs 2 → דורשים זוויות שונות
- רוב הקבצים שיוצאים הפוך → **mirror** (PIL.ImageOps.mirror)

### שלב 3: OCR עם Gemini Vision
**מפתח API**: קרא מ-`GEMINI_API_KEY` במשתני הסביבה. אם אינו מוגדר - בקש מהמשתמש מפתח (חינמי ב-https://aistudio.google.com/apikey) ואל תחפש מפתחות בדיסק.

**מודל מומלץ**: `gemini-2.5-pro` — איכות גבוהה לכתב יד עברי. `gemini-3-pro-preview` חזק יותר אך עדיין preview. **לא** להשתמש ב-`gemini-2.0-flash-exp` (deprecated).

**Prompt קלאסי לדוח ביצוע** (ב-`scripts/gemini_ocr_template.py`):
```python
PROMPT = """המסמך בעברית, דוח ביצוע על תשלום מענקי החזר שכר לימוד למשרד החינוך.
חלץ במדויק. אם שדה לא ברור — null.

החזר JSON תקין:
{
  "שם_המוסד": "...", "סמל_מוטב": "...", "כתובת_המוסד": "...",
  "שם_איש_קשר": "...", "טלפון_איש_קשר": "...", "תקופת_דיווח": "...",
  "מורים": [
    {"מס_שורה": N, "ת.ז": "...", "שם_משפחה": "...", "שם_פרטי": "...",
     "טלפון_זמין": "...", "סכום_משרד_החינוך": NUM,
     "תשלומים_חודשיים": [{"חודש":"MM/YY", "סכום":NUM}],
     "סהכ_שולם_למורה": NUM}
  ]
}"""
```

**שימור אינקרמנטלי**: לכל דף שמור JSON אחרי הקריאה — אם תהליך נופל באמצע, לא צריך להתחיל מחדש.

**Rate limit**: `time.sleep(2)` בין דפים מספיק. עבור 65 דפים: ~5-6 דקות.

### שלב 4: בניית XLSX RTL
ראה `scripts/build_xlsx_template.py`. עיקרי הדרישות:
- `ws.sheet_view.rightToLeft = True`
- גופן David, גודל 11pt טקסט / 12pt כותרת bold
- `Alignment(readingOrder=2)` לכל תא
- כותרת ברקע אפור `D9D9D9`
- גבולות שחורים thin
- `freeze_panes = "A2"`
- מספרים עם פורמט `#,##0.00`

### שלב 5: בדיקה עצמית
**לכל שורה**:
- אם יש `סכום_מענק` → `הפרשה_לגמל = round(grant × 0.05, 2)`
- ספור תאי "לא ברור" (target: < 25% מהשדות)
- סכום כולל של כל המענקים
- חיפוש שורות עם כפילויות (אותו ת.ז.)

```python
err = 0
for r in range(2, ws.max_row+1):
    grant = ws.cell(r, COL_GRANT).value
    gemel = ws.cell(r, COL_GEMEL).value
    if isinstance(grant, (int,float)) and isinstance(gemel, (int,float)):
        if abs(gemel - round(grant*0.05, 2)) > 0.05:
            err += 1
print(f'Errors: {err}')
```

## חוקים מנחים (Rules)

1. **לעולם לא להמציא נתונים** — אם Gemini החזיר null או שדה חסר, רשום `"לא ברור"` ולא 0 או placeholder.
2. **ת.ז. ושמות בכתב יד הם הערכה** — סמן בעמודת הערות שדורש אימות צולב מול הבעלות.
3. **שיוך תלוש→דוח לפי סכום** — בקבצים שבהם Gemini טעה בת.ז. בכתב יד, השווה את `החזר שכל"מ` בתלוש לסכום בדוח (סטייה < 100 ₪).
4. **5% מהמענק** — תמיד מהסכום ששולם בפועל למורה (`paid`), לא מהסכום שאושר ע"י משרד החינוך (יכולים להיות שונים).
5. **חודש התלוש** — שדה "החזר שכל"מ" בתלוש מופיע פעם אחת או מפוצל. אם מפוצל - רשום שני החודשים.

## עמודות סטנדרטיות (Schema)

```
סמל מוטב | שם המטפל | טלפון | שם המורה | ת.ז. | חודש התלוש |
סכום משרד החינוך למוסד (₪) | סכום מענק בתלוש (₪) | הפרשה לגמל 5% (₪) |
מקור | הערות
```

## קבצים בסקיל

- `scripts/render_pdfs.py` — רינדור batch של PDFs לתמונות PNG עם autodetect rotation
- `scripts/gemini_ocr.py` — חילוץ structured JSON מ-images עם Gemini 2.5 Pro
- `scripts/build_xlsx.py` — בנייה של XLSX RTL מ-JSON
- `references/document_types.md` — מילון סוגי מסמכים (דוח ביצוע, תלוש, אישור BDO, אישור משרד החינוך, תלוש תואר שני)
- `references/handwriting_patterns.md` — דפוסי כתב יד נפוצים בטפסים האלו (אותיות בלתי קריאות, תיקונים בעיגול, חתימות מרובות)

## סיווג מסמכים נפוצים

| סוג | זיהוי | מבנה JSON |
|---|---|---|
| **A — אישור משרד החינוך** | "אישור קבלת מענק" + מספר טופס 4-ספרות | פרטי מורה יחיד |
| **B — תלוש שכר** | "מערכת מיכפל 2000" / "פרטי תשלומים" | תלוש פרטי מורה |
| **C — דוח ביצוע** | טבלה עם עמודות "סכום משרד החינוך" + "תשלום בפועל" | רשימת מורים |
| **D — אישור BDO** | לוגו BDO + "מספר רשום" + מכתב | מטא-דאטה של עמותה בלבד |
| **E — ריק/לא רלוונטי** | פחות מ-100 chars | דלג |

## מטפלים חוזרים (תיעוד לפרויקט)

מוסדות/עמותות מטפלות חוזרות בדרך כלל על פני כמה דוחות ותקופות דיווח. שווה
לתעד לכל פרויקט - בקובץ נפרד, לא בסקיל הגלובלי - את שמות המוסדות, מספרי
הזיהוי (סמל מוסד, מספר עמותה, תיק ניכויים) שזוהו, כדי לזרז זיהוי דוחות עתידיים
מאותו מטפל. אל תשמור נתונים מזהים אמיתיים (שמות מוסדות/מורים, ת"ז) בתוך קובצי
הסקיל עצמו.
