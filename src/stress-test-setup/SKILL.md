---
name: stress-test-setup
description: Use after finishing product/requirements setup (e.g. via the pre-build-setup skill, if you have it), when project is a production web app, public API, or system with SLA/load requirements. Sets up k6 load tests (baseline, spike, soak) based on expected user volume from a PRD. Trigger when user says "stress test", "load test", "k6", "בדיקת עומס", or invoked automatically as a follow-up step from a pre-build-setup workflow. Skip for CLI tools, libraries, internal dashboards with <10 users, or POCs.
---

# Stress Test Setup

הפעל רק אחרי שלב תכנון מוצר/דרישות (למשל הסקיל `pre-build-setup`, אם קיים אצלך), ורק אם הפרויקט עומד באחד מהתנאים:

- Web app / API עם משתמשים חיים
- מערכת עם SLA לזמינות / latency
- צפי עומס > 100 RPS או > 1000 משתמשים חודשיים
- מוצר ייצור ציבורי

אם לא — דלג על הסקיל.

## רצף

### שלב 1: שלוף מספרי עומס

קרא `docs/PRD.md` סעיף 7 (אילוצים). חפש "משתמשים צפויים".

אם לא מופיע — שאל:
- RPS צפוי בשעת שיא?
- Peak concurrent users?
- יש SLA? (p95 latency, error rate, availability)

### שלב 2: Plan mode לסקלביליות

לפני כתיבת k6, הפעל plan mode לענות על:

- **Bottlenecks צפויים:** DB queries? External API? Compute? I/O?
- **Graceful degradation:** איך האפליקציה נופלת בחן? circuit breakers? fallback values?
- **Rate limiting:** על מה? (per IP, per user, per endpoint)
- **Caching:** מה יכול להישמר? TTL? cache invalidation?

שמור תשובות ב-`docs/scalability-plan.md`.

### שלב 3: צור תיקיית load tests

```
tests/load/
├── baseline.js    # עומס רגיל — שעת שיא ממוצעת
├── spike.js       # זינוק פתאומי — x5 מהעומס הרגיל לדקה
├── soak.js        # עומס ממושך — עומס רגיל במשך שעה+ (shake memory leaks)
└── README.md      # הוראות הרצה
```

### שלב 4: k6 scripts templates

**baseline.js:**
```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '2m', target: 50 },   // warm up
    { duration: '5m', target: 100 },  // peak
    { duration: '2m', target: 0 },    // cool down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],  // 95% under 500ms
    http_req_failed: ['rate<0.01'],     // error rate < 1%
  },
};

export default function () {
  const res = http.get('http://localhost:3000/api/endpoint');
  check(res, { 'status 200': (r) => r.status === 200 });
  sleep(1);
}
```

**spike.js:** אותו מבנה, stage של זינוק חד (0 → 500 תוך 30 שניות).

**soak.js:** stage יחיד ארוך (target 100, duration 1h+).

### שלב 5: הגדר thresholds ב-PRD

ודא שב-`docs/PRD.md` סעיף 10 (Success Criteria) יש:

- [ ] p95 latency < X ms בעומס Y RPS
- [ ] Error rate < Z% בעומס Y RPS
- [ ] No crashes after 1h soak test

### שלב 6: עדכן plan.md

הוסף ל-`docs/plan.md` שלב אחרון:

```
### שלב N: Load testing before deploy
- הרץ `npm run test:load:baseline`
- הרץ `npm run test:load:spike`
- הרץ `npm run test:load:soak` (שעה+)
- תקן bottlenecks שזוהו
- אמת thresholds מ-PRD §10
```

### שלב 7: עדכן CLAUDE.md של הפרויקט

הוסף:

```markdown
## Load Testing (before production deploys)

Run before any deploy that affects request handling:
- `npm run test:load:baseline` — must pass
- `npm run test:load:spike` — must pass
- `npm run test:load:soak` — run once per release

Thresholds defined in `tests/load/*.js` options.
```

### שלב 8: package.json scripts

הוסף:

```json
{
  "scripts": {
    "test:load:baseline": "k6 run tests/load/baseline.js",
    "test:load:spike": "k6 run tests/load/spike.js",
    "test:load:soak": "k6 run tests/load/soak.js"
  }
}
```

## התקנה

k6 הוא binary, לא npm package. התקנה לפי OS:

- **Mac:** `brew install k6`
- **Windows:** `choco install k6` או `winget install k6`
- **Linux:** לפי הוראות הרשמיות של Grafana

## חוקים

- **אל תריץ soak על production.** רק staging או סביבה מבוקרת.
- **אל תשאיר thresholds ברירת מחדל.** תמיד הגדר לפי PRD.
- **אל תדלג על spike test.** שם תופסים את רוב כשלי הסקלביליות.
- **אם thresholds נכשלים — flag ל-learnings.md, תקן, הרץ שוב.**
