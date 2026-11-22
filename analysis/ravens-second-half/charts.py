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
