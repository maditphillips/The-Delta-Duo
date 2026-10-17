"""Do starting QBs beat their fantasy expectation on Sunday Night Football? 2016-2025.

Usage: python3 analyze.py DATA_DIR   (DATA_DIR holds nflverse games.csv and stats_YYYY.csv,
       the stats_player_week_YYYY.csv release files)  ->  writes qb_games.csv, summary.csv here

Same method as ../browns-vs-ravens: nflverse has no projections, so expected =
QB's average in his other starts that season x (what the opponent allowed other
starting QBs / league QB average). SNF = Sunday kickoff 8pm ET or later.
Neutral-site games are dropped so home/away means something. Since the expectation
ignores home field, SNF home/away is compared to home/away games in other slots.
Also checks win rate vs Vegas for SNF home teams. Regular season only.
"""
import sys
import numpy as np
import pandas as pd

d = sys.argv[1]
SEASONS = range(2016, 2026)
g = pd.read_csv(f'{d}/games.csv')
g = g[g.season.isin(SEASONS) & (g.game_type == 'REG') & g.result.notna()].copy()
g['slot'] = np.select(
    [(g.weekday == 'Sunday') & (g.gametime >= '20:00'), g.weekday == 'Monday',
     g.weekday == 'Thursday'],
    ['SNF', 'MNF', 'TNF'], 'Other')

t = pd.concat([
    pd.DataFrame({'game_id': g.game_id, 'team': g[s + '_team'], 'opp': g[o + '_team'],
                  'side': s, 'slot': g.slot, 'neutral': g.location == 'Neutral',
                  'qb_id': g[s + '_qb_id'], 'ml': g[s + '_moneyline'],
                  'opp_ml': g[o + '_moneyline'], 'pf': g[s + '_score'], 'pa': g[o + '_score']})
    for s, o in (('home', 'away'), ('away', 'home'))
])

s = pd.concat([pd.read_csv(f'{d}/stats_{y}.csv', low_memory=False) for y in SEASONS])
s = s[(s.season_type == 'REG') & (s.position == 'QB')]
s = s.merge(t, on=['game_id', 'team'])
s = s[s.player_id == s.qb_id].copy()           # starting QBs only

# Expected points, leaving the game itself out of both averages
fp = s.fantasy_points
own = s.groupby(['player_id', 'season']).fantasy_points
dfn = s.groupby(['season', 'opp']).fantasy_points
s['own_n'] = own.transform('size') - 1
s['own_avg'] = (own.transform('sum') - fp) / s.own_n
s['allowed'] = (dfn.transform('sum') - fp) / (dfn.transform('size') - 1)
s['expected'] = s.own_avg * s.allowed / s.groupby('season').fantasy_points.transform('mean')
s = s[(s.own_n >= 3) & ~s.neutral].copy()
s['diff'] = fp - s.expected
s[['game_id', 'player_display_name', 'team', 'opp', 'side', 'slot', 'fantasy_points',
   'expected', 'diff']].round(2).to_csv('qb_games.csv', index=False)

def stats(x):
    return pd.Series({'starts': len(x), 'actual': x.fantasy_points.mean(),
                      'expected': x.expected.mean(), 'diff': x['diff'].mean(),
                      'beat_pct': (x['diff'] > 0).mean(),
                      't': x['diff'].mean() / (x['diff'].std() / np.sqrt(len(x)))})

out = s.groupby(['slot', 'side']).apply(stats, include_groups=False).reset_index()
out.round(3).to_csv('summary.csv', index=False)
print(out.round(2).to_string(index=False))

# SNF vs every other slot, same side: is the SNF gap different from normal?
print()
for side in ('home', 'away'):
    a = s[(s.side == side) & (s.slot == 'SNF')]['diff']
    b = s[(s.side == side) & (s.slot != 'SNF')]['diff']
    se = np.sqrt(a.var() / len(a) + b.var() / len(b))
    print(f'{side}: SNF {a.mean():+.2f} vs other slots {b.mean():+.2f} -> '
          f'gap {a.mean() - b.mean():+.2f} pts (t = {(a.mean() - b.mean()) / se:.2f})')

# Team-level: do SNF home teams win more than Vegas expects?
def implied(ml):
    return np.where(ml < 0, -ml / (-ml + 100), 100 / (ml + 100))
h = t[(t.side == 'home') & ~t.neutral].copy()
a, o = implied(h.ml), implied(h.opp_ml)
h['p'] = a / (a + o)
h['win'] = np.sign(h.pf - h.pa) / 2 + .5
print('\nHome team wins vs Vegas:')
print(h.groupby('slot').agg(games=('win', 'size'), win=('win', 'mean'), vegas=('p', 'mean'))
      .round(3).to_string())
