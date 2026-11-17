#!/usr/bin/env bash
# macOS hot folder: drop photos into a folder -> printed on the RX1HS via the Pi.
# Usage: ./hotfolder.sh [folder] [pi-host] [layout]
#   folder  default ~/Desktop/hotfolder
#   pi-host default orangepi.local
#   layout  4x6 (default) or strip
# Needs the Pi's rx1print service. Set RX1_TOKEN in the environment if you enabled one.
set -u
DIR="${1:-$HOME/Desktop/hotfolder}"
PI="${2:-orangepi.local}"
LAYOUT="${3:-4x6}"
mkdir -p "$DIR/done" "$DIR/failed"
echo "Watching $DIR -> http://$PI:8080 ($LAYOUT). Ctrl+C to stop."

auth=()
[ -n "${RX1_TOKEN:-}" ] && auth=(-H "Authorization: Bearer $RX1_TOKEN")

while true; do
  for f in "$DIR"/*.{jpg,jpeg,png,JPG,JPEG,PNG}; do
    [ -f "$f" ] || continue
    # skip files still being copied (size changed in the last second)
    s1=$(stat -f %z "$f"); sleep 1; s2=$(stat -f %z "$f"); [ "$s1" = "$s2" ] || continue
    if curl -fsS "${auth[@]}" --data-binary @"$f" \
         "http://$PI:8080/print?layout=$LAYOUT" >/dev/null; then
      mv "$f" "$DIR/done/"; echo "printed: $(basename "$f")"
    else
      mv "$f" "$DIR/failed/"; echo "FAILED:  $(basename "$f")"
    fi
  done
  sleep 2
done
