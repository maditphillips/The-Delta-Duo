#!/usr/bin/env python3
"""Which defensive metric best predicts a fantasy matchup?

For every QB, RB and WR game 2012-2025 (weeks 5+), the target is how far the player
beat or missed his own season baseline. Each defensive metric is measured the way a
fantasy manager would have it that week: the defense's season-to-date number from the
games *before* kickoff. A metric that predicts matchups well correlates with that
over/under.

    python3 analyze.py > FINDINGS.txt
"""
import os, sys, numpy as np, pandas as pd
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get('DMM_DATA', os.path.join(HERE, '.data'))
EVAL_SEASONS = range(2012, 2026)
FIRST_WEEK   = 5            # need 4 games of evidence before a season-to-date number means anything
MIN_OTHER    = 4            # games needed to form a player's baseline

# name: (numerator, denominator, label). Higher always = more yards/points/EPA allowed,
# except the few marked (-) in the label, where higher = tougher defense.
M = {
  # all-purpose
  'pts_pg':        ('pts',        'games',   'Points allowed / game'),
  'epa_play':      ('tot_epa',    'plays',   'EPA / play allowed'),
  'sr_play':       ('tot_succ',   'plays',   'Success rate allowed (all plays)'),
  'plays_pg':      ('plays',      'games',   'Offensive plays faced / game'),
  # run defense
  'rush_epa':      ('r_epa',      'r_n',     'EPA / rush'),
  'rush_epa_comp': ('rc_epa',     'rc_n',    'EPA / rush, competitive (WP 10-90%)'),
  'rush_epa_neut': ('rn_epa',     'rn_n',    'EPA / rush, neutral (WP 20-80%, not last 2 min)'),
  'rush_sr':       ('r_succ',     'r_n',     'Rush success rate'),
  'rush_sr_neut':  ('rn_succ',    'rn_n',    'Rush success rate, neutral'),
  'ypc':           ('r_yds',      'r_n',     'Yards / carry'),
  'rb_ypc':        ('rbr_yds',    'rbr_n',   'Yards / carry, RBs only'),
  'stuff_rate':    ('r_stuff',    'r_n',     'Stuff rate, runs for <=0 (-)'),
  'expl_run':      ('r_expl',     'r_n',     'Explosive run rate, 10+ yds'),
  'rush_att_pg':   ('r_n',        'games',   'Rush attempts faced / game'),
  'rush_yds_pg':   ('r_yds',      'games',   'Rush yards allowed / game'),
  'rush_td_pg':    ('r_td',       'games',   'Rush TDs allowed / game'),
  'rush_rate':     ('r_n',        'plays',   'Share of plays that are runs (run funnel)'),
  # what RBs did against them
  'rb_fpa':        ('rb_ppr',     'games',   'RB fantasy pts allowed / game (PPR)'),
  'rb_fpa_std':    ('rb_std',     'games',   'RB fantasy pts allowed / game (standard)'),
  'rb_rush_yds_pg':('rb_rush_yds','games',   'RB rush yards allowed / game'),
  'rb_rec_yds_pg': ('rb_rec_yds', 'games',   'RB receiving yards allowed / game'),
  'rb_tgt_pg':     ('rb_tgt',     'games',   'RB targets allowed / game'),
  'rb_td_pg':      ('rb_td',      'games',   'RB TDs allowed / game'),
  'rb_scrim_pg':   (('rb_rush_yds', 'rb_rec_yds'), 'games', 'RB scrimmage yards allowed / game'),
  'rb_tgt_epa':    ('rb_t_epa',   'rb_t_n',  'EPA / target to RBs'),
  # pass defense
  'pass_epa':      ('db_epa',     'db_n',    'EPA / dropback'),
  'pass_epa_comp': ('dbc_epa',    'dbc_n',   'EPA / dropback, competitive (WP 10-90%)'),
  'pass_epa_neut': ('dbn_epa',    'dbn_n',   'EPA / dropback, neutral'),
  'pass_sr':       ('db_succ',    'db_n',    'Dropback success rate'),
  'pass_sr_neut':  ('dbn_succ',   'dbn_n',   'Dropback success rate, neutral'),
  'anya':          ('anya_num',   'pa_n',    'ANY/A allowed'),
  'ypa':           ('att_yds',    'att_n',   'Yards / pass attempt'),
  'cmp_pct':       ('cmp',        'att_n',   'Completion % allowed'),
  'cpoe':          ('cpoe_sum',   'cpoe_n',  'CPOE allowed'),
  'sack_rate':     ('sacks',      'pa_n',    'Sack rate (-)'),
  'hit_rate':      ('hits',       'pa_n',    'QB hit rate incl. sacks (-)'),
  'int_rate':      ('ints',       'pa_n',    'Interception rate (-)'),
  'expl_pass':     ('p_expl',     'att_n',   'Explosive pass rate, 20+ yds'),
  'adot':          ('air',        'air_n',   'Air yards / attempt allowed'),
  'yac_cmp':       ('yac',        'cmp',     'YAC / completion allowed'),
  'proe':          ('proe_sum',   'proe_n',  'Pass rate over expected faced (pass funnel)'),
  'pass_att_pg':   ('att_n',      'games',   'Pass attempts faced / game'),
  'pass_yds_pg':   ('att_yds',    'games',   'Pass yards allowed / game'),
  'pass_td_pg':    ('p_td',       'games',   'Pass TDs allowed / game'),
  # what WRs / QBs did against them
  'wr_fpa':        ('wr_ppr',     'games',   'WR fantasy pts allowed / game (PPR)'),
  'wr_fpa_std':    ('wr_std',     'games',   'WR fantasy pts allowed / game (standard)'),
  'wr_tgt_pg':     ('wr_tgt',     'games',   'WR targets allowed / game'),
  'wr_rec_yds_pg': ('wr_rec_yds', 'games',   'WR receiving yards allowed / game'),
  'wr_td_pg':      ('wr_td',      'games',   'WR TDs allowed / game'),
  'wr_tgt_epa':    ('wr_t_epa',   'wr_t_n',  'EPA / target to WRs'),
  'wr_ypt':        ('wr_t_yds',   'wr_t_n',  'Yards / target to WRs'),
  'qb_fpa':        ('qb_ppr',     'games',   'QB fantasy pts allowed / game'),
  'qb_pass_yds_pg':('qb_pass_yds','games',   'QB pass yards allowed / game'),
  'qb_rush_yds_pg':('qb_rush_yds','games',   'QB rush yards allowed / game'),
  'qb_td_pg':      ('qb_td',      'games',   'QB TDs allowed / game (pass+rush)'),
  'te_fpa':        ('te_ppr',     'games',   'TE fantasy pts allowed / game (PPR)'),
}
NAMES = list(M)

