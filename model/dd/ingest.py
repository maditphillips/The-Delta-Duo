"""nflverse ingest layer.

Every public dataset we use is a GitHub release asset on nflverse/nflverse-data.
Files are cached under model/.cache so a re-run is free and reproducible.
Nothing here filters by date: the point-in-time discipline lives in
dd/dataset.py, which decides what a model was allowed to know.
"""
from __future__ import annotations

import io
import sys
import urllib.request
from pathlib import Path

import pandas as pd

from .config import CACHE, FIRST_SEASON, FTN_FIRST_SEASON, LAST_COMPLETE_SEASON, TARGET_SEASON

BASE = "https://github.com/nflverse/nflverse-data/releases/download"

# release tag -> filename template ({season} filled per season, or static)
PER_SEASON = {
    "pbp": "pbp/play_by_play_{season}.parquet",
    "stats_player": "stats_player/stats_player_week_{season}.parquet",
    "snap_counts": "snap_counts/snap_counts_{season}.parquet",
    "ftn": "ftn_charting/ftn_charting_{season}.parquet",
    "depth_charts": "depth_charts/depth_charts_{season}.parquet",
    "rosters": "weekly_rosters/roster_weekly_{season}.parquet",
    "injuries": "injuries/injuries_{season}.parquet",
}

STATIC = {
    "schedules": "schedules/games.parquet",
    "players": "players/players.parquet",
    "draft_picks": "draft_picks/draft_picks.parquet",
    "contracts": "contracts/historical_contracts.parquet",
    "ngs_receiving": "nextgen_stats/ngs_receiving.parquet",
    "ngs_rushing": "nextgen_stats/ngs_rushing.parquet",
    "ngs_passing": "nextgen_stats/ngs_passing.parquet",
}


def _download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(url, timeout=300) as r:
        data = r.read()
    tmp.write_bytes(data)
    tmp.rename(dest)
    return dest


def fetch(kind: str, season: int | None = None, refresh: bool = False) -> Path:
    """Return a local path to one nflverse asset, downloading if needed."""
    if season is None:
        rel = STATIC[kind]
        dest = CACHE / kind / Path(rel).name
    else:
        rel = PER_SEASON[kind].format(season=season)
        dest = CACHE / kind / Path(rel).name
    if dest.exists() and not refresh:
        return dest
    return _download(f"{BASE}/{rel}", dest)


def load(kind: str, seasons=None, refresh: bool = False, columns=None) -> pd.DataFrame:
    """Load one dataset, concatenating across seasons where it is per-season."""
    if kind in STATIC:
        df = pd.read_parquet(fetch(kind, refresh=refresh), columns=columns)
        if seasons is not None and "season" in df.columns:
            df = df[df["season"].isin(list(seasons))]
        return df.reset_index(drop=True)

    frames = []
    for s in seasons:
        try:
            frames.append(pd.read_parquet(fetch(kind, s, refresh=refresh), columns=columns))
        except Exception as exc:  # a season the release does not carry yet
            print(f"  ! {kind} {s}: {exc}", file=sys.stderr)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def all_seasons(include_target: bool = True):
    end = TARGET_SEASON if include_target else LAST_COMPLETE_SEASON
    return list(range(FIRST_SEASON, end + 1))


def warm_cache(refresh: bool = False) -> None:
    """Pull everything the pipeline needs, once."""
    hist = list(range(FIRST_SEASON, LAST_COMPLETE_SEASON + 1))
    plans = [
        ("pbp", hist),
        ("stats_player", hist),
        ("snap_counts", hist),
        ("ftn", list(range(FTN_FIRST_SEASON, LAST_COMPLETE_SEASON + 1))),
        ("depth_charts", hist + [TARGET_SEASON]),
        ("rosters", hist + [TARGET_SEASON]),
        ("injuries", hist + [TARGET_SEASON]),
    ]
    for kind, seasons in plans:
        for s in seasons:
            try:
                p = fetch(kind, s, refresh=refresh)
                print(f"  {kind} {s}: {p.stat().st_size/1e6:.1f} MB")
            except Exception as exc:
                print(f"  ! {kind} {s}: {exc}")
    for kind in STATIC:
        try:
            p = fetch(kind, refresh=refresh)
            print(f"  {kind}: {p.stat().st_size/1e6:.1f} MB")
        except Exception as exc:
            print(f"  ! {kind}: {exc}")


if __name__ == "__main__":
    warm_cache(refresh="--refresh" in sys.argv)
