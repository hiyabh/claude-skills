---
name: code-visualizer
description: "Generate visual code explanations with syntax highlighting, Mermaid diagrams, and interactive walkthroughs. Opens Rift Code for repo-level analysis. TRIGGER when: explaining code, algorithms, architecture, data flow, debugging, or code review. Also triggers on: 'visualize this code', 'show me how this works', 'explain visually', 'code diagram', 'תראה לי ויזואלית', 'הסבר קוד', 'תרשים קוד', 'ויזואליזציה', 'הסבר אלגוריתם', 'סקירת קוד'. PROACTIVELY trigger when Claude is about to explain complex code (5+ steps), describe architecture (3+ components), walk through debugging with state changes, or review code touching 3+ aspects."
---

# Code Visualizer

`<SKILL_DIR>` = the folder that contains this SKILL.md (normally `~/.claude/skills/code-visualizer`). Resolve it once to an absolute path before running commands - PowerShell/cmd do not expand `~` inside quotes.

## Purpose

Generate beautiful, interactive visual code explanations — proactively, without waiting for user to ask. Two modes:

1. **Rift Code** — open `https://rift-code.com` in browser for full repo architecture visualization
2. **HTML Generation** — create standalone HTML files with syntax highlighting, Mermaid diagrams, step-by-step walkthroughs

## Decision Tree — When and What

```
Code explanation needed?
├── YES: GitHub repo context available?
│   ├── YES: Repo-wide explanation (architecture, dependencies, cross-file)?
│   │   ├── YES → Open Rift Code in browser + optional HTML for deep-dives
│   │   └── NO (single file/function) → HTML only
│   └── NO (standalone snippet, algorithm, concept):
│       └── HTML only
└── NO: Do not trigger
```

## Proactive Triggers (NO user request needed)

Activate automatically when Claude is about to:

1. Explain an algorithm with **5+ steps**
2. Describe system architecture with **3+ components**
3. Walk through debugging with **multiple state changes**
4. Do a code review touching **3+ aspects**
5. Explain data flow with **3+ transformation stages**
6. User pastes a function/class and asks "how does this work" / "איך זה עובד"

**DO NOT trigger for:** one-liner explanations, trivial code, when excalidraw-diagram-generator is already handling a diagram request.

**Always announce:** "מייצר הסבר ויזואלי..." so user knows what's happening and can say "skip".

## Rift Code Workflow

1. Open browser to `https://rift-code.com`
2. User authenticates with GitHub (first time only)
3. Select the relevant repository for analysis
4. Use for: dependency graphs, module relationships, cross-file architecture
5. After exploration, optionally generate HTML for specific code deep-dives

## HTML Generation Workflow

### Step 1: Choose Template

| Template | Use When |
|----------|----------|
| `algorithm-walkthrough` | Step-by-step algorithm/function explanation |
| `architecture-overview` | System design, module relationships, component diagrams |
| `code-review` | Annotated code review with severity markers |
| `debugging-flow` | Bug investigation with state changes at each step |
| `data-flow` | Data transformation pipeline visualization |
| `slide-deck` | Multi-slide presentation of any code topic |

### Step 2: Read Template

Read the chosen template from `<SKILL_DIR>/templates/{template-name}.html`

### Step 3: Generate HTML

Replace placeholder markers in template:
- `{{TITLE}}` — explanation title
- `{{SUBTITLE}}` — optional subtitle/context
- `{{LANGUAGE}}` — highlight.js language identifier
- `{{CODE_BLOCKS}}` — actual code with annotations
- `{{MERMAID_DIAGRAM}}` — Mermaid diagram definition
- `{{STEPS}}` — step-by-step walkthrough content
- `{{METADATA}}` — date, source file, author info

### Step 4: Save & Open

- Save to `./code-visualizations/{type}-{name}-{YYYY-MM-DD}.html` inside the current project directory (create the folder if missing). If there's no project directory in context (e.g. a standalone question), fall back to `<SKILL_DIR>/output/{type}-{name}-{YYYY-MM-DD}.html`.
- Open in browser via Playwright or inform user of file path
- File is self-contained — works offline, no server needed

## Design System

- **Theme:** Dark (Dracula) default, Light toggle available
- **Code font:** JetBrains Mono via Google Fonts CDN
- **Text font:** Inter via Google Fonts CDN
- **Syntax highlighting:** highlight.js v11.9.0 (dracula theme)
- **Diagrams:** Mermaid v10.9.0
- **Navigation:** Arrow keys for steps/slides, F for fullscreen, Esc to exit
- **Responsive:** Works on mobile, tablet, desktop
- **Print-friendly:** `@media print` rules included

## Mermaid Quick Reference

For common diagram types, read `references/mermaid-cheatsheet.md`.
For supported highlight.js languages, read `references/highlight-languages.md`.

## Key Principles

1. **Proactive > Reactive** — don't wait for user to ask. If code explanation is complex, visualize it
2. **HTML is the default** — Rift Code only for repo-wide analysis
3. **Self-contained** — every HTML file must work by double-clicking, no dependencies
4. **Dark theme first** — matches developer environments
5. **Keyboard-first navigation** — arrow keys, F, Esc
6. **No overlap with excalidraw** — if user wants a standalone diagram (no code context), defer to excalidraw skill
7. **Announce activation** — always tell user "מייצר הסבר ויזואלי..." before generating
8. **Keep templates as reference** — Claude reads the template structure and generates content inline, adapting layout to the specific explanation need
