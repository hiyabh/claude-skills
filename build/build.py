"""Build the whole site: validate content, pack skills, render pages + hub.

Usage:  python build/build.py [--no-pack]
"""
import os
import shutil
import stat
import sys

import package
import render_hub
import render_skill
from common import CATEGORIES, DL_DIR, PAGES_DIR, SRC_DIR, load_internal

REQUIRED_FIELDS = ("name", "category", "icon", "title", "tagline", "what")
MAX_TAGLINE = 120
FORBIDDEN_DASHES = ("—", "–")


def validate(pages):
    errors = []
    for page in pages:
        name = page["name"]
        missing = [f for f in REQUIRED_FIELDS if not page.get(f)]
        if missing:
            errors.append(f"{name}: missing fields {missing}")
        if page.get("category") not in CATEGORIES:
            errors.append(f"{name}: unknown category {page.get('category')!r}")
        if len(page.get("tagline", "")) > MAX_TAGLINE:
            errors.append(f"{name}: tagline longer than {MAX_TAGLINE} chars")
        if not (SRC_DIR / name / "SKILL.md").is_file():
            errors.append(f"{name}: no src/{name}/SKILL.md")
        if any(d in str(page) for d in FORBIDDEN_DASHES):
            errors.append(f"{name}: contains an em/en dash - use '-'")
    sources = {d.name for d in SRC_DIR.iterdir() if d.is_dir()}
    for orphan in sorted(sources - {p["name"] for p in pages}):
        errors.append(f"src/{orphan}: has no content/{orphan}.json")
    return errors


def _clear_readonly(func, path, _exc):
    # Windows marks some folders FILE_ATTRIBUTE_READONLY, which blocks rmdir.
    os.chmod(path, stat.S_IWRITE)
    func(path)


def prune(names):
    """Delete generated pages/tarballs of skills that no longer exist."""
    for page_dir in PAGES_DIR.glob("*"):
        if page_dir.is_dir() and page_dir.name not in names:
            shutil.rmtree(page_dir, onexc=_clear_readonly)
    for tarball in DL_DIR.glob("*.tar.gz"):
        if tarball.name[:-len(".tar.gz")] not in names:
            tarball.unlink()


def main():
    pages = load_internal()
    errors = validate(pages)
    if errors:
        print("Build failed - fix these content errors:", *errors, sep="\n  ")
        return 1
    # CI rebuilds HTML only: a different zlib would re-encode unchanged tarballs.
    if "--no-pack" not in sys.argv:
        package.pack_all()
    for page in pages:
        render_skill.render(page)
    prune({p["name"] for p in pages})
    cards, skills = render_hub.render()
    print(f"OK: {len(pages)} skill pages, hub with {cards} cards / {skills} skills")
    return 0


if __name__ == "__main__":
    sys.exit(main())
