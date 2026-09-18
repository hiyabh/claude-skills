---
description: "Systematically debug a failing test, a production symptom, or a build error — find the ROOT cause (not the symptom), fix it minimally, and verify. TRIGGER when the user says 'the <X> test is failing, find out why and fix it', 'users are seeing 500 errors on /checkout, investigate and tell me what's going on', 'here is a build error, fix the root cause and verify the build succeeds', 'why is this broken', 'debug this'. Hebrew: 'הטסט נכשל, תמצא למה ותתקן', 'יש שגיאות 500 ב..., תחקור', 'תתקן את שגיאת הבנייה מהשורש', 'תדבג', 'למה זה נשבר'. Follows a strict reproduce → prove RED → root-cause → surgical fix → GREEN methodology. NOT for adding new tests to passing code (that's a job for a test-writing skill like test-loop, if you have one), NOT for live production incident triage across logs/deploys/config (that's incident-response's job, if you have it)."
---

# Debug — Root-Cause Fix with Proof

## Purpose
Turn a symptom into a proven root cause and a verified fix. Covers three entry
points: a **failing test**, a **production error report**, and a **build error**.
This skill follows a strict bug-handling methodology — do not skip its
phases; in particular **never fix without a failing-state proof, and never declare
fixed without a green proof**.

**Fundamental rule:** don't trust the report — reproduce and prove it first.

**Language:** explanations in Hebrew; code in English.

---

## Mode 1 — Failing test → red → green + explanation
Trigger: "the UserAuth test is failing, find out why and fix it".

1. **Reproduce** — run that test, read the full failure output (message, stack,
   assertion diff). Confirm it fails now (this is your RED evidence).
2. **Root cause** — trace backwards from the failing assertion to the origin. Read
   the code under test *and* the test itself. Apply the 5 Whys. Check `git log`/blame:
   did a recent change break it? Is the test asserting the right thing?
3. **Decide** who's wrong — the code or the test — with a reason, not a guess.
4. **Surgical fix** — smallest change at the root cause; no scope-widening refactors.
5. **Verify GREEN** — re-run the test (must pass), then the **full suite** for
   regressions, then build/lint. A regression is a new bug — block on it.
6. **Explain** in Hebrew: root cause in one sentence, the fix, RED→GREEN evidence,
   files touched, and whether the same pattern exists elsewhere.

---

## Mode 2 — Production symptom → investigation → diagnosis
Trigger: "users are seeing 500 errors on /checkout. investigate and tell me what is going on".

1. **Pin the symptom** — exact endpoint/flow, error code, when it started, blast
   radius (all users / subset / one tenant).
2. **Follow the request path** from entry to failure: route handler → services →
   DB/external calls. Read logs/stack traces if available; grep the codebase for the
   error and the code path.
3. **Form hypotheses**, then confirm/refute each with evidence (a failing test, a log
   line, a reproduced request) — don't stop at the first plausible one.
4. **Reproduce locally** if at all possible; write a failing test that captures the
   bug (RED) before fixing.
5. **Report the diagnosis** clearly even before fixing if the fix is risky:
   most-likely cause, evidence, blast radius, and the proposed fix. For high-risk
   areas (auth, payments, data) present the plan before applying.
6. Fix → verify → prevent (regression test + check for the same pattern elsewhere).

> If the symptom is really a *live incident* (latency spike, ongoing outage) needing
> correlation across logs, recent deploys, and config changes — if you also have the
> **incident-response** skill, hand off to it; otherwise correlate those signals
> manually before diagnosing further.

---

## Mode 3 — Build error → root-cause fix → verified build
Trigger: "here is a build error. fix the root cause and verify the build succeeds".

1. **Read the whole error**, not just the last line — the first error is often the
   real one; the rest are cascades. Note file, line, and error type.
2. **Find the root cause**: type error, missing/mismatched dependency version, bad
   import path, config/tsconfig issue, generated-code drift, env var. Reproduce the
   failing build locally.
3. **Fix at the source** — e.g. correct the type rather than casting to `any`, fix the
   version constraint rather than deleting the lockfile. Don't paper over it.
4. **Verify** — run the **full build** to completion (not just the failing step) and
   confirm it succeeds. Run tests/lint too if the fix touched logic.
5. If the same class of error can recur, note the guard (a tsconfig strictness, a CI
   check) that would catch it.

---

## Core rules
- Never guess-fix; no reproduction = no understanding.
- Never fix without a failing-state proof; never declare fixed without a passing one.
- Never widen scope — a bug fix is not a refactor license.
- Reproduction fails after ≥2 tries → stop, request env details, don't fix blind.
- Fix the same broken pattern wherever else it appears, or flag it.
