"""Build one row per rookie RB: first-3-game metrics, full-rookie-season metrics,
draft capital, and career outcomes. Writes rbs.csv.

Run fetch.sh first (weekly stats, players, snap counts) and fetch_pbp.py (success rate).
"""
import glob
import numpy as np
import pandas as pd

LAST_FULL = 2025  # last completed season; 2026 is in progress

# ---------- weekly box scores, regular season only ----------
wk = pd.concat(
    (pd.read_csv(f, low_memory=False, usecols=[
        "player_id", "player_display_name", "position", "position_group", "season", "week",
        "season_type", "game_id", "team", "carries", "rushing_yards", "rushing_tds",
        "rushing_first_downs", "rushing_epa", "rushing_fumbles_lost", "receptions", "targets",
        "receiving_yards", "receiving_tds", "receiving_first_downs", "receiving_epa",
        "fantasy_points_ppr"])
     for f in sorted(glob.glob("data/stats_player_week_*.csv"))),
    ignore_index=True)
wk = wk[wk.season_type == "REG"].copy()
num = ["carries", "rushing_yards", "rushing_tds", "rushing_first_downs", "rushing_epa",
       "rushing_fumbles_lost", "receptions", "targets", "receiving_yards", "receiving_tds",
       "receiving_first_downs", "receiving_epa", "fantasy_points_ppr"]
wk[num] = wk[num].fillna(0)

# team totals per game, for carry share and target share
team = wk.groupby(["game_id", "team"])[["carries", "targets", "receptions"]].sum().rename(
    columns={"carries": "team_carries", "targets": "team_targets", "receptions": "team_rec"})
wk = wk.join(team, on=["game_id", "team"])

# ---------- play-by-play success rate per player-game ----------
pbp = pd.concat((pd.read_parquet(f) for f in sorted(glob.glob("data/pbp/pbp_*.parquet"))),
                ignore_index=True)
pbp = pbp[pbp.season_type == "REG"]
ru = pbp[(pbp.rush_attempt == 1) & pbp.rusher_player_id.notna()]
ru = ru.groupby(["game_id", "rusher_player_id"]).agg(rush_succ=("success", "sum"),
                                                     rush_n=("success", "size"))
ru.index.names = ["game_id", "player_id"]
re_ = pbp[(pbp.pass_attempt == 1) & pbp.receiver_player_id.notna()]
re_ = re_.groupby(["game_id", "receiver_player_id"]).agg(rec_succ=("success", "sum"),
                                                         rec_n=("success", "size"))
re_.index.names = ["game_id", "player_id"]
wk = wk.join(ru, on=["game_id", "player_id"]).join(re_, on=["game_id", "player_id"])
wk[["rush_succ", "rush_n", "rec_succ", "rec_n"]] = wk[["rush_succ", "rush_n", "rec_succ", "rec_n"]].fillna(0)

# ---------- snap share (2013+), matched via pfr id ----------
players = pd.read_csv("data/players.csv", low_memory=False)
snaps = pd.concat((pd.read_csv(f) for f in sorted(glob.glob("data/snap_counts_*.csv"))
                   if sum(1 for _ in open(f)) > 1), ignore_index=True)
snaps = snaps[snaps.game_type == "REG"][["game_id", "pfr_player_id", "offense_snaps", "offense_pct"]]
idmap = players[["gsis_id", "pfr_id"]].dropna().rename(columns={"gsis_id": "player_id",
                                                                "pfr_id": "pfr_player_id"})
snaps = snaps.merge(idmap, on="pfr_player_id").drop(columns="pfr_player_id")
snaps = snaps.drop_duplicates(["game_id", "player_id"])
wk = wk.merge(snaps, on=["game_id", "player_id"], how="left")

wk = wk.sort_values(["player_id", "season", "week"])

# ---------- who is a rookie RB ----------
first_season = wk.groupby("player_id").season.min().rename("rookie_year")
wk = wk.join(first_season, on="player_id")
info = players.set_index("gsis_id")[["position", "rookie_season", "draft_year", "draft_pick",
                                     "draft_round", "birth_date"]]
info = info[~info.index.duplicated()]
rk = wk[wk.season == wk.rookie_year]
rb_share = rk.assign(is_rb=rk.position == "RB").groupby("player_id").is_rb.mean()
cand = rb_share[rb_share >= 0.5].index
cand = [p for p in cand if p in info.index and info.loc[p, "position"] == "RB"]
# players.csv carries the current position, so converts (e.g. a WR moved to RB later)
# look like RBs. Drop anyone the draft table lists at another position.
dp = pd.read_csv("data/draft_picks.csv").dropna(subset=["gsis_id"]).drop_duplicates("gsis_id")
drafted_as = dp.set_index("gsis_id").position
cand = [p for p in cand if drafted_as.get(p, "RB") in ("RB", "FB")]
wk = wk[wk.player_id.isin(cand)]
# 1999 is the first season of data, so a 1999 "debut" may be a veteran. Start at 2000,
# and drop anyone players.csv says debuted earlier than their first box-score season.
ri = info.loc[cand]
ok = [p for p in cand
      if first_season[p] >= 2000
      # a back drafted the year before his debut (injured rookie year) is still a rookie
      and not (pd.notna(ri.loc[p, "rookie_season"]) and ri.loc[p, "rookie_season"] < first_season[p]
               and ri.loc[p, "draft_year"] != first_season[p] - 1)
      and not (pd.notna(ri.loc[p, "draft_year"]) and ri.loc[p, "draft_year"] < first_season[p] - 1)]
