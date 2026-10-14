#!/usr/bin/env bash
# Add the normalized audio to the silent render and save the deliverable in the lesson folder.
# Usage: bash mux.sh            -> "<title> - סרטון השיעור.mp4"
#        bash mux.sh --reel <n> -> "<title> - רילס <n>.mp4"
set -e
cd "$(dirname "$0")"
TITLE=$(PYTHONIOENCODING=utf-8 python -c "import json;print(json.load(open('video.json',encoding='utf-8'))['title'])")
if [ "$1" = "--reel" ]; then
  VIDEO="reels/$2/renders/video.mp4"; AUDIO="reels/$2/reel.m4a"; OUT="../../$TITLE - רילס $2.mp4"
else
  VIDEO="../clip/renders/video.mp4"; AUDIO="../clip/assets/audio/lesson.m4a"; OUT="../../$TITLE - סרטון השיעור.mp4"
fi
ffmpeg -y -v error -i "$VIDEO" -i "$AUDIO" -map 0:v -map 1:a -c:v copy -c:a aac -b:a 160k -shortest -movflags +faststart "$OUT"
ffprobe -v error -show_entries format=duration:stream=codec_type,width,height -of compact "$OUT"
