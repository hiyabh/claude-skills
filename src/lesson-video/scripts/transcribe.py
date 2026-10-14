"""Word-level Hebrew transcription of the normalized lesson audio (ivrit-ai turbo, local CPU, ~2x realtime).
Run in the background: python -u transcribe.py > transcribe.log 2>&1"""
import json
import sys
import time
from pathlib import Path

from faster_whisper import WhisperModel

from config import AUDIO

OUT = Path(__file__).resolve().parent / "words.json"
MODEL = "ivrit-ai/whisper-large-v3-turbo-ct2"
THREADS = 12


def main():
    model = WhisperModel(MODEL, device="cpu", compute_type="int8", cpu_threads=THREADS)
    t0 = time.time()
    segments, info = model.transcribe(
        str(AUDIO), language="he", word_timestamps=True, vad_filter=True, beam_size=5
    )
    out = []
    for seg in segments:
        words = [{"w": w.word.strip(), "s": round(w.start, 2), "e": round(w.end, 2)} for w in seg.words]
        out.append({"s": round(seg.start, 2), "e": round(seg.end, 2), "text": seg.text.strip(), "words": words})
        print(f"[{seg.start:7.1f}/{info.duration:.0f}] {seg.text.strip()[:70]}", flush=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"DONE {len(out)} segments in {time.time() - t0:.0f}s -> {OUT}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
