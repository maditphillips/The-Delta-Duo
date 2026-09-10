"""Download the nflverse data this study needs and cache it next to this script.

Writes (all gitignored):
  player_week.parquet   weekly offensive player stats, 1999-present
  snaps.parquet         weekly snap counts, 2012-present
  team_week.parquet     weekly team stats (for team EPA), 1999-present
  games.csv             one row per game, 1999-present (scores, spreads)

Re-run it any time; files already on disk are reused unless --refresh is passed.
"""
import os, subprocess, sys
import pandas as pd
import pyarrow.parquet as pq

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "https://github.com/nflverse/nflverse-data/releases/download"
GAMES = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
TMP = os.environ.get("NFLVERSE_TMP", "/tmp/nflverse")

FIRST, LAST = 1999, 2026

PLAYER_COLS = [
    'player_id','player_display_name','position','position_group','season','week','season_type',
    'team','opponent_team','games',
    'completions','attempts','passing_yards','passing_tds','passing_interceptions',
    'sacks_suffered','passing_air_yards','passing_epa','passing_cpoe','passing_first_downs',
    'carries','rushing_yards','rushing_tds','rushing_fumbles_lost','rushing_epa','rushing_first_downs',
    'receptions','targets','receiving_yards','receiving_tds','receiving_air_yards','receiving_epa',
    'receiving_first_downs','target_share','air_yards_share','wopr','racr',
    'fantasy_points','fantasy_points_ppr',
]
TEAM_COLS = [
    'season','week','team','season_type','game_id','opponent_team',
    'attempts','carries','sacks_suffered','passing_yards','rushing_yards',
    'passing_epa','rushing_epa','passing_cpoe','passing_interceptions','rushing_fumbles_lost',
]
SNAP_COLS = ['game_id','season','game_type','week','player','pfr_player_id','position','team',
             'offense_snaps','offense_pct']
# Next Gen rushing carries rush yards over expected, which adjusts a carry for the
# blocking and box count in front of it. One file, all seasons, 2016 on.
NGS_URL = f"{BASE}/nextgen_stats/ngs_rushing.parquet"
NGS_COLS = ['season','season_type','week','player_gsis_id','player_display_name',
            'player_position','team_abbr','rush_attempts','efficiency','avg_time_to_los',
            'percent_attempts_gte_eight_defenders','expected_rush_yards',
            'rush_yards_over_expected','rush_yards_over_expected_per_att',
            'rush_pct_over_expected']


def grab(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return True
    r = subprocess.run(["curl", "-sSL", "--retry", "4", "--retry-delay", "2",
                        "--fail", "-o", path, url])
    if r.returncode != 0:
        if os.path.exists(path):
            os.remove(path)
        return False
    return True


def stack(tag, stem, cols, first, last, out):
    """Download one file per season, keep `cols`, concat, write `out`."""
    frames = []
    for yr in range(first, last + 1):
        path = f"{TMP}/{stem}_{yr}.parquet"
        if not grab(f"{BASE}/{tag}/{stem}_{yr}.parquet", path):
            print(f"  {yr}: not published, skipping", flush=True)
            continue
        pf = pq.ParquetFile(path)
        have = [c for c in cols if c in pf.schema_arrow.names]
        df = pf.read(columns=have).to_pandas()
        for c in cols:
            if c not in df.columns:
                df[c] = pd.NA
        frames.append(df[cols])
        print(f"  {yr}: {len(df):>6} rows", flush=True)
    if not frames:
        sys.exit(f"nothing downloaded for {tag}")
    out_path = os.path.join(HERE, out)
    pd.concat(frames, ignore_index=True).to_parquet(out_path, index=False)
    print("wrote", out_path, flush=True)


def main():
    os.makedirs(TMP, exist_ok=True)
    if "--refresh" in sys.argv:
        for f in os.listdir(TMP):
            os.remove(os.path.join(TMP, f))

    print("player week stats")
    stack("stats_player", "stats_player_week", PLAYER_COLS, FIRST, LAST, "player_week.parquet")
    print("team week stats")
    stack("stats_team", "stats_team_week", TEAM_COLS, FIRST, LAST, "team_week.parquet")
    print("snap counts")
    stack("snap_counts", "snap_counts", SNAP_COLS, 2012, LAST, "snaps.parquet")

    print("next gen rushing")
    npath = os.path.join(HERE, "ngs_rushing.parquet")
    if not os.path.exists(npath):
        tmpn = f"{TMP}/ngs_rushing.parquet"
        if not grab(NGS_URL, tmpn):
            sys.exit("ngs_rushing download failed")
        n = pq.ParquetFile(tmpn).read().to_pandas()
        n[[c for c in NGS_COLS if c in n.columns]].to_parquet(npath, index=False)
    print("wrote", npath)

    print("player id crosswalk")
    ppath = os.path.join(HERE, "players.parquet")
    if not os.path.exists(ppath):
        tmpp = f"{TMP}/players.parquet"
        if not grab(f"{BASE}/players/players.parquet", tmpp):
            sys.exit("players.parquet download failed")
        cw = pq.ParquetFile(tmpp).read().to_pandas()
        keep = [c for c in ['gsis_id','pfr_id','display_name','position','rookie_season',
                            'draft_year','draft_round','draft_pick','draft_team']
                if c in cw.columns]
        cw[keep].to_parquet(ppath, index=False)
    print("wrote", ppath)

    print("games")
    gpath = os.path.join(HERE, "games.csv")
    if not grab(GAMES, gpath):
        sys.exit("games.csv download failed")
    print("wrote", gpath, len(pd.read_csv(gpath)), "games")


if __name__ == "__main__":
    main()
