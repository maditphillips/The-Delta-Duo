"""Arriving from below versus falling from above.

    python3 trajectory.py > TRAJECTORY.txt

Two receivers both score 12 points a game. One came up from 8, the other came
down from 16. Fantasy language treats the first as ascending and the second as
declining, and prices them accordingly. This asks whether season N+1 agrees.

Note this is NOT the within-season question timing.py answers - that one is about
a hot start or a strong finish inside one year, and the answer there is a flat
no. This is year over year: the level he came from, holding the level he is at
now fixed.
"""
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

from horse_race import loso_r2, sample
from panel import build

warnings.filterwarnings("ignore")
pd.set_option("display.width", 220)


PRIOR_MIN_TARGETS = 25   # a season below this is not a baseline worth differencing


def rule(title, char="="):
    print("\n" + char * 78)
    print(title)
    print(char * 78)


def race(s, specs, y="next_ppg_c"):
    for cols in specs:
        sub = s.dropna(subset=cols + [y])
        r2, _ = loso_r2(sub, cols, y)
        print(f"    {' + '.join(cols):<44} cv R2 = {r2:.4f}   n = {len(sub):,}")


def weights(s, cols, label, y="next_ppg_c"):
    sub = s.dropna(subset=cols + [y])
    z = pd.DataFrame({c: (sub[c] - sub[c].mean()) / sub[c].std(ddof=0) for c in cols})
    X = pd.concat([z, pd.get_dummies(sub.season, prefix="y", drop_first=True).astype(float)],
                  axis=1)
    f = sm.OLS(sub[y].to_numpy(float), sm.add_constant(X)).fit(cov_type="HC3")
    print(f"    {label}  (n = {len(sub):,})")
    for c in cols:
        print(f"      {c:<22} {f.params[c]:+.3f} ppg/sd   t = {f.tvalues[c]:+.2f}"
              f"   p = {f.pvalues[c]:.3f}")


def grid(s, label):
    """Within each level of current scoring, split by where he came from."""
    x = s.dropna(subset=["ppg", "prev_ppg_raw", "next_ppg_c"]).copy()
    x["level"] = pd.qcut(x.ppg, 5, labels=["ppg Q1", "Q2", "Q3", "Q4", "ppg Q5"])
    x["dir"] = np.where(x.ppg - x.prev_ppg_raw > 1.0, "rose",
                        np.where(x.ppg - x.prev_ppg_raw < -1.0, "fell", "flat"))
    print(f"\n    {label}: mean season N+1 points per game\n")
    t = x.pivot_table(index="level", columns="dir", values="next_ppg_c",
                      aggfunc="mean", observed=True)
    n = x.pivot_table(index="level", columns="dir", values="next_ppg_c",
                      aggfunc="size", observed=True)
    out = t[["fell", "flat", "rose"]].round(2).astype(str) + " (" + \
        n[["fell", "flat", "rose"]].astype(str) + ")"
    print(out.to_string())
    print("\n    Same cells, share finishing top-24 the following season\n")
    t2 = 100 * x.pivot_table(index="level", columns="dir", values="next_top24",
                             aggfunc="mean", observed=True)
    print(t2[["fell", "flat", "rose"]].round(0).to_string())


