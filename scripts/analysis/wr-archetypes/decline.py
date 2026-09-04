"""When a receiver falls off, which kind of falling off comes back?

    python3 decline.py > DECLINE.txt

A receiver can lose a season two ways. The offence can stop throwing to him -
his target share collapses and someone else has the job. Or he can keep the job
and stop converting it - same targets, fewer points per target. Fantasy talk
treats these as the same bad year. They are not.

Sections 3 and 4 use FTN charting (2022-2025) to split conversion failure again:
were the throws worse, or was he worse? And does a drop rate carry forward?
"""
import os
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

from horse_race import loso_r2, sample
from panel import build

warnings.filterwarnings("ignore")
pd.set_option("display.width", 220)
HERE = os.path.dirname(os.path.abspath(__file__))

DROP = 0.20        # a season counts as a decline if ppg fell this much
ROLE_LOSS = 0.15   # relative fall in target share that counts as losing the job
EFF_LOSS = 0.10    # relative fall in points per target that counts as not converting


def rule(title, char="="):
    print("\n" + char * 78)
    print(title)
    print(char * 78)


def outcomes(s, sel, label):
    g = s[sel]
    if not len(g):
        return {"cohort": label, "n": 0}
    return {"cohort": label, "n": len(g),
            "med_next": g.next_finish_c.median(),
            "q1": g.next_finish_c.quantile(.25), "q3": g.next_finish_c.quantile(.75),
            "top12": 100 * g.next_top12.mean(), "top24": 100 * g.next_top24.mean(),
            "next_ppg": g.next_ppg_c.mean(),
            "bounce": 100 * (g.next_ppg_c > g.prev_ppg).mean()}


def show(rows):
    print(pd.DataFrame(rows).to_string(index=False, formatters={
        "med_next": "WR{:.0f}".format, "q1": "WR{:.0f}".format, "q3": "WR{:.0f}".format,
        "top12": "{:.0f}%".format, "top24": "{:.0f}%".format,
        "next_ppg": "{:.2f}".format, "bounce": "{:.0f}%".format}))


def charting_panel():
    """Receiver-season charting, summed over passers, with next season attached."""
    c = pd.read_parquet(f"{HERE}/charting.parquet")
    g = c.groupby(["season", "receiver_player_id", "receiver_player_name"]).apply(
        lambda x: pd.Series({
            "targets": x.targets.sum(),
            "drop_rate": (x.drops.sum() / x.targets.sum()),
            "catchable": np.average(x.catchable.fillna(0), weights=x.targets),
            "contested": np.average(x.contested.fillna(0), weights=x.targets),
            "adot": np.average(x.adot.fillna(0), weights=x.targets),
            "catch_on_catchable": np.average(x.catch_on_catchable.fillna(0), weights=x.targets),
            "n_passers": (x.targets >= 10).sum(),
        }), include_groups=False).reset_index()
    g = g.rename(columns={"receiver_player_id": "player_id"})
    nxt = g[["player_id", "season", "drop_rate", "catch_on_catchable", "targets"]].copy()
    nxt["season"] -= 1
    nxt = nxt.rename(columns={"drop_rate": "next_drop_rate",
                              "catch_on_catchable": "next_catch_on_catchable",
                              "targets": "next_targets"})
    return g.merge(nxt, on=["player_id", "season"], how="left")


