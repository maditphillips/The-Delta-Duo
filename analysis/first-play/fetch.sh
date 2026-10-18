#!/bin/sh
# nflverse play-by-play, 2016-2025 (~200 MB in data/, which is gitignored).
set -e
mkdir -p data
B=https://github.com/nflverse/nflverse-data/releases/download/pbp
for y in $(seq 2016 2025); do curl -sSLf -o data/pbp_$y.parquet "$B/play_by_play_$y.parquet"; done
