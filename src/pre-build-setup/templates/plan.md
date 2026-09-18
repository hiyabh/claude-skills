# Implementation Plan — [שם הפיצ׳ר / פרויקט]

**סטטוס:** draft / under review / approved / implementing / done
**מבוסס על:** `docs/PRD.md` (סעיפים [X, Y])
**תאריך:** YYYY-MM-DD

---

## מטרה

מה אנחנו בונים, בשורה אחת.

## דרישות מה-PRD

- [ ] דרישה 1 (PRD §4.1)
- [ ] דרישה 2 (PRD §4.2)
- [ ] דרישה 3 (PRD §4.3)

## Preconditions

מה חייב להיות מוכן לפני שמתחילים:

- [ ] Dependencies מותקנות
- [ ] `.env` מוגדר
- [ ] DB schema קיים
- [ ] MCP X מחובר

---

## צעדים

### שלב 1: [שם השלב]

**קבצים:**
- `src/foo/bar.ts` — חדש
- `src/types.ts` — עדכון
- `tests/bar.test.ts` — חדש

**מה לעשות:**
1. ...
2. ...
3. ...

**אימות:**
- טסט `tests/bar.test.ts` עובר
- `npm run build` ללא שגיאות
- Lint נקי

**סיכונים:**
- ...

<!-- NOTE: הערות מהמשתמש כאן -->

---

### שלב 2: [שם השלב]

**קבצים:**
- ...

**מה לעשות:**
1. ...

**אימות:**
- ...

**סיכונים:**
- ...

<!-- NOTE: -->

---

### שלב N: [שם השלב]

...

---

## תלויות חיצוניות

- **Package X** — למה צריך? גרסה? bundle size?
- **MCP Y** — כבר מחובר? אם לא, איך מחברים?
- **API Z** — rate limits? authentication?

## מה **לא** נכלל בתכנית הזו

ציין במפורש מה מחוץ ל-scope של הפרויקט/פיצ׳ר הזה:

- ...
- ...

## סדר ביצוע + Commits

```
שלב 1 → commit: "feat: [שלב 1 תיאור]"
שלב 2 → commit: "feat: [שלב 2 תיאור]"
שלב 3 → commit: "feat: [שלב 3 תיאור]"
final → commit: "docs: update progress and learnings"
```

## Verification Final

בסיום כל השלבים:

- [ ] כל הדרישות מ-PRD מסומנות
- [ ] כל הטסטים עוברים
- [ ] `npm run build` מצליח
- [ ] Lint נקי
- [ ] Manual test של golden path
- [ ] Manual test של 2-3 edge cases
- [ ] `docs/progress.md` עודכן
- [ ] `docs/learnings.md` עודכן (אם היו טעויות)

---

## Feedback Loop

**המשתמש:** פתח קובץ זה באדיטור, קרא שורה-שורה, הוסף הערות `<!-- NOTE: ... -->`.

**Claude:** אחרי שהמשתמש אומר "קרא שוב" — קרא את ההערות, עדכן את התכנית, הסר את `NOTE` לאחר טיפול.

**Loop:** חזור עד שהמשתמש אומר "approved".

**עד אישור מפורש — אפס קוד.**
