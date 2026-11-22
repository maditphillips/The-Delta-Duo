"""Step 1: how unusual is the Ravens' second-half fade, 2020-2026?

Usage: python3 fade.py   (reads team_games.csv from halves.py)  ->  writes season_fade.csv, game_flags.csv

For every team-season: 1st-half diff, 2nd-half diff, the gap (2nd - 1st) and its
league rank. Because big first-half leads normally shrink after halftime, we also
fit 2nd-half diff ~ 1st-half diff across the league (per game) and report how far
each team falls below that expectation ("excess fade").
"""
import os
import numpy as np
import pandas as pd

out = os.path.dirname(os.path.abspath(__file__))
t = pd.read_csv(f'{out}/team_games.csv')
t = t[t.season.between(2020, 2026)]

# Expected 2nd-half diff given 1st-half diff, league-wide, per game
b, a = np.polyfit(t.h1_diff, t.h2_diff, 1)
print(f'League: expected 2nd-half diff = {a:.2f} + {b:.3f} x 1st-half diff (per game)')
t['h2_exp'] = a + b * t.h1_diff

s = t.groupby(['season', 'team']).agg(games=('game_id', 'size'), h1=('h1_diff', 'sum'), h2=('h2_diff', 'sum'),
                                      h2_exp=('h2_exp', 'sum')).reset_index()
s['gap'] = s.h2 - s.h1
s['excess'] = s.h2 - s.h2_exp
g = s.groupby('season')
s['gap_rank'] = g.gap.rank(method='min').astype(int)          # 1 = biggest drop
s['excess_rank'] = g.excess.rank(method='min').astype(int)    # 1 = most below expectation
s['h2_rank'] = g.h2.rank(method='min').astype(int)            # 1 = worst 2nd half
s['lg_avg_gap'] = g.gap.transform('mean')
s['flag_neg2h'] = (s.h1 > 0) & (s.h2 < 0)
s['flag_big_gap'] = s.gap_rank <= 8                            # bottom quarter of the league
s.to_csv(f'{out}/season_fade.csv', index=False)

bal = s[s.team == 'BAL']
pd.set_option('display.width', 220)
print(bal[['season', 'games', 'h1', 'h2', 'gap', 'gap_rank', 'lg_avg_gap', 'h2_exp', 'excess', 'excess_rank',
           'h2_rank', 'flag_neg2h', 'flag_big_gap']].round(1).to_string(index=False))

tot = s.groupby('team')[['games', 'h1', 'h2', 'h2_exp', 'gap', 'excess']].sum()
tot['gap_pg'] = tot.gap / tot.games
tot['excess_pg'] = tot.excess / tot.games
tot['gap_rank'] = tot.gap.rank(method='min').astype(int)
tot['excess_rank'] = tot.excess.rank(method='min').astype(int)
print('\n2020-2026 totals, sorted by excess fade:')
print(tot.sort_values('excess').round(1).head(10).to_string())
print('BAL:', tot.loc['BAL'].round(2).to_dict())
print('League avg gap per team over the span:', round(tot.gap.mean(), 1))
