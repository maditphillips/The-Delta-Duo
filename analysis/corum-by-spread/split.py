"""Corum vs Kyren Williams carries and RB carry share by Rams spread, per season + total.

Usage: python3 split.py DATA_DIR  (same files as workload.py)  ->  writes corum_kyren_split.csv
Every season both were on the Rams (2024-present). Kneel-downs excluded, playoffs included.
Games where Corum was inactive are left out, so each row compares the two in the same games.
"""
import sys
import numpy as np
import pandas as pd

d = sys.argv[1]
SEASONS = range(2024, 2027)
g = pd.read_csv(f'{d}/games.csv')
g = g[g.season.isin(SEASONS) & g.result.notna() & ((g.home_team == 'LA') | (g.away_team == 'LA'))]
g = g.assign(fav_by=np.where(g.home_team == 'LA', g.spread_line, -g.spread_line))
p = pd.concat([pd.read_csv(f'{d}/pbp_{y}.csv.gz', low_memory=False,
                           usecols=['game_id', 'posteam', 'play_type', 'rusher_player_name',
                                    'rusher_player_id', 'qb_kneel'])
               for y in SEASONS])
run = p[(p.posteam == 'LA') & (p.play_type == 'run') & (p.qb_kneel != 1)]
rbs = pd.concat([pd.read_csv(f'{d}/stats_{y}.csv', low_memory=False) for y in SEASONS])
run = run[run.rusher_player_id.isin(rbs[rbs.position == 'RB'].player_id)]
snaps = pd.concat([pd.read_csv(f'{d}/snaps_{y}.csv') for y in SEASONS])
active = set(snaps[(snaps.team == 'LA') & (snaps.player == 'Blake Corum')].game_id) | \
         set(run[run.rusher_player_name == 'B.Corum'].game_id)

c = run.groupby('game_id').rusher_player_name.agg(
    corum=lambda x: (x == 'B.Corum').sum(), kyren=lambda x: (x == 'K.Williams').sum(),
    rb='size')
w = g.set_index('game_id')[['season', 'fav_by']].join(c, how='inner')
w = w[w.index.isin(active)]
w['bucket'] = pd.cut(w.fav_by, [-99, 0, 3, 7, 99], labels=[
    'Not favored', 'Barely favored', 'Favored', 'Strong favorite'])

def table(x):
    t = x.groupby('bucket', observed=True).agg(games=('rb', 'size'), corum=('corum', 'mean'),
                                               kyren=('kyren', 'mean'), cs=('corum', 'sum'),
                                               ks=('kyren', 'sum'), rs=('rb', 'sum'))
    t['corum_share'] = t.cs / t.rs * 100
    t['kyren_share'] = t.ks / t.rs * 100
    return t.drop(columns=['cs', 'ks', 'rs'])

out = pd.concat({**{str(y): table(w[w.season == y]) for y in SEASONS}, 'Total': table(w)})
out.round(1).to_csv('corum_kyren_split.csv')
print(out.round(1).to_string())
