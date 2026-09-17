#!/usr/bin/env bash
# Install the two faces the boards use, so a headless export matches the page.
# Both are SIL Open Font License; sources are the Google Fonts repository.
set -euo pipefail
DEST=${FONT_DIR:-/usr/share/fonts/truetype/delta-duo}
mkdir -p "$DEST"
curl -sSL --retry 4 --retry-delay 2 -o "$DEST/Inter.ttf" \
  "https://raw.githubusercontent.com/google/fonts/main/ofl/inter/Inter%5Bopsz,wght%5D.ttf"
curl -sSL --retry 4 --retry-delay 2 -o "$DEST/Righteous-Regular.ttf" \
  "https://raw.githubusercontent.com/google/fonts/main/ofl/righteous/Righteous-Regular.ttf"
fc-cache -f >/dev/null
fc-list | grep -Ei "inter|righteous" | head -3
