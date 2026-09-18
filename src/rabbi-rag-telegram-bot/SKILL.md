---
description: "Build a private Hebrew Telegram Q&A bot powered by RAG (Cohere embed-v4 + rerank-v3.5 + Qdrant Cloud + Claude Sonnet 4.6) over a specific rabbi's writings (folder of DOC/DOCX/PDF). Every answer cites source book + chapter/section. Deploys to Railway. Trigger phrases: 'בנה בוט רב', 'בנה בוט טלגרם על הרב', 'תבנה לי בוט על כתבי X', 'rabbi bot', 'telegram bot for rabbi X', 'RAG bot over writings of', 'בנה לי מאגר וקטורי על ספרי', 'בוט שאלות-תשובות על כתבי'."
---

# Rabbi RAG Telegram Bot Builder

מטרה: לבנות פרויקט חדש מאפס שעונה על שאלות בעברית מתוך כתבי רב מסוים, עם ציטוט מקור בכל תשובה. הסקיל בנוי על דפוס שנבדק והופץ בפרויקט מסוג `ramchal-bot` (Cohere + Qdrant + Claude + python-telegram-bot, Railway).

`<SKILL_DIR>` = התיקייה שמכילה את קובץ ה-SKILL.md הזה (בדרך כלל `~/.claude/skills/rabbi-rag-telegram-bot`). פענח אותה פעם אחת לנתיב מוחלט לפני הרצת פקודות - PowerShell/cmd לא מרחיבים `~` בתוך מרכאות.
`<PROJECT_DIR>` = תיקיית הפרויקט החדש שנבנה (ראה נגזרת מ-slug בהמשך).

## כשמפעיל את הסקיל

### Phase 0 — איסוף נתונים מהמשתמש (חובה לפני כל פעולה אחרת)

שאל את המשתמש 4 שאלות במשפט אחד או דרך `AskUserQuestion` (לפי שיקול דעת):

1. **שם הרב (קצר)** — איך לקרוא לו בתשובות. דוגמאות: "הרמח״ל", "האר״י הקדוש", "הבן איש חי"
2. **שם מלא + תקופה** — לטקסט `/about`. דוגמה: "רבי משה חיים לוצאטו (1707-1746)"
3. **תיקיית כתבים** — נתיב מלא לתיקייה עם DOC/DOCX/PDF. למשל: `C:\Users\<שם המשתמש>\Documents\<תיקיית-הכתבים>`
4. **slug טכני** — מילה אחת באנגלית קטנה, לשמות technical. דוגמאות: `ramchal`, `arizal`, `benishchai`
5. **תיקיית עבודה לפרויקטים** — היכן המשתמש שומר פרויקטי קוד (PROJECTS_ROOT), למשל `~/Documents` או `~/projects`. אם לא ידוע — שאל.

מ-slug נגזרים אוטומטית:
- `PROJECT_DIR` = `<PROJECTS_ROOT>/{slug}-bot`
- `QDRANT_COLLECTION` = `{slug}_v1`
- proposed bot name = `{slug}Bot` (המשתמש יצור ב-BotFather בעצמו)

### Phase 1 — אישור והכנות (לפני בנייה)

הצג למשתמש סיכום של הפרמטרים שיקבלת + רשימה של מה שהוא צריך לעשות במקביל:

> אני בונה לך את הפרויקט. במקביל, אם עוד לא עשית — לך ל-`@BotFather` בטלגרם:
> 1. `/newbot` → תן שם (למשל "{RABBI_NAME} Bot") → תן username (`{slug}Bot` או `{slug}_qa_bot`)
> 2. תקבל טוקן בפורמט `123456:ABC-...` — תן לי אותו כשתסיים.
>
> ה-`user_id` שלך בטלגרם ייקבע אוטומטית: שלח `/start` לבוט אחרי שהוא יעלה, והוא יציג לך את המזהה שלך כדי שתוסיף אותו ל-whitelist (`TELEGRAM_ALLOWED_USER_IDS`).

### Phase 2 — איסוף credentials

הבוט דורש ארבעה מפתחות/פרטים: `COHERE_API_KEY`, `QDRANT_URL` + `QDRANT_API_KEY`, `ANTHROPIC_API_KEY`, ו-`TELEGRAM_BOT_TOKEN`. **בקש אותם מהמשתמש** (או הפנה אותו למקום שבו הוא יוצר כל אחד — ראה קישורים ב-`templates/.env.example.tmpl`) ושמור אותם אך ורק ב-`.env` של הפרויקט החדש. **אל תחפש ואל תקרא מקבצי `.env` קיימים של פרויקטים אחרים במחשב** — גם אם למשתמש יש מפתחות דומים שמורים במקום אחר, זו אחריותו למסור אותם מחדש; אל תניח נתיב או תנחש היכן הם שמורים.

### Phase 3 — יצירת תיקיית הפרויקט + העתקת templates

צור את התיקייה `{PROJECT_DIR}` + תתי-התיקיות: `extractors/`, `ingest/`, `rag/`, `scripts/`, `data/`, `tmp/converted/`, `docs/memory/`.

