# CodeGuilds CLI — Command Reference

`<SKILL_DIR>` = the folder that contains this skill's SKILL.md (normally `~/.claude/skills/codeguilds-finder`).
Resolve it once to an absolute path before running commands - PowerShell/cmd do not expand `~` inside quotes.

Verified against `codeguilds@0.2.5` on 2026-06-10 (the vendored, patched copy).
Invoke everything through the launcher:

```bash
bash "<SKILL_DIR>/scripts/cg.sh" <command> [args]
```

## Commands

| Command | Description |
|---|---|
| `search <query>` | Search the registry. Best with single keywords; multi-word phrases often return nothing. |
| `info <slug>` | Full details for a package (dumps the whole README — summarize, don't paste). |
| `install <slug>` | Install globally into `~/.claude/`. Add `--project` for project-local `.claude/`. |
| `install <slug> --strategy <append\|prepend\|replace>` | Merge strategy for CLAUDE.md templates (default `append`). |
| `uninstall <slug>` (alias `remove`) | Uninstall and undo config changes. `--project` to target project scope. |
| `list` (alias `ls`) | List installed packages. |
| `info`/`search` need no auth. |
| `login` / `logout` | Browser OAuth — only needed for **publishing**, not for search/install. |
| `collection list` / `collection info <slug>` / `collection install <slug> [-y] [--project]` | Browse and install curated collections. |

## Package types in results
`skill` · `agent` · `MCP` · `hook` · `prompt` · `template`

## Result line format
```
<slug>          <type>     ↓ <downloads>     by @<author>
    <README snippet…>
```

## Backend (for reference)
The CLI talks to a Supabase PostgREST backend (`https://wfolayipdobqxxhmejwq.supabase.co/rest/v1/…`)
with a public anon key embedded in the CLI, plus raw GitHub for package files. No account or API
key is required for search/install. There is no separately documented public REST API.

## The upstream bug (why this is vendored)
`src/index.ts` runs `require("../../package.json")` at module top level. From `dist/index.js`
that path resolves to `node_modules/package.json` (nonexistent) → `MODULE_NOT_FOUND` crash on
**every** command. Fix: `../package.json`. Applied in the vendored copy with a PATCH comment.
Good feedback to report to the maintainer (Haim Madar / xdevsapps).

## Re-installing / updating the vendored CLI
```bash
SKILL="<SKILL_DIR>"
npm install codeguilds@latest --prefix "$SKILL/vendor" --no-audit --no-fund
# then re-apply the patch in vendor/node_modules/codeguilds/dist/index.js if still present:
#   var { version } = require2("../package.json");   // was ../../package.json
```
Once upstream ships a fixed release, point `scripts/cg.sh` at plain `npx -y codeguilds` and
remove `vendor/`.
