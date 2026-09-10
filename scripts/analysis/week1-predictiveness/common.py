"""Shared panel construction and statistics for the Week 1 predictiveness study.

The unit of analysis is a player-season. For each one we build three views of the
same metric:

  w1     the Week 1 value
  ros    the rest-of-season value (weeks 2+), per game for volume, pooled for rates
  prior  the player's previous regular season, per game / pooled

Everything downstream compares those three, so that "how predictive is Week 1" is
always answered against a baseline (what we already knew in August) rather than
against zero.
"""
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
FIRST_SEASON = 1999
LAST_SEASON = 2025          # last complete season
SNAP_FIRST = 2013           # snap counts begin here in nflverse


# ---------------------------------------------------------------- loading

def load_weekly(with_snaps=True):
    p = pd.read_parquet(os.path.join(HERE, "player_week.parquet"))
    p = p[(p.season_type == "REG") & (p.season >= FIRST_SEASON) & (p.season <= LAST_SEASON)].copy()
    p = p[p.position.isin(["QB", "RB", "WR", "TE", "FB"])].copy()
    p.loc[p.position == "FB", "position"] = "RB"
    num = [c for c in p.columns if c not in
           ("player_id", "player_display_name", "position", "position_group",
            "season_type", "team", "opponent_team")]
    for c in num:
        p[c] = pd.to_numeric(p[c], errors="coerce")
    p[[c for c in num if c not in ("season", "week")]] = \
        p[[c for c in num if c not in ("season", "week")]].fillna(0.0)

    # half-PPR is not shipped; PPR minus half a point per catch
    p["fantasy_points_half"] = p.fantasy_points_ppr - 0.5 * p.receptions
    p["touches"] = p.carries + p.receptions
    p["opportunities"] = p.carries + p.targets

    # team rush attempts, so an RB's carry share is comparable across paces
    t = pd.read_parquet(os.path.join(HERE, "team_week.parquet"))
    t = t[t.season_type == "REG"][["season", "week", "team", "carries", "attempts"]]
    t = t.rename(columns={"carries": "team_carries", "attempts": "team_attempts"})
    p = p.merge(t, on=["season", "week", "team"], how="left")
    p["rush_share"] = np.where(p.team_carries > 0, p.carries / p.team_carries, np.nan)
    for c in ("target_share", "air_yards_share", "wopr", "racr"):
        p[c] = p[c].replace([np.inf, -np.inf], np.nan)

    if with_snaps:
        s = pd.read_parquet(os.path.join(HERE, "snaps.parquet"))
        s = s[(s.game_type == "REG") & (s.offense_snaps.notna())]
        cw = pd.read_parquet(os.path.join(HERE, "players.parquet"))
        cw = cw[cw.pfr_id.notna()][["gsis_id", "pfr_id"]].drop_duplicates("pfr_id")
        s = s.merge(cw, left_on="pfr_player_id", right_on="pfr_id", how="left")
        s = s[s.gsis_id.notna()][["season", "week", "gsis_id", "offense_snaps", "offense_pct"]]
        s = s.rename(columns={"gsis_id": "player_id", "offense_pct": "snap_pct"})
        s = s.drop_duplicates(["season", "week", "player_id"])
        p = p.merge(s, on=["season", "week", "player_id"], how="left")
    else:
        p["offense_snaps"] = np.nan
        p["snap_pct"] = np.nan
    return p


def load_games():
    g = pd.read_csv(os.path.join(HERE, "games.csv"))
    return g[(g.season >= FIRST_SEASON) & (g.season <= LAST_SEASON)].copy()


# ------------------------------------------------------- metric definitions
# ("name", numerator, denominator or None). denominator None => per-game mean.
VOLUME = {
    "QB": [("pass_attempts", "attempts"), ("passing_yards", "passing_yards"),
           ("pass_tds", "passing_tds"), ("qb_carries", "carries"),
           ("fantasy_ppg", "fantasy_points_ppr")],
    "RB": [("carries", "carries"), ("rushing_yards", "rushing_yards"),
           ("targets", "targets"), ("receptions", "receptions"),
           ("touches", "touches"), ("opportunities", "opportunities"),
           ("rushing_tds", "rushing_tds"),
           ("fantasy_ppg_ppr", "fantasy_points_ppr"),
           ("fantasy_ppg_half", "fantasy_points_half")],
    "WR": [("targets", "targets"), ("receptions", "receptions"),
           ("receiving_yards", "receiving_yards"), ("air_yards", "receiving_air_yards"),
           ("receiving_tds", "receiving_tds"),
           ("fantasy_ppg_ppr", "fantasy_points_ppr"),
           ("fantasy_ppg_half", "fantasy_points_half")],
    "TE": [("targets", "targets"), ("receptions", "receptions"),
           ("receiving_yards", "receiving_yards"), ("air_yards", "receiving_air_yards"),
           ("fantasy_ppg_ppr", "fantasy_points_ppr"),
           ("fantasy_ppg_half", "fantasy_points_half")],
}
# share metrics are already per-play fractions; average them over games
SHARE = {
    "QB": [],
    "RB": [("snap_pct", "snap_pct"), ("rush_share", "rush_share"),
           ("target_share", "target_share")],
    "WR": [("snap_pct", "snap_pct"), ("target_share", "target_share"),
           ("air_yards_share", "air_yards_share"), ("wopr", "wopr")],
    "TE": [("snap_pct", "snap_pct"), ("target_share", "target_share"),
           ("air_yards_share", "air_yards_share")],
}
# rates are pooled: sum(numerator) / sum(denominator)
RATE = {
    "QB": [("completion_pct", "completions", "attempts"),
           ("yards_per_attempt", "passing_yards", "attempts"),
           ("cpoe", "_cpoe_wt", "attempts"),
           ("epa_per_pass", "passing_epa", "attempts"),
           ("pass_td_rate", "passing_tds", "attempts"),
           ("int_rate", "passing_interceptions", "attempts")],
    "RB": [("yards_per_carry", "rushing_yards", "carries"),
           ("yards_per_touch", "_rb_yards", "touches"),
           ("epa_per_carry", "rushing_epa", "carries"),
           ("rush_fd_rate", "rushing_first_downs", "carries")],
    "WR": [("yards_per_target", "receiving_yards", "targets"),
           ("catch_rate", "receptions", "targets"),
           ("yards_per_catch", "receiving_yards", "receptions"),
           ("adot", "receiving_air_yards", "targets"),
           ("epa_per_target", "receiving_epa", "targets")],
    "TE": [("yards_per_target", "receiving_yards", "targets"),
           ("catch_rate", "receptions", "targets"),
           ("adot", "receiving_air_yards", "targets")],
}
# Week 1 role required to enter the sample, and the ROS denominator a rate needs
W1_GATE = {"QB": ("attempts", 20), "RB": ("carries", 6),
           "WR": ("targets", 3), "TE": ("targets", 2)}
