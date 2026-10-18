"""Charts for the first-play study.

Usage: python3 plot.py   (reads team_games.csv)  ->  *.png here
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

SURFACE, INK, INK2, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#e4e3df'
BLUE, ORANGE = '#2a78d6', '#eb6834'
plt.rcParams.update({
    'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE, 'savefig.facecolor': SURFACE,
    'axes.edgecolor': GRID, 'axes.labelcolor': INK2, 'xtick.color': INK2, 'ytick.color': INK2,
    'text.color': INK, 'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False,
    'axes.grid': True, 'axes.grid.axis': 'y', 'grid.color': GRID, 'grid.linewidth': .8, 'axes.axisbelow': True,
})

t = pd.read_csv('team_games.csv')
t['scored'] = t.first_drive_result.isin(['Touchdown', 'Field goal'])
BINS, LABELS = [-99, -1, 0, 3, 6, 9, 19, 99], ['Loss', '0', '1-3', '4-6', '7-9', '10-19', '20+']
t['bin'] = pd.cut(t.first_yds, BINS, labels=LABELS)


def bars(ax, labels, vals, errs, color=BLUE, fmt='{:.0%}', ref=None, ns=None):
    x = np.arange(len(labels))
    ax.bar(x, vals, width=.62, color=color, edgecolor=SURFACE, linewidth=2)
    ax.errorbar(x, vals, yerr=errs, fmt='none', ecolor=INK2, elinewidth=1.2, capsize=3)
    for i, v in enumerate(vals):
        ax.text(i, v + errs[i] + (ax.get_ylim()[1] - ax.get_ylim()[0]) * .015, fmt.format(v),
                ha='center', va='bottom', fontsize=9.5, color=INK)
    if ref is not None:
        ax.axhline(ref, color=INK2, linewidth=1, linestyle='--')
    ax.set_xticks(x, labels if ns is None else [f'{l}\n(n={n:,})' for l, n in zip(labels, ns)], fontsize=9)


def se(x):
    return 1.96 * x.std(ddof=1) / np.sqrt(len(x))


def title(fig, main, sub):
    fig.suptitle(main, x=.02, ha='left', fontsize=15, fontweight='bold', y=.99)
    fig.text(.02, .925, sub, ha='left', fontsize=10.5, color=INK2)


# 1. First-play yards vs win %, other yards, opening-drive scoring
g = t.groupby('bin', observed=True)
fig, axs = plt.subplots(1, 3, figsize=(15, 5.2))
ax = axs[0]; ax.set_ylim(.35, .7)
bars(ax, LABELS, g.win.mean().values, g.win.apply(se).values, ref=.5, ns=g.size().values)
ax.set_title('Win %', loc='left', fontweight='bold'); ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1, 0))
ax = axs[1]; ax.set_ylim(250, 400)
bars(ax, LABELS, g.rest_yds.mean().values, g.rest_yds.apply(se).values, fmt='{:.0f}', ref=t.rest_yds.mean())
ax.set_title('Yards on all other plays', loc='left', fontweight='bold')
ax = axs[2]; ax.set_ylim(0, .85)
bars(ax, LABELS, g.scored.mean().values, g.scored.apply(se).values, ref=t.scored.mean())
ax.set_title('Opening drive scored (TD or FG)', loc='left', fontweight='bold'); ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1, 0))
for ax in axs:
    ax.set_xlabel('Yards gained on first offensive play')
title(fig, 'A big first play helps you win, but only through that first drive',
      'NFL regular season 2016-2025, 5,278 team-games. Dashed line = league average. Error bars = 95% range.')
fig.tight_layout(rect=(0, 0, 1, .93)); fig.savefig('yards_win_and_total.png', dpi=150); plt.close(fig)

# 2. Head to head: win % for the team with the bigger first play
h = t[t.first_yds - t.opp_first_yds > 0].copy()
h['gap'] = pd.cut(h.first_yds - h.opp_first_yds, [0, 4, 9, 19, 99], labels=['1-4', '5-9', '10-19', '20+'])
g = h.groupby('gap', observed=True)
lab = ['All games'] + list(g.groups.keys())
vals = [h.win.mean()] + list(g.win.mean().values)
errs = [se(h.win)] + list(g.win.apply(se).values)
ns = [len(h)] + list(g.size().values)
fig, ax = plt.subplots(figsize=(8.5, 5.2)); ax.set_ylim(.35, .7)
bars(ax, lab, np.array(vals), np.array(errs), ref=.5, ns=ns)
ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1, 0))
ax.set_xlabel('How many more yards their first play gained than the opponent\'s')
ax.set_ylabel('Win % of team with the bigger first play')
title(fig, 'Winning the first-play matchup barely moves the needle',
      '2,456 games where one first play out-gained the other. Dashed line = coin flip.')
fig.tight_layout(rect=(0, 0, 1, .93)); fig.savefig('head_to_head.png', dpi=150); plt.close(fig)

# 3. First-play type: pass rate the rest of the game, and win %
fig, axs = plt.subplots(1, 3, figsize=(15, 5.2))
g = t.groupby('first_type')
order = ['run', 'pass']
cols = [ORANGE, BLUE]
for ax, col, name in [(axs[0], 'pass_rate', 'Pass rate, rest of game'),
                      (axs[1], 'neutral_pass_rate', 'Pass rate, close game (Q1-3, within 7)')]:
    ax.set_ylim(.4, .7)
    v = g[col].mean()[order].values; e = g[col].apply(lambda x: se(x.dropna()))[order].values
    x = np.arange(2)
    ax.bar(x, v, width=.55, color=cols, edgecolor=SURFACE, linewidth=2)
    ax.errorbar(x, v, yerr=e, fmt='none', ecolor=INK2, elinewidth=1.2, capsize=3)
    for i in x:
        ax.text(i, v[i] + e[i] + .006, f'{v[i]:.1%}', ha='center', va='bottom', fontsize=10)
    ax.set_xticks(x, ['Ran first', 'Passed first'])
    ax.set_title(name, loc='left', fontweight='bold'); ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1, 0))
# Win % by own and opponent first play
ax = axs[2]; ax.set_ylim(.35, .7)
w = t.groupby(['first_type', 'opp_first_type']).win
m, e = w.mean(), w.apply(se)
x = np.arange(2); wd = .36
for j, (opp, c) in enumerate(zip(order, cols)):
    v = m.xs(opp, level=1)[order].values; er = e.xs(opp, level=1)[order].values
    ax.bar(x + (j - .5) * (wd + .02), v, width=wd, color=c, edgecolor=SURFACE, linewidth=2,
           label=f'Opponent {"ran" if opp == "run" else "passed"} first')
    ax.errorbar(x + (j - .5) * (wd + .02), v, yerr=er, fmt='none', ecolor=INK2, elinewidth=1.2, capsize=3)
    for i in x:
        ax.text(i + (j - .5) * (wd + .02), v[i] + er[i] + .006, f'{v[i]:.0%}', ha='center', va='bottom', fontsize=9.5)
ax.axhline(.5, color=INK2, linewidth=1, linestyle='--')
ax.set_xticks(x, ['Team ran first', 'Team passed first'])
ax.legend(frameon=False, fontsize=9, loc='upper left')
ax.set_title('Win %', loc='left', fontweight='bold'); ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1, 0))
title(fig, 'Run or pass on the first snap tells you almost nothing',
      'Pass rates leave out the first play itself. Scrambles count as runs, sacks as passes. Error bars = 95% range.')
fig.tight_layout(rect=(0, 0, 1, .93)); fig.savefig('play_type.png', dpi=150); plt.close(fig)
print('wrote yards_win_and_total.png, head_to_head.png, play_type.png')
