"""Score named receivers against every comparable season since 2009.

    python3 profile.py "Parker Washington" "Brian Thomas Jr." "Rome Odunze"

For each receiver it prints his latest season, where every metric sits inside
that season's field, whether he actually clears each archetype's conditions,
his projection from the forward-selected reference model, and - the part that
does the real work - the historical receivers whose season most resembled his,
with what those receivers did the following year.

Comparables are found on within-season percentile ranks, so a 2011 season and a
2024 season are compared on their standing in their own year rather than on raw
totals.

Metrics are weighted by |standardised coefficient| in a regression of next-season
points per game on the whole matching set, with season fixed effects - that is,
by what each one is worth ALONGSIDE the others, not on its own. The distinction
matters: age predicts almost nothing by itself (cv R2 = 0.02) but is the second
most valuable metric in the horse race, and weighting it by its solo power
matches a 22-year-old coming off a bad year to 31-year-olds coming off the same
bad year, which is exactly the wrong comparison. Where metrics are collinear
(points per game, finish, health-adjusted finish) they split one weight between
them instead of counting three times.
"""
import sys
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm

from horse_race import FEATURES, forward_select, loso_r2, sample
from panel import build

warnings.filterwarnings("ignore")
pd.set_option("display.width", 240)

# The profile a receiver is matched on. Production, opportunity, efficiency,
# health, weekly shape, age and pedigree - one or two of each, not thirty.
MATCH = ["ppg", "pace_finish", "finish", "tpg", "target_share", "ppr_per_target",
         "ypt", "missed", "top5_share", "quiet_rate", "exp", "age",
         "best_prior_finish", "prior_top24", "young_mate_finish"]

SHOW = ["ppg", "finish", "pace_finish", "tpg", "target_share", "ppr_per_target",
        "ypt", "epa_per_target", "adot", "top5_share", "quiet_rate", "missed",
        "best_prior_finish", "young_mate_finish"]

K = 40


def pct_ranks(df, cols):
    """Within-season percentile rank of each metric, oriented so 1.0 is good."""
    out = pd.DataFrame(index=df.index)
    for c in cols:
        r = df.groupby("season")[c].rank(pct=True)
        out[c] = 1 - r if c in LOWER_IS_BETTER else r
    return out


LOWER_IS_BETTER = {"finish", "pace_finish", "best_prior_finish", "quiet_rate",
                   "missed", "age", "exp", "top5_share"}


def archetype_tests(r, eff_cut):
    """Every archetype condition, and whether this receiver clears it."""
    return {
        "A  five-week WR1": [
            ("finished WR4-15", 4 <= r.finish <= 15, f"WR{r.finish:.0f}"),
            ("14+ games", r.games >= 14, f"{r.games:.0f}"),
            ("top 5 games are 45%+ of his points", r.top5_share >= 0.45,
             f"{100 * r.top5_share:.0f}%"),
            ("never a top-24 season before", r.prior_top24 == 0, f"{r.prior_top24:.0f}"),
            ("not a rookie", r.exp >= 2, f"yr {r.exp:.0f}"),
        ],
        "B  young ex-WR1 off a collapse": [
            ("year 4 or earlier", r.exp <= 4, f"yr {r.exp:.0f}"),
            ("a top-12 season already behind him", r.best_prior_finish <= 12,
             f"WR{r.best_prior_finish:.0f}" if np.isfinite(r.best_prior_finish) else "none"),
            ("now finished outside the top 30", r.finish >= 30, f"WR{r.finish:.0f}"),
        ],
        "C  hurt + efficient": [
            ("years 2-4", 2 <= r.exp <= 4, f"yr {r.exp:.0f}"),
            ("missed 3+ games", r.missed >= 3, f"{r.missed:.0f}"),
            ("healthy-pace finish inside WR18", r.pace_finish <= 18, f"WR{r.pace_finish:.0f}"),
            ("6+ targets per game", r.tpg >= 6.0, f"{r.tpg:.1f}"),
            ("top-third efficiency (PPR per target)", r.ppr_per_target >= eff_cut,
             f"{r.ppr_per_target:.2f} vs {eff_cut:.2f}"),
        ],
    }


def match_weights(hist, cols=MATCH, y="next_ppg_c"):
    """|standardised coefficient| in a regression of next season on all of `cols`."""
    z = pd.DataFrame({c: (hist[c] - hist[c].mean()) / hist[c].std(ddof=0) for c in cols})
    X = pd.concat([z, pd.get_dummies(hist.season, prefix="y", drop_first=True).astype(float)],
                  axis=1)
    fit = sm.OLS(hist[y].to_numpy(float), sm.add_constant(X)).fit()
    w = fit.params[cols].abs().to_numpy()
    return w / w.sum()


def fit_predict(train, test, cols, y="next_ppg_c"):
    X, Xt = train[cols].to_numpy(float), test[cols].to_numpy(float)
    mu, sd = X.mean(0), np.where(X.std(0) == 0, 1.0, X.std(0))
    beta, *_ = np.linalg.lstsq(np.c_[np.ones(len(X)), (X - mu) / sd],
                               train[y].to_numpy(float), rcond=None)
    return np.c_[np.ones(len(Xt)), (Xt - mu) / sd] @ beta


