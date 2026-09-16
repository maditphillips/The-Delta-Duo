"""Weekly kicker ranking: venue expectation blended with the kicker's own rate.

The model, locked in after week 1:

    score = 0.50 x venue_rate + 0.50 x [league + w x (kicker_rate - league)]
    w     = n / (n + 100), applied ONE-SIDED (only to kickers above league)

venue_rate is the venue's field goal percentage for a kicker in that role -
visPct straight from src/data/stadiums.ts for a visitor, visPct + gap for the
home kicker - and kicker_rate is his regular-season career field goal
percentage, blocks included.

This generalises week1_kickers.py to any week, and folds the current season's
completed games into the career rates, so a kicker's number moves as he kicks.
The 1999-2025 archive parquet is the base; the current-season pbp release is
appended if it exists.

Picking each team's kicker is not just "status == ACT": nflverse marks injured
reserve as ACT too (status_description_abbr I01), so the roster's headline
kicker can be a man who will not kick. The rule here is A01 (genuinely active)
first, then whoever most recently attempted a kick for that team this season -
which is how a practice-squad elevation gets found.

Run fetch_plays.py once, then:

    WEEK=2 python3 weekly_kickers.py > WEEK2.txt
"""
import json
import os
import re
import subprocess
import warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

from epa_common import tag_kicks

pd.set_option("display.width", 240)
pd.set_option("display.max_columns", 60)
pd.set_option("display.max_rows", 100)

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "plays_1999_2025.parquet")
STADIUMS = os.path.join(HERE, "..", "..", "..", "src", "data", "stadiums.ts")
TMP = os.environ.get("NFLVERSE_TMP", "/tmp/nflverse")

SEASON = int(os.environ.get("SEASON", 2026))
WEEK = int(os.environ.get("WEEK", 2))
# the locked-in model; all three stay overridable for sensitivity checks
W_VENUE = float(os.environ.get("W_VENUE", 0.50))
W_KICKER = 1.0 - W_VENUE
K_SHRINK = float(os.environ.get("K_SHRINK", 100))
SHRINK_MODE = os.environ.get("SHRINK_MODE", "onesided")

SCHED = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
ROSTER = ("https://github.com/nflverse/nflverse-data/releases/download/"
          f"rosters/roster_{SEASON}.parquet")
PBP = ("https://github.com/nflverse/nflverse-data/releases/download/"
       f"pbp/play_by_play_{SEASON}.parquet")
# the columns tag_kicks needs, plus the ones the ranking reads
KICK_COLS = ["season", "season_type", "week", "play_type", "field_goal_attempt",
             "field_goal_result", "kick_distance", "yardline_100", "touchdown",
             "kicker_player_id", "kicker_player_name"]
ACTIVE = "A01"          # nflverse status_description_abbr for a genuinely active player


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


def pick_kickers(ros, week, season):
    """One kicker per team for this week, with why.

    status == 'ACT' is not enough: nflverse files injured reserve under ACT
    with a status_description_abbr of I01, so a man on IR outranks the
    practice-squad kicker who is actually taking the snaps. Prefer A01; if a
    team has none, fall back to whoever last attempted a kick for them this
    season, which is how an elevation shows up.
    """
    k = ros[ros.position.eq("K")]
    if "week" in k.columns and k.week.notna().any():
        wks = sorted(k.week.dropna().unique())
        use = week if week in wks else max(wks)
        k = k[k.week.eq(use)]
    active = k[k.status_description_abbr.eq(ACTIVE)]

    # most recent kicker per team from this season's play-by-play
    try:
        cur = pd.read_parquet(os.path.join(TMP, f"pbp_{season}.parquet"),
                              columns=["posteam", "week", "play_type",
                                       "kicker_player_id", "kicker_player_name"])
        cur = cur[cur.play_type.isin(["field_goal", "extra_point"])
                  & cur.kicker_player_id.notna()]
        last = (cur.sort_values("week").groupby("posteam")
                .agg(kid=("kicker_player_id", "last"),
                     kname=("kicker_player_name", "last")))
    except Exception:
        last = pd.DataFrame(columns=["kid", "kname"])

    out, notes = {}, []
    for team in sorted(set(ros.team.dropna())):
        a = active[active.team.eq(team)]
        if len(a) == 1:
            out[team] = (a.iloc[0].full_name, a.iloc[0].gsis_id)
            continue
        if team in last.index:
            kid = last.loc[team, "kid"]
            row = k[k.gsis_id.eq(kid)]
            name = (row.iloc[0].full_name if len(row)
                    else str(last.loc[team, "kname"]))
            tag = (f"{row.iloc[0].status}/{row.iloc[0].status_description_abbr}"
                   if len(row) else "not on the roster file")
            out[team] = (name, kid)
            benched = ", ".join(f"{x.full_name} ({x.status_description_abbr})"
                                for _, x in k[k.team.eq(team)].iterrows()
                                if x.gsis_id != kid)
            notes.append(f"  {team}: no active (A01) kicker on the roster - "
                         f"using {name} [{tag}], who kicked most recently"
                         + (f"; roster also lists {benched}" if benched else ""))
        elif len(a) > 1:
            out[team] = (a.iloc[0].full_name, a.iloc[0].gsis_id)
            notes.append(f"  {team}: {len(a)} active kickers, took "
                         f"{a.iloc[0].full_name}")
        else:
            notes.append(f"  {team}: no kicker found at all")
    return out, notes


