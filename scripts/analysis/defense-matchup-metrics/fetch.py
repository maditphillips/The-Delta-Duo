#!/usr/bin/env python3
"""Download the nflverse tables this study needs.

Play-by-play is ~20 MB a season and we only want ~35 columns of it, so each season
is column-filtered on the way in and cached in .data/pbp_slim/.

    python3 fetch.py                 # writes into .data/ next to this script
    DMM_DATA=/tmp/x python3 fetch.py
"""
import os, sys, io, urllib.request, pandas as pd

REL     = 'https://github.com/nflverse/nflverse-data/releases/download'
HERE    = os.path.dirname(os.path.abspath(__file__))
DATA    = os.environ.get('DMM_DATA', os.path.join(HERE, '.data'))
SEASONS = range(2011, 2027)          # 2011 only feeds "last season" priors for 2012; 2026 is in progress

PBP_COLS = ['game_id', 'season', 'week', 'season_type', 'posteam', 'defteam', 'play_type',
            'pass', 'rush', 'qb_dropback', 'qb_scramble', 'rush_attempt', 'pass_attempt', 'sack',
            'interception', 'complete_pass', 'yards_gained', 'epa', 'success', 'wp', 'qtr',
            'half_seconds_remaining', 'down', 'touchdown', 'pass_touchdown', 'rush_touchdown',
            'air_yards', 'yards_after_catch', 'cpoe', 'xpass', 'qb_hit', 'fumble_lost',
            'rusher_player_id', 'receiver_player_id', 'passer_player_id', 'two_point_attempt',
            'yardline_100', 'score_differential']

STAT_COLS = ['player_id', 'player_display_name', 'position', 'season', 'week', 'season_type',
             'game_id', 'team', 'opponent_team', 'attempts', 'completions', 'passing_yards',
             'passing_tds', 'passing_interceptions', 'carries', 'rushing_yards', 'rushing_tds',
             'targets', 'receptions', 'receiving_yards', 'receiving_tds',
             'fantasy_points', 'fantasy_points_ppr']


def get(url):
    with urllib.request.urlopen(url) as r:
        return io.BytesIO(r.read())


def main():
    os.makedirs(os.path.join(DATA, 'pbp_slim'), exist_ok=True)
    os.makedirs(os.path.join(DATA, 'stats'), exist_ok=True)

    p = os.path.join(DATA, 'schedules.parquet')
    if not os.path.exists(p):
        print('fetch schedules', flush=True)
        pd.read_csv(get(f'{REL}/schedules/games.csv')).to_parquet(p)

    for y in SEASONS:
        cur = (y == max(SEASONS))    # always refresh the in-progress season
        p = os.path.join(DATA, 'pbp_slim', f'{y}.parquet')
        if cur or not os.path.exists(p):
            print('fetch pbp', y, flush=True)
            d = pd.read_parquet(get(f'{REL}/pbp/play_by_play_{y}.parquet'), columns=PBP_COLS)
            d[(d.pass_attempt == 1) | (d.rush_attempt == 1) | (d.qb_dropback == 1)].to_parquet(p)
        p = os.path.join(DATA, 'stats', f'{y}.parquet')
        if cur or not os.path.exists(p):
            print('fetch player stats', y, flush=True)
            pd.read_parquet(get(f'{REL}/stats_player/stats_player_week_{y}.parquet'),
                            columns=STAT_COLS).to_parquet(p)
    print('done ->', DATA)


if __name__ == '__main__':
    sys.exit(main())
