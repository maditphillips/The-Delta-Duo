"""The break-even question: at what conversion rate should you just kick it?

The back-of-envelope version says: a touchdown is 7, a guaranteed field goal
is 3, so going for it needs P x 7 > 3, and the break-even is 3/7 = 42.9%.

The premise is wrong in one place. Converting a fourth down does not buy a
touchdown, it buys a FIRST DOWN, and what a first down is worth depends
entirely on where you are. A fresh first and ten at the opponent's 10 is
worth 5.0 expected points; at the 42 it is worth 3.4; at midfield 2.9. So the
prize shrinks as you move back, which means the break-even conversion rate
RISES as you move back. It is not one number.

This script measures all three legs from the data and then sweeps a single
threshold policy over every fourth down in the game:

    if the league converts this yards-to-go at least P*, go for it
    otherwise kick it (inside the 42) or punt it (outside)

P* = 0 is "go for it on every fourth down, all game". P* = 100 is "never go
for it". Everything in between is a combo. Run fetch_plays.py first, then:

    python3 threshold.py > THRESHOLD.txt
"""
import os
import warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

from epa_common import SNAP_TO_KICK, add_adjusted, kern

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 60)

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "plays_1999_2025.parquet")

WINDOW = list(range(2018, 2026))
MAX_YL = 42                 # a 60-yard attempt
GAMES = 17
GO = ["pass", "run"]
DECISIONS = ["field_goal", "punt"] + GO

SLOPE = 0.02796             # win% per point of margin per game, 2018-2025
CH5 = 2.15                  # extra points, a 33-yard kick
# NOTE: channel 1 from FINDINGS.txt is deliberately NOT added here. The policy
# below re-decides every fourth down, including the ones teams already kicked,
# so its perfect-minus-average premium already contains channel 1. Adding it
# again would double-count the kicks he was always going to take.
QB_MEAN, QB_MEDIAN = 1.28, 1.59
BASE_WINS = 8.5             # a league-average team, for the "record" line


def hdr(t):
    print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)


def sub(t):
    print(f"\n-- {t}")


