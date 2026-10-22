#!/usr/bin/env bash
# Render the silent video (~1.2x the lesson length on 16 cores).
# Usage: bash render.sh [--reel <name>] [--draft]
#   --draft  fast low-quality preview (15 fps, draft quality) for checking fixes; mux it with `mux.sh --draft`
# Never pipe a long render through `head` - SIGPIPE kills it. Output goes to a log.
set -e
cd "$(dirname "$0")"
DIR="../clip"; OUT="renders/video.mp4"; OPTS="--fps 30 --crf 21"
while [ $# -gt 0 ]; do
  case "$1" in
    --reel) DIR="reels/$2"; shift ;;
    --draft) OUT="renders/draft.mp4"; OPTS="--fps 15 --quality draft" ;;
  esac
  shift
done
cd "$DIR"
npx --yes hyperframes@0.8.106 render -o "$OUT" $OPTS > render.log 2>&1
tail -2 render.log
