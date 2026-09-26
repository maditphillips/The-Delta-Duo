"""Kicker ranking on EXPECTED FANTASY POINTS, not expected make rate.

Why this exists. The published board ranks a kicker by how likely he is to
make one kick. Two weeks of 2026 graded it at 44.8% pairwise against real
scoring - worse than a coin flip - because points are mostly volume and the
board has no volume in it.

Volume, though, is not "which team kicks more field goals". That is very
nearly not a real thing:

    true between-team sd in FG attempts per game : 0.066
    reliability of a WHOLE SEASON of FGA         : 3.5%
    year-to-year correlation of team FGA/game    : +0.065

What is real is how much a team scores, and it reaches the kicker through
extra points. Across deciles of Vegas implied team total, field goal attempts
move 1.78 -> 1.94 while extra points move 1.53 -> 3.27.

So the model is built the way the points are actually made:

    E[points] = E[XPA | implied team total] x 0.910
              + E[FGA | implied, total, spread] x points-per-attempt(make rate)

    make rate = 0.50 x venue rate + 0.50 x shrunk career rate   (the old board)

Points-per-attempt turns the make rate into points through the league's own
distance mix. Note it is nearly flat across distance - 2.78 points per attempt
under 40 yards, 2.94 in the forties, 2.93 from 50+ - because a long kick is
worth more when it goes in and misses more often, and the two almost cancel.
That is why the distance mix is taken as a league constant and only the make
rate moves.

Held out on 2023-2025, ranking every kicker within each week:

    accuracy + venue only (the published board) : 53.5%
    volume only                                 : 55.5%
    volume + accuracy + venue                   : 55.9%

Scoring is Sleeper standard, which is also every other site's: FG under 40 = 3,
40-49 = 4, 50+ = 5, XP = 1, missed FG = -1, missed XP = -1.

    python3 kicker_points.py --week 4
    python3 kicker_points.py --week 4 --publish
    python3 kicker_points.py --backtest 2026        # grade it against a season
"""
from __future__ import annotations

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
import statsmodels.formula.api as smf
from scipy.optimize import brentq

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--season", type=int, default=2026)
ap.add_argument("--week", type=int, default=0, help="the week to rank")
ap.add_argument("--backtest", type=int, default=0, help="grade every week of this season")
ap.add_argument("--publish", action="store_true", help="write data/weekly/<season>/week-NN/k.csv")
ap.add_argument("--train-through", type=int, default=0,
                help="last season of the fit; defaults to the season before --season")
args, _ = ap.parse_known_args()

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
STADIUMS = os.path.join(ROOT, "src", "data", "stadiums.ts")
TMP = os.environ.get("NFLVERSE_TMP", "/tmp/nflverse")
SRC = os.path.join(HERE, "plays_1999_2025.parquet")

SEASON = args.season
TRAIN_THROUGH = args.train_through or (SEASON - 1)
FIT_FROM = 2012                      # first season with a full set of betting lines we trust
K_SHRINK = float(os.environ.get("K_SHRINK", 100))
W_VENUE = float(os.environ.get("W_VENUE", 0.50))
ACTIVE = "A01"
SCHED = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
ROSTER = ("https://github.com/nflverse/nflverse-data/releases/download/"
          f"rosters/roster_{SEASON}.parquet")
PBP = ("https://github.com/nflverse/nflverse-data/releases/download/"
       f"pbp/play_by_play_{SEASON}.parquet")
PLAY_COLS = ["season", "week", "season_type", "game_id", "posteam", "play_type",
             "field_goal_result", "kick_distance", "extra_point_result",
             "kicker_player_id"]


def hdr(t):
    print("\n" + "=" * 100 + f"\n{t}\n" + "=" * 100)


def sub(t):
    print(f"\n-- {t}")


