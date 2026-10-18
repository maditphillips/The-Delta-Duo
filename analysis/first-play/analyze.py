"""What does each team's first offensive play say about the rest of the game? 2016-2025 REG.

Usage: python3 analyze.py   (reads team_games.csv)  ->  tables to stdout, *_summary.csv here

Part 1, yards: first-play yards vs that team's other yards and win %, then the gap
between the two teams' first plays vs who wins.
Part 2, type: first play run or pass vs that team's pass rate, yards and win %, then
the four game combos (both pass, both run, one each).
"""
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

t = pd.read_csv('team_games.csv')
t['first_pass'] = (t.first_type == 'pass').astype(int)
t['yds_gap'] = t.first_yds - t.opp_first_yds
out = {}


def ci(x):
    """Mean and 95% CI half-width."""
    return x.mean(), 1.96 * x.std(ddof=1) / np.sqrt(len(x))


def table(df, by, name):
    g = df.groupby(by, observed=True)
    r = pd.DataFrame({
        'n': g.size(),
        'win_pct': g.win.mean(),
        'win_pct_ci': g.win.apply(lambda x: ci(x)[1]),
        'rest_yds': g.rest_yds.mean(),
        'rest_yds_ci': g.rest_yds.apply(lambda x: ci(x)[1]),
        'pts': g.pf.mean(),
        'pass_rate': g.pass_rate.mean(),
        'neutral_pass_rate': g.neutral_pass_rate.mean(),
    }).round(3)
    out[name] = r
    print(r.to_string(), '\n')


def logit(formula, df):
    # Each game shows up twice (once per team): cluster by game
    m = smf.logit(formula, df.assign(w=(df.win == 1).astype(int))[df.win != .5]).fit(
        disp=0, cov_type='cluster', cov_kwds={'groups': df[df.win != .5].game_id.astype('category').cat.codes})
    return m


print(f'{len(t)} team-games, {t.game_id.nunique()} games, 2016-2025 regular season\n')
print(f'First play: {t.first_pass.mean():.1%} pass, {1 - t.first_pass.mean():.1%} run, '
      f'mean {t.first_yds.mean():.2f} yds, median {t.first_yds.median():.0f}\n')

# ---------------- Part 1: yards ----------------
print('=' * 70, '\nPART 1: FIRST-PLAY YARDS\n')
r, pr = stats.pearsonr(t.first_yds, t.rest_yds)
rs, ps = stats.spearmanr(t.first_yds, t.rest_yds)
print(f'First-play yards vs rest-of-game yards: r = {r:.3f} (p = {pr:.2g}), Spearman = {rs:.3f} (p = {ps:.2g})')
print(f'  -> first play explains {r**2:.1%} of the spread in a team\'s other yards')
m = smf.ols('rest_yds ~ first_yds', t).fit(cov_type='cluster', cov_kwds={'groups': t.game_id.astype('category').cat.codes})
print(f'  each extra first-play yard = {m.params.first_yds:+.2f} other yards (95% CI {m.conf_int().loc["first_yds", 0]:+.2f} to {m.conf_int().loc["first_yds", 1]:+.2f})\n')
m = logit('w ~ first_yds', t)
print(f'Win vs first-play yards (logit): {np.exp(m.params.first_yds * 10):.3f}x odds per 10 yds, p = {m.pvalues.first_yds:.2g}')
# Is that just the first drive's points? Control for whether the opening drive scored
t['first_drive_pts'] = t.first_drive_result.map({'Touchdown': 7, 'Field goal': 3, 'Opp touchdown': -7, 'Safety': -2}).fillna(0)
m = logit('w ~ first_yds + first_drive_pts', t)
print(f'  holding the opening drive points fixed: {np.exp(m.params.first_yds * 10):.3f}x odds per 10 yds, p = {m.pvalues.first_yds:.2g}')
print(f'  opening drive scored: {(t.first_drive_pts > 0).mean():.1%} overall; '
      f'{(t[t.first_yds >= 20].first_drive_pts > 0).mean():.1%} after a 20+ yd first play, '
      f'{(t[t.first_yds <= 0].first_drive_pts > 0).mean():.1%} after 0 or a loss\n')

t['yds_bin'] = pd.cut(t.first_yds, [-99, -1, 0, 3, 6, 9, 19, 99],
                      labels=['loss', '0', '1-3', '4-6', '7-9', '10-19', '20+'])
print('By first-play yards:')
table(t, 'yds_bin', 'by_first_yds')

print('By first-play yards, split by type:')
table(t, ['first_type', 'yds_bin'], 'by_type_and_yds')

print('First play gained a first down?')
table(t, 'first_first_down', 'by_first_down')

# Head to head: one row per game, from the side of the team with the bigger first play
g = t[t.yds_gap >= 0].copy()
g = g[~((g.yds_gap == 0) & (g.team > g.opp))]  # equal gaps: keep one side per game
tie = g[g.yds_gap == 0]
big = g[g.yds_gap > 0]
print('HEAD TO HEAD: did the team with the bigger first play win?')
print(f'  {len(big)} games with a gap, {len(tie)} games with equal first plays')
p_win = big.win.mean()
b = stats.binomtest(int((big.win == 1).sum()), int((big.win != .5).sum()), .5)
print(f'  Bigger first play won {p_win:.1%} (95% CI {b.proportion_ci().low:.1%}-{b.proportion_ci().high:.1%}), p = {b.pvalue:.2g}')
print(f'  ...and outgained the other team {(big.total_yds > big.opp_total_yds).mean():.1%} of the time\n')
g['gap_bin'] = pd.cut(g.yds_gap, [-1, 0, 4, 9, 19, 99], labels=['0 (equal)', '1-4', '5-9', '10-19', '20+'])
print('Win % for the team with the bigger first play, by size of gap:')
table(g, 'gap_bin', 'head_to_head_gap')
m = logit('w ~ yds_gap', t)
print(f'Win vs first-play yard gap (logit): {np.exp(m.params.yds_gap * 10):.3f}x odds per 10-yd gap, p = {m.pvalues.yds_gap:.2g}\n')

