#!/bin/sh
# nflverse injury reports (2009+), weekly player stats, weekly rosters, snap counts, schedules.
# Saved to data/, which is gitignored.
set -e
mkdir -p data
B=https://github.com/nflverse/nflverse-data/releases/download
curl -sSLf -o data/games.csv "$B/schedules/games.csv"
for y in $(seq 2009 2025); do
  curl -sSLf -o data/injuries_$y.csv "$B/injuries/injuries_$y.csv"
  curl -sSLf -o data/stats_player_week_$y.csv "$B/stats_player/stats_player_week_$y.csv"
  curl -sSLf -o data/roster_weekly_$y.csv "$B/weekly_rosters/roster_weekly_$y.csv"
done
for y in $(seq 2013 2025); do curl -sSLf -o data/snap_counts_$y.csv "$B/snap_counts/snap_counts_$y.csv"; done
