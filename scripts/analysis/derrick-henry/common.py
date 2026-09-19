"""Shared context: attach betting lines to every carry, from the RUSHER's side.

nflverse quotes spread_line from the home team's perspective, so a carry's
"was my team favored" answer flips with posteam_type. Moneylines are American
odds carrying about 4-5 points of vig between them; the pair is normalised so
the two implied probabilities sum to 1 before anything is read off them.
"""
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
HENRY = "00-0032764"          # Derrick Henry, gsis id
MIN_CARRIES = 400             # peer-group floor, 2016-2026 combined


def _implied(american):
    """American odds -> implied probability, vig still in it."""
    a = pd.to_numeric(american, errors="coerce")
    return np.where(a < 0, -a / (-a + 100.0), 100.0 / (a + 100.0))


def load():
    g = pd.read_parquet(f"{HERE}/games.parquet")
    r = pd.read_parquet(f"{HERE}/runs.parquet")

    # De-vig the moneyline pair into a home win probability.
    hi, ai = _implied(g.home_moneyline), _implied(g.away_moneyline)
    tot = hi + ai
    g["home_wp_pre"] = np.where(np.isfinite(tot) & (tot > 0), hi / tot, np.nan)

    cols = ["game_id", "spread_line", "home_wp_pre", "total_line", "roof",
            "div_game", "game_type", "home_team", "away_team", "result"]
    r = r.merge(g[cols], on="game_id", how="left", suffixes=("", "_g"))

    home = r.posteam == r.home_team_g
    # Points the rusher's own team was favoured by. Positive = favoured.
    r["team_spread"] = np.where(home, r.spread_line_g, -r.spread_line_g)
    r["team_wp_pre"] = np.where(home, r.home_wp_pre, 1 - r.home_wp_pre)
    r["margin"] = np.where(home, r.result_g, -r.result_g)

    r["favored"] = np.select(
        [r.team_spread > 0, r.team_spread < 0], ["Favored", "Underdog"], "Pick'em")
    r["tier"] = pd.cut(
        r.team_spread,
        [-99, -7.0, -3.0, -0.5, 0.5, 3.0, 7.0, 99],
        labels=["Dog 7+", "Dog 3.5-6.5", "Dog 1-3", "Pick'em",
                "Fav 1-3", "Fav 3.5-6.5", "Fav 7+"])

    # Game-script state at the snap, independent of the pre-game line.
    r["script"] = pd.cut(
        r.score_differential, [-99, -8.5, -0.5, 0.5, 8.5, 99],
        labels=["Down 9+", "Down 1-8", "Tied", "Up 1-8", "Up 9+"])
    r["wp_bucket"] = pd.cut(
        r.vegas_wp, [0, .2, .4, .6, .8, 1.0],
        labels=["<20%", "20-40%", "40-60%", "60-80%", ">80%"])

    r["explosive_10"] = (r.yards_gained >= 10).astype(float)
    r["explosive_15"] = (r.yards_gained >= 15).astype(float)
    r["stuffed"] = (r.yards_gained <= 0).astype(float)
    return g, r


def rates(df):
    """The per-carry line every table in this study reports."""
    if len(df) == 0:
        return pd.Series(dtype=float)
    return pd.Series({
        "att": len(df),
        "yards": df.yards_gained.sum(),
        "ypc": df.yards_gained.mean(),
        "epa": df.epa.mean(),
        "success": df.success.mean(),
        "td_rate": df.rush_touchdown.mean(),
        "exp10": df.explosive_10.mean(),
        "exp15": df.explosive_15.mean(),
        "stuff": df.stuffed.mean(),
    })


def rb_ids():
    """gsis ids listed as RB or FB. Keeps designed QB runs out of the peer group."""
    p = pd.read_parquet(f"{HERE}/players.parquet")
    return set(p.loc[p.position.isin(["RB", "FB", "HB"]), "gsis_id"])


def wavg(values, weights):
    """Weighted mean that ignores rows where the value is missing."""
    v = pd.to_numeric(values, errors="coerce")
    w = pd.to_numeric(weights, errors="coerce")
    ok = v.notna() & w.notna() & (w > 0)
    return float((v[ok] * w[ok]).sum() / w[ok].sum()) if ok.any() else float("nan")
