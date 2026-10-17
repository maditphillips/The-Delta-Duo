"""Blake Corum PPR points over expected, by how much the Rams were favored. 2024-present.

Usage: python3 analyze.py DATA_DIR   (DATA_DIR holds nflverse games.csv and stats_YYYY.csv,
       the stats_player_week_YYYY.csv release files)  ->  writes corum_games.csv here

Buckets use the point spread (nflverse spread_line, + = home favored), the
+1/+3/+7 numbers in the question; the Rams' moneyline is kept alongside.
Expected = Corum's PPR average in his other games that season x (PPR the
opponent allowed to other RBs that season / league RB average). Playoffs included.
"""
import sys
import numpy as np
import pandas as pd

d = sys.argv[1]
SEASONS = range(2024, 2027)
g = pd.read_csv(f'{d}/games.csv')
g = g[g.season.isin(SEASONS) & g.result.notna()]
t = pd.concat([
    pd.DataFrame({'game_id': g.game_id, 'team': g[s + '_team'],
                  'fav_by': g.spread_line * sign, 'ml': g[s + '_moneyline'],
                  'pf': g[s + '_score'], 'pa': g[o + '_score']})
    for s, o, sign in (('home', 'away', 1), ('away', 'home', -1))
])

s = pd.concat([pd.read_csv(f'{d}/stats_{y}.csv', low_memory=False) for y in SEASONS])
s = s[s.position == 'RB'].merge(t, on=['game_id', 'team'])

# What each defense allowed to RBs (all RBs, per game), and the league RB average
per = s.groupby(['season', 'game_id', 'opponent_team']).fantasy_points_ppr.sum().reset_index()
lg = per.groupby('season').fantasy_points_ppr.mean()

c = s[s.player_display_name == 'Blake Corum'].copy()
rows = []
for r in c.itertuples():
    other = c[(c.season == r.season) & (c.game_id != r.game_id)]
    dfn = per[(per.season == r.season) & (per.opponent_team == r.opponent_team) &
              (per.game_id != r.game_id)]
    rows.append(other.fantasy_points_ppr.mean() * dfn.fantasy_points_ppr.mean() / lg[r.season])
c['expected'] = rows
c['over'] = c.fantasy_points_ppr - c.expected
c['bucket'] = pd.cut(c.fav_by, [-99, 0, 3, 7, 99], labels=[
    'Not favored (pick or dog)', 'Barely favored (+0.5 to +3)',
    'Favored (+3.5 to +7)', 'Strong favorite (over +7)'])

cols = ['season', 'week', 'opponent_team', 'fav_by', 'ml', 'pf', 'pa', 'carries',
        'targets', 'fantasy_points_ppr', 'expected', 'over', 'bucket']
c[cols].round(2).to_csv('corum_games.csv', index=False)
print(c[cols].round(1).to_string(index=False))

out = c.groupby('bucket', observed=True).agg(
    games=('over', 'size'), rams_ml=('ml', 'median'), carries=('carries', 'mean'),
    ppr=('fantasy_points_ppr', 'mean'), expected=('expected', 'mean'),
    over=('over', 'mean'), beat=('over', lambda x: (x > 0).mean()), sd=('over', 'std'))
out['t'] = out.over / (out.sd / np.sqrt(out.games))
print('\n' + out.round(2).to_string())
print(f'\nCorrelation of spread with points over expected: {c.fav_by.corr(c.over):.2f} '
      f'(n={len(c)})')
