"""What is the 1.01 worth, in the same currency as the kicker?

Run fetch_plays.py and fetch_draft.py first, then:
    python3 pick_value.py > PICK.txt

The kicker study prices everything in adjusted expected points added and
converts with the points-per-win regression from the same seasons. This
script does the same thing to the first overall pick, so the two numbers can
be put side by side.

Quarterbacks are priced directly: every snap where the player was the passer
or was the rusher on a dropback, summed in adjusted EPA (scoring plays
debited K, the expected points the opponent gets from the possession after
the score, exactly as in kicker_value.py), measured against a replacement
quarterback's rate per play.

Replacement level is the pooled rate of quarterback-seasons of 50 to 320
plays: the backups and spot starters a team actually turns to when it does
not have a starter. That is the correct baseline for a team holding the 1.01,
because a team holding the 1.01 usually does not have a starter.

Non-quarterback first picks cannot be priced this way -- play-by-play EPA has
no defensive attribution -- so they are reported on Pro Football Reference's
approximate value instead, and the quarterback numbers are read as the
best case for the pick rather than the average one.
"""
import os
import warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

from epa_common import add_adjusted

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 60)

HERE = os.path.dirname(os.path.abspath(__file__))
PLAYS = os.path.join(HERE, "plays_1999_2025.parquet")
DRAFT = os.path.join(HERE, "draft_picks.parquet")

WINDOW = list(range(1999, 2026))
PTS_PER_WIN = 35.8      # from kicker_value.py section 7, 2018-2025
GAMES = 17
ROOKIE_YEARS = 5        # first contract plus the fifth-year option
REPL_LO, REPL_HI = 50, 320
STARTER = 400

COLS = ["season", "season_type", "play_id", "game_id", "posteam", "play_type",
        "epa", "ep", "touchdown", "field_goal_result", "half_seconds_remaining",
        "passer_player_id", "passer_player_name", "rusher_player_id",
        "rusher_player_name", "qb_dropback", "qtr", "kicker_player_id",
        "field_goal_attempt", "kick_distance", "yardline_100"]


def hdr(t):
    print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)


def sub(t):
    print(f"\n-- {t}")


def qb_seasons(d):
    """Adjusted EPA and play counts per quarterback-season."""
    p = d[d.passer_player_id.notna()].groupby(
        ["season", "passer_player_id", "passer_player_name"], as_index=False).agg(
        n_pass=("aepa", "size"), e_pass=("aepa", "sum"))
    p = p.rename(columns={"passer_player_id": "pid", "passer_player_name": "name"})
    r = d[d.rusher_player_id.notna() & d.qb_dropback.eq(1)].groupby(
        ["season", "rusher_player_id"], as_index=False).agg(
        n_rush=("aepa", "size"), e_rush=("aepa", "sum"))
    r = r.rename(columns={"rusher_player_id": "pid"})
    q = p.merge(r, on=["season", "pid"], how="left").fillna({"n_rush": 0, "e_rush": 0})
    q["plays"] = q.n_pass + q.n_rush
    q["aepa"] = q.e_pass + q.e_rush
    q["per_play"] = q.aepa / q.plays
    return q


