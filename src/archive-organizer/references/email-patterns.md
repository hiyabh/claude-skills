# Email Export Filename Patterns

A reference guide for parsing filenames produced by common email exporters.
Read this when you need detail on a specific export format or when scan_archive.py
reveals naming patterns you haven't seen before.

---

## Table of Contents

1. Why filenames matter
2. Common exporter formats
3. The universal parse algorithm
4. Stripping Re / Fwd chains
5. Building clean output names
6. Multilingual subjects
7. Edge cases and gotchas

---

## 1. Why filenames matter

When an email archive is exported to files, all the classification signal sits in
the filename: sender, recipient, date, and subject. Reading file contents would be
far too slow for 10,000+ files. The filename is almost always sufficient.

---

## 2. Common Exporter Formats

### 2.1 Custom exporters (most common for NGO/legal archives)

```
[sender@domain.com] [recipient@domain.com] YYYY-MM-DDTHH-MM Subject text.pdf
[sender@domain.com] [recipient@domain.com] YYYY-MM-DDTHH-MM Re_Subject text.msg
[sender@domain.com] YYYY-MM-DD Subject text.pdf
```

Characteristics:
- Sender and optional recipient in square brackets
- ISO 8601 date with T separator, hours/minutes with hyphens (colons are illegal on Windows)
- Re_ and Fwd_ use underscores instead of spaces+colon
- Extension can be .pdf, .msg, .eml, .docx

Detection regex:
```python
re.match(r'^\[([^\]]+)\]\s*(?:\[([^\]]+)\]\s*)?(\d{4}-\d{2}-\d{2})', filename)
```

### 2.2 Gmail Takeout

```
YYYY-MM-DD Subject text.eml
[Subject text].eml            # no date in some versions
```

Characteristics:
- Date is YYYY-MM-DD without time
- No sender/recipient in filename
- Extension always .eml

### 2.3 Outlook PST/MSG export

```
Subject text.msg
RE Subject text.msg
FW_ Subject text.msg
```

Characteristics:
- No date or sender metadata in filename by default
- Re/Fwd may use RE , FW_, Fwd_, or RE: prefix
- Date metadata is inside the .msg file only

### 2.4 Thunderbird / IMAP export

```
YYYY-MM-DD HH-MM-SS - Subject text.eml
```

Characteristics:
- Datetime uses hyphens as separators (colons illegal on Windows)
- Dash separator before subject
- Extension .eml

### 2.5 Hash / attachment dumps

```
3a7f2b91e045cd882f1a0b5d6e3c7f2a.pdf
attachment_00001.pdf
```

Detection:
```python
re.match(r'^[0-9a-f]{20,}\.\w+$', fname, re.I)   # hex hash
re.match(r'^attachment_\d+\.\w+$', fname, re.I)   # attachment_N
```

---

## 3. The Universal Parse Algorithm

The parse_filename() function in classify_template.py handles all formats above:

```python
def parse_filename(filename):
    base, ext = os.path.splitext(filename)
    sender = recipient = date_str = ''

    # Step 1: Extract [sender] if present
    m = re.match(r'^\[([^\]]+)\]\s*(.*)', base)
    if m:
        sender = m.group(1)
        base = m.group(2)

    # Step 2: Extract optional [recipient]
    m = re.match(r'^\[([^\]]+)\]\s*(.*)', base)
    if m:
        recipient = m.group(1)
        base = m.group(2)

    # Step 3: Extract date (YYYY-MM-DD, with or without THH-MM)
    m = re.match(r'^(\d{4}-\d{2}-\d{2})(?:T\d{2}-\d{2})?\s*(.*)', base)
    if m:
        date_str = m.group(1)
        base = m.group(2)

    # Step 4: Strip Thunderbird separator dash
    base = re.sub(r'^-\s*', '', base)

    # Step 5: Strip Re_/Fwd_ chains
    base = strip_reply_chains(base)

    subject = base.strip(' ._-') or 'ללא נושא'
    return dict(sender=sender, recipient=recipient, date_str=date_str,
                subject=subject, ext=ext)
```

---

## 4. Stripping Re / Fwd Chains

Reply chains can be deeply nested: Re_Fwd_RE_Re_ Actual subject.pdf

Strip iteratively until stable:

```python
def strip_reply_chains(s):
    prev = None
    while prev != s:
        prev = s
        s = re.sub(
            r'^(Re_|RE_|Fwd_|FW_|Re:|Fwd:|RE:|FW:)\s*',
            '', s, flags=re.IGNORECASE
        ).strip()
    return s
```

The loop handles Re_Re_Re_Subject — a single re.sub would only strip the first match.

---

## 5. Building Clean Output Names

Canonical format: YYYY-MM-DD - Subject text.ext

```python
def make_new_name(parsed, max_subject_len=100):
    subject = parsed['subject'][:max_subject_len]
    subject = re.sub(r'[<>:"/\\|?*]', '_', subject)
    subject = re.sub(r'[ _]{2,}', ' ', subject).strip()
    ext = parsed['ext']
    if parsed['date_str']:
        return f"{parsed['date_str']} - {subject}{ext}"
    return f"{subject}{ext}"
```

Length budget:
- Windows max path = 260 chars (without extended prefix)
- Reserve ~140 chars for parent folder path (conservative)
- Max filename = 120 chars → subject <= 100 chars + "YYYY-MM-DD - " (13) + ext (<=7)

---

## 6. Multilingual Subjects

### Hebrew

Hebrew works natively on Windows NTFS with Python 3.6+.
Always add: sys.stdout.reconfigure(encoding='utf-8')

Hebrew abbreviations often use the ASCII " character (e.g., יועמ"ש for legal adviser).
The ASCII double-quote (U+0022) is FORBIDDEN in Windows filenames.
Replace with Hebrew gershayim ״ (U+05F4):

```python
name = name.replace('"', '\u05f4')   # ASCII quote → Hebrew gershayim
```

### Emoji

Emoji in subjects are valid in NTFS filenames and pass through safely.

---

## 7. Edge Cases and Gotchas

### 7.1 Subject is only Re_Fwd_ prefixes

After stripping all chains, base may be empty.
Fall back: subject = base.strip(' ._-') or 'ללא נושא'

### 7.2 Multiple emails with identical subject and date

unique_dst() handles this by appending (2), (3), etc.

### 7.3 Subject contains path separators

The / becomes _ via the forbidden-char replacement in make_new_name().

### 7.4 Very long original filenames

Some exporters produce filenames > 200 chars. See windows-notes.md for the
\\?\  extended prefix technique to handle these.

### 7.5 Encoding issues in older exports

Some pre-2010 exporters wrote filenames in Windows-1255 (Hebrew legacy encoding).
If you see garbled names, move to the manual-review folder.

### 7.6 Undeliverable / NDR messages

Recognise by: Undeliverable_ prefix, Delivery Status Notification, NDR_ prefix,
Mailer-Daemon sender, Hebrew: הודעה שלא נמסרה, כשל במשלוח
