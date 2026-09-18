---
description: "Capture and enforce project-specific architecture decisions, design taste, and coding conventions. TRIGGER when: starting a new project, user says 'set up architecture', 'define conventions', 'project structure', 'coding standards', 'תגדיר ארכיטקטורה', 'סטנדרטים של הפרויקט', 'מבנה הפרויקט', or when Claude needs to make an architectural decision in an existing project. Also trigger when user says 'I prefer X over Y' or 'always use X in this project' to record preferences."
---

# Project Architecture Guide

## Purpose
Capture the specific architectural decisions, design taste, and coding conventions for each project. Instead of Claude guessing how to structure code, it reads the project's established patterns and follows them exactly.

This follows Anthropic's practice: don't explain basic programming to Claude - instead invest the text in explaining your project's specific quirks and the exact design taste you prefer.

## How It Works

### Setting Up for a New Project
When starting a new project or first working on an existing one:

1. Create `examples/{project-name}.md` in this directory
2. Analyze the existing codebase (if any) to detect patterns
3. Ask the user about their preferences for:
   - File/folder structure
   - Naming conventions
   - State management approach
   - Styling approach (CSS modules, Tailwind, styled-components)
   - Testing strategy
   - Error handling patterns
   - API communication patterns
   - Hebrew/RTL handling (if applicable)
4. Document everything with CODE EXAMPLES, not just descriptions

### Using the Architecture Guide
Before writing any significant code:

1. Check if `examples/{project-name}.md` exists
2. If yes, read it and follow its patterns EXACTLY
3. If patterns conflict with what Claude would normally do - the guide wins
4. If encountering a new situation not covered - ask the user, then add to guide

## Architecture File Format

File: `examples/{project-name}.md`

```markdown
# {Project Name} Architecture Guide

## Stack
- Framework: Next.js 14 / React / Vue / etc.
- Language: TypeScript strict / JavaScript / Python
- Styling: Tailwind / CSS Modules / etc.
- State: Zustand / Redux / Context / etc.
- Testing: Vitest / Jest / Playwright / etc.

## File Structure
```
src/
  components/    # How components are organized
  hooks/         # Custom hooks pattern
  lib/           # Utilities and helpers
  ...
```

## Naming Conventions
- Components: PascalCase (UserProfile.tsx)
- Hooks: camelCase with use prefix (useAuth.ts)
- Utils: camelCase (formatDate.ts)
- Constants: UPPER_SNAKE_CASE
- CSS: kebab-case / BEM / etc.

## Component Pattern
[Actual code example of how a component should look]

## API Pattern
[Actual code example of how API calls are structured]

## Error Handling
[Actual code example of the error handling approach]

## Design Taste
- Minimal vs feature-rich
- Performance vs developer experience priorities
- Mobile-first vs desktop-first
- Hebrew/RTL considerations
- Animation preferences
- Color palette and spacing system

## Hard Rules
Things that MUST always be done this way:
- Rule 1 with explanation
- Rule 2 with explanation

## Anti-Patterns
Things that MUST NEVER be done:
- Anti-pattern 1 with explanation
- Anti-pattern 2 with explanation
```

## Recording Preferences Mid-Session

When user says "I prefer X" or "always do Y":
1. Read the current project's architecture file
2. Add the preference to the appropriate section
3. Confirm with user that it's recorded
4. Apply immediately to current work

## Key Principles

- CODE EXAMPLES are 10x more useful than descriptions
- "Design taste" is subjective but critical - capture it
- Anti-patterns are as important as patterns
- Update the guide when the project evolves
- One file per project - don't mix architectures
- When in doubt, show the user 2 options and let them choose, then record the preference
