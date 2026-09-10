"""Collapse the study's output files into report_data.json for report.py.

Keeping this separate means the HTML never reaches into a DataFrame, and every
figure on the page traces back to a committed .txt/.csv from analyze.py.
"""
import json
import numpy as np
import pandas as pd
import common as C
import fantasy as Fa

LABEL = {
    'rush_share': 'share of team carries', 'snap_pct': 'snap share',
    'target_share': 'target share', 'air_yards_share': 'air yards share', 'wopr': 'WOPR',
    'carries': 'carries', 'targets': 'targets', 'receptions': 'receptions',
    'touches': 'touches', 'opportunities': 'carries + targets',
    'rushing_yards': 'rushing yards', 'receiving_yards': 'receiving yards',
    'air_yards': 'air yards', 'rushing_tds': 'rushing TDs',
    'receiving_tds': 'receiving TDs', 'pass_tds': 'passing TDs',
    'fantasy_ppg_ppr': 'PPR points', 'fantasy_ppg_half': 'half-PPR points',
    'fantasy_ppg': 'fantasy points', 'pass_attempts': 'pass attempts',
    'passing_yards': 'passing yards', 'qb_carries': 'QB rush attempts',
    'yards_per_carry': 'yards per carry', 'yards_per_touch': 'yards per touch',
    'epa_per_carry': 'EPA per carry', 'rush_fd_rate': 'first down rate',
    'yards_per_target': 'yards per target', 'catch_rate': 'catch rate',
    'yards_per_catch': 'yards per catch', 'adot': 'average depth of target',
    'epa_per_target': 'EPA per target', 'completion_pct': 'completion %', 'cpoe': 'CPOE',
    'yards_per_attempt': 'yards per attempt', 'epa_per_pass': 'EPA per pass',
    'pass_td_rate': 'TD rate', 'int_rate': 'INT rate'}

ASKED = [('RB', 'rush_share'), ('RB', 'snap_pct'), ('RB', 'targets'), ('RB', 'carries'),
         ('RB', 'fantasy_ppg_ppr'), ('RB', 'yards_per_carry'),
         ('WR', 'snap_pct'), ('WR', 'air_yards'), ('WR', 'target_share'), ('WR', 'targets'),
         ('WR', 'fantasy_ppg_ppr'), ('WR', 'yards_per_target'),
         ('TE', 'target_share'), ('TE', 'fantasy_ppg_ppr'),
         ('QB', 'pass_attempts'), ('QB', 'fantasy_ppg'), ('QB', 'completion_pct'),
         ('QB', 'cpoe')]

CURVE_METRICS = {
    'RB': ['rush_share', 'carries', 'fantasy_ppg_ppr', 'yards_per_carry'],
    'WR': ['target_share', 'targets', 'fantasy_ppg_ppr', 'yards_per_target'],
    'TE': ['target_share', 'targets', 'fantasy_ppg_ppr', 'catch_rate'],
    'QB': ['pass_attempts', 'fantasy_ppg', 'completion_pct', 'cpoe']}

TEAM_BINS = [(-99, -21, 'lost by 21+'), (-21, -9, 'lost by 9-20'), (-9, 0, 'lost by 1-8'),
             (0, 9, 'won by 1-8'), (9, 21, 'won by 9-20'), (20, 99, 'won by 21+')]


def signal_frame(pred, stab):
    m = stab.merge(pred[['position', 'metric', 'r', 'r2', 'r_prior', 'r_midweek', 'n']],
                   on=['position', 'metric'], how='left')
    m['label'] = m.metric.map(LABEL).fillna(m.metric)
    m['group'] = np.where(m.kind.isin(['volume', 'share', 'role']), 'opportunity', 'efficiency')
    cols = ['position', 'metric', 'label', 'kind', 'group', 'rel1', 'lam', 'g50', 'g70',
            'r', 'r2', 'r_prior', 'r_midweek']
    return m[cols].round(4).sort_values('rel1', ascending=False)