def grab(url, name, refresh=False):
    os.makedirs(TMP, exist_ok=True)
    p = os.path.join(TMP, name)
    if refresh or not os.path.exists(p):
        subprocess.run(["curl", "-sSL", "--retry", "4", "-o", p, url], check=True)
    return p


def pq_columns(path):
    import pyarrow.parquet as pq
    return set(pq.ParquetFile(path).schema.names)


def kick_plays():
    """Every field goal and extra point, archive plus the current season."""
    d = pd.read_parquet(SRC, columns=PLAY_COLS)
    try:
        p = grab(PBP, f"pbp_{SEASON}.parquet", refresh=True)
        cur = pd.read_parquet(p, columns=[c for c in PLAY_COLS if c in pq_columns(p)])
        cur = cur[~cur.season.isin(d.season.unique())]
        d = pd.concat([d, cur], ignore_index=True)
    except Exception as e:
        print(f"  ! no separate {SEASON} play-by-play ({type(e).__name__})")
    return d[d.season_type.eq("REG") & d.posteam.notna()]


def fantasy(d):
    """Sleeper-standard points on every kick, and the Vegas line for the game."""
    fg = d[d.play_type.eq("field_goal") & d.field_goal_result.notna()].copy()
    fg["made"] = fg.field_goal_result.eq("made")
    fg["pts"] = np.where(~fg.made, -1.0,
                         np.where(fg.kick_distance >= 50, 5.0,
                                  np.where(fg.kick_distance >= 40, 4.0, 3.0)))
    xp = d[d.play_type.eq("extra_point") & d.extra_point_result.notna()].copy()
    xp["pts"] = np.where(xp.extra_point_result.eq("good"), 1.0, -1.0)
    return fg, xp


def team_games(fg, xp, g):
    K = ["season", "week", "game_id", "posteam"]
    base = pd.concat([fg[K], xp[K]]).drop_duplicates()
    a = fg.groupby(K, as_index=False).agg(fga=("made", "size"), fgpts=("pts", "sum"))
    b = xp.groupby(K, as_index=False).agg(xpa=("pts", "size"), xppts=("pts", "sum"))
    t = base.merge(a, on=K, how="left").merge(b, on=K, how="left")
    for c in ["fga", "fgpts", "xpa", "xppts"]:
        t[c] = t[c].fillna(0.0)
    t["pts"] = t.fgpts + t.xppts
    t = t.merge(g[["game_id", "home_team", "spread_line", "total_line", "stadium_id"]],
                on="game_id", how="left")
    return add_lines(t)


def add_lines(t):
    """Implied team total: half the game total, shifted by half the spread.

    nfldata's spread_line is from the home team's side, positive when the home
    team is favoured.
    """
    home = t.posteam.eq(t.home_team)
    t["implied"] = t.total_line / 2 + np.where(home, t.spread_line / 2, -t.spread_line / 2)
    t["abs_spread"] = t.spread_line.abs()
    t["is_home"] = home
    return t


def band_table(fg):
    """League attempt mix, make rate and value, by distance band."""
    f = fg[fg.kick_distance.between(18, 70)].copy()
    f["band"] = pd.cut(f.kick_distance, [0, 39, 49, 99], labels=["u40", "40s", "50p"])
    z = f.groupby("band", observed=True).made.agg(n="size", p="mean")
    return (z.n / z.n.sum()).to_numpy(), z.p.to_numpy(), np.array([3.0, 4.0, 5.0])


def make_ppa(share, prob, value):
    """points-per-attempt as a function of a kicker's overall make rate.

    The make rate is spread back over the league's distance bands as a shift in
    log-odds, so a better leg is better at every distance rather than uniformly
    better in percentage points.
    """
    lo = np.log(prob / (1 - prob))

    def f(r):
        try:
            b = brentq(lambda s: (share / (1 + np.exp(-(lo + s)))).sum() - r, -6, 6)
        except ValueError:
            b = 0.0
        q = 1 / (1 + np.exp(-(lo + b)))
        return float((share * (q * value - (1 - q))).sum())
    return f


