#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
classify_template.py — Phase 3 Classification Template
=======================================================
Copy this file and fill in:
  1. ROOT       — the source folder to classify
  2. DESTS      — mapping of category keys → destination folder paths
  3. RULES      — keyword rules (priority-ordered, first match wins)

Run repeatedly (multi-pass). Each run moves matching files and leaves the
rest in place. After each pass, run scan_archive.py on what remains to find
the next batch of patterns.

Usage:
    py classify_template.py               # dry run — shows what would move
    py classify_template.py --execute     # actually moves files + writes log
"""

import os, re, sys, shutil, argparse
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

# ══════════════════════════════════════════════════════════════════
#  CONFIGURE THIS SECTION
# ══════════════════════════════════════════════════════════════════

# Source folder — where unclassified files currently live
ROOT = r'C:\path\to\archive\source'

# Destination mapping — fill in your real folder paths.
DESTS = {
    'cat1':    r'C:\path\to\archive\1. Category One',
    'cat2':    r'C:\path\to\archive\2. Category Two',
    'cat3':    r'C:\path\to\archive\3. Category Three',
    'junk':    r'C:\path\to\archive\מומלץ למחיקה',
    'review':  r'C:\path\to\archive\לסיווג',
}

# Classification rules — ordered by priority, first match wins.
RULES = [
    ('cat1', [
        'specific phrase one',
        'another specific term',
    ]),
    ('cat2', [
        'keyword for category two',
    ]),
    ('cat3', [
        'cat3 keyword',
    ]),
    ('junk', [
        'undeliverable',
        'delivery status',
        'mailer-daemon',
    ]),
]

LOG_PATH = os.path.join(os.path.dirname(__file__), 'classify_log.txt')

# ══════════════════════════════════════════════════════════════════
#  CORE UTILITIES
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

def mv(src, dst_dir, new_name=None, dry_run=False):
    if not os.path.exists(src):
        log(f'  [SKIP] not found: {src}')
        return 'skipped'
    fname = new_name or os.path.basename(src)
    dst = unique_dst(dst_dir, fname)
    if dry_run:
        log(f'  [DRY]  {os.path.basename(src)} -> {dst}')
        return 'moved'
    os.makedirs(dst_dir, exist_ok=True)
    try:
        shutil.move(src, dst)
        log(f'  [OK]   {os.path.basename(src)}')
        return 'moved'
    except Exception as e:
        log(f'  [ERR]  {src}: {e}')
        return 'error'

# ══════════════════════════════════════════════════════════════════
#  FILENAME PARSING
# ══════════════════════════════════════════════════════════════════

def parse_filename(filename):
    base, ext = os.path.splitext(filename)
    result = {'sender': '', 'recipient': '', 'date_str': '', 'subject': base, 'ext': ext}
    m = re.match(r'^\[([^\]]+)\]\s*(.*)', base)
    if m:
        result['sender'] = m.group(1)
        base = m.group(2)
    m = re.match(r'^\[([^\]]+)\]\s*(.*)', base)
    if m:
        result['recipient'] = m.group(1)
        base = m.group(2)
    m = re.match(r'^(\d{4}-\d{2}-\d{2})(?:T\d{2}-\d{2})?\s*(.*)', base)
    if m:
        result['date_str'] = m.group(1)
        base = m.group(2)
    prev = None
    while prev != base:
        prev = base
        base = re.sub(r'^(Re_|RE_|Fwd_|FW_|Re:|Fwd:)\s*', '', base, flags=re.IGNORECASE).strip()
    result['subject'] = base.strip(' ._-') or 'ללא נושא'
    return result

def make_new_name(parsed, max_subject_len=100):
    subject = parsed['subject'][:max_subject_len]
    subject = re.sub(r'[<>:"/\\|?*]', '_', subject)
    subject = re.sub(r'[ _]{2,}', ' ', subject).strip()
    ext = parsed['ext']
    if parsed['date_str']:
        return f"{parsed['date_str']} - {subject}{ext}"
    return f"{subject}{ext}"

# ══════════════════════════════════════════════════════════════════
#  CLASSIFICATION ENGINE
# ══════════════════════════════════════════════════════════════════

def classify(subject):
    subj_lower = subject.lower()
    for dest_key, keywords in RULES:
        for kw in keywords:
            if kw.lower() in subj_lower:
                return dest_key
    return 'UNCLASSIFIED'

def run(dry_run=False):
    log(f'\n{"="*60}')
    log(f'{"DRY RUN — " if dry_run else ""}CLASSIFY  {datetime.now():%Y-%m-%d %H:%M}')
    log(f'Source: {ROOT}')
    log(f'{"="*60}\n')

    counts = {'moved': 0, 'skipped': 0, 'error': 0, 'unclassified': 0}
    dest_counts = {k: 0 for k in DESTS}

    for dirpath, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for fname in files:
            full = os.path.join(dirpath, fname)
            parsed = parse_filename(fname)
            dest_key = classify(parsed['subject'])
            if dest_key == 'UNCLASSIFIED':
                counts['unclassified'] += 1
                continue
            dst_dir = DESTS[dest_key]
            new_name = make_new_name(parsed)
            result = mv(full, dst_dir, new_name=new_name, dry_run=dry_run)
            counts[result] += 1
            if result == 'moved':
                dest_counts[dest_key] += 1

    log(f'\n{"─"*40}')
    log(f'RESULTS')
    log(f'  Moved:         {counts["moved"]:>6,}')
    log(f'  Unclassified:  {counts["unclassified"]:>6,}')
    log(f'  Skipped:       {counts["skipped"]:>6,}')
    log(f'  Errors:        {counts["error"]:>6,}')
    log(f'\nBy destination:')
    for key, n in dest_counts.items():
        if n:
            log(f'  {key:<14} {n:>6,}')
    log(f'{"─"*40}\n')
    log('Run scan_archive.py on the source folder to see what remains.')
    if not dry_run:
        write_log()

def main():
    p = argparse.ArgumentParser(description='Keyword-based file classifier')
    p.add_argument('--execute', action='store_true', help='Actually move files (default: dry run)')
    args = p.parse_args()
    run(dry_run=not args.execute)

if __name__ == '__main__':
    main()
