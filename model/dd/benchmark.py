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
