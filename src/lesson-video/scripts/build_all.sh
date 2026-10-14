#!/usr/bin/env bash
# Regenerate every composition from words.json + specs/*.py, then density check and lint.
# Video renders WITHOUT audio (mux.sh adds it) - the HyperFrames audio mix timed out on long lessons.
set -e
cd "$(dirname "$0")"
export PYTHONIOENCODING=utf-8
python write_specs.py
python clean_words.py
python make_chapters.py
python make_index.py --no-audio
python beats.py
python density_check.py || { echo "density check failed - add beats/reveals/shots at the listed gaps"; exit 1; }
cd ../clip && npx --yes hyperframes@0.8.106 lint 2>&1 | tail -1
