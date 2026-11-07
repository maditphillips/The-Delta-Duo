#!/usr/bin/env python3
"""Current-season matchup board using the metric that tested best for each position.

Each defense's opponent-adjusted season-to-date number, blended with last season's
as if last season were 8 extra games (the blend that tested best in FINDINGS section H).
Shown as points per game above/below league average.

    python3 board.py > BOARD.txt
"""
import os, sys, numpy as np, pandas as pd
from analyze import DATA, num_den, window, NAMES

PICK = {'RB': ('rb_scrim_pg', 'RB scrimmage yards allowed / game', 'yds'),
        'WR': ('wr_fpa',      'WR fantasy points allowed / game (PPR)', 'pts'),
        'QB': ('qb_fpa',      'QB fantasy points allowed / game', 'pts')}
PRIOR_GAMES = 8


def main():
    tg = pd.read_parquet(os.path.join(DATA, 'team_games.parquet'))
    N, D = num_den(tg)
    s = int(tg.season.max()); wk = int(tg[tg.season == s].week.max())
    cur, cur_adj, ng = window(tg, N, D, tg.season.values == s)
    _, prv_adj, _   = window(tg, N, D, tg.season.values == s - 1)

    print(f'MATCHUP BOARD — {s} season through week {wk}')
    print(f'Opponent-adjusted {s} number blended with {s - 1} (weighted as {PRIOR_GAMES} games).')
    print('+ = softer than league average (start), - = tougher (downgrade).')
    print('Expected effect is small: softest vs toughest quarter is worth about 2 PPR pts/game to a')
    print('QB or RB and about 1 to a WR. Use it to break ties, not to bench a good player.')

    for pos, (k, lab, unit) in PICK.items():
        j = NAMES.index(k)
        lgof = lambda yr: N[tg.season.values == yr][:, j].sum() / D[tg.season.values == yr][:, j].sum()
        lg = lgof(s)
        a = cur_adj[k]                                                 # last season re-centred on this
        p = (prv_adj[k] - lgof(s - 1) + lg).reindex(cur_adj.index).fillna(lg)   # season's league level
        n = ng.reindex(cur_adj.index)
        blend = (n * a + PRIOR_GAMES * p) / (n + PRIOR_GAMES) - lg
        t = pd.DataFrame({'blend': blend, 'this_season_adj': a - lg, 'last_season_adj': p - lg,
                          'raw_this_season': cur[k], 'games': n}).sort_values('blend', ascending=False)
        print(f'\n{pos} — {lab}  (league avg {lg:.1f} {unit})')
        print(f"  {'rank':>4} {'def':<4} {'blend':>7} {s:>7} {s - 1:>7} {'raw':>7} {'gp':>3}")
        for i, (team, r) in enumerate(t.iterrows(), 1):
            print(f'  {i:>4} {team:<4} {r.blend:+7.1f} {r.this_season_adj:+7.1f} {r.last_season_adj:+7.1f} '
                  f'{r.raw_this_season:7.1f} {int(r.games):>3}')


if __name__ == '__main__':
    sys.exit(main())
