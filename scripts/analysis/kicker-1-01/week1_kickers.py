"""Week 1 kicker ranking: venue expectation blended with the kicker's own rate.

The model, as specified:

    score = 0.75 x venue_rate + 0.25 x kicker_rate

where venue_rate is the venue's field goal percentage for a kicker in that
role - visPct straight from src/data/stadiums.ts for a visitor, visPct + gap
for the home kicker - and kicker_rate is his regular-season career field goal
percentage.

A second column reports the same idea built on deviations instead of levels:

    score = league + (venue - league) + 0.25 x (kicker - league)

Both inputs already contain the league average, so averaging them mostly
averages two copies of that average and shrinks the venue effect it is meant
to respect. Adding deviations keeps the venue at full weight, which is what
the 75/25 split was trying to express, and shrinks only the noisy kicker term.

Run fetch_plays.py first, then:  python3 week1_kickers.py > WEEK1.txt
"""
import json
import os
import re
import subprocess
import warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

from epa_common import add_adjusted

pd.set_option("display.width", 240)
pd.set_option("display.max_columns", 60)
pd.set_option("display.max_rows", 100)

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "plays_1999_2025.parquet")
STADIUMS = os.path.join(HERE, "..", "..", "..", "src", "data", "stadiums.ts")
TMP = os.environ.get("NFLVERSE_TMP", "/tmp/nflverse")

SEASON, WEEK = 2026, 1
W_VENUE, W_KICKER = 0.75, 0.25
SCHED = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
ROSTER = ("https://github.com/nflverse/nflverse-data/releases/download/"
          f"rosters/roster_{SEASON}.parquet")


def hdr(t):
    print("\n" + "=" * 100 + f"\n{t}\n" + "=" * 100)


def sub(t):
    print(f"\n-- {t}")


def grab(url, name):
    os.makedirs(TMP, exist_ok=True)
    path = os.path.join(TMP, name)
    if not os.path.exists(path):
        subprocess.run(["curl", "-sSL", "--retry", "4", "-o", path, url], check=True)
    return path


