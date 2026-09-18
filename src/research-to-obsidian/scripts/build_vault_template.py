# -*- coding: utf-8 -*-
"""
build_vault_template.py — TEMPLATE builder for an Obsidian knowledge-graph vault.

HOW TO USE
  1. Set VAULT to the absolute path of the vault folder to create.
  2. Adjust COLORS (tag -> RGB int) to your entity taxonomy.
  3. Fill the NOTES list: one tuple per entity
        (folder, filename, frontmatter, body)
     - filename: NO Windows-forbidden chars (quote colon star question angle-brackets pipe slashes)
     - body: every mention of another entity -> [[exact filename]]
  4. (optional) edit the Excalidraw builders to draw your network/timeline.
  5. Run:  python build_vault_template.py
  6. Verify:  python verify_vault.py   (must report 0 broken wikilinks)

Re-runnable (overwrites). Data-heavy by design: most lines are CONTENT.
"""
import json
import os

# ---------------------------------------------------------------------------
# 1) Vault location
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.abspath(__file__))
VAULT = os.path.join(ROOT, "MyVault")  # <-- CHANGE to your target path

# ---------------------------------------------------------------------------
# 2) Graph color groups. RGB int = R*65536 + G*256 + B.
#    Keys are the controlled tags you put in note frontmatter `tags:`.
# ---------------------------------------------------------------------------
COLORS = {
    "subject":   16766720,  # gold   #FFD700  -> the hub
    "family":    3900150,   # blue   #3B82F6
    "supporter": 2278750,   # green  #22C55E
    "adversary": 15680580,  # red    #EF4444
    "case":      11032055,  # purple #A855F7
    "place":     440020,    # teal   #06B6D4
    "unrelated": 10265519,  # gray   #9CA3AF  -> homonyms / disambiguation
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def fm(type_, role, certainty, tags, aliases=None, date=None, extra=None):
    """Build a YAML frontmatter block."""
    lines = ["---", f"type: {type_}"]
    if role:
        lines.append(f"role: {role}")
    if certainty:
        lines.append(f"certainty: {certainty}")
    if aliases:
        lines.append("aliases: [" + ", ".join(f'"{a}"' for a in aliases) + "]")
    if date:
        lines.append(f"date: {date}")
    lines.append("tags: [" + ", ".join(tags) + "]")
    if extra:
        for k, v in extra.items():
            lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines)


def write(folder, name, frontmatter, body):
    d = os.path.join(VAULT, folder) if folder else VAULT
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, name + ".md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(frontmatter + "\n\n" + body.strip() + "\n")
    return path


# ===========================================================================
# 3) NOTES — fill this with your entities.  Example skeleton below.
#    The hub note links out to everything; events carry date + tag:timeline.
# ===========================================================================
NOTES = [
    ("People", "Subject Name",
     fm("person", "subject", "high", ["subject"], aliases=["Alt Name"]),
     """# Subject Name ⭐
The hub. 2–4 line summary. **Certainty: high.**

## Connections
- Family: [[Relative Name]]
- Ally: [[Advocacy Org]]
- Case: [[Case 123]]

## Timeline
[[2020-01-01 - Key Event]]"""),

    ("People", "Relative Name",
     fm("person", "family", "medium", ["family"]),
     """# Relative Name
Relationship to [[Subject Name]]. **Certainty: medium** — explain the inference."""),

    ("People", "Unrelated Namesake",
     fm("person", "homonym-unrelated", "confirmed-unrelated", ["unrelated"]),
     """# Unrelated Namesake — not related
Shares the surname only. **Not connected** to [[Subject Name]]. Disambiguation only."""),

    ("Organizations", "Advocacy Org",
     fm("organization", "supporter", "high", ["supporter"]),
     """# Advocacy Org
Represents [[Subject Name]] in [[Case 123]]."""),

    ("Cases", "Case 123",
     fm("legal-case", None, "high", ["case"], date="2020-06-01"),
     """# Case 123
Filed by [[Advocacy Org]] for [[Subject Name]]."""),

    ("Events", "2020-01-01 - Key Event",
     fm("event", None, "high", ["timeline"], date="2020-01-01"),
     """# 2020-01-01 — Key Event
What happened to [[Subject Name]]."""),

    ("", "00 - MOC",
     fm("moc", None, None, ["moc"]),
     """# 🗺️ Map of Content
Start here. Hub: [[Subject Name]].
Open Graph View with `Ctrl+G`. Install Dataview/Excalidraw/Timelines if prompted (Trust author)."""),

    ("", "99 - Dashboard",
     fm("dashboard", None, None, ["dashboard"]),
     """# 📊 Dashboard (needs Dataview)
```dataview
TABLE certainty, role FROM "People" SORT certainty ASC
```
```dataview
TABLE date FROM #timeline SORT date ASC
```
## Open tasks
- [ ] example research gap
```dataview
TASK WHERE !completed
```"""),

    ("", "Timeline",
     fm("timeline-view", None, None, ["timeline-view"]),
     """# 🕰️ Timeline (needs timelines-revamped)
<div class="ob-timelines" data-tags="timeline" data-divHeight="600"></div>"""),
]