העתק את כל הקבצים מ-`<SKILL_DIR>/templates/` לפרויקט החדש. **לכל קובץ עם סיומת `.tmpl` — בצע substitution על placeholders** ושמור ללא ה-`.tmpl`:

| Placeholder | החלפה |
|-------------|--------|
| `{{RABBI_NAME}}` | שם קצר (Phase 0 שאלה 1) |
| `{{RABBI_FULL_NAME}}` | שם מלא + תקופה (Phase 0 שאלה 2) |
| `{{SLUG}}` | slug (Phase 0 שאלה 4) |
| `{{SOURCE_DIR}}` | נתיב הכתבים (Phase 0 שאלה 3) |
| `{{QDRANT_COLLECTION}}` | `{slug}_v1` |
| `{{TELEGRAM_BOT_TOKEN}}` | מהמשתמש |
| `{{OWNER_USER_ID}}` | ריק בהתחלה - יתמלא אחרי `/start` ראשון (ראה Phase 1) |
| `{{COHERE_API_KEY}}` | מ-Phase 2 |
| `{{QDRANT_URL}}` | מ-Phase 2 |
| `{{QDRANT_API_KEY}}` | מ-Phase 2 |
| `{{ANTHROPIC_API_KEY}}` | מ-Phase 2 |
| `{{EXAMPLE_QUESTIONS}}` | 5 שאלות שמתאימות לרב (Phase 6 — תייצר לפי שמות הספרים) |
| `{{BOOKS_LIST_SHORT}}` | רשימת 5-8 ספרים עיקריים, מופרדים בפסיק |

קבצים שלא צריכים substitution (העתק as-is): `extractors/*.py`, `ingest/chunk.py`, `ingest/convert.py`, `ingest/discover.py`, `ingest/embed.py`, `ingest/manifest.py`, `ingest/store.py`, `ingest/run_ingest.py`, `rag/retrieve.py`, `rag/answer.py`, `scripts/*.py`, `Dockerfile`, `railway.toml`, `.gitignore`, `.dockerignore`, `requirements.txt`.

### Phase 4 — בניית `data/books_index.json`

זה החלק היחיד שדורש שיקול דעת לרב הספציפי. ראה את ה-guide המלא ב-`<SKILL_DIR>/books-index-guide.md`. בקצרה:

1. רוץ `Glob` על `{SOURCE_DIR}/**/*` כדי לקבל את כל הקבצים
2. סנן רק `.txt/.doc/.docx/.pdf` (לא `.mp3/.jpg/.gif`)
3. לכל קובץ — קבע:
   - `book`: שם הספר הרשמי (ייתכן שכמה קבצים שייכים לאותו ספר, למשל `קיצור הכוונות/חודש אלול.doc`)
   - `subsection`: חלק/פרק/חודש/חג (אם רלוונטי, אחרת `null`)
   - `is_primary`: `true` אם הרב כתב את זה בעצמו, `false` לביאורים/מאמרים על
   - `preferred`: `true` כברירת מחדל. **עדיפות פורמט כשיש כפילויות: TXT > PDF > DOCX > DOC** (TXT הכי נקי, DOC הכי בעייתי). רק לפורמט המועדף `preferred:true`, ליתר `preferred:false`.
4. שמור ל-`{PROJECT_DIR}/data/books_index.json`

### Phase 5 — התקנת dependencies + LibreOffice

```powershell
# בודק LibreOffice
Test-Path "C:\Program Files\LibreOffice\program\soffice.exe"
# אם לא קיים:
winget install -e --id TheDocumentFoundation.LibreOffice --accept-package-agreements --accept-source-agreements --silent

# venv + deps
cd {PROJECT_DIR}
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Phase 6 — שאלות smoke test רב-ספציפיות

תן ל-LLM (אתה) להציע 5 שאלות smoke + 1 negative test, על בסיס הספרים שב-books_index.json. דוגמאות:

| Rabbi | שאלות מתאימות |
|-------|---------------|
| הרמח״ל | "מה זה זריזות?" (מסילת ישרים), "מהי תכלית הבריאה?" (דרך השם), "מה אומר הרמח״ל על תיקון חצות?" (קיצור הכוונות), "ההבדל בין שכר לעונש?" (דעת תבונות), "מהם פרצופים?" (קל״ח פתחי חכמה) |
| <RABBI_NAME> אחר (רב עכשווי, למשל) | שאלות ליבה לפי תחומי העניין של כתביו (אמונה/הלכה/מוסר/חינוך וכו') — לפי מה שמופיע ב-books_index.json |
| Negative test | תמיד: "מה דעת הרב על בינה מלאכותית?" (אמור להחזיר "לא מצאתי") |

עדכן את `{{EXAMPLE_QUESTIONS}}` ב-`bot.py` (`/help`) ו-`scripts/smoke_all.py` בהתאם.

### Phase 7 — ingestion + בדיקות

```powershell
$env:PATH = "$env:PATH;C:\Program Files\LibreOffice\program"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

cd {PROJECT_DIR}

