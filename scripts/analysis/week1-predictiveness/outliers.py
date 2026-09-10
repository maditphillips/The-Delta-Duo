"""What separates a good Week 1 from a bad one, and what predicts the breakouts?

Three things, in order:

1. HOW "GOOD WEEK 1" IS DEFINED, AND WHETHER IT MATTERS. The ADP tables split each
   draft tier at its own median Week 1 score -- a relative-to-tier definition, not a
   relative-to-the-player definition. The alternative is to score each player against
   what someone at HIS exact draft slot typically puts up in Week 1, and split on
   that residual. Both are run here so the difference is visible rather than assumed.

2. OUTLIERS. A player finishes well ahead of his draft slot. Base rates by tier,
   and how many of those outliers had a bad Week 1.

3. WHAT PREDICTS THEM. Among players who had a BAD Week 1, which Week 1 numbers
   separate the ones who still broke out?

   A raw AUC is useless here, and the first version of this script produced one.
   Outlier is defined relative to draft slot, so a late-round player has far more
   room to gain 10 spots than a mid-round one -- and late-round players also have
   lower Week 1 usage. Every metric therefore came back BELOW 0.50, saying only that
   outliers were drafted later. Draft slot has to be held fixed. Two ways here: an
   AUC computed inside a single draft tier, and a logistic model carrying log(draft
   slot) alongside the metric. The same is then run on weeks 2-4.

   Finally, because a breakout is often a teammate's job coming free rather than
   anything the player did, the change in his position-mates' snap share is measured
   directly and reported alongside.

Written to OUTLIERS.txt.
"""
import numpy as np
import pandas as pd
from scipy import stats
import common as C

POS = ("RB", "WR", "TE", "QB")
TIERS = [(1, 5, "top 5"), (6, 12, "6-12"), (13, 24, "13-24"),
         (25, 40, "25-40"), (41, 999, "41+")]
OUTLIER_GAIN = 10          # finished this many positional spots better than drafted
MIN_ROS_GAMES = 4


def panel(pos, weekly, ecr):
    p = weekly[weekly.position == pos]
    bp = C.build_panel(pos, weekly=weekly)
    base = bp[["player_id", "season", "player_display_name", "ros_games", "played_ros"]
              + [c for c in bp.columns if c.startswith("w1_")]]

    # weeks 2-4, the "what do I watch next" window
    e = C.aggregate(p[(p.week >= 2) & (p.week <= 4)], pos).add_prefix("e4_").reset_index()

    f = p.groupby(["player_id", "season"])
    tot = pd.DataFrame(dict(full_pts=f.fantasy_points_ppr.sum(),
                            full_games=f.size())).reset_index()
    w1p = p[p.week == 1].groupby(["player_id", "season"]).fantasy_points_ppr.sum() \
           .rename("w1_pts").reset_index()
    r = p[p.week >= 2].groupby(["player_id", "season"])
    ros = pd.DataFrame(dict(ros_pts=r.fantasy_points_ppr.sum(),
                            ros_g=r.size())).reset_index()

    d = base.merge(w1p, on=["player_id", "season"]).merge(tot, on=["player_id", "season"]) \
            .merge(ros, on=["player_id", "season"], how="left") \
            .merge(e, on=["player_id", "season"], how="left")
    d["ros_ppg"] = np.where(d.ros_g > 0, d.ros_pts / d.ros_g, 0.0)
    d["full_ppg"] = d.full_pts / d.full_games
    d["final_rank"] = d.groupby("season").full_pts.rank(ascending=False, method="min")

    # prior-season positional finish, the long-history stand-in for a draft slot
    pr = p.groupby(["player_id", "season"]).agg(
        pp=("fantasy_points_ppr", "sum"), pg=("fantasy_points_ppr", "size")).reset_index()
    pr = pr[pr.pg >= 6]
    pr["prior_ppg"] = pr.pp / pr.pg
    pr["prior_rank"] = pr.groupby("season").prior_ppg.rank(ascending=False, method="min")
    pr["season"] = pr.season + 1
    d = d.merge(pr[["player_id", "season", "prior_rank"]], on=["player_id", "season"],
                how="left")
    d = d.merge(ecr[ecr.pos == pos][["season", "player_id", "adp_rank"]],
                on=["season", "player_id"], how="left")

    # how much snap share did his position-mates give up after Week 1?
    s = pd.read_parquet(f"{C.HERE}/snaps.parquet")
    s = s[(s.game_type == "REG") & s.offense_snaps.notna()]
    cw = pd.read_parquet(f"{C.HERE}/players.parquet")
    cw = cw[cw.pfr_id.notna()].drop_duplicates("pfr_id")[["gsis_id", "pfr_id"]]
    s = s.merge(cw, left_on="pfr_player_id", right_on="pfr_id", how="left")
    s = s[s.gsis_id.notna()].rename(columns={"gsis_id": "player_id"})
    grp = ["RB", "FB"] if pos == "RB" else [pos]
    s = s[s.position.isin(grp)]
    tw1 = s[s.week == 1].groupby(["season", "team"]).offense_pct.sum().rename("t_w1")
    tros = s[s.week >= 2].groupby(["season", "team", "week"]).offense_pct.sum() \
            .groupby(level=[0, 1]).mean().rename("t_ros")
    own1 = s[s.week == 1].set_index(["season", "player_id"])[["team", "offense_pct"]]
    ownr = s[s.week >= 2].groupby(["season", "player_id"]).offense_pct.mean().rename("own_ros")
    o = own1.join(ownr, how="inner").reset_index()
    o = o.merge(tw1, on=["season", "team"]).merge(tros, on=["season", "team"])
    o["mates_w1"] = o.t_w1 - o.offense_pct
    o["mates_ros"] = o.t_ros - o.own_ros
    o["mates_delta"] = o.mates_ros - o.mates_w1
    d = d.merge(o[["season", "player_id", "mates_w1", "mates_ros", "mates_delta"]],
                on=["season", "player_id"], how="left")
    return d[d.ros_games >= MIN_ROS_GAMES]