wk = wk[wk.player_id.isin(ok)].copy()

# season PPR rank among all RBs (for top-12 / top-24 seasons)
allwk = pd.concat((pd.read_csv(f, low_memory=False, usecols=["player_id", "position", "season",
                                                              "season_type", "fantasy_points_ppr"])
                   for f in sorted(glob.glob("data/stats_player_week_*.csv"))), ignore_index=True)
allwk = allwk[(allwk.season_type == "REG") & (allwk.position == "RB")]
seas = allwk.groupby(["season", "player_id"]).fantasy_points_ppr.sum().reset_index()
seas["rank"] = seas.groupby("season").fantasy_points_ppr.rank(ascending=False, method="first")
rank = seas.set_index(["player_id", "season"])["rank"]


def agg(g):
    """Rate stats over a set of games."""
    c, t = g.carries.sum(), g.targets.sum()
    n = len(g)
    # nflverse has no incompletion targets for 2003-2008 (receiver is blank on
    # incomplete passes), so target-based rates are only defined outside those years
    if g.season.between(2003, 2008).any():
        t = np.nan
    s = g.offense_pct.dropna()
    return {
        "games": n,
        "carries_pg": c / n,
        "targets_pg": t / n,
        "rec_pg": g.receptions.sum() / n,
        "touches_pg": (c + g.receptions.sum()) / n,
        "carry_share": c / g.team_carries.sum() if g.team_carries.sum() else np.nan,
        "target_share": t / g.team_targets.sum() if g.team_targets.sum() else np.nan,
        "rec_share": g.receptions.sum() / g.team_rec.sum() if g.team_rec.sum() else np.nan,
        "snap_share": s.mean() if len(s) == n else np.nan,
        "ypc": g.rushing_yards.sum() / c if c else np.nan,
        "rush_epa_pc": g.rushing_epa.sum() / c if c else np.nan,
        "rush_sr": g.rush_succ.sum() / g.rush_n.sum() if g.rush_n.sum() else np.nan,
        "rush_1d_rate": g.rushing_first_downs.sum() / c if c else np.nan,
        "yds_per_tgt": g.receiving_yards.sum() / t if t else np.nan,
        "rec_epa_pt": g.receiving_epa.sum() / t if t else np.nan,
        "scrim_ypg": (g.rushing_yards.sum() + g.receiving_yards.sum()) / n,
        "ppr_pg": g.fantasy_points_ppr.sum() / n,
        "carries": c,
        "targets": t,
    }


rows = []
for pid, g in wk.groupby("player_id", sort=False):
    ry = int(g.rookie_year.iloc[0])
    rook = g[g.season == ry]
    if len(rook) < 3:
        continue
    first3, rest_rook = rook.iloc[:3], rook.iloc[3:]
    after = g.iloc[3:]
    y2 = g[(g.season > ry) & (g.season <= LAST_FULL)]
    d = {"player_id": pid, "name": g.player_display_name.iloc[-1], "rookie_year": ry,
         "team": rook.team.iloc[0], "rookie_games": len(rook)}
    i = info.loc[pid]
    # a drafted back who missed his rookie year still counts as drafted
    d["draft_pick"] = i.draft_pick if pd.notna(i.draft_pick) and i.draft_year in (ry, ry - 1) else np.nan
    d["draft_round"] = i.draft_round if pd.notna(d["draft_pick"]) else np.nan
    # supplemental-draft picks carry a meaningless pick number (Tony Hollings: round 2,
    # "pick 1"); place them mid-round
    if pd.notna(d["draft_round"]) and d["draft_pick"] < 32 * (d["draft_round"] - 1) - 4:
        d["draft_pick"] = 32 * (d["draft_round"] - 1) + 16
    d["undrafted"] = int(pd.isna(d["draft_pick"]))
    bd = pd.to_datetime(i.birth_date, errors="coerce")
    d["age"] = (pd.Timestamp(f"{ry}-09-01") - bd).days / 365.25 if pd.notna(bd) else np.nan
    d.update({f"f3_{k}": v for k, v in agg(first3).items()})
    d.update({f"rk_{k}": v for k, v in agg(rook).items()})
    # outcomes
    d["career_ppr_after3"] = after.fantasy_points_ppr.sum()
    d["career_games_after3"] = len(after)
    d["y2_ppr"] = y2.fantasy_points_ppr.sum()
    d["y2_games"] = len(y2)
    d["y2_seasons"] = y2.season.nunique()
    yrs = range(ry + 1, LAST_FULL + 1)
    rks = [rank.get((pid, y), np.inf) for y in yrs]
    d["y2_top24"] = sum(r <= 24 for r in rks)
    d["y2_top12"] = sum(r <= 12 for r in rks)
    d["rookie_top24"] = int(rank.get((pid, ry), np.inf) <= 24)
    a = agg(after) if len(after) else {}
    for k in ["ypc", "rush_epa_pc", "rush_sr", "carries_pg", "carry_share", "targets_pg", "rec_pg",
              "target_share", "yds_per_tgt", "ppr_pg", "carries", "targets"]:
        d[f"after_{k}"] = a.get(k, np.nan)
    rows.append(d)

df = pd.DataFrame(rows)
df.to_csv("rbs.csv", index=False)
print(f"{len(df)} rookie RBs with 3+ rookie-year games, {df.rookie_year.min()}-{df.rookie_year.max()}")
print(df.groupby(df.rookie_year >= 2021).size())
