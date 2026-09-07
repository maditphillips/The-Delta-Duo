"""Who calls the plays, and how much of their style travels with them.

Public data has no play-caller table, so this module keeps two things apart:

1.  A *verified* backbone. nflverse schedules carry the head coach of every
    team-season back to 1999. Head-coach continuity is real, checkable data and
    needs no curation.
2.  A *curated overlay*, config/playcallers.csv, where coordinators and the
    actual play-caller can be filled in per team-season. When a row is present
    it wins; when it is absent the head coach stands in and the row is marked
    low confidence.

The carryover model then answers the question empirically rather than by
assumption: when a new play-caller arrives, how much of the new team's tendency
is explained by the team's own last season versus the incoming caller's history?
Per-dimension coefficients and R-squared say which traits actually travel.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import ingest
from .config import CONFIG, TARGET_SEASON
from .scheme import DEF_DIMS, OFF_DIMS

OVERLAY = CONFIG / "playcallers.csv"

OVERLAY_COLUMNS = [
    "season", "team", "head_coach", "off_playcaller", "off_playcaller_role",
    "def_playcaller", "def_playcaller_role", "confidence", "source", "note",
]


def head_coach_table(first_season: int = 1999, last_season: int = TARGET_SEASON) -> pd.DataFrame:
    """One row per team-season with the head coach, straight from schedules."""
    g = ingest.load("schedules")
    g = g[(g["season"] >= first_season) & (g["season"] <= last_season)]
    home = g[["season", "week", "home_team", "home_coach"]].rename(
        columns={"home_team": "team", "home_coach": "head_coach"})
    away = g[["season", "week", "away_team", "away_coach"]].rename(
        columns={"away_team": "team", "away_coach": "head_coach"})
    long = pd.concat([home, away], ignore_index=True).dropna(subset=["head_coach"])
    # A team can change coaches mid-season; take whoever coached the most games,
    # but keep the week-1 coach too since week 1 is what we project.
    modal = (long.groupby(["season", "team"])["head_coach"]
             .agg(lambda s: s.value_counts().idxmax()).rename("head_coach").reset_index())
    wk1 = (long[long["week"] == 1][["season", "team", "head_coach"]]
           .drop_duplicates().rename(columns={"head_coach": "week1_head_coach"}))
    out = modal.merge(wk1, on=["season", "team"], how="left")
    out["team"] = out["team"].replace({"OAK": "LV", "SD": "LAC", "STL": "LA", "LAR": "LA"})
    return out


def load_overlay() -> pd.DataFrame:
    if OVERLAY.exists():
        df = pd.read_csv(OVERLAY)
        for c in OVERLAY_COLUMNS:
            if c not in df.columns:
                df[c] = np.nan
        return df[OVERLAY_COLUMNS]
    return pd.DataFrame(columns=OVERLAY_COLUMNS)


def regimes(first_season: int, last_season: int = TARGET_SEASON) -> pd.DataFrame:
    """Team-season table naming the offensive and defensive play-caller.

    `*_confidence` is 'curated' when the overlay supplied a name and
    'head_coach_proxy' when we fell back to the head coach.
    """
    hc = head_coach_table(first_season, last_season)
    ov = load_overlay()
    df = hc.merge(ov.drop(columns=["head_coach"]), on=["season", "team"], how="left")

    df["off_confidence"] = np.where(df["off_playcaller"].notna(), "curated", "head_coach_proxy")
    df["def_confidence"] = np.where(df["def_playcaller"].notna(), "curated", "head_coach_proxy")
    df["off_playcaller"] = df["off_playcaller"].fillna(df["week1_head_coach"]).fillna(df["head_coach"])
    df["def_playcaller"] = df["def_playcaller"].fillna(df["week1_head_coach"]).fillna(df["head_coach"])

    df = df.sort_values(["team", "season"])
    prev_hc = df.groupby("team")["head_coach"].shift(1)
    df["hc_continuity"] = (df["head_coach"] == prev_hc).astype(float)
    df.loc[prev_hc.isna(), "hc_continuity"] = np.nan

    for side in ("off", "def"):
        prev = df.groupby("team")[f"{side}_playcaller"].shift(1)
        prev_conf = df.groupby("team")[f"{side}_confidence"].shift(1)
        # Compare like with like. Curating one season and not the one before it
        # would otherwise read as "every team changed play-caller", because a
        # coordinator's name never equals last season's head coach's name. Where
        # both seasons are curated, compare the play-callers; anywhere else, fall
        # back to head-coach continuity, which is verified for every season.
        both_curated = (df[f"{side}_confidence"] == "curated") & (prev_conf == "curated")
        df[f"{side}_continuity"] = np.where(
            both_curated,
            (df[f"{side}_playcaller"] == prev).astype(float),
            df["hc_continuity"])
        df.loc[prev.isna(), f"{side}_continuity"] = np.nan
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Fingerprints attached to people
# ---------------------------------------------------------------------------

def _zscore_by_season(df: pd.DataFrame, dims) -> pd.DataFrame:
    """Standardise each dimension within season, so eras are comparable and the
    league mean is always 0. Fingerprints are only ever compared, never used raw."""
    out = df.copy()
    for d in dims:
        g = out.groupby("season")[d]
        out[d] = (out[d] - g.transform("mean")) / g.transform("std").replace(0, np.nan)
    return out


def caller_history(fingerprints: pd.DataFrame, regime: pd.DataFrame, side: str,
                   dims, half_life: float = 2.0, min_weight: float = 0.15) -> pd.DataFrame:
    """For each (season, caller), the recency-weighted average of every prior
    season that caller ran, at any team. Strictly prior: no leakage from the
    season being predicted.

    `min_weight` guards against stale matches. Names are matched across the
    whole table, so a coordinator hired in 2026 can collide with his own head
    coaching stint fifteen years earlier -- Steve Spagnuolo's 2009-11 Rams, say,
    which say nothing about the defence he calls now. Recency weights decay by
    `half_life`, but averaging renormalises them, so an ancient-only history
    would still be used at full strength. Rows whose total *unnormalised* weight
    falls below this floor are dropped instead, and the caller is treated as
    having no history at all -- which sends him to the league mean, the honest
    answer."""
    key = f"{side}_playcaller"
    fp = fingerprints.merge(regime[["season", "team", key]], on=["season", "team"], how="inner")
    rows = []
    for caller, grp in fp.groupby(key):
        seasons = sorted(grp["season"].unique())
        for s in list(seasons) + [max(seasons) + 1]:
            prior = grp[grp["season"] < s]
            if prior.empty:
                continue
            w = 0.5 ** ((s - prior["season"] - 1) / half_life)
            if float(w.sum()) < min_weight:
                continue
            vals = {d: np.average(prior[d], weights=w) if prior[d].notna().all()
                    else (np.average(prior.loc[prior[d].notna(), d],
                                     weights=w[prior[d].notna()]) if prior[d].notna().any() else np.nan)
                    for d in dims}
            rows.append({"season": s, key: caller, "prior_seasons": len(prior),
                         "prior_weight": float(w.sum()), **vals})
    if not rows:
        return pd.DataFrame(columns=["season", key, "prior_seasons", "prior_weight"] + list(dims))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# The carryover model
# ---------------------------------------------------------------------------

class CarryoverModel:
    """Per-dimension OLS answering 'how much of the style travels?'

    Two regimes, fitted separately because under continuity the team's own last
    season and the caller's history are the same observation:

      continuity   : y_t ~ a * y_{t-1}
      caller change: y_t ~ b1 * y_{t-1} + b2 * caller_prior

    b2 is the carryover weight. A dimension with a large b2 and a small b1 is a
    trait the person brings with them; the reverse is a trait the roster owns.
    """

    def __init__(self, dims, min_n: int = 20):
        self.dims = list(dims)
        self.min_n = min_n
        self.cont_: dict = {}
        self.change_: dict = {}

    @staticmethod
    def _ols(X: np.ndarray, y: np.ndarray):
        X = np.column_stack([np.ones(len(X)), X])
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        pred = X @ beta
        ss_res = float(((y - pred) ** 2).sum())
        ss_tot = float(((y - y.mean()) ** 2).sum())
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
        return beta, r2, len(y)

    def fit(self, panel: pd.DataFrame, side: str):
        """panel: one row per team-season with columns
        <dim>, <dim>_lag (team last season), <dim>_caller (caller history), continuity."""
        cont = panel[panel[f"{side}_continuity"] == 1]
        chg = panel[panel[f"{side}_continuity"] == 0]
        for d in self.dims:
            c = cont.dropna(subset=[d, f"{d}_lag"])
            if len(c) >= self.min_n:
                beta, r2, n = self._ols(c[[f"{d}_lag"]].to_numpy(), c[d].to_numpy())
                self.cont_[d] = {"intercept": beta[0], "team_lag": beta[1], "r2": r2, "n": n}
            k = chg.dropna(subset=[d, f"{d}_lag", f"{d}_caller"])
            if len(k) >= self.min_n:
                beta, r2, n = self._ols(k[[f"{d}_lag", f"{d}_caller"]].to_numpy(), k[d].to_numpy())
                self.change_[d] = {"intercept": beta[0], "team_lag": beta[1],
                                   "caller_prior": beta[2], "r2": r2, "n": n}
        return self

    def predict_row(self, d: str, team_lag: float, caller_prior: float, continuity: float) -> float:
        """Projected z-scored tendency for one dimension. Unknown inputs fall
        back to the league mean (0), which is the honest answer for a
        first-time play-caller."""
        if continuity == 1 and d in self.cont_:
            c = self.cont_[d]
            lag = 0.0 if not np.isfinite(team_lag) else team_lag
            return c["intercept"] + c["team_lag"] * lag
        if d in self.change_:
            c = self.change_[d]
            lag = 0.0 if not np.isfinite(team_lag) else team_lag
            if not np.isfinite(caller_prior):
                # No history for the incoming caller: keep the team term, drop
                # the caller term to the league mean rather than guessing.
                return c["intercept"] + c["team_lag"] * lag
            return c["intercept"] + c["team_lag"] * lag + c["caller_prior"] * caller_prior
        return 0.0

    def report(self) -> pd.DataFrame:
        rows = []
        for d in self.dims:
            r = {"dim": d}
            r.update({f"cont_{k}": v for k, v in self.cont_.get(d, {}).items()})
            r.update({f"chg_{k}": v for k, v in self.change_.get(d, {}).items()})
            rows.append(r)
        return pd.DataFrame(rows)


def build_panel(fingerprints: pd.DataFrame, regime: pd.DataFrame, side: str, dims) -> pd.DataFrame:
    """Assemble the fit panel: current value, team's lag, caller's prior history."""
    z = _zscore_by_season(fingerprints, dims)
    key = f"{side}_playcaller"
    hist = caller_history(z, regime, side, dims)
    panel = z.merge(regime[["season", "team", key, f"{side}_continuity"]],
                    on=["season", "team"], how="left")
    lag = z[["season", "team"] + list(dims)].copy()
    lag["season"] = lag["season"] + 1
    panel = panel.merge(lag, on=["season", "team"], how="left", suffixes=("", "_lag"))
    panel = panel.merge(hist, on=["season", key], how="left", suffixes=("", "_caller"))
    for d in dims:  # caller history columns are suffixed only where they collide
        if f"{d}_caller" not in panel.columns:
            panel[f"{d}_caller"] = np.nan
    return panel


def project(fingerprints: pd.DataFrame, regime: pd.DataFrame, side: str, dims,
            target_season: int) -> tuple[pd.DataFrame, CarryoverModel, pd.DataFrame]:
    """Fit carryover on history, then project every team's scheme vector for
    `target_season`. Returns (projection, model, fit report)."""
    dims = list(dims)
    z = _zscore_by_season(fingerprints, dims)
    panel = build_panel(fingerprints, regime, side, dims)
    train = panel[panel["season"] < target_season]
    model = CarryoverModel(dims).fit(train, side)

    key = f"{side}_playcaller"
    hist = caller_history(z, regime, side, dims)
    tgt = regime[regime["season"] == target_season][["season", "team", key, f"{side}_continuity",
                                                     f"{side}_confidence"]].copy()
    lag = z[z["season"] == target_season - 1][["team"] + dims].set_index("team")
    hist_t = hist[hist["season"] == target_season].set_index(key)

    out = []
    for _, r in tgt.iterrows():
        row = {"season": target_season, "team": r["team"], key: r[key],
               "continuity": r[f"{side}_continuity"], "confidence": r[f"{side}_confidence"]}
        prior_seasons = float(hist_t["prior_seasons"].get(r[key], 0)) if len(hist_t) else 0.0
        row["caller_prior_seasons"] = prior_seasons
        for d in dims:
            tl = lag[d].get(r["team"], np.nan)
            cp = hist_t[d].get(r[key], np.nan) if len(hist_t) else np.nan
            row[d] = model.predict_row(d, tl, cp, r[f"{side}_continuity"])
        out.append(row)
    return pd.DataFrame(out), model, model.report()


def write_overlay_skeleton(first_season: int = 2015, last_season: int = TARGET_SEASON,
                           path=None) -> pd.DataFrame:
    """Write config/playcallers.csv pre-filled with verified head coaches and
    blank coordinator columns, without clobbering rows already curated."""
    path = path or OVERLAY
    hc = head_coach_table(first_season, last_season)
    skel = hc[["season", "team", "head_coach"]].copy()
    for c in OVERLAY_COLUMNS:
        if c not in skel.columns:
            skel[c] = np.nan
    skel = skel[OVERLAY_COLUMNS]
    if path.exists():
        cur = load_overlay()
        curated = cur[cur["off_playcaller"].notna() | cur["def_playcaller"].notna()]
        skel = skel.merge(curated.drop(columns=["head_coach"]), on=["season", "team"],
                          how="left", suffixes=("_blank", ""))
        skel = skel[OVERLAY_COLUMNS]
    skel.sort_values(["season", "team"]).to_csv(path, index=False)
    return skel