# קודם בדיקה: קובץ אחד
.\.venv\Scripts\python.exe -X utf8 -m ingest.run_ingest --only "<שם קובץ קצר>"
.\.venv\Scripts\python.exe -X utf8 scripts/smoke_query.py "<שאלה רלוונטית>"

# אם עבד — full ingestion (~15-25 דק' עקב Cohere trial rate limit)
.\.venv\Scripts\python.exe -X utf8 -u -m ingest.run_ingest 2>&1 | Tee-Object -FilePath ingest_run.log
# הרץ ברקע (run_in_background:true) ועקוב

# אחרי סיום
.\.venv\Scripts\python.exe -X utf8 scripts/stats.py
.\.venv\Scripts\python.exe -X utf8 scripts/smoke_all.py
```

**אם Cohere נחנק עם 429 (Too Many Requests)** — זה הצפוי בTrial (100K tokens/min). הקוד ב-`ingest/embed.py` כבר מטפל בזה עם `BATCH_SIZE=32` + `SLEEP=12s` + retry 8 attempts. אם עוד נחנק → להגדיל את ה-SLEEP ל-20s.

### Phase 8 — test לוקלי + deploy ל-Railway

```powershell
# טסט bot לוקלי
.\.venv\Scripts\python.exe -X utf8 -u bot.py 2>&1 | Tee-Object -FilePath bot.log
# חכה ל-"Application started" → הרוג אותו (Ctrl+C או TaskStop)

# Railway
railway whoami                              # אם לא מחובר: railway login
railway init --name {slug}-bot
railway add --service {slug}-bot
railway variables --set "TELEGRAM_BOT_TOKEN=..." --set "TELEGRAM_ALLOWED_USER_IDS=..." --set "COHERE_API_KEY=..." --set "QDRANT_URL=..." --set "QDRANT_API_KEY=..." --set "QDRANT_COLLECTION={slug}_v1" --set "ANTHROPIC_API_KEY=..." --set "ANTHROPIC_MODEL=claude-sonnet-4-6" --service {slug}-bot
railway up --service {slug}-bot --detach

# בדיקה
railway logs --build           # Build Docker
railway logs --deployment      # Runtime — אמור להראות "Application started"
```

### Phase 9 — תיעוד וסגירה

עדכן את המסמכים הפנימיים של הפרויקט החדש:
1. `{PROJECT_DIR}/CHANGELOG.md` — entry `[1.0.0] — YYYY-MM-DD` עם רשימת ספרים שנקלטו ומספרי chunks
2. `{PROJECT_DIR}/docs/memory/primer.md` — מצב + next steps
3. `git init` + commit ראשון בפרויקט החדש (ואם למשתמש יש GitHub — צור repo ודחוף)

הצג סיכום סופי למשתמש:
- שם בוט בטלגרם (קישור `t.me/{bot_name}`)
- מספר vectors שעלו
- תוצאות smoke tests
- Railway dashboard URL
- מה לעשות הלאה (לשלוח `/start` לבוט)

---

## Tunables אם צריך לכוון אחרי deploy

ב-`config.py` (או ב-Railway env vars לאחר deploy):
- `TOP_K_VECTOR=20` → אם הreranker מפספס מקורות, העלה ל-30
- `RERANK_SCORE_THRESHOLD=0.15` → אם הbot מחזיר "לא מצאתי" יותר מדי, הורד ל-0.10
- `CHUNK_SIZE=1500` → אם השאלות דורשות יותר context, העלה ל-2000
- `ANSWER_TEMPERATURE=0.2` → אם התשובות שטחיות, העלה ל-0.4 (אבל סיכון הזיות עולה)

## פתרון בעיות נפוצות

| בעיה | פתרון |
|------|--------|
| `.DOC` נכשל (0 chunks) | זה PDF סרוק (ללא OCR) או DOC ריק. דלג ידנית ב-books_index.json (`preferred:false`). |
| Cohere 429 לאורך זמן | הגדל `SLEEP_BETWEEN_BATCHES` ב-`ingest/embed.py` ל-20s. |
| `ConnectError` בStart של bot | רגיל — Python-telegram-bot מתחיל לפני שhttpx pool מוכן. retry אוטומטי. |
| Qdrant collection size mismatch | מחק collection מ-Qdrant Cloud GUI ו-rerun ingestion (vectors יחזרו). |
| Hebrew encoding ב-PowerShell | תמיד הוסף `$env:PYTHONIOENCODING="utf-8"; $env:PYTHONUTF8="1"; [Console]::OutputEncoding = [System.Text.Encoding]::UTF8` |
| ScheduleWakeup לא לפולינג! | הharness מחזיר notification אוטומטית כשbackground task מסתיים. אל תקרא ScheduleWakeup ל-polling. |

## עלות חודשית משוערת

- Cohere trial: חינם. אחרי trial — 5-10$
- Qdrant Cloud free tier: 0$ (~7MB vectors מתוך 1GB)
- Anthropic Sonnet 4.6: 5-10$ בשימוש פרטי (50-100 שאלות/יום)
- Railway Hobby: 5$
- **סה״כ trial: ~5-10$/חודש**
