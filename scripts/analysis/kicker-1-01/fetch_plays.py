"""Download nflverse play-by-play and keep the columns this study needs.

Every play is kept (the expected-points baselines need first- and second-down
states, and the ensuing-kickoff cost of a made field goal only exists on the
kickoff play), but only ~70 of the 372 columns.

Writes plays_<start>_<end>.parquet next to this script (gitignored).
Each season file is downloaded, filtered, then deleted, so peak disk stays low.
"""
import os
import subprocess
import sys

import pandas as pd
import pyarrow.parquet as pq

WANT = [
    "game_id", "season", "season_type", "week", "home_team", "away_team",
    "posteam", "defteam", "posteam_type", "roof", "surface", "wind", "temp",
    "down", "ydstogo", "yardline_100", "qtr", "quarter_seconds_remaining",
    "half_seconds_remaining", "game_seconds_remaining", "goal_to_go",
    "play_type", "desc", "special_teams_play",
    "field_goal_attempt", "field_goal_result", "kick_distance",
    "extra_point_attempt", "extra_point_result",
    "two_point_attempt", "two_point_conv_result",
    "punt_attempt", "punt_blocked", "kickoff_attempt",
    "fourth_down_converted", "fourth_down_failed",
    "touchdown", "safety", "interception", "fumble_lost", "penalty",
    "ep", "epa", "wp", "wpa", "vegas_wp", "vegas_wpa", "def_wp",
    "score_differential", "score_differential_post",
    "posteam_score", "defteam_score", "total_home_score", "total_away_score",
    "home_score", "away_score", "result", "spread_line", "total_line",
    "posteam_timeouts_remaining", "defteam_timeouts_remaining",
    "kicker_player_name", "kicker_player_id",
    "passer_player_id", "passer_player_name", "rusher_player_id",
    "rusher_player_name", "pass", "rush", "qb_dropback", "sack", "qb_epa",
    "fixed_drive", "fixed_drive_result", "drive_end_transition",
    "series_result", "play_id", "aborted_play",
]

HERE = os.path.dirname(os.path.abspath(__file__))
TMP = os.environ.get("NFLVERSE_TMP", "/tmp/nflverse")


def main(start=2010, end=2025):
    os.makedirs(TMP, exist_ok=True)
    out = os.path.join(HERE, f"plays_{start}_{end}.parquet")
    frames = []
    for yr in range(start, end + 1):
        path = f"{TMP}/pbp_{yr}.parquet"
        if not os.path.exists(path):
            url = ("https://github.com/nflverse/nflverse-data/releases/download/"
                   f"pbp/play_by_play_{yr}.parquet")
            rc = subprocess.run(["curl", "-sSL", "--retry", "4", "--retry-delay", "2",
                                 "-o", path, url]).returncode
            if rc != 0:
                sys.exit(f"download failed for {yr}")
        pf = pq.ParquetFile(path)
        have = [c for c in WANT if c in pf.schema_arrow.names]
        df = pf.read(columns=have).to_pandas()
        for c in WANT:
            if c not in df.columns:
                df[c] = pd.NA
        frames.append(df[WANT])
        os.remove(path)
        print(yr, len(df), flush=True)
    pd.concat(frames, ignore_index=True).to_parquet(out, index=False)
    print("wrote", out)


if __name__ == "__main__":
    a = [int(x) for x in sys.argv[1:]]
    main(*a) if a else main()
