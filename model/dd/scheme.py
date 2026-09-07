"""Scheme fingerprints.

A "type of offense" or "type of defense" is not a label here, it is a vector.
Labels ("Shanahan tree", "Air Raid", "Fangio shell") do not regress and cannot
be blended; a vector of measured tendencies can be attached to a person,
carried to a new team, and shrunk toward the league mean by sample size.

Each function returns one row per team-season.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import ingest
from .config import FTN_FIRST_SEASON

PBP_COLS = [
    "game_id", "season", "week", "season_type", "posteam", "defteam", "play_id",
    "play_type", "pass", "rush", "qb_dropback", "qb_scramble", "shotgun", "no_huddle",
    "air_yards", "yardline_100", "down", "ydstogo", "goal_to_go", "half_seconds_remaining",
    "game_seconds_remaining", "score_differential", "wp", "xpass", "pass_oe", "qtr",
    "epa", "success", "sack", "complete_pass", "touchdown", "pass_touchdown",
    "rush_touchdown", "interception", "penalty", "aborted_play", "special",
    "passer_player_id", "rusher_player_id", "receiver_player_id",
    "drive", "series", "yards_gained", "qb_hit", "play_deleted", "time",
]

FTN_COLS = [
    "season", "week", "nflverse_game_id", "nflverse_play_id", "is_no_huddle", "is_motion",
    "is_play_action", "is_screen_pass", "is_rpo", "n_offense_backfield", "n_defense_box",
    "n_blitzers", "n_pass_rushers",
]

# Offensive dimensions in fingerprint order. Anything a play-caller controls.
OFF_DIMS = [
    "plays_per_game", "sec_per_play", "proe", "neutral_pass_rate", "early_down_pass_rate",
    "shotgun_rate", "no_huddle_rate", "adot", "deep_rate", "short_rate",
    "rb_target_share", "te_target_share", "wr_target_share",
    "rz_pass_rate", "gl_rush_rate", "qb_designed_run_rate", "sack_rate",
    "pa_rate", "motion_rate", "screen_rate", "rpo_rate", "heavy_backfield_rate",
]

DEF_DIMS = [
    "def_epa_pass", "def_epa_rush", "def_pass_funnel", "def_success_rate",
    "def_plays_per_game", "def_sec_per_play", "def_sack_rate", "def_adot_allowed",
    "def_comp_pct_allowed", "def_ypa_allowed", "def_ypc_allowed", "def_rz_td_rate",
    "def_light_box_rate", "def_blitz_rate",
]

# FTN-only dimensions: unavailable before 2022, so they are always allowed to be NaN.
FTN_OFF_DIMS = ["pa_rate", "motion_rate", "screen_rate", "rpo_rate", "heavy_backfield_rate"]
FTN_DEF_DIMS = ["def_light_box_rate", "def_blitz_rate"]


def load_pbp(seasons) -> pd.DataFrame:
    p = ingest.load("pbp", seasons, columns=PBP_COLS)
    p = p[(p["season_type"] == "REG")]
    p = p[(p["play_deleted"] != 1) & (p["special"] != 1) & (p["aborted_play"] != 1)]
    p = p[p["play_type"].isin(["pass", "run"])]
    return p


def load_ftn(seasons) -> pd.DataFrame:
    seasons = [s for s in seasons if s >= FTN_FIRST_SEASON]
    if not seasons:
        return pd.DataFrame(columns=FTN_COLS)
    return ingest.load("ftn", seasons, columns=FTN_COLS)


def _neutral(p: pd.DataFrame) -> pd.Series:
    """Neutral game script: competitive win prob, before garbage time."""
    return (p["wp"].between(0.20, 0.80)) & (p["qtr"] <= 3) & (p["half_seconds_remaining"] > 120)


def _sec_per_play(p: pd.DataFrame, team_col: str) -> pd.Series:
    """Seconds of game clock burned per snap in neutral situations."""
    q = p[_neutral(p)].copy()
    q = q.sort_values(["game_id", "play_id"])
    q["gap"] = q.groupby(["game_id"])["game_seconds_remaining"].diff(-1)
    q = q[(q["gap"] > 0) & (q["gap"] < 60)]
    return q.groupby(["season", team_col])["gap"].median()


def offense_fingerprint(pbp: pd.DataFrame, ftn: pd.DataFrame, stats: pd.DataFrame) -> pd.DataFrame:
    p = pbp.copy()
    p["is_pass"] = p["pass"].fillna(0)
    p["is_rush"] = p["rush"].fillna(0)
    neutral = _neutral(p)
    games = p.groupby(["season", "posteam"])["game_id"].nunique().rename("games")

    g = p.groupby(["season", "posteam"])
    out = pd.DataFrame(index=g.size().index)
    out["plays"] = g.size()
    out["games"] = games
    out["plays_per_game"] = out["plays"] / out["games"]
    out["shotgun_rate"] = g["shotgun"].mean()
    out["no_huddle_rate"] = g["no_huddle"].mean()
    out["sack_rate"] = g["sack"].mean()

    # PROE: nflverse's own expected-pass model, averaged where it is defined.
    xp = p[p["xpass"].notna()]
    out["proe"] = xp.groupby(["season", "posteam"])["pass_oe"].mean() / 100.0

    n = p[neutral]
    out["neutral_pass_rate"] = n.groupby(["season", "posteam"])["is_pass"].mean()
    ed = n[n["down"].isin([1, 2])]
    out["early_down_pass_rate"] = ed.groupby(["season", "posteam"])["is_pass"].mean()
    out["sec_per_play"] = _sec_per_play(p, "posteam")

    # Aggressiveness through the air.
    ay = p[p["air_yards"].notna()]
    out["adot"] = ay.groupby(["season", "posteam"])["air_yards"].mean()
    ay = ay.assign(deep=(ay["air_yards"] >= 20).astype(float), short=(ay["air_yards"] <= 5).astype(float))
    out["deep_rate"] = ay.groupby(["season", "posteam"])["deep"].mean()
    out["short_rate"] = ay.groupby(["season", "posteam"])["short"].mean()

    # Scoring-position tendency: who gets fed inside the 20 and inside the 5.
    rz = p[p["yardline_100"] <= 20]
    out["rz_pass_rate"] = rz.groupby(["season", "posteam"])["is_pass"].mean()
    gl = p[p["yardline_100"] <= 5]
    out["gl_rush_rate"] = gl.groupby(["season", "posteam"])["is_rush"].mean()

    # Designed QB runs, scrambles excluded -- a real play-caller fingerprint.
    qb_runs = p[(p["is_rush"] == 1) & (p["qb_scramble"] != 1) & (p["rusher_player_id"].notna())]
    qb_ids = set(p.loc[p["passer_player_id"].notna()].groupby(["season", "posteam"])["passer_player_id"].agg(
        lambda s: s.value_counts().idxmax()).values)
    qb_runs = qb_runs[qb_runs["rusher_player_id"].isin(qb_ids)]
    out["qb_designed_runs"] = qb_runs.groupby(["season", "posteam"]).size()
    out["qb_designed_run_rate"] = (out["qb_designed_runs"].fillna(0) / out["plays"])

    # Where the targets go by position group. From weekly stats, not pbp joins.
    tgt = stats[stats["position"].isin(["RB", "WR", "TE", "FB"])].copy()
    tgt["position"] = tgt["position"].replace({"FB": "RB"})
    tsum = tgt.groupby(["season", "team", "position"])["targets"].sum().unstack(fill_value=0)
    tsum = tsum.div(tsum.sum(axis=1), axis=0)
    tsum.index.names = ["season", "posteam"]
    for pos in ("RB", "WR", "TE"):
        col = f"{pos.lower()}_target_share"
        out[col] = tsum[pos] if pos in tsum.columns else np.nan

    # FTN charting layer (2022+).
    if len(ftn):
        f = ftn.merge(
            p[["game_id", "play_id", "posteam", "is_pass"]],
            left_on=["nflverse_game_id", "nflverse_play_id"],
            right_on=["game_id", "play_id"], how="inner")
        fg = f.groupby(["season", "posteam"])
        out["motion_rate"] = fg["is_motion"].mean()
        out["rpo_rate"] = fg["is_rpo"].mean()
        out["heavy_backfield_rate"] = fg["n_offense_backfield"].apply(lambda s: (s >= 2).mean())
        fp = f[f["is_pass"] == 1].groupby(["season", "posteam"])
        out["pa_rate"] = fp["is_play_action"].mean()
        out["screen_rate"] = fp["is_screen_pass"].mean()
    for c in FTN_OFF_DIMS:
        if c not in out.columns:
            out[c] = np.nan

    out = out.reset_index().rename(columns={"posteam": "team"})
    return out[["season", "team", "games", "plays"] + OFF_DIMS]


def defense_fingerprint(pbp: pd.DataFrame, ftn: pd.DataFrame) -> pd.DataFrame:
    p = pbp.copy()
    p["is_pass"] = p["pass"].fillna(0)
    p["is_rush"] = p["rush"].fillna(0)
    g = p.groupby(["season", "defteam"])
    out = pd.DataFrame(index=g.size().index)
    out["def_plays"] = g.size()
    out["def_games"] = g["game_id"].nunique()
    out["def_plays_per_game"] = out["def_plays"] / out["def_games"]
    out["def_success_rate"] = g["success"].mean()
    out["def_sack_rate"] = g["sack"].mean()
    out["def_sec_per_play"] = _sec_per_play(p, "defteam")

    pa = p[p["is_pass"] == 1]
    ru = p[p["is_rush"] == 1]
    out["def_epa_pass"] = pa.groupby(["season", "defteam"])["epa"].mean()
    out["def_epa_rush"] = ru.groupby(["season", "defteam"])["epa"].mean()
    out["def_pass_funnel"] = out["def_epa_pass"] - out["def_epa_rush"]
    out["def_adot_allowed"] = pa.groupby(["season", "defteam"])["air_yards"].mean()
    att = pa[pa["sack"] != 1]
    out["def_comp_pct_allowed"] = att.groupby(["season", "defteam"])["complete_pass"].mean()
    out["def_ypa_allowed"] = att.groupby(["season", "defteam"])["yards_gained"].mean()
    out["def_ypc_allowed"] = ru.groupby(["season", "defteam"])["yards_gained"].mean()
    rz = p[p["yardline_100"] <= 20]
    out["def_rz_td_rate"] = rz.groupby(["season", "defteam"])["touchdown"].mean()

    if len(ftn):
        f = ftn.merge(
            p[["game_id", "play_id", "defteam", "is_pass"]],
            left_on=["nflverse_game_id", "nflverse_play_id"],
            right_on=["game_id", "play_id"], how="inner")
        fg = f.groupby(["season", "defteam"])
        out["def_light_box_rate"] = fg["n_defense_box"].apply(lambda s: (s <= 6).mean())
        fp = f[f["is_pass"] == 1].groupby(["season", "defteam"])
        out["def_blitz_rate"] = fp["n_blitzers"].apply(lambda s: (s >= 1).mean())
    for c in FTN_DEF_DIMS:
        if c not in out.columns:
            out[c] = np.nan

    out = out.reset_index().rename(columns={"defteam": "team"})
    return out[["season", "team", "def_games", "def_plays"] + DEF_DIMS]


def positional_points_allowed(stats: pd.DataFrame, scoring) -> pd.DataFrame:
    """Fantasy points a defense allowed per game to each position group."""
    from .scoring import fantasy_points
    s = stats[stats["position"].isin(["QB", "RB", "WR", "TE", "FB"])].copy()
    s["position"] = s["position"].replace({"FB": "RB"})
    s["fp"] = fantasy_points(s, scoring)
    per_game = s.groupby(["season", "opponent_team", "position", "week"])["fp"].sum().reset_index()
    agg = per_game.groupby(["season", "opponent_team", "position"])["fp"].mean().unstack()
    agg.columns = [f"def_fp_allowed_{c.lower()}" for c in agg.columns]
    agg.index.names = ["season", "team"]
    return agg.reset_index()


def build(seasons) -> dict:
    pbp = load_pbp(seasons)
    ftn = load_ftn(seasons)
    stats = ingest.load("stats_player", seasons)
    stats = stats[stats["season_type"] == "REG"]
    return {
        "offense": offense_fingerprint(pbp, ftn, stats),
        "defense": defense_fingerprint(pbp, ftn),
    }
