#!/bin/sh
# nflverse inputs: the game schedule (byes + remaining games) and weekly player
# stats (PPR points per player-week). nflreadr::load_schedules() and
# load_player_stats(summary_level = "week") wrap these same files; no R required.
set -e
curl -sSL -o games.csv "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
for y in 2020 2021 2022 2023 2024 2025 2026; do
  curl -sSL -o "w$y.csv" "https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_$y.csv"
done
wc -l games.csv w*.csv
