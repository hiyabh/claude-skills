# Windows-Specific Notes for Archive Operations

Read this when you hit Windows-specific errors: long paths, encoding issues,
forbidden characters, slow script execution, or other platform surprises.

---

## Table of Contents

1. The 260-character path limit
2. Forbidden filename characters
3. Python launcher: py vs python
4. stdout encoding
5. os.listdir vs os.walk on long paths
6. Hebrew and RTL filenames
7. shutil.move vs os.rename
8. Permissions and locked files
9. Junction points and symlinks

---

## 1. The 260-Character Path Limit

### The problem

Windows refuses to open, move, rename, or stat any path whose total length
exceeds 260 characters (MAX_PATH).

Symptoms:
- FileNotFoundError: [WinError 3] The system cannot find the path specified
- os.path.isfile(long_path) returns False even though the file exists
- shutil.move() silently fails or raises WinError 3

### Diagnosis

```python
for dirpath, dirs, files in os.walk(ROOT):
    for fname in files:
        full = os.path.join(dirpath, fname)
        if len(full) > 255:
            print(len(full), full[:120])
```

### Solution A — Enable LongPathsEnabled (Windows 10 1607+)

gpedit.msc → Local Computer Policy → Computer Configuration →
Administrative Templates → System → Filesystem → Enable Win32 long paths

### Solution B — Extended path prefix

Prefix every path with \\?\ (backslash backslash question-mark backslash).
In Python: '\\\\?\\'

```python
PFX = '\\\\?\\'   # == \\?\ in actual string

os.rename(PFX + long_src, PFX + long_dst)
os.stat(PFX + long_path)
```

shutil.move() does NOT accept the \\?\ prefix. Use two-step rename-then-move:

```python
def move_long_path(src_dir, fname, dst_dir):
    full_src  = os.path.join(src_dir, fname)
    short_tmp = 'tmp_short_' + os.path.splitext(fname)[1]

    # Step 1: rename to short name within same folder
    os.rename(PFX + full_src, PFX + os.path.join(src_dir, short_tmp))

    # Step 2: path is now short enough — move normally
    shutil.move(os.path.join(src_dir, short_tmp), dst_dir)
```

Use a unique short_tmp if processing multiple files in the same folder:
```python
import uuid
short_tmp = f'_tmp_{uuid.uuid4().hex[:8]}{ext}'
```

---

## 2. Forbidden Filename Characters

Windows forbids: < > : " / \ | ? *  (and NUL)

Most common gotcha: the quote character "

Hebrew abbreviations often use " (e.g., יועמ"ש for legal adviser).
This is the ASCII double-quote (U+0022), which is FORBIDDEN in Windows filenames.

Fix: Replace with Hebrew Gershayim ״ (U+05F4) — looks identical in most fonts.

```python
def safe_windows_name(s):
    s = s.replace('"', '\u05f4')         # ASCII quote → Hebrew gershayim
    s = re.sub(r'[<>:/\\|?*]', '_', s)  # other forbidden → underscore
    s = s.strip('. ')                      # no leading/trailing dots or spaces
    return s
```

Reserved device names (rare but real): CON, PRN, AUX, NUL, COM1-COM9, LPT1-LPT9.
Rename to e.g. _CON if encountered.

---

## 3. Python Launcher: py vs python

Use py (the Python Launcher) rather than python on Windows:

    py script.py               # uses the default installed Python version
    py -3.11 script.py         # force a specific version

The py launcher is installed with the official python.org installer and correctly
handles the #!/usr/bin/env python3 shebang line.

---

## 4. stdout Encoding

Windows terminals default to code page 1252 (Western European). Add this at the
top of every script that prints Hebrew or non-ASCII text:

```python
import sys
sys.stdout.reconfigure(encoding='utf-8')
```

If output is still garbled in PowerShell:
    chcp 65001     # switch console to UTF-8 code page

---

## 5. os.listdir vs os.walk on Long Paths

THE SILENT FAILURE:

```python
# WRONG — silently misses files with paths > 260 chars
files = [f for f in os.listdir(folder)
         if os.path.isfile(os.path.join(folder, f))]
```

os.path.isfile() calls GetFileAttributes on the full path. If that path is > 260 chars,
it returns False — the file appears to not exist.

THE CORRECT APPROACH:

```python
# CORRECT — os.walk enumerates without calling isfile on full paths
for dirpath, dirs, files in os.walk(folder):
    dirs[:] = [d for d in dirs if not d.startswith('.')]
    for fname in files:
        full = os.path.join(dirpath, fname)
        # Apply \\?\ prefix before any file operations on long paths
```

---

## 6. Hebrew and RTL Filenames

Python 3.6+ handles Unicode filenames natively through the NTFS API.
No special encoding tricks are needed for Hebrew filenames.

Numbered prefixes like "1. ניהול עמותה" sort correctly in Windows Explorer
regardless of RTL. Always use 1., 2., ... prefixes.

---

## 7. shutil.move vs os.rename

| Operation | When to use |
|-----------|-------------|
| shutil.move(src, dst) | Moving across drives, copy+delete semantics |
| os.rename(src, dst) | Same drive — atomic, no copy, much faster |

For large archives on a single drive, os.rename is instantaneous.
For the long-path two-step rename: use os.rename with \\?\ for step 1,
then shutil.move for step 2.

---

## 8. Permissions and Locked Files

Files open in Word/Outlook raise:
    PermissionError: [WinError 32] The process cannot access the file because
    it is being used by another process

Always wrap moves in try/except:
```python
try:
    shutil.move(src, dst)
except Exception as e:
    log(f'[ERR] {src}: {e}')
```

For read-only files, clear the flag first:
```python
import stat
os.chmod(src, stat.S_IWRITE)
shutil.move(src, dst)
```

OneDrive / cloud-synced folders: ensure files are fully downloaded locally
before running classification (online-only placeholders trigger slow downloads).

---

## 9. Junction Points and Symlinks

os.walk() follows directory junctions by default. To prevent scanning outside
the archive root:
```python
for dirpath, dirs, files in os.walk(ROOT, followlinks=False):
    pass  # followlinks=False is the default, explicit here for clarity
```

Check for junctions before running:
    dir /AL /S C:\path\to\archive
