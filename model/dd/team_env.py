"""Team environment for week 1, the simple way.

The 22-dimension carryover machinery failed its ablation: as raw columns it
diluted the model, and the play-caller layer was a null. This is the reduced
version, and the reasoning is the user's:

  * For week 1 the useful fact about a team is simply **how its offence and
    defence actually performed last season**. That is measured, not projected.
  * The one change worth modelling is a **head-coaching change**, because that
    is the case where last season is least trustworthy -- a new head coach
    almost always brings a new coordinator, a new play-caller and a new scheme
    on both sides of the ball. It is also the only regime signal in verified
    public data: nflverse carries the head coach of every team-season.

So instead of projecting a scheme vector from a play-caller's history, we ask a
much smaller question with two coefficients per dimension: how much does last
season's team rate predict this season's, and how much less when the head coach
changed? The gap between those two coefficients *is* the head-coach effect, and
it is estimated from twenty seasons rather than assumed.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# The dimensions that actually drive fantasy volume. Deliberately few.
ENV_DIMS = [
    "plays_per_game", "neutral_pass_rate", "proe", "sec_per_play",
    "rb_target_share", "te_target_share", "wr_target_share",
    "rz_pass_rate", "gl_rush_rate",
]


class TeamEnvironment:
    """Per-dimension persistence of a team's rates, split by head-coach change.

        continuity  y_t ~ a0 + a1 * y_{t-1}
        hc change   y_t ~ b0 + b1 * y_{t-1}

    b1 < a1 is the head-coach effect: last season means less when the man in
    charge is new. Everything is fitted on raw units, so predictions come back
    in plays and pass rates rather than z-scores.
    """

    def __init__(self, dims=None):
        self.dims = list(dims or ENV_DIMS)
        self.coef_: dict = {}
        self.league_: dict = {}

    @staticmethod
    def _ols(x: np.ndarray, y: np.ndarray):
        X = np.column_stack([np.ones(len(x)), x])
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        pred = X @ beta
        ss_res = float(((y - pred) ** 2).sum())
        ss_tot = float(((y - y.mean()) ** 2).sum())
        return beta, (1 - ss_res / ss_tot if ss_tot > 0 else np.nan), len(y)

    def fit(self, fingerprints: pd.DataFrame, regime: pd.DataFrame, season: int):
        """Fit on every season strictly before `season`."""
        fp = fingerprints[fingerprints["season"] < season]
        lag = fp[["season", "team"] + self.dims].copy()
        lag["season"] = lag["season"] + 1
        panel = fp.merge(lag, on=["season", "team"], how="inner", suffixes=("", "_lag"))
        panel = panel.merge(regime[["season", "team", "hc_continuity"]],
                            on=["season", "team"], how="left")
        self.league_ = {d: float(fingerprints.loc[fingerprints["season"] == season - 1, d].mean())
                        for d in self.dims}
        for d in self.dims:
            for cont, key in ((1.0, "cont"), (0.0, "change")):
                sub = panel[(panel["hc_continuity"] == cont)].dropna(subset=[d, f"{d}_lag"])
                if len(sub) < 25:
                    continue
                beta, r2, n = self._ols(sub[f"{d}_lag"].to_numpy(), sub[d].to_numpy())
                self.coef_[(d, key)] = {"intercept": beta[0], "slope": beta[1],
                                        "r2": r2, "n": n}
        return self

    def project(self, fingerprints: pd.DataFrame, regime: pd.DataFrame,
                season: int) -> pd.DataFrame:
        prev = fingerprints[fingerprints["season"] == season - 1].set_index("team")
        tgt = regime[regime["season"] == season][["team", "hc_continuity", "head_coach"]].copy()
        rows = []
        for _, r in tgt.iterrows():
            row = {"team": r["team"], "hc_change": float(r["hc_continuity"] == 0)}
            for d in self.dims:
                lagv = prev[d].get(r["team"], np.nan)
                key = "cont" if r["hc_continuity"] == 1 else "change"
                c = self.coef_.get((d, key)) or self.coef_.get((d, "cont"))
                mu = self.league_.get(d, np.nan)
                if c is None or not np.isfinite(lagv):
                    row[f"env_{d}"] = mu
                else:
                    row[f"env_{d}"] = c["intercept"] + c["slope"] * lagv
            rows.append(row)
        return pd.DataFrame(rows)

    def report(self) -> pd.DataFrame:
        rows = []
        for d in self.dims:
            c, k = self.coef_.get((d, "cont"), {}), self.coef_.get((d, "change"), {})
            rows.append({"dim": d,
                         "same_hc_slope": c.get("slope"), "same_hc_r2": c.get("r2"),
                         "same_hc_n": c.get("n"),
                         "new_hc_slope": k.get("slope"), "new_hc_r2": k.get("r2"),
                         "new_hc_n": k.get("n"),
                         "hc_effect": (k.get("slope") - c.get("slope"))
                         if (c.get("slope") is not None and k.get("slope") is not None) else None})
        return pd.DataFrame(rows)
