"""How much more work does Blake Corum get as the Rams' spread grows? 2024-present.

Usage: python3 workload.py DATA_DIR   (DATA_DIR holds nflverse games.csv,
       pbp_YYYY.csv.gz and snaps_YYYY.csv)  ->  writes corum_workload.csv here

Buckets match analyze.py. From play-by-play: carries (incl. playoffs), targets,
his share of Rams RB carries, and where his carries came: Rams up 14+
(blowout), 4th quarter, inside the 20, inside the 5. Kneel-downs excluded.
"""
import sys
import numpy as np
import pandas as pd

d = sys.argv[1]
SEASONS = range(2024, 2027)
g = pd.read_csv(f'{d}/games.csv')
g = g[g.season.isin(SEASONS) & g.result.notna() & ((g.home_team == 'LA') | (g.away_team == 'LA'))]
g = g.assign(fav_by=np.where(g.home_team == 'LA', g.spread_line, -g.spread_line))

cols = ['game_id', 'posteam', 'play_type', 'qtr', 'score_differential', 'yardline_100',
        'rusher_player_id', 'rusher_player_name', 'receiver_player_id', 'qb_kneel']
p = pd.concat([pd.read_csv(f'{d}/pbp_{y}.csv.gz', usecols=cols, low_memory=False)
               for y in SEASONS])
p = p[(p.posteam == 'LA') & p.game_id.isin(g.game_id)]
snaps = pd.concat([pd.read_csv(f'{d}/snaps_{y}.csv') for y in SEASONS])
snaps = snaps[(snaps.team == 'LA') & (snaps.position == 'RB')]

ID = p.loc[p.rusher_player_name == 'B.Corum', 'rusher_player_id'].mode()[0]
rb_ids = set(p.loc[p.rusher_player_id.isin(
    pd.concat([pd.read_csv(f'{d}/stats_{y}.csv', low_memory=False) for y in SEASONS])
    .query("position == 'RB'").player_id), 'rusher_player_id'])

run = p[(p.play_type == 'run') & (p.qb_kneel != 1)]
mine = run[run.rusher_player_id == ID]
rows = []
for gid, gr in g.set_index('game_id').iterrows():
    m = mine[mine.game_id == gid]
    sn = snaps[(snaps.game_id == gid) & (snaps.player == 'Blake Corum')]
    rb = run[(run.game_id == gid) & run.rusher_player_id.isin(rb_ids)]
    if sn.empty and m.empty:
        continue                                   # inactive
    rows.append({'game_id': gid, 'fav_by': gr.fav_by,
                 'snap_pct': sn.offense_pct.sum() * 100, 'carries': len(m),
                 'targets': (p[p.game_id == gid].receiver_player_id == ID).sum(),
                 'rb_carry_share': len(m) / max(len(rb), 1) * 100,
                 'up14_carries': (m.score_differential >= 14).sum(),
                 'q4_carries': (m.qtr >= 4).sum(),
                 'rz_carries': (m.yardline_100 <= 20).sum(),
                 'gl_carries': (m.yardline_100 <= 5).sum(),
                 'rams_up14_plays': (p[(p.game_id == gid) & p.play_type.isin(['run', 'pass'])]
                                     .score_differential >= 14).sum()})
w = pd.DataFrame(rows)
w['bucket'] = pd.cut(w.fav_by, [-99, 0, 3, 7, 99], labels=[
    'Not favored', 'Barely (+0.5 to +3)', 'Favored (+3.5 to +7)', 'Strong (over +7)'])
w['season'] = w.game_id.str[:4]
w.round(1).to_csv('corum_workload.csv', index=False)

agg = dict(games=('carries', 'size'), snap_pct=('snap_pct', 'mean'),
           carries=('carries', 'mean'), targets=('targets', 'mean'),
           rb_share=('rb_carry_share', 'mean'), up14=('up14_carries', 'mean'),
           q4=('q4_carries', 'mean'), rz=('rz_carries', 'mean'), gl=('gl_carries', 'mean'),
           team_up14_plays=('rams_up14_plays', 'mean'))
print(w.groupby('bucket', observed=True).agg(**agg).round(1).to_string())
print()
print(w.groupby(['season', 'bucket'], observed=True).agg(**agg).round(1).to_string())
x = w.carries - w.up14_carries
print(f'\nCarries NOT with Rams up 14+, by bucket:')
print(x.groupby(w.bucket, observed=True).mean().round(1).to_string())
