# books-index-guide

מדריך לבניית `data/books_index.json` — הקובץ שמייצר את הציטוטים בכל תשובה.

## למה זה חשוב

לכל chunk שעולה ל-Qdrant יש metadata: `book`, `subsection`, `is_primary`. הציטוט שClaude מחזיר ("מקור: מסילת ישרים פרק ג") מבוסס על המטא-דטה הזה. אם לא תייצר books_index.json טוב — הציטוטים יהיו שגויים או חסרים.

## פורמט

```json
{
  "_meta": {
    "description": "מיפוי שם-קובץ → ספר רשמי + is_primary + preferred",
    "version": 1
  },

  "<filename relative to SOURCE_DIR>": {
    "book": "<שם הספר הרשמי, כפי שיופיע בציטוט>",
    "subsection": "<חלק/חודש/חג — אם רלוונטי, אחרת השמט את הfield>",
    "is_primary": true,           // true = הרב עצמו כתב; false = ביאור עליו
    "preferred": true             // false = דלג על הקובץ (למשל כפילות DOC+PDF)
  }
}
```

## תהליך מומלץ (אוטומטי + ידני)

### שלב 1 — Glob

```python
# קוד שClaude מריץ אוטומטית
from pathlib import Path
files = sorted(Path(SOURCE_DIR).rglob("*"))
allowed = [f for f in files if f.suffix.lower() in {".txt", ".doc", ".docx", ".pdf"} and f.name not in {"Thumbs.db"}]
```

### שלב 2 — סיווג

עבור כל קובץ, Claude מחליט (לפי שם הקובץ ותיקיית-האב):

| שם קובץ | סיווג מוצע |
|---------|------------|
| `מסילת ישרים.pdf` | `book: "מסילת ישרים"`, `is_primary: true`, `preferred: true` |
| `מסילת ישרים.doc` | `book: "מסילת ישרים"`, `is_primary: true`, `preferred: **false**` (כפילות) |
| `ספר X/חודש אלול.doc` | `book: "X"`, `subsection: "חודש אלול"`, `is_primary: true`, `preferred: true` |
| `ביאורים/תולדות הרב.doc` | `book: "ביאור עליו"`, `subsection: "תולדות"`, `is_primary: false`, `preferred: true` |
| `Thumbs.db`, `*.mp3`, `*.jpg` | להשמיט לחלוטין (לא ב-index) |

### שלב 3 — הצג למשתמש לאישור

לפני שאתה כותב את הJSON, הצג למשתמש סיכום:

```
זוהו 60 קבצים (43 DOC + 7 DOCX + 10 PDF).
סיווג:
  • 45 קבצים → primary (כתבי הרב)
  • 8 קבצים → secondary (ביאורים)
  • 7 קבצים → preferred:false (כפילות DOC+PDF)

חלוקה לפי ספרים:
  • <ספר 1>: X קבצים
  • <ספר 2>: Y קבצים
  ...

האם הסיווג נראה נכון? אם לא — תקן את מה שצריך לפני ingestion.
```

### שלב 4 — כתיבת JSON

שמור ל-`{PROJECT_DIR}/data/books_index.json` בקידוד UTF-8.

## כללי אצבע לסיווג נכון

### "ספר" vs "subsection"
- **ספר** = יצירה רשמית של הרב (יש לה שם משלה).
- **subsection** = חלק בתוך הספר (פרק רחב, חודש, חג, נושא).

דוגמה: בתיקייה `ספר קיצור הכוונות לרמח״ל/` היו 26 קבצים — כולם שייכים לספר אחד "קיצור הכוונות", וכל קובץ הוא subsection (חודש אלול, סוד הפסח, וכו'). זה _לא_ 26 ספרים נפרדים!

### כפילויות (סדר עדיפות פורמטים)
לרוב, אותה יצירה קיימת בכמה פורמטים. **סדר עדיפות: TXT > PDF > DOCX > DOC**:
- **TXT preferred** (אם קיים) — הכי נקי, ללא markup. נפוץ באוספי תורה דיגיטליים שעברו עריכה ידנית
- **PDF preferred** (אם אין TXT) — נקי יותר מ-DOC, פלט מעוצב להדפסה
- **DOCX preferred** (אם אין TXT/PDF) — עדיף על DOC כי קל יותר לחילוץ
- **DOC** (Word 97-2003) — אחרון; דורש LibreOffice headless conversion ולעיתים נכשל
- **חריגים**: אם הPDF סרוק (image-based) או חסר חלקים — לרדת לפורמט הבא ברשימה

### is_primary
- `true` רק אם **הרב עצמו** כתב את הטקסט
- `false` ל: ביוגרפיה, מאמרים על הרב, ביאורים של ספרים שלו, תרגומים, מבואות מודרניים
- במידת הספק → `true` (קל יותר לסנן אחר-כך)

### שמות ספרים — איך להציג בציטוט
- השתמש בכתיב **המקובל** בעברית, עם גרשיים אם צריך: `קל״ח פתחי חכמה` (לא `קלח` ולא `קל"ח`)
- ספרים בעלי שני חלקים: `אדיר במרום ח״א`, `אדיר במרום ח״ב`
- שינויי תווים: `_` בשם קובץ → `״` בשם הספר (אם רלוונטי)

## דוגמה מלאה (קטע מ-ramchal-bot)

```json
{
  "_meta": {
    "description": "מיפוי שם-קובץ → ספר רשמי + is_primary + preferred",
    "version": 1
  },

  "מסילת ישרים.pdf":  {"book": "מסילת ישרים", "is_primary": true, "preferred": true},
  "מסילת ישרים.doc":  {"book": "מסילת ישרים", "is_primary": true, "preferred": false},
  "דעת תבונות.pdf":   {"book": "דעת תבונות", "is_primary": true, "preferred": true},
  "קל_ח פתחי חכמה.pdf": {"book": "קל״ח פתחי חכמה", "is_primary": true, "preferred": true},
  "אדיר במרום.pdf":   {"book": "אדיר במרום ח״א", "is_primary": true, "preferred": true},
  "אדיר במרום ח_ב.pdf": {"book": "אדיר במרום ח״ב", "is_primary": true, "preferred": true},

  "ספר קיצור הכוונות לרמח_ל/חודש אלול.doc":     {"book": "קיצור הכוונות", "subsection": "חודש אלול", "is_primary": true, "preferred": true},
  "ספר קיצור הכוונות לרמח_ל/סוד הפסח.doc":       {"book": "קיצור הכוונות", "subsection": "סוד הפסח", "is_primary": true, "preferred": true},

  "מכון רמח_ל/תולדות הרמח_ל.doc": {"book": "ביאור מכון רמח״ל", "subsection": "תולדות", "is_primary": false, "preferred": true}
}
```

## אזהרה — קבצים שיכשלו ב-ingestion

לפעמים PDF הוא **סקירת תמונה** (סרוק ללא OCR). ה-ingestion יחזיר `0 chunks` עבורם. אפשרויות:

1. **לדלג** — סמן `preferred: false` ב-books_index.json (פשוט)
2. **OCR** — להוסיף Tesseract ל-`extractors/pdf_x.py` (מורכב, לא נכלל ב-template)

ברירת מחדל: דלג + הזכר בdocumentation שזה לטיפול עתידי.
