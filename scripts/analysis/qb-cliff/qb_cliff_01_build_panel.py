"""Rebuild the QB season panel (obj_qb_season) from nflverse play-by-play.

Stands in for the missing R scripts 01a-01d. For every quarterback season
2008-2025 it computes starts, kneel-excluded rushing split into designed runs
and scrambles, EPA per dropback, ANY/A, fantasy points and the league-wide
fantasy rank, then joins draft round/pick for the 212 QBs drafted 2008-2025.

Writes cache/qb_season.parquet.

  python3 qb_cliff_01_build_panel.py
"""
import os
import subprocess
import sys

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from qb_cliff_00_setup import CONFIG, NFLVERSE

PBP_COLS = [
    "game_id", "season", "season_type", "week", "posteam",
    "passer_id", "passer_player_name", "rusher_player_id", "rusher_player_name",
    "qb_dropback", "qb_kneel", "qb_spike", "qb_scramble",
    "pass_attempt", "rush_attempt", "complete_pass", "interception", "sack",
    "passing_yards", "rushing_yards", "yards_gained",
    "pass_touchdown", "rush_touchdown", "epa",
    "fumble_lost", "fumbled_1_player_id",
    "two_point_attempt", "two_point_conv_result", "td_player_id",
]


def download(url, path):
    if os.path.exists(path):
        return path
    rc = subprocess.run(
        ["curl", "-sSL", "--retry", "4", "--retry-delay", "2", "-o", path, url]
    ).returncode
    if rc != 0:
        sys.exit(f"download failed: {url}")
    return path


def load_pbp(year):
    path = os.path.join(CONFIG["tmp_dir"], f"pbp_{year}.parquet")
    download(f"{NFLVERSE}/pbp/play_by_play_{year}.parquet", path)
    pf = pq.ParquetFile(path)
    cols = [c for c in PBP_COLS if c in pf.schema_arrow.names]
    df = pf.read(columns=cols).to_pandas()
    for c in PBP_COLS:
        if c not in df.columns:
            df[c] = np.nan
    return df[df.season_type == "REG"].copy()


