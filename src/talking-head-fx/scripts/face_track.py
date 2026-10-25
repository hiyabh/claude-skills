#!/usr/bin/env python3
"""Sample the speaker's face position over time -> face.json for talking-head-fx.

The effects runtime aims every zoom, the face portal and the glass lens at the
face, so it needs where the face is at each moment. Output (normalised 0..1 of
the source frame):

    {"src_w":1920,"src_h":1080,"fps":5,
     "samples":[[t, cx, cy, size], ...],   # size = face height / frame height
     "found": 0.97}                        # share of samples with a real detection

Usage:
    python face_track.py footage.mp4 -o face.json [--rate 5] [--smooth 1.0]
"""
import argparse
import json
import sys

import cv2
import numpy as np

DEFAULT_RATE = 5.0          # samples per second
DEFAULT_SMOOTH_SEC = 1.0    # moving-average window
MIN_FACE_RATIO = 0.06       # smallest face side, as share of frame height
DETECT_SCALE = 1.1
DETECT_NEIGHBORS = 6
DETECT_WIDTH = 960          # detect on a downscaled frame for speed
FALLBACK = (0.5, 0.38, 0.22)  # typical talking-head framing when nothing is found


def load_cascades():
    base = cv2.data.haarcascades
    front = cv2.CascadeClassifier(base + "haarcascade_frontalface_default.xml")
    prof = cv2.CascadeClassifier(base + "haarcascade_profileface.xml")
    return front, prof


def detect(gray, front, prof):
    """Largest face as (cx, cy, h) in pixels of `gray`, or None."""
    min_side = int(gray.shape[0] * MIN_FACE_RATIO)
    kw = dict(scaleFactor=DETECT_SCALE, minNeighbors=DETECT_NEIGHBORS,
              minSize=(min_side, min_side))
    faces = front.detectMultiScale(gray, **kw)
    if len(faces) == 0:
        faces = prof.detectMultiScale(gray, **kw)
    if len(faces) == 0:
        w = gray.shape[1]
        flipped = prof.detectMultiScale(cv2.flip(gray, 1), **kw)
        faces = [(w - (x + fw), y, fw, fh) for (x, y, fw, fh) in flipped]
    if len(faces) == 0:
        return None
    x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
    return x + fw / 2.0, y + fh / 2.0, float(fh)


def scan(path, rate):
    """Return (raw samples [(t, cx, cy, size) | (t, None)], src_w, src_h)."""
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        sys.exit(f"ERROR: cannot open '{path}' - check the path and that it is a video file.")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    step = max(1, int(round(fps / rate)))
    scale = min(1.0, DETECT_WIDTH / src_w)
    front, prof = load_cascades()
    raw, idx = [], 0
    while True:
        ok = cap.grab()
        if not ok:
            break
        if idx % step == 0:
            _, frame = cap.retrieve()
            small = cv2.resize(frame, None, fx=scale, fy=scale)
            hit = detect(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), front, prof)
            t = idx / fps
            if hit is None:
                raw.append((t, None))
            else:
                sw, sh = small.shape[1], small.shape[0]
                raw.append((t, hit[0] / sw, hit[1] / sh, hit[2] / sh))
        idx += 1
    cap.release()
    return raw, src_w, src_h


def fill_and_smooth(raw, rate, smooth_sec):
    """Interpolate missed samples, then moving-average each channel."""
    times = np.array([r[0] for r in raw])
    valid = np.array([r[1] is not None for r in raw])
    out = []
    for ch in range(3):
        vals = np.array([r[ch + 1] if r[1] is not None else np.nan for r in raw])
        if valid.sum() == 0:
            vals[:] = FALLBACK[ch]
        else:
            vals = np.interp(times, times[valid], vals[valid])
        win = max(1, int(round(rate * smooth_sec)))
        win += (win + 1) % 2
        padded = np.pad(vals, win // 2, mode="edge")
        out.append(np.convolve(padded, np.ones(win) / win, mode="valid"))
    found = float(valid.mean()) if len(valid) else 0.0
    return times, out, found


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("-o", "--out", default="face.json")
    ap.add_argument("--rate", type=float, default=DEFAULT_RATE)
    ap.add_argument("--smooth", type=float, default=DEFAULT_SMOOTH_SEC)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # Hebrew output through a pipe on non-Hebrew Windows
    raw, src_w, src_h = scan(a.video, a.rate)
    if not raw:
        sys.exit("ERROR: no frames decoded - the file may be corrupt or use an unsupported codec.")
    times, (cx, cy, size), found = fill_and_smooth(raw, a.rate, a.smooth)
    samples = [[round(float(t), 3), round(float(x), 4), round(float(y), 4), round(float(s), 4)]
               for t, x, y, s in zip(times, cx, cy, size)]
    data = {"src_w": src_w, "src_h": src_h, "fps": a.rate, "samples": samples, "found": round(found, 3)}
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(data, f)
    print(f"face track: {len(samples)} samples, face found in {found:.0%} -> {a.out}")
    if found < 0.5:
        print("WARNING: face found in under half the samples - zooms will aim at the fallback point. "
              "Check the framing, or pass explicit 'focus' params in the plan.")


if __name__ == "__main__":
    main()