# ===========================================================================
# 4) Excalidraw generator (.excalidraw.md the plugin reads)
# ===========================================================================
def _node(eid, x, y, w, h, label, fill, group):
    rect = {"type": "rectangle", "version": 1, "versionNonce": 1, "isDeleted": False,
            "id": eid, "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
            "roughness": 1, "opacity": 100, "angle": 0, "x": x, "y": y,
            "strokeColor": "#1e1e1e", "backgroundColor": fill, "width": w, "height": h,
            "seed": 1, "groupIds": [group] if group else [], "frameId": None,
            "roundness": {"type": 3}, "boundElements": [{"type": "text", "id": eid + "_t"}],
            "updated": 1, "link": None, "locked": False}
    text = {"type": "text", "version": 1, "versionNonce": 2, "isDeleted": False,
            "id": eid + "_t", "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
            "roughness": 1, "opacity": 100, "angle": 0, "x": x + 6, "y": y + h / 2 - 12,
            "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
            "width": w - 12, "height": 24, "seed": 1, "groupIds": [], "frameId": None,
            "roundness": None, "boundElements": [], "updated": 1, "link": None, "locked": False,
            "fontSize": 16, "fontFamily": 1, "text": label, "rawText": label,
            "textAlign": "center", "verticalAlign": "middle", "containerId": eid,
            "originalText": label, "lineHeight": 1.25, "baseline": 18}
    return [rect, text]


def _arrow(eid, x1, y1, x2, y2):
    return [{"type": "arrow", "version": 1, "versionNonce": 3, "isDeleted": False,
             "id": eid, "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
             "roughness": 1, "opacity": 100, "angle": 0, "x": x1, "y": y1,
             "strokeColor": "#495057", "backgroundColor": "transparent",
             "width": abs(x2 - x1), "height": abs(y2 - y1), "seed": 1, "groupIds": [],
             "frameId": None, "roundness": {"type": 2}, "boundElements": [], "updated": 1,
             "link": None, "locked": False, "points": [[0, 0], [x2 - x1, y2 - y1]],
             "lastCommittedPoint": None, "startBinding": None, "endBinding": None,
             "startArrowhead": None, "endArrowhead": "arrow"}]


def _excalidraw_file(folder, name, elements):
    scene = {"type": "excalidraw", "version": 2, "source": "build_vault_template.py",
             "elements": elements,
             "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"}, "files": {}}
    body = ("---\nexcalidraw-plugin: parsed\ntags: [excalidraw]\n---\n\n"
            "# Excalidraw Data\n\n## Drawing\n```json\n"
            + json.dumps(scene, ensure_ascii=False, indent=1) + "\n```\n")
    d = os.path.join(VAULT, folder)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, name + ".excalidraw.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    return path