# metrics each position's tables print, in addition to the overall top of the ranking
ASKED = {
  'RB': ['rush_epa_comp', 'rush_epa', 'rush_yds_pg', 'rush_td_pg', 'rb_fpa', 'ypc', 'rush_sr', 'pts_pg'],
  'WR': ['pass_epa_comp', 'pass_epa', 'pass_yds_pg', 'pass_td_pg', 'wr_fpa', 'ypa', 'anya', 'pts_pg'],
  'QB': ['pass_epa_comp', 'pass_epa', 'pass_yds_pg', 'pass_td_pg', 'qb_fpa', 'anya', 'sack_rate', 'pts_pg'],
}
FPA = {'RB': 'rb_fpa', 'WR': 'wr_fpa', 'QB': 'qb_fpa'}


# ---------------------------------------------------------------- defensive features
def num_den(tg):
    col = lambda c: tg[list(c)].sum(axis=1) if isinstance(c, tuple) else tg[c]
    N = np.column_stack([col(M[k][0]) for k in NAMES])
    D = np.column_stack([tg[M[k][1]] for k in NAMES])
    return N.astype(float), D.astype(float)


def window(tg, N, D, mask):
    """Raw and opponent-adjusted defensive rates over the rows in `mask`, indexed by defense.

    adjusted = raw - (den-weighted mean of how far each opponent's offense sits above
    league average, measured on that offense's *other* games in the window)."""
    t, n, d = tg[mask], N[mask], D[mask]
    off = t['off'].values
    on = pd.DataFrame(n).groupby(off).sum(); od = pd.DataFrame(d).groupby(off).sum()
    with np.errstate(invalid='ignore', divide='ignore'):
        o_ex  = (on.loc[off].values - n) / (od.loc[off].values - d)
        lg    = n.sum(0) / d.sum(0)
        dev   = o_ex - lg
        ok    = np.isfinite(dev) & (d > 0)
        contrib = np.where(ok, d * dev, 0.0); w = np.where(ok, d, 0.0)
    g = lambda a: pd.DataFrame(a).groupby(t['def'].values).sum()
    dn, dd, cc, ww = g(n), g(d), g(contrib), g(w)
    with np.errstate(invalid='ignore', divide='ignore'):
        raw = dn / dd
        adj = raw - (cc / ww).fillna(0)
    raw.columns = adj.columns = NAMES
    return raw, adj, dd.iloc[:, NAMES.index('pts_pg')].rename('n_games')