def main():
    d, _ = add_adjusted(pd.read_parquet(SRC), fit_seasons=WINDOW)
    w = d[d.season.isin(WINDOW)].copy()
    n_tg = 2 * w.game_id.nunique()
    tsn = n_tg / GAMES
    grid = np.arange(1, 100)

    # ------------------------------------------------------ the three legs
    hdr("1. THE THREE LEGS OF THE DECISION, MEASURED")
    go = w[w.down.eq(4) & w.play_type.isin(GO)].copy()
    go["conv"] = go.fourth_down_converted.fillna(0).eq(1)
    won, lost = go[go.conv], go[~go.conv]

    prize = pd.Series(kern(grid, won.yardline_100.to_numpy(float),
                           won.aepa.to_numpy(float), 5.0), index=grid)
    cost = pd.Series(kern(grid, lost.yardline_100.to_numpy(float),
                          lost.aepa.to_numpy(float), 5.0), index=grid)
    punts = w[w.down.eq(4) & w.play_type.eq("punt")]
    punt_v = pd.Series(kern(grid, punts.yardline_100.to_numpy(float),
                            punts.aepa.to_numpy(float), 5.0), index=grid)
    cmod = smf.glm("conv ~ bs(ydstogo, df=4)",
                   data=go.assign(conv=go.conv.astype(int),
                                  ydstogo=go.ydstogo.clip(upper=15)),
                   family=sm.families.Binomial()).fit()
    p_conv = pd.Series(
        cmod.predict(pd.DataFrame({"ydstogo": np.arange(1, 16)})).to_numpy(),
        index=np.arange(1, 16))

    print("what a fresh first and ten is worth, in expected points, by yard line")
    o = w[w.down.eq(1) & w.ydstogo.eq(10) & w.half_seconds_remaining.gt(120)]
    e1 = o.groupby(pd.cut(o.yardline_100, [0, 10, 20, 25, 30, 35, 42, 50, 60, 80]),
                   observed=True).ep.agg(["size", "mean"])
    e1.columns = ["snaps", "expected points"]
    print(e1.round(2).to_string())
    print("\n  THIS is the prize for converting, and it is 5.0 near the goal line")
    print("  falling to 3.4 at the 42. Never 7. Seven is what you get if the")
    print("  conversion turns into a touchdown, which is not the same event.")

    sub("the same three legs in adjusted EPA, which is what you can add up")
    bands = [0, 5, 10, 20, 32, 42]
    gi = go[go.yardline_100.le(MAX_YL)].copy()
    f4 = w[w.down.eq(4) & w.yardline_100.le(MAX_YL)]
    tab = pd.DataFrame({
        "convert (prize)": gi[gi.conv].groupby(
            pd.cut(gi[gi.conv].yardline_100, bands), observed=True).aepa.mean(),
        "fail (cost)": gi[~gi.conv].groupby(
            pd.cut(gi[~gi.conv].yardline_100, bands), observed=True).aepa.mean(),
        "guaranteed FG": f4.groupby(pd.cut(f4.yardline_100, bands),
                                    observed=True).v_perfect.mean(),
    })
    tab["break-even P*"] = 100 * ((tab["guaranteed FG"] - tab["fail (cost)"])
                                  / (tab["convert (prize)"] - tab["fail (cost)"]))
    tab.index.name = "yard line"
    print(tab.round(2).to_string())
    print("\n  break-even P* = (FG - fail) / (convert - fail): the conversion rate")
    print("  going for it needs to beat a guaranteed three.")
    print(f"\n  The 3/7 shortcut says 42.9% everywhere. The real answer runs from")
    print(f"  {tab['break-even P*'].iloc[0]:.0f}% at the goal line to "
          f"{tab['break-even P*'].iloc[-1]:.0f}% out at the 42, because that is")
    print("  where the prize for converting collapses relative to three points.")
    print("  Inside the 10 you should go for it on almost anything; out at the 42")
    print("  you should kick on almost anything.")

    # ------------------------------------------------- 1b. the full surface
    hdr("1b. THE ACTUAL GO/KICK BOUNDARY, BOTH DIMENSIONS AT ONCE")
    print("Break-even is a surface, not a line, because the prize depends on")
    print("field position and the conversion rate depends on yards to go. Here")
    print("are both, and then the difference that decides it.")
    fb = [0, 10, 20, 32, 38, MAX_YL]
    go["band"] = pd.cut(go.yardline_100, fb)
    go["tg2"] = go.ydstogo.clip(upper=6)
    gi2 = go[go.yardline_100.le(MAX_YL)]
    f4b = w[w.down.eq(4) & w.yardline_100.le(MAX_YL)].assign(
        band=lambda x: pd.cut(x.yardline_100, fb))
    pzb = gi2[gi2.conv].groupby("band", observed=True).aepa.mean()
    csb = gi2[~gi2.conv].groupby("band", observed=True).aepa.mean()
    fgb = f4b.groupby("band", observed=True).v_perfect.mean()
    be = 100 * (fgb - csb) / (pzb - csb)
    print("\n  break-even conversion rate needed for GOING to beat a guaranteed 3")
    print(pd.DataFrame({"guaranteed FG": fgb, "convert": pzb, "fail": csb,
                        "break-even %": be}).round(2).to_string())
    act = 100 * gi2.pivot_table(index="tg2", columns="band", values="conv",
                                aggfunc="mean", observed=True)
    nn = gi2.pivot_table(index="tg2", columns="band", values="conv",
                         aggfunc="size", observed=True)
    print("\n  actual conversion rate, by yards to go and field position")
    print(act.round(1).to_string())
    print("\n  MARGIN = actual minus break-even. Positive means GO FOR IT,")
    print("  negative means take the guaranteed three.")
    print((act - be).round(1).to_string())
    print("\n  sample sizes")
    print(nn.to_string())
    print("\n  The boundary runs diagonally, and it does not collapse to one")
    print("  yards-to-go number:")
    print("    inside the 20 : go on 4th & 4 or less")
    print("    20 to 32      : go on 4th & 1 or 2")
    print("    32 to 38      : go on 4th & 1 only, and it is nearly a coin flip")
    print("                    (68.6% converted against 65.1% needed)")
    print("    38 to 42      : kick everything, 4th & 1 included - but 4th & 1 is")
    print("                    the closest call on the board (67.5% against 73.2%")
    print("                    needed, a 5.7 point margin)")
    print("\n  So yes: fourth and 1 is the one exception out at the edge of the")
    print("  guarantee, and from the 32 to the 38 you should still go for it.")
    print("  Only from the 38 to the 42, where the kick is 56 to 60 yards and the")
    print("  prize for converting is at its smallest, does a guaranteed three")
    print("  finally beat fourth and 1 - and it wins by a nose, not a mile.")

    # ------------------------------------------------------- 2. the sweep
    hdr("2. THE SWEEP: ONE THRESHOLD, APPLIED TO EVERY FOURTH DOWN IN THE GAME")
    f = w[w.down.eq(4) & w.play_type.isin(DECISIONS) & w.yardline_100.notna()].copy()
    tg = f.ydstogo.clip(lower=1, upper=15).round().astype(int)
    f["p_conv"] = tg.map(p_conv).astype(float)
    f["v_go"] = (f.p_conv * f.yardline_100.round().astype(int).map(prize)
                 + (1 - f.p_conv) * f.yardline_100.round().astype(int).map(cost))
    f["v_punt"] = f.yardline_100.round().astype(int).map(punt_v)
    # beyond the 42 the guarantee does not apply, so a field goal there is
    # worth whatever it was actually worth, to both kickers alike
    f["v_kick"] = np.where(f.yardline_100.le(MAX_YL), f.v_perfect,
                           np.where(f.play_type.eq("field_goal"), f.aepa, np.nan))
    f["in_range"] = f.yardline_100.le(MAX_YL)
    # what they actually did, valued the same way, as the reference point
    f["v_actual"] = np.select(
        [f.play_type.eq("field_goal"), f.play_type.eq("punt")],
        [f.v_kick, f.v_punt], default=f.v_go)
    actual = np.nansum(f.v_actual) / tsn

    # the same policy with an ordinary NFL leg, so the kicker can be separated
    # from the coaching. Make probability from a logistic spline in distance.
    fgs = w[w.is_fg & w.dist.le(60)]
    pmod = smf.glm("made ~ bs(dist, df=5)",
                   data=fgs.assign(made=fgs.made.astype(int)),
                   family=sm.families.Binomial()).fit()
    miss_v = pd.Series(kern(grid, fgs[~fgs.made].yardline_100.to_numpy(float),
                            fgs[~fgs.made].aepa.to_numpy(float), 6.0), index=grid)
    # only predict inside the guarantee; the spline has no knots past 60 yards
    ir = f.in_range.to_numpy()
    pk = np.full(len(f), np.nan)
    pk[ir] = pmod.predict(pd.DataFrame(
        {"dist": f.loc[ir, "yardline_100"] + SNAP_TO_KICK})).to_numpy()
    f["v_kick_avg"] = np.where(
        ir, pk * f.v_perfect + (1 - pk) * f.yardline_100.round().astype(int)
        .map(miss_v),
        np.where(f.play_type.eq("field_goal"), f.aepa, np.nan))
    actual_avg = np.nansum(np.select(
        [f.play_type.eq("field_goal"), f.play_type.eq("punt")],
        [f.v_kick_avg, f.v_punt], default=f.v_go)) / tsn

    # field goals that are not fourth-down plays (end-of-half kicks, mostly)
    # are outside the policy, so their premium is added once, separately
    off4 = w[w.is_fg & w.dist.le(60) & ~w.down.eq(4)]
    p_off = pmod.predict(pd.DataFrame({"dist": off4.dist})).to_numpy()
    off4_prem = ((off4.v_perfect
                  - (p_off * off4.v_perfect
                     + (1 - p_off) * off4.yardline_100.round().astype(int)
                     .map(miss_v))).sum()) / tsn
    print(f"\nfield goal attempts not on fourth down: {len(off4):,} "
          f"({len(off4) / n_tg:.2f} a game), outside the policy;")
    print(f"the guarantee is worth {off4_prem:+.1f} points a season on those, "
          f"counted once.")

    print(f"every fourth down, {WINDOW[0]}-{WINDOW[-1]}: {len(f):,} plays, "
          f"{len(f) / n_tg:.2f} a game")
    print(f"reference point: what teams actually called, valued the same way.")
    print(f"  with an ordinary leg taking their field goals : "
          f"{actual_avg:+.1f} points a season")
    print(f"  with the perfect leg taking their field goals : "
          f"{actual:+.1f} points a season")
    print(f"\nEach row runs the policy twice - once with the perfect leg, once")
    print(f"with an ordinary one. 'coach' is what the policy is worth to any team")
    print(f"regardless of kicker; 'leg' is what the guarantee adds on top. Only")
    print(f"the last column is the kicker's.")
    print("\n  P*   go if togo<=  go%  kick%  punt%  FGA/gm   pts  vs act  "
          "coach  leg   TOTAL")
    rows = []
    for ps in [0, 20, 30, 35, 40, 42.9, 50, 55, 60, 70, 100]:
        goes = f.p_conv * 100 >= ps
        kicks = ~goes & f.in_range
        punt = ~goes & ~f.in_range
        pts = np.nansum(np.where(goes, f.v_go,
                                 np.where(kicks, f.v_kick, f.v_punt))) / tsn
        pts_avg = np.nansum(np.where(goes, f.v_go,
                                     np.where(kicks, f.v_kick_avg,
                                              f.v_punt))) / tsn
        coach = SLOPE * (pts_avg - actual_avg)
        leg = SLOPE * ((pts - pts_avg) + off4_prem + CH5)
        maxtogo = int(f.loc[goes, "ydstogo"].max()) if goes.any() else 0
        lab = ("always" if ps == 0 else "never" if ps >= 100 else f"{maxtogo}")
        rows.append({"P*": ps, "go_if_togo_le": lab, "go%": 100 * goes.mean(),
                     "kick%": 100 * kicks.mean(), "punt%": 100 * punt.mean(),
                     "FGA/gm": kicks.sum() / n_tg, "pts": pts,
                     "delta": pts - actual, "coach": coach, "leg": leg,
                     "wins": coach + leg})
        star = "  <-- your 3/7 rule" if abs(ps - 42.9) < 0.01 else ""
        print(f"  {ps:4.1f}  {lab:>11}  {100 * goes.mean():5.1f} "
              f"{100 * kicks.mean():6.1f} {100 * punt.mean():6.1f} "
              f"{kicks.sum() / n_tg:7.2f} {pts:6.1f} {pts - actual:6.1f} "
              f"{coach:6.2f} {leg:5.2f} {coach + leg:6.2f}{star}")
    r = pd.DataFrame(rows)
    best = r.loc[r.wins.idxmax()]
    best_leg = best   # the leg's value read at the best TOTAL policy
    print(f"\n  'go if togo<=' is the plain-English version of P*: the policy only")
    print(f"  changes at whole yards, which is why 42.9% and 45% are the same row.")
    print(f"  'FGA/gm' is fourth-down field goals a game. 'coach' is the policy")
    print(f"  run with an ordinary leg, against what teams actually called with an")
    print(f"  ordinary leg. 'leg' is the same policy run with the perfect leg minus")
    print(f"  the ordinary one, plus extra points and the off-fourth-down kicks.")
    print(f"  Both convert at {1 / SLOPE:.0f} points a win. They add to the total.")

    sub("what the sweep says")
    yours = r[r["P*"].between(42.8, 43.0)].iloc[0]
    print(f"  your 3/7 rule, P* = 42.9%  (go if 4 or fewer to go):")
    print(f"    total {yours['wins']:+.2f} wins = {yours['coach']:+.2f} from the "
          f"decisions + {yours['leg']:+.2f} from the leg")
    print(f"    {yours['FGA/gm']:.2f} fourth-down field goals a game")
    print(f"  best total          : P* = {best['P*']:g}%, {best['wins']:+.2f} wins")
    print(f"  the leg's share of that best row: {best['leg']:+.2f} wins")
    print(f"  (the 'leg' column rises all the way to never-go-for-it, because the")
    print(f"   more you kick the more a guarantee is worth. That is not a")
    print(f"   recommendation - the total is worse there. The number that counts")
    print(f"   is the leg's share at the policy you would actually run.)")
    print(f"  go for it always    : {r.iloc[0]['wins']:+.2f} wins "
          f"({r.iloc[0]['coach']:+.2f} coach, {r.iloc[0]['leg']:+.2f} leg)")
    print(f"  never go for it     : {r.iloc[-1]['wins']:+.2f} wins "
          f"({r.iloc[-1]['coach']:+.2f} coach, {r.iloc[-1]['leg']:+.2f} leg)")
    print(f"\n  Two separate findings, and they should not be blended:")
    print(f"  1. Fourth-down policy is worth up to {r.coach.max():+.2f} wins to any")
    print(f"     team with any kicker. That is free, and it is not the kicker's.")
    print(f"  2. The guarantee itself is worth {best['leg']:.2f} wins at that best")
    print(f"     policy. That is the number to compare against the 1.01.")
    print(f"\n  The total curve is flat across the middle - every threshold from 40%")
    print(f"  to 60% lands within "
          f"{r[r['P*'].between(40, 60)].wins.max() - r[r['P*'].between(40, 60)].wins.min():.2f} "
          f"wins of the best - so your 42.9% is inside the")
    print(f"  plateau. The shortcut lands in about the right place despite the")
    print(f"  wrong premise. Both ends of the sweep are where it costs you.")

    # -------------------------------------- 3. the field-position-aware rule
    hdr("3. WHAT A FIELD-POSITION-AWARE RULE BUYS YOU")
    opt = np.nansum(np.nanmax(np.vstack([f.v_go, f.v_kick, f.v_punt]),
                              axis=0)) / tsn
    opt_avg = np.nansum(np.nanmax(np.vstack([f.v_go, f.v_kick_avg, f.v_punt]),
                                  axis=0)) / tsn
    coach_opt = SLOPE * (opt_avg - actual_avg)
    leg_opt = SLOPE * ((opt - opt_avg) + off4_prem + CH5)
    wins_opt = coach_opt + leg_opt
    print(f"  take the best of the three options on every single fourth down,")
    print(f"  with no rule at all: {opt:+.1f} points, {wins_opt:+.2f} wins")
    print(f"    of which coaching {coach_opt:+.2f}, the leg itself "
          f"{leg_opt:+.2f}")
    print(f"  best single-threshold rule: {best['wins']:+.2f} total, "
          f"{best['leg']:+.2f} leg")
    print(f"  the cost of using one number instead of thinking: "
          f"{wins_opt - best['wins']:.2f} wins total, "
          f"{leg_opt - best['leg']:.2f} of it the leg's")
    pol = pd.DataFrame({"go": f.v_go, "kick": f.v_kick, "punt": f.v_punt}).idxmax(axis=1)
    f["opt"] = pol.values
    sub("what the no-rule optimum actually does, by field position")
    print(pd.crosstab(pd.cut(f.yardline_100, [0, 10, 20, 32, 42, 60, 80, 100]),
                      f.opt, normalize="index").mul(100).round(1).to_string())
    print("\n  it goes for it near the goal line, kicks from 32 to 42, and punts")
    print("  outside the 42 - which is the field-position pattern a single")
    print("  yards-to-go threshold cannot express.")

    # ----------------------------------------------------------- 4. verdict
    hdr("4. SO WHAT IS THE WIN RATE?")
    print("  the kicker's own contribution, which is what the 1.01 buys:")
    for lab, wv in [("your 3/7 rule, P* = 42.9%", yours["leg"]),
                    (f"best threshold, P* = {best['P*']:g}%", best["leg"]),
                    ("no rule, best option every time", leg_opt)]:
        print(f"    {lab:40}: {wv:+.2f} wins")
        print(f"    {'':40}  {BASE_WINS:.1f}-{GAMES - BASE_WINS:.1f} becomes "
              f"{BASE_WINS + wv:.1f}-{GAMES - BASE_WINS - wv:.1f}, "
              f"{100 * (BASE_WINS + wv) / GAMES:.1f}%")
    print("\n  and if you ALSO hand the team optimal fourth-down decisions, which")
    print("  they could have had for free with any kicker:")
    print(f"    {'both together':40}: {wins_opt:+.2f} wins")
    print(f"    {'':40}  {BASE_WINS:.1f}-{GAMES - BASE_WINS:.1f} becomes "
          f"{BASE_WINS + wins_opt:.1f}-{GAMES - BASE_WINS - wins_opt:.1f}, "
          f"{100 * (BASE_WINS + wins_opt) / GAMES:.1f}%")
    print(f"\n  the first overall pick, for comparison: {QB_MEAN:+.2f} wins a "
          f"season on average")
    print(f"  ({BASE_WINS + QB_MEAN:.1f} wins, "
          f"{100 * (BASE_WINS + QB_MEAN) / GAMES:.1f}%), {QB_MEDIAN:+.2f} median "
          f"({100 * (BASE_WINS + QB_MEDIAN) / GAMES:.1f}%)")
    sub("why the total is not the number to compare against the quarterback")
    print(f"  The total ({best['wins']:+.2f} at the best threshold) is close to the")
    print(f"  average 1.01 quarterback ({QB_MEAN:+.2f}), but it is not the right")
    print(f"  comparison, because {best['coach']:+.2f} of it is the fourth-down chart")
    print(f"  and any team can fix that with any kicker. Put both draft choices")
    print(f"  side by side and the chart appears on both sides and cancels:")
    print(f"\n    draft the kicker : {BASE_WINS:.2f} + {best['coach']:.2f} chart "
          f"+ {best['leg']:.2f} kicker = {BASE_WINS + best['wins']:.2f} wins")
    print(f"    draft the QB     : {BASE_WINS:.2f} + {best['coach']:.2f} chart "
          f"+ {QB_MEAN:.2f} QB     = {BASE_WINS + best['coach'] + QB_MEAN:.2f} wins")
    print(f"    difference       : {QB_MEAN - best['leg']:.2f} wins a season, "
          f"which is exactly QB minus leg")
    print(f"\n  The quarterback's {QB_MEAN:+.2f} is that player against a replacement")
    print(f"  quarterback. It does not come bundled with a fourth-down chart")
    print(f"  either. Compare like with like: {best['leg']:.2f} against "
          f"{QB_MEAN:.2f}, or {QB_MEDIAN:.2f} at the median.")
    return r


if __name__ == "__main__":
    main()