# ---------------- Part 2: type ----------------
print('=' * 70, '\nPART 2: FIRST-PLAY TYPE (scramble = run, sack = pass)\n')
table(t, 'first_type', 'by_first_type')
a, b_ = t[t.first_pass == 1], t[t.first_pass == 0]
for col in ['pass_rate', 'neutral_pass_rate', 'rest_yds', 'pf']:
    x, y = a[col].dropna(), b_[col].dropna()
    print(f'  {col}: pass-first {x.mean():.3f} vs run-first {y.mean():.3f}, diff {x.mean() - y.mean():+.3f}, '
          f't-test p = {stats.ttest_ind(x, y).pvalue:.2g}')
m = logit('w ~ first_pass', t)
print(f'  win: pass-first {a.win.mean():.1%} vs run-first {b_.win.mean():.1%}, p = {m.pvalues.first_pass:.2g}\n')

# Is pass-first just pass-heavy teams? Compare to the team's own season rate (this game left out)
t['pass_rate_vs_own'] = t.pass_rate - t.season_pass_rate_ex
a, b_ = t[t.first_pass == 1], t[t.first_pass == 0]
d = t.groupby('first_type').pass_rate_vs_own.agg(['mean', 'count'])
print("Pass rate vs the team's own season average (this game left out):")
print(d.round(4).to_string())
print(f"  t-test p = {stats.ttest_ind(a.pass_rate_vs_own, b_.pass_rate_vs_own).pvalue:.2g}")
print(f"  season pass rate of pass-first teams {a.season_pass_rate_ex.mean():.3f} vs run-first {b_.season_pass_rate_ex.mean():.3f}\n")
pf_rate = t.groupby(pd.qcut(t.season_pass_rate_ex, 4, labels=['lowest', '2nd', '3rd', 'highest'])).first_pass.mean()
print('Share of first plays that are passes, by team season pass-rate quartile:')
print(pf_rate.round(3).to_string(), '\n')

# Did the first play match how the team played? "Mostly pass" = pass rate above 50%
t['mostly_pass'] = t.pass_rate > .5
c = pd.crosstab(t.first_type, t.mostly_pass, normalize='index').round(3)
c.columns = ['mostly run', 'mostly pass']
print('First play type vs whether the team mostly passed (>50%) that game:')
print(c.to_string())
print(f'  baseline: {t.mostly_pass.mean():.1%} of team-games are mostly pass\n')

# Game combos, one row per game
gm = t[t.home].copy()
gm['combo'] = np.select(
    [(gm.first_type == 'pass') & (gm.opp_first_type == 'pass'), (gm.first_type == 'run') & (gm.opp_first_type == 'run')],
    ['both pass', 'both run'], 'one each')
gm['total_pts'] = gm.pf + gm.pa
gm['total_yds_both'] = gm.total_yds + gm.opp_total_yds
gm['abs_margin'] = gm.margin.abs()
cg = gm.groupby('combo')
combo = pd.DataFrame({
    'games': cg.size(), 'share': cg.size() / len(gm),
    'total_pts': cg.total_pts.mean(), 'total_yds': cg.total_yds_both.mean(),
    'abs_margin': cg.abs_margin.mean(), 'one_score_pct': cg.abs_margin.apply(lambda x: (x <= 8).mean()),
}).round(3)
out['combos'] = combo
print('GAME COMBOS (both teams\' first plays):')
print(combo.to_string())
for col in ['total_pts', 'total_yds_both', 'abs_margin']:
    print(f'  {col}: ANOVA p = {stats.f_oneway(*[x[col] for _, x in cg]).pvalue:.2g}')
exp = t.first_pass.mean()
print(f'  expected share if independent: both pass {exp**2:.3f}, both run {(1 - exp)**2:.3f}, one each {2 * exp * (1 - exp):.3f}\n')

# One each: does the passer or the runner win?
mx = t[(t.first_type == 'pass') & (t.opp_first_type == 'run')]
b = stats.binomtest(int((mx.win == 1).sum()), int((mx.win != .5).sum()), .5)
print(f'ONE EACH ({len(mx)} games): pass-first team won {mx.win.mean():.1%} '
      f'(95% CI {b.proportion_ci().low:.1%}-{b.proportion_ci().high:.1%}), p = {b.pvalue:.2g}')
print(f'  pass-first team outgained the run-first team {(mx.total_yds > mx.opp_total_yds).mean():.1%}; '
      f'avg yds {mx.total_yds.mean():.0f} vs {mx.opp_total_yds.mean():.0f}\n')

# Home teams win more; check combos by home first play type
print('Win % by own first play and opponent first play:')
w = t.pivot_table('win', 'first_type', 'opp_first_type', aggfunc='mean').round(3)
w.index.name, w.columns.name = 'own first play', 'opp first play'
print(w.to_string(), '\n')
out['win_by_both_types'] = w

for k, v in out.items():
    v.to_csv(f'{k}.csv')
gm[['game_id', 'season', 'week', 'team', 'opp', 'first_type', 'opp_first_type', 'first_yds', 'opp_first_yds',
    'pf', 'pa', 'combo']].rename(columns={'team': 'home', 'opp': 'away'}).to_csv('games.csv', index=False)