def career_rates(fg, upto=None):
    """Career make rate per kicker, optionally only through a given (season, week)."""
    f = fg if upto is None else fg[fg.season * 100 + fg.week < upto]
    z = f.groupby("kicker_player_id").made.agg(n="size", m="sum")
    z["raw"] = z.m / z.n
    return z


def shrink(raw, n, league):
    w = n / (n + K_SHRINK)
    w = np.where(raw > league, w, 1.0)          # one-sided: a hot small sample must earn it
    return league + w * (raw - league), w


def venues():
    ts = open(STADIUMS).read()
    return {v["id"]: v for v in json.loads(
        re.search(r"export const stadiums[^=]*=\s*(\[.*?\]);", ts, re.S).group(1))}


def venue_rate(V, stadium_id, home, league):
    v = V.get(stadium_id)
    if v is None:
        return league, "no venue history, league average"
    if home:
        return (v["visPct"] + v["gap"]) / 100.0, f"visPct {v['visPct']:.1f} + gap {v['gap']:+.1f}"
    return v["visPct"] / 100.0, f"visPct {v['visPct']:.1f}"


def pick_kickers(ros, week, season):
    """A01 first; then whoever last attempted a kick for the team this season."""
    k = ros[ros.position.eq("K")]
    if "week" in k.columns and k.week.notna().any():
        wks = sorted(k.week.dropna().unique())
        k = k[k.week.eq(week if week in wks else max(wks))]
    active = k[k.status_description_abbr.eq(ACTIVE)]
    try:
        cur = pd.read_parquet(os.path.join(TMP, f"pbp_{season}.parquet"),
                              columns=["posteam", "week", "play_type", "kicker_player_id"])
        cur = cur[cur.play_type.isin(["field_goal", "extra_point"])
                  & cur.kicker_player_id.notna()]
        last = cur.sort_values("week").groupby("posteam").agg(kid=("kicker_player_id", "last"))
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
            out[team] = (name, kid)
            notes.append(f"  {team}: no active (A01) kicker listed - using {name} [{tag}], "
                         f"who kicked most recently")
        elif len(a) > 1:
            out[team] = (a.iloc[0].full_name, a.iloc[0].gsis_id)
            notes.append(f"  {team}: {len(a)} active kickers, took {a.iloc[0].full_name}")
        else:
            notes.append(f"  {team}: no kicker found at all")
    return out, notes


def fit(t):
    """The two volume equations, fit on seasons up to TRAIN_THROUGH."""
    f = t[t.season.between(FIT_FROM, TRAIN_THROUGH)].dropna(
        subset=["implied", "total_line", "spread_line"])
    return (smf.ols("xpa ~ implied", data=f).fit(),
            smf.ols("fga ~ implied + total_line + abs_spread", data=f).fit(),
            f)


def pairwise(rank, val):
    rank, val = np.asarray(rank, float), np.asarray(val, float)
    right = total = 0
    for i in range(len(rank)):
        for j in range(i + 1, len(rank)):
            if val[i] == val[j]:
                continue
            total += 1
            hi = i if val[i] > val[j] else j
            pick = i if rank[i] < rank[j] else j
            right += (hi == pick)
    return right, total


