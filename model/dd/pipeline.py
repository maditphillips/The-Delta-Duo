"""Backtest and prediction runners."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import benchmark, dataset, evaluate
from .config import BACKTEST_SEASONS, CACHE, LIST_DEPTH, LISTS, OUTPUTS, POSITIONS, TARGET_SEASON
from .features import rankable
from .model import PositionModel, QUANTILES, rank_frame

SCORINGS = ("ppr", "half_ppr", "qb_4pt", "qb_6pt")
FIRST_TRAIN_SEASON = 2017  # needs a 2016 prior season underneath it


def build_panel(seasons, refresh: bool = False) -> pd.DataFrame:
    """Feature rows plus outcomes for week 1 of every season requested."""
    path = CACHE / "panel.parquet"
    if path.exists() and not refresh:
        cached = pd.read_parquet(path)
        if set(seasons).issubset(set(cached["season"].unique())):
            return cached[cached["season"].isin(list(seasons))].copy()
    frames = []
    for s in seasons:
        rows = dataset.build_rows(s)
        frames.append(dataset.attach_targets(rows, SCORINGS))
    panel = pd.concat(frames, ignore_index=True)
    panel.to_parquet(path)
    return panel


def attach_consensus(panel: pd.DataFrame) -> pd.DataFrame:
    out = []
    for s in sorted(panel["season"].unique()):
        c = benchmark.preseason_consensus(int(s))
        out.append(c)
    cons = pd.concat(out, ignore_index=True) if out else pd.DataFrame()
    if cons.empty:
        panel["consensus_rank"] = np.nan
        return panel
    return panel.merge(cons[["season", "player_id", "consensus_rank"]],
                       on=["season", "player_id"], how="left")


def backtest(panel: pd.DataFrame, positions=POSITIONS, verbose: bool = True) -> pd.DataFrame:
    """Expanding window: to project season S, train only on seasons before S.

    No leave-one-season-out, no shuffled folds. A model that has seen 2024 while
    projecting 2022 is not the model that will project 2026.
    """
    results, preds = [], []
    for pos in positions:
        for scoring in LISTS[pos]:
            for season in BACKTEST_SEASONS:
                train_seasons = [s for s in range(FIRST_TRAIN_SEASON, season)]
                if len(train_seasons) < 2:
                    continue
                tr = pd.concat([rankable(panel[panel["season"] == s], pos) for s in train_seasons])
                te = rankable(panel[panel["season"] == season], pos)
                if len(tr) < 100 or len(te) < 20:
                    continue
                # Model choice is made on the most recent training season only,
                # so the test season never influences which learner is used.
                holdout = rankable(panel[panel["season"] == train_seasons[-1]], pos)
                fit_on = pd.concat([rankable(panel[panel["season"] == s], pos)
                                    for s in train_seasons[:-1]]) if len(train_seasons) > 2 else tr
                m = PositionModel(pos, scoring).fit(fit_on, select_on=holdout)
                m = PositionModel(pos, scoring, kind=m.chosen_).fit(tr)

                p = m.predict(te)
                te = te.join(p)
                sims_cols = [f"q{int(q*100)}" for q in QUANTILES]
                from .model import simulate
                sims = simulate(p)
                te["p_play"] = p["p_play"].to_numpy()
                order = (-sims).argsort(axis=0).argsort(axis=0) + 1
                te["p_top12"] = (order <= 12).mean(axis=1)
                te["position"], te["scoring"], te["season"] = pos, scoring, season
                preds.append(te)

                actual = f"actual_{scoring}"
                row = evaluate.grade(te, "proj", actual, k=12, qcols=sims_cols,
                                     prob_col="p_top12")
                row.update({"position": pos, "scoring": scoring, "season": season,
                            "learner": m.chosen_, "n_train": len(tr)})
                # Baselines on the identical row set.
                cmp = evaluate.compare(te, actual, {
                    "model": "proj",
                    "consensus": "consensus_rank",
                    "prior_ppg": "ppg_ppr",
                }, k=12)
                metrics = ("spearman", "regret@12", "top12_overlap")
                have = set(cmp.columns) if len(cmp) else set()
                for src in ("consensus", "prior_ppg", "model"):
                    if src not in cmp.index:
                        continue
                    prefix = "model_common" if src == "model" else src
                    for metric in metrics:
                        if metric in have:
                            row[f"{prefix}_{metric}"] = cmp.loc[src, metric]
                results.append(row)
                if verbose:
                    print(f"  {pos:>3} {scoring:<8} {season}  rho={row['spearman']:.3f} "
                          f"({m.chosen_}, n={len(tr)})")
    res = pd.DataFrame(results)
    if preds:
        pd.concat(preds, ignore_index=True).to_parquet(CACHE / "backtest_preds.parquet")
    return res


def fit_final(panel: pd.DataFrame, pos: str, scoring: str, target_season: int) -> PositionModel:
    train_seasons = [s for s in range(FIRST_TRAIN_SEASON, target_season)]
    tr = pd.concat([rankable(panel[panel["season"] == s], pos) for s in train_seasons])
    holdout = rankable(panel[panel["season"] == train_seasons[-1]], pos)
    fit_on = pd.concat([rankable(panel[panel["season"] == s], pos)
                        for s in train_seasons[:-1]])
    probe = PositionModel(pos, scoring).fit(fit_on, select_on=holdout)
    return PositionModel(pos, scoring, kind=probe.chosen_).fit(tr)


def predict_week1(panel: pd.DataFrame, target_rows: pd.DataFrame,
                  target_season: int = TARGET_SEASON) -> dict:
    """Produce all eight published lists."""
    out = {}
    for pos in POSITIONS:
        for scoring in LISTS[pos]:
            m = fit_final(panel, pos, scoring, target_season)
            te = rankable(target_rows, pos)
            preds = m.predict(te)
            ranked = rank_frame(te, preds, LIST_DEPTH[pos])
            ranked["learner"] = m.chosen_
            out[(pos, scoring)] = ranked
    return out
