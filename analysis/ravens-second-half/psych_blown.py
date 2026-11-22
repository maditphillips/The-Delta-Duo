"""Step 15: blown leads for teams with vs without a dedicated sports psychologist -- seasons, teams, before/after hire.

Usage: python3 psych_blown.py DATA_DIR [confident|expanded]  (pbp_slim.parquet, games.csv, team_games.csv)  ->  writes psych_blown.csv, psych_blown_teams.csv,
       psych_blown_before_after.csv
Groups from psych_groups.py (Ravens are in the no-psychologist group). Flags rebuilt from play-by-play for 2017-2026 so
the 3 seasons before each hire are available:
  blew10   - led by 10+ at any point and did not win
  wp85     - win probability reached 85%+ and did not win
  blew_q4  - led entering the 4th quarter and did not win
  blew_half - led at halftime (any margin) and did not win
Rates per team-season = blown / chances. Tests: team-seasons (Welch t-test, permutation, seasons with 0 chances
dropped), teams (Mann-Whitney on each team's pooled rate), before/after hire (paired t-test on pooled rates).
"""
import sys, os
import numpy as np
import pandas as pd
from scipy import stats

d = sys.argv[1]
out = os.path.dirname(os.path.abspath(__file__))
pd.set_option('display.width', 220)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from psych_groups import has_group, NO, UNDATED
VARIANT = sys.argv[2] if len(sys.argv) > 2 else 'confident'
HAS = has_group(VARIANT)
SUF = '' if VARIANT == 'confident' else '_expanded'
M = {'blew10': ('led10', 'Lost after leading by 10+'), 'wp85_lost': ('wp85', 'Lost after 85%+ win chance'),
     'blew_q4': ('led_q4', 'Lost after leading entering the 4th'),
     'blew_half': ('led_half', 'Lost after leading at half')}

p = pd.read_parquet(f'{d}/pbp_slim.parquet', columns=['game_id', 'season', 'qtr', 'total_home_score', 'total_away_score', 'home_wp'])
p = p[p.season.between(2017, 2026)]
p['m'] = p.total_home_score - p.total_away_score
g = p.groupby('game_id').agg(home_max=('m', 'max'), away_max=('m', lambda x: -x.min()),
                             home_wp=('home_wp', 'max'), away_wp=('home_wp', lambda w: 1 - w.min()))
g = g.join(p[p.qtr <= 3].groupby('game_id').m.last().rename('m3')).join(p[p.qtr <= 2].groupby('game_id').m.last().rename('m2'))
t = pd.read_csv(f'{out}/team_games.csv')
t = t[t.season.between(2017, 2026)].merge(g.reset_index(), on='game_id')
home = t.game_id.str.split('_').str[-1] == t.team
t['won'] = t.pf > t.pa
t['led10'] = np.where(home, t.home_max, t.away_max) >= 10
t['wp85'] = np.where(home, t.home_wp, t.away_wp) >= .85
t['led_q4'] = np.where(home, t.m3, -t.m3) > 0
t['led_half'] = np.where(home, t.m2, -t.m2) > 0
for k, (c, _) in M.items():
    t[k] = t[c] & ~t.won

ts = t.groupby(['season', 'team'])[['led10', 'blew10', 'wp85', 'wp85_lost', 'led_q4', 'blew_q4', 'led_half', 'blew_half']].sum().reset_index()
for k, (c, _) in M.items():
    ts[k + '_rate'] = ts[k] / ts[c].replace(0, np.nan)
r = ts[ts.season.between(2020, 2026)].copy()
hire = r.team.map(HAS)
r['grp'] = np.where(r.team.isin(NO), 'No psychologist', np.where(hire.notna() & (r.season >= hire.fillna(9999)), 'Has psychologist', None))
r = r[r.grp.notna()]

