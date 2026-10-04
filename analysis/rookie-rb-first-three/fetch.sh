#!/bin/sh
# nflverse weekly player stats (1999-present), player table, draft picks, snap counts (2013+),
# then slimmed play-by-play for success rate. ~250 MB in data/, which is gitignored.
set -e
mkdir -p data
B=https://github.com/nflverse/nflverse-data/releases/download
curl -sSLf -o data/players.csv "$B/players/players.csv"
curl -sSLf -o data/draft_picks.csv "$B/draft_picks/draft_picks.csv"
for y in $(seq 1999 2026); do curl -sSLf -o data/stats_player_week_$y.csv "$B/stats_player/stats_player_week_$y.csv"; done
for y in $(seq 2013 2026); do curl -sSLf -o data/snap_counts_$y.csv "$B/snap_counts/snap_counts_$y.csv"; done
python3 fetch_pbp.py 1999 2026
