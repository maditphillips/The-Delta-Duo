"""The bottom line, with the baselines finally matched.

Every valuation in this study has the same shape:

    value = (team WITH the thing) - (team WITHOUT the thing)

Both sides always have the perfect kicker in the first term. What the earlier
scripts differ on is the SECOND term - what "without him" means - and that is
where a mismatch crept in:

    the kicker was being priced against an AVERAGE NFL leg
    the quarterback was being priced against a REPLACEMENT quarterback

Those are not the same rung. An average leg is a good kicker; a replacement
quarterback is a bad quarterback. Comparing one against the other flattered
the quarterback. This script prices the kicker on both rungs so the
like-for-like comparison is available.

The comparison leg's miss rate is scaled: x1.0 is the league-average leg,
x1.46 is the rate that mid-season fill-in kickers (5 to 20 attempt seasons)
actually posted. Coaching is held IDENTICAL in both worlds - real NFL
behaviour, plus taking a guaranteed three when it beats the play that was
actually called - so nothing in here is credit for fixing a fourth-down chart.

Run fetch_plays.py first, then:  python3 verdict.py > VERDICT.txt
"""
import os
import warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

from epa_common import SNAP_TO_KICK, add_adjusted, kern

pd.set_option("display.width", 200)

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "plays_1999_2025.parquet")

WINDOW = list(range(2018, 2026))
MAX_YL = 42
GAMES = 17
SLOPE = 0.02796          # win% per point of margin per game, 2018-2025
BASE_WINS = 8.5

# from PICK.txt: all 17 quarterbacks taken first overall 1999-2021, priced
# against a REPLACEMENT quarterback over the five years of the rookie deal
QB_MEAN, QB_MEDIAN = 1.28, 1.59
QB_BELOW = {"0.84": 35.3, "1.13": 58.8}   # % of them under each kicker figure
QB_CUM10 = 11.71         # mean cumulative WAR through career year 10


def hdr(t):
    print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)


def sub(t):
    print(f"\n-- {t}")


