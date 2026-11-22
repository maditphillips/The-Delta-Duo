"""Charts for the Ravens second-half study. Run after halves.py, fade.py, blown.py, extras.py.

Usage: python3 charts.py  ->  writes chart_*.png here
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

out = os.path.dirname(os.path.abspath(__file__))
SURF, INK, INK2, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#e4e3df'
BLUE, ORANGE, GRAY = '#2a78d6', '#eb6834', '#b5b4ae'
plt.rcParams.update({'figure.facecolor': SURF, 'axes.facecolor': SURF, 'axes.edgecolor': GRID, 'axes.labelcolor': INK2,
                     'xtick.color': INK2, 'ytick.color': INK2, 'text.color': INK, 'font.size': 11,
                     'axes.spines.top': False, 'axes.spines.right': False, 'axes.grid': True, 'grid.color': GRID,
                     'grid.linewidth': .8, 'axes.axisbelow': True})

def save(fig, name):
    fig.tight_layout()
    fig.savefig(f'{out}/{name}', dpi=160)
    plt.close(fig)

# 1. First-half vs second-half margin by season, with league rank of the drop
s = pd.read_csv(f'{out}/season_fade.csv')
b = s[s.team == 'BAL'].sort_values('season')
fig, ax = plt.subplots(figsize=(10, 5.2))
x = np.arange(len(b)); w = .38
ax.bar(x - w / 2 - .01, b.h1, w, color=BLUE, label='1st half')
ax.bar(x + w / 2 + .01, b.h2, w, color=ORANGE, label='2nd half')
ax.axhline(0, color=INK2, lw=1)
for i, r in enumerate(b.itertuples()):
    top = max(r.h1, r.h2, 0) + 6
    ax.text(i, top, f'drop rank\n#{r.gap_rank} of 32' if r.gap < 0 else 'no drop', ha='center', va='bottom', fontsize=9, color=INK2)
ax.set_xticks(x, [f'{int(y)}' + ('*' if y == 2026 else '') for y in b.season])
ax.set_ylabel('Point differential')
ax.set_ylim(min(b.h2.min(), b.h1.min()) - 15, max(b.h1.max(), b.h2.max()) + 40)
ax.legend(frameon=False, loc='upper right', ncol=2)
ax.set_title('Ravens point differential by half, 2020–2026\n"Drop rank" = how big the 1st-to-2nd-half fall was vs. all 32 teams (#1 = biggest)',
             loc='left', fontsize=12)
fig.text(.01, .005, '*2026 through Week 10. Second half = 3rd + 4th quarters (overtime excluded). Regular season + playoffs. Data: nflverse.',
         fontsize=8.5, color=INK2)
save(fig, 'chart_halves_by_season.png')

# 2. Average margin by quarter, BAL vs NFL rank
q = pd.read_csv(f'{out}/quarters.csv').set_index('team')
fig, ax = plt.subplots(figsize=(7, 4.4))
vals = q.loc['BAL', ['Q1', 'Q2', 'Q3', 'Q4']]
ranks = q.loc['BAL', ['Q1_rank', 'Q2_rank', 'Q3_rank', 'Q4_rank']]
ax.bar(range(4), vals, .55, color=[BLUE, BLUE, BLUE, ORANGE])
ax.axhline(0, color=INK2, lw=1)
for i, (v, r) in enumerate(zip(vals, ranks)):
    ax.text(i, v + (.08 if v >= 0 else -.08), f'{v:+.2f}\n#{int(r)} in NFL', ha='center', va='bottom' if v >= 0 else 'top', fontsize=10)
ax.set_xticks(range(4), ['1st Q', '2nd Q', '3rd Q', '4th Q'])
ax.set_ylabel('Avg points margin per game')
ax.set_ylim(-1.4, 3)
ax.set_title('Ravens average margin by quarter, 2020–2026\nBest in the NFL in the 1st and 2nd; 24th in the 4th', loc='left', fontsize=12)
save(fig, 'chart_by_quarter.png')

# 3. Blown leads leaderboard
bt = pd.read_csv(f'{out}/blown_by_team.csv').set_index('team').sort_values('wp85_lost', ascending=True).tail(12)
fig, ax = plt.subplots(figsize=(7.5, 5))
ax.barh(bt.index, bt.wp85_lost, .6, color=[BLUE if t == 'BAL' else GRAY for t in bt.index])
for i, (t, r) in enumerate(bt.iterrows()):
    ax.text(r.wp85_lost + .2, i, f'{int(r.wp85_lost)} of {int(r.wp85)} ({r.wp85_rate:.0%})', va='center', fontsize=9, color=INK2)
ax.set_xlabel('Losses after reaching 85%+ win probability')
ax.set_xlim(0, bt.wp85_lost.max() + 6)
ax.grid(axis='y', visible=False)
ax.set_title('Most losses after an 85%+ win chance, 2020–2026\nNFL average rate: 11.6%', loc='left', fontsize=12)
save(fig, 'chart_blown_leads.png')

# 4. Q4 pass defense with a lead, by season
d = pd.read_csv(f'{out}/q4_pass_defense_by_season.csv')
fig, ax = plt.subplots(figsize=(9, 4.8))
ax.plot(d.season, d.pass_epa_allowed, color=BLUE, lw=2, marker='o', ms=8, label='Ravens')
ax.plot(d.season, d.nfl_avg, color=GRAY, lw=2, marker='o', ms=8, label='NFL average')
for r in d.itertuples():
    below = r.pass_epa_allowed < r.nfl_avg
    ax.text(r.season, r.pass_epa_allowed + (-.04 if below else .03), f'#{r.rank_worst} worst', ha='center',
            va='top' if below else 'bottom', fontsize=9, color=INK2)
ax.axhline(0, color=INK2, lw=1)
ax.set_ylabel('EPA per dropback allowed (higher = worse)')
ax.set_xticks(d.season)
ax.set_ylim(-.15, .5)
ax.legend(frameon=False, loc='lower right')
ax.set_title('Ravens pass defense in the 4th quarter with a 1–16 point lead\nWorst in the NFL over 2020–2026; worse than average in 6 of 7 seasons',
             loc='left', fontsize=12)
save(fig, 'chart_q4_pass_defense.png')
print('charts written')

# 5. Defensive calls in the 4th quarter with a lead (2020-2025 tracking data)
dd = pd.read_csv(f'{out}/deep_defense.csv', index_col=0)
mz = pd.read_csv(f'{out}/deep_defense_man_zone.csv')
cv = pd.read_csv(f'{out}/deep_defense_coverage.csv', header=[0, 1], index_col=0)
c0 = cv.loc['COVER_0']
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.6))
labels = ['Man coverage', 'Cover 0\n(no deep safety)']
bal = [dd.loc['man_rate', 'BAL Q4 lead'], c0[('share', 'BAL Q4')]]
nfl = [dd.loc['man_rate', 'NFL Q4 lead'], c0[('share', 'NFL Q4')]]
x = np.arange(2); w = .36
a1.bar(x - w / 2 - .01, bal, w, color=BLUE, label='Ravens'); a1.bar(x + w / 2 + .01, nfl, w, color=GRAY, label='NFL average')
for i in range(2):
    a1.text(i - w / 2, bal[i] + .01, f'{bal[i]:.0%}', ha='center', fontsize=10); a1.text(i + w / 2, nfl[i] + .01, f'{nfl[i]:.0%}', ha='center', fontsize=10)
a1.set_xticks(x, labels); a1.set_ylim(0, .55); a1.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
a1.set_title('How often they call it\n(share of opponent dropbacks)', loc='left', fontsize=11); a1.legend(frameon=False)
m = mz[mz.man == True].set_index('cell')
cells = ['BAL 1H', 'BAL Q4', 'NFL Q4']
vals = [m.loc[c, 'epa'] for c in cells]
a2.bar(range(3), vals, .55, color=[BLUE, ORANGE, GRAY])
for i, v in enumerate(vals):
    a2.text(i, v + (.01 if v >= 0 else -.01), f'{v:+.2f}', ha='center', va='bottom' if v >= 0 else 'top', fontsize=10)
a2.axhline(0, color=INK2, lw=1)
a2.set_xticks(range(3), ['Ravens\n1st half', 'Ravens\n4th quarter', 'NFL\n4th quarter']); a2.set_ylim(-.06, .27)
a2.set_title('EPA allowed per dropback in man coverage\n(higher = worse)', loc='left', fontsize=11)
fig.suptitle('Ravens 4th-quarter defense with a 1–16 point lead, 2020–2025: aggressive calls that stop working', x=.01, ha='left', fontsize=12.5)
save(fig, 'chart_q4_defense_calls.png')

# 6. Offense: pass rate over expected, 2nd half with a lead, by season
ob = pd.read_csv(f'{out}/deep_offense_by_season.csv')
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.bar(ob.season, ob.pass_over_expected, .6, color=BLUE)
ax.axhline(0, color=INK2, lw=1)
for r in ob.itertuples():
    ax.text(r.season, r.pass_over_expected - .4, f'{r.pass_over_expected:+.1f}\n#{int(33 - r.proe_rank)} most\nrun-heavy', ha='center', va='top', fontsize=9)
ax.set_ylim(-20, 2)
ax.set_xticks(ob.season)
ax.set_ylabel('Pass rate over expected (pct. points)')
ax.set_title('Ravens pass rate vs. expected, 2nd half with a 1–16 point lead\nBelow expected every season. Rank among 32 teams; #1 = most run-heavy vs. expectation',
             loc='left', fontsize=12)
save(fig, 'chart_offense_proe.png')
print('deep charts written')

# 7. Ravens vs teams with / without a dedicated sports psychologist
pc = pd.read_csv(f'{out}/psych_compare.csv', index_col=0)
cols = {'Ravens': (pc['Ravens'], BLUE), 'Has psychologist (GB, DET, CHI, BUF, KC, TEN)': (pc['Has psychologist'], ORANGE),
        'No psychologist (PIT + 13 teams where none was found)': (pc['No psychologist: all (Steelers + none found)'], GRAY)}
metrics = [('blew_10_rate', 'Lost after\nleading by 10+'), ('lost_after_85pct_rate', 'Lost after 85%+\nwin chance'),
           ('blew_q4_lead_rate', 'Lost after leading\nentering the 4th'), ('blew_q4_7plus_rate', 'Lost after leading\nby 7+ entering the 4th'),
           ('led_half_lost_game_rate', 'Lost after\nleading at half')]
fig, ax = plt.subplots(figsize=(11.5, 5.2))
w = .26; x = np.arange(len(metrics))
for j, (lab, (ser, col)) in enumerate(cols.items()):
    vals = [ser[m] for m, _ in metrics]
    xs = x + (j - 1) * (w + .01)
    ax.bar(xs, vals, w, color=col, label=lab)
    for xx, v in zip(xs, vals):
        ax.text(xx, v + .005, f'{v:.0%}', ha='center', fontsize=9)
ax.set_xticks(x, [l for _, l in metrics]); ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
ax.set_ylim(0, .34); ax.legend(frameon=False, loc='upper right', fontsize=9.5)
ax.set_title('How often a lead turns into a loss, 2020–2026\nRavens vs teams with and without a dedicated sports psychologist',
             loc='left', fontsize=12)
fig.text(.01, .005, f"Win pct: Ravens {pc.loc['win_pct', 'Ravens']:.3f}, psychologist teams {pc.loc['win_pct', 'Has psychologist']:.3f}, "
         f"no-psychologist teams {pc.loc['win_pct', 'No psychologist: all (Steelers + none found)']:.3f}. Psychologist teams counted only from their hire year.",
         fontsize=8.5, color=INK2)
save(fig, 'chart_psych_compare.png')
print('psych chart written')
