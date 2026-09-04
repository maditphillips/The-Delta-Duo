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

    hdr("2. WHAT THE GUARANTEE IS WORTH")
    rows = []
    for lab, sc in [("vs an AVERAGE leg", 1.0),
                    ("vs a REPLACEMENT leg", repl_scale)]:
        c1, c3, c5 = leg(sc)
        tot = c1 + c3 + c5
        rows.append({"baseline": lab, "ch1_kicks_he_takes": c1,
                     "ch3_kicks_he_unlocks": c3, "ch5_extra_points": c5,
                     "points": tot, "wins": SLOPE * tot})
    r = pd.DataFrame(rows)
    print(r.round(2).to_string(index=False))
    avg_w, repl_w = r.wins.iloc[0], r.wins.iloc[1]
    print("\n  coaching is identical on both sides of every one of these numbers,")
    print("  so none of it is credit for fixing a fourth-down chart.")

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
