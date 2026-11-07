#!/usr/bin/env python3
"""Would the weekly model rank players better if it knew the implied total
*relative to the team's norm*?

The in-season model (dd/inseason.py on the weekly-rankings branch) already reads
the raw implied team total, spread and game total. It has no column for what the
same team is usually implied for, so it cannot tell "24 for a weak offence"
from "24 for an elite one". This script does not change the model. It imports it,
rebuilds its backtest exactly, and compares:

  A  shipped     the model as it runs today (features_final)
  B  +relative   same model, plus implied_norm (team's average implied total in its
                 earlier games this season) and implied_rel (this week minus that)
  C  multiplier  A's projection times (1 + beta * implied_rel). No retraining: a layer
                 on top of the model. beta is fitted on A's out-of-sample misses in the
                 OTHER test seasons (leave-one-season-out), never on the season scored.

Scored the way the model is scored: Spearman of projection vs actual within each
week, averaged; plus mean absolute error in points. Seasons 2022-2025, each
predicted by a model trained only on earlier seasons.

    DD_MODEL=/path/to/model python3 implied_in_model.py > IMPLIED_IN_MODEL.txt
"""
import os, sys, numpy as np, pandas as pd
from scipy import stats

sys.path.insert(0, os.environ.get('DD_MODEL', 'model'))
from dd import inseason                                    # noqa: E402
from dd.features import rankable                           # noqa: E402
from dd.model import PositionModel                         # noqa: E402

SEASONS = range(2022, 2026)
POS = [('QB', 'actual_qb_4pt'), ('RB', 'actual_ppr'), ('WR', 'actual_ppr'), ('TE', 'actual_ppr')]


def add_relative(panel):
    """implied_norm: the team's mean implied total over its earlier games this season."""
    t = (panel[['season', 'week', 'team', 'implied_team_total']].dropna()
         .drop_duplicates(['season', 'week', 'team']).sort_values(['team', 'season', 'week']))
    g = t.groupby(['team', 'season']).implied_team_total
    t['implied_norm'] = g.transform(lambda x: x.shift(1).expanding().mean())
    t['implied_rel'] = t.implied_team_total - t.implied_norm
    return panel.merge(t[['season', 'week', 'team', 'implied_norm', 'implied_rel']],
                       on=['season', 'week', 'team'], how='left')


def weekly_rho(d, col, target):
    t = d.dropna(subset=[col, target])
    return t.groupby('week').apply(lambda x: stats.spearmanr(x[col], x[target]).statistic
                                   if len(x) > 5 else np.nan, include_groups=False)


def fit_predict(tr, te, pos, col, feats):
    m = PositionModel(pos, 'ppr', features=feats)
    m.fit(tr.assign(**{f'actual_{m.scoring}': tr[col]}))
    return m.predict(te)['proj'].to_numpy(), m.predict(tr)['proj'].to_numpy()


