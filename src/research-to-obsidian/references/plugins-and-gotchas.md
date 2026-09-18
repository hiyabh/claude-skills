# Plugins & Gotchas — reference

## Community plugins used

| Plugin | id (community-plugins.json) | GitHub repo | Purpose |
|---|---|---|---|
| Dataview | `dataview` | `blacksmithgu/obsidian-dataview` | dynamic tables/queries from frontmatter |
| Excalidraw | `obsidian-excalidraw-plugin` | `zsviczian/obsidian-excalidraw-plugin` | hand-style diagrams (`.excalidraw.md`) |
| Timelines (Revamped) | `timelines-revamped` | `seanlowe/obsidian-timelines` | renders `<div class="ob-timelines">` |

**Graph View** is a **core** plugin — no install, enabled by default. It is the primary visualization
and always works, even before the trust click.

## Installing plugin files manually (release URL pattern)

Each plugin release ships `manifest.json`, `main.js`, and usually `styles.css`. Drop them into
`<vault>/.obsidian/plugins/<id>/`. Two ways to fetch:

```
# A) direct latest-download (works when the repo publishes assets to latest)
https://github.com/<owner>/<repo>/releases/latest/download/main.js

# B) robust — query the API for the latest release's asset URLs
GET https://api.github.com/repos/<owner>/<repo>/releases/latest  -> .assets[].browser_download_url
```
`setup_obsidian.ps1` uses (B), which is more reliable.

## Known pitfalls (all hit during the first build)

1. **`obsidian.json` BOM bug (critical).** Windows PowerShell 5.1 `Out-File -Encoding utf8` writes a
   UTF-8 **BOM**. Obsidian (Electron/Node `JSON.parse`) chokes on the BOM, silently ignores the file,
   and the vault never opens (no `workspace.json`). Fix: write with `System.Text.UTF8Encoding($false)`.

2. **`Darakah/obsidian-timelines` is dead.** Its `releases/latest` returns 404. The maintained
   successor is `timelines-revamped` (repo `seanlowe/obsidian-timelines`). Same `ob-timelines` div
   syntax, so view notes don't change — only the plugin id and download repo.

3. **Windows-forbidden filename chars** `" : * ? < > | \ /`. Hebrew gershayim in legal abbreviations
   (`בג"ץ`, `סא"ל`, `עת"ם`) contain `"` — strip in filenames, keep pretty form in H1 + `aliases`.

4. **Don't wikilink folders.** `[[05 - events]]` pointing at a folder is a broken link. `verify_vault.py`
   catches it. Reference folders as plain text.

5. **Confirm load by `workspace.json`,** not process count — Electron spawns ~4 processes regardless.

6. **First-run trust dialog needs a human click** ("Trust author and enable plugins"). Cannot be
   automated; Restricted Mode is an Obsidian security default.

## obsidian.json shape (the file that tells Obsidian which vault to open)

```json
{
  "vaults": {
    "<16-hex-id>": { "path": "C:/abs/path/with/forward/slashes", "ts": 1700000000000, "open": true }
  }
}
```
Set `open: true` on exactly one vault (clear it on the others) to auto-open that vault on launch.

## Graph color palette (RGB integers = R*65536 + G*256 + B)

gold 16766720 · blue 3900150 · green 2278750 · red 15680580 · purple 11032055 · teal 440020 · gray 10265519
