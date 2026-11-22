"""Step 4: quarter-by-quarter margin, drive results and 4th downs when leading, 2020-2026.

Usage: python3 extras.py DATA_DIR  ->  writes quarters.csv, drives.csv, fourth_downs.csv
"""
import sys, os
import numpy as np
import pandas as pd

d = sys.argv[1]
out = os.path.dirname(os.path.abspath(__file__))
p = pd.read_parquet(f'{d}/pbp_slim.parquet')
p = p[p.season.between(2020, 2026)].reset_index(drop=True)
pd.set_option('display.width', 250)

# --- Points margin by quarter: per game, BAL vs league rank
q = p[p.qtr <= 4].groupby(['game_id', 'qtr'])[['total_home_score', 'total_away_score']].max()
q = q.groupby(level=0).diff().fillna(q).reset_index()  # points scored in each quarter
g = p.groupby('game_id')[['home_team', 'away_team']].first()
q = q.join(g, on='game_id')
qq = pd.concat([pd.DataFrame({'game_id': q.game_id, 'qtr': q.qtr, 'team': q.home_team, 'diff': q.total_home_score - q.total_away_score}),
                pd.DataFrame({'game_id': q.game_id, 'qtr': q.qtr, 'team': q.away_team, 'diff': q.total_away_score - q.total_home_score})])
qt = qq.pivot_table(index='team', columns='qtr', values='diff', aggfunc='mean')
qt.columns = [f'Q{int(c)}' for c in qt.columns]
rk = qt.rank(ascending=False, method='min').astype(int).add_suffix('_rank')
qt = qt.join(rk)
qt.round(2).to_csv(f'{out}/quarters.csv')
print('Avg point margin per game by quarter (rank of 32, 1 = best):'); print(qt.loc[['BAL']].round(2).to_string())

# --- Drives that start with the team leading by 1-16 in the 2nd half
dr = p[p.fixed_drive.notna() & p.posteam.notna() & (p.qtr.isin([3, 4]))]
first = dr.groupby(['game_id', 'fixed_drive']).agg(off=('posteam', 'first'), deff=('defteam', 'first'),
                                                  lead=('score_differential', 'first'), result=('fixed_drive_result', 'first'),
                                                  plays=('drive_play_count', 'first'), start=('yardline_100', 'first'),
                                                  season=('season', 'first')).dropna(subset=['lead'])
pts = {'Touchdown': 7, 'Field goal': 3, 'Opp touchdown': -7, 'Safety': -2}
first['pts'] = first.result.map(pts).fillna(0)
first['three_out'] = (first.plays <= 3) & (first.result == 'Punt')
first['score'] = first.result.isin(['Touchdown', 'Field goal'])
first['turnover'] = first.result.isin(['Turnover', 'Turnover on downs', 'Opp touchdown'])
o = first[first.lead.between(1, 16)]
dfn = first[first.lead.between(-16, -1)].assign(team=lambda x: x.deff)  # opponent drives while team leads
def drive_table(x, team_col):
    t = x.groupby(team_col).agg(drives=('pts', 'size'), pts_per_drive=('pts', 'mean'), score_rate=('score', 'mean'),
                               three_out_rate=('three_out', 'mean'), turnover_rate=('turnover', 'mean'),
                               start_yards_to_goal=('start', 'mean'))
    t.loc['NFL avg'] = t.drop(index='BAL').mean()
    return t
od, ddf = drive_table(o, 'off'), drive_table(dfn, 'team')
od['pts_rank'] = od.pts_per_drive.drop('NFL avg').rank(ascending=False, method='min')
ddf['pts_allowed_rank'] = ddf.pts_per_drive.drop('NFL avg').rank(ascending=False, method='min')  # 1 = most allowed
pd.concat({'offense_leading_2H': od, 'defense_leading_2H': ddf}).round(3).to_csv(f'{out}/drives.csv')
print('\nOffensive drives, leading by 1-16 in 2nd half:'); print(od.loc[['BAL', 'NFL avg']].round(3).to_string())
print('Opponent drives vs. team leading by 1-16 in 2nd half (1 = most points allowed):'); print(ddf.loc[['BAL', 'NFL avg']].round(3).to_string())
print('BAL defense by season:'); print(dfn[dfn.team == 'BAL'].groupby('season').pts.agg(['size', 'mean']).round(2).to_string())
nfl_by_season = dfn[dfn.team != 'BAL'].groupby('season').pts.mean().round(2)
print('NFL by season:', nfl_by_season.to_dict())

