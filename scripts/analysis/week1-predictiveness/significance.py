"""Significance tests for the Week 1 study.

Three separate questions, which the correlation tables alone do not answer:

1. Is r(Week 1 -> rest of season) distinguishable from zero?
   t = r * sqrt(n-2) / sqrt(1-r^2), two-sided, df = n-2.

2. Does Week 1 add anything ONCE LAST SEASON IS ALREADY IN THE MODEL? This is the
   question that matters, and it is a different test: the partial F on the Week 1
   term in ROS ~ Week1 + prior, F = (dR2/1) / ((1-R2_both)/(n-3)).
   Reported with the t on the standardised Week 1 coefficient, which is its root.

3. With 55 metrics tested, some small p-values are expected by chance, so both
   p-columns carry Benjamini-Hochberg q-values across the whole family.

Also prints, for every metric, the correlation from EACH of weeks 1-9 taken alone,
so Week 1 can be placed inside the ordinary week-to-week spread rather than
compared against a single averaged benchmark.

Written to SIGNIFICANCE.txt.
"""
import numpy as np
import pandas as pd
from scipy import stats
import common as C

WEEKS = range(1, 10)


def bh(p):
    """Benjamini-Hochberg q-values."""
    p = np.asarray(p, dtype=float)
    ok = np.isfinite(p)
    q = np.full_like(p, np.nan)
    v = p[ok]
    n = len(v)
    order = np.argsort(v)
    ranked = v[order]
    adj = ranked * n / (np.arange(n) + 1)
    adj = np.minimum.accumulate(adj[::-1])[::-1]
    out = np.empty(n)
    out[order] = np.minimum(adj, 1.0)
    q[ok] = out
    return q


def r_to_p(r, n):
    if not np.isfinite(r) or n < 5 or abs(r) >= 1:
        return np.nan
    t = r * np.sqrt(n - 2) / np.sqrt(1 - r * r)
    return float(2 * stats.t.sf(abs(t), n - 2))


def ols_full(y, X):
    """Coefficients, standard errors, t and p, plus R^2. X excludes the intercept."""
    X = np.column_stack([np.ones(len(y)), X])
    n, k = X.shape
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    ss_res = float(resid @ resid)
    ss_tot = float(((y - y.mean()) ** 2).sum())
    dof = n - k
    s2 = ss_res / dof
    xtx_inv = np.linalg.pinv(X.T @ X)
    se = np.sqrt(np.diag(xtx_inv) * s2)
    t = beta / se
    p = 2 * stats.t.sf(np.abs(t), dof)
    return dict(beta=beta, se=se, t=t, p=p, r2=1 - ss_res / ss_tot, n=n, dof=dof)


def per_week(p_pos, pos, metrics):
    """r for each of weeks 1-9 taken alone against the rest of that same season."""
    gate_min = C.W1_GATE[pos][1]
    rows = {m: {} for m, _ in metrics}
    for k in WEEKS:
        wk = C.aggregate(p_pos[p_pos.week == k], pos).add_prefix("a_")
        rest = C.aggregate(p_pos[p_pos.week != k], pos).add_prefix("b_")
        d = wk.join(rest, how="inner")
        d = d[d["a_" + C._gate_name(pos)] >= gate_min]
        d = d[d.b_games >= C.MIN_ROS_GAMES]
        for m, kind in metrics:
            a, b = d["a_" + m], d["b_" + m]
            ok = a.notna() & b.notna() & np.isfinite(a) & np.isfinite(b)
            if kind in ("rate", "role"):
                ok &= d["b_den_" + m].fillna(0) >= C.RATE_MIN_DEN[pos]
            rows[m][k] = (float(np.corrcoef(a[ok], b[ok])[0, 1]), int(ok.sum())) \
                if ok.sum() >= 30 else (np.nan, int(ok.sum()))
    return rows


