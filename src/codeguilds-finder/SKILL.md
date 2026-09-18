---
name: codeguilds-finder
description: 'Search the CodeGuilds community registry (3,000+ skills, agents, MCP servers, hooks, prompts for Claude Code) for an existing tool that does what the current task needs, then install it — only after the user approves. Use PROACTIVELY whenever Claude is about to tell the user it lacks a capability, tool, skill, agent, MCP server, or integration to complete a task: before giving up, building from scratch, or saying "I can''t do X", first search CodeGuilds for something that already does it. Also use when the user explicitly says: "codeguilds", "find a tool/skill/MCP for", "is there a skill/agent/plugin for", "search the registry", "תחפש כלי", "יש תוסף/סקיל ל...", "תתקין כלי בשביל", "חפש ב-codeguilds", "יש משהו מוכן ש...". NOT for tasks Claude can already do with built-in tools or existing skills — only when a genuine capability gap exists.'
---

# CodeGuilds Finder

`<SKILL_DIR>` = the folder that contains this SKILL.md (normally `~/.claude/skills/codeguilds-finder`).
Resolve it once to an absolute path before running commands - PowerShell/cmd do not expand `~` inside quotes.

Discover and install Claude Code extensions from the **CodeGuilds** community registry
(`codeguilds.dev`) when the current task needs a capability you don't already have.

This is a **discovery + install** helper. It does **not** replace skills/tools you already
have — it fills genuine gaps by finding something the community already built.

## When to activate

Activate when **both** are true:
1. The current task needs a specialized capability (export X→Y, talk to service Z, a niche
   workflow, a domain tool, an MCP integration, a hook), **and**
2. No built-in tool and no already-installed skill covers it.

Do **NOT** activate for things you can already do (reading/writing files, running bash, web
search, code edits, or any task an installed skill already handles). Searching the registry
on every task is noise — only reach for it on a real gap.

## How to run the CLI

A patched copy of the `codeguilds` CLI is vendored with this skill (see
[Why a vendored CLI](#why-a-vendored-cli)). Always call it through the launcher — never plain
`npx codeguilds` (the published 0.2.5 is broken):

```bash
bash "<SKILL_DIR>/scripts/cg.sh" <command> [args]
```

Available commands: `search <query>` · `info <slug>` · `install <slug>` · `list` · `uninstall <slug>`.

## Workflow (4 steps — never skip step 3)

### 1. Name the gap
State, in one sentence, the missing capability — e.g. *"need a tool that converts a Postman
collection into a typed API client"*. Derive 1–3 **single-keyword** search terms from it.

### 2. Search
```bash
bash ".../scripts/cg.sh" search "postman"
```
- Search best with **single keywords** or short terms. Multi-word phrases ("figma to react")
  often return zero — if a phrase returns nothing, retry with one keyword at a time.
- Each result line shows: `slug`, `type` (skill / agent / MCP / hook / prompt / template),
  `↓ downloads`, and `by @author`.
- If still nothing relevant after ~2 attempts → tell the user no match was found and continue
  with the normal approach. **Do not invent a package or pretend one exists.**

### 3. Present & ASK — mandatory
- Pick the top 1–3 relevant matches. Run `info <slug>` on the leading one for details, and
  **summarize** it in 2–3 lines (what it is, type, author, downloads) — the raw `info` output
  dumps the full README, so never paste it wholesale.
- Prefer matches with higher download counts and a clear, on-topic description. Remember this is
  a **community registry — not official Anthropic** content; flag anything that looks unmaintained,
  unrelated, or low-trust.
- Then **always stop and ask the user** with `AskUserQuestion` whether to install it for this
  task. Installing writes to the user's global `~/.claude/` config — it is a state-changing action
  and requires explicit approval every time, even under blanket auto-approval. Never install silently.

### 4. Install — only after approval
```bash
bash ".../scripts/cg.sh" install <slug>            # global → ~/.claude/
bash ".../scripts/cg.sh" install <slug> --project  # only if the user asked for project-local
```
After install:
- **skill / agent** → available immediately; proceed to do the original task with it.
- **MCP server / hook** → tell the user a Claude Code restart is needed to load it, then continue.
- Confirm with `list`. To undo: `uninstall <slug>`.

## Safety rules
- **Never install without the user's explicit yes** — this is the core requirement of this skill.
- **Never fabricate results.** No match → say so plainly and fall back to the normal path.
- **One gap at a time.** Don't bulk-install; install only what the current task needs.
- It's a community registry — prefer well-downloaded, clearly-described packages; surface trust concerns.

## Why a vendored CLI
The published `codeguilds@0.2.5` (current `latest`) has a one-line bug: it reads
`../../package.json` at module load, which resolves to `node_modules/package.json`, so **every**
command crashes before running. This skill bundles the CLI under `vendor/` with the single-line
fix (`../package.json`) applied — see the PATCH comment in
`vendor/node_modules/codeguilds/dist/index.js`. The registry backend itself works fine.

**When upstream fixes this** (verify with `npm view codeguilds version`), you can switch the
launcher to plain `npx -y codeguilds` and delete `vendor/`. Until then, use the launcher.

See [references/cli-reference.md](references/cli-reference.md) for the full command reference.