def build_relations_diagram():
    """EDIT to draw your network. Example: hub + 3 branches + a disconnected homonym."""
    els = []
    els += _node("hub", 360, 260, 200, 70, "Subject Name", "#ffd700", "g")
    els += _node("fam", 120, 120, 180, 50, "Relative", "#a5d8ff", "g")
    els += _node("org", 640, 200, 180, 50, "Advocacy Org", "#b2f2bb", "g")
    els += _node("case", 640, 300, 180, 50, "Case 123", "#d0bfff", "g")
    els += _node("hom", 700, 460, 200, 60, "Unrelated namesake", "#e9ecef", "g2")
    els += _arrow("a1", 360, 280, 300, 145)
    els += _arrow("a2", 560, 280, 640, 225)
    els += _arrow("a3", 560, 300, 640, 325)
    return _excalidraw_file("Diagrams", "Relations", els)


def build_timeline_diagram():
    els = []
    items = [n for n in NOTES if n[0] == "Events"]
    y = 80
    for i, (_, name, _, _) in enumerate(items):
        els += _node(f"t{i}", 200, y, 340, 50, name, "#ffc9c9", "tl")
        if i:
            els += _arrow(f"ta{i}", 370, y - 30, 370, y)
        y += 90
    return _excalidraw_file("Diagrams", "Timeline Visual", els)


# ===========================================================================
# 5) .obsidian configuration
# ===========================================================================
def write_obsidian_config(rtl=True):
    cfg = os.path.join(VAULT, ".obsidian")
    os.makedirs(cfg, exist_ok=True)

    app = {"rightToLeft": rtl, "defaultViewMode": "preview", "livePreview": True,
           "newFileLocation": "root", "attachmentFolderPath": "Diagrams",
           "showLineNumber": False}
    with open(os.path.join(cfg, "app.json"), "w", encoding="utf-8") as f:
        json.dump(app, f, ensure_ascii=False, indent=2)

    graph = {"collapse-filter": False, "search": "", "showTags": True,
             "showAttachments": False, "hideUnresolved": False, "showOrphans": True,
             "collapse-color-groups": False,
             "colorGroups": [{"query": f"tag:#{t}", "color": {"a": 1, "rgb": rgb}}
                             for t, rgb in COLORS.items()],
             "collapse-display": False, "showArrow": True, "textFadeMultiplier": 0,
             "nodeSizeMultiplier": 1.4, "lineSizeMultiplier": 1, "collapse-forces": False,
             "centerStrength": 0.5, "repelStrength": 12, "linkStrength": 1,
             "linkDistance": 250, "scale": 1, "close": False}
    with open(os.path.join(cfg, "graph.json"), "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)

    core = ["file-explorer", "global-search", "switcher", "graph", "backlink",
            "outgoing-link", "tag-pane", "page-preview", "templates", "note-composer",
            "command-palette", "markdown-importer", "outline", "word-count", "file-recovery"]
    with open(os.path.join(cfg, "core-plugins.json"), "w", encoding="utf-8") as f:
        json.dump(core, f, ensure_ascii=False, indent=2)

    community = ["dataview", "obsidian-excalidraw-plugin", "timelines-revamped"]
    with open(os.path.join(cfg, "community-plugins.json"), "w", encoding="utf-8") as f:
        json.dump(community, f, ensure_ascii=False, indent=2)


# ===========================================================================
# Main
# ===========================================================================
def main():
    os.makedirs(VAULT, exist_ok=True)
    written = [write(*n) for n in NOTES]
    written.append(build_relations_diagram())
    written.append(build_timeline_diagram())
    write_obsidian_config()
    print(f"Vault built at: {VAULT}")
    print(f"Files written: {len(written)}")


if __name__ == "__main__":
    main()
