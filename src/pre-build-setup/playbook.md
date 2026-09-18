# Playbook — Pre-Build Setup

רצף מפורט לביצוע. עקוב שלב אחר שלב. אל תדלג.

---

## שלב 0: סיווג פרויקט

שאל את המשתמש (או הסק מההקשר): מה אתה בונה?

**Web app / API / SaaS ייצור:**
- המשך ברצף
- לפרויקטים גדולים/קריטיים לייצור, שקול תהליך עבודה עם שכבות בקרה נוספות (Review/QA/Security) אחרי סיום הסקיל

**פיצ׳ר מהותי ב-project קיים:**
- המשך ברצף
- אין צורך בשכבות הבקרה הנוספות

**סקריפט / POC / notebook:**
- עצור. הסקיל לא רלוונטי.
- חזור לתהליך הפיתוח הרגיל שלך

---

## שלב 1: ראיון PRD

בסשן הנוכחי, הפעל AskUserQuestion בלולאה עד כיסוי מלא.

כסה את הקטגוריות הבאות:

**מוצר:**
- מה המוצר עושה, בשורה אחת
- מי המשתמש (פרסונה)
- 3 use cases מרכזיים

**UX:**
- Flow ראשי מההתחלה עד הסיום
- אילו מסכים / endpoints נדרשים
- מה חשוב להדגיש ויזואלית

**טכני:**
- Frontend framework
- Backend / DB
- Auth (אם רלוונטי)
- Hosting / deployment target

**Edge cases:**
- מה קורה אם אין נתונים (empty state)
- מה קורה אם יש שגיאה (error state)
- מה קורה בטעינה (loading state)
- הרשאות / תרחישי אבטחה

**אילוצים:**
- תקציב (אם רלוונטי)
- Deadline
- מספר משתמשים צפוי / RPS
- שפות (עברית? RTL?)

**Scope:**
- מה **לא** בפרויקט (לציין במפורש)

**סיכונים + Tradeoffs:**
- מה יכול להשתבש
- איפה יש שיקול דעת (A או B?)

**כללים לראיון:**
- אל תשאל שאלות ברורות מאליהן
- חפור בחלקים קשים שאולי לא חשבו עליהם
- המשך עד שאין שאלות קריטיות פתוחות

אחרי הראיון — כתוב ל-`docs/PRD.md` לפי `templates/PRD.md`.

אמור למשתמש: "PRD נכתב ל-docs/PRD.md. תעבור עליו ותגיד לי מה לתקן."

---

## שלב 2: constraints.md

מתוך הראיון + ידע כללי על הפרויקט, כתוב `docs/constraints.md` לפי `templates/constraints.md`.

**חוק הזהב:** כל אילוץ חייב חלופה.

פורמט: `אל תעשה X. תעשה Y במקום, כי Z.`

**לא מקובל:**
> אל תשתמש ב-localStorage.

**מקובל:**
> אל תשתמש ב-localStorage לטוקני auth. תשתמש ב-httpOnly cookies במקום, כי localStorage חשוף ל-XSS.

אילוץ ללא חלופה = אייג׳נט נתקע. הוא מוטה לפעולה.

---

## שלב 3: טסטים מ-PRD בסשן נפרד

**חשוב:** זה חייב להיות סשן נקי (או subagent), אחרת הטסטים יתאימו עצמם לאימפלמנטציה שכבר ראית.

הפעל subagent (Agent tool, subagent_type=general-purpose) עם פרומפט:

> קרא את `docs/PRD.md` בלבד. אל תסתכל על קוד קיים.
> 
> כתוב טסטים שמכסים את הדרישות במסמך. עבור כל דרישה:
> 1. זהה מה הדרישה מבטיחה
> 2. כתוב טסט שיכשל אם הדרישה לא מתקיימת
> 3. שמור ב-`tests/` לפי framework המתאים לפרויקט
> 
> אם ה-framework עוד לא נקבע — כתוב בפסאודו-קוד ברור, ואסמן ב-TODO להמיר אחרי scaffold.

חזור לסשן הראשי אחרי שהטסטים נכתבו.

---

## שלב 4: plan.md + feedback loop

כתוב `docs/plan.md` לפי `templates/plan.md`. חובה לכלול:

- מטרה בשורה אחת
- רשימת דרישות מ-PRD (עם רפרנס לסעיף)
- צעדים ממוספרים (1, 2, 3...)
- לכל צעד: אילו קבצים (נתיב מלא), מה לעשות, איך לאמת
- סיכונים לכל צעד
- סדר ביצוע עם commits
- מה **לא** נכלל בתכנית

אחרי כתיבה, בצע feedback loop:

1. אמור למשתמש: "plan.md נכתב. תפתח באדיטור, תקרא שורה-שורה, תוסיף הערות inline במקומות הרלוונטיים (למשל `<!-- NOTE: לא הגיוני, השנה ל-X -->`)."
2. המתן לאישור המשתמש שההערות הוספו
3. קרא את plan.md מחדש, עדכן לפי ההערות
4. חזור לשלב 1 עד שהמשתמש מאשר

**אסור לעבור לכתיבת קוד לפני אישור מפורש של plan.md.**

---

## שלב 5: progress.md + learnings.md

צור שני קבצים לפי התבניות (ריקים, מוכנים למילוי):

- `docs/progress.md` מ-`templates/progress.md`
- `docs/learnings.md` מ-`templates/learnings.md`

---

## שלב 6: עדכון CLAUDE.md של הפרויקט

אם אין עדיין `CLAUDE.md` בשורש הפרויקט — צור אחד.

הוסף (או וודא שקיים) סעיף:

```markdown
## Progress & Learnings Tracking (MANDATORY)

After EVERY completed task:
1. Update `docs/progress.md` — mark completed items, note what's next
2. If any mistake was made or unexpected issue discovered — add entry to `docs/learnings.md` with: what happened, root cause, how it was fixed, rule added to prevent recurrence
3. Commit with conventional commit message (`feat:`, `fix:`, `refactor:`, etc.)

## Reference Docs

- `docs/PRD.md` — product requirements
- `docs/constraints.md` — negative constraints (what NOT to do)
- `docs/plan.md` — implementation plan
- `docs/progress.md` — progress tracking
- `docs/learnings.md` — mistakes and lessons

Link references: @docs/PRD.md @docs/constraints.md @docs/plan.md
```

---

## שלב 7: Stress tests (תנאי)

בדוק: האם הפרויקט דורש load tests?

**כן, אם:**
- Web app / API עם משתמשים חיים
- יש SLA (availability / latency)
- צפי עומס > 100 RPS או > 1000 משתמשים חודשיים

**לא, אם:**
- CLI tool
- Library / SDK
- Admin dashboard פנימי עם < 10 משתמשים
- POC

אם כן ומותקן אצלך גם הסקיל `stress-test-setup` — הפעל אותו כעת. אחרת, הגדר בדיקות עומס בסיסיות ידנית.

---

## סיום

סיכום למשתמש:

```
Pre-build setup הושלם.

קבצים שנוצרו:
- docs/PRD.md (מאושר)
- docs/constraints.md
- docs/plan.md (מאושר)
- docs/progress.md (ריק)
- docs/learnings.md (ריק)
- tests/ (טסטים ראשוניים מ-PRD)
- CLAUDE.md (עודכן)

הצעד הבא: מתחילים לממש לפי plan.md, החל מהיכרות עם הקוד הקיים (recon).
תזכורת: כל משימה שנסגרת → עדכון progress.md + learnings.md (אם היה תיקון).
```
