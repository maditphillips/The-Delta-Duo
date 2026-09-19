"""Receiving: the value he produces without the thing modern RB value is built on.

The premise worth testing is not "Henry cannot catch" but how far a back can get
on rushing alone in an era that prices receiving work heavily. Snap share is the
same question from the other end - how much of his offence he is even present for.
Weekly stats carry game_id, so the betting line joins straight on.
"""
import numpy as np
import pandas as pd

import common

pd.set_option("display.width", 215)
pd.set_option("display.max_columns", 40)

g, r = common.load()
w = pd.read_parquet(f"{common.HERE}/weekly.parquet")
w = w[(w.season_type == "REG") & w.player_id.isin(common.rb_ids())].copy()
w = w[(w.carries.fillna(0) + w.targets.fillna(0)) > 0]

for c in ["targets", "receptions", "receiving_yards", "receiving_tds", "carries",
          "rushing_yards", "rushing_tds", "receiving_air_yards",
          "receiving_yards_after_catch", "receiving_first_downs"]:
    w[c] = w[c].fillna(0)

tot = w.groupby("player_id").agg(
    name=("player_display_name", "last"), g=("game_id", "nunique"),
    car=("carries", "sum"), ruyd=("rushing_yards", "sum"), rutd=("rushing_tds", "sum"),
    tgt=("targets", "sum"), rec=("receptions", "sum"),
    reyd=("receiving_yards", "sum"), retd=("receiving_tds", "sum"),
    ay=("receiving_air_yards", "sum"), yac=("receiving_yards_after_catch", "sum"),
    tshare=("target_share", "mean"), ppr=("fantasy_points_ppr", "sum"),
    std=("fantasy_points", "sum"))   # nflverse fantasy_points is STANDARD scoring
peers = tot[tot.car >= common.MIN_CARRIES].copy()
peers["tgt/g"] = peers.tgt / peers.g
peers["rec_yd_share"] = peers.reyd / (peers.reyd + peers.ruyd)
peers["ppr/g"] = peers.ppr / peers.g
# Share of PPR points that come from the passing game (rec + 0.5/rec + TD).
peers["rec_pts"] = peers.reyd * 0.1 + peers.rec * 1.0 + peers.retd * 6
peers["rec_pts_share"] = peers.rec_pts / peers.ppr
peers["half"] = peers["std"] + 0.5 * peers.rec      # half-PPR, built not assumed
H = peers.loc[common.HENRY]

print("=" * 104)
print("RECEIVING WORK")
print("=" * 104)


def rank(series, label, higher_better=True, fmt="{:.2f}"):
    s = series.dropna().sort_values(ascending=not higher_better)
    v = s.loc[common.HENRY]
    pos = list(s.index).index(common.HENRY) + 1
    pct = 100 * (len(s) - pos) / (len(s) - 1)
    lead = peers.name.get(s.index[0], "?")
    print(f"  {label:<40} {fmt.format(v):>8}   rank {pos:>3}/{len(s)}   "
          f"{pct:>5.1f}th pct   (leader: {lead} {fmt.format(s.iloc[0])})")


print(f"\n### Career receiving line, {int(H.g)} games\n")
print(f"  {int(H.tgt)} targets, {int(H.rec)} receptions, {int(H.reyd)} yards, "
      f"{int(H.retd)} TD")
print(f"  {H['tgt/g']:.2f} targets per game; aDOT "
      f"{H.ay / max(H.tgt, 1):.2f}; {H.yac / max(H.rec, 1):.1f} YAC per catch")

print(f"\n### Against {len(peers)} backs with 400+ carries\n")
rank(peers["tgt/g"], "targets per game", higher_better=False)
rank(peers.tshare * 100, "team target share (%)", higher_better=False)
rank(peers.rec / peers.g, "receptions per game", higher_better=False)
rank(peers.rec_yd_share * 100, "% of his yards that are receiving",
     higher_better=False, fmt="{:.1f}")
rank(peers.rec_pts_share * 100, "% of PPR points from the passing game",
     higher_better=False, fmt="{:.1f}")
print()
rank(peers.ppr, "career PPR points", fmt="{:.0f}")
rank(peers["ppr/g"], "PPR points per game")
rank(peers["std"], "career STANDARD points", fmt="{:.0f}")
rank(peers.half, "career HALF-PPR points", fmt="{:.0f}")
rank((peers.ruyd + peers.reyd) / peers.g, "scrimmage yards per game")

