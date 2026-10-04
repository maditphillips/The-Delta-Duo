"""Pull nflverse play-by-play one season at a time and keep only the columns needed
for RB rushing/receiving success rate. Raw season files are deleted after slimming."""
import os, sys, urllib.request
import pandas as pd

B = "https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{y}.parquet"
COLS = ["game_id", "season", "week", "season_type", "posteam", "play_type",
        "rusher_player_id", "receiver_player_id", "rush_attempt", "pass_attempt",
        "success", "epa", "yards_gained", "two_point_attempt"]
os.makedirs("data/pbp", exist_ok=True)
for y in range(int(sys.argv[1]), int(sys.argv[2]) + 1):
    out = f"data/pbp/pbp_{y}.parquet"
    if os.path.exists(out):
        continue
    tmp = f"data/pbp/raw_{y}.parquet"
    urllib.request.urlretrieve(B.format(y=y), tmp)
    d = pd.read_parquet(tmp, columns=COLS)
    d = d[(d.two_point_attempt != 1) & (d.rusher_player_id.notna() | d.receiver_player_id.notna())]
    d.drop(columns="two_point_attempt").to_parquet(out)
    os.remove(tmp)
    print(y, len(d), flush=True)
