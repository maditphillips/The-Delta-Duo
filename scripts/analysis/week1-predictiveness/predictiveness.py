"""How much does one Week 1 game tell you about the rest of the season?

For every position and metric this prints, side by side:

  r(W1 -> ROS)      the raw correlation everyone quotes
  r(prior -> ROS)   what last season alone already told you
  R2 both / dR2     what Week 1 adds once last season is in the model
  beta_W1           standardized weight Week 1 earns in that model
  r(mid-week)       the same test run on weeks 2-9 instead of Week 1,
                    which separates "Week 1 is special" from "one game is one game"

Rate metrics are pooled (sum/sum) and need a minimum rest-of-season denominator;
volume metrics are per game. Written to PREDICTIVENESS.txt.
"""
import sys
import numpy as np
import pandas as pd
import common as C

MIDWEEKS = range(2, 10)


def midweek_benchmark(p_pos, pos, metrics):
    """corr(week k, mean of the season's other weeks), averaged over k=2..9."""
    gate_col, gate_min = C.W1_GATE[pos]
    acc = {m: [] for m, _ in metrics}
    for k in MIDWEEKS:
        wk = C.aggregate(p_pos[p_pos.week == k], pos).add_prefix("a_")
        rest = C.aggregate(p_pos[p_pos.week != k], pos).add_prefix("b_")
        d = wk.join(rest, how="inner")
        d = d[d["a_" + C._gate_name(pos)] >= gate_min]
        d = d[d.b_games >= C.MIN_ROS_GAMES]
        for m, kind in metrics:
            a, b = d["a_" + m], d["b_" + m]
            ok = a.notna() & b.notna()
            if "den_" + m in rest.columns.str.replace("b_", "", regex=False).tolist():
                ok &= d["b_den_" + m].fillna(0) >= C.RATE_MIN_DEN[pos]
            if ok.sum() >= 30:
                acc[m].append(np.corrcoef(a[ok], b[ok])[0, 1])
    return {m: (float(np.mean(v)) if v else np.nan) for m, v in acc.items()}


def row(panel, pos, metric, kind):
    x, y = C.pair(panel, metric, kind, pos, "w1", "ros")
    base = C.corr(x, y)

    # same comparison restricted to players who have a prior season on file
    d = panel[panel.played_ros].copy()
    cols = ["w1_" + metric, "ros_" + metric, "prior_" + metric]
    if any(c not in d for c in cols):
        return None
    m = d[cols].notna().all(axis=1)
    if "w1_den_" + metric in d:
        for pre, floor in (("w1", 0), ("ros", C.RATE_MIN_DEN[pos]), ("prior", C.RATE_MIN_DEN[pos])):
            c = pre + "_den_" + metric
            if c in d:
                m &= d[c].fillna(0) >= floor
    dd = d.loc[m, cols]
    out = dict(metric=metric, kind=kind, **base)
    if len(dd) >= 40:
        w1, ros, pri = (C.z(dd[c]) for c in cols)
        _, r2_w1 = C.ols(ros, np.column_stack([w1]))
        _, r2_pri = C.ols(ros, np.column_stack([pri]))
        beta, r2_both = C.ols(ros, np.column_stack([w1, pri]))
        out.update(n_prior=len(dd), r_prior=float(np.corrcoef(pri, ros)[0, 1]),
                   r2_prior=r2_pri, r2_w1_sub=r2_w1, r2_both=r2_both,
                   d_r2=r2_both - r2_pri, beta_w1=beta[1], beta_prior=beta[2])
    else:
        out.update(n_prior=len(dd), r_prior=np.nan, r2_prior=np.nan, r2_w1_sub=np.nan,
                   r2_both=np.nan, d_r2=np.nan, beta_w1=np.nan, beta_prior=np.nan)

    # rookies / no prior line: Week 1 is all you have
    nop = panel[panel.played_ros & panel["prior_" + metric].isna()]
    xr, yr = C.pair(nop, metric, kind, pos, "w1", "ros")
    out["r_norookieprior"] = C.corr(xr, yr)["r"]
    out["n_noprior"] = C.corr(xr, yr)["n"]
    return out