print("\n### The trade, laid out: the ten most productive backs of the era\n")
top = peers.nlargest(12, "ppr")[
    ["name", "g", "car", "ruyd", "rutd", "tgt", "rec", "reyd", "retd",
     "ppr", "ppr/g", "rec_pts_share"]].copy()
top["rec_pts_share"] = (top.rec_pts_share * 100).round(1)
top["ppr/g"] = top["ppr/g"].round(1)
top.columns = ["player", "g", "car", "ru yd", "ru td", "tgt", "rec",
               "re yd", "re td", "PPR", "PPR/g", "% PPR receiving"]
print(top.to_string(index=False))

# --- Snap share ---------------------------------------------------------------
sn = pd.read_parquet(f"{common.HERE}/snaps.parquet")
sn = sn[(sn.game_type == "REG") & (sn.position == "RB") & sn.offense_pct.notna()]
key = w[["game_id", "player_display_name", "player_id"]].drop_duplicates()
sn = sn.merge(key, left_on=["game_id", "player"],
              right_on=["game_id", "player_display_name"], how="inner")
sp = sn.groupby("player_id").agg(snap_pct=("offense_pct", "mean"),
                                 gms=("game_id", "nunique"))
sp = sp[sp.index.isin(peers.index) & (sp.gms >= 40)]

print(f"\n### Snap share — what fraction of his offence he was on the field for "
      f"({len(sp)} backs, 40+ games)\n")
j0 = sp.join(peers[["name", "ppr", "ppr/g"]]).dropna()
print(f"  Henry {100*sp.snap_pct.loc[common.HENRY]:.1f}%; "
      f"whole-pool median {100*sp.snap_pct.median():.1f}% — but that pool is mostly "
      f"committee backs,\n  so the honest comparison is against backs of his own "
      f"production tier:")
tier = j0.nlargest(20, "ppr")
print(f"    top-20 backs by career PPR: median snap share "
      f"{100*tier.snap_pct.median():.1f}%, "
      f"Henry {100*sp.snap_pct.loc[common.HENRY]:.1f}% "
      f"(rank {list(tier.snap_pct.sort_values().index).index(common.HENRY)+1}"
      f"/{len(tier)} from the bottom)\n")
j = sp.join(peers[["name", "ppr", "ppr/g", "rec_pts_share"]]).dropna()
print("  the twelve most productive backs, by how often they were on the field:")
print(j.nlargest(12, "ppr")[["name", "snap_pct", "ppr/g", "rec_pts_share"]]
      .assign(snap_pct=lambda d: (100*d.snap_pct).round(1),
              rec_pts_share=lambda d: (100*d.rec_pts_share).round(1),
              **{"ppr/g": lambda d: d["ppr/g"].round(1)})
      .rename(columns={"snap_pct": "snap %", "rec_pts_share": "% PPR receiving"})
      .to_string(index=False))

print("\n### Henry's snap share by season\n")
hs = sn[sn.player_id == common.HENRY].groupby("season").agg(
    g=("game_id", "nunique"), snap_pct=("offense_pct", "mean"))
hs["snap_pct"] = (100 * hs.snap_pct).round(1)
print(hs.to_string())

# --- Does the spread change his receiving usage? ------------------------------
gm = g[g.game_type == "REG"].copy()
long = pd.concat([gm.assign(team=gm.home_team, sp=gm.spread_line),
                  gm.assign(team=gm.away_team, sp=-gm.spread_line)])[
    ["game_id", "team", "sp"]]
hw = w[w.player_id == common.HENRY].merge(long, on=["game_id", "team"], how="left")
hw = hw[hw.sp.notna()]
hw["favored"] = np.where(hw.sp > 0, "Favored", np.where(hw.sp < 0, "Underdog", "Pick'em"))
print("\n### His receiving usage, favoured vs underdog\n")
t = hw[hw.favored != "Pick'em"].groupby("favored").agg(
    games=("game_id", "nunique"), tgt=("targets", "sum"), rec=("receptions", "sum"),
    re_yd=("receiving_yards", "sum"), car=("carries", "sum"),
    ppr=("fantasy_points_ppr", "mean"), half=("fantasy_points", "mean"))
t["tgt/g"] = (t.tgt / t.games).round(2)
t["car/g"] = (t.car / t.games).round(1)
t["PPR/g"] = t.ppr.round(1)
t["half/g"] = t.half.round(1)
print(t[["games", "car/g", "tgt/g", "rec", "re_yd", "PPR/g", "half/g"]].to_string())
