# מקורות: endpoints, גופי בקשה ומוזרויות

נבדק חי ב-2026-09-30. ארבעה מהמקורות (רשומות, עליון) הם API פנימיים לא מתועדים - כשמשהו נשבר, `python scripts/selftest.py` אומר איפה, וכאן כתוב מה היה נכון ביום שעבד.

## 1. כנסת - OData v4 (`scripts/knesset.py`)

- Base: `https://knesset.gov.il/OdataV4/ParliamentInfo/` (יש גם v3 ב-`/Odata/ParliamentInfo.svc/`, מפתחות שונים: `IsraelLawID` במקום `Id`).
- ללא מפתח. כל UA עובד. **כל עמוד מוגבל ל-100 שורות** בשקט (`$top=5000` עדיין מחזיר 100); הסקריפט מזהיר.
- ישויות: `KNS_IsraelLaw` (מרשם החוקים + `LawValidityDesc`: תקף/בטל/פקע/נושן), `KNS_LawBinding` (תיקונים: `IsraelLawID` -> `LawID`), `KNS_Bill` (+`KNS_DocumentBill` - החוק המתקן מאוחסן כהצעת חוק שהושלמה; המסמך "חוק - פרסום ברשומות" הוא ה-PDF הרשמי), `KNS_SecondaryLaw` (+`KNS_DocumentSecondaryLaw`), `KNS_DocumentCommitteeSession` (פרוטוקולים), `KNS_PlenumVote`.
- מסננים: `contains(Name,'...')`, `startswith`. גרש בתוך מחרוזת מוכפל `''`.
- `FilePath` מגיע לפעמים עם backslash (`https://fs.knesset.gov.il/25\law\...`) - הסקריפט מנרמל.
- `$expand=KNS_IsraelLawName` על `KNS_IsraelLaw(id)` מחזיר 500 - לא להשתמש.
- אין נוסח משולב. יש רק מטא-דאטה + PDF של כל תיקון ב-`fs.knesset.gov.il`.

## 2. ויקיטקסט - ספר החוקים הפתוח (`scripts/wikisrc.py`)

- `https://he.wikisource.org/w/api.php` - MediaWiki סטנדרטי. **חובה User-Agent תיאורי** (UA של python-requests מקבל 403).
- מבנה הדף: `{{ח:מאגר|<IsraelLawID>}}` בפתיח מקשר למזהה הכנסת; כל סעיף `{{ח:סעיף|<מספר>|<כותרת>|תיקון: ...}}`; סעיפי משנה `{{ח:תת|(א)}}`, `{{ח:תתת|(1)}}`; הפניות `{{ח:פנימי|...|טקסט}}`, `{{ח:חיצוני|...|טקסט}}`.
- הפלט כולל `revision_timestamp` ו-permalink (`?oldid=`). **קהילתי, לא רשמי**; `OpenLawBot` מעדכן יומיום אבל יש דפים מפגרים (חוק המקרקעין: גרסה 2025-10-28).
- קטגוריות לא שימושיות לחיפוש; `list=search&srsearch=intitle:...` עובד.

## 3. רשומות (`scripts/reshumot.py`)

