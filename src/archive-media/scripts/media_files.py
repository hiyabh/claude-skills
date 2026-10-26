"""Pick the best playable file of an archive.org item, and probe/extract with ffmpeg."""
import hashlib
import json
import os
import shutil
import subprocess
import urllib.request

from ia_api import TIMEOUT_S, USER_AGENT, download_url

CHUNK_BYTES = 1 << 20
CACHE_KEY_LEN = 16

# Higher = better for seeking and quality at the same resolution.
VIDEO_FORMAT_PRIORITY = {"h.264": 6, "h.264 hd": 7, "mpeg4": 5, "hires mpeg4": 5, "mpeg2": 4,
                         "512kb mpeg4": 2, "ogg video": 1, "cinepack": 0}
VIDEO_EXTS = (".mp4", ".m4v", ".mov", ".mkv", ".mpeg", ".mpg", ".ogv", ".avi")
# MP3 by default: a 78's own bandwidth is narrow, and the MP3 is ~12x smaller than the 24-bit FLAC.
AUDIO_PRIORITY_FAST = {"vbr mp3": 5, "mp3": 5, "flac": 3, "24bit flac": 3, "ogg vorbis": 2}
AUDIO_PRIORITY_LOSSLESS = {"flac": 5, "24bit flac": 5, "vbr mp3": 3, "mp3": 3, "ogg vorbis": 2}
AUDIO_EXTS = (".flac", ".mp3", ".ogg", ".wav")
FONT_CANDIDATES = ("C:/Windows/Fonts/arial.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf",
                   "/Library/Fonts/Arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _length_s(f):
    raw = str(f.get("length") or "")
    if ":" in raw:
        secs = 0.0
        for part in raw.split(":"):
            secs = secs * 60 + _num(part)
        return secs
    return _num(raw)


def best_video(files):
    """Highest-resolution video derivative, ties broken by codec friendliness."""
    vids = [f for f in files if f["name"].lower().endswith(VIDEO_EXTS)]
    if not vids:
        return None
    return max(vids, key=lambda f: (_num(f.get("height")),
                                    VIDEO_FORMAT_PRIORITY.get(str(f.get("format", "")).lower(), 3),
                                    -_num(f.get("size"))))


def audio_tracks(files, lossless=False):
    """One file per track (MP3 by default, FLAC when lossless), keyed by base name, in item order."""
    priority = AUDIO_PRIORITY_LOSSLESS if lossless else AUDIO_PRIORITY_FAST
    best = {}
    for f in files:
        if not f["name"].lower().endswith(AUDIO_EXTS) or "_sample" in f["name"].lower():
            continue
        base = os.path.splitext(f["name"])[0]
        prio = priority.get(str(f.get("format", "")).lower(), 1)
        if base not in best or prio > best[base][0]:
            best[base] = (prio, f)
    return [f for _, f in best.values()]


def describe(identifier, f):
    return {"name": f["name"], "url": download_url(identifier, f["name"]),
            "format": f.get("format"), "length_s": round(_length_s(f), 2),
            "width": int(_num(f.get("width"))) or None, "height": int(_num(f.get("height"))) or None,
            "size_mb": round(_num(f.get("size")) / 1e6, 1)}


def cache_path(out_dir, identifier, filename):
    """Short hashed name: 78rpm identifiers alone run ~90 chars, which breaks Windows' 260-char path limit."""
    key = hashlib.sha1(f"{identifier}/{filename}".encode("utf-8")).hexdigest()[:CACHE_KEY_LEN]
    return os.path.join(out_dir, ".ia-cache", key + os.path.splitext(filename)[1].lower())


def download(url, path):
    """Stream a file to disk once (skips if already complete); returns the path."""
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    tmp = f"{path}.{os.getpid()}.part"
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp, open(tmp, "wb") as fh:
        shutil.copyfileobj(resp, fh, CHUNK_BYTES)
    os.replace(tmp, path)
    return path


def require_ffmpeg():
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            raise SystemExit(f"{tool} not found on PATH. Install ffmpeg (Windows: winget install Gyan.FFmpeg), then retry.")


def run_ffmpeg(args, timeout=600):
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg failed ({res.returncode}): {' '.join(cmd[:12])} ...\n{res.stderr[-1500:]}")


def probe(path):
    """(stream types present, duration seconds) - ffmpeg can exit 0 yet write an empty file."""
    res = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type:format=duration",
                          "-of", "json", path], capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        data = json.loads(res.stdout or "{}")
    except json.JSONDecodeError:
        return set(), 0.0
    kinds = {s.get("codec_type") for s in data.get("streams", [])}
    return kinds, _num(data.get("format", {}).get("duration"))


def label_font():
    """A TTF path escaped for ffmpeg drawtext, or None (labels are then skipped)."""
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return path.replace(":", "\\:")
    return None