def season_frame(year):
    d = load_pbp(year)
    for c in ("qb_dropback", "qb_kneel", "qb_spike", "qb_scramble", "pass_attempt",
              "rush_attempt", "complete_pass", "interception", "sack",
              "pass_touchdown", "rush_touchdown", "fumble_lost", "two_point_attempt"):
        d[c] = pd.to_numeric(d[c], errors="coerce").fillna(0)
    for c in ("passing_yards", "rushing_yards", "yards_gained", "epa"):
        d[c] = pd.to_numeric(d[c], errors="coerce")

    live = d[(d.qb_kneel == 0) & (d.qb_spike == 0)]

    # --- passing side, attributed to passer_id (filled for sacks and scrambles)
    p = live[live.qb_dropback == 1].copy()
    p["is_pass_att"] = p.pass_attempt
    p["sack_yards"] = np.where(p.sack == 1, -p.yards_gained.fillna(0), 0.0)
    passing = p.groupby(["season", "passer_id"]).agg(
        dropbacks=("qb_dropback", "sum"),
        att=("is_pass_att", "sum"),
        cmp=("complete_pass", "sum"),
        pass_yd=("passing_yards", "sum"),
        pass_td=("pass_touchdown", "sum"),
        ints=("interception", "sum"),
        sacks=("sack", "sum"),
        sack_yd=("sack_yards", "sum"),
        epa_sum=("epa", "sum"),
        epa_n=("epa", "count"),
        pass_name=("passer_player_name", "last"),
    ).reset_index().rename(columns={"passer_id": "qb_id"})

    # --- rushing side, kneels already excluded; split designed vs scramble
    r = live[(live.rush_attempt == 1) & live.rusher_player_id.notna()].copy()
    r["designed_yd"] = np.where(r.qb_scramble == 0, r.rushing_yards.fillna(0), 0.0)
    r["scramble_yd"] = np.where(r.qb_scramble == 1, r.rushing_yards.fillna(0), 0.0)
    r["designed_att"] = (r.qb_scramble == 0).astype(float)
    r["scramble_att"] = (r.qb_scramble == 1).astype(float)
    rushing = r.groupby(["season", "rusher_player_id"]).agg(
        rush_att=("rush_attempt", "sum"),
        rush_yd=("rushing_yards", "sum"),
        designed_yd=("designed_yd", "sum"),
        scramble_yd=("scramble_yd", "sum"),
        designed_att=("designed_att", "sum"),
        scramble_att=("scramble_att", "sum"),
        rush_td=("rush_touchdown", "sum"),
        rush_name=("rusher_player_name", "last"),
    ).reset_index().rename(columns={"rusher_player_id": "qb_id"})

    # --- fumbles lost charged to the player who fumbled
    f = d[(d.fumble_lost == 1) & d.fumbled_1_player_id.notna()]
    fum = f.groupby(["season", "fumbled_1_player_id"]).size().reset_index(name="fum_lost")
    fum = fum.rename(columns={"fumbled_1_player_id": "qb_id"})

    # --- two point conversions (passing and rushing), scored 2 each
    tp = d[(d.two_point_attempt == 1) & (d.two_point_conv_result == "success")]
    tp_pass = tp.groupby(["season", "passer_id"]).size().reset_index(name="tp_pass")
    tp_pass = tp_pass.rename(columns={"passer_id": "qb_id"})
    tp_rush = tp.groupby(["season", "rusher_player_id"]).size().reset_index(name="tp_rush")
    tp_rush = tp_rush.rename(columns={"rusher_player_id": "qb_id"})

    # --- starts: the passer with the most dropbacks for his team in that game
    g = p.groupby(["season", "game_id", "posteam", "passer_id"]).size().reset_index(name="db")
    g = g.sort_values("db", ascending=False).drop_duplicates(["season", "game_id", "posteam"])
    starts = g.groupby(["season", "passer_id"]).size().reset_index(name="starts")
    starts = starts.rename(columns={"passer_id": "qb_id"})

    # --- games played: any dropback or rush attempt
    gp = pd.concat([
        p[["season", "game_id", "passer_id"]].rename(columns={"passer_id": "qb_id"}),
        r[["season", "game_id", "rusher_player_id"]].rename(columns={"rusher_player_id": "qb_id"}),
    ]).dropna().drop_duplicates()
    gp = gp.groupby(["season", "qb_id"]).size().reset_index(name="games")

    out = passing
    for extra in (rushing, fum, tp_pass, tp_rush, starts, gp):
        out = out.merge(extra, on=["season", "qb_id"], how="outer")
    num = [c for c in out.columns if c not in ("season", "qb_id", "pass_name", "rush_name")]
    out[num] = out[num].fillna(0)
    return out


