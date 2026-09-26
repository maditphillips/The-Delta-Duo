"""Kicker ranking for one week: venue expectation blended with the kicker's own rate.

The model, as it was settled on in week 1:

    score = 0.50 x venue_rate + 0.50 x [league + w x (kicker_rate - league)]
    w     = n / (n + 100), applied ONE-SIDED (only above the league average)

where venue_rate is the venue's field goal percentage for a kicker in that
role - visPct straight from src/data/stadiums.ts for a visitor, visPct + gap
for the home kicker - and kicker_rate is his regular-season career field goal
percentage.

The split started at 75/25 and moved to 50/50 by hand: 75/25 let the venue
term carry nearly the whole board, and the week-1 slate it produced put
kickers in places football sense would not. Both weights remain overridable.

A second column reports the same idea built on deviations instead of levels:

    score = league + (venue - league) + W_KICKER x (kicker - league)

Both inputs already contain the league average, so averaging them mostly
averages two copies of that average and shrinks the venue effect it is meant
to respect. That version is reported, never published: its weights sum to
more than one, so it is not on the make-rate scale.

Run fetch_plays.py first, then:

    python3 weekly_kickers.py --week 2                 # the report
    python3 weekly_kickers.py --week 2 --publish       # and data/weekly/.../k.csv

The published board is the shrunk ranking, not the as-specified one. The
defaults below are what week 1 shipped with: a kicker's own rate earns half
weight at 100 career attempts, and only kickers above the league average are
discounted for it. Both remain overridable by environment variable.
"""
import argparse
import csv
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

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--season", type=int, default=2026)
ap.add_argument("--week", type=int, default=1)
ap.add_argument("--plays", default=None, help="the parquet fetch_plays.py wrote")
ap.add_argument("--publish", action="store_true",
                help="also write data/weekly/<season>/week-NN/k.csv")
args, _ = ap.parse_known_args()

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
STADIUMS = os.path.join(ROOT, "src", "data", "stadiums.ts")
TMP = os.environ.get("NFLVERSE_TMP", "/tmp/nflverse")

SEASON, WEEK = args.season, args.week
# Whatever fetch_plays.py last wrote, so the career totals include this season.
SRC = args.plays or sorted(
    p for p in os.listdir(HERE) if p.startswith("plays_") and p.endswith(".parquet"))[-1]
SRC = SRC if os.path.isabs(SRC) else os.path.join(HERE, SRC)
# venue / kicker split, overridable: W_VENUE=0.75 python3 weekly_kickers.py
W_VENUE = float(os.environ.get("W_VENUE", 0.50))
W_KICKER = 1.0 - W_VENUE
# Attempts at which a kicker's own rate earns half weight. The empirical value
# from the year-to-year correlation of distance-adjusted FG% (r = 0.102, so
# k = n(1-r)/r at a typical n of 28) is about 250; raw FG% implies 600. Lower
# values trust the kicker more. Overridable.
K_SHRINK = float(os.environ.get("K_SHRINK", 100))
# "symmetric" shrinks every kicker toward the league average, which is the
# statistically correct move but pulls BAD small-sample kickers up as well as
# good ones down. "onesided" shrinks only kickers above average - a prove-it
# rule that discounts small-sample hot numbers while letting a poor record
# stand. Not standard statistics; a deliberate design choice.
SHRINK_MODE = os.environ.get("SHRINK_MODE", "onesided")
SCHED = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
ROSTER = ("https://github.com/nflverse/nflverse-data/releases/download/"
          f"rosters/roster_{SEASON}.parquet")


# Venues whose stadium_id was REUSED for a different physical building. nfldata
# keeps BUF00 for the Bills' new stadium, so 2002-2025 numbers from the old
# ground in Orchard Park would otherwise be applied to a building that opened in
# 2026. A venue listed here has no usable history from that season on, and falls
# back to the league average like any other unknown ground.
REBUILT = {"BUF00": 2026}


def rebuilt(stadium_id, season):
    return stadium_id in REBUILT and season >= REBUILT[stadium_id]


def hdr(t):
    print("\n" + "=" * 100 + f"\n{t}\n" + "=" * 100)


def sub(t):
    print(f"\n-- {t}")


def grab(url, name, refresh=False):
    os.makedirs(TMP, exist_ok=True)
    path = os.path.join(TMP, name)
    if refresh or not os.path.exists(path):
        subprocess.run(["curl", "-sSL", "--retry", "4", "-o", path, url], check=True)
    return path


