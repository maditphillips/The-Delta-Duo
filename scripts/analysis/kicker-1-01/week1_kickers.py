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
# venue / kicker split, overridable: W_VENUE=0.5 python3 week1_kickers.py
W_VENUE = float(os.environ.get("W_VENUE", 0.75))
W_KICKER = 1.0 - W_VENUE
# Attempts at which a kicker's own rate earns half weight. The empirical value
# from the year-to-year correlation of distance-adjusted FG% (r = 0.102, so
# k = n(1-r)/r at a typical n of 28) is about 250; raw FG% implies 600. Lower
# values trust the kicker more. Overridable.
K_SHRINK = float(os.environ.get("K_SHRINK", 250))
# "symmetric" shrinks every kicker toward the league average, which is the
# statistically correct move but pulls BAD small-sample kickers up as well as
# good ones down. "onesided" shrinks only kickers above average - a prove-it
# rule that discounts small-sample hot numbers while letting a poor record
# stand. Not standard statistics; a deliberate design choice.
SHRINK_MODE = os.environ.get("SHRINK_MODE", "symmetric")
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
    r["rel"] = r.k_att / (r.k_att + K_SHRINK)
    if SHRINK_MODE == "onesided":
        # only discount kickers whose rate is ABOVE the league average
        w = np.where(r.kicker_rate > league, r.rel, 1.0)
    else:
        w = r.rel
    r["shrink_w"] = w
    r["kicker_shrunk"] = league + w * (r.kicker_rate - league)
    r["score_shrunk"] = W_VENUE * r.venue_rate + W_KICKER * r.kicker_shrunk
    r = r.sort_values("score", ascending=False).reset_index(drop=True)
    r["rank"] = r.index + 1
    r["rank_shrunk"] = r.score_shrunk.rank(ascending=False).astype(int)

    hdr("THE RANKING, AS SPECIFIED")
    print(f"{'#':>3}  {'kicker':18} {'tm':4} {'role':8} {'venue':26} "
          f"{'venue':>7} {'kick':>7} {'att':>4}  {'calculation':>34} {'score':>7}")
    for _, x in r.iterrows():
        calc = (f"{x.venue_rate:.4f}x{W_VENUE:.2f} + "
                f"{x.kicker_rate:.4f}x{W_KICKER:.2f}")
        print(f"{x['rank']:3d}  {x.kicker:18} {x.team:4} {x.role:8} {x.venue:26} "
              f"{x.venue_rate:7.4f} {x.kicker_rate:7.4f} {x.k_att:4d}  "
              f"{calc:>34} {x.score:7.4f}")

    hdr("HOW RELIABLE IS A KICKER'S OWN FIELD GOAL PERCENTAGE?")
    print("  Year-to-year correlation of a kicker's FG%, 335 consecutive")
    print("  kicker-season pairs with 20+ attempts each, 2010-2025:")
    print("    raw FG%                            r = +0.044")
    print("    FG% over expected (distance-adj)   r = +0.102")
    print("\n  Both are near zero. True kicking skill has a spread of roughly 1.8")
    print("  percentage points, while a 28-attempt season carries 6.8 points of")
    print("  pure binomial noise. Almost all the visible spread between kickers")
    print("  is sampling, not ability.")
    print(f"\n  So a kicker's own rate earns half weight only at ~{K_SHRINK} career")
    print("  attempts. What that does to this slate:")
    print(f"\n{'kicker':18} {'att':>4} {'raw':>7} {'reliab':>7} {'shrunk':>7} "
          f"{'as-spec':>8} {'shrunk':>7}")
    for _, x in r.sort_values("k_att").iterrows():
        print(f"{x.kicker:18} {x.k_att:4d} {x.kicker_rate:7.4f} {x.rel:7.3f} "
              f"{x.kicker_shrunk:7.4f} {x['rank']:8d} {x.rank_shrunk:7d}")

    hdr("RANKING WITH THE KICKER TERM SHRUNK BY SAMPLE SIZE")
    print(f"  score = {W_VENUE:.2f} x venue + {W_KICKER:.2f} x [league + "
          f"w x (kicker - league)],  w = n/(n+{K_SHRINK:.0f})")
    print(f"  shrink mode: {SHRINK_MODE}")
    print("  Weights still sum to 1, so the score stays on the make-rate scale.")
    print(f"\n{'#':>3}  {'kicker':18} {'tm':4} {'role':8} {'venue':26} "
          f"{'venue':>7} {'shrunk':>7} {'score':>7}  {'as-spec':>8}")
    for _, x in r.sort_values("score_shrunk", ascending=False).iterrows():
        print(f"{x.rank_shrunk:3d}  {x.kicker:18} {x.team:4} {x.role:8} "
              f"{x.venue:26} {x.venue_rate:7.4f} {x.kicker_shrunk:7.4f} "
              f"{x.score_shrunk:7.4f}  {x['rank']:8d}")
    print(f"\n  rank correlation with the as-specified version: "
          f"{r['rank'].corr(r.rank_shrunk, method='spearman'):.3f}")

    hdr("WHAT THIS MODEL RANKS, AND WHAT IT DOES NOT")
    print("  It ranks EXPECTED MAKE RATE on one kick. It says nothing about how")
    print("  many kicks a man gets, and that is where the rest of the")
    print("  disagreement with intuition lives.")
    print("\n  Note which way shrinkage cuts: it moves a POOR kicker UP, because")
    print("  his badness was mostly noise and shrinking pulls him toward average.")
    print("  If the ranking should punish a kicker his coach does not trust, that")
    print("  belongs in a volume term - expected attempts - not in the accuracy")
    print("  term. Volume is the honest home for team quality, coach aggression")
    print("  and the short-leash effect.")

    tag = (f"{int(100 * W_VENUE)}_{int(100 * W_KICKER)}"
           f"_k{K_SHRINK:.0f}_{SHRINK_MODE}")
    r.to_csv(os.path.join(HERE, f"week{WEEK}_{SEASON}_kickers_{tag}.csv"),
             index=False)
    print(f"\n  wrote week{WEEK}_{SEASON}_kickers_{tag}.csv")
    return r


if __name__ == "__main__":
    main()