def main():
    frames = []
    for yr in range(CONFIG["season_first"], CONFIG["season_last"] + 1):
        frames.append(season_frame(yr))
        path = os.path.join(CONFIG["tmp_dir"], f"pbp_{yr}.parquet")
        if os.path.exists(path):
            os.remove(path)
        print(f"  {yr} done", flush=True)
    s = pd.concat(frames, ignore_index=True)

    # ---- identify quarterbacks and attach names
    players = pd.read_parquet(
        download(f"{NFLVERSE}/players/players.parquet",
                 os.path.join(CONFIG["tmp_dir"], "players.parquet"))
    )[["gsis_id", "display_name", "position"]].rename(columns={"gsis_id": "qb_id"})
    s = s.merge(players, on="qb_id", how="left")
    s["player_name"] = s.display_name.fillna(s.pass_name).fillna(s.rush_name)
    s = s[(s.position == "QB") | (s.position.isna() & (s.dropbacks >= 50))].copy()

    # ---- fantasy points, standard scoring
    s["fp"] = (s.pass_yd / 25 + 4 * s.pass_td - 2 * s.ints
               + s.rush_yd / 10 + 6 * s.rush_td
               - 2 * s.fum_lost + 2 * (s.tp_pass + s.tp_rush))

    # ---- league-wide fantasy rank among quarterbacks, by total points
    s["qb_rank"] = s.groupby("season").fp.rank(ascending=False, method="min").astype(int)
    s["is_qb1"] = s.qb_rank <= CONFIG["qb1_rank"]
    s["is_sfx"] = s.qb_rank <= CONFIG["sfx_rank"]

    # ---- per game and per dropback rates
    g = s.games.replace(0, np.nan)
    s["fp_per_game"] = s.fp / g
    s["rush_yd_pg"] = s.rush_yd / g
    s["designed_yd_pg"] = s.designed_yd / g
    s["scramble_yd_pg"] = s.scramble_yd / g
    s["att_pg"] = s.att / g
    s["epa_per_db"] = s.epa_sum / s.epa_n.replace(0, np.nan)
    s["any_a"] = ((s.pass_yd - s.sack_yd + 20 * s.pass_td - 45 * s.ints)
                  / (s.att + s.sacks).replace(0, np.nan))

    # ---- draft join, the 212 QBs drafted 2008-2025
    dp = pd.read_parquet(
        download(f"{NFLVERSE}/draft_picks/draft_picks.parquet",
                 os.path.join(CONFIG["tmp_dir"], "draft_picks.parquet"))
    )
    # every drafted QB, so pre-2008 picks still show a round and pick; the
    # 2008-2025 study population is flagged separately by in_study_pop
    dp = dp[(dp.position == "QB") & dp.gsis_id.notna()]
    dp = dp[["gsis_id", "season", "round", "pick"]].rename(
        columns={"gsis_id": "qb_id", "season": "draft_season"})
    dp["draft_day"] = np.where(dp["round"] == 1, "Round 1",
                        np.where(dp["round"].isin([2, 3]), "Day 2", "Day 3"))

    s = s.merge(dp, on="qb_id", how="left")
    s["drafted"] = s.draft_season.notna()
    s["in_study_pop"] = s.draft_season.between(CONFIG["draft_first"], CONFIG["draft_last"])
    for c in ("starts", "games", "dropbacks", "att", "cmp", "sacks", "rush_att"):
        s[c] = s[c].round().astype(int)
    for c in ("draft_season", "round", "pick"):
        s[c] = s[c].astype("Int64")

    keep = ["qb_id", "player_name", "season", "draft_season", "round", "pick", "draft_day",
            "drafted", "in_study_pop", "starts", "games", "dropbacks", "att", "cmp", "pass_yd", "pass_td",
            "ints", "sacks", "sack_yd", "rush_att", "rush_yd", "designed_yd", "scramble_yd",
            "designed_att", "scramble_att", "rush_td", "fum_lost", "epa_per_db", "any_a",
            "att_pg", "rush_yd_pg", "designed_yd_pg", "scramble_yd_pg",
            "fp", "fp_per_game", "qb_rank", "is_qb1", "is_sfx"]
    s = s[keep].sort_values(["season", "qb_rank"])

    out = os.path.join(CONFIG["cache_dir"], "qb_season.parquet")
    s.to_parquet(out, index=False)
    print(f"\nwrote {out}: {len(s)} QB seasons, {s.qb_id.nunique()} quarterbacks")

    panel = s[s.in_study_pop & (s.starts >= CONFIG["start_bar_season"])]
    print(f"study population (drafted 2008-2025) with {CONFIG['start_bar_season']}+ starts: "
          f"{len(panel)} starter seasons, {panel.qb_id.nunique()} quarterbacks")


if __name__ == "__main__":
    main()