def main():
    # K is fit on every play, then the quarterback aggregation is regular
    # season only, so the yardstick matches kicker_value.py exactly
    d, _ = add_adjusted(pd.read_parquet(PLAYS, columns=COLS))
    d = d[d.season_type.eq("REG")]
    q = qb_seasons(d)

    hdr("0. THE QUARTERBACK YARDSTICK")
    repl = q[q.plays.between(REPL_LO, REPL_HI)]
    rate = repl.aepa.sum() / repl.plays.sum()
    st = q[q.plays.ge(STARTER)]
    srate = st.aepa.sum() / st.plays.sum()
    print(f"quarterback-seasons, {WINDOW[0]}-{WINDOW[-1]} regular season: "
          f"{len(q[q.plays.ge(50)]):,} with 50+ plays")
    print(f"  replacement level ({REPL_LO}-{REPL_HI} plays, {len(repl)} seasons): "
          f"{rate:+.4f} adjusted EPA per play")
    print(f"  full-time starters ({STARTER}+ plays, {len(st)} seasons)  : "
          f"{srate:+.4f}")
    print(f"  a {STARTER + 150:.0f}-play season at replacement level is worth "
          f"{(STARTER + 150) * rate:+.0f} points")
    print(f"\nwins above replacement = (per-play rate - {rate:.4f}) x plays "
          f"/ {PTS_PER_WIN}")
    q["war"] = (q.per_play - rate) * q.plays / PTS_PER_WIN

    sub("the scale, quarterback-seasons of 400+ plays")
    big = q[q.plays.ge(STARTER)].copy()
    for lab, p in [("best", 1.0), ("95th", 0.95), ("75th", 0.75), ("median", 0.5),
                   ("25th", 0.25), ("5th", 0.05), ("worst", 0.0)]:
        print(f"  {lab:>6}: {big.war.quantile(p):+5.2f} wins above replacement")
    print("\n  top 10 quarterback-seasons in the window:")
    print(big.nlargest(10, "war")[["season", "name", "plays", "aepa", "war"]]
             .round(2).to_string(index=False))

    # ---------------------------------------------------------- the 1.01
    hdr("1. WHO THE 1.01 HAS ACTUALLY BEEN")
    dp = pd.read_parquet(DRAFT)
    one = dp[dp.pick.eq(1) & dp["round"].eq(1)].copy()
    era = one[one.season.between(1999, 2025)]
    print(f"first overall picks 1999-2025: {len(era)}")
    print(era.position.value_counts().to_string())
    print(f"\n  quarterbacks: {100 * era.position.eq('QB').mean():.0f}% of them")
    print(f"  since 2010  : {100 * era[era.season >= 2010].position.eq('QB').mean():.0f}%")

    sub("the full list, with Pro Football Reference approximate value")
    show = era[["season", "team", "pfr_player_name", "position", "games",
                "seasons_started", "probowls", "allpro", "w_av", "dr_av"]]
    print(show.to_string(index=False))
    print("\n  w_av = weighted career approximate value, dr_av = value to the")
    print("  drafting team. Both are PFR's cross-position currency, not points.")

    # ------------------------------------------------- QB #1 picks in wins
    hdr("2. THE 1.01 QUARTERBACKS, PRICED IN WINS")
    qb1 = era[era.position.eq("QB") & era.season.between(1999, 2021)].copy()
    rows = []
    for _, r in qb1.iterrows():
        yrs = range(int(r.season), int(r.season) + ROOKIE_YEARS)
        s = q[q.pid.eq(r.gsis_id) & q.season.isin(yrs)]
        played = s[s.plays >= 100]
        rows.append({
            "draft": int(r.season), "player": r.pfr_player_name, "team": r.team,
            "seasons_100+": len(played),
            "plays": s.plays.sum(),
            "aepa": s.aepa.sum(),
            "war_5yr": s.war.sum(),
            "war_per_season": s.war.sum() / ROOKIE_YEARS,
            "war_per_played": s.war.sum() / len(played) if len(played) else np.nan,
        })
    t = pd.DataFrame(rows).sort_values("war_per_season", ascending=False)
    print(f"first overall quarterbacks drafted 1999-2021, first {ROOKIE_YEARS} "
          f"seasons (the rookie deal plus the option year):")
    print(t.round(2).to_string(index=False))
    print(f"\n  mean   : {t.war_per_season.mean():+.2f} wins above replacement "
          f"per season of the rookie deal")
    print(f"  median : {t.war_per_season.median():+.2f}")
    print(f"  spread : {t.war_per_season.min():+.2f} to {t.war_per_season.max():+.2f}")

    sub("and over their whole careers to date, not just the rookie deal")
    rows2 = []
    for _, r in era[era.position.eq("QB") & era.season.between(1999, 2023)].iterrows():
        s = q[q.pid.eq(r.gsis_id)]
        rows2.append({"draft": int(r.season), "player": r.pfr_player_name,
                      "seasons_100+": (s.plays >= 100).sum(),
                      "plays": s.plays.sum(), "war_total": s.war.sum(),
                      "war_per_seas": s.war.sum() / max((s.plays >= 100).sum(), 1)})
    t2 = pd.DataFrame(rows2).sort_values("war_total", ascending=False)
    print(t2.round(2).to_string(index=False))

    # ------------------------------------------------ the spread, not the mean
    hdr("3. THE SPREAD IS THE WHOLE POINT")
    print("the kicker is a certainty. the pick is a draw from this distribution.")
    print(f"\n  first overall quarterbacks, {ROOKIE_YEARS}-year rookie-deal average:")
    for lab, p in [("best", 1.0), ("75th", 0.75), ("median", 0.5),
                   ("25th", 0.25), ("worst", 0.0)]:
        print(f"    {lab:>6}: {t.war_per_season.quantile(p):+5.2f} wins a season")
    for thr in [0.0, 0.94, 1.14, 2.0, 3.0]:
        print(f"  share clearing {thr:+.2f} wins a season: "
              f"{100 * t.war_per_season.gt(thr).mean():5.1f}%")
    print(f"\n  standard deviation across the {len(t)} of them: "
          f"{t.war_per_season.std():.2f} wins")

    # -------------------------------------------------- the non-quarterbacks
    hdr("4. THE QUARTER OF FIRST PICKS WHO ARE NOT QUARTERBACKS")
    nq = era[~era.position.eq("QB") & era.season.le(2021)]
    qq = era[era.position.eq("QB") & era.season.le(2021)]
    print("play-by-play EPA has no defensive attribution, so a Myles Garrett")
    print("cannot be priced the way a quarterback can. PFR approximate value is")
    print("the only common currency available, and on it the two groups look")
    print("about the same, which is the argument for reading the quarterback")
    print("number as representative of the pick rather than flattering to it:")
    print(f"\n  first picks 1999-2021 who were quarterbacks ({len(qq)}): "
          f"mean weighted AV {qq.w_av.mean():.0f}, median {qq.w_av.median():.0f}")
    print(f"  first picks who were not ({len(nq)}): "
          f"mean weighted AV {nq.w_av.mean():.0f}, median {nq.w_av.median():.0f}")
    print(f"  Pro Bowls per pick: {qq.probowls.mean():.1f} vs {nq.probowls.mean():.1f}")
    print(f"  All-Pros per pick : {qq.allpro.mean():.1f} vs {nq.allpro.mean():.1f}")
    print(f"\n  {nq[['season', 'pfr_player_name', 'position', 'probowls', 'allpro', 'w_av']].to_string(index=False)}")

    # ------------------------------------------------------ how long it lasts
    hdr("5. HOW LONG EACH ASSET LASTS")
    print("the guarantee runs for his entire career. the pick's surplus runs for")
    print("the rookie deal, after which you pay the market for the same player.")
    fg = d[d.field_goal_attempt.eq(1) & d.kicker_player_id.notna()]
    ka = fg.groupby(["kicker_player_id", "season"]).size().rename("att").reset_index()
    ka = ka[ka.att.ge(10)]
    kcar = ka.groupby("kicker_player_id").season.agg(["size", "min", "max"])
    kdone = kcar[kcar["min"].ge(2002) & kcar["max"].le(2022)]
    qa = q[q.plays.ge(100)].groupby("pid").season.agg(["size", "min", "max"])
    qdone = qa[qa["min"].ge(2002) & qa["max"].le(2022)]
    print(f"\n  seasons as a real starter, careers observed start to finish:")
    print(f"    kickers (10+ attempts a year, {len(kdone)} careers): "
          f"median {kdone['size'].median():.0f}, "
          f"75th {kdone['size'].quantile(.75):.0f}, "
          f"90th {kdone['size'].quantile(.90):.0f}, max {kdone['size'].max():.0f}")
    print(f"    quarterbacks (100+ plays a year, {len(qdone)} careers): "
          f"median {qdone['size'].median():.0f}, "
          f"75th {qdone['size'].quantile(.75):.0f}, "
          f"90th {qdone['size'].quantile(.90):.0f}, max {qdone['size'].max():.0f}")
    # conditional on being good: top-quartile career make rate
    rate_by_k = fg[fg.field_goal_result.notna()].assign(
        m=lambda x: x.field_goal_result.eq("made")).groupby("kicker_player_id").m.agg(
        ["size", "mean"])
    good = rate_by_k[(rate_by_k["size"] >= 50)
                     & (rate_by_k["mean"] >= rate_by_k[rate_by_k["size"] >= 50]["mean"]
                        .quantile(0.75))].index
    kg = kdone[kdone.index.isin(good)]
    # matched comparison: condition both groups on being good, not just present
    qrate = q[q.plays.ge(100)].groupby("pid").apply(
        lambda x: pd.Series({"plays": x.plays.sum(),
                             "per": x.aepa.sum() / x.plays.sum()}),
        include_groups=False)
    qelig = qrate[qrate.plays >= 500]
    qgood = qelig[qelig.per >= qelig.per.quantile(0.75)].index
    qg = qdone[qdone.index.isin(qgood)]
    print(f"\n  conditioning both groups on being good, since a leg that never")
    print(f"  misses is never cut and the median of all comers is not the")
    print(f"  relevant number:")
    print(f"    kickers, top quartile of career make rate ({len(kg)} careers): "
          f"median {kg['size'].median():.0f}, "
          f"90th {kg['size'].quantile(.90):.0f}, max {kg['size'].max():.0f}")
    print(f"    quarterbacks, top quartile of career EPA per play ({len(qg)}): "
          f"median {qg['size'].median():.0f}, "
          f"90th {qg['size'].quantile(.90):.0f}, max {qg['size'].max():.0f}")
    print("\n  so the durability edge is real but much smaller than the raw")
    print("  medians suggest: good quarterbacks last a long time too.")

    return dict(rate=rate, t=t, big=big, era=era,
                k_med=kg["size"].median(), k_max=kg["size"].max(),
                q_med=qg["size"].median())