def surprise(d, rank_col):
    """Week 1 points minus what a player at that draft slot typically scores."""
    m = np.isfinite(d[[rank_col, "w1_pts"]]).all(axis=1)
    x = np.log(d.loc[m, rank_col].values)
    y = d.loc[m, "w1_pts"].values
    X = np.column_stack([np.ones(len(x)), x, x ** 2])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    out = pd.Series(np.nan, index=d.index)
    out[m] = y - X @ beta
    return out


def auc(pos_vals, neg_vals):
    a = np.asarray(pos_vals, float)
    b = np.asarray(neg_vals, float)
    a, b = a[np.isfinite(a)], b[np.isfinite(b)]
    if len(a) < 8 or len(b) < 8:
        return np.nan, np.nan, len(a), len(b)
    u = stats.mannwhitneyu(a, b, alternative="two-sided")
    return float(u.statistic / (len(a) * len(b))), float(u.pvalue), len(a), len(b)


CANDS = {
    "RB": [("snap_pct", "snap share"), ("rush_share", "share of team carries"),
           ("target_share", "target share"), ("carries", "carries"),
           ("targets", "targets"), ("touches", "touches"),
           ("yards_per_carry", "yards per carry"), ("fantasy_ppg_ppr", "PPR points")],
    "WR": [("snap_pct", "snap share"), ("target_share", "target share"),
           ("air_yards_share", "air yards share"), ("wopr", "WOPR"),
           ("targets", "targets"), ("air_yards", "air yards"), ("adot", "aDOT"),
           ("yards_per_target", "yards per target"), ("catch_rate", "catch rate"),
           ("fantasy_ppg_ppr", "PPR points")],
    "TE": [("snap_pct", "snap share"), ("target_share", "target share"),
           ("air_yards_share", "air yards share"), ("targets", "targets"),
           ("adot", "aDOT"), ("fantasy_ppg_ppr", "PPR points")],
    "QB": [("pass_attempts", "pass attempts"), ("qb_carries", "rush attempts"),
           ("completion_pct", "completion %"), ("cpoe", "CPOE"),
           ("epa_per_pass", "EPA per pass"), ("fantasy_ppg", "fantasy points")],
}


