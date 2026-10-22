# -*- coding: utf-8 -*-
"""Soft sound effects, synthesized locally (numpy, no samples, no licences) and mixed under the narration.

Renderers call ev(kind, t) with chapter-local times while a chapter is built; beats.py shifts them to
lesson time and writes build/sfx.json. render_video mixes build_track() under the voice.
Kinds: whoosh (beat change), click (a button is pressed), pop (a result appears), chime (title, closing, link card)."""
import json
import math
import wave
from pathlib import Path

import numpy as np

RATE = 48000
EVENTS = []
PEAK = 0.16                 # final mix peak, far under the voice
LEVEL = {"whoosh": 0.35, "click": 0.5, "pop": 0.55, "chime": 0.4}
MIN_GAP = 0.35              # the same kind closer than this is dropped (no machine-gun pops)


def ev(kind, t):
    EVENTS.append({"k": kind, "t": round(float(t), 3)})


def _env(n, attack, release):
    a, r = max(1, int(attack * RATE)), max(1, int(release * RATE))
    e = np.ones(n)
    e[:a] = np.linspace(0, 1, a)
    e[-r:] *= np.exp(-np.linspace(0, 6, r))
    return e


def _noise(n, seed):
    return np.random.default_rng(seed).standard_normal(n)


def _whoosh():
    n = int(0.5 * RATE)
    x = _noise(n, 1)
    # one-pole low-pass whose cutoff sweeps up then down: the "air" moving past
    cut = np.sin(np.linspace(0, math.pi, n)) * 0.18 + 0.02
    y, prev = np.empty(n), 0.0
    for i in range(n):
        prev += cut[i] * (x[i] - prev)
        y[i] = prev
    return y * np.sin(np.linspace(0, math.pi, n)) ** 2


def _tick():
    n = int(0.012 * RATE)
    x = np.diff(_noise(n, 7), prepend=0)          # crude high-pass: a dry key click
    return x * np.exp(-np.linspace(0, 9, n))


def _click():
    n = int(0.03 * RATE)
    t = np.arange(n) / RATE
    x = np.sin(2 * math.pi * 1800 * t) * np.exp(-t * 180)
    tick = _tick()
    x[:len(tick)] += tick * 0.4
    return x


def _pop():
    n = int(0.12 * RATE)
    t = np.arange(n) / RATE
    f = 760 * np.exp(-t * 14) + 260                # pitch drops: a bubble pop
    return np.sin(2 * math.pi * np.cumsum(f) / RATE) * _env(n, 0.003, 0.1)


def _chime():
    n = int(1.1 * RATE)
    t = np.arange(n) / RATE
    tone = sum(a * np.sin(2 * math.pi * f * t) for f, a in ((1046.5, 1.0), (1568.0, 0.45), (2093.0, 0.2)))
    return tone * np.exp(-t * 4.2) * _env(n, 0.004, 0.05)


SOUNDS = {"whoosh": _whoosh, "click": _click, "pop": _pop, "chime": _chime}


def _norm(x):
    m = np.max(np.abs(x))
    return x / m if m else x


def _thin(events):
    out, last = [], {}
    for e in sorted(events, key=lambda e: e["t"]):
        if e["t"] - last.get(e["k"], -9) < MIN_GAP:
            continue
        last[e["k"]] = e["t"]
        out.append(e)
    return out


def build_track(events, total, path):
    """Mix all events into one mono WAV of `total` seconds at path."""
    track = np.zeros(int((total + 1.5) * RATE))
    cache = {}
    for e in _thin(events):
        if e["k"] not in cache:
            cache[e["k"]] = _norm(SOUNDS[e["k"]]()) * LEVEL[e["k"]]
        snd = cache[e["k"]]
        i = int(max(0.0, e["t"]) * RATE)
        seg = track[i:i + len(snd)]
        seg += snd[:len(seg)]
    track = _norm(track[:int(total * RATE)]) * PEAK
    pcm = (track * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.tobytes())
    return path


def save(path):
    Path(path).write_text(json.dumps(EVENTS, ensure_ascii=False), encoding="utf-8")