def main():
    d, _ = add_adjusted(pd.read_parquet(SRC), fit_seasons=WINDOW)
    w = d[d.season.isin(WINDOW)].copy()
    n_tg = 2 * w.game_id.nunique()
    tsn = n_tg / GAMES
    yls = np.arange(1, MAX_YL + 1)
    fgs = w[w.is_fg & w.dist.le(60)].copy()

    pm = smf.glm("made ~ bs(dist, df=5)",
                 data=fgs.assign(made=fgs.made.astype(int)),
                 family=sm.families.Binomial()).fit()
    miss_v = pd.Series(kern(yls, fgs[~fgs.made].yardline_100.to_numpy(float),
                            fgs[~fgs.made].aepa.to_numpy(float), 6.0), index=yls)

    # how much worse than average is a mid-season fill-in?
    cnt = fgs.groupby(["kicker_player_id", "season"]).size().rename("att")
    fill = set(map(tuple, cnt[cnt.between(5, 20)].index))
    fgs["isfill"] = [(k, s) in fill for k, s in
                     zip(fgs.kicker_player_id, fgs.season)]
    p_all = pm.predict(fgs).to_numpy()
    repl_scale = ((1 - fgs.loc[fgs.isfill, "made"].mean())
                  / (1 - p_all[fgs.isfill.to_numpy()].mean()))

    f = w[w.down.eq(4) & w.yardline_100.le(MAX_YL)
          & w.play_type.isin(["punt", "pass", "run"])].copy()
    go = f[f.play_type.isin(["pass", "run"])]
    go_v = go.groupby(go.ydstogo.clip(upper=11)).aepa.mean()
    punts = f[f.play_type.eq("punt")]
    punt_v = pd.Series(kern(yls, punts.yardline_100.to_numpy(float),
                            punts.aepa.to_numpy(float), 6.0), index=yls)
    v_alt = np.where(f.play_type.eq("punt"),
                     f.yardline_100.round().astype(int).map(punt_v),
                     f.ydstogo.clip(upper=11).map(go_v).astype(float))
    p_f = pm.predict(pd.DataFrame(
        {"dist": f.yardline_100 + SNAP_TO_KICK})).to_numpy()
    xp = w[w.extra_point_attempt.fillna(0).eq(1) & w.extra_point_result.notna()]
    xp_miss = 1 - xp.extra_point_result.eq("good").mean()

    def leg(scale):
        """Points a season the guarantee adds over a leg whose miss rate is
        `scale` x the league average, coaching held identical."""
        p = 1 - scale * (1 - p_all)
        base = p * fgs.v_perfect + (1 - p) * fgs.yardline_100.round().astype(int).map(miss_v)
        ch1 = (fgs.v_perfect - base).sum() / tsn
        pf = 1 - scale * (1 - p_f)
        basef = pf * f.v_perfect + (1 - pf) * f.yardline_100.round().astype(int).map(miss_v)
        ch3 = (np.maximum(0, f.v_perfect - v_alt)
               - np.maximum(0, basef - v_alt)).sum() / tsn
        ch5 = len(xp) * scale * xp_miss / tsn
        return ch1, ch3, ch5

    hdr("1. THE MISMATCH, AND THE FIX")
    print(f"the comparison leg, two rungs:")
    print(f"  AVERAGE     : the league's own make curve, {100 * fgs.made.mean():.1f}% "
          f"inside 60")
    print(f"  REPLACEMENT : the mid-season fill-in. Kicker-seasons of 5-20")
    print(f"                attempts ({fgs.isfill.sum():,} attempts) made "
          f"{100 * fgs.loc[fgs.isfill, 'made'].mean():.1f}% against "
          f"{100 * p_all[fgs.isfill.to_numpy()].mean():.1f}%")
    print(f"                expected, a miss rate of x{repl_scale:.2f}")
    print("\nthe quarterback is priced against a REPLACEMENT quarterback, so the")
    print("second row below is the like-for-like comparison. The first row is the")
    print("practically relevant one, because a team that passes on this kicker")
    print("signs an average leg that afternoon, while a team that passes on the")
    print("quarterback actually does play a replacement quarterback.")

    hdr("2. WHAT THE GUARANTEE IS WORTH - ALL FOUR COMBINATIONS")
    print("Two independent choices, so four cells. The PERFECT leg is in the")
    print("'with' term of all four; the rows are what gets subtracted, and the")
    print("columns are what coaching BOTH teams get.")

    # optimal-coaching variant: both legs pick the best of kick / go / punt on
    # every fourth down, so the only difference left is the leg
    fourth = w[w.down.eq(4) & w.play_type.isin(["field_goal", "punt", "pass", "run"])
               & w.yardline_100.notna()].copy()
    tgo = fourth.ydstogo.clip(lower=1, upper=11).round().astype(int)
    gv_all = w[w.down.eq(4) & w.play_type.isin(["pass", "run"])]
    gvm = gv_all.groupby(gv_all.ydstogo.clip(upper=11)).aepa.mean()
    grid = np.arange(1, 100)
    pv_all = pd.Series(kern(grid, gv_all.yardline_100.to_numpy(float),
                            gv_all.yardline_100.to_numpy(float) * 0, 5.0), index=grid)
    allp = w[w.down.eq(4) & w.play_type.eq("punt")]
    punt_full = pd.Series(kern(grid, allp.yardline_100.to_numpy(float),
                               allp.aepa.to_numpy(float), 5.0), index=grid)
    fourth["v_go"] = tgo.map(gvm).astype(float)
    fourth["v_punt"] = fourth.yardline_100.round().astype(int).map(punt_full)
    fir = fourth.yardline_100.le(MAX_YL).to_numpy()
    p4 = np.full(len(fourth), np.nan)
    p4[fir] = pm.predict(pd.DataFrame(
        {"dist": fourth.loc[fir, "yardline_100"] + SNAP_TO_KICK})).to_numpy()
    fourth["v_kick_perf"] = np.where(fir, fourth.v_perfect, np.nan)

    def optimal(scale):
        pb = 1 - scale * (1 - p4)
        v_base_kick = np.where(
            fir, pb * fourth.v_perfect
            + (1 - pb) * fourth.yardline_100.round().astype(int).map(miss_v), np.nan)
        best_perf = np.nanmax(np.vstack(
            [fourth.v_go, fourth.v_kick_perf, fourth.v_punt]), axis=0)
        best_base = np.nanmax(np.vstack(
            [fourth.v_go, v_base_kick, fourth.v_punt]), axis=0)
        # field goals off fourth down sit outside the policy, so add them once
        off4 = w[w.is_fg & w.dist.le(60) & ~w.down.eq(4)]
        po = 1 - scale * (1 - pm.predict(pd.DataFrame({"dist": off4.dist})).to_numpy())
        off = (off4.v_perfect - (po * off4.v_perfect + (1 - po)
               * off4.yardline_100.round().astype(int).map(miss_v))).sum() / tsn
        ch5 = len(xp) * scale * xp_miss / tsn
        return (np.nansum(best_perf - best_base) / tsn) + off + ch5

    cells = {}
    for rlab, sc in [("vs an AVERAGE leg", 1.0), ("vs a REPLACEMENT leg", repl_scale)]:
        c1, c3, c5 = leg(sc)
        cells[(rlab, "real coaching")] = SLOPE * (c1 + c3 + c5)
        cells[(rlab, "optimal coaching")] = SLOPE * optimal(sc)
    grid_out = pd.DataFrame(
        [[cells[(rl, cl)] for cl in ["real coaching", "optimal coaching"]]
         for rl in ["vs an AVERAGE leg", "vs a REPLACEMENT leg"]],
        index=["vs an AVERAGE leg", "vs a REPLACEMENT leg"],
        columns=["real coaching", "optimal coaching"])
    grid_out.index.name = "what is subtracted"
    print("\n" + grid_out.round(2).to_string())
    avg_w = grid_out.loc["vs an AVERAGE leg", "real coaching"]
    repl_w = grid_out.loc["vs a REPLACEMENT leg", "real coaching"]
    print("\n  'real coaching' = what teams actually called, plus taking a")
    print("  guaranteed three when it beats that call. 'optimal coaching' = both")
    print("  teams take the best of kick/go/punt on every fourth down.")
    print("\n  Optimal coaching LOWERS the guarantee's value, because a well-coached")
    print("  team with an ordinary leg already kicks the 56-yarders and goes for it")
    print("  near the goal line. Better coaching substitutes for a better kicker.")
    print("\n  the components, real coaching:")
    for rlab, sc in [("vs an AVERAGE leg", 1.0), ("vs a REPLACEMENT leg", repl_scale)]:
        c1, c3, c5 = leg(sc)
        print(f"    {rlab:22}: kicks he takes {c1:5.1f} + kicks he unlocks "
              f"{c3:5.1f} + XP {c5:4.1f} = {c1 + c3 + c5:5.1f} pts")
    print("\n  A NOTE ON 0.94, which appeared in earlier drafts: that figure did")
    print("  not subtract the part an ordinary leg would also have captured on the")
    print("  fourth downs he 'unlocks'. Correcting that gives the 0.84 above. Use")
    print("  this table; 0.94 is superseded.")
    r = grid_out

    hdr("3. AGAINST THE 1.01")
    print(f"{'':34}{'wins/season':>13}{'certain?':>11}")
    print(f"  {'perfect leg, vs average leg':32}{avg_w:>12.2f}{'yes':>11}")
    print(f"  {'perfect leg, vs replacement leg':32}{repl_w:>12.2f}{'yes':>11}")
    print(f"  {'1.01 QB, vs replacement QB (mean)':32}{QB_MEAN:>12.2f}{'no':>11}")
    print(f"  {'1.01 QB, vs replacement QB (median)':32}{QB_MEDIAN:>12.2f}{'no':>11}")
    print(f"\n  like-for-like, both against replacement: "
          f"{repl_w:.2f} certain against {QB_MEAN:.2f} expected.")
    print(f"  That is a {100 * (QB_MEAN - repl_w) / QB_MEAN:.0f}% edge to the "
          f"quarterback on the mean, and "
          f"{QB_BELOW['1.13']:.0f}% of the seventeen")
    print(f"  first overall quarterbacks since 1999 came in BELOW {repl_w:.2f} over "
          f"their")
    print(f"  rookie deal. The kicker's figure has no distribution at all.")
    print(f"\n  on the practical baseline: {avg_w:.2f} against {QB_MEAN:.2f}, and "
          f"{QB_BELOW['0.84']:.0f}% of them came in below.")

    sub("over a career, not a season")
    for lab, wv in [("vs average leg", avg_w), ("vs replacement leg", repl_w)]:
        print(f"  kicker at {wv:.2f} a year for 10 years {lab:20}: "
              f"{10 * wv:5.1f} wins")
    print(f"  average 1.01 quarterback, cumulative through year 10 : "
          f"{QB_CUM10:5.1f} wins")
    print(f"\n  On the like-for-like baseline that is {10 * repl_w:.1f} against "
          f"{QB_CUM10:.1f} - a dead heat over a decade,")
    print(f"  with the kicker's half of it guaranteed and the quarterback's a draw")
    print(f"  from a distribution that includes JaMarcus Russell. On the practical")
    print(f"  baseline the quarterback wins clearly, {QB_CUM10:.1f} to "
          f"{10 * avg_w:.1f}.")

    hdr("4. THE VERDICT, STATED HONESTLY")
    print("  It depends on a baseline choice, and that should be said out loud")
    print("  rather than buried:")
    print(f"\n  - If passing on the kicker means signing an ordinary NFL leg -")
    print(f"    which is what actually happens, because average kickers are")
    print(f"    available on any Tuesday - he is worth {avg_w:.2f} wins and the "
          f"quarterback")
    print(f"    wins comfortably, {QB_MEAN:.2f} on the mean and {QB_MEDIAN:.2f} on "
          f"the median.")
    print(f"\n  - If you insist on the strictly symmetric comparison, replacement")
    print(f"    against replacement, he is worth {repl_w:.2f} guaranteed against "
          f"{QB_MEAN:.2f}")
    print(f"    expected, {QB_BELOW['1.13']:.0f}% of quarterbacks came in under him, "
          f"and over ten")
    print(f"    years it is a coin flip. On that framing the risk-adjusted case")
    print(f"    for the kicker is real, not a joke.")
    print(f"\n  The first framing is the better answer to the question as asked,")
    print(f"  because the alternative to drafting a kicker is not fielding a")
    print(f"  replacement kicker. But the honest range for 'would you be mad' is")
    print(f"  'yes, and less than you would expect'.")
    return r, repl_scale


if __name__ == "__main__":
    main()
