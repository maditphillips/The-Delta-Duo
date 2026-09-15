"""Matchup: what a defence has given up so far, and to whom. Measured, and
not used.

The verdict first, because it decides how to read the rest. None of this pays.
Added to the week 2 model it moves within-week Spearman by between -0.002 and
+0.003, negative at three positions of four. The test that settles it is a
permutation: join every player to a real defence from the same week, drawn at
random rather than the one he actually faced, and the model scores identically.
The pairing carries nothing, which means the gain is not a matchup gain.

An earlier read of the same data said otherwise, and the way it was wrong is
worth recording. Bucketed five ways, a quarterback facing the softest fifth of
matchups beat his projection by 1.08 points more than one facing the toughest
fifth, which looks like a finding. The five buckets ran -1.21, -0.84, -1.29,
-0.48, -0.13: not a gradient, two ends of a noisy line. Endpoints are not an
effect.

The module is kept because the measurement is worth keeping and because the
answer could change with a better opponent adjustment or with defensive
personnel data we do not have. dd/inseason.features_final takes matchup=False
and that is where it stays until something here beats the null.


The week 2 model as first built had no opponent in it at all. It knew the
game's total and the spread, which is Vegas pricing the matchup, but a total
lifts both sidelines equally and cannot say that a defence stops the run and
leaks to the slot. That split is what this module supplies.

Three honesty problems have to be solved before one week of defence is worth
anything, and each one shapes what is built here.

A single game is close to noise. Nothing here is used raw: every defensive
measure is shrunk towards the same team's previous season by the same
empirical-Bayes rule the role features use, with its own fitted k. If one
week of defence carries no signal, the fitted k comes back large and the
adjustment is small in week 2 and grows through the season. That is a
measurement, not an assumption.

A defence that looks good may simply have played a bad offence. Points
allowed to a position are therefore taken as a residual: what the opposing
position group scored, minus what that same group scored per game last
season. A defence is credited with the difference it made, not with the
schedule it drew.

Score drives play calling, and play calling drives yards. A team that leads
all afternoon faces opponents who abandon the run and then looks stout
against it. So the per-play measures are rates, never volume, and are taken
in neutral game script only, with win probability between 20 and 80 percent.

The interaction is built by hand rather than hoped for. Ridge is linear and
wins at every position, which means it cannot represent "this offence throws
well AND this defence cannot cover", the thing anyone actually means by a
matchup. The product is therefore formed explicitly, from figures centred
within their own week so the scale is the league's that week and no future
information enters.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import ingest
from .config import CACHE
from .scoring import fantasy_points

POSITIONS = ["QB", "RB", "WR", "TE"]

# Both sides of the same play. Everything is a rate: a defence that faces
# sixty plays is not worse than one that faces fifty.
PLAY_COLS = ["season", "week", "season_type", "posteam", "defteam",
             "play_type", "epa", "success", "wp", "pass", "rush"]

# The in-season measure and the previous-season measure of the same thing.
# A blend is only meaningful between two readings of one quantity.
DEF_PAIRS = {
    "def_fpa_qb": ("sd_def_fpa_qb", "py_def_fpa_qb"),
    "def_fpa_rb": ("sd_def_fpa_rb", "py_def_fpa_rb"),
    "def_fpa_wr": ("sd_def_fpa_wr", "py_def_fpa_wr"),
    "def_fpa_te": ("sd_def_fpa_te", "py_def_fpa_te"),
    "def_epa_pass": ("sd_def_epa_pass", "py_def_epa_pass"),
    "def_epa_rush": ("sd_def_epa_rush", "py_def_epa_rush"),
    "def_sr_pass": ("sd_def_sr_pass", "py_def_sr_pass"),
    "def_sr_rush": ("sd_def_sr_rush", "py_def_sr_rush"),
}
OFF_PAIRS = {
    "off_epa_pass": ("sd_off_epa_pass", "py_off_epa_pass"),
    "off_epa_rush": ("sd_off_epa_rush", "py_off_epa_rush"),
}


def _plays(seasons) -> pd.DataFrame:
    """Per-play EPA and success, one row per team-week per side of the ball."""
    d = ingest.load("pbp", seasons, columns=PLAY_COLS)
    if not len(d):
        return pd.DataFrame()
    d = d[d.season_type.eq("REG")] if "season_type" in d else d
    d = d[d.play_type.isin(["pass", "run"]) & d.posteam.notna() & d.defteam.notna()]
    # Neutral script only. Garbage time is where a defence's yards-allowed
    # goes to die and where a leading team's run defence is flattered.
    d = d[d.wp.between(0.20, 0.80)]
    d["is_pass"] = d.play_type.eq("pass")
    d["epa"] = pd.to_numeric(d.epa, errors="coerce")
    d["success"] = pd.to_numeric(d.success, errors="coerce")

    frames = []
    for side, key in (("def", "defteam"), ("off", "posteam")):
        g = d.groupby(["season", "week", key, "is_pass"]).agg(
            epa=("epa", "mean"), sr=("success", "mean"), plays=("epa", "size"))
        g = g.reset_index().pivot_table(index=["season", "week", key],
                                        columns="is_pass",
                                        values=["epa", "sr", "plays"])
        g.columns = [f"{side}_{a}_{'pass' if b else 'rush'}" for a, b in g.columns]
        frames.append(g.reset_index().rename(columns={key: "team"}))
    a, b = frames
    return a.merge(b, on=["season", "week", "team"], how="outer")


def _allowed(seasons) -> pd.DataFrame:
    """Fantasy points each position scored against each defence, per week.

    Taken as a residual against the scoring offence's own previous-season rate
    for that position group, so a defence is not praised for the schedule it
    drew. PPR throughout: the question is which defences a position group eats
    against, and the format does not change that ordering.
    """
    s = ingest.load("stats_player", seasons)
    s = s[s.season_type.eq("REG")] if "season_type" in s else s
    s = s[s.position.isin(POSITIONS)].copy()
    s["pts"] = fantasy_points(s, "ppr")
    grp = s.groupby(["season", "week", "team", "opponent_team", "position"],
                    as_index=False).pts.sum()

    # What that offence's position group normally produces, measured last
    # season, so nothing from the week being scored enters the baseline.
    base = (grp.groupby(["season", "team", "position"], as_index=False)
            .pts.mean().rename(columns={"pts": "base"}))
    base["season"] = base.season + 1
    grp = grp.merge(base, on=["season", "team", "position"], how="left")
    # A team with no previous season falls back to that season's league rate,
    # which is the least-committed thing available.
    lg = grp.groupby(["season", "position"], as_index=False).pts.mean() \
        .rename(columns={"pts": "lg"})
    grp = grp.merge(lg, on=["season", "position"], how="left")
    grp["resid"] = grp.pts - grp.base.fillna(grp.lg)

    w = grp.pivot_table(index=["season", "week", "opponent_team"],
                        columns="position", values="resid").reset_index()
    w.columns = ["season", "week", "team"] + [f"def_fpa_{c.lower()}" for c in w.columns[3:]]
    return w


def _to_date(d: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """This season so far, strictly before the week in hand.

    Same rule and same order as dd/inseason.py: shift, then expand. Reversed,
    every row would carry the week it is meant to predict.
    """
    d = d.sort_values(["team", "season", "week"]).copy()
    g = d.groupby(["team", "season"], sort=False)
    for c in cols:
        if c in d.columns:
            d[f"sd_{c}"] = g[c].transform(lambda x: x.shift(1).expanding().mean())
    d["sd_def_games"] = g.cumcount()
    return d


def _prev_season(d: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """The same measures a whole season earlier, as the prior to shrink to."""
    p = d.groupby(["season", "team"], as_index=False)[cols].mean()
    p["season"] = p.season + 1
    return p.rename(columns={c: f"py_{c}" for c in cols})


def build(seasons=range(2019, 2027), refresh: bool = False) -> pd.DataFrame:
    """One row per team-week, carrying that team as a defence and as an offence."""
    path = CACHE / "defense.parquet"
    if path.exists() and not refresh:
        return pd.read_parquet(path)
    seasons = list(seasons)
    # pbp is the expensive half, and the previous season is needed as a prior,
    # so it is loaded one season wider than asked for.
    p = _plays(range(min(seasons) - 1, max(seasons) + 1))
    a = _allowed(range(min(seasons) - 1, max(seasons) + 1))
    d = p.merge(a, on=["season", "week", "team"], how="outer")
    raw = [c for c in d.columns if c.startswith(("def_", "off_")) and "plays" not in c]
    d = _to_date(d, raw)
    d = d.merge(_prev_season(d, raw), on=["season", "team"], how="left")
    d = d[d.season.isin(seasons)].reset_index(drop=True)
    d.to_parquet(path)
    return d


def blend(d: pd.DataFrame, k_def: float) -> pd.DataFrame:
    """This season's defence against last season's, n games against k."""
    out = d.copy()
    n = out.get("sd_def_games", pd.Series(0.0, index=out.index)).fillna(0.0)
    for name, (sd, prior) in {**DEF_PAIRS, **OFF_PAIRS}.items():
        if sd not in out or prior not in out:
            continue
        cur, old = out[sd], out[prior]
        out[f"b_{name}"] = np.where(
            cur.isna(), old,
            np.where(old.isna(), cur, (n * cur + k_def * old) / (n + k_def)))
    return out


def _centre(d: pd.DataFrame, col: str) -> pd.Series:
    """Standardised against the rest of the league that same week.

    Centring within the week rather than against a global mean keeps the
    interaction scale-free and leaks nothing: every input is already a
    strictly-before figure, and the comparison set is the other 31 teams.
    """
    g = d.groupby(["season", "week"])[col]
    return (d[col] - g.transform("mean")) / g.transform("std").replace(0, np.nan)


def attach(panel: pd.DataFrame, k_def: float, d: pd.DataFrame | None = None) -> pd.DataFrame:
    """Join the matchup onto a player panel and form the interaction terms.

    The defensive half joins on the opponent, the offensive half on his own
    team. The two products are the thing the ridge cannot build for itself:
    an offence that throws well meeting a defence that cannot stop the pass.
    """
    if d is None:
        d = build()
    d = blend(d, k_def)
    for c in ["b_off_epa_pass", "b_off_epa_rush", "b_def_epa_pass", "b_def_epa_rush"]:
        if c in d.columns:
            d[f"z_{c}"] = _centre(d, c)

    dcols = ["season", "week", "team", "sd_def_games"] \
        + [f"b_{k}" for k in DEF_PAIRS] + ["z_b_def_epa_pass", "z_b_def_epa_rush"]
    ocols = ["season", "week", "team"] + [f"b_{k}" for k in OFF_PAIRS] \
        + ["z_b_off_epa_pass", "z_b_off_epa_rush"]
    dcols = [c for c in dcols if c in d.columns]
    ocols = [c for c in ocols if c in d.columns]

    out = panel.merge(d[dcols].rename(columns={"team": "opponent"}),
                      on=["season", "week", "opponent"], how="left")
    out = out.merge(d[ocols], on=["season", "week", "team"], how="left")
    out["mx_pass"] = out.get("z_b_off_epa_pass") * out.get("z_b_def_epa_pass")
    out["mx_rush"] = out.get("z_b_off_epa_rush") * out.get("z_b_def_epa_rush")
    # Each position is handed the points-allowed column that is about it.
    if "position" in out.columns:
        pick = pd.Series(np.nan, index=out.index)
        for pos in POSITIONS:
            c = f"b_def_fpa_{pos.lower()}"
            if c in out.columns:
                m = out.position.eq(pos)
                pick[m] = out.loc[m, c]
        out["b_def_fpa_pos"] = pick
    return out


# What the matchup layer offers a position model. Kept separate from
# inseason.feature_list so that the model without it stays exactly the model
# that produced the week 2 board, and turning this on is a deliberate act.
MATCHUP = ["b_def_fpa_pos", "b_def_epa_pass", "b_def_epa_rush",
           "b_def_sr_pass", "b_def_sr_rush", "sd_def_games",
           "mx_pass", "mx_rush"]
