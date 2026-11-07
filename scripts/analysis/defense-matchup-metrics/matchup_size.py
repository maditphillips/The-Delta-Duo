#!/usr/bin/env python3
"""How big is a matchup, measured other ways than correlation?

1. True spread of defenses: separate real defense-to-defense differences from
   single-game noise (variance components), in PPR points.
2. Tiers and extremes: over/under, % of baseline, boom and bust rates, by matchup decile
   and for the 3 softest vs 3 toughest defenses each week.
3. Start/sit: two players with nearly the same baseline in the same week — how often does
   the one with the softer matchup outscore the other? Compared with how often a higher
   baseline wins, to put a matchup in "points of baseline".

Matchup = the board metric (opponent-adjusted, this season blended with last season as 8 games).

    python3 matchup_size.py > MATCHUP_SIZE.txt
"""
import os, sys, numpy as np, pandas as pd
from analyze import DATA, EVAL_SEASONS, FIRST_WEEK, features, player_targets

PICK = {'RB': 'rb_scrim_pg', 'WR': 'wr_fpa', 'QB': 'qb_fpa'}
PRIOR_GAMES = 8


def true_spread(ev):
    """SD of the real per-defense effect on a player's over/under, net of sampling noise."""
    g = ev.groupby(['season', 'def', 'game_id']).res_ppr.mean().reset_index()
    g['res'] = g.res_ppr - g.groupby('season').res_ppr.transform('mean')
    d = g.groupby(['season', 'def']).res.agg(['mean', 'var', 'count'])
    within = (d['var'] * (d['count'] - 1)).sum() / (d['count'] - 1).sum()
    tau2 = d['mean'].var() - (within / d['count']).mean()
    return np.sqrt(max(tau2, 0)), np.sqrt(within)


def pairs(ev, col, max_base_gap):
    """Same-week pairs at the position; returns base gap, matchup gap, who scored more."""
    out = []
    for _, w in ev[['season', 'week', 'base_ppr', 'ppr', col]].dropna().groupby(['season', 'week']):
        a = np.column_stack([np.zeros(len(w)), w.values.astype(float)])   # pad so columns 3-5 line up
        i, j = np.triu_indices(len(a), 1)
        b = a[i, 3] - a[j, 3]
        keep = np.abs(b) <= max_base_gap
        out.append(np.column_stack([b[keep], (a[i, 5] - a[j, 5])[keep], (a[i, 4] - a[j, 4])[keep],
                                    a[i, 5][keep], a[j, 5][keep]]))
    return pd.DataFrame(np.vstack(out), columns=['dbase', 'dmatch', 'dpts', 'm_i', 'm_j'])


def win_rate(p, sel, by):
    """P(the player favoured by `by` outscores the other), ties dropped."""
    q = p[sel & (p[by] != 0) & (p.dpts != 0)]
    return (np.sign(q[by]) == np.sign(q.dpts)).mean(), len(q)


def hdr(s):
    print(); print('=' * len(s)); print(s); print('=' * len(s))


