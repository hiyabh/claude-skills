---
name: archive-organizer
description: >
  Expert skill for organizing large unstructured file collections — email exports, legal documents,
  NGO archives, research folders, or any mixed document archive. Use this skill whenever the user
  mentions having hundreds or thousands of unorganized files they need to sort, classify, or clean up.
  Trigger phrases include: "organize my files", "sort my archive", "classify documents",
  "ארגן קבצים", "מיין תיקיות", "סדר את הארכיב", "I have thousands of files", "create a folder structure",
  "sort my emails", "clean up my downloads", "help me organize", "file organization",
  "document classification", "de-duplicate files". Also trigger when the user describes a messy
  directory with many files and no clear structure, or when they want a systematic folder hierarchy
  created. This skill provides the complete methodology, Python script templates, and proven
  patterns for organizing any size archive safely and reproducibly.
---

# Archive Organizer

A complete methodology for turning an unstructured file collection into a clean, navigable archive —
using only Python, with zero deletions, full logging, and reproducible scripts.

> `<SKILL_DIR>` = the folder that contains this SKILL.md (normally `~/.claude/skills/archive-organizer`).
> Resolve it once to an absolute path before running commands — PowerShell/cmd do not expand `~` inside
> quotes. All script paths below (e.g. `scripts/scan_archive.py`) are relative to `<SKILL_DIR>`.

> **Core principle:** All operations use `shutil.move()`, never `os.remove()`. Nothing is ever
> permanently deleted. "Junk" files go to a quarantine folder for human review.

---

## Workflow Overview

```
Phase 0: Reconnaissance  →  understand what's there
Phase 1: Design          →  agree on folder structure with user
Phase 2: Scaffold        →  create empty folder hierarchy
Phase 3: Classify        →  move files into categories (multi-pass)
Phase 4: Rename          →  strip metadata, clean filenames
Phase 5: Clean           →  quarantine junk/duplicates
Phase 6: Report          →  summary log + optional video
```

Always start with reconnaissance before writing any classification script. The patterns you find
in Phase 0 directly determine which keywords and rules to use in Phase 3.

---

## Phase 0: Reconnaissance

Run `scripts/scan_archive.py` (bundled). It outputs:
- Total file/folder count
- File type distribution
- Top-level folder structure
- Sample of 30 filenames (to understand naming conventions)
- Rough size breakdown

From the scan, identify:
1. **Naming convention** — are files named by date, sender, subject, hash, or random?
2. **Main categories** implied by filenames or existing folders
3. **Junk patterns** — temp files, delivery receipts, duplicates, auto-recovery files
4. **Scale** — dozens vs. hundreds vs. thousands changes the approach

Share the scan findings with the user before moving forward.

---

## Phase 1: Design — Folder Structure

Propose a numbered folder hierarchy. Numbered prefixes (`1.`, `2.`, ...) ensure folders sort
consistently in file explorers regardless of OS locale.

**Pattern:**
```
ROOT/
├── 1. Category Name/
│   ├── Sub-folder A/
│   └── Sub-folder B/
├── 2. Category Name/
│   └── ...
├── לסיווג/          ← files needing manual review
└── מומלץ למחיקה/   ← quarantine (NOT deleted, just segregated)
    ├── הודעות מערכת ומיילי שגיאה/
    ├── קבצים זמניים/
    └── כפילויות/
```

Ask the user to confirm or adjust the proposed structure before scripting.

---

## Phase 2: Scaffold

Create the empty folder hierarchy with `os.makedirs(path, exist_ok=True)`.

Write a single scaffold script that creates ALL folders at once. This is safe to re-run and
serves as living documentation of the intended structure.

---

## Phase 3: Classification — Multi-Pass Strategy

### Architecture

Each classification script follows this pattern:
1. Walk source directory
2. Extract a clean "subject" from each filename (strip metadata prefix)
3. Match subject against keyword rules (ordered by priority)
4. Move matching files to destination with `shutil.move()`
5. Files that don't match stay in source ("remaining")
6. Write a log

**Never try to classify everything in one pass.** Run multiple targeted passes:
- Pass 1: Broad — the most common, obvious categories (handles 60-80%)
- Pass 2: Remaining patterns discovered after seeing what's left
- Pass 3–N: Each pass whittles down the unclassified set
- Final: Move whatever remains to `לסיווג/` (manual review folder)

### Keyword Rule Structure

```python
RULES = [
    # Priority order matters — first match wins
    ('category_key', ['keyword1', 'keyword2', 'keyword3']),
    ('other_key',    ['another keyword', 'phrase']),
]

def classify(subject: str) -> str:
    subj_lower = subject.lower()
    for dest_key, keywords in RULES:
        for kw in keywords:
            if kw.lower() in subj_lower:
                return dest_key
    return 'UNCLASSIFIED'
```

Use `scripts/classify_template.py` as the starting point for each pass.

### Between Passes

After each pass, run `scripts/scan_archive.py` on the remaining files to see what's left.
Sample the filenames, identify new patterns, add new rules to the next pass script.

