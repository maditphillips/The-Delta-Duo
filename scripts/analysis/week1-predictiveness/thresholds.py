"""How good does he actually have to be? Breakout rates by metric threshold.

The logistic coefficients in outliers.py say which metrics matter but not where the
line is. This turns them into a lookup: among players who were drafted in a given
band and had a below-expectation Week 1, what share finished 10+ positional spots
ahead of their draft slot, broken out by where they landed on each metric.

Draft band is held fixed inside each table, so the base rate at the bottom is the
right comparison -- a bin beats the base rate or it does not.

Both windows are shown, because they are not close: Week 1 alone splits these
groups weakly, and weeks 2-4 splits them hard.

Sample sizes are small once a band and a bin are both applied, so every bin prints
its n and a Wilson interval on the rate. Bins whose interval covers the base rate
are not telling you anything.

Written to THRESHOLDS.txt.
"""
import numpy as np
import pandas as pd
from scipy import stats
import common as C
import outliers as O

BANDS = [(13, 40, "drafted 13-40"), (13, 60, "drafted 13-60"), (41, 999, "drafted 41+")]
CUTS = {
    "RB": [("snap_pct", "snap share", [0, .35, .45, .55, .65, 1.01], "pct"),
           ("rush_share", "share of team carries", [0, .35, .50, .65, 1.01], "pct"),
           ("carries", "carries", [0, 8, 12, 16, 99], "num"),
           ("touches", "touches", [0, 10, 14, 18, 99], "num"),
           ("yards_per_carry", "yards per carry", [0, 3.0, 4.0, 5.0, 99], "num"),
           ("fantasy_ppg_ppr", "PPR points", [0, 6, 10, 14, 99], "num")],
    "WR": [("target_share", "target share", [0, .12, .18, .24, 1.01], "pct"),
           ("snap_pct", "snap share", [0, .60, .75, .85, 1.01], "pct"),
           ("targets", "targets", [0, 4, 6, 9, 99], "num"),
           ("wopr", "WOPR", [0, .25, .40, .60, 9], "num"),
           ("air_yards", "air yards", [0, 30, 55, 85, 999], "num"),
           ("fantasy_ppg_ppr", "PPR points", [0, 5, 9, 14, 99], "num")],
}


def wilson(k, n, z=1.96):
    if n == 0:
        return np.nan, np.nan
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - h) / d, (c + h) / d


def fmt_edge(v, kind):
    if v in (0,):
        return "0"
    if v >= 99:
        return "+"
    return f"{v:.0%}" if kind == "pct" else (f"{v:g}")


def table(bad, prefix, pos, band_lab, base):
    print(f"\n     {'metric':<24}{'bin':<16}{'n':>5}{'broke out':>11}{'rate':>8}"
          f"{'95% interval':>18}{'  vs base':>10}")
    print("     " + "-" * 92)
    for m, lab, edges, kind in CUTS[pos]:
        col = prefix + m
        if col not in bad:
            continue
        sub = bad[np.isfinite(bad[col])]
        if len(sub) < 40:
            continue
        first = True
        for lo, hi in zip(edges[:-1], edges[1:]):
            b = sub[(sub[col] >= lo) & (sub[col] < hi)]
            if len(b) < 12:
                continue
            k, n = int(b.out.sum()), len(b)
            wl, wh = wilson(k, n)
            binlab = f"{fmt_edge(lo, kind)}-{fmt_edge(hi, kind)}" if hi < 99 \
                else f"{fmt_edge(lo, kind)}+"
            mark = "  ++" if wl > base else ("  --" if wh < base else "")
            print(f"     {lab if first else '':<24}{binlab:<16}{n:>5}{k:>11}"
                  f"{k/n*100:>7.0f}%{f'[{wl*100:.0f}, {wh*100:.0f}]%':>18}{mark:>10}")
            first = False
    print(f"     {'BASE RATE, ' + band_lab:<45}{base*100:>7.0f}%")
    print("     ++ / -- marks a bin whose interval clears the base rate entirely")


