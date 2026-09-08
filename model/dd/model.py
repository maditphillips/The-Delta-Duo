"""The projection models: one per position, fitted per scoring format.

Structure follows the studies. Roughly half of every rankable week-1 pool
scores nothing at all -- the backup who never sees the field -- and lumping
those rows in with the starters produces a model that mostly predicts *whether
a man plays* and a "floor" of zero for everyone. So the question is split the
way the research splits it:

    stage A   P(he plays a real role)          -- classifier, whole pool
    stage B   E[points | he plays]             -- regressor, players only
    output    P x E[points | plays]            -- plus a mixture distribution

That mirrors the finding running through the QB, RB and WR studies: getting on
the field and producing once there are different questions with different
predictors, and conflating them is what makes draft capital look like talent.

Deliberately small learners. Week 1 gives roughly a thousand usable rows per
position across nine seasons, so a heavily regularised model with an explicit
linear baseline is the honest choice, and which one ships is decided by
expanding-window backtest, per position, not by taste.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import RidgeCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .features import FEATURES

QUANTILES = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)

# Boosting here is stochastic: early stopping carves a random validation split
# out of a few hundred rows, so the fitted model depends on the seed. Measured
# on this data, a seed change alone moved single-run Spearman by up to 0.14 --
# several times larger than any feature effect worth testing. Nothing about an
# ablation is readable at that noise level, so the ranking models are bagged
# across seeds and every reported metric is a seed-averaged one.
SEED = 17
N_SEEDS = 5


def _seeds(n: int | None = None):
    return [SEED + 1000 * i for i in range(n or N_SEEDS)]


class _Bag:
    """Average of the same estimator fitted under several seeds."""

    def __init__(self, factory, seeds):
        self.factory = factory
        self.seeds = list(seeds)
        self.members_ = []

    def fit(self, X, y):
        self.members_ = [self.factory(s).fit(X, y) for s in self.seeds]
        return self

    def predict(self, X):
        return np.mean([m.predict(X) for m in self.members_], axis=0)

    def predict_proba(self, X):
        return np.mean([m.predict_proba(X) for m in self.members_], axis=0)
PLAY_THRESHOLD = 0.5  # fantasy points; below this he did not have a week


def _ridge() -> Pipeline:
    return Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
        ("est", RidgeCV(alphas=np.logspace(-1, 3, 25))),
    ])


def _gbm(loss="squared_error", quantile=None, seed=None) -> HistGradientBoostingRegressor:
    return HistGradientBoostingRegressor(
        loss=loss, quantile=quantile,
        max_depth=3, max_iter=300, learning_rate=0.04,
        min_samples_leaf=20, l2_regularization=1.0,
        early_stopping=True, validation_fraction=0.2, n_iter_no_change=25,
        random_state=SEED if seed is None else seed,
    )


def _clf(seed=None) -> HistGradientBoostingClassifier:
    return HistGradientBoostingClassifier(
        max_depth=3, max_iter=300, learning_rate=0.05,
        min_samples_leaf=25, l2_regularization=1.0,
        early_stopping=True, validation_fraction=0.2, n_iter_no_change=25,
        random_state=SEED if seed is None else seed,
    )


class _Avg:
    """Average of two fitted estimators' predictions."""

    def __init__(self, members):
        self.members = list(members)

    def fit(self, X, y):
        for m in self.members:
            m.fit(X, y)
        return self

    def predict(self, X):
        return np.mean([m.predict(X) for m in self.members], axis=0)


# When is a ridge-vs-GBM gap real?
#
# The across-seed standard deviation of week-1 Spearman on this data is
# 0.024-0.052 -- but that is the noise for a *fixed* model re-fitted. A gap
# measured on a single held-out season also carries season-sampling noise,
# which is larger: season-to-season Spearman on this problem ranges from 0.12
# to 0.82. Using the seed-only figure as the threshold crowned a winner almost
# every time, which is precisely the coin-flip the blend rule exists to avoid.
# So the band is set to roughly twice the largest seed-only SD, and the gap must
# also agree in sign across two holdout seasons before either model is picked
# outright. Otherwise the two are averaged.
NOISE_BAND = 0.10