---

## Phase 4: Filename Renaming

Many archives have filenames with metadata prefixes that obscure the actual content.

**Common pattern for email exports:**
```
[sender@domain.com] [recipient@domain.com] 2024-03-15T09-22 Re_Fwd_Re_ Subject text.pdf
```

Strip to:
```
2024-03-15 - Subject text.pdf
```

Use `scripts/classify_template.py` which includes `parse_filename()` and `make_new_name()`.

**Rules for clean filenames:**
- Keep the date prefix: `YYYY-MM-DD - `
- Strip Re_/Fwd_/RE_/FW_ prefixes (loop until stable)
- Replace invalid chars `< > : " / \ | ? *` with `_`
- Truncate to 120 chars max (leaves room for parent path)
- If no subject, use `ללא נושא` or `untitled`

---

## Phase 5: Junk Detection

Use `scripts/find_junk.py` (bundled). It finds and quarantines:

| Junk Type | Pattern | Bucket |
|-----------|---------|--------|
| System emails | `Undeliverable_`, `Delivery Status`, `JumboMail`, scanner notifications | הודעות מערכת |
| Word temp files | `~WRL*.tmp`, `~WRA*.docx`, `Thumbs.db`, `~$*.docx` | קבצים זמניים |
| Auto-recovery | `שמירת שחזור אוטומטי`, `AutoRecovery save of` | שחזורים |
| Hash names | `[0-9a-f]{20,}.pdf` | קבצים ללא שם |
| Download dupes | `Download (N).pdf`, `filename (1).docx` | כפילויות |
| docx+pdf pairs | Same base name exists as both `.docx` and `.pdf` in same folder | כפילויות |

---

## Phase 6: Summary Report

Always end with a text log file saved inside the archive root. Include:
- Total files moved per category
- Total files quarantined (and why)
- Errors (path too long, permission denied, etc.)
- Remaining unclassified count

---

## Critical Technical Patterns

### Safe Move with Unique Destination

```python
import os, shutil

def unique_dst(dst_dir: str, fname: str) -> str:
    base, ext = os.path.splitext(fname)
    candidate = os.path.join(dst_dir, fname)
    if not os.path.exists(candidate):
        return candidate
    i = 2
    while True:
        candidate = os.path.join(dst_dir, f'{base} ({i}){ext}')
        if not os.path.exists(candidate):
            return candidate
        i += 1

def mv(src: str, dst_dir: str, new_name: str = None) -> None:
    if not os.path.exists(src):
        return
    fname = new_name or os.path.basename(src)
    os.makedirs(dst_dir, exist_ok=True)
    dst = unique_dst(dst_dir, fname)
    try:
        shutil.move(src, dst)
        log(f'[OK] {src} → {dst}')
    except Exception as e:
        log(f'[ERR] {src}: {e}')
```

### Windows Long Path Handling (>260 chars)

```python
PFX = '\\\\'   # \\?\ in actual string — extended path prefix

for dirpath, dirs, files in os.walk(root):
    for fname in files:
        full = os.path.join(dirpath, fname)
        if len(full) > 255:
            src_ext = PFX + full
            short   = PFX + os.path.join(dirpath, 'temp_short.pdf')
            os.rename(src_ext, short)
            shutil.move(os.path.join(dirpath, 'temp_short.pdf'), dst)
```

**Key insight:** `os.path.isfile(long_path)` returns False for paths > 260 chars.
Always use `os.walk()` to find files when long paths may be present.

### Hebrew / RTL Filename Support (Windows)

```python
import sys
sys.stdout.reconfigure(encoding='utf-8')
```

Run with `py script.py`. Python 3.6+ handles Hebrew filenames natively on Windows NTFS.

### Folder Name with Quotes on Windows

Windows forbids `"` in filenames. Replace with Hebrew gershayim `״` (U+05F4).

---

## Script Templates (in `scripts/`)

| Script | Purpose |
|--------|---------|
| `scan_archive.py` | Phase 0 reconnaissance — run this first |
| `classify_template.py` | Phase 3 starting point — copy and fill in RULES + DESTS |
| `find_junk.py` | Phase 5 junk/duplicate quarantine |

---

## Reading the Reference Files

- `references/email-patterns.md` — Parsing email export filenames (Gmail Takeout, Outlook, custom)
- `references/windows-notes.md` — Long paths, encoding, forbidden chars, `py` vs `python`

---

## Common Mistakes to Avoid

1. **Classifying everything in one pass** — scan first, then write targeted rules.
2. **Using `os.remove()` or `shutil.rmtree()`** — Never delete. Move to quarantine.
3. **Using `os.listdir()` + `os.path.isfile()` on deep paths** — Fails silently. Use `os.walk()`.
4. **Hardcoding destination paths in one big dict** — Define path helpers instead.
5. **Trying to read file contents for classification** — Too slow. Filename is almost always enough.
6. **Not checking `os.path.exists()` before moving** — Previous passes may have moved the file.
7. **Overwriting destinations** — Always use `unique_dst()`.
