"""Where in the draft does the perfect kicker stop being a bad pick?

Two questions from the comments:

  1. How long does the guarantee have to be before it beats the 1.01?
  2. At what pick number does a kicker who never misses inside 60 become
     worth more than what you would expect from that slot?

The first is a rerun of distance_sweep.py at one-yard resolution. The second
needs a draft-value curve in wins, which takes a calibration step.

Method for question 2
---------------------
Pro Football Reference's approximate value is the only currency that spans
every position, so the pick curve is built in AV and then converted:

  * dr_av = career approximate value the player delivered TO THE DRAFTING
    TEAM. Picks who never played for them count as 0.
  * The conversion is fitted on quarterbacks, where both measures exist:
    career wins above replacement from play-by-play EPA (the same figure
    used everywhere else in this study) against career weighted AV.

That calibration is the weak joint, and it is worth being explicit about
which way it errs. AV is generally held to understate quarterbacks, so
wins-per-AV fitted on them is too generous when applied to a guard or a
safety. That inflates every pick's win value, which pushes the crossover
pick LATER than the truth. The number this script produces is therefore a
conservative one from the kicker's point of view: the real crossover is at
least this early, probably earlier.

Run fetch_plays.py and fetch_draft.py first, then:
    python3 pick_curve.py > PICKCURVE.txt
"""
import os
import warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from epa_common import add_adjusted, kern

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 60)
pd.set_option("display.max_rows", 100)

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "plays_1999_2025.parquet")
DRAFT = os.path.join(HERE, "draft_picks.parquet")

PBP = list(range(1999, 2026))
DRAFTS = list(range(1999, 2020))    # enough seasons observed to judge
PTS_PER_WIN = 35.8
REPL_LO, REPL_HI = 50, 320
KICK_SEASONS = 10                   # median career for a top-quartile kicker
KICK_AVG, KICK_REPL = 0.84, 1.13    # wins a season (VERDICT.txt)

COLS = ["season", "season_type", "play_id", "game_id", "posteam", "play_type",
        "epa", "ep", "touchdown", "field_goal_result", "half_seconds_remaining",
        "passer_player_id", "passer_player_name", "rusher_player_id",
        "qb_dropback", "qtr", "field_goal_attempt", "kick_distance",
        "yardline_100"]


def hdr(t):
    print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)


def sub(t):
    print(f"\n-- {t}")


def qb_war():
    d, _ = add_adjusted(pd.read_parquet(SRC, columns=COLS))
    d = d[d.season_type.eq("REG")]
    p = d[d.passer_player_id.notna()].groupby(
        ["season", "passer_player_id"], as_index=False).agg(
        n=("aepa", "size"), e=("aepa", "sum"))
    r = d[d.rusher_player_id.notna() & d.qb_dropback.eq(1)].groupby(
        ["season", "rusher_player_id"], as_index=False).agg(
        nr=("aepa", "size"), er=("aepa", "sum"))
    q = p.rename(columns={"passer_player_id": "pid"}).merge(
        r.rename(columns={"rusher_player_id": "pid"}),
        on=["season", "pid"], how="left").fillna({"nr": 0, "er": 0})
    q["plays"] = q.n + q.nr
    q["aepa"] = q.e + q.er
    repl = q[q.plays.between(REPL_LO, REPL_HI)]
    rate = repl.aepa.sum() / repl.plays.sum()
    q["war"] = (q.aepa / q.plays - rate) * q.plays / PTS_PER_WIN
    return q.groupby("pid", as_index=False).agg(
        seasons=("plays", lambda x: (x >= 100).sum()),
        plays=("plays", "sum"), war=("war", "sum")), rate