def main():
    weekly = C._derived(C.load_weekly())
    import adp as A
    ecr = A.ecr_ranks(C.load_games())
    print("=" * 104)
    print("HOW GOOD DOES HE HAVE TO BE? BREAKOUT RATES BY THRESHOLD")
    print(f"Among players with a below-expectation Week 1. Outlier = finished "
          f"{O.OUTLIER_GAIN}+ spots")
    print("ahead of draft slot. Draft slot stand-in: prior-season positional finish, "
          f"{C.FIRST_SEASON}-{C.LAST_SEASON}.")
    print("=" * 104)

    for pos in ("RB", "WR"):
        d = O.panel(pos, weekly, ecr).copy()
        d["sur"] = O.surprise(d, "prior_rank")
        d = d[np.isfinite(d[["prior_rank", "final_rank", "sur"]]).all(axis=1)]
        d["out"] = ((d.prior_rank - d.final_rank) >= O.OUTLIER_GAIN).astype(float)
        bad_all = d[d.sur <= 0]
        for lo, hi, band_lab in BANDS:
            bad = bad_all[(bad_all.prior_rank >= lo) & (bad_all.prior_rank <= hi)]
            if len(bad) < 60:
                continue
            base = float(bad.out.mean())
            print(f"\n\n{'#'*104}")
            print(f"## {pos}, {band_lab}, bad Week 1   —   {len(bad)} players, "
                  f"{int(bad.out.sum())} broke out ({base*100:.0f}%)")
            print(f"{'#'*104}")
            print("\n   WHAT HE DID IN WEEK 1")
            table(bad, "w1_", pos, band_lab, base)
            print("\n   WHAT HE DID IN WEEKS 2-4")
            table(bad, "e4_", pos, band_lab, base)

    print("\n\n" + "=" * 104)
    print("THE SAME QUESTION AS A SINGLE NUMBER")
    print("=" * 104)
    print("Best single threshold per metric: the cut that maximises the breakout rate")
    print("above it, requiring at least 30 players on the high side.")
    print("")
    print("READ THESE LIFTS AS AN UPPER BOUND. Twelve candidate cuts are searched per")
    print("metric and the best one kept, so the winning lift is optimistically biased --")
    print("the same search on noise would return something above 1.0. A lift near 1.0")
    print("after that search means the metric has no usable threshold at all. A single")
    print("cut also cannot express a middle-band effect, which is what the RB Week 1")
    print("snap-share bins look like above (55-65% best, 65%+ worse).")
    for pos in ("RB", "WR"):
        d = O.panel(pos, weekly, ecr).copy()
        d["sur"] = O.surprise(d, "prior_rank")
        d = d[np.isfinite(d[["prior_rank", "final_rank", "sur"]]).all(axis=1)]
        d["out"] = ((d.prior_rank - d.final_rank) >= O.OUTLIER_GAIN).astype(float)
        bad = d[(d.sur <= 0) & (d.prior_rank >= 13) & (d.prior_rank <= 60)]
        base = float(bad.out.mean())
        print(f"\n   {pos}, drafted 13-60, bad Week 1   (n={len(bad)}, "
              f"base rate {base*100:.0f}%)")
        print(f"     {'window':<10}{'metric':<24}{'threshold':>12}{'n above':>9}"
              f"{'rate above':>12}{'rate below':>12}{'lift':>7}")
        for prefix, wlab in (("w1_", "week 1"), ("e4_", "weeks 2-4")):
            rows = []
            for m, lab, edges, kind in CUTS[pos]:
                col = prefix + m
                if col not in bad:
                    continue
                sub = bad[np.isfinite(bad[col])]
                if len(sub) < 60:
                    continue
                best = None
                for q in np.arange(.30, .90, .05):
                    thr = sub[col].quantile(q)
                    hi_g = sub[sub[col] >= thr]
                    lo_g = sub[sub[col] < thr]
                    if len(hi_g) < 30 or len(lo_g) < 30:
                        continue
                    r = hi_g.out.mean()
                    if best is None or r > best[0]:
                        best = (r, thr, len(hi_g), lo_g.out.mean())
                if best:
                    rows.append((best[0] / base, lab, best[1], best[2], best[0], best[3],
                                 kind))
            for lift, lab, thr, n_hi, r_hi, r_lo, kind in sorted(rows, reverse=True):
                t = f"{thr:.0%}" if kind == "pct" else f"{thr:.1f}"
                print(f"     {wlab:<10}{lab:<24}{'>= ' + t:>12}{n_hi:>9}"
                      f"{r_hi*100:>11.0f}%{r_lo*100:>11.0f}%{lift:>7.2f}x")


if __name__ == "__main__":
    main()
