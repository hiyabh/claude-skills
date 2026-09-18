---
description: "Maintain structured session journal for cross-session continuity. TRIGGER when: starting a new session on an ongoing project, user says 'where did we stop', 'continue from yesterday', 'what did we do last time', 'מאיפה הפסקנו', 'תמשיך מאתמול', 'מה עשינו', or at END of a substantial work session to save progress. Also trigger when user says 'save progress', 'log what we did', 'שמור התקדמות'."
---

# Session Journal

## Purpose
Create structured memory so that tomorrow's session can pick up exactly where today's left off. Instead of losing context between conversations, Claude reads the journal and continues seamlessly.

This follows Anthropic's practice of telling Claude to save a log file inside the skill directory so it can read what it did yesterday and continue from the same point.

## Log Location

`<SKILL_DIR>` = the folder that contains this SKILL.md (normally `~/.claude/skills/session-journal`). Resolve it once to an absolute path before running commands - PowerShell/cmd do not expand `~` inside quotes.

Logs are stored at `<SKILL_DIR>/logs/`, one file per project per day: `<SKILL_DIR>/logs/YYYY-MM-DD-{project-name}.md`. If that location isn't writable or the user prefers a different spot (e.g. inside the project itself), pick one documented location and stay consistent - don't scatter logs across multiple folders.

## How It Works

### At Session End (or when user asks to save progress)
Create/update a log entry in `<SKILL_DIR>/logs/`:

1. Read the latest entry for this project to understand sequence
2. Create new entry: `<SKILL_DIR>/logs/YYYY-MM-DD-{project-name}.md`
3. Include:
   - **Project**: Which project was worked on
   - **What was done**: Bullet list of completed tasks
   - **Current state**: Where things stand right now
   - **Next steps**: What should happen next session
   - **Open issues**: Anything unresolved or blocked
   - **Key decisions**: Important choices made and WHY
   - **Files changed**: List of files modified (paths)

### At Session Start (or when user asks to continue)
1. Find the most recent log for the current project in `<SKILL_DIR>/logs/`
2. Read it and present a brief summary to the user
3. Propose picking up from the documented next steps
4. If files were listed, check if they still exist/match

## Log Entry Format

File: `<SKILL_DIR>/logs/YYYY-MM-DD-{project-name}.md`

```markdown
# Session Log: {Project Name}
**Date**: YYYY-MM-DD
**Duration**: ~X hours

## Completed
- [ ] Task 1 that was finished
- [ ] Task 2 that was finished

## Current State
Brief description of where the project stands right now.
What's working, what's deployed, what's in progress.

## Next Steps (Priority Order)
1. Most important next task
2. Second priority
3. Nice to have

## Open Issues
- Issue description and any leads on solving it

## Key Decisions
- Decision: Why we chose X over Y

## Files Changed
- `path/to/file1.ts` - Added auth middleware
- `path/to/file2.tsx` - Fixed RTL layout bug

## Notes
Any additional context that might help tomorrow.
```

## Key Principles

- Write the journal as if briefing a colleague who knows the codebase but missed this session
- "Key decisions" is the most valuable section - without it, tomorrow's Claude might redo the same analysis
- Keep entries concise but complete - if in doubt, include it
- One entry per project per day (append if multiple sessions)
- The "Next steps" section IS tomorrow's todo list
- Don't log trivial sessions (quick one-off questions don't need journals)
