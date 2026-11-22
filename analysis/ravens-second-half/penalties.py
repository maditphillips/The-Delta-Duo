"""Step 11: 4th-quarter defensive penalties, 2020-2026 (checks an SI claim: worst 4th-quarter penalty margin, 2nd-most DPI).

Usage: python3 penalties.py DATA_DIR  (pbp_deep.parquet)  ->  writes penalties_q4.csv
Counts accepted penalties on the defense by quarter group, per game; rank of 32 (1 = most).
"""
import sys, os
import numpy as np
import pandas as pd
d = sys.argv[1]
out = os.path.dirname(os.path.abspath(__file__))
p = pd.read_parquet(f'{d}/pbp_deep.parquet', columns=['game_id', 'season', 'qtr', 'defteam', 'posteam', 'penalty', 'penalty_team', 'penalty_type', 'score_differential'])
p = p[(p.qtr <= 4) & (p.penalty == 1) & p.defteam.notna()]
p = p[p.penalty_team == p.defteam]
p['per'] = np.where(p.qtr == 4, 'Q4', 'Q1-3')
p['dpi'] = p.penalty_type == 'Defensive Pass Interference'
games = pd.read_csv(f'{out}/team_games.csv').query('season >= 2020').groupby('team').size()
t = p.groupby(['defteam', 'per']).agg(pens=('penalty', 'size'), dpi=('dpi', 'sum')).unstack()
t.columns = [f'{a}_{b}' for a, b in t.columns]
t = t.div(games, axis=0)
t.loc[:, 'q4_share'] = (t.pens_Q4 / (t['pens_Q1-3'] + t.pens_Q4))
for c in list(t.columns):
    t[c + '_rk'] = t[c].rank(ascending=False, method='min')
t.round(3).to_csv(f'{out}/penalties_q4.csv')
print('BAL:', t.loc['BAL'].round(3).to_dict())
print('NFL avg:', t.drop('BAL').mean().round(3).to_dict())