ACTIVE = "A01"          # nflverse status_description_abbr for a genuinely active player
PBP = ("https://github.com/nflverse/nflverse-data/releases/download/"
       f"pbp/play_by_play_{SEASON}.parquet")


def plays_with_current_season():
    """The archive parquet, plus this season's completed games.

    Career rates have to move as men kick, and the archive is only refreshed
    when fetch_plays.py is re-run. The current season's pbp release is small,
    so it is pulled fresh every time and appended - restricted to the columns
    the archive already carries, so the frame keeps its shape.
    """
    d = pd.read_parquet(SRC)
    try:
        path = grab(PBP, f"pbp_{SEASON}.parquet", refresh=True)
        cols = [c for c in d.columns if c in set(pq_columns(path))]
        cur = pd.read_parquet(path, columns=cols)
        cur = cur[~cur.season.isin(d.season.unique())]
        if len(cur):
            weeks = sorted(cur[cur.season_type.eq("REG")].week.unique())
            note = (f"  {SEASON} weeks folded into the career rates: "
                    + ", ".join(str(int(w)) for w in weeks))
            return pd.concat([d, cur], ignore_index=True), note
        return d, f"  {SEASON} is already in the archive parquet"
    except Exception as e:
        return d, f"  no separate {SEASON} play-by-play ({type(e).__name__})"


def pq_columns(path):
    import pyarrow.parquet as pq
    return pq.ParquetFile(path).schema.names


def pick_kickers(ros, week, season):
    """One kicker per team for this week, with the reason when it is not obvious.

    status == "ACT" is not enough: nflverse files injured reserve under ACT
    with a status_description_abbr of I01, so a man on IR can outrank the
    practice-squad kicker who is actually taking the snaps. Prefer A01; if a
    team has none, fall back to whoever last attempted a kick for them this
    season, which is how an elevation shows up.
    """
    k = ros[ros.position.eq("K")]
    if "week" in k.columns and k.week.notna().any():
        wks = sorted(k.week.dropna().unique())
        k = k[k.week.eq(week if week in wks else max(wks))]
    active = k[k.status_description_abbr.eq(ACTIVE)]
    try:
        cur = pd.read_parquet(os.path.join(TMP, f"pbp_{season}.parquet"),
                              columns=["posteam", "week", "play_type",
                                       "kicker_player_id", "kicker_player_name"])
        cur = cur[cur.play_type.isin(["field_goal", "extra_point"])
                  & cur.kicker_player_id.notna()]
        last = (cur.sort_values("week").groupby("posteam")
                .agg(kid=("kicker_player_id", "last")))
    except Exception:
        last = pd.DataFrame(columns=["kid"])

    out, notes = {}, []
    for team in sorted(set(ros.team.dropna())):
        a = active[active.team.eq(team)]
        if len(a) == 1:
            out[team] = (a.iloc[0].full_name, a.iloc[0].gsis_id)
        elif team in last.index:
            kid = last.loc[team, "kid"]
            row = k[k.gsis_id.eq(kid)]
            name = row.iloc[0].full_name if len(row) else str(kid)
            tag = (f"{row.iloc[0].status}/{row.iloc[0].status_description_abbr}"
                   if len(row) else "not on the roster file")
            benched = ", ".join(f"{x.full_name} ({x.status_description_abbr})"
                                for _, x in k[k.team.eq(team)].iterrows()
                                if x.gsis_id != kid)
            out[team] = (name, kid)
            notes.append(f"  {team}: no active (A01) kicker listed - using "
                         f"{name} [{tag}], who kicked most recently"
                         + (f"; the roster also lists {benched}" if benched else ""))
        elif len(a) > 1:
            out[team] = (a.iloc[0].full_name, a.iloc[0].gsis_id)
            notes.append(f"  {team}: {len(a)} active kickers, took "
                         f"{a.iloc[0].full_name}")
        else:
            notes.append(f"  {team}: no kicker found at all")
    return out, notes