def season_to_date(tg, N, D):
    """Feature rows for (season, week W, def): every game the defense played before week W."""
    out = []
    for s in sorted(tg.season.unique()):
        for W in range(1, 19):
            mask = (tg.season.values == s) & (tg.week.values < W)
            if W == 1 or not mask.any():
                continue
            raw, adj, ng = window(tg, N, D, mask)
            f = raw.add_prefix('std_').join(adj.add_prefix('adj_')).join(ng)
            f['season'], f['week'] = s, W
            out.append(f.rename_axis('def').reset_index())
    return pd.concat(out, ignore_index=True)


def full_season(tg, N, D):
    """Whole-season rates per (season, def); used as next year's prior."""
    out = []
    for s in sorted(tg.season.unique()):
        raw, adj, _ = window(tg, N, D, tg.season.values == s)
        f = raw.add_prefix('prior_').join(adj.add_prefix('prioradj_'))
        f['season'] = s + 1
        out.append(f.rename_axis('def').reset_index())
    return pd.concat(out, ignore_index=True)


def leave_one_out(tg, N, D):
    """The defense's rate over every *other* game that season (hindsight; a ceiling, not a forecast)."""
    out = []
    for s in sorted(tg.season.unique()):
        mask = tg.season.values == s
        t, n, d = tg[mask], N[mask], D[mask]
        dn = pd.DataFrame(n).groupby(t['def'].values).sum(); dd = pd.DataFrame(d).groupby(t['def'].values).sum()
        with np.errstate(invalid='ignore', divide='ignore'):
            r = (dn.loc[t['def']].values - n) / (dd.loc[t['def']].values - d)
        f = pd.DataFrame(r, columns=['loo_' + k for k in NAMES])
        f['game_id'], f['def'] = t.game_id.values, t['def'].values
        out.append(f)
    return pd.concat(out, ignore_index=True)


def split_half(tg, N, D):
    """Odd-week vs even-week correlation of each raw rate across defense-seasons, de-meaned by season."""
    rows = []
    sub = tg.season.isin(EVAL_SEASONS).values
    for par in (1, 0):
        m = sub & (tg.week.values % 2 == par)
        t = tg[m]
        key = [t.season.values, t['def'].values]
        dn = pd.DataFrame(N[m]).groupby(key).sum(); dd = pd.DataFrame(D[m]).groupby(key).sum()
        r = dn / dd; r.columns = NAMES
        r = r - r.groupby(level=0).transform('mean')
        rows.append(r)
    a, b = rows[0].align(rows[1], join='inner')
    return pd.Series({k: a[k].corr(b[k]) for k in NAMES})


# ---------------------------------------------------------------- targets
def player_targets(pg, pos):
    p = pg[pg.season.isin(range(2011, 2027))].copy()
    if pos == 'QB':
        p = p[(p.pos == 'QB') & p.is_start_qb]
    else:
        p = p[(p.pos == pos) & p.touched]
    g = p.groupby(['player_id', 'season'])
    for sc in ('ppr', 'half', 'std'):
        tot, n = g[sc].transform('sum'), g[sc].transform('count')
        p[f'base_{sc}'] = (tot - p[sc]) / (n - 1)
        p[f'res_{sc}'] = p[sc] - p[f'base_{sc}']
    p['n_other'] = g['ppr'].transform('count') - 1
    # trailing baseline: only the player's earlier games this season (what a manager actually has)
    p = p.sort_values(['player_id', 'season', 'week'])
    cs = p.groupby(['player_id', 'season']).ppr.cumsum() - p.ppr
    k  = p.groupby(['player_id', 'season']).cumcount()
    p['base_trail'] = cs / k.replace(0, np.nan)
    p['res_trail']  = p.ppr - p.base_trail
    p['n_prev'] = k
    floor = {'QB': 10, 'RB': 7, 'WR': 7}[pos]
    return p[(p.n_other >= MIN_OTHER) & (p.base_ppr >= floor)]


