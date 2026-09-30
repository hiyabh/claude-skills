# מה לא נגיש לסקריפט - ואיך בכל זאת

נבדק 2026-09-30. הרשימה הזו נאמרת למשתמש **במפורש** כשמקור רלוונטי לשאלה שלו נמצא כאן. לעולם לא "אין" - אלא "לא נבדק כי...".

## דרוש הרשאה רשמית - אין דרך עוקפת

| מקור | מה יש שם | למה חסום |
|---|---|---|
| נט המשפט (`court.gov.il`) - תיקים, כתבי טענות, פרוטוקולים, החלטות ביניים | כל ההליך האזרחי בערכאות הנמוכות | כרטיס חכם של עו"ד או הזדהות לאומית. אין API ציבורי. |
| פסקי דין חסויים / דלתיים סגורות | | לפי דין |

## חסום ב-Cloudflare / bot-challenge - דפדפן בלבד (Playwright MCP)

| מקור | כתובת | מה יש שם |
|---|---|---|
| אוספי gov.il | `https://www.gov.il/he/collectors/policies` וכל `gov.il/he/departments/...` | הנחיות היועמ"ש, החלטות ממשלה, חוזרי מנכ"ל |
| פסיקה מדוברות בתי המשפט | `https://www.gov.il/he/departments/dynamiccollectors/spokmanship_court` | פסקי דין נבחרים של מחוזי/שלום שהדוברות הפיצה |
| פסיקת בתי הדין הרבניים | `https://www.gov.il/he/departments/dynamiccollectors/verdict_the_rabbinical_courts` | |
| רשות המסים - חוזרים, החלטות מיסוי, ה"ב מיסוי מקרקעין | `https://www.gov.il/he/departments/israel_tax_authority` | `taxes.gov.il` מפנה לשם |
| רמ"י - החלטות מועצה ונהלים | `https://apps.land.gov.il/CouncilDecisions/` (Angular; PDF מרוכז ב-`.../assets/data/31/CouncilDecisions.pdf` יורד ישירות) | |
| מאגר החקיקה הלאומי של הכנסת | `https://main.knesset.gov.il/Activity/Legislation/Laws/Pages/LawPrimary.aspx?lawitemid=<ID>` | אותו מידע כמו OData - להשתמש ב-`knesset.py` |
| איתור החלטות (אנונימי) בנט המשפט | `https://www.court.gov.il/NGCS.Web.Site/HomePage.aspx` -> "איתור החלטות" | טופס ASP.NET; לא נבדק |

**נוהל דפדפן**: (1) לפתוח את הדף עם Playwright, (2) לאתר את המסמך, (3) אם מתקבל קישור `gov.il/BlobFolder/...pdf` - הוא **כן** יורד ישירות עם `cite.py url` / `net.get_pdf`, (4) לצטט את כתובת הדף + כתובת ה-PDF + תאריך.

## אין מאגר רשמי פתוח - לומר זאת

| תחום | מה נבדק |
|---|---|
| פסיקת מחוזי / שלום / עבודה באופן שיטתי | אין feed רשמי. `judgments.org.il` (4M+ פסקי דין, חינמי) **אוסר סורקי AI ב-robots.txt - לא באוטומציה**; מותר לתת למשתמש קישור לחפש בעצמו. `psakdin.co.il` - מצב paywall לא ברור. |
| ועדות ערר לתכנון ובנייה - החלטות | אין מאגר; רק דף הגשה ב-gov.il |
| ועדות ערר מס שבח | אין מאגר רשמי; רק אתרי עו"ד |
| המפקח על רישום מקרקעין - החלטות | אין מאגר רשמי. ערעורים עליו מגיעים למחוזי ולעליון - חפש בעליון "המפקח על רישום מקרקעין". |
| הוצאה לפועל | data.gov.il: דוחות סטטיסטיים שנתיים בלבד |

## מאגרים היסטוריים (לא עדכניים, לשימוש מחקרי)

- HuggingFace `LevMuchnik/SupremeCourtOfIsrael` - 751K פסקי דין של העליון בטקסט מלא, עד 2022, רישיון OpenRAIL.
- HuggingFace `guychuk/case-law-israel` - 10,558 פסקי דין של ערכאות נמוכות (רובם משפחה), 2018-2025, בלי רישיון מוצהר. זה הקורפוס של `il-eli` (`il_search_case_law`).
- Versa (Cardozo) `https://larc.cardozo.yu.edu/iscp-opinions` - תרגומים לאנגלית של פסקי דין נבחרים 2011-2024.