def main():
    df = build()
    s = sample(df).copy()

    # The prior season has to be a real one. A receiver with three targets in
    # year N-1 has a points-per-target that is pure noise, and differencing
    # against it produced a -247 outlier that on its own wrecked a fold of the
    # cross-validation.
    prior = df[["player_id", "season", "ppg", "target_share", "ppr_per_target",
                "targets", "games"]].copy()
    prior["season"] += 1
    prior = prior.rename(columns={"ppg": "prev_ppg_raw", "target_share": "prev_ts",
                                  "ppr_per_target": "prev_eff",
                                  "targets": "prev_targets_n", "games": "prev_games_n"})
    bad = (prior.prev_targets_n < PRIOR_MIN_TARGETS) | (prior.prev_games_n < 4)
    prior.loc[bad, ["prev_ppg_raw", "prev_ts", "prev_eff"]] = np.nan
    s = s.merge(prior.drop(columns=["prev_targets_n", "prev_games_n"]),
                on=["player_id", "season"], how="left")

    # Career-best season before this one, and the level he is arriving from.
    df2 = df.sort_values(["player_id", "season"])
    df2["peak_prior_ppg"] = df2.groupby("player_id").ppg.transform(lambda x: x.shift().cummax())
    s = s.merge(df2[["player_id", "season", "peak_prior_ppg"]], on=["player_id", "season"],
                how="left")

    s = s[s.prev_ppg_raw.notna()].copy()
    s["d_ppg"] = s.ppg - s.prev_ppg_raw
    s["d_ts"] = s.target_share - s.prev_ts
    s["d_eff"] = s.ppr_per_target - s.prev_eff
    s["off_peak"] = s.ppg - s.peak_prior_ppg

    rule("THE SAMPLE")
    print(f"WR-seasons 2009-2024 with a real prior season "
          f"({PRIOR_MIN_TARGETS}+ targets, 4+ games): {len(s):,}")
    print(f"{100 * (s.d_ppg > 1).mean():.0f}% arrived rising, "
          f"{100 * (s.d_ppg < -1).mean():.0f}% falling, "
          f"{100 * s.d_ppg.abs().le(1).mean():.0f}% flat.")

    # ------------------------------------------------------------------ 1 ---
    rule("1. AT THE SAME LEVEL, DOES DIRECTION MATTER?")
    print("Rows are quintiles of THIS season's points per game, so every cell in a")
    print("row scored about the same. Columns are how he got there.")
    grid(s, "Everyone")

    # ------------------------------------------------------------------ 2 ---
    rule("2. THE SAME THING AS A COEFFICIENT")
    print("Holding this season's scoring fixed, what does the change from last")
    print("season add?  A positive coefficient would mean rising is good.\n")
    weights(s, ["ppg", "d_ppg"], "Current scoring and the year-over-year change:")
    print()
    weights(s, ["ppg", "prev_ppg_raw"], "The same information stated as the level he came from:")
    print("\n    Those are the same regression. Given where he is now, a HIGHER")
    print("    previous season predicts a better next year, which is the same")
    print("    statement as: at equal current scoring, falling beats rising.\n")
    weights(s, ["ppg", "peak_prior_ppg"], "Career-best season instead of last season:")
    print()
    weights(s, ["ppg", "d_ppg", "age", "exp"],
            "With age and experience in, in case 'rising' is just 'young':")

    # ------------------------------------------------------------------ 3 ---
    rule("3. DOES ANY OF IT HELP OUT OF SAMPLE?")
    race(s, [["ppg"], ["ppg", "d_ppg"], ["ppg", "prev_ppg_raw"], ["ppg", "peak_prior_ppg"],
             ["ppg", "age"], ["ppg", "age", "d_ppg"], ["ppg", "age", "peak_prior_ppg"]])

    # ------------------------------------------------------------------ 4 ---
    rule("4. IS IT DIFFERENT FOR YOUNG RECEIVERS?")
    print("The whole effect could be survivorship: a 30-year-old who is rising is")
    print("rare and probably real, a 30-year-old falling is just ageing.\n")
    for label, sub in [("years 1-3", s[s.exp <= 3]), ("years 4-6", s[s.exp.between(4, 6)]),
                       ("year 7+", s[s.exp >= 7])]:
        w = sub.dropna(subset=["ppg", "d_ppg", "next_ppg_c"])
        z = pd.DataFrame({c: (w[c] - w[c].mean()) / w[c].std(ddof=0) for c in ["ppg", "d_ppg"]})
        X = pd.concat([z, pd.get_dummies(w.season, prefix="y", drop_first=True).astype(float)],
                      axis=1)
        f = sm.OLS(w.next_ppg_c.to_numpy(float), sm.add_constant(X)).fit(cov_type="HC3")
        print(f"    {label:<12} n = {len(w):>4}   d_ppg {f.params.d_ppg:+.3f} ppg/sd"
              f"   t = {f.tvalues.d_ppg:+.2f}   p = {f.pvalues.d_ppg:.3f}")
    print()
    grid(s[s.exp <= 4], "Years 1-4 only")

    # ------------------------------------------------------------------ 5 ---
    rule("5. A RISING ROLE VS RISING POINTS")
    print("Target share is the part of a trend a receiver's team controls. If any")
    print("trajectory matters it should be this one.\n")
    weights(s, ["ppg", "d_ts"], "Change in target share, holding scoring fixed:")
    print()
    weights(s, ["ppg", "d_ts", "d_eff"], "Splitting the change into role and conversion:")
    print()
    race(s, [["ppg"], ["ppg", "d_ts"], ["ppg", "d_ts", "d_eff"],
             ["ppg", "target_share"], ["ppg", "target_share", "d_ts"]])

    # ------------------------------------------------------------------ 6 ---
    rule("6. MULTI-YEAR SLOPE")
    print("Three seasons of history, fit a line, ask whether its slope adds")
    print("anything to the last point on it.\n")
    hist = df.sort_values(["player_id", "season"])[["player_id", "season", "ppg"]]
    sl = []
    for pid, g in hist.groupby("player_id"):
        g = g.reset_index(drop=True)
        for i in range(2, len(g)):
            w = g.iloc[i - 2:i + 1]
            if w.season.max() - w.season.min() != 2:
                continue
            sl.append((pid, int(w.season.iloc[-1]),
                       float(np.polyfit(w.season - w.season.min(), w.ppg, 1)[0])))
    slope = pd.DataFrame(sl, columns=["player_id", "season", "slope3"])
    t = s.merge(slope, on=["player_id", "season"], how="inner")
    print(f"    n = {len(t):,} receiver-seasons with three consecutive years\n")
    weights(t, ["ppg", "slope3"], "Three-year slope, holding current scoring fixed:")
    print()
    race(t, [["ppg"], ["ppg", "slope3"], ["ppg", "prev_ppg_raw"], ["ppg", "slope3", "age"]])

    # ------------------------------------------------------------------ 7 ---
    rule("7. THE MATCHUP THIS STARTED FROM")
    print("Receivers in years 2-4 who arrived at 9-13 points a game, split by")
    print("whether they climbed to it or fell to it.\n")
    band = s[(s.exp.between(2, 4)) & (s.ppg.between(9, 13))]
    for label, sel in [("fell to it (down 3+ ppg)", band.d_ppg <= -3),
                       ("held roughly level", band.d_ppg.abs() < 3),
                       ("climbed to it (up 3+ ppg)", band.d_ppg >= 3)]:
        g = band[sel]
        if len(g) < 5:
            print(f"    {label:<28} n = {len(g)} (too few)")
            continue
        print(f"    {label:<28} n = {len(g):>3}   median next WR{g.next_finish_c.median():>4.0f}"
              f"   top-12 {100 * g.next_top12.mean():>4.1f}%   top-24 {100 * g.next_top24.mean():>4.1f}%"
              f"   next ppg {g.next_ppg_c.mean():>5.2f}")
    a = band[band.d_ppg <= -3].next_ppg_c
    b = band[band.d_ppg >= 3].next_ppg_c
    if len(a) >= 5 and len(b) >= 5:
        print(f"\n    Mann-Whitney, fell vs climbed: p = {stats.mannwhitneyu(a, b).pvalue:.3f}")


if __name__ == "__main__":
    main()