def career_rates():
    """Career regular-season FG attempts and makes by kicker, through the last
    completed game. Archive plus the current season if it has started."""
    frames = [pd.read_parquet(SRC, columns=[c for c in KICK_COLS if c != "week"])]
    try:
        cur = pd.read_parquet(grab(PBP, f"pbp_{SEASON}.parquet", refresh=True),
                              columns=KICK_COLS)
        played = sorted(cur[cur.season_type.eq("REG")].week.unique())
        note = (f"  {SEASON} regular-season weeks folded into career rates: "
                f"{', '.join(str(int(w)) for w in played) or 'none yet'}")
    except Exception as e:                                    # season not posted
        cur, note = None, f"  no {SEASON} play-by-play yet ({type(e).__name__})"
    d = pd.concat([frames[0], cur], ignore_index=True) if cur is not None else frames[0]
    d = tag_kicks(d)
    fg = d[d.is_fg & d.season_type.eq("REG")]
    league = fg[fg.season.ge(SEASON - 3)].made.mean()
    by_id = fg.groupby("kicker_player_id").agg(att=("made", "size"),
                                               made=("made", "sum"))
    by_id["pct"] = by_id.made / by_id.att
    return by_id, league, note


def main():
    # ------------------------------------------------------------- inputs
    ts = open(STADIUMS).read()
    venues = {v["id"]: v for v in json.loads(
        re.search(r"export const stadiums[^=]*=\s*(\[.*?\]);", ts, re.S).group(1))}

    g = pd.read_csv(grab(SCHED, "games.csv", refresh=True))
    wk = g[(g.season == SEASON) & (g.week == WEEK)].copy()

    ros = pd.read_parquet(grab(ROSTER, f"roster_{SEASON}.parquet", refresh=True))
    by_id, league, pbp_note = career_rates()
    ks, ks_notes = pick_kickers(ros, WEEK, SEASON)

    hdr(f"WEEK {WEEK}, {SEASON} - KICKER RANKING")
    print(f"model            : score = {W_VENUE:.2f} x venue rate + "
          f"{W_KICKER:.2f} x shrunk kicker rate")
    print(f"shrinkage        : w = n/(n+{K_SHRINK:.0f}), {SHRINK_MODE}")
    print(f"league average   : {league:.4f} (all regular-season attempts, "
          f"{SEASON - 3}-{SEASON})")
    print(f"venue rate       : visPct from stadiums.ts for a visitor, "
          f"visPct + gap for the home kicker")
    print(f"kicker rate      : career REGULAR-SEASON field goal percentage, "
          f"blocks included")
    print(f"games            : {len(wk)}")
    print(pbp_note)

    rows = []
    for _, m in wk.iterrows():
        v = venues.get(m.stadium_id)
        for team, role in [(m.away_team, "visitor"), (m.home_team, "home")]:
            kname, kid = ks.get(team, (None, None))
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
                "team": team, "kicker": kname or "?",
                "role": role, "opp": m.home_team if role == "visitor" else m.away_team,
                "venue": (v["name"] if v else m.stadium)[:26],
                "venue_id": m.stadium_id, "venue_rate": vpct, "venue_src": vsrc,
                "kicker_rate": kpct, "k_att": katt,
            })
    r = pd.DataFrame(rows)

    sub("who is kicking, where the roster needed a second look")
    print("\n".join(ks_notes) if ks_notes else
          "  every team has exactly one genuinely active (A01) kicker")

    sub("gaps in the inputs, and how they are filled")
    nov, nok = r[r.venue_rate.isna()], r[r.kicker_rate.isna()]
    for _, x in nov.iterrows():
        print(f"  {x.venue_id} ({x.venue}) has no entry in stadiums.ts - "
              f"{x.team} {x.role}")
    print(f"    -> {len(nov)} venue rate(s) set to the league average, "
          f"{league:.4f}")
    for _, x in nok.iterrows():
        print(f"  {x.kicker} ({x.team}) has no regular-season NFL attempts")
    print(f"    -> {len(nok)} kicker rate(s) set to the league average, "
          f"{league:.4f}")
    r["venue_rate"] = r.venue_rate.fillna(league)
    r["kicker_rate"] = r.kicker_rate.fillna(league)

    # ------------------------------------------------------------ scoring
    r["rel"] = r.k_att / (r.k_att + K_SHRINK)
    if SHRINK_MODE == "onesided":
        # only discount kickers whose rate is ABOVE the league average
        w = np.where(r.kicker_rate > league, r.rel, 1.0)
    else:
        w = r.rel
    r["shrink_w"] = w
    r["kicker_shrunk"] = league + w * (r.kicker_rate - league)
    r["score"] = W_VENUE * r.venue_rate + W_KICKER * r.kicker_shrunk
    r["raw_score"] = W_VENUE * r.venue_rate + W_KICKER * r.kicker_rate
    r = r.sort_values("score", ascending=False).reset_index(drop=True)
    r["rank"] = r.index + 1
    # MC's placeholder column: the kickers arranged by unshrunk accuracy alone
    r["rank_acc"] = r.kicker_rate.rank(ascending=False, method="first").astype(int)

    hdr("THE RANKING")
    print(f"{'#':>3}  {'kicker':18} {'tm':4} {'role':8} {'venue':26} "
          f"{'venue':>7} {'raw':>7} {'att':>4} {'w':>5} {'shrunk':>7} "
          f"{'score':>7} {'acc#':>5}")
    for _, x in r.iterrows():
        print(f"{x['rank']:3d}  {x.kicker:18} {x.team:4} {x.role:8} {x.venue:26} "
              f"{x.venue_rate:7.4f} {x.kicker_rate:7.4f} {x.k_att:4d} "
              f"{x.shrink_w:5.2f} {x.kicker_shrunk:7.4f} {x.score:7.4f} "
              f"{x.rank_acc:5d}")

    hdr("THE VENUES IN THIS SLATE, BEST TO WORST FOR THE MAN KICKING THERE")
    vr = r.sort_values("venue_rate", ascending=False)
    print(f"{'venue':28} {'tm':4} {'role':8} {'rate':>7}  source")
    for _, x in vr.iterrows():
        print(f"{x.venue:28} {x.team:4} {x.role:8} {x.venue_rate:7.4f}  "
              f"{x.venue_src}")

    hdr("WHERE THE SHRINKAGE BITES")
    print(f"  w = n/(n+{K_SHRINK:.0f}); w = 1.00 marks a below-average kicker, "
          f"whose record stands")
    print(f"\n{'kicker':18} {'att':>4} {'raw':>7} {'w':>6} {'shrunk':>7} "
          f"{'moved':>7} {'rank':>5} {'acc#':>5}")
    for _, x in r.sort_values("k_att").iterrows():
        print(f"{x.kicker:18} {x.k_att:4d} {x.kicker_rate:7.4f} {x.shrink_w:6.2f} "
              f"{x.kicker_shrunk:7.4f} {x.kicker_shrunk - x.kicker_rate:+7.4f} "
              f"{x['rank']:5d} {x.rank_acc:5d}")

    hdr("WHAT THIS MODEL RANKS, AND WHAT IT DOES NOT")
    print("  It ranks EXPECTED MAKE RATE on one kick. It says nothing about how")
    print("  many kicks a man gets, and that is where the rest of the")
    print("  disagreement with intuition lives. Volume - team quality, coach")
    print("  aggression, red-zone efficiency, the short leash - is a separate")
    print("  term and belongs in a separate term.")

    tag = (f"{int(100 * W_VENUE)}_{int(100 * W_KICKER)}"
           f"_k{K_SHRINK:.0f}_{SHRINK_MODE}")
    out = os.path.join(HERE, f"week{WEEK}_{SEASON}_kickers_{tag}.csv")
    r.to_csv(out, index=False)
    print(f"\n  wrote {os.path.basename(out)}")
    return r


if __name__ == "__main__":
    main()
