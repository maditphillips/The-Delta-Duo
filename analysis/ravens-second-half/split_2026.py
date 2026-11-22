"""Step 8: is the 2nd-half drop the offense scoring less or the defense allowing more? By season, 2020-2026.

Usage: python3 split_2026.py  (reads team_games.csv)  ->  writes off_def_split.csv
offense_drop = 2nd-half points scored - 1st-half points scored; defense_drop = 1st-half points allowed - 2nd-half
points allowed (negative = allowed more after halftime). Rank of 32 within season, 1 = biggest drop.
"""
import os
import pandas as pd
out = os.path.dirname(os.path.abspath(__file__))
t = pd.read_csv(f'{out}/team_games.csv')
t = t[t.season.between(2020, 2026)]
s = t.groupby(['season', 'team'])[['h1_pf', 'h2_pf', 'h1_pa', 'h2_pa']].sum().reset_index()
s['offense_drop'] = s.h2_pf - s.h1_pf
s['defense_drop'] = s.h1_pa - s.h2_pa
g = s.groupby('season')
s['off_rank'] = g.offense_drop.rank(method='min').astype(int)
s['def_rank'] = g.defense_drop.rank(method='min').astype(int)
s['nfl_avg_off'] = g.offense_drop.transform('mean')
s['nfl_avg_def'] = g.defense_drop.transform('mean')
b = s[s.team == 'BAL'].drop(columns='team')
b.round(1).to_csv(f'{out}/off_def_split.csv', index=False)
pd.set_option('display.width', 200)
print(b.round(1).to_string(index=False))
