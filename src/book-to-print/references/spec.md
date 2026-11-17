# מפרט הכריכה (cover_spec.json)

קובץ אחד מחזיק כל מספר וכל מילה של הכריכה. משנים בו, ומריצים שוב. מתחילים מהעתקה של
`assets/cover_spec.hard.example.json` או `cover_spec.soft.example.json`. נתיבים יחסיים נמדדים מהתיקייה של המפרט.
כל המידות במ"מ.

## הספר
| שדה | ערכים | הערה |
|---|---|---|
| `title` | טקסט | שם הספר, גם לשמות הקבצים |
| `printer` | `offset` / `digital` / `bookpod` | פריסט: גלישה, סימנים, צבע, ברקוד |
| `binding` | `hard` / `soft` | |
| `direction` | `rtl` / `ltr` | עברית = rtl (החזית משמאל) |
| `trim` | `[רוחב, גובה]` | גודל הדף אחרי חיתוך |
| `pages` | מספר | אחרי הריפוד לכפולה |
| `paper` | `white-80` ועוד (`spine.py`) | או `caliper_per_leaf` (מ"מ לגיליון) מבית הדפוס |
| `spine_override` | מ"מ | רוחב שדרה מבית הדפוס. גובר על החישוב |
| `spine_reading` | `top-down` / `bottom-up` | כיוון הקריאה של שדרה מסובבת |

## כריכה קשה (`hard`)
`board` `[רוחב, גובה]`, `joint` (ביג), `wrap` (גלישה מסביב לקרטון), `board_thickness`, `spine_extra`.
ערך חסר מקבל הערכה, ו-`spec.py` מדפיס אותו כ"משוער".

## קובץ
| שדה | ברירת מחדל | |
|---|---|---|
| `bleed` | 3 (בוקפוד 3.2) | גלישה לחיתוך |
| `safe` | 6 | אזור בטוח מקצה הקרטון/הדף |
| `marks` | true (בוקפוד false) | סימני חיתוך וקיפול ושורת מידע |
| `colour` | `cmyk` (בוקפוד `rgb`) | |
| `icc` | `auto` | ISO Coated v2, או נתיב לפרופיל שבית הדפוס נתן |
| `dpi` | 300 | |
| `background` | `#ffffff` | צבע מתחת לציור |
| `output` | `{"folder": "לדפוס", "name": "..."}` | |

## ציור (`art`) ותמונות (`images`)
ראה `cover-art.md`. `images`: `[{"panel": "back", "file": "logo.png", "box": [x, y, w, h]}]`.

## טקסט (`text`) - רשימה, כל פריט:
| שדה | | |
|---|---|---|
| `panel` | `front` / `back` / `spine` | |
| `text` | | `\n` לשורה חדשה. בלי ניקוד |
| `font` | מפתח מתוך `fonts` | `fonts`: `{"title": "Bellefair-Regular.ttf", "body": "david.ttf"}` |
| `size` | נקודות | הגודל המרבי. הטקסט מוקטן עד שהוא נכנס לתיבה |
| `box` | `[x, y, רוחב, גובה]` | מ"מ מהפינה **השמאלית העליונה** של הקרטון/הדף. `x` = `"center"` ממרכז את התיבה על הקרטון (מומלץ - נשאר ממורכז גם כשהקרטון משתנה). בלי box: כל האזור הבטוח |
| `align` | `center` / `right` / `left` | ברירת מחדל: מרכז |
| `valign` | `top` / `middle` / `bottom` | |
| `leading` | 1.25 | מרווח בין שורות |
| `wrap` | true | שבירת שורות אוטומטית |
| `colour` | `cmyk 0 0 0 100` או `#rrggbb` | טקסט שחור קטן: `cmyk 0 0 0 100` |
| `orient` (שדרה) | `vertical` / `horizontal` | ברירת מחדל: מסובב בשדרה צרה מ-25 מ"מ |

בשדרה מסובבת `box` הוא `[מרחק מלמעלה, אורך]`, ו-`position` הוא `top` / `middle` / `bottom`.

## ברקוד (`barcode`)
`{"isbn": "978...", "zone": [40, 25], "position": "spine-bottom" | "outer-bottom" | "centre-bottom",
"edge": 10, "fill": "white" | "clear"}`. מסת"ב שגוי (ספרת ביקורת) עוצר את הבנייה.
בבוקפוד: `fill: clear` ובלי isbn - הם מדביקים תווית. בלי מסת"ב: `fill: clear` שומר את המקום ריק
(`white` מדפיס ריבוע לבן ריק, וה-build מזהיר).

שדות שמתחילים ב-`_` (כמו `_הערה`) הם הערות, והמנוע מתעלם מהם.

## מסמך ההנחיות (`brief`)
`{"interior": "<שם קובץ הפנים>", "notes": [...], "questions": [...]}`.