def main():
    tg = pd.read_parquet(os.path.join(DATA, 'team_games.parquet'))
    pg = pd.read_parquet(os.path.join(DATA, 'player_games.parquet'))
    attach = features(tg)

    # weekly finish rank among every player at the position
    pg['wk_rank'] = pg.groupby(['season', 'week', 'pos']).ppr.rank(ascending=False, method='min')

    print('HOW BIG IS A MATCHUP? — other ways to measure it')
    print(f'Regular season {EVAL_SEASONS.start}-{EVAL_SEASONS.stop - 1}, weeks {FIRST_WEEK}+. Same players and over/under as FINDINGS.txt.')
    print('Matchup metric = BOARD.txt metric: RB scrimmage yds allowed, WR / QB fantasy pts allowed;')
    print('opponent-adjusted, blended with last season as 8 games. Everything is PPR.')
    print('boom = scored 1.5x his baseline or more;  bust = half his baseline or less.')

    for pos, k in PICK.items():
        p = attach(player_targets(pg, pos))
        ng = p.n_games.fillna(0)
        p['m'] = (ng * p[f'adj_{k}'].fillna(0) + PRIOR_GAMES * p[f'prioradj_{k}']) / (ng + PRIOR_GAMES)
        ev = p[p.season.isin(EVAL_SEASONS) & (p.week >= FIRST_WEEK)].dropna(subset=['m']).copy()
        ev['boom'] = ev.ppr >= 1.5 * ev.base_ppr
        ev['bust'] = ev.ppr <= 0.5 * ev.base_ppr
        ev['top12'] = ev.wk_rank <= 12
        hdr(f'{pos}  ({len(ev):,} player-games, mean baseline {ev.base_ppr.mean():.1f} PPR)')

        # 1. true spread
        tau, noise = true_spread(ev)
        sd = ev.res_ppr.std()
        print('\n1. True size of the defense effect (variance components, defense-season level)')
        print(f'   sd of a single game over/under                     {sd:5.2f} PPR')
        print(f'   sd of the TRUE defense effect                      {tau:5.2f} PPR   '
              f'({100 * tau / ev.base_ppr.mean():.0f}% of the average baseline)')
        print(f'   => a defense at the 90th pct vs 10th pct of true softness: {2.56 * tau:4.1f} PPR apart')
        print(f'   => best any defensive metric could ever do: r = {tau / sd:.3f} '
              f'(knowing each defense perfectly)')
        r_now = np.mean([g.m.corr(g.res_ppr) for _, g in ev.groupby('season')])
        print(f'   board metric achieves r = {r_now:.3f}, i.e. {100 * r_now / (tau / sd):.0f}% of that ceiling')

        # 2. deciles and extremes
        ev['dec'] = ev.groupby(['season', 'week']).m.rank(pct=True).mul(10).clip(upper=9.999).astype(int) + 1
        ev['rk'] = ev.groupby(['season', 'week']).m.rank(ascending=False, method='dense')
        nd = ev.groupby(['season', 'week']).rk.transform('max')
        print('\n2. By matchup decile (10 = softest defenses that week)')
        print(f"   {'decile':>6} {'n':>6} {'over/under':>10} {'% of base':>9} {'boom':>6} {'bust':>6} {'top-12':>7}")
        def line(lab, x):
            print(f'   {lab:>6} {len(x):6d} {x.res_ppr.mean():+10.2f} {100 * x.res_ppr.mean() / x.base_ppr.mean():+8.1f}% '
                  f'{100 * x.boom.mean():5.1f}% {100 * x.bust.mean():5.1f}% {100 * x.top12.mean():6.1f}%')
        for dcl in range(1, 11):
            line(str(dcl), ev[ev.dec == dcl])
        line('all', ev)
        print('   extremes, ranked each week:')
        line('3 soft', ev[ev.rk <= 3]); line('3 tough', ev[ev.rk > nd - 3])

        # 3. start/sit
        pr = pairs(ev, 'm', 4.0)
        print('\n3. Start/sit: two players at this position, same week')
        print('   How often the higher-BASELINE player outscores the other (matchup ignored):')
        for lo, hi in ((0.5, 1), (1, 2), (2, 3), (3, 4)):
            wr, n = win_rate(pr, pr.dbase.abs().between(lo, hi), 'dbase')
            print(f'     baseline gap {lo}-{hi} pts{"":<14} {100 * wr:5.1f}%   (n={n:,})')
        q = pr.dbase.abs() <= 1.0
        wr, n = win_rate(pr, q, 'dmatch')
        print('   How often the SOFTER-MATCHUP player outscores the other (baselines within 1 pt):')
        print(f'     any matchup difference{"":<17} {100 * wr:5.1f}%   (n={n:,})')
        hi_gap = pr.dmatch.abs() >= pr.dmatch.abs().quantile(0.75)
        wr, n = win_rate(pr, q & hi_gap, 'dmatch')
        print(f'     largest quarter of matchup gaps{"":<8} {100 * wr:5.1f}%   (n={n:,})')
        top = pr.dmatch.abs() >= pr.dmatch.abs().quantile(0.95)
        wr, n = win_rate(pr, q & top, 'dmatch')
        print(f'     largest 5% of matchup gaps{"":<13} {100 * wr:5.1f}%   (n={n:,})')
        # points-of-baseline equivalent: regress who-wins on both gaps
        z = pr[(pr.dpts != 0)].copy()
        y = (z.dpts > 0).astype(float).values
        X = np.column_stack([z.dbase, z.dmatch])
        b = np.linalg.lstsq(np.column_stack([np.ones(len(X)), X]), y, rcond=None)[0]
        iq = ev.groupby(['season', 'week']).m.quantile(0.75).mean() - ev.groupby(['season', 'week']).m.quantile(0.25).mean()
        top_bot = ev[ev.dec == 10].m.mean() - ev[ev.dec == 1].m.mean()
        print('   Exchange rate (linear probability model on both gaps):')
        print(f'     soft-quarter vs tough-quarter matchup is worth {b[2] * iq / b[1]:4.1f} pts of baseline')
        print(f'     softest-tenth vs toughest-tenth matchup is worth {b[2] * top_bot / b[1]:4.1f} pts of baseline')


if __name__ == '__main__':
    sys.exit(main())