def main():
    # ------------------------------------------------------------- inputs
    ts = open(STADIUMS).read()
    venues = {v["id"]: v for v in json.loads(
        re.search(r"export const stadiums[^=]*=\s*(\[.*?\]);", ts, re.S).group(1))}

    g = pd.read_csv(grab(SCHED, "games.csv"))
    wk = g[(g.season == SEASON) & (g.week == WEEK)].copy()

    ros = pd.read_parquet(grab(ROSTER, f"roster_{SEASON}.parquet"))
    ks = ros[ros.position.eq("K") & ros.status.eq("ACT")].set_index("team")

    d, _ = add_adjusted(pd.read_parquet(SRC))
    fg = d[d.is_fg & d.season_type.eq("REG")]
    league = fg[fg.season.ge(2023)].made.mean()
    by_id = fg.groupby("kicker_player_id").agg(att=("made", "size"),
                                               made=("made", "sum"))
    by_id["pct"] = by_id.made / by_id.att

    hdr(f"WEEK {WEEK}, {SEASON} - KICKER RANKING")
    print(f"model            : score = {W_VENUE:.2f} x venue rate + "
          f"{W_KICKER:.2f} x kicker rate")
    print(f"league average   : {league:.4f} (all regular-season attempts, "
          f"2023-2025)")
    print(f"venue rate       : visPct from stadiums.ts for a visitor, "
          f"visPct + gap for the home kicker")
    print(f"kicker rate      : career REGULAR-SEASON field goal percentage, "
          f"blocks included")
    print(f"games            : {len(wk)}")

    rows = []
    for _, m in wk.iterrows():
        v = venues.get(m.stadium_id)
        for team, role in [(m.away_team, "visitor"), (m.home_team, "home")]:
            k = ks.loc[team] if team in ks.index else None
            kid = k.gsis_id if k is not None else None
            rec = by_id.loc[kid] if kid in by_id.index else None
            kpct = float(rec.pct) if rec is not None else np.nan
            katt = int(rec.att) if rec is not None else 0
            if v is None:
                vpct, vsrc = np.nan, "no venue history"
            elif role == "visitor":
                vpct, vsrc = v["visPct"] / 100.0, f"visPct {v['visPct']:.1f}"
            else:
                vpct = (v["visPct"] + v["gap"]) / 100.0
                vsrc = f"visPct {v['visPct']:.1f} + gap {v['gap']:+.1f}"
            rows.append({
                "team": team, "kicker": k.full_name if k is not None else "?",
                "role": role, "opp": m.home_team if role == "visitor" else m.away_team,
                "venue": (v["name"] if v else m.stadium)[:26],
                "venue_id": m.stadium_id, "venue_rate": vpct, "venue_src": vsrc,
                "kicker_rate": kpct, "k_att": katt,
            })
    r = pd.DataFrame(rows)

    sub("gaps in the inputs, and how they are filled")
    nov = r[r.venue_rate.isna()]
    nok = r[r.kicker_rate.isna()]
    for _, x in nov.iterrows():
        print(f"  {x.venue_id} ({x.venue}) has no entry in stadiums.ts - "
              f"{x.team} {x.role}")
    print(f"    -> venue rate set to the league average, {league:.4f}")
    for _, x in nok.iterrows():
        print(f"  {x.kicker} ({x.team}) has no regular-season NFL attempts")
    print(f"    -> kicker rate set to the league average, {league:.4f}")
    r["venue_rate"] = r.venue_rate.fillna(league)
    r["kicker_rate"] = r.kicker_rate.fillna(league)

    # ------------------------------------------------------------ scoring
    r["score"] = W_VENUE * r.venue_rate + W_KICKER * r.kicker_rate
    r["score_dev"] = (league + (r.venue_rate - league)
                      + W_KICKER * (r.kicker_rate - league))
    r = r.sort_values("score", ascending=False).reset_index(drop=True)
    r["rank"] = r.index + 1
    r["rank_dev"] = r.score_dev.rank(ascending=False).astype(int)

    hdr("THE RANKING, AS SPECIFIED")
    print(f"{'#':>3}  {'kicker':18} {'tm':4} {'role':8} {'venue':26} "
          f"{'venue':>7} {'kick':>7} {'att':>4}  {'calculation':>34} {'score':>7}")
    for _, x in r.iterrows():
        calc = (f"{x.venue_rate:.4f}x{W_VENUE:.2f} + "
                f"{x.kicker_rate:.4f}x{W_KICKER:.2f}")
        print(f"{x['rank']:3d}  {x.kicker:18} {x.team:4} {x.role:8} {x.venue:26} "
              f"{x.venue_rate:7.4f} {x.kicker_rate:7.4f} {x.k_att:4d}  "
              f"{calc:>34} {x.score:7.4f}")

    hdr("THE SAME THING ON DEVIATIONS, WHICH IS THE VERSION I WOULD USE")
    print("  score = league + (venue - league) + 0.25 x (kicker - league)")
    print(f"{'#':>3}  {'kicker':18} {'tm':4} {'venue eff':>10} "
          f"{'kicker eff':>11} {'shrunk':>8} {'score':>8}  {'as-spec rank':>12}")
    for _, x in r.sort_values("score_dev", ascending=False).iterrows():
        ve, ke = x.venue_rate - league, x.kicker_rate - league
        print(f"{x.rank_dev:3d}  {x.kicker:18} {x.team:4} {ve:+10.4f} "
              f"{ke:+11.4f} {W_KICKER * ke:+8.4f} {x.score_dev:8.4f}  "
              f"{x['rank']:12d}")
    print(f"\n  rank correlation between the two: "
          f"{r['rank'].corr(r.rank_dev, method='spearman'):.3f}")
    biggest = (r.rank_dev - r["rank"]).abs().idxmax()
    b = r.loc[biggest]
    print(f"  biggest disagreement: {b.kicker} - {b['rank']} as specified, "
          f"{b.rank_dev} on deviations")

    hdr("WHY THE TWO DIFFER")
    print("  Both inputs are anchored on the same league average, so averaging")
    print("  them averages two copies of it. Take a kicker 3 points below")
    print("  average at a venue 2 points below average:")
    print(f"    as specified : 0.75 x (L-0.02) + 0.25 x (L-0.03) = "
          f"L - 0.0225")
    print(f"    on deviations: L + (-0.02) + 0.25 x (-0.03)      = L - 0.0275")
    print("  The first understates it, because averaging pulls the venue")
    print("  penalty toward the kicker's number instead of adding to it. The")
    print("  75/25 split was expressing confidence in each estimate, and")
    print("  confidence belongs on the kicker's DEVIATION - shrink the noisy")
    print("  term toward zero - not on the level.")
    r.to_csv(os.path.join(HERE, f"week{WEEK}_{SEASON}_kickers.csv"), index=False)
    print(f"\n  wrote week{WEEK}_{SEASON}_kickers.csv")
    return r


if __name__ == "__main__":
    main()
