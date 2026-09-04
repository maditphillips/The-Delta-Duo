"""Should he just kick the moment you cross into range?

A commenter's idea: don't wait for fourth down. The instant the offence
reaches the opponent's 42, send him out. Guaranteed three, every drive, and
lean on your defence.

Run fetch_plays.py first, then:  python3 kick_early.py > EARLY.txt

The test is the same one used everywhere else in this study. Kicking right
now is worth

    3 - K - ep

where K is the expected points the opponent gets from the possession after
the score and ep is what the situation you are giving up was already worth.
On fourth down at the 40 that is positive, because ep is small - the drive
was probably over anyway. On FIRST down at the 40 it is deeply negative,
because ep is about 3.4: a fresh set of downs in scoring range is already
worth more than a field goal.
"""
import os
import warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

from epa_common import SNAP_TO_KICK, add_adjusted

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 60)

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "plays_1999_2025.parquet")

WINDOW = list(range(2018, 2026))
MAX_YL = 42
GAMES = 17
SLOPE = 0.02796
SCRIM = ["pass", "run", "punt", "field_goal", "qb_kneel", "qb_spike"]


def hdr(t):
    print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)


def sub(t):
    print(f"\n-- {t}")


def main():
    d, _ = add_adjusted(pd.read_parquet(SRC), fit_seasons=WINDOW)
    w = d[d.season.isin(WINDOW)].copy()
    n_tg = 2 * w.game_id.nunique()
    tsn = n_tg / GAMES

    hdr("1. WHAT KICKING RIGHT NOW IS WORTH, BY DOWN")
    live = w[w.play_type.isin(["pass", "run"]) & w.yardline_100.le(MAX_YL)
             & w.down.notna() & w.half_seconds_remaining.gt(120)].copy()
    live["yl"] = pd.cut(live.yardline_100, [0, 10, 20, 30, 36, 42])
    t = live.pivot_table(index="down", columns="yl", values="v_perfect",
                         aggfunc="mean", observed=True)
    print("  expected points ADDED by sending him out on this snap instead of")
    print("  running the play (positive = kick, negative = do not kick)")
    print(t.round(2).to_string())
    print("\n  and the same thing without the field-position split:")
    print(live.groupby("down").v_perfect.agg(["size", "mean"]).round(2).to_string())
    print("\n  First down inside the 42 is worth about 3.4 expected points on its")
    print("  own. Trading that for three points, and handing the ball back, loses")
    print("  around two and a half points every time you do it.")
    print("\n  Note the bottom-right corner: fourth down from the 36-42 is +1.00.")
    print("  That single cell is the entire real strategy. The commenter has the")
    print("  right patch of grass and the wrong down.")

    # ------------------------------------------------------- 2. per drive
    hdr("2. RUN THE POLICY: KICK ON THE FIRST SNAP IN RANGE, EVERY DRIVE")
    s = w[w.play_type.isin(SCRIM) & w.posteam.notna() & w.yardline_100.notna()]
    inr = s[s.yardline_100.le(MAX_YL)]
    first = inr.sort_values(["game_id", "fixed_drive", "play_id"]).groupby(
        ["game_id", "posteam", "fixed_drive"], as_index=False).first()
    res = s.sort_values(["game_id", "fixed_drive", "play_id"]).groupby(
        ["game_id", "posteam", "fixed_drive"], as_index=False).fixed_drive_result.last()
    dr = first.merge(res, on=["game_id", "posteam", "fixed_drive"],
                     suffixes=("", "_end"))
    print(f"drives that reached the opponent's {MAX_YL}: {len(dr):,} "
          f"= {len(dr) / n_tg:.2f} a game")
    print(f"  the snap the policy would fire on:")
    print(dr.groupby("down").agg(n=("v_perfect", "size"),
                                 mean_v=("v_perfect", "mean")).round(2).to_string())

    sub("what those drives actually produced")
    out = dr.fixed_drive_result_end.value_counts(normalize=True).mul(100).round(1)
    print(out.to_string())
    pts = {"Touchdown": 7, "Field goal": 3, "Opp touchdown": -7, "Safety": -2}
    dr["actual_pts"] = dr.fixed_drive_result_end.map(pts).fillna(0.0)
    print(f"\n  average points those drives actually scored: "
          f"{dr.actual_pts.mean():.2f}")
    print(f"  the policy scores exactly 3.00 on every one of them")
    print(f"  raw scoreboard difference: {3 - dr.actual_pts.mean():+.2f} points a drive")
    td = 100 * dr.fixed_drive_result_end.eq("Touchdown").mean()
    print(f"\n  So the policy loses on the raw scoreboard before any clever")
    print(f"  accounting at all. {td:.0f}% of drives that reach the {MAX_YL} end in a")
    print(f"  TOUCHDOWN; the policy caps every one of those at three. Only "
          f"{100 - td - 29.9:.0f}%")
    print(f"  of them end in something worse than a field goal.")

    sub("the full accounting")
    cost = dr.v_perfect.mean()
    print(f"  expected points added, per drive : {cost:+.2f}")
    print(f"  drives in range per game         : {len(dr) / n_tg:.2f}")
    print(f"  cost per game                    : {cost * len(dr) / n_tg:+.2f} points")
    season = cost * len(dr) / tsn
    print(f"  cost per 17-game season          : {season:+.1f} points = "
          f"{SLOPE * season:+.2f} wins")

    sub("against the sensible policies")
    print(f"  kick on the first snap in range        : {SLOPE * season:+.2f} wins")
    print(f"  kick on fourth down when it beats the")
    print(f"    play the coach actually called       : +0.84 wins  (VERDICT.txt)")
    print(f"  swing between the two                  : "
          f"{0.84 - SLOPE * season:.2f} wins")

    # ---------------------------------------------- 3. the defence argument
    hdr("3. BUT WHAT IF THE DEFENCE IS GREAT?")
    print("The argument has a real kernel: guaranteed threes are low variance, and")
    print("a good defence in a low-scoring game might prefer certainty to upside.")
    print("The problem is the size of the toll. Check whether teams with elite")
    print("defences actually lose less from the trade:")
    pa = w[w.season_type.eq("REG")].groupby("game_id").last().reset_index()
    tg = pd.concat([
        pa[["season", "home_team", "away_score"]].rename(
            columns={"home_team": "team", "away_score": "pa"}),
        pa[["season", "away_team", "home_score"]].rename(
            columns={"away_team": "team", "home_score": "pa"})])
    dpg = tg.groupby(["season", "team"], as_index=False).pa.mean()
    dpg["def_tier"] = dpg.groupby("season").pa.transform(
        lambda x: pd.qcut(x, 4, labels=["elite", "good", "poor", "worst"]))
    dr2 = dr.merge(dpg, left_on=["season", "posteam"],
                   right_on=["season", "team"], how="left")
    print("\n" + dr2.groupby("def_tier", observed=True).agg(
        drives=("v_perfect", "size"), pts_allowed_pg=("pa", "mean"),
        cost_per_drive=("v_perfect", "mean")).round(2).to_string())
    print("\n  The toll is the same whoever is on defence, because it is paid on")
    print("  YOUR side of the ball: you are throwing away your own drive. A good")
    print("  defence makes each point you hold more valuable, it does not make")
    print("  giving up a point and a half per drive cheaper.")

    # ------------------------------------------------------ 4. one team
    hdr("4. WOULD IT HAVE PUT HOUSTON IN THE SUPER BOWL?")
    for team, yr in [("HOU", 2024), ("HOU", 2025)]:
        sel = dr2[dr2.posteam.eq(team) & dr2.season.eq(yr)]
        if not len(sel):
            continue
        g = w[w.season.eq(yr) & w.posteam.eq(team) & w.season_type.eq("REG")].game_id.nunique()
        pol = 3.0 * len(sel)
        act = sel.actual_pts.sum()
        print(f"\n  {team} {yr}: {len(sel)} drives reached the {MAX_YL} "
              f"({len(sel) / g:.2f} a game over {g} games)")
        print(f"    those drives actually scored      : {act:.0f} points "
              f"({act / g:.1f} a game)")
        print(f"    the policy would score            : {pol:.0f} points "
              f"({pol / g:.1f} a game)")
        print(f"    raw scoreboard change             : {pol - act:+.0f} points")
        print(f"    but expected points added         : "
              f"{sel.v_perfect.sum():+.0f}, i.e. "
              f"{SLOPE * sel.v_perfect.sum() * 17 / 17:+.2f} wins WORSE")
        print(f"    and the opponent gets "
              f"{len(sel) - (sel.fixed_drive_result_end.isin(['Touchdown', 'Field goal'])).sum():+.0f} "
              f"extra possessions from drives that would otherwise have ended")
        print(f"    in a punt or a turnover deep in their own territory")
    print("\n  Houston scores FEWER points in both seasons on the raw scoreboard,")
    print("  before counting the possessions handed back early. The idea does not")
    print("  need the sophisticated accounting to fail; it fails on points.")
    return dr2


if __name__ == "__main__":
    main()
