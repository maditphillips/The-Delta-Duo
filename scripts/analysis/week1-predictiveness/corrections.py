"""Two corrections to the outlier and draft-tier tables.

1. MULTIPLE COMPARISONS. The breakout-predictor tables ranked 6-10 metrics per
   position with no correction, so a p just under 0.05 in a list that long is not
   evidence of much. Benjamini-Hochberg q-values are added within each position's
   own family of tests, which is what decides whether a metric stays.

2. THE TIER GAPS ARE NOT ON A COMMON SCALE. The draft-tier tables report the
   good-minus-bad Week 1 gap in points per game. But a top-5 tier averages ~13-19
   ppg and a 41+ tier averages ~3-8, so the same 2 ppg gap is a small effect in one
   tier and a large one in the other. That is why the ppg gaps and the log-rank
   interaction appeared to disagree at TE. The gap is re-expressed as a share of the
   tier's own mean and in units of the tier's own standard deviation, which puts
   every tier on a common footing.

Written to CORRECTIONS.txt.
"""
import numpy as np
import pandas as pd
from scipy import stats
import common as C
import outliers as O
import adp as A

POS = ("RB", "WR", "TE", "QB")


def bh(p):
    p = np.asarray(p, float)
    ok = np.isfinite(p)
    q = np.full_like(p, np.nan)
    v = p[ok]
    n = len(v)
    order = np.argsort(v)
    adj = v[order] * n / (np.arange(n) + 1)
    adj = np.minimum.accumulate(adj[::-1])[::-1]
    out = np.empty(n)
    out[order] = np.minimum(adj, 1.0)
    q[ok] = out
    return q


def logit_beta(sub, col, out_col="out"):
    import statsmodels.api as sm
    sub = sub[np.isfinite(sub[[col, "prior_rank"]]).all(axis=1)]
    if len(sub) < 60 or sub[out_col].nunique() < 2:
        return np.nan, np.nan, 0
    lr = np.log(sub.prior_rank.values)
    X = np.column_stack([np.ones(len(sub)), (lr - lr.mean()) / lr.std(), C.z(sub[col])])
    try:
        f = sm.Logit(sub[out_col].values, X).fit(disp=0)
        return float(f.params[2]), float(f.pvalues[2]), len(sub)
    except Exception:
        return np.nan, np.nan, len(sub)


def main():
    weekly = C._derived(C.load_weekly())
    ecr = A.ecr_ranks(C.load_games())
    P = {pos: O.panel(pos, weekly, ecr) for pos in POS}

    print("=" * 96)
    print("CORRECTION 1: BREAKOUT PREDICTORS WITH MULTIPLE COMPARISONS ACCOUNTED FOR")
    print("=" * 96)
    print("   q is Benjamini-Hochberg within that position's own list of metrics.")
    print("   A metric earns its place only if q < 0.05.")
    for prefix, plab in (("w1_", "WEEK 1"), ("e4_", "WEEKS 2-4")):
        print(f"\n\n## {plab}")
        for pos in POS:
            d = P[pos].copy()
            d["sur"] = O.surprise(d, "prior_rank")
            d = d[np.isfinite(d[["prior_rank", "final_rank", "sur"]]).all(axis=1)]
            d["out"] = ((d.prior_rank - d.final_rank) >= O.OUTLIER_GAIN).astype(float)
            bad = d[d.sur <= 0]
            if len(bad) < 80:
                continue
            rows = []
            for m, lab in O.CANDS[pos].__iter__():
                col = prefix + m
                if col not in bad:
                    continue
                b, p, n = logit_beta(bad, col)
                if np.isfinite(b):
                    rows.append(dict(metric=lab, beta=b, p=p, n=n))
            if not rows:
                continue
            t = pd.DataFrame(rows)
            t["q"] = bh(t.p)
            t = t.sort_values("p")
            print(f"\n   {pos}   ({len(t)} metrics tested, n={int(t.n.max())})")
            print(f"     {'metric':<26}{'beta':>8}{'p':>11}{'q (BH)':>11}{'  verdict':<18}")
            for _, r in t.iterrows():
                v = "holds up" if r.q < .05 else ("borderline" if r.q < .10 else "drops out")
                print(f"     {r.metric:<26}{r.beta:>+8.3f}{r.p:>11.3g}{r.q:>11.3g}  {v:<18}")

    print("\n\n" + "=" * 96)
    print("CORRECTION 2: DRAFT-TIER GAPS ON A COMMON SCALE")
    print("=" * 96)
    print("   'gap ppg' is the raw good-minus-bad Week 1 difference, as reported before.")
    print("   'as % of tier' divides it by that tier's own mean ppg.")
    print("   'in tier sd' divides it by that tier's own standard deviation in ROS ppg.")
    print("   The last two are the ones that can be compared across tiers.")
    for rank_col, span in (("adp_rank", "preseason ECR 2020-2025"),
                           ("prior_rank", "prior finish 1999-2025")):
        print(f"\n\n## {span}")
        print(f"   {'pos':<5}{'tier':<9}{'n':>5}{'tier mean ppg':>15}{'gap ppg':>10}"
              f"{'as % of tier':>15}{'in tier sd':>13}")
        print("   " + "-" * 72)
        for pos in POS:
            d = P[pos].copy()
            if rank_col == "adp_rank":
                d = d[d.season >= 2020]
            for lo, hi, lab in A.TIERS:
                b = d[(d[rank_col] >= lo) & (d[rank_col] <= hi)]
                b = b[np.isfinite(b[["ros_ppg", "w1_pts"]]).all(axis=1)]
                if len(b) < 25:
                    continue
                med = b.w1_pts.median()
                h, l = b[b.w1_pts > med].ros_ppg, b[b.w1_pts <= med].ros_ppg
                gap = h.mean() - l.mean()
                sd = b.ros_ppg.std(ddof=1)
                print(f"   {pos:<5}{lab:<9}{len(b):>5}{b.ros_ppg.mean():>15.2f}"
                      f"{gap:>+10.2f}{gap/b.ros_ppg.mean()*100:>14.0f}%"
                      f"{gap/sd:>+13.2f}")
            print()

    print("\n## WHAT CORRECTION 2 DOES TO THE READING, POSITION BY POSITION")
    print("   WR is the only position where scaling leaves the pattern intact under both")
    print("   rank measures: the gap in tier-sd units climbs from +0.02 at the top to")
    print("   +0.44 at 41+ under ECR, and +0.27 to +0.60 under the long-history proxy.")
    print("   RB holds under ECR (-0.25 to +0.51) but goes flat under the proxy (+0.69")
    print("   at the top, +0.56 at 41+), so the RB result rests on the thinner sample.")
    print("   QB is mixed: it climbs to the 13-24 tier then falls back at 25-40.")
    print("   TE does not resolve. Its raw ppg gap is largest at the top; in tier-sd")
    print("   units under ECR it also runs highest at the top (+0.60, +0.67) and lowest")
    print("   at 41+ (+0.25); but under the long-history proxy the same column runs the")
    print("   other way (+0.54 at the top, +0.67 at 41+). Three views, three answers, on")
    print("   27 to 178 players per cell. Nothing about the TE tier pattern is settled")
    print("   here, and its log-rank interaction is the weakest of the four (p = 0.042).")
    print("\n   The honest summary: scaled to each tier's own spread, the effect is well")
    print("   established at WR, likely at RB, unresolved at QB and TE. In raw points")
    print("   per game the split looks starker than that, because the later tiers score")
    print("   so much less that the same gap is a bigger share of their output.")


if __name__ == "__main__":
    main()
