#!/bin/sh
# nflverse game log: one row per game, 1999-present, with both head coaches and the score.
# This is what nflreadr::load_schedules() wraps; no R required.
set -e
curl -sSL -o games.csv "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
wc -l games.csv
