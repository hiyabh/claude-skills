---
description: "Hands-on Git workflows: resolve merge/rebase conflicts with a documented rationale, generate professional Conventional-Commit messages from the actual diff, and author complete CI/CD GitHub Actions pipelines. TRIGGER when the user says 'resolve the merge conflicts in this branch and explain what you kept from each side', 'commit these changes with a message that summarizes what I did', 'write a GitHub Actions workflow that runs tests, builds, and deploys to staging on push to develop', or similar. Hebrew: 'תפתור את הקונפליקטים', 'תסביר מה שמרת מכל צד', 'תעשה commit עם הודעה טובה', 'תכתוב workflow ל-GitHub Actions', 'CI/CD', 'pipeline של דיפלוי'. Follows the global Git Hygiene rules (atomic commits, conventional messages). NOT for routine `git status`/`git log` questions — just answer those directly."
---

# Git Workflow — Conflicts · Commits · CI/CD

## Purpose
Three focused Git workflows, each done end-to-end by Claude (never hand a git
command back to the user — run it):
- **Conflict resolution** with a decision log.
- **Commit message** authoring from the real diff (Conventional Commits).
- **CI/CD pipeline** authoring for GitHub Actions.

**Language:** explanations in Hebrew; commit messages, YAML, and code in English.

---

## Workflow A — Resolve merge/rebase conflicts (with documented decisions)
Trigger: "resolve the merge conflicts in this branch and explain what you kept from each side".

1. **Survey** — `git status` to list conflicted files; `git log --oneline --left-right
   --merge` and `git diff` to understand both sides. Know which branch is "ours" vs
   "theirs" and what each was trying to do.
2. **Resolve each hunk on merit**, not mechanically:
   - Understand the intent of both sides before choosing.
   - Prefer a resolution that keeps *both* intents when they're compatible (e.g. two
     independent additions) rather than dropping one.
   - Never blindly take one side across the board.
   - Watch for semantic conflicts that aren't textual (both sides compile, logic
     still breaks) — reason about behavior, not just markers.
3. **Remove all conflict markers**, then verify: build + run the test suite. A "resolved"
   branch that doesn't compile isn't resolved.
4. **Document the decisions** — for each conflicted file, one line: what you kept from
   each side and *why*. Present this table in Hebrew to the user before committing.
5. Complete the merge/rebase (`git add` + `git commit` / `git rebase --continue`).
   Do **not** `push --force` to a shared branch without explicit approval.

---

## Workflow B — Professional commit message from the diff
Trigger: "commit these changes with a message that summarizes what I did".

1. Inspect the **actual change**: `git status`, `git diff --staged` (and unstaged).
   Stage the intended files (`git add -p` mentally — group only related changes).
2. If the staged changes are really several unrelated things, propose splitting into
   **atomic commits**, one logical change each.
3. Write a **Conventional Commit**:
   - Type: `feat` / `fix` / `refactor` / `docs` / `test` / `chore` / `perf` / `style`.
   - `type(scope): concise summary in imperative mood` (≤ ~72 chars).
   - Body (when non-trivial): *why*, notable decisions, breaking changes
     (`BREAKING CHANGE:` footer).
   - Summarize what the diff *does*, not a file listing.
4. If this repo's commits end with a `Co-Authored-By` trailer, keep the convention.
5. Commit. Never `--no-verify` or skip signing unless the user explicitly asks. If a
   hook fails, fix the underlying issue.

---

## Workflow C — CI/CD GitHub Actions pipeline
Trigger: "write a GitHub Actions workflow that runs tests, builds, and deploys to staging on every push to develop".

1. **Learn the project**: language/runtime + versions, package manager + lockfile,
   test/build/deploy commands, and the deploy target (Vercel, Railway, AWS, Docker,
   Pages…). Read `package.json` / `pyproject.toml` / existing `.github/workflows`.
2. **Author `.github/workflows/*.yml`** with:
   - Correct `on:` triggers (e.g. `push: branches: [develop]`, plus `pull_request`
     for the test job if useful).
   - Jobs wired by `needs:` — typically `test` → `build` → `deploy` — so deploy only
     runs on green.
   - Dependency caching (`actions/setup-node` cache, `actions/cache`), pinned action
     versions, matrix only if genuinely needed.
   - Deploy step using the target's official action/CLI; environment via
     `environment:` and `secrets.*` — **never hardcode secrets**.
3. **List required secrets** for the user to add in repo settings (names only, with a
   one-line description each) — the one thing Claude can't set.
4. Sanity-check the YAML (indentation, valid keys). Note anything that can only be
   fully verified by an actual run, and offer to trigger/watch it.

---

## Rules
- Run every git command yourself; don't ask the user to run it.
- Atomic commits, conventional messages, no secrets in code.
- `push --force` / history rewrites on shared branches → confirm first.