- Base: `https://api.justice.gov.il/reshumot` (ה-frontend ב-`reshumot.justice.gov.il`). לא מתועד.
- **חובה** `User-Agent` דפדפני + `Origin: https://reshumot.justice.gov.il`. בלעדיהם התשובה היא `{"_event_transid": ...}` ריק - הסקריפט מזהה ומדווח `bad_payload`.
- `GET /akn-document-types` - הסדרות: `statuteBook` (ס"ח), `generalSL` (ק"ת), `municipalSL`, `taxesSL`, `publicNotices` (י"פ), `governmentBills`, `knessetGovernmentBills`, `newVersionBills`, `newVersionLaws`.
- `POST /search/portfolios` body: `{"freeText":"...","filters":{"seriesShortName":["statuteBook"]},"page":0,"sort":{"publishDate":"desc"},"searchInContent":false,"lang":"heb"}`. `filters` הוא אובייקט (מערך = 500). גודל עמוד קבוע 50. `searchInContent:true` מחפש בתוך המסמכים.
- `GET /official-gazette?ID=/officialGazette/statuteBook/3579&includePromulgationData=true` - תוכן עניינים + תיקונים עקיפים + פרסום מקורי.
- `GET /resolver?path=akn/il/officialGazette/statuteBook/3579/heb@2026-08-02` -> 302 ל-S3 חתום (תוקף שעה). הנתיב **בלי** `/` בהתחלה. הסקריפט לא עוקב אחרי ה-redirect אוטומטית אלא מוריד מה-`Location`.
- קישור לציטוט: `https://reshumot.justice.gov.il/#/view/officialGazette/statuteBook/3579` (portal_url בפלט).

## 4. בית המשפט העליון (`scripts/supreme.py`)

- אתר: `https://supremedecisions.court.gov.il/` (AngularJS). ה-backend נמצא מקריאת ה-JS של האתר.
- **סדר חובה**: `GET /` קודם (cookies), ואז `POST /Home/SearchVerdicts` עם `User-Agent` דפדפני, `Referer`, `Origin`, `X-Requested-With: XMLHttpRequest`. **curl נחתך (connection reset) - רק Python עובד.**
- גוף החיפוש: `{"document":{"Year":null,"CaseNum":null,"dateType":2,"publishDate":8,"SearchText":[{"Text":"...","textOperator":1,"option":2,"Inverted":false,"Synonym":false,"NearDistance":3,"MatchOrder":false}],"PublishFrom":"...T00:00:00.000Z","PublishTo":"...","Month":null,"OldMainNumFormat":false},"lan":1}`.
  - `dateType:2` = תאריך פסק הדין (עובד). `dateType:1` לא מסנן ישנים כמו שצריך.
  - חיפוש לפי מספר הליך: `Year` + `CaseNum` עם `SearchText` ריק.
  - **תקרה 500 תוצאות** - הסקריפט מסמן `truncated`.
- שורת תוצאה: `CaseDesc` (ע"א 1642-24), `CaseName`, `Type` (פסק-דין/החלטה), `VerdictsDtString`, `PathForWeb`, `FileName`, `Pages`.
- הורדה: `GET /Home/Download?path=<PathForWeb>&fileName=<FileName>&type=4` (PDF) / `5` (DOCX) / `2` (HTML). **ל-HTML סדר RTL לוגי נכון; חילוץ מ-PDF מערבב ספרות** - `supreme.py get` משתמש ב-HTML לטקסט וב-PDF לשמירה.
- WAF: דף "unauthorized activity detected" ב-HTTP 200 בפרץ בקשות. האטה 2 שניות לבקשה ב-`net.py`. תנאי השימוש של האתר לא נקראו (הקובץ לא נפתח) - נפח נמוך.

## 5. data.gov.il - CKAN (`scripts/datagov.py`)

- Base: `https://data.gov.il/api/3/action/` (`package_search`, `package_show`, `datastore_search`). ללא מפתח. הדף הראשי מחזיר 403 לסקריפט - רק ה-API.
- משאבים שמורים בסקריפט: `samay` (הכרעות שמאי מכריע, 31,446 שורות, `link` -> PDF ב-`free-justice.openapi.gov.il` שיורד ישירות), `companies` (רשם החברות), `ararim` (בית הדין לעררים), `regulation_index` (מאגר האסדרה - חוק -> ויקיטקסט/כנסת, מעודכן עד 2025-06).
- ה-API של free-justice עצמו (חיפוש) מחזיר 500 - להשתמש ב-CKAN כאינדקס ולהוריד לפי `link`.

## 6. מנהל התכנון - iplan (`scripts/iplan.py`)

- `https://ags.iplan.gov.il/arcgisiplan/rest/services/PlanningPublic/Xplan/MapServer/1/query` (שכבה 1 = "קוים כחולים-תכניות מקוונות"). ArcGIS REST, `f=json`.
- **TLS ישן**: השרת מציע ציפרים מתחת לרמת האבטחה של OpenSSL 3 -> `SSLV3_ALERT_HANDSHAKE_FAILURE`. `net.py` מרכיב adapter עם `DEFAULT:@SECLEVEL=1` ל-host הזה בלבד.
- שדות: `pl_number`, `pl_name`, `plan_county_name`, `internet_short_status`, `station_desc`, `depositing_date`, `pl_date7` (אישור), `pl_date_8` (**פרסום ברשומות**), `pl_url` (mavat), `pl_objectives`. תאריכים במילישניות epoch - הסקריפט ממיר.

## 7. ספריא (`scripts/sefaria.py`)

- `https://www.sefaria.org/api/texts/<ref>`, `POST /api/search-wrapper`. משפט עברי - הקשר, לא דין מחייב.

## 8. שרתי MCP מותקנים (user scope, `~/.claude.json`)

| שרת | גרסה נעוצה | כלים | הערת אבטחה מסקירת הקוד |
|---|---|---|---|
| `il-eli` | PyPI `il-eli-mcp==0.5.3` | `il_search_laws`, `il_get_law`, `il_search_law_texts`, `il_get_law_documents`, `il_search_case_law`, `il_get_case`, `il_coverage` | מוריד מניפסט "runtime" מ-GitHub releases של המחבר שיכול להחליף את כתובת ה-API. **נוטרל**: `IL_ELI_RUNTIME_URL=""` + `IL_ELI_BASE_URL` נעוץ לכנסת. cache/audit הופנו ל-`%LOCALAPPDATA%\il-law\il-eli`. הקורפוס (10,558 פסקי דין, HuggingFace `guychuk/case-law-israel`) ברישיון לא מתועד - למחקר בלבד, כל ציטוט ממנו מאומת מול המקור. |
| `data-gov-il` | npm `data-gov-il-mcp@3.0.1` | `find_datasets`, `get_dataset_info`, `list_resources`, `search_records`, ... (9) | פונה ל-data.gov.il בלבד. |
| `knesset` | npm `knesset-mcp@1.1.1` | `search-bills-by-name` (פרמטר `keyword`), `get-bill-info`, `list-bills-by-status`, `get-committee-info`, `list-committees`, `list-knesset-members`, `list-factions`, ... (9) | פונה ל-knesset.gov.il בלבד. |
| `sefaria` | HTTP `https://mcp.sefaria.org/mcp` | `get_text`, `text_search`, `get_links_between_texts`, ... (14) | השרת הרשמי של ספריא (בעל הנתונים). הגרסה המקומית היא HTTP-only עם הגנת host, לכן נבחר המארח הרשמי. |
| `playwright` | npm `@playwright/mcp@0.0.83` | דפדפן | Microsoft. למקורות החסומים ב-Cloudflare (ראה `blocked.md`). |

**הוסר**: `@skills-il/kolzchut-mcp` - ה-API של כל-זכות (`/w/api.php`) מחזיר 404, השרת שבור upstream. **לא הותקנו**: `pipeworx` (שאילתות דרך שרת צד ג'), `judaro` (מסחרי), `Ansvar` (מת), `nevo-takdin-courts-mcp` (מקורות מסחריים).
