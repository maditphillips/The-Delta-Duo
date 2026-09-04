"""Download nflverse weekly player stats and build the wide receiver panel.

    python3 fetch.py [first_season] [last_season]

Writes five gitignored files next to this script:

  wr_weeks.parquet   every regular-season WR game line, 2000-2025
  team_games.parquet season/team/week grid, so "games missed" is measured
                     against the games the player's team actually played
  players.parquet    rookie year, birth date and draft slot per player
  injuries.parquet   weekly injury report, 2009-2025 - what he was listed with,
                     his game status and his practice participation
  snaps.parquet      offensive snap share by game, 2012-2025

Each season's weekly file is downloaded, filtered, then deleted, so peak disk
use stays under 100 MB.
"""
import os
import subprocess
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
TMP = os.environ.get("NFLVERSE_TMP", "/tmp/nflverse")
REL = "https://github.com/nflverse/nflverse-data/releases/download"

WEEK_COLS = [
    "player_id", "player_name", "player_display_name", "position", "position_group",
    "season", "week", "season_type", "game_id", "team", "opponent_team",
    "receptions", "targets", "receiving_yards", "receiving_tds",
    "receiving_air_yards", "receiving_yards_after_catch", "receiving_first_downs",
    "receiving_epa", "receiving_20", "receiving_40", "racr", "target_share",
    "air_yards_share", "wopr", "carries", "rushing_yards", "rushing_tds",
    "fantasy_points", "fantasy_points_ppr",
]
INJURY_COLS = [
    "season", "season_type", "team", "week", "gsis_id", "position", "full_name",
    "report_primary_injury", "report_status", "practice_primary_injury", "practice_status",
]
SNAP_COLS = ["season", "week", "player", "pfr_player_id", "position", "team",
             "offense_snaps", "offense_pct"]
ROSTER_COLS = [
    "season", "gsis_id", "full_name", "position", "birth_date", "draft_number",
    "entry_year", "rookie_year", "years_exp",
]


def download(url, path):
    if os.path.exists(path):
        return path
    ok = subprocess.run(
        ["curl", "-sSL", "--retry", "4", "--retry-delay", "2", "-o", path, url]
    ).returncode
    if ok != 0:
        sys.exit(f"download failed: {url}")
    return path


def main(start=2000, end=2025):
    os.makedirs(TMP, exist_ok=True)
    weeks, team_games, rosters = [], [], []

    for yr in range(start, end + 1):
        path = download(f"{REL}/stats_player/stats_player_week_{yr}.csv", f"{TMP}/w_{yr}.csv")
        df = pd.read_csv(path, low_memory=False)
        df = df[df.season_type == "REG"]

        # Team-week grid from every position, before we filter down to receivers.
        team_games.append(
            df[["season", "team", "week", "game_id"]].drop_duplicates(["season", "team", "week"])
        )

        wr = df[df.position == "WR"].copy()
        for c in WEEK_COLS:
            if c not in wr.columns:
                wr[c] = pd.NA
        weeks.append(wr[WEEK_COLS])
        os.remove(path)

        rpath = download(f"{REL}/rosters/roster_{yr}.csv", f"{TMP}/r_{yr}.csv")
        r = pd.read_csv(rpath, low_memory=False)
        for c in ROSTER_COLS:
            if c not in r.columns:
                r[c] = pd.NA
        rosters.append(r[ROSTER_COLS])
        os.remove(rpath)
        print(yr, len(wr), "WR game lines", flush=True)

    wk = pd.concat(weeks, ignore_index=True)
    wk.to_parquet(f"{HERE}/wr_weeks.parquet", index=False)

    tg = pd.concat(team_games, ignore_index=True)
    tg.to_parquet(f"{HERE}/team_games.parquet", index=False)

    # Injury reports (2009+) and snap counts (2012+). Both are only needed for
    # the "was he playing hurt" question, so a missing season is not fatal.
    inj, snaps = [], []
    for yr in range(max(start, 2009), end + 1):
        try:
            ipath = download(f"{REL}/injuries/injuries_{yr}.csv", f"{TMP}/i_{yr}.csv")
            i = pd.read_csv(ipath, low_memory=False)
            inj.append(i[[c for c in INJURY_COLS if c in i.columns]])
            os.remove(ipath)
        except SystemExit:
            print(f"  no injury report for {yr}", flush=True)
        if yr >= 2012:
            try:
                spath = download(f"{REL}/snap_counts/snap_counts_{yr}.csv", f"{TMP}/s_{yr}.csv")
                sn = pd.read_csv(spath, low_memory=False)
                sn = sn[sn.game_type == "REG"] if "game_type" in sn.columns else sn
                snaps.append(sn[[c for c in SNAP_COLS if c in sn.columns]])
                os.remove(spath)
            except SystemExit:
                print(f"  no snap counts for {yr}", flush=True)
    if inj:
        pd.concat(inj, ignore_index=True).to_parquet(f"{HERE}/injuries.parquet", index=False)
    if snaps:
        pd.concat(snaps, ignore_index=True).to_parquet(f"{HERE}/snaps.parquet", index=False)

    ros = pd.concat(rosters, ignore_index=True)
    ros = ros[ros.gsis_id.notna()]
    # One row per player: earliest roster season wins for the static fields.
    ros = ros.sort_values("season")
    first_seen = ros.groupby("gsis_id").season.min().rename("first_roster_season")
    players = ros.groupby("gsis_id").agg(
        full_name=("full_name", "last"),
        birth_date=("birth_date", "first"),
        draft_number=("draft_number", "first"),
        entry_year=("entry_year", "first"),
        rookie_year=("rookie_year", "first"),
    ).join(first_seen).reset_index()

    dpath = download(f"{REL}/draft_picks/draft_picks.csv", f"{TMP}/draft_picks.csv")
    draft = pd.read_csv(dpath, low_memory=False)
    draft = draft[draft.gsis_id.notna()][["gsis_id", "season", "round", "pick"]]
    draft = draft.rename(columns={"season": "draft_season", "round": "draft_round", "pick": "draft_pick"})
    players = players.merge(draft.drop_duplicates("gsis_id"), on="gsis_id", how="left")
    players.to_parquet(f"{HERE}/players.parquet", index=False)

    print(f"\nwrote {len(wk):,} WR game lines, {wk.player_id.nunique():,} receivers, "
          f"{wk.season.min()}-{wk.season.max()}")


if __name__ == "__main__":
    a = sys.argv[1:]
    main(int(a[0]) if a else 2000, int(a[1]) if len(a) > 1 else 2025)