def main(names):
    df = build()
    hist = sample(df)                      # 2009-2024, has a season N+1
    model, model_r2 = forward_select(hist, [c for c in FEATURES if c in hist.columns])

    last = int(df.season.max())
    cur = sample(df, min_season=last, with_next=False)
    cur = cur[cur.season == last].copy()
    cur["proj_ppg"] = fit_predict(hist, cur, model)
    cur["proj_rank"] = cur.proj_ppg.rank(ascending=False, method="min")
    eff_cut = cur.ppr_per_target.quantile(2 / 3)

    wv = match_weights(hist)

    both = pd.concat([hist, cur], ignore_index=False)
    ranks = pct_ranks(both, MATCH)
    hr, cr = ranks.loc[hist.index], ranks.loc[cur.index]

    print(f"Reference model (forward-selected, leave-one-season-out R2 = {model_r2:.4f}):")
    print("  " + ", ".join(model))
    print(f"\nComparable pool: {len(hist):,} WR-seasons, 2009-2024.")
    print("Matching weights (share of the distance each metric owns):")
    print("  " + "   ".join(f"{c} {100 * w:.0f}%" for c, w in
                            sorted(zip(MATCH, wv), key=lambda t: -t[1]) if w > 0.02))

    summary, comps = [], {}
    for name in names:
        rows = cur[cur.player.str.lower() == name.lower()]
        if not len(rows):
            print(f"\n!! no {last} season for {name}")
            continue
        r = rows.iloc[0]
        print("\n" + "=" * 78)
        print(f"{r.player.upper()}   {r.team}   year {r.exp:.0f}   {last} season")
        print("=" * 78)

        print(f"\n  {r.games:.0f} games ({r.missed:.0f} missed), {r.targets:.0f} targets, "
              f"{r.ppr:.1f} PPR points -> WR{r.finish:.0f}\n")
        pr = cr.loc[r.name]
        for c in SHOW:
            v = r[c]
            pctl = pct_ranks(both, [c]).loc[r.name, c]
            val = f"WR{v:.0f}" if c.endswith("finish") else (
                f"{100 * v:.0f}%" if c in ("top5_share", "quiet_rate", "target_share")
                else f"{v:.2f}")
            bar = "#" * int(round(20 * pctl))
            print(f"    {c:<18} {val:>8}   {100 * pctl:>3.0f}th  {bar}")
        print("\n    (percentile is within the same season, oriented so higher = better)")

        print("\n  Archetype conditions:")
        for arch, tests in archetype_tests(r, eff_cut).items():
            passed = sum(ok for _, ok, _ in tests)
            print(f"\n    {arch}  -  {passed}/{len(tests)} conditions met")
            for label, ok, shown in tests:
                print(f"      [{'x' if ok else ' '}] {label:<40} {shown}")

        # ---- nearest historical seasons ---------------------------------
        d = np.sqrt((((hr - pr) ** 2) * wv).sum(axis=1)).sort_values()
        near = hist.loc[d.index[:K]].copy()
        print(f"\n  The most similar seasons since 2009, and what they did next:")
        print(f"    {'comps':>6}  {'median next':>12}  {'quartiles':>13}  "
              f"{'top-12':>7}  {'top-24':>7}  {'next ppg':>9}")
        for k in (20, K, 80):
            g = hist.loc[d.index[:k]]
            print(f"    {k:>6}  {'WR%d' % g.next_finish_c.median():>12}"
                  f"  {'WR%d-WR%d' % (g.next_finish_c.quantile(.25), g.next_finish_c.quantile(.75)):>13}"
                  f"  {100 * g.next_top12.mean():>6.0f}%  {100 * g.next_top24.mean():>6.0f}%"
                  f"  {g.next_ppg_c.mean():>9.2f}")
        summary.append({
            "player": r.player, "yr": r.exp, "finish": r.finish,
            "med_next": near.next_finish_c.median(),
            "top12": 100 * near.next_top12.mean(),
            "top24": 100 * near.next_top24.mean(),
            "comp_ppg": near.next_ppg_c.mean(),
            "proj_ppg": r.proj_ppg, "proj_rank": r.proj_rank,
        })
        comps[r.player] = near.next_finish_c.to_numpy()
        print(f"\n    closest 12 of the {K}:")
        for _, c in near.head(12).iterrows():
            nxt = "did not play" if pd.isna(c.next_finish) else f"WR{c.next_finish:.0f}"
            print(f"      {int(c.season)}  {c.player:<22} yr {c.exp:>2.0f}  WR{c.finish:>3.0f}"
                  f"  {c.ppg:>5.2f} ppg  {c.missed:>2.0f} missed  ->  {nxt}")

        print(f"\n  Reference-model projection for {last + 1}: {r.proj_ppg:.2f} ppg "
              f"(#{r.proj_rank:.0f} of the {len(cur)} qualifying {last} receivers)")

    if len(summary) < 2:
        return
    print("\n" + "=" * 78)
    print("SIDE BY SIDE")
    print("=" * 78)
    print("\nEach receiver's %d nearest historical seasons, and the reference model:\n" % K)
    t = pd.DataFrame(summary).sort_values("proj_ppg", ascending=False)
    print(t.to_string(index=False, formatters={
        "yr": "{:.0f}".format, "finish": "WR{:.0f}".format, "med_next": "WR{:.0f}".format,
        "top12": "{:.0f}%".format, "top24": "{:.0f}%".format,
        "comp_ppg": "{:.2f}".format, "proj_ppg": "{:.2f}".format, "proj_rank": "#{:.0f}".format}))

    print("\nP(the row receiver's comps finish ahead of the column receiver's),")
    print("over every ordered pair of comparable seasons, ties split:\n")
    names_ = list(comps)
    M = pd.DataFrame(index=names_, columns=names_, dtype=float)
    for i in names_:
        for j in names_:
            if i == j:
                continue
            a, b = comps[i], comps[j]
            M.loc[i, j] = 100 * ((a[:, None] < b[None, :]).mean()
                                 + 0.5 * (a[:, None] == b[None, :]).mean())
    print(M.to_string(float_format=lambda v: "" if np.isnan(v) else f"{v:.0f}%"))


if __name__ == "__main__":
    main(sys.argv[1:] or ["Parker Washington", "Brian Thomas Jr.", "Rome Odunze"])