def main():
    panel = add_relative(inseason.usable(inseason.training_panel()))
    print('IMPLIED TOTAL vs TEAM NORM, TESTED INSIDE THE WEEKLY MODEL')
    print('Model: dd/inseason.py, weekly-rankings branch, unchanged. Backtest 2022-2025, weeks 2-18,')
    print('each season predicted by a model trained on the seasons before it.')
    print('rho = Spearman of projection vs actual within each week, averaged (the model\'s own score).')
    print('MAE = mean absolute error in fantasy points, players who played.')
    rows, weeks, preds = [], [], []
    for pos, col in POS:
        d = inseason.blend(rankable(panel, pos), inseason.K_ROLE, inseason.K_EFF)
        base = inseason.features_final(pos)
        plus = base + ['implied_norm', 'implied_rel']
        for s in SEASONS:
            tr, te = d[d.season < s], d[d.season == s].copy()
            if len(tr) < 500 or len(te) < 200:
                continue
            te['A'], _ = fit_predict(tr, te, pos, col, base)
            te['B'], _ = fit_predict(tr, te, pos, col, plus)
            te['pos_'], te['target'] = pos, te[col]
            preds.append(te[['pos_', 'season', 'week', 'player_id', 'team', 'implied_team_total',
                             'implied_norm', 'implied_rel', 'target', 'A', 'B']])
            print(f'  done {pos} {s}', file=sys.stderr, flush=True)
    P = pd.concat(preds, ignore_index=True)
    P.to_parquet(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.data', 'implied_in_model_preds.parquet'))

    # beta: proportional miss of A per point of implied_rel, from the other test seasons
    def beta_from(q):
        q = q.dropna(subset=['implied_rel', 'target'])
        q = q[q.A > 3]
        return np.polyfit(q.implied_rel, q.target / q.A - 1, 1)[0]
    P['C'] = np.nan
    for pos in P.pos_.unique():
        for s in SEASONS:
            m = (P.pos_ == pos) & (P.season == s)
            b = beta_from(P[(P.pos_ == pos) & (P.season != s)])
            P.loc[m, 'C'] = P.loc[m, 'A'] * (1 + b * P.loc[m, 'implied_rel'].fillna(0))
            P.loc[m, 'beta'] = b
    for (pos, s), te in P.groupby(['pos_', 'season']):
        for v in ('A', 'B', 'C'):
            r = weekly_rho(te, v, 'target')
            played = te[te.target.notna() & (te.target != 0)]
            rows.append({'pos': pos, 'season': s, 'variant': v, 'rho': r.mean(),
                         'mae': (played[v] - played.target).abs().mean(), 'beta': te.beta.iloc[0]})
            weeks.append(pd.DataFrame({'pos': pos, 'season': s, 'week': r.index,
                                       'variant': v, 'rho': r.values}))
    r = pd.DataFrame(rows); w = pd.concat(weeks)

    print('\nRanking accuracy (rho, higher is better)')
    piv = r.pivot_table(index='pos', columns='variant', values='rho')
    wp = w.pivot_table(index=['pos', 'season', 'week'], columns='variant', values='rho')
    print(f"  {'pos':<4} {'A shipped':>10} {'B +rel':>8} {'B-A':>7} {'p':>6} {'C mult':>8} {'C-A':>7} {'p':>6}")
    for pos in piv.index:
        x = wp.loc[pos]
        pb = stats.ttest_rel(x.B, x.A).pvalue; pc = stats.ttest_rel(x.C, x.A).pvalue
        print(f'  {pos:<4} {piv.loc[pos, "A"]:10.4f} {piv.loc[pos, "B"]:8.4f} {piv.loc[pos, "B"] - piv.loc[pos, "A"]:+7.4f} '
              f'{pb:6.3f} {piv.loc[pos, "C"]:8.4f} {piv.loc[pos, "C"] - piv.loc[pos, "A"]:+7.4f} {pc:6.3f}')
    print('  p = paired t-test over the ~68 test weeks per position')

    print('\nBy season (rho)')
    print(r.pivot_table(index=['pos', 'season'], columns='variant', values='rho').round(4).to_string())

    print('\nPoint accuracy (MAE, lower is better)')
    print(r.pivot_table(index='pos', columns='variant', values='mae').round(3).to_string())

    print('\nIs the shipped model already pricing it? A\'s out-of-sample miss by implied vs team norm')
    print('(actual / projection - 1, players projected 3+ points; 0% everywhere = already priced in)')
    q = P[(P.A > 3)].dropna(subset=['implied_rel', 'target']).copy()
    q['bin'] = pd.cut(q.implied_rel, [-99, -3, -1, 1, 3, 99], labels=['3+ below', '1-3 below', 'within 1', '1-3 above', '3+ above'])
    q['miss'] = q.target / q.A - 1
    print(q.pivot_table(index='pos_', columns='bin', values='miss', aggfunc='mean', observed=True)
           .map(lambda v: f'{100 * v:+.1f}%').to_string())

    print('\nMultiplier C: projection change per +1 point of implied total vs team norm')
    b = r[r.variant == 'C'].groupby('pos').beta.mean()
    for pos, v in b.items():
        print(f'  {pos}: {100 * v:+.2f}% per point  (so +3 vs norm = {300 * v:+.1f}%)')


if __name__ == '__main__':
    sys.exit(main())
