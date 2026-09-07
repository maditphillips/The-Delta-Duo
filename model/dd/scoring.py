"""Fantasy scoring, one function per format.

Only four distinct rule sets exist across the eight published lists: PPR and
half-PPR for RB/WR/TE, and 4-point / 6-point passing touchdowns for QB.
Reception scoring does not move a QB and passing-TD scoring does not move a
skill player, so the eight lists are four computations viewed twice.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import SCORING, Scoring


def _col(df: pd.DataFrame, name: str) -> pd.Series:
    if name in df.columns:
        return df[name].fillna(0).astype(float)
    return pd.Series(0.0, index=df.index)


def fantasy_points(df: pd.DataFrame, scoring: Scoring | str) -> pd.Series:
    """Fantasy points from an nflverse stats_player_week-shaped frame."""
    s = SCORING[scoring] if isinstance(scoring, str) else scoring
    pts = (
        _col(df, "passing_yards") * s.pass_yd
        + _col(df, "passing_tds") * s.pass_td
        + _col(df, "passing_interceptions") * s.interception
        + _col(df, "rushing_yards") * s.rush_yd
        + _col(df, "rushing_tds") * s.rush_td
        + _col(df, "receiving_yards") * s.rec_yd
        + _col(df, "receiving_tds") * s.rec_td
        + _col(df, "receptions") * s.reception
        + (_col(df, "sack_fumbles_lost") + _col(df, "rushing_fumbles_lost")
           + _col(df, "receiving_fumbles_lost")) * s.fumble_lost
        + (_col(df, "passing_2pt_conversions") + _col(df, "rushing_2pt_conversions")
           + _col(df, "receiving_2pt_conversions")) * s.two_pt
    )
    return pts


def points_from_components(comp: dict, scoring: Scoring | str) -> np.ndarray:
    """Fantasy points from simulated component arrays (used by the simulator)."""
    s = SCORING[scoring] if isinstance(scoring, str) else scoring
    z = lambda k: np.asarray(comp.get(k, 0.0), dtype=float)
    return (
        z("passing_yards") * s.pass_yd
        + z("passing_tds") * s.pass_td
        + z("interceptions") * s.interception
        + z("rushing_yards") * s.rush_yd
        + z("rushing_tds") * s.rush_td
        + z("receiving_yards") * s.rec_yd
        + z("receiving_tds") * s.rec_td
        + z("receptions") * s.reception
        + z("fumbles_lost") * s.fumble_lost
    )
