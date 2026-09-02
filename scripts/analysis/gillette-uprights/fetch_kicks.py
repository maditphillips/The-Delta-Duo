"""Download nflverse play-by-play (2002-2025) and keep only kicking plays.

Writes kicks_2002_2025.parquet next to this script (gitignored - ~4 MB).
Each season's full pbp file is downloaded, filtered, then deleted, so peak
disk use stays around 25 MB.
"""
import os, subprocess, sys
import pandas as pd
import pyarrow.parquet as pq

WANT = ['game_id','season','season_type','week','home_team','away_team','posteam','defteam',
        'stadium','game_stadium','stadium_id','roof','surface','wind','temp','weather',
        'field_goal_attempt','field_goal_result','extra_point_attempt','extra_point_result',
        'kick_distance','kicker_player_name','kicker_player_id','result','home_score','away_score',
        'qtr','game_seconds_remaining','score_differential','wp','desc']

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kicks_2002_2025.parquet")
TMP = os.environ.get("NFLVERSE_TMP", "/tmp/nflverse")


def main(start=2002, end=2025):
    os.makedirs(TMP, exist_ok=True)
    frames = []
    for yr in range(start, end + 1):
        path = f"{TMP}/pbp_{yr}.parquet"
        if not os.path.exists(path):
            url = ("https://github.com/nflverse/nflverse-data/releases/download/"
                   f"pbp/play_by_play_{yr}.parquet")
            if subprocess.run(["curl", "-sSL", "--retry", "4", "--retry-delay", "2",
                               "-o", path, url]).returncode != 0:
                sys.exit(f"download failed for {yr}")
        pf = pq.ParquetFile(path)
        df = pf.read(columns=[c for c in WANT if c in pf.schema_arrow.names]).to_pandas()
        df = df[(df.field_goal_attempt == 1) | (df.extra_point_attempt == 1)].copy()
        for c in WANT:
            if c not in df.columns:
                df[c] = pd.NA
        frames.append(df[WANT])
        os.remove(path)
        print(yr, len(df), flush=True)
    pd.concat(frames, ignore_index=True).to_parquet(OUT, index=False)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
