#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
find_junk.py — Phase 5 Junk & Duplicate Quarantine
====================================================
NEVER deletes anything — only moves to quarantine sub-buckets.

Usage:
    py find_junk.py               # dry run
    py find_junk.py --execute     # actually moves files + log
"""

import os, re, sys, shutil, argparse
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

# ══════════════════════════════════════════════════════════════════
#  CONFIGURE THIS SECTION
# ══════════════════════════════════════════════════════════════════

ROOT = r'C:\path\to\archive'
QUARANTINE = os.path.join(ROOT, 'מומלץ למחיקה')
BUCKETS = {
    'system':    os.path.join(QUARANTINE, 'הודעות מערכת ומיילי שגיאה'),
    'temp':      os.path.join(QUARANTINE, 'קבצים זמניים'),
    'recovery':  os.path.join(QUARANTINE, 'שחזורים אוטומטיים'),
    'hash':      os.path.join(QUARANTINE, 'קבצים ללא שם משמעותי'),
    'dupes':     os.path.join(QUARANTINE, 'כפילויות'),
}
LOG_PATH = os.path.join(os.path.dirname(__file__), 'find_junk_log.txt')

# ══════════════════════════════════════════════════════════════════
#  JUNK PATTERNS
# ══════════════════════════════════════════════════════════════════

JUNK_RULES = [
    ('system',   re.compile(r'(Undeliverable_|Delivery[ _]Status|NDR_|JumboMail|Mailer-Daemon|'
                             r'נסיון פקס|Message from|כניסה חדשה|המערכת)', re.I)),
    ('temp',     re.compile(r'^(~WR[LA].*|~\$.*|Thumbs\.db|desktop\.ini)$', re.I)),
    ('recovery', re.compile(r'(שמירת שחזור|AutoRecovery save of|AutoRecovery Save)', re.I)),
    ('hash',     re.compile(r'^[0-9a-f]{20,}\.\w+$', re.I)),
    ('dupes',    re.compile(r'^.+\s*\(\d+\)\.\w+$')),
]

# ══════════════════════════════════════════════════════════════════
#  UTILITIES
# ══════════════════════════════════════════════════════════════════

_log_lines = []
def log(msg):
    print(msg)
    _log_lines.append(msg)
def write_log():
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write('\n'.join(_log_lines) + '\n')

def unique_dst(dst_dir, fname):
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

def mv(src, bucket_key, dry_run=False):
    if not os.path.exists(src):
        return 'skipped'
    dst_dir = BUCKETS[bucket_key]
    fname = os.path.basename(src)
    dst = unique_dst(dst_dir, fname)
    if dry_run:
        log(f'  [DRY-{bucket_key.upper()}]  {fname}')
        return 'moved'
    os.makedirs(dst_dir, exist_ok=True)
    try:
        shutil.move(src, dst)
        log(f'  [OK-{bucket_key.upper()}]  {fname}')
        return 'moved'
    except Exception as e:
        log(f'  [ERR]  {src}: {e}')
        return 'error'

def pass_pattern_junk(all_files, dry_run):
    counts = {k: 0 for k in BUCKETS}
    for full_path in all_files:
        fname = os.path.basename(full_path)
        for bucket_key, pat in JUNK_RULES:
            if pat.search(fname):
                result = mv(full_path, bucket_key, dry_run)
                if result == 'moved':
                    counts[bucket_key] += 1
                break
    return counts

def pass_docx_pdf_dupes(root, dry_run):
    moved = 0
    quarantine_abs = os.path.abspath(QUARANTINE)
    for dirpath, dirs, files in os.walk(root):
        if os.path.abspath(dirpath).startswith(quarantine_abs):
            dirs[:] = []
            continue
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        pdf_bases  = {os.path.splitext(f)[0].lower(): f for f in files if f.lower().endswith('.pdf')}
        docx_bases = {os.path.splitext(f)[0].lower(): f for f in files if f.lower().endswith('.docx')}
        for base_lower, docx_fname in docx_bases.items():
            if base_lower in pdf_bases:
                src = os.path.join(dirpath, docx_fname)
                log(f'  [DUPE]  {docx_fname}')
                result = mv(src, 'dupes', dry_run)
                if result == 'moved':
                    moved += 1
    return moved

def run(dry_run=False):
    log(f'\n{"="*60}')
    log(f'{"DRY RUN — " if dry_run else ""}FIND_JUNK  {datetime.now():%Y-%m-%d %H:%M}')
    log(f'Root: {ROOT}')
    log(f'{"="*60}')

    quarantine_abs = os.path.abspath(QUARANTINE)
    all_files = []
    for dirpath, dirs, files in os.walk(ROOT):
        if os.path.abspath(dirpath).startswith(quarantine_abs):
            dirs[:] = []
            continue
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for fname in files:
            all_files.append(os.path.join(dirpath, fname))

    log(f'\nScanning {len(all_files):,} files...\n')

    log('Pass 1: Pattern junk')
    pattern_counts = pass_pattern_junk(all_files, dry_run)

    log('\nPass 2: docx+pdf duplicates')
    dupe_count = pass_docx_pdf_dupes(ROOT, dry_run)

    total_junk = sum(pattern_counts.values()) + dupe_count
    log(f'\n{"─"*40}')
    log(f'JUNK QUARANTINE SUMMARY')
    log(f'  System / delivery emails:  {pattern_counts.get("system", 0):>6,}')
    log(f'  Temp / lock files:         {pattern_counts.get("temp", 0):>6,}')
    log(f'  Auto-recovery saves:       {pattern_counts.get("recovery", 0):>6,}')
    log(f'  Hash-named files:          {pattern_counts.get("hash", 0):>6,}')
    log(f'  Download duplicates (N):   {pattern_counts.get("dupes", 0):>6,}')
    log(f'  docx+pdf pairs:            {dupe_count:>6,}')
    log(f'  {"─"*30}')
    log(f'  TOTAL quarantined:         {total_junk:>6,}')
    log(f'{"─"*40}\n')
    log(f'Review files in: {QUARANTINE}')
    if not dry_run:
        write_log()

def main():
    p = argparse.ArgumentParser(description='Archive junk quarantine')
    p.add_argument('--execute', action='store_true', help='Actually move files')
    args = p.parse_args()
    run(dry_run=not args.execute)

if __name__ == '__main__':
    main()
