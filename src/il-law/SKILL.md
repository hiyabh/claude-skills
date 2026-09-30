---
name: il-law
description: |
  Live, cited Israeli legal research from official free sources only: Knesset law register (validity, amendments), Reshumot gazette PDFs, Wikisource consolidated statutes, Supreme Court rulings (search + full text), data.gov.il (decisive appraisers, companies), iplan plans, Sefaria. No Nevo/Takdin. Every legal claim gets an official link + retrieval date; unverified claims are labelled.
  TRIGGER on Hebrew: "פסק דין", "פסיקה", "הלכה", "בית משפט", "העליון", "בג"ץ", "תקדים", "חוק", "סעיף", "תקנות", "רשומות", "הצעת חוק", "מה הדין", "מה החוק אומר", "האם חוקי", "חוזה", "תביעה", "ערעור", "היטל השבחה", "שמאי מכריע", "תב"ע", "מיסוי מקרקעין", "פינוי בינוי", "תמ"א 38", "הגנת הדייר".
  English: "Israeli law", "Israeli court", "Supreme Court of Israel", "ruling", "statute", "Knesset", "regulation", "case law".
  USE THIS before stating what Israeli law or case law says - in answers, memos, contract reviews or other skills. NOT for halacha on its own, NOT for documents without legal claims.
---

# il-law - מחקר משפטי ישראלי עם מקורות חיים

הסקיל עונה על שאלות משפט ישראלי **מתוך מקור רשמי שנשלף עכשיו**, לא מזיכרון המודל. הסקריפטים ב-`scripts/` מדפיסים JSON אחיד: `status`, `source_url`, `authority` (official / community / metadata), `retrieved_at`, `warnings`, `data`. אין נבו ואין תקדין - לא כקישור ולא כסריקה.

`<SKILL_DIR>` = התיקייה שמכילה את ה-SKILL.md הזה (בדרך כלל `~/.claude/skills/il-law`). לפתור אותה פעם אחת לנתיב מוחלט לפני הרצת פקודות - PowerShell/cmd לא מרחיבים `~` בתוך מרכאות.

הרצה: `python <SKILL_DIR>/scripts/<script>.py <command> ...` (Python 3.10+, חבילות `requests`, `beautifulsoup4`, `pymupdf`; `truststore` רצוי מאחורי proxy ארגוני. ללא מפתחות API). ה-JSON קריא; להוסיף `--help` לכל סקריפט לרשימת הפקודות. בדיקה ראשונה אחרי התקנה: `python <SKILL_DIR>/scripts/selftest.py`.

## 1. איזה כלי לאיזו שאלה

| השאלה | כלי | מה מקבלים | דרגה |
|---|---|---|---|
| "מה אומר סעיף X בחוק Y" | `wikisrc.py get --title "חוק Y" --section X` ואז `cite.py law --id <ID> --title "חוק Y"` | נוסח משולב + אימות שהחוק תקף ושהנוסח לא מפגר אחרי התיקון האחרון | community + metadata |
| "האם חוק Y בתוקף / מה תוקן לאחרונה" | `knesset.py law --id <ID>` (ID ב-`references/law_ids.md`, או `knesset.py search --name`) | תוקף, תאריך תיקון אחרון, PDF רשמי של כל תיקון | metadata + official |
| "הנוסח הרשמי כפי שפורסם" | `reshumot.py search --text "..." --series statuteBook` -> `reshumot.py pdf --path ...` | PDF של ס"ח / ק"ת / י"פ מהמדפיס הממשלתי | official |
| "תקנות בנושא..." | `reshumot.py search --text --series generalSL` ; `knesset.py secondary --name` ; `wikisrc.py find --name "תקנות ..."` | תקנות שפורסמו / שמונחות בוועדה / נוסח משולב | official / community |
| "הצעת חוק / מה קורה בכנסת עם..." | `knesset.py bills --name "..." --knesset 25` ; MCP `knesset` (`search-bills-by-name`, פרמטר `keyword`) | הצעות + מסמכי הקריאות + סטטוס | official |
| "כוונת המחוקק / דיוני ועדה" | `knesset.py query --entity KNS_DocumentCommitteeSession --filter "contains(DocumentName,'...')"` | פרוטוקולי ועדות (DOC/PDF) | official |
| "מה פסק העליון על..." | `supreme.py search --text "..." --from 2015-01-01 [--type verdict]` -> `supreme.py get --path --file` | רשימת הליכים + טקסט מלא (HTML, סדר RTL נכון) + קישור PDF | official |
| "פסק דין ע"א 1642/24 קיים?" | `cite.py case --num 1642 --year 2024` | found / not_found + קישורים | official |
| "פסיקה של ערכאות נמוכות" | MCP `il-eli` -> `il_search_case_law` (קורפוס 10,558 פסקי דין, רובם משפחה, 2018-2025) ; אחרת: `references/blocked.md` | **חלקי בלבד** - לומר במפורש מה לא נבדק | research corpus |
| "היטל השבחה / שמאי מכריע בגוש-חלקה" | `datagov.py samay --q "..." --filter block=6158` -> `datagov.py samay-pdf --url` | 31,446 הכרעות עם PDF רשמי | official |
| "מי בעלי החברה / האם החברה פעילה" | `datagov.py company --q "..."` ; MCP `data-gov-il` | רשם החברות (מעודכן יומי) | official |
| "מה סטטוס תכנית / מתי פורסמה ברשומות" | `iplan.py plan --number "101-..."` ; `iplan.py plans --name --city` | סטטוס, תאריכי הפקדה/אישור/פרסום, קישור mavat | official |
| הנחיות יועמ"ש, חוזרי מס, החלטות ממשלה, פסיקת דוברות, בתי דין רבניים | Playwright MCP לפי `references/blocked.md` | דפדפן בלבד (Cloudflare) | official |
| משפט עברי כהקשר | `sefaria.py text --ref` / `search --text` ; MCP `sefaria` | טקסט + קישור, **לא דין מחייב** | community |

