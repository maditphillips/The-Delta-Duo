"""The three receivers, run against every season since 2000.

    python3 archetypes.py > ARCHETYPES.txt

  A  The five-week WR1.  Finished around WR8 on the back of a handful of huge
     games; quiet the rest of that season, and quiet for his whole career before it.
  B  The sophomore crash.  Finished top-5 as a rookie, then injury and a slump
     dropped him to around WR40 in year two.  Now entering year three.
  C  The hurt efficient one.  Years two to four, always well targeted, elite
     per-target production, missed real time, and his per-game pace says he was
     on a top-15 season - but a younger receiver on his own team finished strong.

Each is a ladder: the loose version first, then each extra condition, so you can
watch the sample shrink and see which condition is doing the work.  Outcomes are
season N+1 finish and points per game; receivers who never played another
qualifying season are kept, censored at the bottom of the pool.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

from horse_race import FEATURES, forward_select, loso_r2, sample
from panel import build

warnings.filterwarnings("ignore")
pd.set_option("display.width", 250)
RNG = np.random.default_rng(20260904)

# The model here is not hand-picked: it is whatever survives the same
# out-of-sample forward selection horse_race.py runs, so the two can never drift.

COLS = ["cohort", "n", "med_next", "p10_p90", "q1", "q3", "top12", "top24", "top36",
        "next_ppg", "model_ppg", "beat"]
FMT = {"med_next": "{:.0f}".format, "q1": "{:.0f}".format, "q3": "{:.0f}".format,
       "top12": "{:.0f}%".format, "top24": "{:.0f}%".format, "top36": "{:.0f}%".format,
       "next_ppg": "{:.2f}".format, "model_ppg": "{:.2f}".format, "beat": "{:+.2f}".format}


def boot_median(x, n=4000):
    x = np.asarray(x, dtype=float)
    if len(x) < 3:
        return (np.nan, np.nan)
    m = [np.median(RNG.choice(x, len(x), replace=True)) for _ in range(n)]
    return tuple(np.percentile(m, [10, 90]))


def describe(s, sel, label):
    g = s[sel]
    if not len(g):
        return {"cohort": label, "n": 0}
    lo, hi = boot_median(g.next_finish_c)
    return {
        "cohort": label, "n": len(g),
        "med_next": g.next_finish_c.median(),
        "p10_p90": f"{lo:.0f}-{hi:.0f}" if np.isfinite(lo) else "-",
        "q1": g.next_finish_c.quantile(.25), "q3": g.next_finish_c.quantile(.75),
        "top12": 100 * g.next_top12.mean(), "top24": 100 * g.next_top24.mean(),
        "top36": 100 * g.next_top36.mean(),
        "next_ppg": g.next_ppg_c.mean(),
        "model_ppg": g.model_ppg.mean(),
        "beat": g.next_ppg_c.mean() - g.model_ppg.mean(),
    }


def show(rows):
    print(pd.DataFrame(rows).reindex(columns=COLS).to_string(index=False, formatters=FMT))


def roster(s, sel, k=16):
    g = s[sel].sort_values("season")
    lines = [f"      {int(r.season)}  {r.player:<22} yr {r.exp:>2.0f}  WR{r.finish:>3.0f}"
             f"  ->  {'did not play' if pd.isna(r.next_finish) else f'WR{r.next_finish:.0f}'}"
             for _, r in g.iterrows()]
    if len(lines) > k:
        lines = lines[:k // 2] + [f"      ... {len(lines) - k} more ..."] + lines[-(k // 2):]
    print("\n".join(lines) if lines else "      (none)")


def rule(title, char="="):
    print("\n" + char * 78)
    print(title)
    print(char * 78)


def fit_predict(train, test, cols, y="next_ppg_c"):
    """Fit on `train`, predict on `test`. Standardisation uses train only."""
    X, Xt = train[cols].to_numpy(float), test[cols].to_numpy(float)
    mu, sd = X.mean(0), np.where(X.std(0) == 0, 1.0, X.std(0))
    beta, *_ = np.linalg.lstsq(np.c_[np.ones(len(X)), (X - mu) / sd],
                               train[y].to_numpy(float), rcond=None)
    return np.c_[np.ones(len(Xt)), (Xt - mu) / sd] @ beta


def main():
    df = build()
    s = sample(df)
    MODEL, model_r2 = forward_select(s, [c for c in FEATURES if c in s.columns])
    print(f"Reference model (forward-selected, leave-one-season-out R2 = {model_r2:.4f}):")
    print("  " + ", ".join(f"{c} ({FEATURES[c]})" for c in MODEL))
    _, pred = loso_r2(s, MODEL)
    s = s.copy()
    s["model_ppg"] = pred
    s["resid"] = s.next_ppg_c - s.model_ppg

    base = describe(s, pd.Series(True, index=s.index), "every WR season in the sample")

    # ------------------------------------------------------------------ A ---
    rule("ARCHETYPE A - the five-week WR1")
    print("A top-10-ish finish carried by a handful of enormous weeks, from a")
    print("receiver who had never done anything before.\n")
    a_top = s.finish.between(4, 15) & (s.games >= 14)
    a_spike = s.top5_share >= 0.45
    a_quiet = s.prior_top24 == 0
    a_career = s.exp >= 2
    A = a_top & a_spike & a_quiet & a_career
    show([base] + [describe(s, sel, lab) for lab, sel in [
        ("finished WR4-15, 14+ games", a_top),
        ("  + top 5 games are 45%+ of his points", a_top & a_spike),
        ("  + never a top-24 season before", a_top & a_spike & a_quiet),
        ("  + not a rookie (a career to be quiet in)", A),
    ]])
    print("\n    Dose-response on the spike itself, inside the WR4-15 group:")
    show([describe(s, a_top & (s.top5_share < 0.42), "  top-5 share under 42%"),
          describe(s, a_top & s.top5_share.between(0.42, 0.50), "  42-50%"),
          describe(s, a_top & (s.top5_share > 0.50), "  over 50%"),
          describe(s, a_top & (s.top5_share > 0.55), "  over 55%")])
    print("\n    Control: same finish range and era, but not spike-built and/or")
    print("    with a top-24 season already on the shelf.")
    show([describe(s, a_top & ~A, "  WR4-15 finishers who are not archetype A")])
    print("\n    Who they were:")
    roster(s, A)

    # ------------------------------------------------------------------ B ---
    rule("ARCHETYPE B - the sophomore crash")
    print("A monster rookie year, then injury and a slump in year two.\n")
    print("First, the fact that governs everything else: since 2000 only ten")
    print("receivers have finished top-12 as a rookie.  Here is every one, with")
    print("what happened in year two and year three.\n")
    rook = df[(df.exp == 1) & (df.finish <= 12)][["player_id", "season", "player", "finish"]]
    for _, r in rook.sort_values("season").iterrows():
        after = df[(df.player_id == r.player_id) & df.season.between(r.season + 1, r.season + 2)]
        after = {int(x.season - r.season): x for _, x in after.iterrows()}
        def fin(k):
            x = after.get(k)
            if x is None:
                return "  -  "
            return f"WR{x.finish:>3.0f}" + (f" ({x.games:.0f}g)" if x.games < 14 else "     ")
        print(f"      {int(r.season)}  {r.player:<22} rookie WR{r.finish:>3.0f}"
              f"   yr2 {fin(1)}   yr3 {fin(2)}")

    b_exact = (s.exp == 2) & (s.prev_finish <= 12) & (s.finish >= 30)
    b_near = (s.exp == 2) & (s.prev_finish <= 24) & (s.finish >= 30)
    b_wide = (s.exp <= 4) & (s.best_prior_finish <= 12) & (s.finish >= 30)
    b_wide_hurt = b_wide & (s.missed >= 2)
    print("\n    The cohorts:\n")
    show([base] + [describe(s, sel, lab) for lab, sel in [
        ("exact: 2nd yr, rookie top-12, yr2 outside top-30", b_exact),
        ("near:  2nd yr, rookie top-24, yr2 outside top-30", b_near),
        ("wide:  yrs 1-4, a top-12 season behind him, now outside top-30", b_wide),
        ("  + missed 2+ games in the down year", b_wide_hurt),
    ]])
    B = b_wide
    print("\n    Control: same age band, same collapse, but no top-12 season behind him.")
    show([describe(s, (s.exp <= 4) & (s.best_prior_finish > 24) & (s.finish >= 30),
                   "  yrs 1-4, outside top-30, never top-24")])
    print("\n    Who the wide cohort were:")
    roster(s, B)

    # ------------------------------------------------------------------ C ---
    rule("ARCHETYPE C - the hurt efficient one")
    print("Missed real time, but the targets and the per-target production were")
    print("there, and the per-game pace says the healthy version was a top-15 WR.")
    print("Behind him, a younger receiver on the same team finished strong.\n")
    eff_hi = s.groupby("season").ppr_per_target.transform(lambda x: x.quantile(2 / 3))
    c_year = s.exp.between(2, 4)
    c_hurt = s.missed >= 3
    c_pace = s.pace_finish <= 18
    c_vol = s.tpg >= 6.0
    c_eff = s.ppr_per_target >= eff_hi
    c_mate = s.mate_threat == 1
    C = c_year & c_hurt & c_pace & c_vol & c_eff
    show([base] + [describe(s, sel, lab) for lab, sel in [
        ("years 2-4, missed 3+ games", c_year & c_hurt),
        ("  + healthy-pace finish inside WR18", c_year & c_hurt & c_pace),
        ("  + 6+ targets per game", c_year & c_hurt & c_pace & c_vol),
        ("  + top-third efficiency (PPR per target)", C),
        ("  + a 1st/2nd-year teammate finished top-36", C & c_mate),
    ]])
    print("\n    Control: hurt receivers of the same age whose pace was NOT top-18.")
    show([describe(s, c_year & c_hurt & ~c_pace, "  years 2-4, missed 3+, pace outside WR18")])
    print("\n    Does the young teammate matter?")
    show([describe(s, C & c_mate, "  young riser behind him"),
          describe(s, C & ~c_mate, "  no young riser")])
    print("\n    Who they were (before the teammate condition):")
    roster(s, C, k=99)

    # ------------------------------------------------------------ head to head
    rule("HEAD TO HEAD")
    cohorts = [("A  five-week WR1", A), ("B  young ex-WR1, off a collapse", B),
               ("C  hurt + efficient", C)]
    print("Season N+1, all seasons pooled:\n")
    show([describe(s, sel, lab) for lab, sel in cohorts] + [base])
    print(f"\n    Overlap: A n B = {(A & B).sum()},  A n C = {(A & C).sum()},"
          f"  B n C = {(B & C).sum()}")

    print("\nP(the row archetype finishes ahead of the column archetype) next")
    print("season, over every ordered pair of members, ties split.\n")
    names = [c[0] for c in cohorts]
    M = pd.DataFrame(index=names, columns=names, dtype=float)
    for i, (_, si) in enumerate(cohorts):
        for j, (_, sj) in enumerate(cohorts):
            if i == j:
                continue
            a, b = s[si].next_finish_c.to_numpy(), s[sj].next_finish_c.to_numpy()
            M.iloc[i, j] = 100 * ((a[:, None] < b[None, :]).mean()
                                  + 0.5 * (a[:, None] == b[None, :]).mean())
    print(M.to_string(float_format=lambda v: "" if np.isnan(v) else f"{v:.0f}%"))

    print("\nMann-Whitney on next-season points per game:\n")
    for i in range(len(cohorts)):
        for j in range(i + 1, len(cohorts)):
            u = stats.mannwhitneyu(s[cohorts[i][1]].next_ppg_c, s[cohorts[j][1]].next_ppg_c)
            print(f"    {cohorts[i][0]:<32} vs {cohorts[j][0]:<32} p = {u.pvalue:.3f}")

    print("\nAgainst the model that knows nothing about archetypes.  'beat' is")
    print("actual next-season ppg minus what the reference model predicted; a")
    print("cohort the standard metrics misprice shows a beat away from zero.\n")
    for lab, sel in cohorts:
        g = s[sel]
        t = stats.ttest_1samp(g.resid.dropna(), 0)
        print(f"    {lab:<32} n = {len(g):>3}   beat = {g.resid.mean():+.2f} ppg   "
              f"t = {t.statistic:+.2f}   p = {t.pvalue:.3f}")

    # ---------------------------------------------------------------- today
    rule("WHO FITS RIGHT NOW, AND WHAT THE MODEL SAYS")
    last = int(df.season.max())
    cur = sample(df, with_next=False)
    cur = cur[cur.season == last].copy()
    train = s
    cur["proj_ppg"] = fit_predict(train, cur, MODEL)
    cur["proj_rank"] = cur.proj_ppg.rank(ascending=False, method="min")
    eff_cut = cur.ppr_per_target.quantile(2 / 3)
    tags = {
        "A  five-week WR1": cur.finish.between(4, 15) & (cur.games >= 14)
            & (cur.top5_share >= 0.45) & (cur.prior_top24 == 0) & (cur.exp >= 2),
        "B  young ex-WR1, off a collapse": (cur.exp <= 4) & (cur.best_prior_finish <= 12)
            & (cur.finish >= 30),
        "C  hurt + efficient": cur.exp.between(2, 4) & (cur.missed >= 3)
            & (cur.pace_finish <= 18) & (cur.tpg >= 6.0) & (cur.ppr_per_target >= eff_cut),
    }
    print(f"{last} receivers matching each archetype, with the reference model's")
    print(f"projection for {last + 1} (points per game, and where that ranks among")
    print(f"all {len(cur)} qualifying {last} receivers).\n")
    for k, sel in tags.items():
        g = cur[sel].sort_values("proj_ppg", ascending=False)
        print(f"  {k}: {len(g)} receiver(s)")
        for _, r in g.iterrows():
            mate = "-" if pd.isna(r.mate_finish) else f"WR{r.mate_finish:.0f}/yr{r.mate_exp:.0f}"
            print(f"      {r.player:<22} yr {r.exp:.0f}  WR{r.finish:>3.0f}  pace WR{r.pace_finish:>3.0f}"
                  f"  {r.games:>2.0f}g  top5 {100 * r.top5_share:>3.0f}%  {r.tpg:>4.1f} tgt/g"
                  f"  {r.ppr_per_target:.2f} ppr/tgt  mate {mate:<10}"
                  f"  proj {r.proj_ppg:>5.2f} ppg (#{r.proj_rank:.0f})")
        print()


if __name__ == "__main__":
    main()
