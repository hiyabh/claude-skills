---
description: "Track and learn from common mistakes in any project. TRIGGER when: Claude makes an error, user corrects Claude, a bug is found that was introduced by Claude, or user says 'remember this mistake', 'don't do this again', 'add to mistakes', 'תזכור את הטעות', 'אל תעשה את זה שוב'. Also trigger PROACTIVELY at the start of coding tasks to check existing mistakes for the current project/technology."
---

# Common Mistakes Tracker

## Purpose
Maintain a living log of mistakes per project and technology stack. Every time Claude falls into a technical trap, the mistake gets recorded here so it never repeats.

This follows Anthropic's internal practice of maintaining a "common mistakes zone" that the model reads before starting work.

## How It Works

### Recording a Mistake
When a mistake is identified (by user correction, failed test, or explicit request):

1. Identify the project name or technology
2. Read the existing mistakes log: `mistakes-log.json` in this directory
3. Add the new entry with:
   - `category`: The tech/framework/language involved
   - `mistake`: What went wrong (concise)
   - `correct_approach`: What should have been done
   - `context`: When this typically happens
   - `date`: When it was recorded
4. Write the updated log back

### Using the Mistakes Log
At the START of any coding task:

1. Read `mistakes-log.json`
2. Filter for entries matching the current technology/framework
3. Keep these in mind as active constraints while coding
4. If about to do something that matches a recorded mistake - STOP and use the correct approach instead

## Mistakes Log Format

The file `mistakes-log.json` in this directory stores all entries as:
```json
[
  {
    "id": 1,
    "category": "react",
    "mistake": "Used useEffect for derived state instead of useMemo",
    "correct_approach": "Use useMemo for values computed from props/state, useEffect only for side effects",
    "context": "When computing filtered/sorted lists from state",
    "date": "2026-03-22",
    "project": "my-app"
  }
]
```

## Key Principles

- Be SPECIFIC. Not "don't write bad code" but "don't use `any` type in TypeScript interfaces for API responses"
- Include the CONTEXT - when does this mistake typically happen?
- The correct approach should be copy-paste ready when possible
- Review and prune outdated entries when frameworks/projects change
- Cross-project mistakes (like git habits) use category "general"

## Categories to Watch
- Language-specific pitfalls (JS, Python, TypeScript quirks)
- Framework misuse (React, Next.js, Vue patterns done wrong)
- Architecture mistakes (wrong file structure, circular deps)
- Build/deploy errors (wrong configs, missing env vars)
- Hebrew/RTL specific issues (bidi text, font problems)
- Git workflow errors (wrong branch, force push accidents)
