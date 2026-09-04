"""Target quality and drops, from nflverse play-by-play joined to FTN charting.

    python3 fetch_charting.py [first_season] [last_season]

FTN charting starts in 2022, so this covers 2022-2025 only. It answers the one
question the box score cannot: when a receiver's production falls, were the
throws worse or was he worse? Writes charting.parquet (gitignored), one row per
receiver-season-passer.
"""
import os
import subprocess
import sys

import pandas as pd
import pyarrow.parquet as pq

HERE = os.path.dirname(os.path.abspath(__file__))
TMP = os.environ.get("NFLVERSE_TMP", "/tmp/nflverse")
REL = "https://github.com/nflverse/nflverse-data/releases/download"
FTN_FROM = 2022

PBP_COLS = ["season", "week", "season_type", "posteam", "game_id", "play_id",
            "passer_player_name", "passer_player_id", "receiver_player_name",
            "receiver_player_id", "complete_pass", "receiving_yards", "air_yards",
            "pass_touchdown", "epa", "play_type", "sack", "qb_spike"]
FTN_COLS = ["nflverse_game_id", "nflverse_play_id", "is_catchable_ball",
            "is_contested_ball", "is_drop", "is_created_reception",
            "is_screen_pass", "is_play_action", "is_throw_away"]


def download(url, path):
    if os.path.exists(path):
        return path
    if subprocess.run(["curl", "-sSL", "--retry", "4", "--retry-delay", "2",
                       "-o", path, url]).returncode != 0:
        sys.exit(f"download failed: {url}")
    return path


def main(start=FTN_FROM, end=2025):
    os.makedirs(TMP, exist_ok=True)
    frames = []
    for yr in range(max(start, FTN_FROM), end + 1):
        pbp = download(f"{REL}/pbp/play_by_play_{yr}.parquet", f"{TMP}/pbp_{yr}.parquet")
        d = pq.ParquetFile(pbp).read(columns=PBP_COLS).to_pandas()
        d = d[(d.season_type == "REG") & (d.play_type == "pass")
              & (d.sack != 1) & (d.qb_spike != 1) & d.receiver_player_id.notna()]

        ftn = download(f"{REL}/ftn_charting/ftn_charting_{yr}.csv", f"{TMP}/ftn_{yr}.csv")
        f = pd.read_csv(ftn, low_memory=False)
        f = f[[c for c in FTN_COLS if c in f.columns]].rename(
            columns={"nflverse_game_id": "game_id", "nflverse_play_id": "play_id"})
        m = d.merge(f, on=["game_id", "play_id"], how="left")
        # FTN ships these as booleans with nulls, which sum to an object column.
        for c in ("is_catchable_ball", "is_contested_ball", "is_drop",
                  "is_created_reception", "is_screen_pass", "is_play_action"):
            if c in m.columns:
                m[c] = pd.to_numeric(m[c], errors="coerce")

        # One row per receiver-season-passer, so a quarterback change inside a
        # season can be looked at directly rather than averaged away.
        g = m.groupby(["season", "receiver_player_id", "receiver_player_name",
                       "posteam", "passer_player_name"], dropna=False).agg(
            targets=("play_id", "size"),
            rec=("complete_pass", "sum"),
            yards=("receiving_yards", "sum"),
            tds=("pass_touchdown", "sum"),
            epa=("epa", "mean"),
            adot=("air_yards", "mean"),
            catchable=("is_catchable_ball", "mean"),
            contested=("is_contested_ball", "mean"),
            drops=("is_drop", "sum"),
            drop_rate=("is_drop", "mean"),
            created=("is_created_reception", "mean"),
            screen=("is_screen_pass", "mean"),
            charted=("is_catchable_ball", lambda x: x.notna().mean()),
        ).reset_index()
        # Catch rate on balls the charters called catchable: the cleanest split
        # between "the throw was bad" and "he did not come down with it".
        catchable = m[m.is_catchable_ball == 1].groupby(
            ["season", "receiver_player_id", "passer_player_name"], dropna=False
        ).complete_pass.mean().rename("catch_on_catchable").reset_index()
        g = g.merge(catchable, on=["season", "receiver_player_id", "passer_player_name"],
                    how="left")
        frames.append(g)
        os.remove(pbp)
        os.remove(ftn)
        print(yr, len(g), "receiver-passer rows", flush=True)

    out = pd.concat(frames, ignore_index=True)
    out.to_parquet(f"{HERE}/charting.parquet", index=False)
    print(f"\nwrote {len(out):,} rows, {out.season.min()}-{out.season.max()}")


if __name__ == "__main__":
    a = sys.argv[1:]
    main(int(a[0]) if a else FTN_FROM, int(a[1]) if len(a) > 1 else 2025)
