#!/usr/bin/env python3
"""What Vegas implied team total marks a good vs bad fantasy matchup?

Implied team total = (game total +/- spread) / 2, from nflverse closing lines.
For each position: the player's over/under vs his own baseline, by implied total.

The break-even is where the average over/under crosses zero. It is reported two ways:
  absolute  — one implied total for everyone
  relative  — implied total minus what the same team has been implied for in its
              earlier games this season (known on game day)

    python3 implied.py > IMPLIED.txt
"""
import os, sys, numpy as np, pandas as pd
from analyze import DATA, EVAL_SEASONS, FIRST_WEEK, features, player_targets

ABS_BINS = [0, 17, 19, 21, 23, 25, 27, 29, 99]
REL_BINS = [-99, -5, -3, -1, 1, 3, 5, 99]


def fit(x, y):
    b, a = np.polyfit(x, y, 1)
    return a, b, -a / b


def table(ev, col, bins, fmt):
    ev = ev.assign(bin=pd.cut(ev[col], bins, right=False))
    print(f"   {'implied':>11} {'n':>6} {'over/under':>10} {'% of base':>9} {'boom':>6} {'bust':>6}")
    for b, g in ev.groupby('bin', observed=True):
        lo, hi = b.left, b.right
        lab = (f'< {fmt(hi)}' if lo <= -99 or lo == 0 else f'{fmt(lo)}+' if hi >= 99 else f'{fmt(lo)} to {fmt(hi)}')
        print(f'   {lab:>11} {len(g):6d} {g.res_ppr.mean():+10.2f} {100 * g.res_ppr.mean() / g.base_ppr.mean():+8.1f}% '
              f'{100 * (g.ppr >= 1.5 * g.base_ppr).mean():5.1f}% {100 * (g.ppr <= 0.5 * g.base_ppr).mean():5.1f}%')


def hdr(s):
    print(); print('=' * len(s)); print(s); print('=' * len(s))


def main():
    tg = pd.read_parquet(os.path.join(DATA, 'team_games.parquet'))
    pg = pd.read_parquet(os.path.join(DATA, 'player_games.parquet'))
    attach = features(tg)

    print('VEGAS IMPLIED TEAM TOTAL — where does a matchup turn good or bad?')
    print(f'Regular season {EVAL_SEASONS.start}-{EVAL_SEASONS.stop - 1}, weeks {FIRST_WEEK}+. Same players and over/under as FINDINGS.txt (PPR).')
    print('over/under = points vs the player\'s own average;  boom >= 1.5x baseline;  bust <= 0.5x.')
    print('team norm = the team\'s average implied total in its earlier games this season.')

    for pos in ('RB', 'WR', 'QB'):
        p = attach(player_targets(pg, pos))
        ev = p[p.season.isin(EVAL_SEASONS) & (p.week >= FIRST_WEEK)].dropna(subset=['implied', 'implied_trail'])
        hdr(f'{pos}  ({len(ev):,} player-games)')
        # the over/under averages slightly below zero in this sample (players are selected on a
        # high baseline, which then regresses), so break-evens are found on the centred value
        ev = ev.assign(res_ppr=ev.res_ppr - ev.res_ppr.mean())

        a, b, x0 = fit(ev.implied, ev.res_ppr)
        print(f'\n1. Absolute implied total  (league average in sample: {ev.implied.mean():.1f})')
        table(ev, 'implied', ABS_BINS, lambda v: f'{v:g}')
        print(f'   linear fit: each +1 implied point = {b:+.2f} PPR;  break-even at {x0:.1f}')

        print('\n   Break-even depends on how good the offense usually is:')
        tn = ev.implied - ev.implied_trail
        for lab, m in (('teams usually implied < 21', tn < 21), ('21 to 24', tn.between(21, 24)),
                       ('24+', tn > 24)):
            g = ev[m]
            a2, b2, x2 = fit(g.implied, g.res_ppr)
            print(f'     {lab:<28} n={len(g):5,}  team norm {tn[m].mean():4.1f}  break-even {x2:4.1f}  '
                  f'slope {b2:+.2f}/pt')

        a, b, x0 = fit(ev.implied_trail, ev.res_ppr)
        print('\n2. Relative to the team\'s norm (implied total minus its earlier-game average)')
        table(ev, 'implied_trail', REL_BINS, lambda v: f'{v:+g}')
        print(f'   linear fit: each +1 point vs norm = {b:+.2f} PPR;  break-even at {x0:+.1f} vs norm')

        print('\n3. By era (absolute break-even moves with league scoring)')
        for lo, hi in ((2012, 2017), (2018, 2025)):
            g = ev[ev.season.between(lo, hi)]
            _, b3, x3 = fit(g.implied, g.res_ppr)
            print(f'     {lo}-{hi}: league avg implied {g.implied.mean():4.1f}   break-even {x3:4.1f}   slope {b3:+.2f}/pt')


if __name__ == '__main__':
    sys.exit(main())
