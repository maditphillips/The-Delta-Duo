"""Conditional cells inside a Week 1 snap-share band.

The question: among running backs who opened at 45-60% of snaps, does a Week 1
yards-per-carry above 5.0 tell you anything about the rest of the season?

A group on its own cannot answer that -- the band's own average would look the same
whatever the split. So every cell is reported against the complement inside the same
band (Week 1 YPC <= 5.0), with a confidence interval on the DIFFERENCE, which is
the actual test.

Two sampling notes that matter here:
  - Week 1 YPC needs a carry floor or one 20-yard run on two carries qualifies as
    10.0. Results are shown at three floors so the reader can see the sensitivity.
  - Rest-of-season YPC needs a carry floor too, and that floor quietly drops the
    backs who lost their job -- the most interesting outcome. So snap share and
    fantasy points are reported on the whole cell, YPC only on the qualifying
    subset, and the share of the cell that fails the floor is stated.

Written to BAND_CELLS.txt.
"""
import numpy as np
import pandas as pd
from scipy import stats
import common as C

BAND = (0.45, 0.60)
YPC_CUT = 5.0
W1_CARRY_FLOORS = (6, 8, 10)
ROS_CARRY_FLOOR = 40
BOOT = 10000
RNG = np.random.default_rng(20260910)


def ci_mean(x):
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 3:
        return dict(n=n, mean=np.nan, lo=np.nan, hi=np.nan, sd=np.nan, se=np.nan)
    m, sd = x.mean(), x.std(ddof=1)
    se = sd / np.sqrt(n)
    h = stats.t.ppf(0.975, n - 1) * se
    return dict(n=n, mean=m, lo=m - h, hi=m + h, sd=sd, se=se)


def ci_median(x):
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 5:
        return (np.nan, np.nan, np.nan)
    b = RNG.choice(x, size=(BOOT, len(x)), replace=True)
    med = np.median(b, axis=1)
    return (float(np.median(x)), float(np.percentile(med, 2.5)),
            float(np.percentile(med, 97.5)))


