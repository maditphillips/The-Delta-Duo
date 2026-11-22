"""Step 2: blown leads and second-half collapses by team, 2020-2026 (reg + post).

Usage: python3 blown.py DATA_DIR  ->  writes game_flags.csv, blown_by_team.csv

Per team-game flags:
  blew10  - led by 10+ at some point, did not win
  wp85    - nflverse win probability reached 85%+, did not win
  half_fade - led at halftime, lost the second half (3rd+4th quarters)
"""
import sys, os
import pandas as pd

d = sys.argv[1]
out = os.path.dirname(os.path.abspath(__file__))
p = pd.read_parquet(f'{d}/pbp_slim.parquet', columns=['game_id', 'season', 'total_home_score', 'total_away_score',
                                                       'home_wp', 'qtr'])
p = p[p.season.between(2020, 2026)]
p['margin'] = p.total_home_score - p.total_away_score
gm = p.groupby('game_id').agg(home_max=('margin', 'max'), away_max=('margin', lambda m: -m.min()),
                              home_wp_max=('home_wp', 'max'), away_wp_max=('home_wp', lambda w: 1 - w.min()))
t = pd.read_csv(f'{out}/team_games.csv')
t = t[t.season.between(2020, 2026)].merge(gm.reset_index(), on='game_id')
home = t.game_id.str.split('_').str[-1] == t.team  # game_id ends with home team
t['max_lead'] = t.home_max.where(home, t.away_max)
t['wp_max'] = t.home_wp_max.where(home, t.away_wp_max)
t['won'] = t.pf > t.pa
t['led10'] = t.max_lead >= 10
t['blew10'] = t.led10 & ~t.won
t['wp85'] = t.wp_max >= .85
t['wp85_lost'] = t.wp85 & ~t.won
t['led_half'] = t.h1_diff > 0
t['half_fade'] = t.led_half & (t.h2_diff < 0)
t['led_half_lost'] = t.led_half & ~t.won
t = t.drop(columns=['home_max', 'away_max', 'home_wp_max', 'away_wp_max'])
t.to_csv(f'{out}/game_flags.csv', index=False)

by = t.groupby('team').agg(games=('game_id', 'size'), led10=('led10', 'sum'), blew10=('blew10', 'sum'),
                           wp85=('wp85', 'sum'), wp85_lost=('wp85_lost', 'sum'), led_half=('led_half', 'sum'),
                           half_fade=('half_fade', 'sum'), led_half_lost=('led_half_lost', 'sum'))
by['blew10_rate'] = by.blew10 / by.led10
by['wp85_rate'] = by.wp85_lost / by.wp85
by['half_fade_rate'] = by.half_fade / by.led_half
by['led_half_lost_rate'] = by.led_half_lost / by.led_half
for c in ['blew10', 'wp85_lost', 'half_fade', 'blew10_rate', 'wp85_rate', 'half_fade_rate', 'led_half_lost_rate']:
    by[c + '_rk'] = by[c].rank(ascending=False, method='min').astype(int)   # 1 = most blown
by.to_csv(f'{out}/blown_by_team.csv')
pd.set_option('display.width', 250)
print(by.loc['BAL'].round(3).to_string())
lg = by[['led10', 'blew10', 'wp85', 'wp85_lost', 'led_half', 'half_fade', 'led_half_lost']].sum()
print('\nLeague rates: blew10', round(lg.blew10 / lg.led10, 3), ' wp85', round(lg.wp85_lost / lg.wp85, 3),
      ' half_fade', round(lg.half_fade / lg.led_half, 3), ' led_half_lost', round(lg.led_half_lost / lg.led_half, 3))
print('\nMost blown 10+ leads:'); print(by.sort_values('blew10', ascending=False).head(6)[['led10', 'blew10', 'blew10_rate']].round(3))
print('\nBAL by season:')
b = t[t.team == 'BAL'].groupby('season')[['led10', 'blew10', 'wp85', 'wp85_lost', 'led_half', 'half_fade', 'led_half_lost']].sum()
print(b.to_string())
print('\nBAL blown games:')
bg = t[(t.team == 'BAL') & (t.blew10 | t.wp85_lost | t.half_fade)]
print(bg[['season', 'week', 'opp', 'coach', 'h1_pf', 'h1_pa', 'h2_pf', 'h2_pa', 'pf', 'pa', 'max_lead', 'wp_max', 'blew10',
          'wp85_lost', 'half_fade']].round(2).to_string(index=False))