def main():
    pred = pd.read_csv('out_predictiveness.csv')
    stab = pd.read_csv('out_stability.csv')
    team = pd.read_csv('out_team.csv')
    sig = signal_frame(pred, stab)

    curves = {}
    for pos, mets in CURVE_METRICS.items():
        c = pd.read_csv(f'out_curve_{pos}.csv')
        curves[pos] = [dict(metric=x, label=LABEL.get(x, x),
                            vals=[round(v, 3) for v in c[x].tolist()],
                            prior=round(float(c['prior_' + x].iloc[0]), 3)) for x in mets]

    panic = {}
    for pos in ('QB', 'RB', 'WR', 'TE'):
        r = pd.read_csv(f'out_ranks_{pos}.csv')
        r = r[r.prior_rank.notna()]
        rows = []
        for pt in (True, False):
            for wt in (True, False):
                s = r[((r.prior_rank <= 12) == pt) & ((r.w1_rank <= 12) == wt)]
                if len(s) < 15:
                    continue
                rows.append(dict(prior=pt, wk1=wt, n=int(len(s)),
                                 top12=round(float((s.ros_rank <= 12).mean()), 3),
                                 top24=round(float((s.ros_rank <= 24).mean()), 3),
                                 med_ppg=round(float(s.ros_ppg.median()), 1)))
        panic[pos] = rows

    won, lost = team[team.w1_win == 1], team[team.w1_win == 0]
    def side(s):
        return dict(n=int(len(s)), ros_win=round(float(s.ros_win.mean()), 4),
                    playoffs=round(float(s.playoffs.mean()), 4),
                    wins=round(float((s.wins / s.games * 17).mean()), 2),
                    cover=round(float(s.ros_cover.mean()), 4))
    d = team[np.isfinite(team[['w1_margin', 'ros_margin']]).all(axis=1)]
    T = dict(n=int(len(team)), won=side(won), lost=side(lost),
             r_margin=round(float(np.corrcoef(d.w1_margin, d.ros_margin)[0, 1]), 3),
             bins=[dict(label=lab, n=int(len(s)), ros_win=round(float(s.ros_win.mean()), 3),
                        playoffs=round(float(s.playoffs.mean()), 3))
                   for lo, hi, lab in TEAM_BINS
                   for s in [team[(team.w1_margin > lo) & (team.w1_margin <= hi)]]
                   if len(s) >= 20],
             split=[dict(prior=pl, wk1=wl, n=int(len(s)),
                         ros_win=round(float(s.ros_win.mean()), 3),
                         playoffs=round(float(s.playoffs.mean()), 3))
                    for pl, pm in (('winning', team.prior_win_pct > 0.5),
                                   ('losing', team.prior_win_pct <= 0.5))
                    for wl, wm in (('won', team.w1_win == 1), ('lost', team.w1_win == 0))
                    for s in [team[pm & wm & team.prior_win_pct.notna()]]])

    # the model ladders come straight from fantasy.py rather than its printed table
    weekly = C._derived(C.load_weekly())
    models = {}
    for pos in ('QB', 'RB', 'WR', 'TE'):
        panel = C.build_panel(pos, weekly=weekly)
        out = {}
        for add, lab in ((False, 'all'), (True, 'snaps')):
            pv = Fa.points_vs_usage(panel, pos, add_snaps=add)
            if pv:
                n, r2 = pv
                out[lab] = dict(n=n, **{k: round(v, 3) for k, v in r2.items()})
        models[pos] = out

    blob = dict(
        meta=dict(first=C.FIRST_SEASON, last=C.LAST_SEASON, snap_first=C.SNAP_FIRST),
        signal=sig.to_dict('records'),
        asked=pd.DataFrame(ASKED, columns=['position', 'metric'])
                .merge(sig, on=['position', 'metric']).to_dict('records'),
        curves=curves, panic=panic, team=T, models=models,
        midweek={p: dict(w1=round(float(pred[pred.position == p].r.mean()), 3),
                         mid=round(float(pred[pred.position == p].r_midweek.mean()), 3))
                 for p in ('QB', 'RB', 'WR', 'TE')},
        overall=dict(
            opp=round(float(pred[pred.kind.isin(['volume', 'share', 'role'])].r.mean()), 3),
            eff=round(float(pred[pred.kind == 'rate'].r.mean()), 3),
            edge=round(float(pred.w1_edge.mean()), 3), pairs=int(len(pred))))
    json.dump(blob, open('report_data.json', 'w'), indent=1)
    print(f"report_data.json: {len(blob['signal'])} metrics, {T['n']} team-seasons")


if __name__ == "__main__":
    main()