def build(week, t, fg, mx, mf, ppa, league, V, g, ks=None):
    """One row per kicker on the week's slate, with expected points."""
    wk = g[(g.season == SEASON) & (g.week == week)]
    car = career_rates(fg, upto=SEASON * 100 + week)
    rows = []
    for _, m in wk.iterrows():
        for team, home in [(m.away_team, False), (m.home_team, True)]:
            name, kid = ks.get(team, ("?", None))
            n = int(car.n.get(kid, 0)) if kid else 0
            raw = float(car.raw.get(kid, league)) if n else league
            sh, w = shrink(np.array([raw]), np.array([n]), league)
            vr, vsrc = venue_rate(V, m.stadium_id, home, league)
            make = W_VENUE * vr + (1 - W_VENUE) * sh[0]
            implied = m.total_line / 2 + (m.spread_line / 2 if home else -m.spread_line / 2)
            x = pd.DataFrame([{"implied": implied, "total_line": m.total_line,
                               "abs_spread": abs(m.spread_line)}])
            exp_xpa = float(mx.predict(x).iloc[0])
            exp_fga = float(mf.predict(x).iloc[0])
            rows.append({
                "team": team, "kicker": name, "role": "home" if home else "visitor",
                "opp": m.away_team if home else m.home_team,
                "venue": V.get(m.stadium_id, {}).get("name", m.stadium),
                "venue_id": m.stadium_id, "venue_rate": vr, "venue_src": vsrc,
                "k_att": n, "raw_rate": raw, "shrunk": sh[0], "shrink_w": w[0],
                "make": make, "implied": implied, "total": m.total_line,
                "spread": m.spread_line, "exp_xpa": exp_xpa, "exp_fga": exp_fga,
                "ppa": ppa(make),
            })
    r = pd.DataFrame(rows)
    r["xp_pts"] = r.exp_xpa * (2 * league_xp - 1)
    r["fg_pts"] = r.exp_fga * r.ppa
    r["exp_pts"] = r.xp_pts + r.fg_pts
    return r.sort_values("exp_pts", ascending=False).reset_index(drop=True)


def publish(r, week):
    out = os.path.join(ROOT, "data", "weekly", str(SEASON), f"week-{week:02d}")
    os.makedirs(out, exist_ok=True)
    rows = []
    for i, (_, x) in enumerate(r.iterrows(), start=1):
        where = "at home" if x.role == "home" else f"at {x.venue}".replace("®", "")
        note = (f"{x.exp_pts:.1f} expected points. {x.implied:.1f} implied team total "
                f"{where} -> {x.exp_xpa:.1f} extra points and {x.exp_fga:.1f} field goals "
                f"at a {100 * x.make:.1f}% make rate.")
        rows.append({"rank_data": i, "rank_vibes": i, "player": x.kicker,
                     "team": x.team, "note_data": note, "note_vibes": ""})
    p = os.path.join(out, "k.csv")
    with open(p, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["rank_data", "rank_vibes", "player", "team",
                                           "note_data", "note_vibes"])
        w.writeheader(); w.writerows(rows)
    print(f"\n  wrote {os.path.relpath(p, ROOT)}  ({len(rows)} kickers)")


