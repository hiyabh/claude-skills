---
description: "Write tests, run them, and drive to green — either for existing code or full TDD (tests first, then implement until they pass). TRIGGER when the user says 'write tests for <file>, run them, and fix any failures', 'write tests for the <X> first, then implement it until they pass', 'add test coverage', 'TDD this', 'make the tests pass'. Hebrew: 'תכתוב טסטים ל...', 'תכתוב טסטים ותריץ עד שהכל ירוק', 'תעשה TDD', 'תוסיף כיסוי בדיקות', 'תריץ את הטסטים ותתקן'. Covers detecting the test framework, writing meaningful tests, running them, and iterating fix→run until pass. NOT for debugging one already-failing test in isolation (that's the debug skill's job, if you have it), NOT for load/stress testing (that's stress-test-setup's job, if you have it)."
---

# Test Loop — Write · Run · Fix Until Green

## Purpose
Two related workflows around automated tests, both ending in a **green run**:
- **Coverage mode** — write tests for existing code, run, and fix failures.
- **TDD mode** — write the tests *first* from the spec, then implement the code
  until every test passes.

**Language:** explanations in Hebrew; test code/comments in English.

---

## Step 0 — Detect the test setup (always first)
- Identify the framework from the project: `package.json` scripts + devDeps
  (Jest, Vitest, Playwright, Mocha), `pytest`/`unittest` (Python), `go test`,
  `cargo test`, RSpec, etc. **Never assume** — read the config.
- Find the run command (`npm test`, `pytest -q`, `go test ./...`) and the test file
  convention (`*.test.ts`, `*.spec.ts`, `test_*.py`, `_test.go`) and location.
- If no test framework exists and the task needs one, propose + install the
  ecosystem-standard choice before writing tests, then scaffold minimal config.
- Read an existing test file to **match style, imports, and patterns** exactly.

---

## Coverage Mode — tests for existing code
Trigger shape: "write tests for `app/parsers/feed.py`, run them, and fix any failures".

1. **Read the target thoroughly** — understand its real behavior, inputs, outputs,
   error paths, and dependencies (what to mock vs. call for real).
2. **Write meaningful tests**, not filler:
   - Happy path(s) with representative inputs.
   - Edge cases: null/undefined, empty, zero, negative, boundary, large, malformed.
   - Error handling: does it throw/return errors as intended?
   - Each test asserts one clear behavior; name tests by behavior, not by function.
3. **Run** the suite.
4. **Triage each failure honestly** — decide per failure:
   - Test is wrong (bad assumption/assertion) → fix the test.
   - Code is genuinely broken → this is a real bug. Fix the code **minimally and
     surgically** (do not refactor), and tell the user you found and fixed a bug —
     don't silently rewrite the test to match buggy behavior.
5. **Iterate** run→fix until green. Report coverage of behaviors added, and any bugs
   surfaced.

---

## TDD Mode — tests first, then implement
Trigger shape: "write tests for the discount engine first, then implement it until they pass".

1. **Derive tests from the spec/requirements**, before any implementation exists.
   Cover the described behavior + edge cases. It's fine (expected) that they won't
   even compile/import yet.
2. **Confirm RED** — run and show they fail (or error) for the right reason. A test
   that passes before implementation is a broken test; rewrite it.
3. **Implement** the minimum code to satisfy the tests, following project patterns
   and general clean-code practice (small, focused files and functions, no magic
   numbers, validate inputs at boundaries).
4. **Run → GREEN.** Iterate implement→run until all pass. Don't weaken tests to pass;
   if a test was wrong, fix the *test* deliberately and say so.
5. **Refactor safely** with tests green as the safety net, then re-run.

---

## Rules
- Green means the **full** relevant suite passes, not just the new tests — check for
  regressions you introduced.
- Never delete or `.skip` a failing test to "make it pass" without explicit reason.
- Don't test framework internals or trivial getters — test behavior that can break.
- If you can't reach green after focused iterations, stop and report the blocker with
  the actual failing output, rather than thrashing.

## Output
- Files added/changed, the final run output (proof of green), and — for coverage
  mode — any real bugs discovered and fixed along the way.