def main():
    df = build()
    s = sample(df).copy()

    # Season N-1 opportunity and efficiency, so a decline can be decomposed.
    prior = df[["player_id", "season", "target_share", "ppr_per_target", "tpg", "ppg"]].copy()
    prior["season"] += 1
    prior = prior.rename(columns={"target_share": "prev_target_share",
                                  "ppr_per_target": "prev_ppr_per_target",
                                  "tpg": "prev_tpg", "ppg": "prev_ppg_raw"})
    s = s.merge(prior, on=["player_id", "season"], how="left")
    s = s[s.prev_target_share.notna() & (s.prev_ppg_raw > 0)]

    s["d_ppg"] = s.ppg / s.prev_ppg_raw - 1
    s["d_share"] = s.target_share / s.prev_target_share.replace(0, np.nan) - 1
    s["d_eff"] = s.ppr_per_target / s.prev_ppr_per_target.replace(0, np.nan) - 1
    s = s.replace([np.inf, -np.inf], np.nan).dropna(subset=["d_ppg", "d_share", "d_eff"])

    rule("THE SAMPLE")
    print(f"WR-seasons 2009-2024 with a qualifying season before them: {len(s):,}")
    dec = s[s.d_ppg <= -DROP]
    print(f"Of those, {len(dec):,} saw points per game fall {100 * DROP:.0f}% or more.")

    # ------------------------------------------------------------------ 1 ---
    rule("1. LOSING THE JOB VS NOT CONVERTING IT")
    print(f"Among receivers whose points per game fell {100 * DROP:.0f}%+ from the year")
    print("before. 'bounce' = share who beat their season N-1 points per game in")
    print("season N+1 - a full recovery, not just an improvement.\n")
    role = dec.d_share <= -ROLE_LOSS
    eff = dec.d_eff <= -EFF_LOSS
    show([outcomes(dec, role & ~eff, "lost the role only"),
          outcomes(dec, ~role & eff, "kept the role, stopped converting"),
          outcomes(dec, role & eff, "lost both"),
          outcomes(dec, ~role & ~eff, "neither (fewer games)"),
          outcomes(s, s.index.isin(s.index), "every season with a prior year")])
    print("\n    Mann-Whitney on next-season points per game,")
    a = dec[~role & eff].next_ppg_c
    b = dec[role & ~eff].next_ppg_c
    print(f"    kept-the-role vs lost-the-role: p = {stats.mannwhitneyu(a, b).pvalue:.3f}")
    print()
    z = pd.DataFrame({c: (dec[c] - dec[c].mean()) / dec[c].std(ddof=0)
                      for c in ["ppg", "d_share", "d_eff"]})
    X = pd.concat([z, pd.get_dummies(dec.season, prefix="y", drop_first=True).astype(float)], axis=1)
    f = sm.OLS(dec.next_ppg_c.to_numpy(float), sm.add_constant(X)).fit(cov_type="HC3")
    print("    Which part of the fall predicts next season (declining seasons only):")
    for c in ["ppg", "d_share", "d_eff"]:
        print(f"      {c:<10} {f.params[c]:+.3f} ppg/sd   t = {f.tvalues[c]:+.2f}"
              f"   p = {f.pvalues[c]:.3f}")

    # ----------------------------------------------------------------- 1b ---
    rule("1b. THOSE BUCKETS ARE MOSTLY AGE")
    print("The three cohorts above pool a 22-year-old with a 30-year-old, and")
    print("most of a receiver's decline risk is just age. Splitting the worst")
    print("bucket shows what the pooled number is actually measuring.\n")
    both = dec[role & eff]
    print(f"    'lost both': n = {len(both)}, median age {both.age.median():.1f}, "
          f"median experience year {both.exp.median():.0f}\n")
    show([outcomes(both, both.age <= 24, "  lost both, age 24 and under"),
          outcomes(both, both.age.between(25, 27, inclusive="left"), "  lost both, age 25-26"),
          outcomes(both, both.age >= 27, "  lost both, age 27+")])
    print()
    show([outcomes(both, both.best_prior_finish <= 12, "  lost both, a top-12 season behind him"),
          outcomes(both, both.best_prior_finish > 24, "  lost both, never top-24")])

    print("\n    The cell that matters for a young receiver coming off a WR1 season:")
    print("    any 20%+ decline, year 4 or earlier, with a top-12 finish already")
    print("    on the shelf - regardless of which way the fall broke down.\n")
    young = dec[(dec.exp <= 4) & (dec.best_prior_finish <= 12)]
    show([outcomes(dec, dec.index.isin(young.index), "  young, pedigreed decliners"),
          outcomes(dec, ~dec.index.isin(young.index), "  everyone else who declined")])
    print(f"\n    Note the sample: n = {len(young)}. And note that no receiver in the")
    print("    panel with 3 or fewer years and a top-12 season has ever landed in")
    print("    'lost both' at all - the cell is empty, which is not the same as safe.\n")
    cols = ["season", "player", "exp", "age", "prev_ppg_raw", "ppg", "finish", "next_finish"]
    y = young.sort_values("season")[cols].copy()
    y["mode"] = np.where((y.index.isin(both.index)), "both",
                         np.where(y.index.isin(dec[role].index), "role",
                                  np.where(y.index.isin(dec[eff].index), "eff", "-")))
    print(y.to_string(index=False, float_format="{:.2f}".format))

    # ------------------------------------------------------------------ 2 ---
    rule("2. THE SAME QUESTION AS A PREDICTION PROBLEM")
    print("Leave-one-season-out R2 on next-year points per game, declining seasons.\n")
    for cols in ([["ppg"], ["ppg", "d_share"], ["ppg", "d_eff"],
                  ["ppg", "d_share", "d_eff"], ["ppg", "prev_ppg_raw"],
                  ["ppg", "prev_ppg_raw", "d_share"]]):
        r2, _ = loso_r2(dec, cols)
        print(f"    {' + '.join(cols):<38} cv R2 = {r2:.4f}")

    # ------------------------------------------------------------------ 3 ---
    ch = charting_panel()
    m = s.merge(ch.drop(columns=["receiver_player_name", "targets"]),
                on=["player_id", "season"], how="inner")
    m = m[m.targets >= 40]
    rule("3. WERE THE THROWS WORSE, OR WAS HE WORSE?  (FTN charting, 2022-2025)")
    print(f"{len(m):,} receiver-seasons with 40+ targets and charting.\n")
    print("    Next season by quartile of drop rate, top-60 finishers:\n")
    top = m[m.finish <= 60]
    q = pd.qcut(top.drop_rate, 4, labels=["cleanest", "clean", "dropsy", "dropsiest"])
    g = top.groupby(q, observed=True).agg(
        n=("player_id", "size"), drop_rate=("drop_rate", "mean"),
        catchable=("catchable", "mean"), ppg=("ppg", "mean"),
        next_ppg=("next_ppg_c", "mean"), med_next=("next_finish_c", "median"))
    print(g.to_string(float_format="{:.3f}".format))
    print("\n    Does a drop rate add anything to points per game?\n")
    for cols in ([["ppg"], ["ppg", "drop_rate"], ["ppg", "catchable"],
                  ["ppg", "catch_on_catchable"], ["ppg", "drop_rate", "catchable"]]):
        sub = m.dropna(subset=cols + ["next_ppg_c"])
        r2, _ = loso_r2(sub, cols)
        print(f"    {' + '.join(cols):<38} cv R2 = {r2:.4f}   n = {len(sub)}")

    # ------------------------------------------------------------------ 4 ---
    rule("4. DOES A DROP RATE CARRY FORWARD?")
    print("Year-over-year persistence, receivers with 40+ targets in both years.")
    print("A stat that regresses hard is a reason to discount the bad year, not")
    print("to project it forward.\n")
    pair = ch[(ch.targets >= 40) & (ch.next_targets >= 40)].dropna(
        subset=["drop_rate", "next_drop_rate"])
    r = stats.pearsonr(pair.drop_rate, pair.next_drop_rate)
    print(f"    drop rate           n = {len(pair):>3}   r = {r.statistic:+.3f}"
          f"   p = {r.pvalue:.3f}   R2 = {r.statistic ** 2:.3f}")
    pc = ch[(ch.targets >= 40) & (ch.next_targets >= 40)].dropna(
        subset=["catch_on_catchable", "next_catch_on_catchable"])
    r2p = stats.pearsonr(pc.catch_on_catchable, pc.next_catch_on_catchable)
    print(f"    catch on catchable  n = {len(pc):>3}   r = {r2p.statistic:+.3f}"
          f"   p = {r2p.pvalue:.3f}   R2 = {r2p.statistic ** 2:.3f}")
    hi = pair[pair.drop_rate >= pair.drop_rate.quantile(0.9)]
    print(f"\n    Receivers in the worst decile of drop rate ({100 * hi.drop_rate.mean():.1f}% mean)")
    print(f"    dropped {100 * hi.next_drop_rate.mean():.1f}% the following year, against a "
          f"league mean of {100 * pair.next_drop_rate.mean():.1f}%.")

    # ------------------------------------------------------------------ 5 ---
    rule("5. THE JACKSONVILLE AND CHICAGO PASSING GAMES, BY PASSER")
    c = pd.read_parquet(f"{HERE}/charting.parquet")
    for team, season_list in (("JAX", (2024, 2025)), ("CHI", (2024, 2025))):
        for yr in season_list:
            x = c[(c.posteam == team) & (c.season == yr) & (c.targets >= 15)].copy()
            if not len(x):
                continue
            x["ypt"] = x.yards / x.targets
            x["ppr_per_tgt"] = (x.rec + 0.1 * x.yards + 6 * x.tds) / x.targets
            x = x.sort_values("targets", ascending=False)
            print(f"\n  {team} {yr}")
            print(x[["receiver_player_name", "passer_player_name", "targets", "ypt",
                     "ppr_per_tgt", "adot", "catchable", "contested", "drop_rate",
                     "catch_on_catchable"]].to_string(
                index=False, float_format="{:.3f}".format))

    section6(s)