def diff_ci(a, b):
    """Welch difference in means, a - b."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    a, b = a[np.isfinite(a)], b[np.isfinite(b)]
    if len(a) < 3 or len(b) < 3:
        return dict(d=np.nan, lo=np.nan, hi=np.nan, t=np.nan, p=np.nan, dof=np.nan)
    t = stats.ttest_ind(a, b, equal_var=False)
    va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
    se = np.sqrt(va + vb)
    dof = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1))
    h = stats.t.ppf(0.975, dof) * se
    d = a.mean() - b.mean()
    return dict(d=d, lo=d - h, hi=d + h, t=float(t.statistic), p=float(t.pvalue), dof=dof)


def line(lab, c, pct=False, nd=3):
    if not np.isfinite(c["mean"]):
        return f"     {lab:<30} n={c['n']:>3}   too few to report"
    f = 100 if pct else 1
    u = "%" if pct else ""
    return (f"     {lab:<30} n={c['n']:>3}   mean {c['mean']*f:.{nd}f}{u}"
            f"   95% CI [{c['lo']*f:.{nd}f}, {c['hi']*f:.{nd}f}]{u}"
            f"   sd {c['sd']*f:.{nd}f}")


def main():
    weekly = C._derived(C.load_weekly())
    panel = C.build_panel("RB", weekly=weekly)
    panel = panel[(panel.season >= C.SNAP_FIRST) & panel.played_ros]
    panel = panel[np.isfinite(panel[["w1_snap_pct", "w1_yards_per_carry",
                                     "w1_carries", "ros_snap_pct"]]).all(axis=1)]

    print("=" * 100)
    print(f"RB WEEK 1 SNAP SHARE {BAND[0]:.0%}-{BAND[1]:.0%}, SPLIT BY WEEK 1 YARDS PER CARRY")
    print(f"nflverse {C.SNAP_FIRST}-{C.LAST_SEASON}; rest-of-season target excludes Week 1")
    print("=" * 100)

    band_all = panel[(panel.w1_snap_pct >= BAND[0]) & (panel.w1_snap_pct < BAND[1])]
    print(f"\nWhole band, before any YPC condition: n = {len(band_all)}")
    print(line("ROS snap share", ci_mean(band_all.ros_snap_pct), pct=True, nd=1))
    print(line("ROS PPR points/game", ci_mean(band_all.ros_fantasy_ppg_ppr), nd=2))

    for floor in W1_CARRY_FLOORS:
        band = band_all[band_all.w1_carries >= floor]
        hi = band[band.w1_yards_per_carry > YPC_CUT]
        lo = band[band.w1_yards_per_carry <= YPC_CUT]
        print(f"\n\n{'#'*100}")
        print(f"## Week 1 carries >= {floor}   band n = {len(band)}"
              f"   ({len(hi)} over {YPC_CUT} YPC, {len(lo)} at or under)")
        print(f"{'#'*100}")
        if len(hi) < 8:
            print("   too few over the YPC cut to report at this floor")
            continue

        print(f"\n   are the two groups matched on the thing we are holding fixed?")
        for lab, g in (("> 5.0 YPC", hi), ("<= 5.0 YPC", lo)):
            print(f"     {lab:<12} Week 1 snap share {g.w1_snap_pct.mean()*100:.1f}%"
                  f"   Week 1 carries {g.w1_carries.mean():.1f}"
                  f"   Week 1 YPC {g.w1_yards_per_carry.mean():.2f}"
                  f"   Week 1 PPR {g.w1_fantasy_ppg_ppr.mean():.1f}")

        # ---- rest-of-season snap share
        print(f"\n   REST-OF-SEASON SNAP SHARE")
        ch, cl = ci_mean(hi.ros_snap_pct), ci_mean(lo.ros_snap_pct)
        print(line("Week 1 YPC > 5.0", ch, pct=True, nd=1))
        print(line("Week 1 YPC <= 5.0", cl, pct=True, nd=1))
        d = diff_ci(hi.ros_snap_pct, lo.ros_snap_pct)
        print(f"     difference {d['d']*100:+.1f} pts   95% CI "
              f"[{d['lo']*100:+.1f}, {d['hi']*100:+.1f}]   t {d['t']:.2f}   p {d['p']:.3f}")
        m, ml, mh = ci_median(hi.ros_snap_pct)
        q = hi.ros_snap_pct.quantile([.1, .25, .5, .75, .9]).values
        print(f"     > 5.0 YPC group percentiles  p10 {q[0]:.2f}  p25 {q[1]:.2f}  "
              f"p50 {q[2]:.2f}  p75 {q[3]:.2f}  p90 {q[4]:.2f}"
              f"   (median 95% CI [{ml:.2f}, {mh:.2f}])")

        # ---- rest-of-season fantasy points
        print(f"\n   REST-OF-SEASON PPR POINTS PER GAME")
        ch, cl = ci_mean(hi.ros_fantasy_ppg_ppr), ci_mean(lo.ros_fantasy_ppg_ppr)
        print(line("Week 1 YPC > 5.0", ch, nd=2))
        print(line("Week 1 YPC <= 5.0", cl, nd=2))
        d = diff_ci(hi.ros_fantasy_ppg_ppr, lo.ros_fantasy_ppg_ppr)
        print(f"     difference {d['d']:+.2f} ppg   95% CI [{d['lo']:+.2f}, {d['hi']:+.2f}]"
              f"   t {d['t']:.2f}   p {d['p']:.3f}")
        m, ml, mh = ci_median(hi.ros_fantasy_ppg_ppr)
        q = hi.ros_fantasy_ppg_ppr.quantile([.1, .25, .5, .75, .9]).values
        print(f"     > 5.0 YPC group percentiles  p10 {q[0]:.1f}  p25 {q[1]:.1f}  "
              f"p50 {q[2]:.1f}  p75 {q[3]:.1f}  p90 {q[4]:.1f}"
              f"   (median 95% CI [{ml:.1f}, {mh:.1f}])")

        # ---- rest-of-season YPC, which needs its own floor
        hq = hi[hi.ros_den_yards_per_carry >= ROS_CARRY_FLOOR]
        lq = lo[lo.ros_den_yards_per_carry >= ROS_CARRY_FLOOR]
        print(f"\n   REST-OF-SEASON YARDS PER CARRY   (needs {ROS_CARRY_FLOOR}+ carries "
              f"after Week 1)")
        print(f"     dropped for too few carries: {len(hi)-len(hq)} of {len(hi)} in the "
              f"> 5.0 group ({(len(hi)-len(hq))/len(hi)*100:.0f}%), "
              f"{len(lo)-len(lq)} of {len(lo)} in the <= 5.0 group "
              f"({(len(lo)-len(lq))/len(lo)*100:.0f}%)")
        ch, cl = ci_mean(hq.ros_yards_per_carry), ci_mean(lq.ros_yards_per_carry)
        print(line("Week 1 YPC > 5.0", ch, nd=2))
        print(line("Week 1 YPC <= 5.0", cl, nd=2))
        d = diff_ci(hq.ros_yards_per_carry, lq.ros_yards_per_carry)
        print(f"     difference {d['d']:+.2f} y/c   95% CI [{d['lo']:+.2f}, {d['hi']:+.2f}]"
              f"   t {d['t']:.2f}   p {d['p']:.3f}")
        if len(hq) >= 5:
            m, ml, mh = ci_median(hq.ros_yards_per_carry)
            q = hq.ros_yards_per_carry.quantile([.1, .25, .5, .75, .9]).values
            print(f"     > 5.0 YPC group percentiles  p10 {q[0]:.2f}  p25 {q[1]:.2f}  "
                  f"p50 {q[2]:.2f}  p75 {q[3]:.2f}  p90 {q[4]:.2f}"
                  f"   (median 95% CI [{ml:.2f}, {mh:.2f}])")
            lg = panel[np.isfinite(panel.ros_yards_per_carry) &
                       (panel.ros_den_yards_per_carry >= ROS_CARRY_FLOOR)]
            print(f"     for reference, every qualifying RB {C.SNAP_FIRST}-{C.LAST_SEASON}: "
                  f"mean {lg.ros_yards_per_carry.mean():.2f}, "
                  f"sd {lg.ros_yards_per_carry.std():.2f} (n={len(lg)})")

        # ---- does YPC survive next to snap share inside the band?
        print(f"\n   REGRESSION INSIDE THE BAND (does Week 1 YPC add anything to Week 1 "
              f"snap share?)")
        for tgt, lab in (("ros_snap_pct", "ROS snap share"),
                         ("ros_fantasy_ppg_ppr", "ROS PPR ppg")):
            b = band[np.isfinite(band[[tgt, "w1_snap_pct", "w1_yards_per_carry"]]).all(axis=1)]
            if len(b) < 30:
                continue
            X = np.column_stack([np.ones(len(b)), C.z(b.w1_snap_pct),
                                 C.z(b.w1_yards_per_carry)])
            beta, *_ = np.linalg.lstsq(X, C.z(b[tgt]), rcond=None)
            resid = C.z(b[tgt]) - X @ beta
            dof = len(b) - 3
            s2 = float(resid @ resid) / dof
            se = np.sqrt(np.diag(np.linalg.pinv(X.T @ X)) * s2)
            t = beta / se
            p = 2 * stats.t.sf(np.abs(t), dof)
            print(f"     {lab:<18} beta(snap %) {beta[1]:+.3f} (p {p[1]:.3f})"
                  f"   beta(YPC) {beta[2]:+.3f} (p {p[2]:.3f})   n={len(b)}")

    print(f"\n\nAll intervals are 95%. Group differences use Welch's t (unequal variance).")
    print(f"Median intervals are {BOOT}-resample bootstrap percentile intervals.")


if __name__ == "__main__":
    main()
