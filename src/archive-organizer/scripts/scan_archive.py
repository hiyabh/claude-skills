#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scan_archive.py — Phase 0 Reconnaissance
=========================================
Run this BEFORE writing any classification script.
Outputs a full picture of the archive: counts, types, naming patterns, top folders.

Usage:
    py scan_archive.py  C:\\path\\to\\archive
    py scan_archive.py  C:\\path\\to\\archive  --sample 50
    py scan_archive.py  C:\\path\\to\\archive  --depth 2
"""
import os, sys, re, argparse
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding='utf-8')

def parse_args():
    p = argparse.ArgumentParser(description='Archive reconnaissance scanner')
    p.add_argument('root', help='Root directory to scan')
    p.add_argument('--sample', type=int, default=30, help='Number of sample filenames to show')
    p.add_argument('--depth', type=int, default=3, help='Max folder depth for tree view')
    return p.parse_args()

def human_size(n):
    for unit in ['B','KB','MB','GB','TB']:
        if n < 1024:
            return f'{n:.1f} {unit}'
        n /= 1024
    return f'{n:.1f} PB'

def extract_subject(filename: str) -> str:
    """Strip common metadata prefixes to expose the real subject."""
    base = os.path.splitext(filename)[0]
    # Strip [sender] [recipient] YYYY-MM-DDTHH-MM prefix
    base = re.sub(r'^\\[.*?\\]\\s*(?:\\[.*?\\]\\s*)?(?:\\d{4}-\\d{2}-\\d{2}T\\d{2}-\\d{2}\\s*)?', '', base)
    # Strip Re_/Fwd_ chains
    prev = None
    while prev != base:
        prev = base
        base = re.sub(r'^(Re_|RE_|Fwd_|FW_|Re:|Fwd:)\\s*', '', base, flags=re.IGNORECASE).strip()
    return base.strip()

def main():
    args = parse_args()
    ROOT = os.path.abspath(args.root)

    if not os.path.isdir(ROOT):
        print(f'ERROR: {ROOT} is not a directory')
        sys.exit(1)

    print(f'\\n{"="*60}')
    print(f'ARCHIVE SCAN: {ROOT}')
    print(f'{"="*60}\\n')

    total_files = 0
    total_dirs  = 0
    total_size  = 0
    ext_counter = Counter()
    first_words = Counter()
    all_files   = []

    for dirpath, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        total_dirs += len(dirs)
        for fname in files:
            full = os.path.join(dirpath, fname)
            try:
                sz = os.path.getsize(full)
            except OSError:
                sz = 0
            total_files += 1
            total_size  += sz
            ext = os.path.splitext(fname)[1].lower() or '(no ext)'
            ext_counter[ext] += 1
            rel = os.path.relpath(full, ROOT)
            all_files.append((rel, sz))
            subj = extract_subject(fname)
            if subj:
                first_words[subj.split()[0].strip('._-') if subj.split() else '?'] += 1

    print('TOP-LEVEL STRUCTURE')
    print('-' * 40)
    for item in sorted(os.listdir(ROOT)):
        full = os.path.join(ROOT, item)
        if os.path.isdir(full):
            n = sum(len(fs) for _, _, fs in os.walk(full))
            print(f'  {item}/  ({n:,} files)')
        else:
            sz = os.path.getsize(full) if os.path.exists(full) else 0
            print(f'  {item}  ({human_size(sz)})')

    print(f'\\nSUMMARY')
    print('-' * 40)
    print(f'  Total files:   {total_files:,}')
    print(f'  Total folders: {total_dirs:,}')
    print(f'  Total size:    {human_size(total_size)}')

    print(f'\\nFILE TYPES (top 15)')
    print('-' * 40)
    for ext, cnt in ext_counter.most_common(15):
        bar = '█' * min(40, int(cnt / max(ext_counter.values()) * 40))
        print(f'  {ext:>12}  {cnt:>6,}  {bar}')

    print(f'\\nTOP FIRST WORDS IN SUBJECTS (top 25)')
    print('-' * 40)
    for word, cnt in first_words.most_common(25):
        print(f'  {cnt:>5,}  {word}')

    import random
    sample = random.sample(all_files, min(args.sample, len(all_files)))
    print(f'\\nSAMPLE FILENAMES ({args.sample} random)')
    print('-' * 40)
    for rel, sz in sorted(sample, key=lambda x: x[0]):
        print(f'  {rel[:120]}')

    junk_patterns = {
        'Temp Word files (~WRL, ~WRA)': re.compile(r'^~WR[LA].*\\.(tmp|docx)$', re.I),
        'Thumbs.db / desktop.ini': re.compile(r'^(Thumbs\\.db|desktop\\.ini)$', re.I),
        'Auto-recovery': re.compile(r'שמירת שחזור|AutoRecovery save', re.I),
        'Hash names (20+ hex chars)': re.compile(r'^[0-9a-f]{20,}\\.\\w+$', re.I),
        'Download (N) duplicates': re.compile(r'^.+\\s*\\(\\d+\\)\\.\\w+$'),
        'Undeliverable / Delivery': re.compile(r'Undeliverable_|Delivery Status|NDR_', re.I),
        'System / scanner noise': re.compile(r'(Message from|JumboMail|נסיון פקס|כניסה חדשה)', re.I),
    }

    print(f'\\nJUNK INDICATORS')
    print('-' * 40)
    for label, pat in junk_patterns.items():
        matches = [r for r, _ in all_files if pat.search(os.path.basename(r))]
        if matches:
            print(f'  {label}: {len(matches):,}')
            for m in matches[:3]:
                print(f'       {m[:100]}')
            if len(matches) > 3:
                print(f'       ... and {len(matches)-3} more')

    print(f'\\n{"="*60}')
    print('NEXT STEPS:')
    print('  1. Confirm folder structure with user (see SKILL.md Phase 1)')
    print('  2. Copy scripts/classify_template.py and fill in RULES + DESTS')
    print('  3. Run scripts/find_junk.py for automatic junk quarantine')
    print(f'{"="*60}\\n')

if __name__ == '__main__':
    main()