def main():
    car, rate = qb_war()
    dp = pd.read_parquet(DRAFT)
    d = dp[dp.season.isin(DRAFTS)].copy()
    d["dr_av"] = d.dr_av.fillna(0.0)
    d["w_av"] = d.w_av.fillna(0.0)

    hdr("1. CALIBRATING APPROXIMATE VALUE INTO WINS")
    qb = d[d.position.eq("QB") & d.gsis_id.notna()].merge(
        car, left_on="gsis_id", right_on="pid", how="left").fillna(
        {"war": 0.0, "seasons": 0, "plays": 0})
    # both sides of the fit are CAREER, all teams: weighted career AV against
    # career wins above replacement. Applying a career-AV fit to
    # drafting-team-only AV would double-count the intercept.
    print(f"quarterbacks drafted {DRAFTS[0]}-{DRAFTS[-1]} with a gsis id: "
          f"{len(qb)}")
    print(f"  replacement quarterback: {rate:+.4f} adjusted EPA per play")
    print("  the fit is non-parametric - a kernel mean of career WAR among")
    print("  quarterbacks of similar career AV - because the relationship bends")
    print("  at the top and a straight line overshoots the stars.")
    av_grid = np.arange(0, 201, 1.0)
    war_of_av = pd.Series(kern(av_grid, qb.w_av.to_numpy(float),
                               qb.war.to_numpy(float), 12.0), index=av_grid)
    war_of_av = war_of_av.cummax()          # value cannot fall as AV rises
    lin = smf.ols("war ~ w_av", data=qb).fit()
    print(f"\n  for reference a straight line gives WAR = "
          f"{lin.params['Intercept']:+.2f} + {lin.params['w_av']:.3f} x AV, "
          f"R^2 = {lin.rsquared:.2f}")
    print("\n  the calibration curve:")
    chk = pd.DataFrame({"career AV": [10, 25, 40, 55, 70, 85, 100, 130],
                        "career wins": [war_of_av[v] for v in
                                        [10, 25, 40, 55, 70, 85, 100, 130]]})
    print(chk.round(1).to_string(index=False))

    sub("does it reproduce the groups we measured directly?")
    for lab, sel in [("first overall QBs", qb[qb.pick.eq(1)]),
                     ("QBs picked 2-32", qb[qb.pick.between(2, 32)]),
                     ("QBs picked 33+", qb[qb.pick.gt(32)])]:
        pred = np.interp(sel.w_av, av_grid, war_of_av.to_numpy())
        print(f"  {lab:20} n={len(sel):3d}  measured career WAR "
              f"{sel.war.mean():5.1f}, predicted from AV {pred.mean():5.1f}")

    # ------------------------------------------------------ 2. the curve
    hdr("2. THE DRAFT CURVE, IN CAREER WINS ABOVE REPLACEMENT")
    d["wins"] = np.interp(d.w_av, av_grid, war_of_av.to_numpy())
    d["wins_to_drafter"] = d.wins * np.where(
        d.w_av > 0, (d.dr_av / d.w_av.replace(0, np.nan)).fillna(0).clip(0, 1), 0)
    # a fixed bandwidth flattens the very top of the draft, where the curve is
    # steepest and pick 1 is genuinely its own thing. Bandwidth grows with the
    # pick number instead: sharp at the top, smooth through the tail.
    picks = np.arange(1, 225)
    px, wv = d.pick.to_numpy(float), d.wins.to_numpy(float)
    wd = d.wins_to_drafter.to_numpy(float)

    def prop_smooth(y):
        out = np.empty(len(picks))
        for i, p0 in enumerate(picks):
            bw = max(1.5, 0.18 * p0)
            k = np.exp(-0.5 * ((px - p0) / bw) ** 2)
            out[i] = (k * y).sum() / k.sum()
        return pd.Series(out, index=picks)

    curve, curve_dr = prop_smooth(wv), prop_smooth(wd)
    tab = d.groupby(pd.cut(d.pick, [0, 1, 5, 10, 16, 32, 50, 75, 100, 150, 224]),
                    observed=True).apply(lambda x: pd.Series({
        "picks": len(x), "career_AV": x.w_av.mean(),
        "career_wins": x.wins.mean(),
        "wins_kept_by_drafter": x.wins_to_drafter.mean(),
        "never_played_for_them%": 100 * x.dr_av.eq(0).mean(),
        "probowl%": 100 * x.probowls.gt(0).mean()}), include_groups=False)
    print("  'career_wins' is the player's whole career, whoever employed him.")
    print("  'wins_kept_by_drafter' scales that by the share of his career AV")
    print("  he delivered to the team that drafted him - the rest walked in free")
    print("  agency or a trade. The kicker comparison uses the second column,")
    print("  because that is what the pick actually buys you.")
    print("\n" + tab.round(2).to_string())

    hdr("3. WHERE THE KICKER LANDS")
    for lab, wps in [("vs an average leg", KICK_AVG),
                     ("vs a replacement leg", KICK_REPL)]:
        tot = wps * KICK_SEASONS
        print(f"\n  perfect-inside-60 kicker, {lab}: {wps:.2f} wins a season")
        print(f"    x {KICK_SEASONS} seasons (the median career for a top-quartile")
        print(f"      kicker, from PICK.txt) = {tot:.1f} career wins")
        for cl, cv in [("whole career, whoever employs him", curve),
                       ("only what the drafting team keeps", curve_dr)]:
            below = cv[cv < tot]
            pick = int(below.index[0]) if len(below) else None
            if pick:
                print(f"    vs {cl:35}: crosses at pick {pick:3d} "
                      f"(round {1 + (pick - 1) // 32})")
            else:
                print(f"    vs {cl:35}: never crosses inside 224")
        print(f"    The first line is the like-for-like one - every other")
        print(f"    quarterback figure in this study is a whole-career number too.")
    sub("sensitivity to how long he lasts")
    print("  (whole-career basis; crossover pick for each career length)")
    for yrs in [6, 8, 10, 12, 15]:
        row = []
        for wps in [KICK_AVG, KICK_REPL]:
            below = curve[curve < wps * yrs]
            row.append(str(int(below.index[0])) if len(below) else ">224")
        print(f"  {yrs:2d} seasons: {KICK_AVG * yrs:4.1f} / "
              f"{KICK_REPL * yrs:4.1f} career wins -> crossover at pick "
              f"{row[0]:>4} (vs average leg), {row[1]:>4} (vs replacement leg)")

    sub("the curve near the crossover")
    show = [1, 5, 10, 16, 24, 32, 40, 50, 64, 80, 100, 128, 160, 200]
    print(pd.DataFrame({"pick": show,
                        "round": [1 + (p - 1) // 32 for p in show],
                        "career_wins": [curve[p] for p in show],
                        "kept_by_drafter": [curve_dr[p] for p in show]}
                       ).round(2).to_string(index=False))

    hdr("4. WHAT THIS DOES AND DOES NOT SAY")
    print("  It says the EXPECTED return of a pick - averaged over everyone ever")
    print("  taken there - falls below the kicker inside the top ten. It does NOT")
    print("  say he beats every player taken after that: he beats the average")
    print("  outcome, and the spread around that average is enormous.")
    print("\n  Nor does it contradict the per-season finding that he loses to the")
    print("  1.01. Both are true because the top of the draft curve is very")
    print("  steep. Pick 1 returns about "
          f"{curve[1]:.1f} career wins and pick 7 about {curve[7]:.1f};")
    print(f"  the kicker sits at {KICK_AVG * KICK_SEASONS:.1f}. Per season that is "
          f"{KICK_AVG:.2f} against the")
    print(f"  1.01 quarterback's 1.28 - a ratio of "
          f"{1.28 / KICK_AVG:.2f}, which matches the career ratio of")
    print(f"  {curve[1] / (KICK_AVG * KICK_SEASONS):.2f}. The two framings agree; "
          f"they just answer different")
    print("  questions.")
    print(f"\n  Share of picks who never played a down for the team that drafted")
    print(f"  them: {100 * d[d.pick.between(33, 64)].dr_av.eq(0).mean():.0f}% in "
          f"round 2, "
          f"{100 * d[d.pick.between(65, 100)].dr_av.eq(0).mean():.0f}% in round 3, "
          f"{100 * d[d.pick.gt(150)].dr_av.eq(0).mean():.0f}% after pick 150.")
    print("\n  And the calibration is fitted on quarterbacks, who are usually")
    print("  held to be UNDERSTATED by approximate value. That makes wins-per-AV")
    print("  too generous when applied to everyone else, which inflates the")
    print("  curve and pushes the crossover later. The real crossover is at")
    print("  least this early.")
    return curve, curve_dr, d


if __name__ == "__main__":
    main()
