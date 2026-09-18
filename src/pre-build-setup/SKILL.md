---
name: pre-build-setup
description: Use this skill at the very start of a meaningful project or substantial feature, before any code is written. Sets up PRD, negative constraints, tests-from-PRD, reviewable implementation plan, and progress/learnings tracking. Trigger when user says "אני רוצה לבנות X", "פרויקט חדש", "נבנה פיצ׳ר משמעותי", "start new project", or before starting a multi-file feature with architectural decisions. Skip for bug fixes, refactors, single-file scripts, quick POCs, or data analysis notebooks.
---

# Pre-Build Setup

מבוסס על פרק 13 של "אני בונה אייג׳נטים". מטרת הסקיל: לסגור את הפער שבין רעיון לקוד לפני שהאייג׳נט קופץ פנימה ובונה משהו שלא תואם למה שרצינו.

## מתי כן להפעיל

- Web app / API / SaaS / מערכת ייצור
- פיצ׳ר מהותי שנוגע ב-3+ קבצים עם החלטות ארכיטקטוניות
- כל פרויקט עם משתמשים אמיתיים או לוגיקה עסקית
- פרויקט חדש מ-scratch

## מתי לא להפעיל

- תיקון באג (השתמש בתהליך תיקון-באגים הרגיל שלך, למשל סקיל debug אם קיים אצלך)
- Refactor מקומי (השתמש בתהליך רה-פקטורינג רגיל)
- סקריפט יחיד / POC מהיר / notebook ניתוח
- שינוי טקסט / סגנון
- פיצ׳ר טריוויאלי בקובץ אחד

## הרצף

הפעל את `playbook.md` שבתיקייה זו. השלבים:

1. **סיווג** — האם מדובר בפרויקט/פיצ'ר גדול שדורש שכבות בקרה נוספות (Review/QA/Security)?
2. **PRD** — ראיון עם AskUserQuestion → `docs/PRD.md`
3. **Constraints** — אילוצים שליליים + חלופות → `docs/constraints.md`
4. **Tests from PRD** — סשן נפרד, טסטים מהמפרט בלבד
5. **Plan + Feedback loop** — `docs/plan.md` + הערות inline עד אישור
6. **Tracking files** — `docs/progress.md` + `docs/learnings.md`
7. **Update project CLAUDE.md** — הנחיות עדכון מפורשות
8. **Stress tests** (תנאי) — אם מותקן אצלך גם הסקיל `stress-test-setup`, הפעל אותו כעת אם רלוונטי (אחרת אפשר להגדיר בדיקות עומס ידנית)

## תבניות

בתיקיית `templates/` יש:

- `PRD.md` — תבנית דרישות מוצר
- `constraints.md` — תבנית אילוצים שליליים
- `plan.md` — תבנית תכנית אימפלמנטציה
- `progress.md` — תבנית מעקב התקדמות
- `learnings.md` — תבנית תיעוד טעויות

העתק כל תבנית ל-`docs/` של הפרויקט ומלא לפי הפלט של הראיון.

## כלל קריטי

**אל תכתוב שורת קוד לפני שהמשתמש אישר את `plan.md`.**

זו הסיבה היקרה ביותר לכישלון פרויקטי AI: אימפלמנטציה שעובדת בבידוד אבל שוברת את המערכת הקיימת. התכנון מונע את זה.

## תפוקה מצופה בסוף הסקיל

```
docs/
├── PRD.md          (מלא, מאושר)
├── constraints.md  (עם חלופות)
├── plan.md         (מאושר על ידי המשתמש)
├── progress.md     (ריק, מוכן למילוי)
└── learnings.md    (ריק, מוכן למילוי)

tests/              (טסטים ראשוניים מ-PRD)

CLAUDE.md           (עודכן עם חוקי progress + learnings)
```

רק אחרי שכל אלה קיימים — עוברים לשלב המימוש בפועל, החל מהיכרות עם הקוד הקיים (recon).
