"""Step 14: win % for teams with vs without a dedicated sports psychologist, and whether the gap is statistically significant.

Usage: python3 psych_wins.py [confident|expanded]  (team_games.csv, psych_compare.py groups)  ->  writes psych_wins.csv, psych_wins_teams.csv,
       psych_wins_before_after.csv
Ties count as half a win. Games within a team-season aren't independent, so tests use team-seasons (and teams),
not single games. Same groups as psych_compare.py; Ravens left out of both.
"""
import os, sys
import numpy as np
import pandas as pd
from scipy import stats

out = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from psych_groups import has_group, NO, UNDATED
VARIANT = sys.argv[1] if len(sys.argv) > 1 else 'confident'
HAS = has_group(VARIANT)
SUF = '' if VARIANT == 'confident' else '_expanded'
t = pd.read_csv(f'{out}/team_games.csv')
t['win'] = np.sign(t.pf - t.pa) / 2 + .5
ts = t.groupby(['season', 'team']).agg(games=('win', 'size'), wins=('win', 'sum')).reset_index()
ts['win_pct'] = ts.wins / ts.games

r = ts[ts.season.between(2020, 2026)].copy()
r['grp'] = np.where(r.team.isin(NO), 'No psychologist',
                    np.where(r.team.map(HAS).notna() & (r.season >= r.team.map(HAS).fillna(9999)), 'Has psychologist', None))
r = r[r.grp.notna()]
grp = r.groupby('grp').agg(team_seasons=('win_pct', 'size'), games=('games', 'sum'), wins=('wins', 'sum'))
grp['win_pct'] = grp.wins / grp.games

# Tests: (1) team-seasons, Welch t-test + permutation; (2) teams, Mann-Whitney
a, b = r[r.grp == 'Has psychologist'].win_pct, r[r.grp == 'No psychologist'].win_pct
tt = stats.ttest_ind(a, b, equal_var=False)
rng = np.random.default_rng(0)
allv, na = r.win_pct.values, len(a)
obs = a.mean() - b.mean()
perm = np.array([(lambda s: s[:na].mean() - s[na:].mean())(rng.permutation(allv)) for _ in range(20000)])
p_perm = (np.abs(perm) >= abs(obs)).mean()
# bootstrap 95% CI of each group's win pct, resampling team-seasons
def ci(x):
    bs = [rng.choice(x, len(x)).mean() for _ in range(10000)]
    return np.percentile(bs, [2.5, 97.5])
grp['ci_low'] = [ci(r[r.grp == g].win_pct.values)[0] for g in grp.index]
grp['ci_high'] = [ci(r[r.grp == g].win_pct.values)[1] for g in grp.index]
teams = r.groupby(['grp', 'team']).agg(seasons=('win_pct', 'size'), win_pct=('win_pct', 'mean')).reset_index()
mw = stats.mannwhitneyu(teams[teams.grp == 'Has psychologist'].win_pct, teams[teams.grp == 'No psychologist'].win_pct)
grp.round(3).to_csv(f'{out}/psych_wins{SUF}.csv')
teams.round(3).to_csv(f'{out}/psych_wins_teams{SUF}.csv', index=False)
print(grp.round(3).to_string())
print(f'\nDifference: {obs:+.3f} win pct (team-season average)')
print(f'Welch t-test on team-seasons: t={tt.statistic:.2f}, p={tt.pvalue:.3f}')
print(f'Permutation test on team-seasons: p={p_perm:.3f}')
print(f'Mann-Whitney on team averages ({teams.grp.eq("Has psychologist").sum()} vs {teams.grp.eq("No psychologist").sum()} teams): p={mw.pvalue:.3f}')
print(teams.round(3).to_string(index=False))

# Before vs after the hire, same team: 3 seasons before vs seasons after (Titans left out: 1 season)
rows = []
for team, yr in HAS.items():
    if team == 'TEN' or team in UNDATED:
        continue
    pre = ts[(ts.team == team) & ts.season.between(yr - 3, yr - 1)]
    post = ts[(ts.team == team) & ts.season.between(yr, 2026)]
    rows.append({'team': team, 'hire_season': yr, 'win_pct_3yrs_before': pre.wins.sum() / pre.games.sum(),
                 'win_pct_after': post.wins.sum() / post.games.sum(), 'seasons_after': len(post)})
ba = pd.DataFrame(rows)
ba['change'] = ba.win_pct_after - ba.win_pct_3yrs_before
ba.round(3).to_csv(f'{out}/psych_wins_before_after{SUF}.csv', index=False)
print('\n=== Before vs after hire ==='); print(ba.round(3).to_string(index=False))
print(f'Paired t-test ({len(ba)} teams): p=%.3f' % stats.ttest_rel(ba.win_pct_after, ba.win_pct_3yrs_before).pvalue)
