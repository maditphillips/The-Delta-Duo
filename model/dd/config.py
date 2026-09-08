"""Paths, seasons, and scoring formats."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache"
CONFIG = ROOT / "config"
OUTPUTS = ROOT / "outputs"

# The season we are projecting, and the week we are projecting.
TARGET_SEASON = 2026
TARGET_WEEK = 1

# History used to fit everything. 2016 is the first season with reliable
# snap-count coverage in nflverse; FTN charting only exists from 2022.
FIRST_SEASON = 2016
# Scheme fingerprints reach further back than player features: the carryover
# model needs as many coaching changes as it can get, and pbp carries the
# expected-pass model from 2006.
SCHEME_FIRST_SEASON = 2006
LAST_COMPLETE_SEASON = 2025
FTN_FIRST_SEASON = 2022

# Backtest window: week 1 of each of these seasons is a held-out test set.
BACKTEST_SEASONS = tuple(range(2018, LAST_COMPLETE_SEASON + 1))

POSITIONS = ("QB", "RB", "WR", "TE")

# How deep each published list goes.
LIST_DEPTH = {"QB": 36, "RB": 60, "WR": 80, "TE": 36}

# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
# Eight lists ship: RB/WR/TE in PPR and half-PPR, QB at 4-point and 6-point
# passing touchdowns. Reception scoring is irrelevant to QBs and passing-TD
# scoring is irrelevant to skill players, so only four distinct rule sets exist.


class Scoring:
    def __init__(self, name: str, reception: float, pass_td: float):
        self.name = name
        self.reception = reception
        self.pass_td = pass_td

    # Everything below is league-standard and shared across formats.
    pass_yd = 0.04
    interception = -2.0
    rush_yd = 0.1
    rush_td = 6.0
    rec_yd = 0.1
    rec_td = 6.0
    fumble_lost = -2.0
    two_pt = 2.0

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"Scoring({self.name})"


SCORING = {
    "ppr": Scoring("ppr", reception=1.0, pass_td=4.0),
    "half_ppr": Scoring("half_ppr", reception=0.5, pass_td=4.0),
    "qb_4pt": Scoring("qb_4pt", reception=1.0, pass_td=4.0),
    "qb_6pt": Scoring("qb_6pt", reception=1.0, pass_td=6.0),
}

# Which weeks of prior seasons each position may train on.
#
# Quarterback uses weeks 1-6; every other position uses week 1 only. That is a
# judgement call, and the evidence behind it is thin but one-directional: over
# three seeds and five backtest seasons the wider window was never worse for QB
# on a single season, gained +0.40 captured top-12 (p = 0.18) and cut start/sit
# regret from 5.43 to 4.92, which puts QB ahead of expert consensus on both
# lineup metrics for the first time. There is a mechanism for it too -- of the
# four positions a quarterback's role is the most stable week to week, so
# mid-season rows resemble week 1 more closely than they do at receiver, which
# is where the wider window did the most damage. It is still a choice made
# partly on backtest evidence, so it is recorded here rather than buried.
TRAIN_WEEKS = {"QB": tuple(range(1, 7)), "RB": (1,), "WR": (1,), "TE": (1,)}

# Which formats each position publishes.
LISTS = {
    "QB": ("qb_4pt", "qb_6pt"),
    "RB": ("ppr", "half_ppr"),
    "WR": ("ppr", "half_ppr"),
    "TE": ("ppr", "half_ppr"),
}

# Team abbreviation drift in nflverse sources.
TEAM_FIXES = {"OAK": "LV", "SD": "LAC", "STL": "LA", "LAR": "LA"}


def fix_team(s):
    return s.replace(TEAM_FIXES)


for _p in (CACHE, OUTPUTS, CONFIG):
    _p.mkdir(parents=True, exist_ok=True)