rng = np.random.default_rng(0)
rows, team_rows = [], []
for k, (c, label) in M.items():
    pooled = r.groupby('grp')[[c, k]].sum()
    x = r.dropna(subset=[k + '_rate'])
    a, b = x[x.grp == 'Has psychologist'][k + '_rate'], x[x.grp == 'No psychologist'][k + '_rate']
    obs = a.mean() - b.mean()
    allv, na = x[k + '_rate'].values, len(a)
    perm = np.array([(lambda s: s[:na].mean() - s[na:].mean())(rng.permutation(allv)) for _ in range(20000)])
    tm = r.groupby(['grp', 'team'])[[c, k]].sum()
    tm['rate'] = tm[k] / tm[c]
    tm = tm.reset_index()
    mw = stats.mannwhitneyu(tm[tm.grp == 'Has psychologist'].rate.dropna(), tm[tm.grp == 'No psychologist'].rate.dropna())
    def ci(gx):
        # 95% range of the pooled rate, resampling team-seasons
        ch, bl = gx[c].values, gx[k].values
        idx = rng.integers(0, len(gx), (10000, len(gx)))
        return np.percentile(bl[idx].sum(1) / ch[idx].sum(1), [2.5, 97.5])
    for grp_name, v in (('Has psychologist', a.values), ('No psychologist', b.values)):
        lo, hi = ci(x[x.grp == grp_name])
        rows.append({'metric': label, 'group': grp_name, 'chances': int(pooled.loc[grp_name, c]), 'blown': int(pooled.loc[grp_name, k]),
                     'pooled_rate': pooled.loc[grp_name, k] / pooled.loc[grp_name, c], 'season_avg_rate': v.mean(),
                     'ci_low': lo, 'ci_high': hi, 'team_seasons_used': len(v)})
    # Ravens, same definitions, for reference (not part of either group or the tests)
    bal = ts[ts.season.between(2020, 2026) & (ts.team == 'BAL')]
    lo, hi = ci(bal)
    rows.append({'metric': label, 'group': 'Ravens', 'chances': int(bal[c].sum()), 'blown': int(bal[k].sum()),
                 'pooled_rate': bal[k].sum() / bal[c].sum(), 'ci_low': lo, 'ci_high': hi, 'team_seasons_used': len(bal)})
    # Permutation test on the pooled rate (shuffle group labels across team-seasons)
    chv, blv, isa = x[c].values, x[k].values, (x.grp == 'Has psychologist').values
    pooled_obs = blv[isa].sum() / chv[isa].sum() - blv[~isa].sum() / chv[~isa].sum()
    pp = []
    for _ in range(20000):
        sh = rng.permutation(isa)
        pp.append(blv[sh].sum() / chv[sh].sum() - blv[~sh].sum() / chv[~sh].sum())
    p_pooled = (np.abs(pp) >= abs(pooled_obs)).mean()
    rows.append({'metric': label, 'group': 'TEST', 'diff_pooled': pooled_obs, 'p_perm_pooled': p_pooled, 'diff_season_avg': obs, 'p_ttest_seasons': stats.ttest_ind(a, b, equal_var=False).pvalue,
                 'p_perm_seasons': (np.abs(perm) >= abs(obs)).mean(), 'p_mannwhitney_teams': mw.pvalue})
    tm['metric'] = label
    team_rows.append(tm)
res = pd.DataFrame(rows)
res.round(3).to_csv(f'{out}/psych_blown{SUF}.csv', index=False)
teams = pd.concat(team_rows)
teams.round(3).to_csv(f'{out}/psych_blown_teams{SUF}.csv', index=False)
print(res.round(3).to_string(index=False))
print(teams[['metric', 'grp', 'team', 'rate']].pivot_table(index=['grp', 'team'], columns='metric', values='rate').round(2).to_string())

# Before vs after hire
ba_rows = []
for team, yr in HAS.items():
    if team == 'TEN' or team in UNDATED:
        continue
    pre = ts[(ts.team == team) & ts.season.between(yr - 3, yr - 1)].sum(numeric_only=True)
    post = ts[(ts.team == team) & ts.season.between(yr, 2026)].sum(numeric_only=True)
    row = {'team': team, 'hire_season': yr}
    for k, (c, label) in M.items():
        row[f'{k}_before'] = pre[k] / pre[c]
        row[f'{k}_after'] = post[k] / post[c]
        row[f'{k}_chances_before'] = int(pre[c]); row[f'{k}_chances_after'] = int(post[c])
    ba_rows.append(row)
ba = pd.DataFrame(ba_rows)
ba.round(3).to_csv(f'{out}/psych_blown_before_after{SUF}.csv', index=False)
print('\n=== Before vs after hire ===')
print(ba[['team', 'hire_season'] + [f'{k}_{w}' for k in M for w in ('before', 'after')]].round(3).to_string(index=False))
for k, (_, label) in M.items():
    print(f'{label}: paired t-test p={stats.ttest_rel(ba[k + "_after"], ba[k + "_before"]).pvalue:.3f}, '
          f'avg change {(ba[k + "_after"] - ba[k + "_before"]).mean():+.3f}')

# Control for team quality: among games where the team led at half, did it lose? Logistic regression with the
# pregame Vegas spread (team's expected margin) and the halftime margin as controls; standard errors clustered by team.
import statsmodels.formula.api as smf
gm = pd.read_csv(f'{d}/games.csv', usecols=['game_id', 'spread_line'])
x = t[t.season.between(2020, 2026)].merge(gm, on='game_id', how='left')
x['exp_margin'] = np.where(x.game_id.str.split('_').str[-1] == x.team, x.spread_line, -x.spread_line)
x['half_margin'] = np.where(x.game_id.str.split('_').str[-1] == x.team, x.m2, -x.m2)
hire = x.team.map(HAS)
x['has'] = (hire.notna() & (x.season >= hire.fillna(9999))).astype(int)
x = x[(x.team.isin(NO) | (x.has == 1)) & x.exp_margin.notna()]
reg = []
for flag, chance in (('blew_half', 'led_half'), ('blew10', 'led10'), ('blew_q4', 'led_q4'), ('wp85_lost', 'wp85')):
    sub = x[x[chance]].copy()
    sub['lost'] = sub[flag].astype(int)
    m = smf.logit('lost ~ has + exp_margin + half_margin', data=sub).fit(disp=0, cov_type='cluster', cov_kwds={'groups': sub.team.astype('category').cat.codes})
    reg.append({'metric': flag, 'odds_ratio_psychologist': np.exp(m.params['has']), 'p_value': m.pvalues['has'], 'games': len(sub)})
    print(f'{flag}: psychologist odds ratio {np.exp(m.params["has"]):.2f}, p={m.pvalues["has"]:.3f}  (controls: Vegas spread, halftime margin; n={len(sub)})')
pd.DataFrame(reg).round(3).to_csv(f'{out}/psych_blown_controlled{SUF}.csv', index=False)