def main():
    weekly = C._derived(C.load_weekly())
    recs, wk_recs = [], []

    for pos in ("QB", "RB", "WR", "TE"):
        p_pos = weekly[weekly.position == pos]
        panel = C.build_panel(pos, weekly=weekly)
        metrics = C.metric_list(pos)
        pw = per_week(p_pos, pos, metrics)

        for m, kind in metrics:
            x, y = C.pair(panel, m, kind, pos, "w1", "ros")
            if x is None or len(x) < 40:
                continue
            r = float(np.corrcoef(x, y)[0, 1])
            rec = dict(position=pos, metric=m, kind=kind, n=len(x), r=r,
                       p_r=r_to_p(r, len(x)))

            cols = ["w1_" + m, "ros_" + m, "prior_" + m]
            d = panel[panel.played_ros]
            if "w1_den_" + m in d:
                for pre in ("ros", "prior"):
                    d = d[d[pre + "_den_" + m].fillna(0) >= C.RATE_MIN_DEN[pos]]
            d = d[np.isfinite(d[cols]).all(axis=1)]
            if len(d) >= 60:
                fit1 = ols_full(C.z(d[cols[1]]), np.column_stack([C.z(d[cols[2]])]))
                fit2 = ols_full(C.z(d[cols[1]]),
                                np.column_stack([C.z(d[cols[0]]), C.z(d[cols[2]])]))
                dr2 = fit2["r2"] - fit1["r2"]
                F = (dr2 / 1) / ((1 - fit2["r2"]) / fit2["dof"])
                rec.update(n_j=len(d), r2_prior=fit1["r2"], r2_both=fit2["r2"], d_r2=dr2,
                           beta_w1=fit2["beta"][1], se_w1=fit2["se"][1],
                           t_w1=fit2["t"][1], p_w1=float(fit2["p"][1]),
                           F=F, p_F=float(stats.f.sf(F, 1, fit2["dof"])))
            recs.append(rec)

            vals = [pw[m][k][0] for k in WEEKS]
            others = [v for k, v in zip(WEEKS, vals) if k != 1 and np.isfinite(v)]
            if np.isfinite(vals[0]) and len(others) >= 5:
                wk_recs.append(dict(
                    position=pos, metric=m, r_wk1=vals[0], mean_other=float(np.mean(others)),
                    sd_other=float(np.std(others, ddof=1)),
                    min_other=float(np.min(others)), max_other=float(np.max(others)),
                    rank_of_wk1=int(sum(1 for v in others if v < vals[0]) + 1),
                    n_weeks=len(others) + 1,
                    z=(vals[0] - np.mean(others)) / np.std(others, ddof=1),
                    per_week=[None if not np.isfinite(v) else round(v, 3) for v in vals]))

    df = pd.DataFrame(recs)
    df["q_r"] = bh(df.p_r)
    df["q_w1"] = bh(df.p_w1)
    wk = pd.DataFrame(wk_recs)

    print("=" * 108)
    print("SIGNIFICANCE TESTS")
    print(f"nflverse regular seasons {C.FIRST_SEASON}-{C.LAST_SEASON}; "
          f"{len(df)} position-metric pairs tested")
    print("=" * 108)
    print("""
  r        Week 1 -> rest-of-season correlation
  p_r/q_r  is that r different from zero (q = Benjamini-Hochberg across all pairs)
  dR2      extra variance Week 1 explains AFTER last season is in the model
  t_w1     t on the standardised Week 1 coefficient in ROS ~ Week1 + prior
  p_w1/q_w1  does Week 1 add anything beyond last season (this is the real test)
""")
    for pos in ("QB", "RB", "WR", "TE"):
        d = df[df.position == pos].sort_values("d_r2", ascending=False)
        print(f"\n## {pos}")
        print(f"{'metric':<20}{'kind':<7}{'n':>5}{'r':>7}{'p_r':>10}{'q_r':>9}"
              f"{'| n':>7}{'dR2':>7}{'t_w1':>7}{'p_w1':>10}{'q_w1':>9}{'  verdict':<12}")
        print("-" * 108)
        for _, r in d.iterrows():
            def fp(v):
                if not np.isfinite(v):
                    return "     n/a"
                return "  <1e-16" if v < 1e-16 else f"{v:>8.2g}"
            q = r.get("q_w1", np.nan)
            v = ("adds signal" if np.isfinite(q) and q < .05 else "not distinguishable")
            print(f"{r.metric:<20}{r.kind:<7}{int(r.n):>5}{r.r:>7.3f}{fp(r.p_r):>10}"
                  f"{fp(r.q_r):>9}{int(r.get('n_j', 0)):>7}{r.get('d_r2', np.nan):>7.3f}"
                  f"{r.get('t_w1', np.nan):>7.2f}{fp(r.get('p_w1', np.nan)):>10}"
                  f"{fp(r.get('q_w1', np.nan)):>9}  {v:<12}")

    print("\n\n" + "=" * 108)
    print("WEEK 1 PLACED INSIDE THE WEEK-TO-WEEK SPREAD")
    print("Each of weeks 1-9 correlated on its own against the rest of that same season.")
    print("=" * 108)
    print(f"\n{'':<26}{'r from':>8}{'weeks 2-9 alone':>26}{'  wk1':>7}{'  z':>7}")
    print(f"{'metric':<26}{'week 1':>8}{'mean':>9}{'sd':>8}{'min':>8}{'max':>8}"
          f"{'rank':>7}{'':>7}")
    print("-" * 100)
    for pos in ("QB", "RB", "WR", "TE"):
        for _, r in wk[wk.position == pos].sort_values("r_wk1", ascending=False).iterrows():
            print(f"{pos+' '+r.metric:<26}{r.r_wk1:>8.3f}{r.mean_other:>9.3f}"
                  f"{r.sd_other:>8.3f}{r.min_other:>8.3f}{r.max_other:>8.3f}"
                  f"{str(r.rank_of_wk1)+'/'+str(r.n_weeks):>7}{r.z:>7.2f}")
    d = wk.r_wk1 - wk.mean_other
    tt = stats.ttest_1samp(d, 0)
    print(f"\nAcross all {len(wk)} metrics, Week 1's r minus the mean of weeks 2-9:")
    print(f"  mean difference {d.mean():+.4f}   sd {d.std(ddof=1):.4f}"
          f"   t({len(d)-1}) = {tt.statistic:.2f}   p = {tt.pvalue:.2g}")
    print(f"  metrics where Week 1 is the single lowest of the nine weeks: "
          f"{int((wk.rank_of_wk1 == 1).sum())} of {len(wk)}")
    print(f"  metrics where Week 1 is the single highest: "
          f"{int((wk.rank_of_wk1 == wk.n_weeks).sum())} of {len(wk)}")
    print(f"  metrics where Week 1 sits inside the weeks 2-9 range: "
          f"{int(((wk.r_wk1 >= wk.min_other) & (wk.r_wk1 <= wk.max_other)).sum())} "
          f"of {len(wk)}")
    print("  (these metrics share players and seasons, so they are not independent"
          " tests --")
    print("   the t above treats each metric as one observation and overstates its"
          " own precision)")

    df.to_csv("out_significance.csv", index=False)
    wk.to_csv("out_perweek.csv", index=False)


if __name__ == "__main__":
    main()
