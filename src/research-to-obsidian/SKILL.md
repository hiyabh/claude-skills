---
name: research-to-obsidian
description: >
  Turn a linear research document (OSINT dossier, case file, investigation report, literature
  review, any entity-rich MD/DOCX/PDF) into an interactive Obsidian knowledge-graph vault, then
  install Obsidian Desktop and open it. Use when the user wants to VISUALIZE or "see the network"
  behind a body of research: who connects to whom, at what certainty, and why. Decomposes the
  material into one note per entity (person/organization/place/event/case/source), wires them with
  [[wikilinks]], assigns Graph-View color groups, and adds four visualizations: interactive Graph,
  timeline, Dataview tables, Excalidraw diagrams. Also installs Obsidian via winget, downloads the
  Dataview/Excalidraw/Timelines plugins, registers + launches the vault. Trigger phrases: "תהפוך את
  המחקר ל-Obsidian", "תבנה לי vault", "knowledge graph", "תפתח באובסידיאן", "turn my notes into a
  vault", "build an obsidian graph", "map the relationships". Also trigger on entity/relationship
  research the user wants to see visually.
---

# Research → Obsidian Knowledge Graph

`<SKILL_DIR>` = the folder that contains this SKILL.md (normally `~/.claude/skills/research-to-obsidian`).
Resolve it once to an absolute path before running commands — PowerShell/cmd do not expand `~` inside
quotes. The scripts below are self-contained (no dependency on files outside this folder); copy or
reference them as `<SKILL_DIR>/scripts/...`.

A repeatable method to convert any **entity-rich linear research** into an **interactive Obsidian
vault**, then install Obsidian and open it. Proven on a multi-entity OSINT dossier (people,
organizations, places, legal cases, events, sources, homonyms-to-disambiguate).

**Why it works:** linear MD/DOCX hides the most valuable thing in relational research — the *network*.
Obsidian's Graph View renders that network automatically from `[[wikilinks]]`, colored by entity type,
so a central subject and its branches become visible at a glance, and unrelated look-alikes (homonyms)
visibly disconnect.

---

## The 6-phase workflow

### Phase 1 — Read the source material
Read the existing research fully (report, relations tree, sources list). Extract every **entity** and
every **relationship** between entities. Note the **certainty** the research assigns to each fact
(high / medium / low / confirmed-unrelated) — preserving certainty is essential for honest OSINT.

### Phase 2 — Design the entity model
Classify each entity into a `type` and `role`, decide its `tags` (which drive graph color), and write
the `[[wikilinks]]` it should emit. See **Entity model** below. Plan the folder layout (one folder per
type). Aim for one note per entity — atomic, linkable.

### Phase 3 — Generate the vault with a build script
Copy `scripts/build_vault_template.py`, fill its `NOTES` list with your entities, and run it. The script
writes all notes (UTF-8), the `.obsidian` config (RTL + graph color-groups + plugin registration), and
the Excalidraw diagrams. It is **re-runnable** (overwrites) — iterate freely.

### Phase 4 — Verify
Run `scripts/verify_vault.py`. It counts files, checks every note has frontmatter, and reports **broken
wikilinks** (a link whose target filename does not exist). Fix until **0 broken links** — that is what
guarantees a connected graph.

### Phase 5 — Install Obsidian + plugins, register + open the vault
Run `scripts/setup_obsidian.ps1 -VaultPath "<abs path to vault>"`. It:
1. installs Obsidian via winget if missing,
2. downloads Dataview / Excalidraw / Timelines plugin releases from GitHub into `.obsidian/plugins/`,
3. registers the vault in `%APPDATA%\obsidian\obsidian.json` **as UTF-8 without BOM** (critical — see Gotchas),
4. launches Obsidian and confirms the vault loaded (`workspace.json` appears).

### Phase 6 — Hand off
Tell the user to start from the `00 - MOC` note and press `Ctrl+G` for the Graph. Note the **one manual
click** that cannot be automated: Obsidian's first-run **"Trust author and enable plugins"** dialog
(Restricted Mode is a security default). The Graph View is a core plugin and works without it.

---

## Entity model (frontmatter schema)

Every note carries this frontmatter. `tags` is what colors the graph — keep it controlled.

```yaml
---
type: person | organization | place | legal-case | event | source | moc | dashboard
role: subject | family | lawyer | judge | adversary | co-detainee | supporter | precedent | homonym-unrelated
certainty: high | medium | low | confirmed-unrelated
aliases: ["transliteration", "alternate name"]
date: YYYY-MM-DD          # events only — feeds the timeline
tags: [<one controlled tag that maps to a color>]
---
```

