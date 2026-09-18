---
description: "Manage reusable code snippets and patterns across projects. TRIGGER when: user says 'save this snippet', 'save this pattern', 'add to snippets', 'שמור את הקוד', 'תוסיף לספריה', or when Claude is about to write code that matches an existing saved pattern. Also trigger when user says 'show my snippets', 'what patterns do I have', 'find snippet for X'. PROACTIVELY check snippets before writing boilerplate code for known patterns."
---

# Code Snippets Library

## Purpose
Instead of reinventing code from scratch every time, maintain a library of proven, tested code snippets organized by category. Claude pulls from these snippets instead of generating from memory, ensuring consistency and quality.

This follows Anthropic's practice of giving Claude pre-made code examples so it reads real patterns instead of guessing.

## Directory Structure

```
snippets/
  react/           # React components, hooks, patterns
  python/          # Python utilities, scripts, patterns
  typescript/      # TypeScript types, utilities
  css/             # CSS/Tailwind patterns, layouts
  api/             # API call patterns, auth flows
  hebrew-rtl/      # RTL-specific code patterns
  config/          # Config files, env templates
  general/         # Cross-language utilities
```

## How It Works

### Saving a Snippet
When user says to save, or when a particularly good pattern emerges:

1. Identify the category (create directory if needed)
2. Create a file in `snippets/{category}/{name}.md` with:
   - Title and description
   - The code itself (properly formatted)
   - Usage example
   - Gotchas/notes
3. Update `snippets/index.json` with the new entry

### Using Snippets
Before writing boilerplate or common patterns:

1. Read `snippets/index.json` to check for relevant snippets
2. If a match exists, read the snippet file
3. ADAPT it to the current context (don't blindly copy)
4. Credit the snippet source in a comment if useful

## Snippet File Format

Each snippet file (`snippets/{category}/{name}.md`):

```markdown
# Snippet Name

## Description
What this does and when to use it.

## Code
\`\`\`typescript
// The actual code here
\`\`\`

## Usage
How to integrate this into a project.

## Notes
- Any gotchas or variations
```

## Index Format

`snippets/index.json`:
```json
[
  {
    "name": "auth-middleware",
    "category": "api",
    "file": "api/auth-middleware.md",
    "tags": ["auth", "express", "jwt", "middleware"],
    "description": "JWT authentication middleware for Express"
  }
]
```

## Key Principles

- Snippets should be PROVEN code that worked in real projects
- Include enough context that the snippet can be adapted, not just copied
- Tag generously - the more tags, the easier to find later
- Hebrew/RTL snippets get their own category because they're specialized
- Config templates (tsconfig, vite.config, etc.) are extremely valuable snippets
- Update snippets when better patterns emerge - don't hoard outdated code
