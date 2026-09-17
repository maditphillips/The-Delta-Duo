"""The benchmark the model has to beat: human consensus.

DynastyProcess mirrors FantasyPros' expert-consensus rankings history, which is
the closest public stand-in for what a well-informed manager believes going into
week 1. Absolute accuracy in week 1 is poor for everyone; the only number worth
reporting is the margin over this.

Preseason positional consensus (redraft-qb/rb/wr/te) covers 2021 onward,
including the current season. Weekly consensus exists too but is only densely
scraped for a couple of seasons, so preseason is the primary benchmark.
"""
from __future__ import annotations

import urllib.request

import numpy as np
import pandas as pd

from .config import CACHE

ECR_URL = "https://raw.githubusercontent.com/dynastyprocess/data/master/files/db_fpecr.parquet"
IDS_URL = "https://raw.githubusercontent.com/dynastyprocess/data/master/files/db_playerids.csv"

PAGES = {"QB": "redraft-qb", "RB": "redraft-rb", "WR": "redraft-wr", "TE": "redraft-te"}
WEEKLY_PAGES = {"QB": "weekly-qb", "RB": "weekly-rb", "WR": "weekly-wr", "TE": "weekly-te"}


def _cached(url: str, name: str):
    dest = CACHE / "benchmark" / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        with urllib.request.urlopen(url, timeout=600) as r:
            dest.write_bytes(r.read())
    return dest


def crosswalk() -> pd.DataFrame:
    p = pd.read_csv(_cached(IDS_URL, "db_playerids.csv"), low_memory=False)
    p = p[["fantasypros_id", "gsis_id", "merge_name", "position"]].dropna(subset=["gsis_id"])
    p["fantasypros_id"] = pd.to_numeric(p["fantasypros_id"], errors="coerce")
    return p


def _load_ecr(pages) -> pd.DataFrame:
    cols = ["page_type", "player", "pos", "team", "ecr", "sd", "best", "worst",
            "id", "mergename", "scrape_date"]
    d = pd.read_parquet(_cached(ECR_URL, "db_fpecr.parquet"), columns=cols)
    d = d[d["page_type"].isin(pages)].copy()
    d["scrape_date"] = pd.to_datetime(d["scrape_date"])
    d["id"] = pd.to_numeric(d["id"], errors="coerce")
    return d


def preseason_consensus(season: int, cutoff: str | None = None) -> pd.DataFrame:
    """Latest preseason positional consensus published before week 1.

    `cutoff` defaults to Sept 10 of that season, which is before or on the
    first Sunday in every year covered.
    """
    d = _load_ecr(set(PAGES.values()))
    cut = pd.Timestamp(cutoff) if cutoff else pd.Timestamp(f"{season}-09-10")
    win = d[(d["scrape_date"] <= cut) & (d["scrape_date"] >= pd.Timestamp(f"{season}-08-01"))]
    if win.empty:
        return pd.DataFrame(columns=["season", "player_id", "position", "consensus_rank",
                                     "consensus_sd"])
    out = []
    for pos, page in PAGES.items():
        sub = win[win["page_type"] == page]
        if sub.empty:
            continue
        sub = sub[sub["scrape_date"] == sub["scrape_date"].max()].copy()
        sub["position"] = pos
        out.append(sub)
    if not out:
        return pd.DataFrame(columns=["season", "player_id", "position", "consensus_rank",
                                     "consensus_sd"])
    df = pd.concat(out, ignore_index=True)
    xw = crosswalk()
    df = df.merge(xw[["fantasypros_id", "gsis_id"]], left_on="id",
                  right_on="fantasypros_id", how="left")
    miss = df["gsis_id"].isna()
    if miss.any():  # fall back to normalised-name join
        xw2 = xw.dropna(subset=["merge_name"]).drop_duplicates(["merge_name", "position"])
        df.loc[miss, "gsis_id"] = df.loc[miss].merge(
            xw2, left_on=["mergename", "position"], right_on=["merge_name", "position"],
            how="left")["gsis_id_y"].values
    df["season"] = season
    df["consensus_rank"] = df.groupby("position")["ecr"].rank(method="first")
    return (df.dropna(subset=["gsis_id"])
              .rename(columns={"gsis_id": "player_id", "sd": "consensus_sd"})
              [["season", "player_id", "position", "consensus_rank", "consensus_sd", "ecr"]]
              .drop_duplicates(["season", "player_id"]))