def team_targets(tg, pos):
    col = f'{pos.lower()}_ppr'
    t = tg[['game_id', 'season', 'week', 'off', 'def', col]].copy()
    g = t.groupby(['off', 'season'])[col]
    t['base_ppr'] = (g.transform('sum') - t[col]) / (g.transform('count') - 1)
    t['res_ppr'] = t[col] - t['base_ppr']
    return t


# ---------------------------------------------------------------- scoring
def season_r(df, x, y):
    """Mean of per-season Pearson r and its 95% half-width across seasons."""
    rs = []
    for _, g in df.groupby('season'):
        m = g[[x, y]].dropna()
        if len(m) > 30 and m[x].std() > 0:
            rs.append(m[x].corr(m[y]))
    rs = np.array(rs)
    return rs.mean(), 1.96 * rs.std(ddof=1) / np.sqrt(len(rs))


def tier_gap(df, x, y):
    """Within each week, rank the defenses by x. Mean outcome vs the 8 softest minus the 8 toughest."""
    d = df.dropna(subset=[x, y])
    rk = d.groupby(['season', 'week'])[x].rank(pct=True)
    return d.loc[rk > 0.75, y].mean() - d.loc[rk <= 0.25, y].mean()


def score_table(df, cols, y, flip=None):
    rows = []
    for c in cols:
        if c not in df or df[c].notna().sum() < 500:
            continue
        r, hw = season_r(df, c, y)
        rows.append((c, r, hw, tier_gap(df, c, y), df[[c, y]].dropna().shape[0]))
    t = pd.DataFrame(rows, columns=['feat', 'r', 'ci', 'gap', 'n']).set_index('feat')
    return t.sort_values('r', ascending=False)


def label(feat):
    for pre, tag in (('std_', ''), ('adj_', ' [opp-adj]'), ('loo_', ' [hindsight]'),
                     ('prior_', ' [last season]'), ('prioradj_', ' [last season, opp-adj]')):
        if feat.startswith(pre) and feat[len(pre):] in M:
            return M[feat[len(pre):]][2] + tag
    return {'implied': 'Vegas implied team total', 'implied_rel': 'Vegas implied total vs team norm',
            'total_line': 'Vegas game total', 'spread': 'Vegas spread (+ = favoured)'}.get(feat, feat)


def show(t, k=None, rel=None, extra_note=''):
    if k: t = t.head(k)
    print(f"  {'metric':<58} {'r':>6} {'±95%':>6} {'r²%':>5} {'soft-tough':>10}{'  stab' if rel is not None else ''}")
    for f, row in t.iterrows():
        st = f"  {rel.get(f.split('_', 1)[1], np.nan):5.2f}" if rel is not None and '_' in f else ''
        print(f"  {label(f):<58} {row.r:6.3f} {row.ci:6.3f} {100*row.r**2:5.2f} {row.gap:+10.2f}{st}")


def cv_r2(df, feats, y):
    """Leave-one-season-out OLS on season-z-scored features; out-of-sample R² of y."""
    d = df.dropna(subset=feats + [y]).copy()
    Z = d.groupby('season')[feats].transform(lambda v: (v - v.mean()) / v.std()).values
    Y = d[y].values; S = d.season.values
    pred = np.empty_like(Y)
    for s in np.unique(S):
        tr, te = S != s, S == s
        X = np.column_stack([np.ones(tr.sum()), Z[tr]])
        b = np.linalg.lstsq(X, Y[tr], rcond=None)[0]
        pred[te] = np.column_stack([np.ones(te.sum()), Z[te]]) @ b
    return 1 - ((Y - pred) ** 2).sum() / ((Y - Y.mean()) ** 2).sum()


def forward(df, pool, y, k=5):
    chosen, path = [], []
    for _ in range(k):
        best = max(((cv_r2(df, chosen + [f], y), f) for f in pool if f not in chosen), default=None)
        if best is None or (path and best[0] <= path[-1][0] + 1e-5):
            break
        chosen.append(best[1]); path.append(best)
    return path


def hdr(s, ch='='):
    print(); print(ch * len(s)); print(s); print(ch * len(s))