class PositionModel:
    def __init__(self, position: str, scoring: str, kind: str = "auto"):
        self.position = position
        self.scoring = scoring
        self.kind = kind
        self.features_: list[str] = []
        self.play_ = None
        self.mean_ = None
        self.quantiles_: dict = {}
        self.chosen_: str | None = None
        self.selection_: dict = {}

    # -- data ------------------------------------------------------------
    def _cols(self, df: pd.DataFrame) -> list[str]:
        return list(dict.fromkeys(c for c in FEATURES[self.position] if c in df.columns))

    def _matrix(self, df: pd.DataFrame, cols=None) -> pd.DataFrame:
        cols = cols or self._cols(df)
        X = df[cols].apply(pd.to_numeric, errors="coerce")
        if self.features_:
            return X[self.features_]
        keep = [c for c in cols if X[c].notna().any() and X[c].nunique(dropna=True) > 1]
        return X[keep]

    # -- fit -------------------------------------------------------------
    def fit(self, train: pd.DataFrame, select_on: pd.DataFrame | None = None):
        y = train[f"actual_{self.scoring}"].to_numpy(dtype=float)
        played = y > PLAY_THRESHOLD
        X = self._matrix(train)
        self.features_ = list(X.columns)
        Xn = X.to_numpy()

        self.play_ = _Bag(lambda s: _clf(seed=s), _seeds()).fit(Xn, played.astype(int))

        Xp, yp = Xn[played], y[played]
        candidates = {"ridge": _ridge(),
                      "gbm": _Bag(lambda s: _gbm(seed=s), _seeds())}
        if self.kind in candidates:
            self.chosen_ = self.kind
        elif select_on is not None and len(select_on) >= 40:
            from scipy.stats import spearmanr
            for est in candidates.values():
                est.fit(Xp, yp)
            probes = select_on if isinstance(select_on, (list, tuple)) else [select_on]
            gaps, per_season = [], {"ridge": [], "gbm": []}
            for probe_df in probes:
                if len(probe_df) < 40:
                    continue
                Xq = self._matrix(probe_df).to_numpy()
                truth = probe_df[f"actual_{self.scoring}"]
                p_play = self.play_.predict_proba(Xq)[:, 1]
                sc = {}
                for name, est in candidates.items():
                    r = spearmanr(est.predict(Xq) * p_play, truth).statistic
                    sc[name] = r if np.isfinite(r) else np.nan
                    per_season[name].append(sc[name])
                gaps.append(sc["ridge"] - sc["gbm"])
            gaps = [g for g in gaps if np.isfinite(g)]
            mean_gap = float(np.mean(gaps)) if gaps else 0.0
            consistent = len(gaps) > 0 and all(np.sign(g) == np.sign(mean_gap) for g in gaps)
            if abs(mean_gap) > NOISE_BAND and consistent:
                self.chosen_ = "ridge" if mean_gap > 0 else "gbm"
            else:
                self.chosen_ = "blend"
            self.selection_ = {"mean_gap": mean_gap, "gaps": gaps,
                               "band": NOISE_BAND, "consistent": consistent}
        else:
            self.chosen_ = "ridge"

        if self.chosen_ == "blend":
            self.mean_ = _Avg([_ridge(), _Bag(lambda s: _gbm(seed=s), _seeds())])
        else:
            self.mean_ = candidates[self.chosen_]
        self.mean_.fit(Xp, yp)
        for q in QUANTILES:
            self.quantiles_[q] = _gbm(loss="quantile", quantile=q).fit(Xp, yp)
        return self

    # -- predict ---------------------------------------------------------
    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        X = self._matrix(df).to_numpy()
        p_play = self.play_.predict_proba(X)[:, 1]
        cond = np.clip(self.mean_.predict(X), 0, None)

        cq = np.column_stack([np.clip(self.quantiles_[q].predict(X), 0, None)
                              for q in QUANTILES])
        cq = np.sort(cq, axis=1)  # independently fitted quantiles can cross

        out = pd.DataFrame(index=df.index)
        out["p_play"] = p_play
        out["cond_points"] = cond
        out["proj"] = p_play * cond
        # Mixture quantiles: a (1-p) point mass at zero sits below the
        # conditional distribution, so low quantiles are genuinely zero for a
        # player who may not play, and genuinely positive for one who will.
        levels = np.array(QUANTILES)
        for j, q in enumerate(QUANTILES):
            adj = (q - (1 - p_play)) / np.clip(p_play, 1e-6, None)
            vals = np.where(adj <= 0, 0.0,
                            [np.interp(a, levels, cq[i]) for i, a in enumerate(adj)])
            out[f"q{int(q*100)}"] = vals
        for j, q in enumerate(QUANTILES):
            out[f"cq{int(q*100)}"] = cq[:, j]
        return out


def simulate(preds: pd.DataFrame, n: int = 4000, seed: int = 7) -> np.ndarray:
    """Draw weeks: first whether he plays, then how it went if he did."""
    rng = np.random.default_rng(seed)
    ccols = sorted([c for c in preds.columns if c.startswith("cq")], key=lambda c: int(c[2:]))
    levels = np.array([int(c[2:]) / 100 for c in ccols])
    vals = preds[ccols].to_numpy()
    p = preds["p_play"].to_numpy()
    u = rng.random((len(preds), n))
    plays = rng.random((len(preds), n)) < p[:, None]
    sims = np.empty_like(u)
    for i in range(len(preds)):
        sims[i] = np.interp(u[i], levels, vals[i])
    return np.where(plays, sims, 0.0)


def rank_frame(rows: pd.DataFrame, preds: pd.DataFrame, depth: int) -> pd.DataFrame:
    """Turn projections into the published list, with the tails attached."""
    out = rows.copy().join(preds)
    sims = simulate(preds)
    order = (-sims).argsort(axis=0).argsort(axis=0) + 1
    out["p_top12"] = (order <= 12).mean(axis=1)
    out["p_top24"] = (order <= 24).mean(axis=1)
    out["floor_q20"] = preds["q20"].to_numpy()
    out["ceiling_q90"] = preds["q90"].to_numpy()
    out["bust_rate"] = (sims < 5).mean(axis=1)
    out = out.sort_values("proj", ascending=False)
    out["rank_data"] = np.arange(1, len(out) + 1)
    return out.head(depth)
