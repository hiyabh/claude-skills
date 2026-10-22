#!/usr/bin/env bash
# Add the normalized audio to the silent render and save the deliverable in the lesson folder.
# Soft sound effects (build/sfx.json, video.json "sfx": false turns them off) are mixed under the voice.
# After a verified delivery (and after a draft) the heavy render intermediates are deleted.
# Usage: bash mux.sh            -> "<title> - סרטון השיעור.mp4"
#        bash mux.sh --reel <n> -> "<title> - רילס <n>.mp4" (no sound effects)
#        bash mux.sh --draft    -> build/qc/draft.mp4 (preview of render.sh --draft)
set -e
cd "$(dirname "$0")"
export PYTHONIOENCODING=utf-8
TITLE=$(python -c "import json;print(json.load(open('video.json',encoding='utf-8'))['title'])")
KIND=lesson
if [ "$1" = "--reel" ]; then
  KIND=reel; RENDERS="reels/$2/renders"; VIDEO="$RENDERS/video.mp4"; AUDIO="reels/$2/reel.m4a"; OUT="../../$TITLE - רילס $2.mp4"
elif [ "$1" = "--draft" ]; then
  KIND=draft; RENDERS="../clip/renders"; VIDEO="$RENDERS/draft.mp4"; AUDIO="../clip/assets/audio/lesson.m4a"; OUT="qc/draft.mp4"; mkdir -p qc
else
  RENDERS="../clip/renders"; VIDEO="$RENDERS/video.mp4"; AUDIO="../clip/assets/audio/lesson.m4a"; OUT="../../$TITLE - סרטון השיעור.mp4"
fi
FX="$RENDERS/sfx.wav"
if [ "$KIND" != "reel" ] && python sfx_track.py "$AUDIO" "$FX"; then
  ffmpeg -y -v error -i "$VIDEO" -i "$AUDIO" -i "$FX" \
    -filter_complex "[1:a][2:a]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]" \
    -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 160k -shortest -movflags +faststart "$OUT"
else
  ffmpeg -y -v error -i "$VIDEO" -i "$AUDIO" -map 0:v -map 1:a -c:v copy -c:a aac -b:a 160k -shortest -movflags +faststart "$OUT"
fi
ffprobe -v error -show_entries format=duration:stream=codec_type,width,height -of compact "$OUT"
if [ "$KIND" != "draft" ]; then
  DUR_OUT=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT")
  DUR_IN=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$AUDIO")
  HAS_AUDIO=$(ffprobe -v error -select_streams a -show_entries stream=codec_type -of csv=p=0 "$OUT")
  if [ -n "$HAS_AUDIO" ] && awk -v a="$DUR_OUT" -v b="$DUR_IN" 'BEGIN{d=a-b; exit !(d<0.5 && d>-0.5)}'; then
    rm -f "$RENDERS"/*; echo "delivery verified - render intermediates deleted"
  else
    echo "delivery NOT verified (duration $DUR_OUT vs audio $DUR_IN) - intermediates kept"; exit 1
  fi
else
  rm -f "$RENDERS"/*
fi