# ---------------------------------------------------------------- main
def features(tg):
    """Every defensive feature plus Vegas columns; returns a function that attaches them to a target table."""
    N, D = num_den(tg)
    std   = season_to_date(tg, N, D)
    prior = full_season(tg, N, D)
    loo   = leave_one_out(tg, N, D)

    # Vegas, relative to what the same offense is usually implied for
    v = tg[['game_id', 'off', 'season', 'week', 'implied', 'total_line', 'spread']].copy()
    gv = v.groupby(['off', 'season']).implied
    v['implied_rel'] = v.implied - (gv.transform('sum') - v.implied) / (gv.transform('count') - 1)
    # same idea using only the team's earlier games this season (usable on game day)
    v = v.sort_values(['off', 'season', 'week'])
    g = v.groupby(['off', 'season']).implied
    prev_n = g.cumcount()
    v['implied_trail'] = v.implied - (g.cumsum() - v.implied) / prev_n.replace(0, np.nan)
    v = v.drop(columns='week')

    def attach(t):
        t = t.merge(std, on=['season', 'week', 'def'], how='left')
        t = t.merge(prior, on=['season', 'def'], how='left')
        t = t.merge(loo, on=['game_id', 'def'], how='left')
        return t.merge(v.drop(columns='season'), on=['game_id', 'off'], how='left')
    return attach


