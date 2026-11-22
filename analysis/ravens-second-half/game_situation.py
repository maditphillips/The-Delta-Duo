"""Step 10: what game situations does the Ravens offense hand its defense late in games? 2020-2026.

Usage: python3 game_situation.py DATA_DIR  (pbp_slim.parquet)  ->  writes situation_offense.csv, situation_handoff.csv

Every 4th-quarter offensive drive that starts with the team leading by 1-16, and the opponent drive that follows it.
Compared to the other 31 teams (rank of 32, 1 = highest value).
"""
import sys, os
import numpy as np
import pandas as pd

d = sys.argv[1]
out = os.path.dirname(os.path.abspath(__file__))
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30)
p = pd.read_parquet(f'{d}/pbp_slim.parquet')
p = p[p.season.between(2020, 2026) & (p.qtr <= 4)].reset_index(drop=True)
p['clock_min'] = p.game_seconds_remaining / 60
sc = p.play_type.isin(['pass', 'run']) & (p.qb_kneel == 0) & (p.qb_spike == 0)

# One row per drive
dr = p[p.posteam.notna() & p.fixed_drive.notna()].groupby(['game_id', 'fixed_drive']).agg(
    season=('season', 'first'), off=('posteam', 'first'), deff=('defteam', 'first'), qtr=('qtr', 'first'),
    lead=('score_differential', 'first'), start_min=('clock_min', 'first'), end_min=('clock_min', 'last'),
    start_yds=('yardline_100', 'first'), result=('fixed_drive_result', 'first')).reset_index()
plays = p[sc].groupby(['game_id', 'fixed_drive']).agg(n_plays=('epa', 'size'), runs=('rush', 'sum'), epa=('epa', 'sum'),
                                                     first_downs=('first_down', 'sum'))
dr = dr.join(plays, on=['game_id', 'fixed_drive'])
dr['mins_used'] = dr.start_min - dr.end_min
dr['pts'] = dr.result.map({'Touchdown': 7, 'Field goal': 3}).fillna(0)
dr['three_out'] = (dr.n_plays <= 3) & (dr.result == 'Punt')
dr['punt'] = dr.result == 'Punt'
dr['turnover'] = dr.result.isin(['Turnover', 'Turnover on downs'])
dr['kept_ball_to_end'] = dr.result == 'End of half'
dr = dr.sort_values(['game_id', 'fixed_drive'])
nxt = dr.groupby('game_id').shift(-1)  # the opponent's next drive
dr['opp_start_min'] = nxt.start_min
dr['opp_start_yds'] = nxt.start_yds
dr['opp_pts'] = nxt.pts
dr['opp_scored'] = nxt.pts > 0

q4 = dr[(dr.qtr == 4) & dr.lead.between(1, 16)].copy()
q4['who'] = np.where(q4.off == 'BAL', 'BAL', 'NFL')
q4['window'] = np.where(q4.start_min > 5, 'Q4, >5 min left', 'Q4, last 5 min')

M = {'drives': ('pts', 'size'), 'pts_per_drive': ('pts', 'mean'), 'mins_used': ('mins_used', 'mean'),
     'plays': ('n_plays', 'mean'), 'run_share': ('runs', 'sum'), 'first_downs': ('first_downs', 'mean'),
     'three_and_out': ('three_out', 'mean'), 'punt_rate': ('punt', 'mean'), 'turnover_rate': ('turnover', 'mean'),
     'ran_out_clock': ('kept_ball_to_end', 'mean'), 'opp_gets_ball_min_left': ('opp_start_min', 'mean'),
     'opp_start_yds_to_goal': ('opp_start_yds', 'mean'), 'opp_next_drive_pts': ('opp_pts', 'mean'),
     'opp_next_drive_scored': ('opp_scored', 'mean')}
def agg(x):
    t = x.agg(**{k: pd.NamedAgg(*v) for k, v in M.items()})
    t['run_share'] = x.runs.sum() / x.n_plays.sum() if not hasattr(x, 'groups') else x.runs.sum() / x.n_plays.sum()
    return t
rows = {}
for (w, win), g in q4.groupby(['who', 'window']):
    rows[f'{w} | {win}'] = agg(g.assign(k=1).groupby('k')).iloc[0]
for w, g in q4.groupby('who'):
    rows[f'{w} | Q4 all'] = agg(g.assign(k=1).groupby('k')).iloc[0]
res = pd.DataFrame(rows)
team = q4.groupby('off')
tt = agg(team)
res['BAL rank of 32 (Q4 all)'] = tt.rank(ascending=False, method='min').loc['BAL']
res = res[['BAL | Q4 all', 'NFL | Q4 all', 'BAL rank of 32 (Q4 all)', 'BAL | Q4, >5 min left', 'NFL | Q4, >5 min left',
           'BAL | Q4, last 5 min', 'NFL | Q4, last 5 min']]
res.round(3).to_csv(f'{out}/situation_offense.csv')
print('=== 4th-quarter drives starting with a 1-16 lead, and the opponent drive that follows ==='); print(res.round(3).to_string())

# By season: last-5-minute drives with a lead
l5 = q4[q4.window == 'Q4, last 5 min']
bs = l5.groupby(['season', 'who']).agg(drives=('pts', 'size'), three_and_out=('three_out', 'mean'), ran_out_clock=('kept_ball_to_end', 'mean'),
                                       mins_used=('mins_used', 'mean'), opp_next_drive_scored=('opp_scored', 'mean')).unstack()
bs.round(3).to_csv(f'{out}/situation_handoff.csv')
print('\n=== Last 5 minutes with a lead, by season ==='); print(bs.round(2).to_string())

# Exposure: how many opponent dropbacks does the defense face in Q4 with a lead, per game?
dbk = p[sc & (p.qb_dropback == 1) & (p.qtr == 4) & (-p.score_differential).between(1, 16)]
games = p[(p.qtr == 4) & (-p.score_differential).between(1, 16)].groupby('defteam').game_id.nunique()
exp = (dbk.groupby('defteam').size() / games).rename('q4_lead_dropbacks_per_game')
print('\nOpponent Q4 dropbacks per game when leading: BAL', round(exp['BAL'], 1), ' NFL', round(exp.drop('BAL').mean(), 1),
      ' BAL rank', int(exp.rank(ascending=False)['BAL']))