def main():
    g = pd.read_csv(grab(SCHED, "games.csv", refresh=True))
    d = kick_plays()
    fg, xp = fantasy(d)
    t = team_games(fg, xp, g)
    share, prob, value = band_table(fg[fg.season.ge(FIT_FROM)])
    ppa = make_ppa(share, prob, value)
    global league_xp
    league_xp = float(xp[xp.season.ge(FIT_FROM)].pts.gt(0).mean())
    league = float(fg[fg.season.ge(SEASON - 3)].made.mean())
    mx, mf, fitset = fit(t)
    V = venues()

    hdr(f"EXPECTED KICKER POINTS - {SEASON}")
    print(f"fit on            : {FIT_FROM}-{TRAIN_THROUGH}, {len(fitset):,} team-games")
    print(f"E[XPA]            : {mx.params['Intercept']:+.3f} "
          f"{mx.params['implied']:+.4f} x implied team total   (R2 {mx.rsquared:.3f})")
    print(f"E[FGA]            : {mf.params['Intercept']:+.3f} "
          f"{mf.params['implied']:+.4f} x implied {mf.params['total_line']:+.4f} x total "
          f"{mf.params['abs_spread']:+.4f} x |spread|   (R2 {mf.rsquared:.4f})")
    print(f"league make rate  : {league:.4f}      XP make rate: {league_xp:.4f}")
    print(f"points/attempt    : {ppa(0.80):.3f} at 80%, {ppa(league):.3f} at league, "
          f"{ppa(0.92):.3f} at 92%")

    if args.backtest:
        hdr(f"BACKTEST - {args.backtest}, every completed week")
        played = sorted(d[d.season.eq(args.backtest)].week.unique())
        # the man who actually kicked that week, so the grade is not distorted by
        # today's roster being applied to a game three weeks old
        act_k = (d[d.season.eq(args.backtest) & d.play_type.isin(["field_goal", "extra_point"])]
                 .groupby(["week", "posteam", "kicker_player_id"]).size().rename("n").reset_index()
                 .sort_values("n", ascending=False).drop_duplicates(["week", "posteam"]))
        names = (d.dropna(subset=["kicker_player_id"])
                 .drop_duplicates("kicker_player_id").set_index("kicker_player_id"))
        rows = []
        for wk in played:
            w_k = act_k[act_k.week.eq(wk)]
            ks = {r.posteam: (str(r.kicker_player_id), r.kicker_player_id)
                  for r in w_k.itertuples()}
            r = build(wk, t, fg, mx, mf, ppa, league, V, g, ks)
            act = t[(t.season == args.backtest) & (t.week == wk)][["posteam", "pts"]]
            r = r.merge(act, left_on="team", right_on="posteam", how="left")
            r["week"] = wk
            rows.append(r)
        b = pd.concat(rows, ignore_index=True).dropna(subset=["pts"])
        print(f"  {'week':6} {'n':>4} {'expected points':>18} {'make rate only':>18}")
        TR = TT = AR = AT = 0
        for wk, grp in b.groupby("week"):
            r1, n1 = pairwise(grp.exp_pts.rank(ascending=False, method="first"), grp.pts)
            r2, n2 = pairwise(grp.make.rank(ascending=False, method="first"), grp.pts)
            TR += r1; TT += n1; AR += r2; AT += n2
            print(f"  week {wk:<2} {len(grp):4d} {r1:6d}/{n1:<4} {100*r1/n1:5.1f}%"
                  f"   {r2:6d}/{n2:<4} {100*r2/n2:5.1f}%")
        print(f"  {'total':6} {len(b):4d} {TR:6d}/{TT:<4} {100*TR/TT:5.1f}%"
              f"   {AR:6d}/{AT:<4} {100*AR/AT:5.1f}%")
        return b

    week = args.week
    ros = pd.read_parquet(grab(ROSTER, f"roster_{SEASON}.parquet", refresh=True))
    ks, notes = pick_kickers(ros, week, SEASON)
    r = build(week, t, fg, mx, mf, ppa, league, V, g, ks)
    sub("who is kicking, where the roster needed a second look")
    print("\n".join(notes) if notes else "  every team has exactly one active (A01) kicker")

    hdr(f"WEEK {week}, {SEASON} - BY EXPECTED FANTASY POINTS")
    print(f"{'#':>3}  {'kicker':18} {'tm':4} {'opp':4} {'role':8} {'impl':>5} "
          f"{'xXPA':>5} {'xFGA':>5} {'make':>6} {'pt/att':>6} {'XPpts':>6} {'FGpts':>6} {'TOTAL':>6}")
    for i, (_, x) in enumerate(r.iterrows(), start=1):
        print(f"{i:3d}  {x.kicker:18} {x.team:4} {x.opp:4} {x.role:8} {x.implied:5.1f} "
              f"{x.exp_xpa:5.2f} {x.exp_fga:5.2f} {100*x.make:6.1f} {x.ppa:6.3f} "
              f"{x.xp_pts:6.2f} {x.fg_pts:6.2f} {x.exp_pts:6.2f}")
    if args.publish:
        publish(r, week)
    return r


if __name__ == "__main__":
    main()