# --- 4th downs while leading 1-16 in 2nd half
fd = p[(p.down == 4) & p.qtr.isin([3, 4]) & p.score_differential.between(1, 16) & p.play_type.isin(['pass', 'run', 'punt', 'field_goal'])]
fd = fd.assign(go=fd.play_type.isin(['pass', 'run']), short=fd.ydstogo <= 2)
f4 = fd.groupby(fd.posteam.where(fd.posteam == 'BAL', 'NFL')).agg(fourths=('go', 'size'), go_rate=('go', 'mean'),
                                                                 go_rate_4th_and_short=('go', lambda s: s[fd.loc[s.index, 'short']].mean()))
gos = fd[fd.go]
f4['conv_rate'] = gos.groupby(gos.posteam.where(gos.posteam == 'BAL', 'NFL')).fourth_down_converted.mean()
f4.round(3).to_csv(f'{out}/fourth_downs.csv')
print('\n4th downs leading by 1-16 in 2nd half:'); print(f4.round(3).to_string())

# --- Pass vs run split, and 3rd vs 4th quarter, while leading 1-16
pl = p[p.play_type.isin(['pass', 'run']) & (p.qb_kneel == 0) & (p.qb_spike == 0) & (p.qtr <= 4)].copy()
pl['deep'] = pl.air_yards >= 15
rows = []
for side, team_col, sign in (('offense', 'posteam', 1), ('defense', 'defteam', -1)):
    x = pl[(sign * pl.score_differential).between(1, 16)].copy()
    x['who'] = np.where(x[team_col] == 'BAL', 'BAL', 'NFL')
    x['period'] = np.select([x.qtr <= 2, x.qtr == 3], ['1H', 'Q3'], 'Q4')
    for (who, period), g in x.groupby(['who', 'period']):
        ps, rs = g[g['pass'] == 1], g[g.rush == 1]
        rows.append({'side': side, 'who': who, 'period': period, 'plays': len(g), 'pass_rate': g['pass'].mean(),
                     'pass_epa': ps.epa.mean(), 'rush_epa': rs.epa.mean(), 'epa': g.epa.mean(),
                     'deep_pass_share': ps.deep.mean(), 'avg_air_yards': ps.air_yards.mean()})
split = pd.DataFrame(rows).set_index(['side', 'who', 'period'])
split.round(3).to_csv(f'{out}/pass_run_by_period.csv')
print('\nLeading 1-16, by period:'); print(split.round(3).to_string())

# --- 4th-quarter pass defense with a 1-16 lead: every season, BAL rank of 32 (1 = worst)
q4 = pl[(pl.qtr == 4) & (-pl.score_differential).between(1, 16) & (pl['pass'] == 1)]
t = q4.groupby(['season', 'defteam']).agg(dropbacks=('epa', 'size'), pass_epa_allowed=('epa', 'mean'),
                                          success_allowed=('success', 'mean')).reset_index()
t['rank_worst'] = t.groupby('season').pass_epa_allowed.rank(ascending=False, method='min').astype(int)
t['nfl_avg'] = t.season.map(q4.groupby('season').epa.mean())
t[t.defteam == 'BAL'].round(3).to_csv(f'{out}/q4_pass_defense_by_season.csv', index=False)
print('\nQ4 pass defense with a 1-16 lead, BAL by season:'); print(t[t.defteam == 'BAL'].round(3).to_string(index=False))
a = q4.groupby('defteam').epa.mean().rank(ascending=False, method='min')
print('2020-26 overall BAL rank (1 = worst):', int(a['BAL']))
