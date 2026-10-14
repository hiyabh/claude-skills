#!/usr/bin/env bash
# Render the silent video (~1.2x the lesson length on 16 cores). Usage: bash render.sh [--reel <name>]
# Never pipe a long render through `head` - SIGPIPE kills it. Output goes to a log.
set -e
cd "$(dirname "$0")"
if [ "$1" = "--reel" ]; then DIR="reels/$2"; else DIR="../clip"; fi
cd "$DIR"
npx --yes hyperframes@0.8.106 render -o renders/video.mp4 --fps 30 --crf 21 > render.log 2>&1
tail -2 render.log
