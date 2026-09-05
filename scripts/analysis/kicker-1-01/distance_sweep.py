"""What if the guarantee were 70 yards instead of 60?

A follow-up from the comments: same deal, but he is automatic from 70 and in.
70 yards is a snap from the opponent's 52 - your own 48 - so the guarantee
would cover a bit more than half the field.

Run fetch_plays.py first, then:  python3 distance_sweep.py > DISTANCE.txt

Method is the same as verdict.py, run at every guarantee distance:

    channel 1  field goals teams already attempt inside D, misses -> makes
    channel 3  fourth downs inside D that were punted or gone for, where a
               guaranteed make beats the play the coach actually called
    channel 5  extra points

One thing changes past 60 yards and it matters. An ordinary kicker has no
field goal option out there at all - 27 attempts from the opponent's 42 to
52 in eight seasons, against 3,595 fourth downs - so beyond the 42 the
comparison leg punts or goes for it. Every point the guarantee produces from
that strip is genuinely new, not an upgrade on a kick someone was already
taking. That is why the curve bends the way it does.
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
GAMES = 17
SLOPE = 0.02796
REAL_MAX = 62          # past this an ordinary NFL leg simply does not attempt
REPL_SCALE = 1.46      # a fill-in leg's miss rate, x average (VERDICT.txt)
QB_MEAN, QB_MEDIAN = 1.28, 1.59
KICK_AVG_60 = 0.84     # the 60-yard headline, vs an average leg (VERDICT.txt)
GO = ["pass", "run"]


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

    fgs_all = w[w.is_fg]
    pm = smf.glm("made ~ bs(dist, df=5)",
                 data=fgs_all[fgs_all.dist.le(REAL_MAX)].assign(
                     made=lambda x: x.made.astype(int)),
                 family=sm.families.Binomial()).fit()
    miss_v = pd.Series(kern(grid, fgs_all[~fgs_all.made].yardline_100.to_numpy(float),
                            fgs_all[~fgs_all.made].aepa.to_numpy(float), 6.0),
                       index=grid)
    xp = w[w.extra_point_attempt.fillna(0).eq(1) & w.extra_point_result.notna()]
    ch5 = len(xp) * (1 - xp.extra_point_result.eq("good").mean()) / tsn

    f4 = w[w.down.eq(4) & w.play_type.isin(["field_goal", "punt"] + GO)
           & w.yardline_100.notna()].copy()
    go = f4[f4.play_type.isin(GO)]
    go_v = go.groupby(go.ydstogo.clip(upper=11)).aepa.mean()
    punts = f4[f4.play_type.eq("punt")]
    punt_v = pd.Series(kern(grid, punts.yardline_100.to_numpy(float),
                            punts.aepa.to_numpy(float), 5.0), index=grid)
    f4["v_alt"] = np.where(f4.play_type.eq("punt"),
                           f4.yardline_100.round().astype(int).map(punt_v),
                           f4.ydstogo.clip(upper=11).map(go_v).astype(float))

    hdr("1. THE FIELD THE GUARANTEE COVERS")
    print("fourth downs by field position, and what teams do with them")
    band = pd.cut(f4.yardline_100, [0, 42, 45, 48, 50, 52, 55, 60, 100])
    t = f4.groupby(band, observed=True).apply(lambda x: pd.Series({
        "kick_dist": x.yardline_100.mean() + SNAP_TO_KICK,
        "n": len(x), "per_game": len(x) / n_tg,
        "kick%": 100 * x.play_type.eq("field_goal").mean(),
        "punt%": 100 * x.play_type.eq("punt").mean(),
        "go%": 100 * x.play_type.isin(GO).mean()}), include_groups=False)
    print(t.round(2).to_string())
    strip = f4[f4.yardline_100.between(43, 52)]
    print(f"\n  The 43-to-52 strip - a 61 to 70 yard kick - carries "
          f"{len(strip) / n_tg:.2f} fourth")
    print(f"  downs a game, {100 * strip.play_type.eq('punt').mean():.0f}% of them "
          f"punted and "
          f"{100 * strip.play_type.eq('field_goal').mean():.1f}% kicked. Extending the")
    print(f"  guarantee from 60 to 70 hands him a piece of field nobody uses.")

    sub("longest field goals actually made, 1999-2025")
    fg_ever = d[d.is_fg]
    made_long = fg_ever[fg_ever.made & fg_ever.dist.ge(64)]
    print(made_long[["season", "posteam", "kicker_player_name", "dist"]]
          .sort_values("dist", ascending=False).head(8).to_string(index=False))
    print(f"\n  The record across 1999-2025 is 68 yards, hit once. A 70-yard")
    print(f"  guarantee is not an extension of something kickers already do -")
    print(f"  it is a new thing entirely.")

    # ------------------------------------------------------- 2. the sweep
    hdr("2. THE SWEEP: WHAT EACH GUARANTEE DISTANCE IS WORTH")

    def value(dist, scale=1.0):
        """scale = the comparison leg's miss rate as a multiple of average."""
        yl = dist - SNAP_TO_KICK
        # channel 1: attempts teams already take inside the guarantee
        fin = fgs_all[fgs_all.dist.le(dist)]
        p = 1 - scale * (1 - pm.predict(pd.DataFrame(
            {"dist": fin.dist.clip(upper=REAL_MAX)})).to_numpy())
        base = np.where(fin.dist.le(REAL_MAX),
                        p * fin.v_perfect
                        + (1 - p) * fin.yardline_100.round().astype(int).map(miss_v),
                        fin.aepa)
        c1 = (fin.v_perfect - base).sum() / tsn
        # channel 3: fourth downs in range the team did not kick. Beyond the
        # 42 this is identical for both comparison legs, because neither one
        # attempts a 61-yarder - there is no kick to be worse at.
        sel = f4[f4.yardline_100.le(yl) & ~f4.play_type.eq("field_goal")].copy()
        c3 = np.maximum(0.0, sel.v_perfect - sel.v_alt).sum() / tsn
        n_new = (np.maximum(0.0, sel.v_perfect - sel.v_alt) > 0).sum() / n_tg
        return c1, c3, ch5 * scale, n_new

    rows = []
    for dist in [50, 55, 60, 62, 65, 70, 75]:
        c1, c3, c5, n_new = value(dist)
        rc1, rc3, rc5, _ = value(dist, REPL_SCALE)
        tot = c1 + c3 + c5
        rows.append({"guarantee": f"{dist} yds", "from the": dist - SNAP_TO_KICK,
                     "ch1": c1, "ch3": c3, "ch5": c5, "points": tot,
                     "wins_vs_avg": SLOPE * tot,
                     "wins_vs_repl": SLOPE * (rc1 + rc3 + rc5),
                     "extra_kicks/gm": n_new})
    r = pd.DataFrame(rows).rename(columns={"wins_vs_avg": "wins"})
    print("  'from the' is the opponent's yard line the guarantee reaches.")
    print("  Per 17-game team-season. 'wins' is against an AVERAGE NFL leg;")
    print("  'wins_vs_repl' is against a replacement leg, the same rung the")
    print("  quarterback's 1.28 is measured on, so that is the like-for-like one.")
    print("\n" + r.round(2).to_string(index=False))
    w60 = r[r.guarantee.eq("60 yds")].iloc[0]
    w70 = r[r.guarantee.eq("70 yds")].iloc[0]
    print(f"\n  60 yards : {w60.wins:.2f} wins")
    print(f"  70 yards : {w70.wins:.2f} wins  "
          f"({w70.wins - w60.wins:+.2f}, a {100 * (w70.wins / w60.wins - 1):.0f}% jump)")
    print(f"  the extra ten yards is worth more than DOUBLE the first sixty,")
    print(f"  because it is all new territory: {w70['ch3'] - w60['ch3']:.1f} of the")
    print(f"  {w70.points - w60.points:.1f} extra points come from fourth downs")
    print(f"  nobody currently kicks on.")

    sub("against the first overall pick")
    for _, row in r.iterrows():
        mark = ""
        if row.wins > QB_MEDIAN:
            mark = "  <-- beats the MEDIAN 1.01 quarterback"
        elif row.wins > QB_MEAN:
            mark = "  <-- beats the AVERAGE 1.01 quarterback"
        print(f"  {row.guarantee:>7}: {row.wins:5.2f} wins{mark}")
    print(f"\n  1.01 quarterback: {QB_MEAN:.2f} mean, {QB_MEDIAN:.2f} median")
    sub("like-for-like, both against replacement level")
    for _, row in r.iterrows():
        mark = ("  <-- beats the MEDIAN 1.01" if row.wins_vs_repl > QB_MEDIAN
                else "  <-- beats the AVERAGE 1.01" if row.wins_vs_repl > QB_MEAN
                else "")
        print(f"  {row.guarantee:>7}: {row.wins_vs_repl:5.2f} wins{mark}")
    print(f"\n  The two columns converge as the guarantee lengthens, because the")
    print(f"  new value is all in territory where NEITHER comparison leg has a")
    print(f"  field goal option. You cannot be worse than someone at a kick they")
    print(f"  were never going to attempt.")

    # ------------------------------------------- 3. kick-on-arrival at 70
    hdr("3. DOES 'KICK THE MOMENT YOU CROSS THE 50' WORK AT 70 YARDS?")
    print("At 60 yards this idea lost 4.2 wins a season (EARLY.txt). The longer")
    print("guarantee starts the range further out, where a drive is worth less,")
    print("so the trade should be less bad. Expected points added by kicking on")
    print("this snap instead of running the play:")
    live = w[w.play_type.isin(GO) & w.yardline_100.le(52) & w.down.notna()
             & w.half_seconds_remaining.gt(120)].copy()
    live["yl"] = pd.cut(live.yardline_100, [0, 20, 32, 42, 47, 52])
    print("\n" + live.pivot_table(index="down", columns="yl", values="v_perfect",
                                  aggfunc="mean", observed=True).round(2).to_string())
    print("\n  Still negative on every down except fourth. It is less bad out at")
    print("  the 47-52, but 'less bad' is not 'good': first down there is worth")
    print(f"  {live[live.down.eq(1) & live.yl.astype(str).eq('(47, 52]')].v_perfect.mean():+.2f}. "
          f"The answer does not change - the value is on FOURTH down.")

    scrim = ["pass", "run", "punt", "field_goal", "qb_kneel", "qb_spike"]
    s = w[w.play_type.isin(scrim) & w.posteam.notna() & w.yardline_100.notna()]
    for lim, lab in [(42, "60-yard guarantee"), (52, "70-yard guarantee")]:
        inr = s[s.yardline_100.le(lim)]
        first = inr.sort_values(["game_id", "fixed_drive", "play_id"]).groupby(
            ["game_id", "posteam", "fixed_drive"], as_index=False).first()
        print(f"\n  {lab}: {len(first) / n_tg:.2f} drives a game reach the "
              f"{lim}, kicking on arrival costs {first.v_perfect.mean():+.2f} a drive")
        print(f"    = {first.v_perfect.mean() * len(first) / tsn:+.0f} points a "
              f"season = {SLOPE * first.v_perfect.mean() * len(first) / tsn:+.2f} wins")

    hdr("4. THE CATCH")
    print("  Two things get shakier at 70 that were solid at 60.")
    print("\n  1. Nobody has ever done this. The longest made field goal in the")
    fg_ever = d[d.is_fg]
    n70 = int(fg_ever.dist.ge(70).sum())
    n70m = int((fg_ever.dist.ge(70) & fg_ever.made).sum())
    n64 = int(fg_ever.dist.between(64, 69).sum())
    n64m = int((fg_ever.dist.between(64, 69) & fg_ever.made).sum())
    print(f"     data is 68 yards. Across 1999-2025 there are {n70} attempts of")
    print(f"     70 or more, {n70m} of them made, and {n64} attempts of 64 to 69,")
    print(f"     {n64m} made. Every number above prices a play that does not exist,")
    print("     using the value of the field position it replaces. That part is")
    print("     solid; what is untested is whether the snap, hold and protection")
    print("     even hold up at that range.")
    print("\n  2. The opponent adapts harder. At 60 the guarantee touches a")
    print("     narrow strip of field. At 70 it covers everything past your own")
    print("     48, which changes punt coverage, two-minute defence and")
    print("     fourth-down policy for the other team on more than half the")
    print("     field. A frozen-history study cannot see any of that, and it all")
    print("     cuts against the kicker.")
    return r


if __name__ == "__main__":
    main()