RATE_MIN_DEN = {"QB": 100, "RB": 40, "WR": 25, "TE": 20}
MIN_ROS_GAMES = 4
ROLE_RATES = {"adot"}          # per-play, but a coaching choice rather than a result


def _derived(p):
    p = p.copy()
    p["_cpoe_wt"] = p.passing_cpoe * p.attempts       # so pooling gives an att-weighted mean
    p["_rb_yards"] = p.rushing_yards + p.receiving_yards
    return p


def aggregate(df, pos, per_game=True):
    """Collapse game rows to one row per (player_id, season) for every metric of `pos`."""
    vol, shr, rat = VOLUME[pos], SHARE[pos], RATE[pos]
    g = df.groupby(["player_id", "season"])
    out = pd.DataFrame(index=g.size().index)
    out["games"] = g.size()
    for name, num in vol:
        out[name] = g[num].sum()
        if per_game:
            out[name] = out[name] / out["games"]
    for name, col in shr:
        out[name] = g[col].mean().replace([np.inf, -np.inf], np.nan)
    for name, num, den in rat:
        n, d = g[num].sum(), g[den].sum()
        out[name] = np.where(d > 0, n / d.replace(0, np.nan), np.nan)
        out["den_" + name] = d
    return out


def build_panel(pos, weekly=None, snaps_only=False):
    """One row per player-season with w1_/ros_/prior_ columns for every metric."""
    p = _derived(load_weekly() if weekly is None else weekly)
    p = p[p.position == pos].copy()
    if snaps_only:
        p = p[p.season >= SNAP_FIRST]

    w1 = aggregate(p[p.week == 1], pos).add_prefix("w1_").reset_index()
    ros = aggregate(p[p.week >= 2], pos).add_prefix("ros_").reset_index()
    prior = aggregate(p, pos).add_prefix("prior_").reset_index()
    prior["season"] = prior.season + 1                # last year's line, aligned to this year

    panel = w1.merge(ros, on=["player_id", "season"], how="left") \
              .merge(prior, on=["player_id", "season"], how="left")
    panel["ros_games"] = panel.ros_games.fillna(0)
    panel = panel[panel["w1_" + _gate_name(pos)] >= W1_GATE[pos][1]].copy()
    panel["played_ros"] = panel.ros_games >= MIN_ROS_GAMES
    names = p[["player_id", "player_display_name", "season", "team"]] \
        .drop_duplicates(["player_id", "season"])
    return panel.merge(names, on=["player_id", "season"], how="left")


def _gate_name(pos):
    col = W1_GATE[pos][0]
    return {"attempts": "pass_attempts"}.get(col, col)


def metric_list(pos):
    return ([(n, "volume") for n, _ in VOLUME[pos]]
            + [(n, "share") for n, _ in SHARE[pos]]
            + [(n, "role" if n in ROLE_RATES else "rate") for n, _, _ in RATE[pos]])


# ------------------------------------------------------------- statistics

def pair(panel, metric, kind, pos, prefix_a, prefix_b, require_played=True):
    """Return the two aligned series for a metric, after sample filters."""
    d = panel
    if require_played:
        d = d[d.played_ros]
    a, b = prefix_a + "_" + metric, prefix_b + "_" + metric
    if a not in d or b not in d:
        return None, None
    m = d[a].notna() & d[b].notna()
    if kind in ("rate", "role"):
        for pre in (prefix_a, prefix_b):
            dcol = pre + "_den_" + metric
            if dcol in d:
                floor = 0 if pre == "w1" else RATE_MIN_DEN[pos]
                m &= d[dcol].fillna(0) >= floor
    return d.loc[m, a], d.loc[m, b]


def corr(x, y):
    if x is None or len(x) < 20:
        return dict(n=0 if x is None else len(x), r=np.nan, rho=np.nan, r2=np.nan)
    r = float(np.corrcoef(x, y)[0, 1])
    rho = float(pd.Series(x).rank().corr(pd.Series(y).rank()))
    return dict(n=len(x), r=r, rho=rho, r2=r * r)


def ols(y, X):
    """Least squares with an intercept. X is a 2-D array of standardized columns."""
    X = np.column_stack([np.ones(len(y)), X])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    ss_res = float(resid @ resid)
    ss_tot = float(((y - y.mean()) ** 2).sum())
    return beta, 1 - ss_res / ss_tot if ss_tot > 0 else np.nan


def z(s):
    s = np.asarray(s, dtype=float)
    sd = s.std()
    return (s - s.mean()) / sd if sd > 0 else s * 0.0


def fmt(x, nd=3):
    return "  n/a" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:.{nd}f}"
