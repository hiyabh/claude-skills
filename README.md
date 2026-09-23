# כל הסקילים של בין קודש לקלוד

מרכז אחד לכל הסקילים ל-Claude Code שבנינו בקהילה - עם דף הסבר והתקנה בהדבקה אחת לכל סקיל.

**האתר:** https://hiyabh.github.io/claude-skills/

## התקנה מהירה (טרמינל)

```bash
curl -fsSL https://hiyabh.github.io/claude-skills/install.sh | bash -s -- debug test-loop
```

להתקנת **כל** הסקילים (כולל החבילות מהדפים הנפרדים):

```bash
curl -fsSL https://hiyabh.github.io/claude-skills/install.sh | bash -s -- all
```

הסקריפט לא דורס סקיל קיים באותו שם.

## מבנה

| נתיב | מה יש שם |
|---|---|
| `src/<name>/` | קוד המקור של כל סקיל (מה שמותקן ב-`~/.claude/skills/<name>`) |
| `content/<name>.json` | תוכן דף ההסבר בעברית |
| `catalog.json` | דפים חיצוניים (סקילים שיש להם ריפו משלהם) + כרטיס "מתחילים כאן" |
| `build/` | סקריפטי הבנייה (Python, בלי תלויות) |
| `skills/`, `dl/`, `index.html` | **נוצרים ע"י הבנייה** - לא לערוך ידנית |

## הוספת סקיל

**סקיל בתוך המרכז:** מעתיקים את התיקייה ל-`src/<name>/`, כותבים `content/<name>.json`
(ראו דוגמה קיימת), מריצים `python build/build.py`, ודוחפים.

**סקיל עם ריפו ודף משלו:** מוסיפים לריפו את ה-topic `claude-skill`.
ה-Action היומי (`.github/workflows/sync.yml`) מוסיף אותו לבד ל-`catalog.json` ובונה מחדש.
אפשר ללטש אחר כך את האייקון, הכותרת והקטגוריה ב-`catalog.json`.

## רישיון

MIT - לשימוש חופשי. מותר להעביר הלאה.
