import pandas as pd, numpy as np, glob

frames=[]
for y in range(2012,2026):
    w = pd.read_parquet(f'stats/week_{y}.parquet')
    w = w[(w.season_type=='REG') & (w.position.isin(['QB','RB','WR','TE']))]
    w = w[['player_id','player_display_name','position','season','week','team','fantasy_points','fantasy_points_ppr']].copy()
    frames.append(w)
d = pd.concat(frames, ignore_index=True)
d['hppr'] = (d.fantasy_points + d.fantasy_points_ppr)/2.0
# collapse rare duplicate rows (mid-season trades produce one row per team-week? verify)
dup = d.duplicated(['player_id','season','week']).sum()
print("dup player-weeks:", dup)
d = d.groupby(['player_id','player_display_name','position','season','week'], as_index=False).agg(
    hppr=('hppr','sum'), team=('team','last'))
d.to_parquet('hppr_weekly.parquet', index=False)
print(d.shape, d.season.min(), d.season.max())
print(d.groupby('season').week.max().tail(6))
