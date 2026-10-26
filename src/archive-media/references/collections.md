# אוספים ושאילתות

המספרים נבדקו מול ה-API ב-2026-10-26.

| preset | אוסף | מה יש בו | פריטים |
|---|---|---|---|
| `prelinger` | `collection:prelinger AND mediatype:movies` | סרטי תדמית, חינוך, תעשייה ופרסומות, 1920-1980 | 10,468 (מתוכם 1,914 עם רישיון) |
| `78rpm` | `collection:georgeblood AND mediatype:audio` | Great 78 Project: תקליטי 78 סל"ד שעברו דיגיטציה | 187,039 |
| `live` | `collection:etree AND mediatype:etree` | Live Music Archive: הקלטות הופעות | 305,793 |
| `any` | בלי סינון אוסף | כל הארכיון. הדירוג עדיין חל | - |

האוסף הרחב `78rpm` (335,288 פריטים) כולל גם את `georgeblood`. ה-preset משתמש ב-`georgeblood` כי שם המטא-דאטה של השנה עקבי.

## תחביר

- השאילתה היא Lucene: `--query "computer OR automation"`, `--query "\"assembly line\""`, `--query "kitchen AND 1950s"`.
- שדות מועילים: `title:`, `subject:`, `description:` ו-`creator:`. לדוגמה: `--query "subject:(television) AND title:(future)"`.
- `--years 1950-1965` מסנן לפי שנת הפריט. ב-78 סל"ד כדאי `--years 1900-1925` כדי להישאר בטווח 🟢.

## שאילתות טובות לפי צורך

| צורך | preset | שאילתה |
|---|---|---|
| פרסומת טק רטרו | prelinger | `computer OR automation OR "electronic brain"` |
| "העתיד" בעיני העבר | prelinger | `future OR tomorrow OR "world of tomorrow"` |
| עיר ותנועה | prelinger | `traffic OR highway OR downtown` |
| מטבח ובית של שנות ה-50 | prelinger | `kitchen OR housewife OR appliance` |
| מפעל ומכונות | prelinger | `factory OR "assembly line" OR machinery` |
| טלפון ותקשורת | prelinger | `telephone OR communications` (למשל Century21964) |
| ג'אז ודאנס של שנות ה-20 | 78rpm | `foxtrot OR jazz` + `--years 1920-1925` |
| מוזיקה קלאסית ישנה | 78rpm | `symphony OR concerto OR overture` + `--years 1900-1925` |
| ראגטיים | 78rpm | `rag OR ragtime` + `--years 1900-1925` |

## טיפים

- **מיון:** ברירת המחדל היא `downloads desc`, כלומר הפריטים הפופולריים ראשונים, ובדרך כלל באיכות טובה יותר.
- **גרסאות כפולות:** ל-Prelinger יש לפעמים כמה גרסאות של אותו סרט. הגרסה שהועלתה אחרונה היא בדרך כלל באיכות הגבוהה ביותר. `inspect_item.py` בוחר את הקובץ ברזולוציה הגבוהה ביותר בתוך הפריט.
- **רזולוציה:** רוב סרטי Prelinger הם 640x480 (4:3). ההגדלה ל-1080p רכה, וזה חלק מהמראה. ב-`--fit crop` (ברירת המחדל) ממלאים את מסגרת 16:9 וחותכים בערך רבע מגובה התמונה. ב-`--fit pad` שומרים את כל התמונה עם פסים שחורים, וזה מראה ארכיוני מובהק.
