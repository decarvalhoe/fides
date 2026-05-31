#!/usr/bin/env bash
# Encode des aperçus écoutables + copie des livrables vers un dossier Windows.
set -uo pipefail
OUT="$HOME/dlz/out/REC_0001"
WIN="/mnt/c/Dev/dlz-data/out/REC_0001"
IN="$HOME/dlz/in/REC_0001.wav"
cd "$OUT"
mkdir -p "$WIN"

q() { ffmpeg -y -loglevel error "$@"; }

# Master : FLAC lossless + MP3 320 (fallback AAC)
q -i master.wav -c:a flac master.flac
q -i master.wav -c:a libmp3lame -b:a 320k master.mp3 || q -i master.wav -c:a aac -b:a 256k master.m4a
# Résidu null-test (ce qui a été ajouté/retiré) + A/B
q -i null_residual.wav -c:a libmp3lame -b:a 192k null_residual.mp3 || true
q -i _pre_master.wav   -c:a libmp3lame -b:a 320k pre_master.mp3 || true
# Original du canal primaire (ch12) pour comparaison A/B
q -i "$IN" -af "pan=mono|c0=c12" -c:a libmp3lame -b:a 320k original_ch12.mp3 || true
[ -f original_match.wav ] && q -i original_match.wav -c:a libmp3lame -b:a 320k original_match.mp3 || true

cp -f master.wav master.flac report.md report.json null_residual.wav "$WIN"/ 2>/dev/null || true
for f in master.mp3 master.m4a null_residual.mp3 pre_master.mp3 original_ch12.mp3 original_match.mp3 report.html; do
  [ -f "$f" ] && cp -f "$f" "$WIN"/ 2>/dev/null || true
done
echo "--- contenu livré ---"
ls -la "$WIN"
echo DELIVER_OK
