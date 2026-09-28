"""Pick the music, find its beat grid, write assets/music/beats.json.

    python beat_grid.py <project> --track sneaky
    python beat_grid.py <project> --track "C:/path/song.mp3"
    python beat_grid.py <project> --track https://.../song.mp3 --credit "..."

The film is cut on this grid. Every shot in shots.json is a whole number of
beats, so a new track re-times the whole film without touching the edit spec.

The bed starts on a beat inside the track's strongest section - starting at
0:00 opens the film on an intro that has not arrived anywhere yet. The pulse is
read off an audition cut made with the *same* filters as the final bed
(build_composition.py cuts that one to the film's exact length), because
loudnorm and the fade shift onset strength slightly and the grid has to match
the audio the viewer hears.
"""

import os
import subprocess
import sys

import librosa
import numpy as np

from pm_common import download, flag, project_arg, write_json

# Kevin MacLeod, incompetech.com, CC BY 4.0 - attribution required, and
# build_composition.py puts it on the closing card. URLs verified 2026-09-28.
INCOMPETECH = "https://incompetech.com/music/royalty-free/mp3-royaltyfree/"
TRACKS = {
    "sneaky": ("Sneaky Snitch", "Sneaky%20Snitch.mp3"),
    "investigations": ("Investigations", "Investigations.mp3"),
    "riley": ("Life of Riley", "Life%20of%20Riley.mp3"),
    "duck": ("Fluffing a Duck", "Fluffing%20a%20Duck.mp3"),
    "carefree": ("Carefree", "Carefree.mp3"),
    "monkeys": ("Monkeys Spinning Monkeys", "Monkeys%20Spinning%20Monkeys.mp3"),
}
LICENSE = "Kevin MacLeod (incompetech.com) - Licensed under CC BY 4.0"

SR = 22050
AUDITION_S = 90.0        # long enough for any film this skill makes
STRONG_WINDOW_S = 30.0   # how much track to weigh when finding the strong part
FADE_IN_S = 0.4
TAIL_FADE_S = 1.6
BPM_COMFORT = (78, 135)  # outside this, cutting on every beat fights the picture
HALF_TIME_ABOVE = 135    # above this, the grid uses every second beat
ENVELOPE_BINS = 160      # bars in the making-of waveform


def resolve_track(project):
    """(local path, display name, credit line) for --track."""
    choice = flag("track", "sneaky")
    if choice in TRACKS:
        name, file = TRACKS[choice]
        dest = os.path.join(project, "assets", "music", "src", file.replace("%20", "_"))
        return download(INCOMPETECH + file, dest), name, f'"{name}" - {LICENSE}'
    if str(choice).startswith("http"):
        dest = os.path.join(project, "assets", "music", "src", "track.mp3")
        return download(choice, dest), flag("name", "track"), flag("credit", "")
    if not os.path.exists(choice):
        sys.exit(f"--track {choice}: not a file, URL, or one of {sorted(TRACKS)}")
    name = flag("name", os.path.splitext(os.path.basename(choice))[0])
    return choice, name, flag("credit", "")


def strongest_start(y, sr):
    """Beat-aligned start of the loudest STRONG_WINDOW_S stretch."""
    rms = librosa.feature.rms(y=y)[0]
    hop_s = 512 / sr
    win = max(1, int(STRONG_WINDOW_S / hop_s))
    start = 0.0
    if len(rms) > win:
        cum = np.concatenate([[0.0], np.cumsum(rms)])
        start = float(np.argmax((cum[win:] - cum[:-win]) / win) * hop_s)
    onset = librosa.onset.onset_strength(y=y, sr=sr)
    _, beats = librosa.beat.beat_track(onset_envelope=onset, sr=sr, units="time")
    if len(beats):
        start = float(beats[np.argmin(np.abs(beats - start))])
    room = max(0.0, librosa.get_duration(y=y, sr=sr) - AUDITION_S)
    return max(0.0, min(start, room))


def cut_bed(src, start, seconds, dest):
    """`seconds` of src from `start`, faded and loudness-normalised.
    AAC for the film; PCM when dest is .wav (librosa reads WAV natively -
    an .m4a sends it through the deprecated audioread fallback)."""
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    fade_at = max(0.0, seconds - TAIL_FADE_S)
    codec = (["-c:a", "pcm_s16le", "-ar", "44100"] if dest.endswith(".wav")
             else ["-c:a", "aac", "-b:a", "192k"])
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-ss", f"{start:.3f}", "-t", f"{seconds:.4f}",
         "-i", src, "-af",
         f"afade=t=in:st=0:d={FADE_IN_S},afade=t=out:st={fade_at:.4f}:d={TAIL_FADE_S},"
         "loudnorm=I=-15:TP=-1.5:LRA=11", *codec, dest],
        check=True, capture_output=True)


def pulse(bed):
    """(period, phase, raw bpm) of the bed. The grid is a regular ruler anchored
    on the first detected beat - beat_track drops beats in quiet bars."""
    y, sr = librosa.load(bed, sr=SR, mono=True)
    onset = librosa.onset.onset_strength(y=y, sr=sr)
    tempo, beats = librosa.beat.beat_track(onset_envelope=onset, sr=sr, units="time")
    bpm = float(np.atleast_1d(tempo)[0])
    period = 60.0 / bpm
    if bpm > HALF_TIME_ABOVE:
        period *= 2
    phase = float(beats[0]) % period if len(beats) else 0.0
    return period, phase, bpm


def envelope(bed):
    """ENVELOPE_BINS loudness values in 0..1, for the making-of waveform."""
    y, _ = librosa.load(bed, sr=SR, mono=True)
    chunks = np.array_split(np.abs(y), ENVELOPE_BINS)
    rms = np.array([float(np.sqrt(np.mean(c ** 2))) if len(c) else 0.0 for c in chunks])
    return [round(float(v), 3) for v in rms / (rms.max() or 1.0)]


def main():
    project = project_arg()
    src, name, credit = resolve_track(project)
    y, sr = librosa.load(src, sr=SR, mono=True)
    start = strongest_start(y, sr)
    audition = os.path.join(project, "assets", "music", "audition.wav")
    cut_bed(src, start, AUDITION_S, audition)
    period, phase, bpm = pulse(audition)
    data = {"source": os.path.abspath(src), "name": name, "credit": credit,
            "start": round(start, 4), "bpm": round(bpm, 2),
            "period": round(period, 5), "phase": round(phase, 5),
            "envelope": envelope(audition)}
    write_json(os.path.join(project, "assets", "music", "beats.json"), data)
    shown = 60 / period
    print(f"{name} - {bpm:.1f} BPM (grid {shown:.1f}/min, {period:.3f}s a beat), "
          f"bed from {start:.1f}s")
    if not BPM_COMFORT[0] <= shown <= BPM_COMFORT[1]:
        print(f"  warning: grid {shown:.0f}/min is outside {BPM_COMFORT} - "
              f"consider another track")


if __name__ == "__main__":
    main()