def adjusted_charting():
    """Target quality and conversion, adjusted for the job he was asked to do.

    A deep target is inherently less catchable and a contested one is inherently
    harder to convert, so the raw rates partly measure the route tree. Residuals
    against depth (and against depth plus contested rate) say whether he was
    thrown bad balls and whether he failed to convert good ones, holding the
    role constant.
    """
    c = pd.read_parquet(f"{HERE}/charting.parquet")
    g = c.groupby(["season", "receiver_player_id", "receiver_player_name"]).apply(
        lambda x: pd.Series({
            "targets": x.targets.sum(),
            "adot": np.average(x.adot.fillna(0), weights=x.targets),
            "catchable": np.average(x.catchable.fillna(0), weights=x.targets),
            "contested": np.average(x.contested.fillna(0), weights=x.targets),
            "drop_rate": x.drops.sum() / x.targets.sum(),
            "coc": np.average(x.catch_on_catchable.fillna(0), weights=x.targets),
        }), include_groups=False).reset_index()
    g = g[g.targets >= 40].reset_index(drop=True)
    g["catchable_oe"] = sm.OLS(
        g.catchable, sm.add_constant(pd.DataFrame({"a": g.adot, "a2": g.adot ** 2}))).fit().resid
    g["coc_oe"] = sm.OLS(
        g.coc, sm.add_constant(pd.DataFrame({"c": g.contested, "a": g.adot}))).fit().resid
    return g.rename(columns={"receiver_player_id": "player_id"})