def main():
    weekly = C._derived(C.load_weekly())
    import adp as A
    ecr = A.ecr_ranks(C.load_games())
    P = {pos: panel(pos, weekly, ecr) for pos in POS}

    print("=" * 100)
    print("DEFINING A GOOD WEEK 1, AND WHAT PREDICTS THE OUTLIERS")
    print("=" * 100)

    # ---------------- 1. two definitions of a bad Week 1
    print("\n\n## 1. TWO WAYS TO CALL A WEEK 1 BAD")
    print("   A: below the median Week 1 score of his own draft tier (what the earlier")
    print("      tables used -- relative to the tier, across the board)")
    print("   B: below what a player at his EXACT draft slot typically scores in Week 1")
    print("      (a residual off a quadratic in log rank -- relative to expectation)")
    for rank_col, span in (("adp_rank", "preseason ECR 2020-2025"),
                           ("prior_rank", "prior finish 1999-2025")):
        print(f"\n   --- {span} ---")
        print(f"   {'pos':<5}{'tier':<9}{'n':>5}"
              f"{'A: gap ppg':>13}{'95% int':>17}{'B: gap ppg':>13}{'95% int':>17}")
        print("   " + "-" * 79)
        for pos in POS:
            d = P[pos].copy()
            if rank_col == "adp_rank":
                d = d[d.season >= 2020]
            d["sur"] = surprise(d, rank_col)
            for lo, hi, lab in TIERS:
                b = d[(d[rank_col] >= lo) & (d[rank_col] <= hi)]
                b = b[np.isfinite(b[["ros_ppg", "w1_pts", "sur"]]).all(axis=1)]
                if len(b) < 25:
                    continue
                row = [pos, lab, len(b)]
                for col in ("w1_pts", "sur"):
                    med = b[col].median()
                    h, l = b[b[col] > med].ros_ppg, b[b[col] <= med].ros_ppg
                    g = h.mean() - l.mean()
                    se = np.sqrt(h.var(ddof=1) / len(h) + l.var(ddof=1) / len(l))
                    row += [g, 1.96 * se]
                print(f"   {row[0]:<5}{row[1]:<9}{row[2]:>5}{row[3]:>+13.2f}"
                      f"{f'[{row[3]-row[4]:+.2f},{row[3]+row[4]:+.2f}]':>17}"
                      f"{row[5]:>+13.2f}{f'[{row[5]-row[6]:+.2f},{row[5]+row[6]:+.2f}]':>17}")

    # ---------------- 2. outlier base rates
    print(f"\n\n## 2. OUTLIERS: FINISHED {OUTLIER_GAIN}+ POSITIONAL SPOTS AHEAD OF DRAFT SLOT")
    for rank_col, span in (("adp_rank", "preseason ECR 2020-2025"),
                           ("prior_rank", "prior finish 1999-2025")):
        print(f"\n   --- {span} ---")
        print(f"   {'pos':<5}{'tier':<9}{'n':>5}{'outliers':>11}{'rate':>8}"
              f"{'of those, had a bad wk1':>26}")
        print("   " + "-" * 65)
        for pos in POS:
            d = P[pos].copy()
            if rank_col == "adp_rank":
                d = d[d.season >= 2020]
            d["sur"] = surprise(d, rank_col)
            d = d[np.isfinite(d[[rank_col, "final_rank", "sur"]]).all(axis=1)]
            d["out"] = (d[rank_col] - d.final_rank) >= OUTLIER_GAIN
            for lo, hi, lab in TIERS:
                b = d[(d[rank_col] >= lo) & (d[rank_col] <= hi)]
                if len(b) < 25 or b.out.sum() < 5:
                    continue
                bad = b[b.out & (b.sur <= 0)]
                print(f"   {pos:<5}{lab:<9}{len(b):>5}{int(b.out.sum()):>11}"
                      f"{b.out.mean()*100:>7.0f}%"
                      f"{len(bad)/max(int(b.out.sum()),1)*100:>25.0f}%")

    # ---------------- 3 & 4. what predicts an outlier, with draft slot held fixed
    for prefix, plab in (("w1_", "WEEK 1"), ("e4_", "WEEKS 2-4")):
        print(f"\n\n## {'3' if prefix == 'w1_' else '4'}. AMONG PLAYERS WITH A "
              f"BELOW-EXPECTATION WEEK 1, WHICH {plab} NUMBERS")
        print(f"      PICKED OUT THE ONES WHO STILL FINISHED {OUTLIER_GAIN}+ SPOTS AHEAD?")
        print("      Draft slot is held fixed: 'AUC in tier' uses only players drafted")
        print("      13-40, and the logistic model carries log(draft slot) alongside.")
        print("      AUC 0.50 and beta 0.00 are both coin flips.")
        for pos in POS:
            d = P[pos].copy()
            d["sur"] = surprise(d, "prior_rank")
            d = d[np.isfinite(d[["prior_rank", "final_rank", "sur"]]).all(axis=1)]
            d["out"] = ((d.prior_rank - d.final_rank) >= OUTLIER_GAIN).astype(float)
            bad = d[d.sur <= 0]
            if len(bad) < 80:
                continue
            mid = bad[(bad.prior_rank >= 13) & (bad.prior_rank <= 40)]
            print(f"\n   {pos}   {len(bad)} below-expectation Week 1s, "
                  f"{int(bad.out.sum())} broke out ({bad.out.mean()*100:.0f}%)"
                  f"   |  in the 13-40 band: {len(mid)}, "
                  f"{int(mid.out.sum())} broke out ({mid.out.mean()*100:.0f}%)")
            print(f"     {prefix.rstrip('_')+' metric':<26}{'AUC in tier':>12}{'p':>9}"
                  f"{'| logistic beta':>17}{'p':>9}{'  outliers':>11}{'others':>9}")
            rows = []
            for m, lab in CANDS[pos]:
                col = prefix + m
                if col not in bad:
                    continue
                a, pa, na, nb = auc(mid.loc[mid.out == 1, col], mid.loc[mid.out == 0, col])
                sub = bad[np.isfinite(bad[[col, "prior_rank"]]).all(axis=1)]
                b_, pb = np.nan, np.nan
                if len(sub) >= 60 and sub.out.nunique() > 1:
                    lr = np.log(sub.prior_rank.values)
                    X = np.column_stack([np.ones(len(sub)),
                                         (lr - lr.mean()) / lr.std(), C.z(sub[col])])
                    try:
                        import statsmodels.api as sm
                        fit = sm.Logit(sub.out.values, X).fit(disp=0)
                        b_, pb = float(fit.params[2]), float(fit.pvalues[2])
                    except Exception:
                        pass
                if not np.isfinite(a) and not np.isfinite(b_):
                    continue
                rows.append((abs(b_) if np.isfinite(b_) else 0, a, pa, b_, pb, lab,
                             mid.loc[mid.out == 1, col].mean(),
                             mid.loc[mid.out == 0, col].mean()))
            for _, a, pa, b_, pb, lab, mo, mn in sorted(rows, reverse=True):
                fa = "     n/a" if not np.isfinite(a) else f"{a:>12.3f}"
                fpa = "    n/a" if not np.isfinite(pa) else f"{pa:>9.3g}"
                fb = "     n/a" if not np.isfinite(b_) else f"{b_:>+17.3f}"
                fpb = "    n/a" if not np.isfinite(pb) else f"{pb:>9.3g}"
                print(f"     {lab:<26}{fa}{fpa}{fb}{fpb}{mo:>11.3f}{mn:>9.3f}")

    # ---------------- 5. earned or vacated?
    print("\n\n## 5. EARNED, OR VACATED? change in his position-mates' combined snap share")
    print("     from Week 1 to the rest of the season. Negative means the room shrank")
    print("     around him -- someone ahead of him stopped playing.")
    print(f"   {'pos':<5}{'group':<22}{'n':>5}{'mates snap share change':>26}"
          f"{'95% interval':>20}{'share where it fell 20+ pts':>29}")
    print("   " + "-" * 107)
    for pos in POS:
        d = P[pos].copy()
        d["sur"] = surprise(d, "prior_rank")
        d = d[np.isfinite(d[["prior_rank", "final_rank", "sur", "mates_delta"]]).all(axis=1)]
        d["out"] = (d.prior_rank - d.final_rank) >= OUTLIER_GAIN
        for lab, b in (("outliers, bad wk1", d[d.out & (d.sur <= 0)]),
                       ("outliers, good wk1", d[d.out & (d.sur > 0)]),
                       ("everyone else", d[~d.out])):
            if len(b) < 15:
                continue
            x = b.mates_delta
            m, se = x.mean(), x.std(ddof=1) / np.sqrt(len(x))
            h = stats.t.ppf(.975, len(x) - 1) * se
            print(f"   {pos:<5}{lab:<22}{len(b):>5}{m*100:>25.1f}%"
                  f"{f'[{(m-h)*100:+.1f}, {(m+h)*100:+.1f}]%':>20}"
                  f"{(x <= -0.20).mean()*100:>28.0f}%")
    pd.concat([d.assign(position=p) for p, d in P.items()]).to_csv("out_outliers.csv",
                                                                   index=False)


if __name__ == "__main__":
    main()