def weekly_consensus(season: int, week: int) -> pd.DataFrame:
    """Expert consensus for one week, as it stood going into that week.

    The weekly pages are scraped once a week, midweek, so the right snapshot
    is the last one published strictly before that week's first kickoff. Early
    in a week the scrape has not happened yet; rather than return nothing, the
    most recent weekly snapshot is used and `scraped` says which, so a caller
    can tell a current board from a carried-over one and re-run when the real
    thing lands.
    """
    from . import ingest
    d = _load_ecr(set(WEEKLY_PAGES.values()))
    if d.empty:
        return pd.DataFrame(columns=["season", "week", "player_id", "position",
                                     "consensus_rank", "consensus_sd", "scraped"])
    sched = ingest.load("schedules")
    g = sched[(sched.season == season) & (sched.week == week)]
    if g.empty:
        raise SystemExit(f"no schedule for {season} week {week}")
    # The weekly pages are scraped on the Friday INSIDE the week they rank,
    # after Thursday night and before the Sunday slate. Selecting on the first
    # kickoff therefore rejects a week's own board and reaches back to the
    # previous one: asking for 2026 week 1 returned a scrape from December
    # 2025, and asking for week 2 returned week 1's. The window is the week
    # itself, from the day after the previous week's last game to this week's
    # last.
    last = pd.Timestamp(pd.to_datetime(g.gameday).max())
    prev = sched[(sched.season == season) & (sched.week == week - 1)]
    floor = (pd.Timestamp(pd.to_datetime(prev.gameday).max()) if len(prev)
             else pd.Timestamp(pd.to_datetime(g.gameday).min()) - pd.Timedelta(days=7))
    window = d[(d.scrape_date > floor) & (d.scrape_date <= last)]
    # A week with no scrape yet falls back to whatever the market last said,
    # which is stale by one week and says so through `scraped`.
    pick = window if not window.empty else d[d.scrape_date <= last]
    out = []
    for pos, page in WEEKLY_PAGES.items():
        sub = pick[pick.page_type == page]
        if sub.empty:
            continue
        sub = sub[sub.scrape_date == sub.scrape_date.max()].copy()
        sub["position"] = pos
        out.append(sub)
    if not out:
        return pd.DataFrame(columns=["season", "week", "player_id", "position",
                                     "consensus_rank", "consensus_sd", "scraped"])
    df = pd.concat(out, ignore_index=True)
    xw = crosswalk()
    df = df.merge(xw[["fantasypros_id", "gsis_id"]], left_on="id",
                  right_on="fantasypros_id", how="left")
    miss = df["gsis_id"].isna()
    if miss.any():
        xw2 = xw.dropna(subset=["merge_name"]).drop_duplicates(["merge_name", "position"])
        df.loc[miss, "gsis_id"] = df.loc[miss].merge(
            xw2, left_on=["mergename", "position"], right_on=["merge_name", "position"],
            how="left")["gsis_id_y"].values
    df["season"], df["week"] = season, week
    df["scraped"] = df.scrape_date.dt.strftime("%Y-%m-%d")
    df["consensus_rank"] = df.groupby("position")["ecr"].rank(method="first")
    return (df.dropna(subset=["gsis_id"])
              .rename(columns={"gsis_id": "player_id", "sd": "consensus_sd"})
              [["season", "week", "player_id", "position", "consensus_rank",
                "consensus_sd", "ecr", "scraped"]]
              .drop_duplicates(["season", "week", "player_id"]))