KICKER_VS_AVERAGE = 0.94      # from FINDINGS.txt
KICKER_VS_REPLACEMENT = 1.14

if __name__ == "__main__":
    r = main()
    hdr("6. SIDE BY SIDE")
    t = r["t"]
    print(f"  perfect kicker, vs an average leg     : "
          f"{KICKER_VS_AVERAGE:+.2f} wins a season, guaranteed")
    print(f"  perfect kicker, vs a replacement leg  : "
          f"{KICKER_VS_REPLACEMENT:+.2f} wins a season, guaranteed")
    print(f"  1.01 quarterback, mean of 1999-2021   : "
          f"{t.war_per_season.mean():+.2f} wins a season, on the rookie deal")
    print(f"  1.01 quarterback, median              : "
          f"{t.war_per_season.median():+.2f}")
    print(f"\n  share of 1.01 quarterbacks who beat the kicker over five years: "
          f"{100 * t.war_per_season.gt(KICKER_VS_REPLACEMENT).mean():.0f}%")
    print(f"  over a career: {KICKER_VS_AVERAGE:.2f} x {r['k_med']:.0f} seasons "
          f"for a good kicker = {KICKER_VS_AVERAGE * r['k_med']:.1f} wins,")
    print(f"  against {t.war_per_season.mean():.2f} x {ROOKIE_YEARS} = "
          f"{t.war_per_season.mean() * ROOKIE_YEARS:.1f} wins of rookie-deal surplus")
    print("  from the average 1.01 quarterback. That is the strongest form of the")
    print("  case for the kicker, and it still needs the quarterback's post-rookie")
    print("  seasons to be worth nothing, which they are not - you keep the player")
    print("  and pay him, and he is still better than the alternative.")
