#!/usr/bin/env python3
"""Download the nflverse tables this study needs and reduce play-by-play as we go.

Play-by-play is ~20 MB a season and we only want four slices of it, so each season
file is downloaded, filtered, and deleted before the next one starts.

    python3 fetch.py            # writes into .data/ next to this script
    RB_ACL_DATA=/tmp/x python3 fetch.py
"""
import os, sys, io, urllib.request, pandas as pd

REL   = 'https://github.com/nflverse/nflverse-data/releases/download'
HERE  = os.path.dirname(os.path.abspath(__file__))
DATA  = os.environ.get('RB_ACL_DATA', os.path.join(HERE, '.data'))
SEASONS = range(1999, 2026)

PBP_COLS = ['game_id','season','week','season_type','game_date','posteam','play_type',
            'rush_attempt','pass_attempt','complete_pass','rusher_player_id','receiver_player_id',
            'yards_gained','epa','success','touchdown','first_down','down','ydstogo',
            'yardline_100','two_point_attempt','home_team','away_team']


def get(url):
    with urllib.request.urlopen(url) as r:
        return io.BytesIO(r.read())


def main():
    os.makedirs(DATA, exist_ok=True)

    for name, url in [('players.parquet',     f'{REL}/players/players.parquet'),
                      ('ngs_rushing.parquet', f'{REL}/nextgen_stats/ngs_rushing.parquet')]:
        p = os.path.join(DATA, name)
        if not os.path.exists(p):
            print('fetch', name, flush=True)
            pd.read_parquet(get(url)).to_parquet(p)

    # snap counts (2012+)
    for sub, tag, fmt, yrs in [('snaps', 'snap_counts', 'snap_counts_{}', range(2012, 2026))]:
        os.makedirs(os.path.join(DATA, sub), exist_ok=True)
        for y in yrs:
            p = os.path.join(DATA, sub, f'{y}.parquet')
            if os.path.exists(p):
                continue
            print('fetch', sub, y, flush=True)
            d = pd.read_parquet(get(f'{REL}/{tag}/{fmt.format(y)}.parquet'))
            for c in ('draft_number','years_exp','entry_year','height','weight'):
                if c in d: d[c] = pd.to_numeric(d[c], errors='coerce')
            d.to_parquet(p)

    # play-by-play, one season at a time, keeping only games / rushes / targets
    games, rush, targ = [], [], []
    for y in SEASONS:
        cache = os.path.join(DATA, 'pbp_slim', f'{y}.parquet')
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        if os.path.exists(cache):
            d = pd.read_parquet(cache)
        else:
            print('fetch pbp', y, flush=True)
            d = pd.read_parquet(get(f'{REL}/pbp/play_by_play_{y}.parquet'), columns=PBP_COLS)
            d = d[(d.rush_attempt == 1) | (d.pass_attempt == 1) | d.game_id.notna()]
            d.to_parquet(cache)

        games.append(d.groupby('game_id', as_index=False).agg(
            season=('season','first'), week=('week','first'), season_type=('season_type','first'),
            game_date=('game_date','first'), home_team=('home_team','first'), away_team=('away_team','first')))
        r = d[(d.rush_attempt == 1) & (d.two_point_attempt != 1) & d.rusher_player_id.notna()]
        rush.append(r[['game_id','season','week','season_type','posteam','rusher_player_id',
                       'yards_gained','epa','success','touchdown','first_down','down','ydstogo','yardline_100']])
        c = d[(d.pass_attempt == 1) & (d.two_point_attempt != 1) & d.receiver_player_id.notna()]
        targ.append(c[['game_id','season','week','season_type','posteam','receiver_player_id',
                       'complete_pass','yards_gained','epa','success','touchdown','first_down']])

    pd.concat(games, ignore_index=True).to_parquet(os.path.join(DATA, 'games.parquet'))
    pd.concat(rush,  ignore_index=True).to_parquet(os.path.join(DATA, 'rush_plays.parquet'))
    pd.concat(targ,  ignore_index=True).to_parquet(os.path.join(DATA, 'target_plays.parquet'))
    print('done ->', DATA)


if __name__ == '__main__':
    sys.exit(main())
