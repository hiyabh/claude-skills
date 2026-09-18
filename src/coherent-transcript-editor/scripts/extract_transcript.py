"""
Extract clean spoken content from a raw auto-transcription, stripping the
timestamp / duration marker lines that auto-transcribers interleave.

Handles:
  - DOCX input (uses glob so Hebrew filenames don't break on Windows codepage)
  - TXT / MD / SRT / VTT input
  - Numeric timestamps:  0:06 / 1:09 / 1:09:09
  - Hebrew duration markers:  "6 שניות" / "1 דקה, 4 שניות" / "שתי דקות, 10 שניות"

Usage:
    python extract_transcript.py [<path-to-file>] [--out <out.txt>]

If no path is given, picks the single *.docx in the current directory.
Writes one cleaned paragraph per line, prefixed with its index ("000| ..."),
so the editor can read every word with stable line references.
"""
import sys
import os
import re
import glob

TS = re.compile(r'^\d{1,2}:\d{2}(:\d{2})?$')
_NUM = (r'(?:\d+|אחת|שתי|שתיים|שלוש|שלושה|ארבע|ארבעה|חמש|חמישה|שש|שישה|'
        r'שבע|שבעה|שמונה|תשע|תשעה|עשר|עשרה|אחת עשרה|שתים עשרה)')
DUR = re.compile(
    rf'^{_NUM}?\s*(שנייה|שניות|דקה|דקות|שעה|שעות)'
    rf'(\s*,?\s*ו?{_NUM}?\s*(שנייה|שניות|דקה|דקות))*$'
)
# SRT/VTT cue lines like "00:00:06,000 --> 00:00:09,000"
CUE = re.compile(r'^\d{2}:\d{2}:\d{2}[.,]\d{3}\s*-->')
SEQ = re.compile(r'^\d+$')  # bare SRT sequence numbers


def is_marker(t):
    return bool(TS.match(t) or DUR.match(t) or CUE.match(t) or t == 'WEBVTT')


def read_paragraphs(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == '.docx':
        from docx import Document
        d = Document(path)
        return [p.text.strip() for p in d.paragraphs if p.text.strip()]
    with open(path, 'r', encoding='utf-8') as f:
        return [ln.strip() for ln in f if ln.strip()]


def main():
    args = [a for a in sys.argv[1:]]
    out = None
    if '--out' in args:
        i = args.index('--out')
        out = args[i + 1]
        del args[i:i + 2]
    sys.stdout.reconfigure(encoding='utf-8')
    path = args[0] if args else None

    def sole_transcript():
        # Single transcript file in cwd, across supported extensions.
        cands = []
        for pat in ('*.docx', '*.txt', '*.srt', '*.vtt', '*.md'):
            cands += [c for c in glob.glob(pat) if not c.startswith('_')]
        return cands[0] if len(cands) == 1 else None

    if path is None or not os.path.isfile(path):
        # Windows mangles Hebrew filenames passed as argv; fall back to the
        # single transcript file in the current directory.
        recovered = sole_transcript()
        if recovered:
            if path is not None:
                print(f'note: "{path}" not found as given; '
                      f'using sole file in cwd: {recovered}')
            path = recovered
        else:
            print(f'ERROR: file not found ({path}), and could not pick a sole '
                  f'transcript in cwd. Pass an ASCII-named path explicitly.')
            sys.exit(1)

    paras = read_paragraphs(path)
    kept = [t for t in paras if not is_marker(t) and not SEQ.match(t)]

    out = out or '_raw_content.txt'
    with open(out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(f'{i:03d}| {t}' for i, t in enumerate(kept)))

    words = sum(len(t.split()) for t in kept)
    sys.stdout.reconfigure(encoding='utf-8')
    print(f'source: {path}')
    print(f'total paragraphs: {len(paras)}  |  kept content: {len(kept)}  |  '
          f'removed markers: {len(paras) - len(kept)}')
    print(f'approx words: {words}')
    print(f'wrote: {out}')


if __name__ == '__main__':
    main()