**Body rules**
- 2–4 line summary, then a `## קשרים` / `## Connections` section.
- **Every mention of another entity becomes a `[[wikilink]]`** — this is how the graph is built.
- State **certainty** explicitly in the body (bold it). Never upgrade a "medium" to look certain.
- The subject note is the hub: it links out to every major entity.
- Disambiguation entities (homonyms, unrelated namesakes) get `certainty: confirmed-unrelated` and the
  "unrelated" color tag, so they render gray and **disconnected** — visually proving they're separate.

## Graph color groups

Map each controlled tag to a color in `.obsidian/graph.json` (`build_vault_template.py` does this from a
`COLORS` dict). RGB is an integer: `R*65536 + G*256 + B`. A proven palette:

| tag | color | meaning |
|---|---|---|
| `#subject` (נושא) | gold `16766720` | the central subject — the hub |
| `#family` (משפחה) | blue `3900150` | family / close ties |
| `#supporter` (תומך) | green `2278750` | allies (counsel, advocacy orgs) |
| `#adversary` (עוין) | red `15680580` | opposing actors |
| `#case` (תיק-משפטי) | purple `11032055` | legal cases / documents |
| `#place` (מקום) | teal `440020` | locations |
| `#unrelated` (לא-קשור) | gray `10265519` | homonyms / disambiguation |

## The four visualizations

1. **Graph View** — core plugin, works immediately. The payoff visualization.
2. **Timeline** — event notes carry `tag: timeline` + `date:`; a view note renders them via the
   *timelines-revamped* plugin using `<div class="ob-timelines" data-tags="timeline"></div>`.
3. **Dataview tables** — a `99 - dashboard` note with ```dataview``` blocks: entities by certainty,
   events sorted by date, open tasks (research gaps).
4. **Excalidraw diagrams** — hand-style relations tree + visual timeline, generated as `.excalidraw.md`
   files (see the Excalidraw generator in the build script).

---

## Filenames & RTL gotchas

- **Forbidden in Windows filenames:** `" : * ? < > | \ /`. Hebrew legal abbreviations use gershayim
  (`בג"ץ`, `סא"ל`, `עת"ם`) — strip them in filenames (`בגץ`, `סאל`, `עתם`). Keep the pretty form in the H1
  and in `aliases`. **Wikilinks must match filenames exactly.**
- **Never wikilink a folder name** — only notes are link targets (a `[[05 - events]]` pointing at a folder
  is a broken link). Reference folders as plain inline text.
- **RTL:** set `"rightToLeft": true` in `.obsidian/app.json` for Hebrew/Arabic vaults.
- Spaces, hyphens, and parentheses in filenames are fine.

## Obsidian setup gotchas (learned the hard way)

- **`obsidian.json` MUST be UTF-8 *without BOM*.** PowerShell's `Out-File -Encoding utf8` (Win PS 5.1)
  writes a BOM; Obsidian's Electron/Node `JSON.parse` then fails silently and the vault never loads
  (no `workspace.json` appears). Write it with `System.Text.UTF8Encoding($false)`. `setup_obsidian.ps1`
  already does this — do not "simplify" it back to `Out-File -Encoding utf8`.
- The timelines plugin id is **`timelines-revamped`** (repo `seanlowe/obsidian-timelines`). The old
  `Darakah/obsidian-timelines` was de-listed and its `releases/latest` 404s. See `references/plugins-and-gotchas.md`.
- Confirm load by checking for `<vault>/.obsidian/workspace.json`, not by the process count (Electron
  spawns ~4 processes regardless).
- First-run **community-plugin trust dialog requires a human click** — cannot be bypassed automatically.

---

## Scripts in this skill

- `scripts/build_vault_template.py` — fill `NOTES`, run; writes notes + `.obsidian` config + Excalidraw.
- `scripts/verify_vault.py` — counts files, checks frontmatter, finds broken wikilinks (exit 1 if any).
- `scripts/setup_obsidian.ps1` — install Obsidian (winget) + download plugins + register (no-BOM) + open.
- `references/plugins-and-gotchas.md` — plugin repos/ids, GitHub-release URL patterns, known pitfalls.

## Scope

Best for **relational / entity-rich** research (investigations, case files, genealogies, org maps,
literature networks). Overkill for short linear notes with few cross-references. Does not replace the
source documents — the vault is an additive visualization layer; leave the originals untouched.