def section6(s):
    rule("6. WAS HE THROWN BAD BALLS, OR DID HE DROP GOOD ONES?")
    print("Catchable rate residual against depth of target, and catch-on-catchable")
    print("residual against contested rate and depth. Positive means better than")
    print("the job he was asked to do would predict.\n")
    g = adjusted_charting()
    nxt = g[["player_id", "season", "coc_oe", "catchable_oe", "drop_rate"]].copy()
    nxt["season"] -= 1
    nxt = nxt.rename(columns={"coc_oe": "n_coc", "catchable_oe": "n_catch", "drop_rate": "n_drop"})
    pair = g.merge(nxt, on=["player_id", "season"], how="inner")
    print("    Persistence, receivers with 40+ targets in consecutive years:")
    for a, b, lab in [("coc_oe", "n_coc", "adjusted catch-on-catchable"),
                      ("catchable_oe", "n_catch", "adjusted target quality"),
                      ("drop_rate", "n_drop", "drop rate")]:
        r = stats.pearsonr(pair[a], pair[b])
        print(f"      {lab:<30} n = {len(pair)}   r = {r.statistic:+.3f}"
              f"   R2 = {r.statistic ** 2:.3f}")

    m = sample(build()).merge(g.drop(columns=["receiver_player_name", "targets"]),
                              on=["player_id", "season"], how="inner")
    print(f"\n    Does any of it predict next season?  (n = {len(m)})\n")
    for cols in ([["ppg"], ["ppg", "coc_oe"], ["ppg", "catchable_oe"], ["ppg", "drop_rate"],
                  ["ppg", "age"], ["ppg", "age", "coc_oe"]]):
        r2, _ = loso_r2(m, cols)
        print(f"      {' + '.join(cols):<30} cv R2 = {r2:.4f}")
    print("\n    Next season by quintile of adjusted conversion:\n")
    q = pd.qcut(m.coc_oe, 5, labels=["worst", "2", "3", "4", "best"])
    t = m.groupby(q, observed=True).agg(
        n=("player_id", "size"), coc_oe=("coc_oe", "mean"), ppg=("ppg", "mean"),
        next_ppg=("next_ppg_c", "mean"), med_next=("next_finish_c", "median"),
        top24=("next_top24", "mean"))
    t["top24"] = 100 * t.top24
    print(t.to_string(float_format="{:.3f}".format))
    print("\n    The worst quintile does finish worse - and its current points per")
    print("    game is already the lowest, which is why the residual adds nothing")
    print("    once scoring is in the model.")

    print("\n\n    The three receivers, and where regression to the mean puts them:\n")
    for a, b, lab in [("coc_oe", "n_coc", "adjusted catch-on-catchable"),
                      ("drop_rate", "n_drop", "drop rate")]:
        sl, ic, r, _, _ = stats.linregress(pair[a], pair[b])
        print(f"    {lab}  (year-to-year slope {sl:+.3f})")
        for who in ("B.Thomas", "P.Washington", "R.Odunze", "L.Burden"):
            row = g[(g.receiver_player_name == who) & (g.season == 2025)]
            if not len(row):
                continue
            v = float(row.iloc[0][a])
            rank = int(g[a].rank().loc[row.index[0]])
            print(f"      {who:<14} 2025 {v:+.3f}  (rank {rank} of {len(g)})"
                  f"  ->  projected {sl * v + ic:+.3f}   league mean {pair[b].mean():+.3f}")
        print()


if __name__ == "__main__":
    main()