def publish(r, league):
    """Write the week's kicker list in the shape the site reads.

    The published order is the shrunk one. A kicker with nineteen career
    attempts and a 94.7% rate has not shown he is better than anyone; ranking
    him on that number would be ranking him on nineteen coin flips.

    MC does not get a separate kicker board. Nobody has vibes about kickers,
    and inventing a second order so the delta column has something to show
    would be inventing a disagreement. His column mirrors the model, which is
    what a delta of zero honestly means.
    """
    out = os.path.join(ROOT, "data", "weekly", str(SEASON), f"week-{WEEK:02d}")
    os.makedirs(out, exist_ok=True)
    rows = []
    for _, x in r.sort_values("score_shrunk", ascending=False).iterrows():
        where = "at home" if x.role == "home" else f"at {x.venue}"
        note = f"{100 * x.venue_rate:.1f}% venue rate {where}. "
        if x.k_att:
            note += (f"{100 * x.kicker_rate:.1f}% on {x.k_att} career kicks, "
                     f"weighted {x.shrink_w:.2f}.")
        else:
            note += "No NFL attempts yet, so his own rate is the league average."
        rows.append({"rank_data": len(rows) + 1, "rank_vibes": len(rows) + 1,
                     "player": x.kicker, "team": x.team,
                     "note_data": note, "note_vibes": ""})
    path = os.path.join(out, "k.csv")
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["rank_data", "rank_vibes", "player",
                                           "team", "note_data", "note_vibes"])
        w.writeheader()
        w.writerows(rows)
    print(f"\n  wrote {path}  ({len(rows)} kickers)")


def main():
    # ------------------------------------------------------------- inputs
    ts = open(STADIUMS).read()
    venues = {v["id"]: v for v in json.loads(
        re.search(r"export const stadiums[^=]*=\s*(\[.*?\]);", ts, re.S).group(1))}

    g = pd.read_csv(grab(SCHED, "games.csv", refresh=True))
    wk = g[(g.season == SEASON) & (g.week == WEEK)].copy()

    ros = pd.read_parquet(grab(ROSTER, f"roster_{SEASON}.parquet", refresh=True))

    plays, pbp_note = plays_with_current_season()
    ks, ks_notes = pick_kickers(ros, WEEK, SEASON)

    d, _ = add_adjusted(plays)
    fg = d[d.is_fg & d.season_type.eq("REG")]
    league = fg[fg.season.ge(2023)].made.mean()
    by_id = fg.groupby("kicker_player_id").agg(att=("made", "size"),
                                               made=("made", "sum"))
    by_id["pct"] = by_id.made / by_id.att

    hdr(f"WEEK {WEEK}, {SEASON} - KICKER RANKING")
    print(f"model            : score = {W_VENUE:.2f} x venue rate + "
          f"{W_KICKER:.2f} x kicker rate")
    print(f"league average   : {league:.4f} (all regular-season attempts, "
          f"2023 onward)")
    print(f"venue rate       : visPct from stadiums.ts for a visitor, "
          f"visPct + gap for the home kicker")
    print(f"kicker rate      : career REGULAR-SEASON field goal percentage, "
          f"blocks included")
    print(f"games            : {len(wk)}")
    print(pbp_note)

    sub("who is kicking, where the roster needed a second look")
    print("\n".join(ks_notes) if ks_notes else
          "  every team has exactly one genuinely active (A01) kicker")

    rows = []
    for _, m in wk.iterrows():
        v = None if rebuilt(m.stadium_id, SEASON) else venues.get(m.stadium_id)
        for team, role in [(m.away_team, "visitor"), (m.home_team, "home")]:
            kname, kid = ks.get(team, (None, None))
            rec = by_id.loc[kid] if kid in by_id.index else None
            kpct = float(rec.pct) if rec is not None else np.nan
            katt = int(rec.att) if rec is not None else 0
            if v is None:
                vpct = np.nan
                vsrc = ("new building, no history yet"
                        if rebuilt(m.stadium_id, SEASON) else "no venue history")
            elif role == "visitor":
                vpct, vsrc = v["visPct"] / 100.0, f"visPct {v['visPct']:.1f}"
            else:
                vpct = (v["visPct"] + v["gap"]) / 100.0
                vsrc = f"visPct {v['visPct']:.1f} + gap {v['gap']:+.1f}"
            rows.append({
                "team": team, "kicker": kname or "?",
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
        why = ("is a new building with no history yet" if rebuilt(x.venue_id, SEASON)
               else "has no entry in stadiums.ts")
        print(f"  {x.venue_id} ({x.venue}) {why} - {x.team} {x.role}")
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

    if args.publish:
        publish(r, league)

    tag = (f"{int(100 * W_VENUE)}_{int(100 * W_KICKER)}"
           f"_k{K_SHRINK:.0f}_{SHRINK_MODE}")
    r.to_csv(os.path.join(HERE, f"week{WEEK}_{SEASON}_kickers_{tag}.csv"),
             index=False)
    print(f"\n  wrote week{WEEK}_{SEASON}_kickers_{tag}.csv")
    return r


if __name__ == "__main__":
    main()