שרתי ה-MCP הם ליד ונוחות. **כל ציטוט שמגיע משרת MCP מאומת ב-`cite.py` לפני מסירה** (`il-eli` מחזיר `lex_uri` לכנסת - להריץ עליו `cite.py law`).

## 2. פרוטוקול הציטוט - חובה, בלי חריגים

1. **כל טענה משפטית** (סעיף, הלכה, תוקף, סכום, מועד) נושאת: `[מקור: <דרגה> <url>, נשלף <YYYY-MM-DD>]`. הדרגה: **רשמי** (כנסת / רשומות / PDF של בית המשפט / data.gov.il), **קהילתי** (ויקיטקסט - תמיד עם "לא רשמי, גרסה מיום X"), **מטא-דאטה** (מרשם הכנסת: תוקף ותיקונים, בלי נוסח).
2. **אין קישור = "לא מאומת (מזיכרון)"** באותה שורה. לעולם לא להציג ידע מהזיכרון כאילו נשלף.
3. **חוק**: (א) נוסח מ-`wikisrc.py`; (ב) `cite.py law --id --title` - אם `text_current: false` או `in_force: false`, לכתוב זאת ליד הציטוט; (ג) לשאלה על תיקון ספציפי - ה-PDF מ-`knesset.py law` או מרשומות הוא המקור, לא ויקיטקסט.
4. **פסק דין**: מספר הליך, ערכאה, תאריך, שמות הצדדים, וקישור `pdf_url` **בדיוק כפי שהסקריפט החזיר אותו** (path + fileName + type - קישור קטום מוביל לדף הבית ולא לפסק). ציטוט מילולי והלכה **רק מתוך טקסט שנשלף ב-`supreme.py get`**, עם ציון הפסקה. אם לא נשלף - "לא נקרא, נמצא רק בחיפוש".
5. **שלילה**: לעולם לא "אין פסיקה בנושא" / "החוק לא מסדיר". אלא: "לא נמצא במקורות שנבדקו: העליון (ביטוי X, שנים Y-Z), ...; לא נבדקו: מחוזי ושלום (אין מאגר פתוח)".
6. **מה לא נבדק** נאמר בסוף כל תשובה, מתוך `references/blocked.md`, כשהוא רלוונטי לשאלה.
7. **משפט עברי** מסומן "הקשר, לא דין מחייב". **קורפוס `il-eli`** מסומן "קורפוס מחקרי, רישיון לא מתועד".
8. **הסקיל תומך מחקר ואינו ייעוץ משפטי.** כשההשלכה כספית או דיונית - לכתוב במפורש שעו"ד צריך לאשר, ומה בדיוק לבקש ממנו לבדוק.
9. לפני מסירה - **צ'ק-ליסט**: כל טענה מקושרת? כל דרגה מסומנת? כל תאריך שליפה קיים? `cite.py` רץ על כל מספר הליך ומזהה חוק? רשימת "לא נבדק" בסוף?

## 3. דוגמה מלאה - "מה הדין לגבי דייר סרבן בפינוי-בינוי?"