def unconditional(panel, pos):
    """Fantasy reality: weeks missed count as zero, so injury risk stays in the number."""
    rows = []
    full_weeks = panel.season.map(lambda s: 15 if s < 2021 else 16)  # games left after wk 1
    for metric in [m for m, k in C.metric_list(pos) if k == "volume"]:
        d = panel.copy()
        d["ros_total"] = d["ros_" + metric].fillna(0) * d.ros_games
        d["ros_per_slot"] = d.ros_total / full_weeks
        m = d.ros_per_slot.notna() & d["w1_" + metric].notna()
        rows.append(dict(metric=metric, **C.corr(d.loc[m, "w1_" + metric], d.loc[m, "ros_per_slot"])))
    return pd.DataFrame(rows)


def main():
    weekly = C._derived(C.load_weekly())
    print("=" * 100)
    print("WEEK 1 PREDICTIVENESS OF THE REST OF THE SEASON")
    print(f"nflverse regular seasons {C.FIRST_SEASON}-{C.LAST_SEASON}"
          f"  (snap share {C.SNAP_FIRST}+)")
    print("=" * 100)

    all_rows = {}
    for pos in ("QB", "RB", "WR", "TE"):
        p_pos = weekly[weekly.position == pos]
        panel = C.build_panel(pos, weekly=weekly)
        metrics = C.metric_list(pos)
        mid = midweek_benchmark(p_pos, pos, metrics)

        rows = [r for r in (row(panel, pos, m, k) for m, k in metrics) if r]
        df = pd.DataFrame(rows)
        df["r_midweek"] = df.metric.map(mid)
        df["w1_edge"] = df.r - df.r_midweek
        all_rows[pos] = df

        gate = C.W1_GATE[pos]
        print(f"\n\n{'#'*100}\n## {pos}   Week 1 gate: {gate[0]} >= {gate[1]}"
              f"   player-seasons: {len(panel)}  (played >= {C.MIN_ROS_GAMES} more games:"
              f" {int(panel.played_ros.sum())})\n{'#'*100}")
        print(f"\n{'metric':<20}{'type':<8}{'n':>5}{'r':>8}{'rho':>7}{'R2':>7}"
              f"{'| r_mid':>9}{'edge':>7}{'| r_prior':>10}{'R2pri':>7}{'R2both':>8}{'dR2':>7}"
              f"{'| bW1':>8}{'bPri':>7}{'| r_rook':>10}{'n':>5}")
        print("-" * 122)
        for _, r in df.sort_values(["kind", "r"], ascending=[True, False]).iterrows():
            print(f"{r.metric:<20}{r.kind:<8}{int(r.n):>5}{C.fmt(r.r):>8}{C.fmt(r.rho):>7}"
                  f"{C.fmt(r.r2):>7}{C.fmt(r.r_midweek):>9}{C.fmt(r.w1_edge):>7}"
                  f"{C.fmt(r.r_prior):>10}{C.fmt(r.r2_prior):>7}{C.fmt(r.r2_both):>8}"
                  f"{C.fmt(r.d_r2):>7}{C.fmt(r.beta_w1):>8}{C.fmt(r.beta_prior):>7}"
                  f"{C.fmt(r.r_norookieprior):>10}{int(r.n_noprior):>5}")

        u = unconditional(panel, pos)
        print(f"\n  same test with missed weeks counted as zero (what a fantasy roster feels):")
        for _, r in u.iterrows():
            base = df[df.metric == r.metric].r
            b = float(base.iloc[0]) if len(base) else np.nan
            print(f"    {r.metric:<22}n={int(r.n):>5}  r={C.fmt(r.r)}  "
                  f"(conditional on playing: {C.fmt(b)}, diff {C.fmt(r.r - b)})")

    # headline: volume vs efficiency
    print(f"\n\n{'='*100}\nSUMMARY: OPPORTUNITY vs EFFICIENCY\n{'='*100}")
    print(f"{'':<6}{'mean r, opportunity/role':>26}{'mean r, rate/efficiency':>26}{'ratio':>8}")
    for pos, df in all_rows.items():
        v = df[df.kind.isin(("volume", "share", "role"))].r.mean()
        e = df[df.kind == "rate"].r.mean()
        print(f"{pos:<6}{v:>24.3f}{e:>26.3f}{v/e if e else np.nan:>8.2f}")
    pd.concat([d.assign(position=p) for p, d in all_rows.items()]) \
        .to_csv("out_predictiveness.csv", index=False)


if __name__ == "__main__":
    main()
