# -*- coding: utf-8 -*-
"""
verify_vault.py — sanity-check an Obsidian vault before opening it.

Counts notes, verifies every note has YAML frontmatter, and finds BROKEN wikilinks
(a [[target]] whose target filename does not exist anywhere in the vault).
Exit code 1 if any broken links — so it can gate a build.

Usage:  python verify_vault.py [path-to-vault]
        (defaults to ./MyVault relative to this script)
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
VAULT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "MyVault")

md_files = []
for dp, _, fns in os.walk(VAULT):
    if ".obsidian" in dp:
        continue
    md_files += [os.path.join(dp, fn) for fn in fns if fn.endswith(".md")]

# valid link targets = note basenames (and the bare name of .excalidraw.md files)
names = set()
for p in md_files:
    base = os.path.basename(p)[:-3]
    names.add(base)
    if base.endswith(".excalidraw"):
        names.add(base[:-len(".excalidraw")])

link_re = re.compile(r"\[\[([^\]]+)\]\]")
broken, total_links, no_fm = [], 0, []

for p in md_files:
    with open(p, encoding="utf-8") as f:
        txt = f.read()
    if not txt.startswith("---"):
        no_fm.append(os.path.basename(p))
    for m in link_re.findall(txt):
        target = m.split("|")[0].split("#")[0].strip()
        if not target:
            continue
        total_links += 1
        if target not in names:
            broken.append((os.path.basename(p), target))

print(f"Vault: {VAULT}")
print(f"MD files (excl .obsidian): {len(md_files)}")
print(f"Unique note names: {len(names)}")
print(f"Total wikilinks: {total_links}")
print(f"Notes missing frontmatter: {len(no_fm)} {no_fm if no_fm else ''}")
print(f"Broken wikilinks: {len(broken)}")
for src, tgt in broken:
    print(f"  [{src}] -> [[{tgt}]]")

cfg = os.path.join(VAULT, ".obsidian")
for c in ["app.json", "graph.json", "community-plugins.json", "core-plugins.json"]:
    print(f"config {c}: {'OK' if os.path.exists(os.path.join(cfg, c)) else 'MISSING'}")

sys.exit(1 if broken else 0)