```
python scripts/knesset.py search --name "פינוי ובינוי"                # -> ID 2001158, תקף
python scripts/wikisrc.py get --title "חוק פינוי ובינוי (עידוד מיזמי פינוי ובינוי)"   # TOC
python scripts/wikisrc.py grep --title "חוק פינוי ובינוי (עידוד מיזמי פינוי ובינוי)" --text "מסרב"   # "סרבן" = 0 תוצאות; החוק אומר "סירוב בלתי סביר" (ס' 2)
python scripts/cite.py law --id 2001158 --title "חוק פינוי ובינוי (עידוד מיזמי פינוי ובינוי)"
python scripts/supreme.py search --text "דייר סרבן" --from 2015-01-01 --type verdict
python scripts/supreme.py get --path "<path>" --file "<file>" --max-chars 8000
python scripts/reshumot.py search --text "פינוי ובינוי" --series statuteBook   # התיקון האחרון כפי שפורסם
```

תשובה: סעיף + נוסח (קהילתי, גרסה מיום X, `text_current: true`) + הלכת העליון עם ציטוט מהפסקה שנקראה + קישורים + "לא נבדקו: מחוזי/שלום, ועדות ערר".

## 4. מלכודות שנמצאו בבנייה (2026-09-30)

- כתיב שונה בין המאגרים: כנסת "והבנייה", ויקיטקסט "והבניה". 0 תוצאות = לנסות כתיב אחר לפני שמסיקים שאין.
- כנסת מחזירה **עד 100 שורות לעמוד** בשקט; העליון **עד 500 תוצאות**. אזהרת `truncated` = לצמצם, לא להסיק "זה הכל".
- טקסט מ-PDF עברי מערבב ספרות ("1642/24" עלול להופיע הפוך). לציטוט מדויק מהעליון להשתמש ב-`supreme.py get` (HTML). מרשומות - לאמת מספרים מול ה-PDF עצמו.
- ויקיטקסט מפגר לפעמים אחרי תיקון (חוק המקרקעין: גרסה 2025-10-28 מול תיקון 2024-07 - עדיין current; חוקים אחרים לא). `cite.py law --title` בודק.
- `judgments.org.il` אוסר סורקי AI ב-robots.txt - **לא לשלוף ממנו**; מותר לתת למשתמש קישור ידני.
- שני שרתים לא הותקנו/הוסרו בכוונה: `kolzchut` (API מת), ומקורות מסחריים/מתווכים (`pipeworx`, `judaro`, `nevo-takdin`). לא להתקין אותם "כדי לעזור".
- `python scripts/selftest.py` - להריץ כשמקור מתנהג מוזר או פעם בחודש. כשמשהו נופל - `references/sources.md` מתעד מה היה נכון כשעבד.

## 5. פרטיות ופלט

- פסקי דין מכילים שמות של אנשים פרטיים. הם פומביים, אבל חלים כללי הגינות: מטרה לגיטימית, בלי איסוף עודף, בלי פרופיל על אדם שלא קשור לשאלה.
- כשהתוצר הוא מסמך Word - בלוק המקורות נכנס כרשימה בסוף המסמך, כל שורה: שם המקור, קישור, תאריך שליפה.

## 6. שרתי MCP - אופציונלי

הסקריפטים עומדים בפני עצמם. שרתי ה-MCP מוסיפים נוחות (וקורפוס פסיקה של ערכאות נמוכות שאין בסקריפטים). אם אחד לא מחובר (`claude mcp list`) - הסקריפטים מכסים את אותו מידע, חוץ מ-`il_search_case_law` ומדפדפן. התקנה בגרסאות נעוצות, אחרי שקוראים את הקוד:

```bash
python -m pip install il-eli-mcp==0.5.3
claude mcp add -s user il-eli -e IL_ELI_RUNTIME_URL= -e IL_ELI_BASE_URL=https://knesset.gov.il/Odata/ParliamentInfo.svc -- python -m il_eli_mcp
claude mcp add -s user knesset -- npx -y knesset-mcp@1.1.1
claude mcp add -s user data-gov-il -- npx -y data-gov-il-mcp@3.0.1
claude mcp add -s user --transport http sefaria https://mcp.sefaria.org/mcp
claude mcp add -s user playwright -- npx -y @playwright/mcp@0.0.83
```

`IL_ELI_RUNTIME_URL=` ריק מנטרל מניפסט שהשרת מושך מ-GitHub של המחבר ושיכול להחליף את כתובת ה-API. פירוט ב-`references/sources.md` סעיף 8.