def main():
    tg = pd.read_parquet(os.path.join(DATA, 'team_games.parquet'))
    pg = pd.read_parquet(os.path.join(DATA, 'player_games.parquet'))
    N, D = num_den(tg)
    rel = split_half(tg, N, D)
    attach = features(tg)

    STD = ['std_' + k for k in NAMES]; ADJ = ['adj_' + k for k in NAMES]
    LOO = ['loo_' + k for k in NAMES]; VEG = ['implied', 'implied_rel', 'total_line', 'spread']

    print('DEFENSIVE MATCHUP METRICS — which defensive number best predicts a fantasy matchup?')
    print(f'nflverse play-by-play, weekly stats and closing lines; regular season {EVAL_SEASONS.start}-{EVAL_SEASONS.stop - 1}')
    print(f'Forecast sample: weeks {FIRST_WEEK}+ using only games played before kickoff.')
    print()
    print('Target   = player PPR points minus his average in his other games that season')
    print('           (RB/WR: >=7 PPR baseline, touched the ball; QB: the listed starter, >=10 baseline).')
    print('r        = mean of 14 single-season Pearson correlations; ±95% across seasons.')
    print('           Positive = the metric points the right way (bigger number, softer matchup);')
    print('           metrics marked (-) are "higher = tougher" so they should come out negative.')
    print('r²%      = share of the week-to-week over/under the metric explains.')
    print('soft-tough = PPR pts/game vs the softest quarter of defenses that week minus the toughest quarter.')
    print('stab     = odd-week vs even-week reliability of the defensive number itself (season de-meaned).')

    all_tables = {}
    for pos in ('RB', 'WR', 'QB'):
        p = attach(player_targets(pg, pos))
        ev = p[p.season.isin(EVAL_SEASONS) & (p.week >= FIRST_WEEK)]
        hdr(f'{pos}: {len(ev):,} player-games, {ev.player_id.nunique():,} players '
            f'(mean baseline {ev.base_ppr.mean():.1f} PPR, sd of over/under {ev.res_ppr.std():.1f})')

        t_std = score_table(ev, STD + VEG, 'res_ppr')
        t_adj = score_table(ev, ADJ, 'res_ppr')
        all_tables[pos] = (t_std, t_adj)

        print('\nA. The metrics you asked about — season-to-date, as known before kickoff')
        show(t_std.loc[[f'std_{k}' for k in ASKED[pos]]].sort_values('r', ascending=False), rel=rel)
        show(t_adj.loc[[f'adj_{k}' for k in ASKED[pos]]].sort_values('r', ascending=False).head(4), rel=rel)

        print('\nB. Top 15 of every metric tested, season-to-date (raw)')
        show(t_std.drop(VEG, errors='ignore'), 15, rel=rel)
        print('\n   ...and the bottom 5 (sign-reversed predictors carry their own lesson)')
        show(t_std.drop(VEG, errors='ignore').tail(5), rel=rel)

        print('\nC. Top 10, opponent-adjusted (each opponent offense measured against league average)')
        show(t_adj, 10, rel=rel)

        print('\nD. Vegas benchmarks (not a defensive metric — what the market already knows)')
        show(t_std.loc[[c for c in VEG if c in t_std.index]])

        print('\nE. Hindsight ceiling: the defense measured on every OTHER game that season')
        print('   (not available on game day; shows how much true signal exists)')
        show(score_table(ev, LOO, 'res_ppr'), 6)

        # combinations, out-of-sample
        best_std = t_std.drop(VEG, errors='ignore').index[0]
        best_adj = t_adj.index[0]
        pool = t_std.drop(VEG, errors='ignore').index[:15].tolist() + t_adj.index[:15].tolist()
        print('\nF. Out-of-sample R² of the over/under (leave-one-season-out regression)')
        for name, feats in [('best single raw metric: ' + label(best_std), [best_std]),
                            ('best single adj metric: ' + label(best_adj), [best_adj]),
                            ('Vegas implied total vs team norm', ['implied_rel']),
                            ('Vegas implied + best adj metric', ['implied_rel', best_adj])]:
            print(f'  {name:<80} {100*cv_r2(ev, feats, "res_ppr"):5.2f}%')
        print('  forward selection from the top-15 raw + top-15 adjusted metrics (no Vegas):')
        for r2, f in forward(ev, pool, 'res_ppr', 4):
            print(f'    + {label(f):<74} {100*r2:5.2f}%')

        # robustness
        print('\nG. Robustness — r for the leading metrics under other definitions')
        top = list(dict.fromkeys([best_std, best_adj, f'std_{FPA[pos]}', f'adj_{FPA[pos]}'] +
                                 [f'std_{k}' for k in ASKED[pos][:4]]))
        stars = ev[ev.base_ppr >= (18 if pos == 'QB' else 13)]
        late  = ev[ev.week >= 10]
        trail = ev[ev.n_prev >= 3]
        team  = attach(team_targets(tg, pos)); team = team[team.season.isin(EVAL_SEASONS) & (team.week >= FIRST_WEEK)]
        print(f"  {'metric':<52} {'PPR':>6} {'std':>6} {'trail':>6} {'stars':>6} {'wk10+':>6} {'team':>6}")
        for f in top:
            vals = [season_r(ev, f, 'res_ppr')[0], season_r(ev, f, 'res_std')[0],
                    season_r(trail, f, 'res_trail')[0], season_r(stars, f, 'res_ppr')[0],
                    season_r(late, f, 'res_ppr')[0], season_r(team, f, 'res_ppr')[0]]
            print(f'  {label(f):<52} ' + ' '.join(f'{x:6.3f}' for x in vals))
        print(f'  stars = baseline >= {18 if pos == "QB" else 13} PPR (n={len(stars):,});  '
              f'trail = baseline from earlier games only;  team = whole {pos} room vs its own norm')

        # early season: last year's number, this year's number, or a blend?
        print('\nH. Early season — how to measure a defense before it has a body of work')
        k = FPA[pos]; e = best_adj.split('_', 1)[1]
        allw = p[p.season.isin(EVAL_SEASONS)].copy()
        for kk in dict.fromkeys([k, e]):
            for m in (0, 2, 4, 8):
                ng = allw.n_games.fillna(0)
                cur = allw[f'adj_{kk}'].fillna(allw[f'prioradj_{kk}'])
                allw[f'blend{m}_{kk}'] = np.where(ng + m > 0,
                    (ng * cur + m * allw[f'prioradj_{kk}']) / (ng + m).replace(0, np.nan), np.nan)
            print(f'  {M[kk][2]} [opp-adj]')
            print(f"    {'weeks':<8} {'last season':>12} {'this season':>12} {'blend +2g':>10} {'blend +4g':>10} {'blend +8g':>10}")
            for lo, hi in ((2, 4), (5, 8), (9, 12), (13, 18)):
                w = allw[allw.week.between(lo, hi)]
                cells = [season_r(w, f'prioradj_{kk}', 'res_ppr')[0], season_r(w, f'adj_{kk}', 'res_ppr')[0]] + \
                        [season_r(w, f'blend{m}_{kk}', 'res_ppr')[0] for m in (2, 4, 8)]
                print(f'    {lo:>2}-{hi:<5} ' + ' '.join(f'{c:12.3f}' if i < 2 else f'{c:10.3f}' for i, c in enumerate(cells)))

    hdr('SUMMARY — best season-to-date predictor per position')
    for pos, (t_std, t_adj) in all_tables.items():
        b = pd.concat([t_std.drop(VEG, errors='ignore'), t_adj]).sort_values('r', ascending=False).head(3)
        print(f'\n{pos}')
        show(b)


if __name__ == '__main__':
    sys.exit(main())
