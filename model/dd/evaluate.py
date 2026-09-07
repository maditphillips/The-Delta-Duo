"""Grading. Ranking is the product, so the metrics are mostly rank metrics.

Absolute accuracy in week 1 is bad for every projection system ever built. The
number that decides whether this ships is the margin over consensus, not the
raw correlation.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import kendalltau, spearmanr


def ndcg_at_k(pred: np.ndarray, actual: np.ndarray, k: int = 12) -> float:
    """Gain is the player's actual points; discount is his predicted position."""
    order = np.argsort(-pred)
    gains = np.clip(actual[order][:k], 0, None)
    disc = 1 / np.log2(np.arange(2, len(gains) + 2))
    dcg = float((gains * disc).sum())
    ideal = np.sort(np.clip(actual, 0, None))[::-1][:k]
    idcg = float((ideal * disc[:len(ideal)]).sum())
    return dcg / idcg if idcg > 0 else np.nan


def top_k_overlap(pred: np.ndarray, actual: np.ndarray, k: int = 12) -> float:
    return len(set(np.argsort(-pred)[:k]) & set(np.argsort(-actual)[:k])) / k


def start_sit_regret(pred: np.ndarray, actual: np.ndarray, k: int = 12) -> float:
    """Points per starter left on the bench by trusting this order."""
    got = np.clip(actual[np.argsort(-pred)][:k], 0, None).sum()
    best = np.sort(np.clip(actual, 0, None))[::-1][:k].sum()
    return (best - got) / k


def pinball(actual: np.ndarray, q_values: np.ndarray, levels: np.ndarray) -> float:
    """Mean pinball loss across the quantile ladder. 2x this approximates CRPS."""
    a = actual[:, None]
    diff = a - q_values
    loss = np.maximum(levels * diff, (levels - 1) * diff)
    return float(loss.mean())


def brier(prob: np.ndarray, outcome: np.ndarray) -> float:
    return float(np.mean((prob - outcome) ** 2))


def grade(df: pd.DataFrame, pred_col: str, actual_col: str, k: int = 12,
          qcols: list[str] | None = None, prob_col: str | None = None) -> dict:
    d = df.reset_index(drop=True)
    p = d[pred_col].to_numpy(dtype=float)
    a = d[actual_col].to_numpy(dtype=float)
    ok = np.isfinite(p) & np.isfinite(a)
    p, a = p[ok], a[ok]
    if len(p) < 5:
        return {}
    out = {
        "n": len(p),
        "spearman": float(spearmanr(p, a).statistic),
        "kendall": float(kendalltau(p, a).statistic),
        f"ndcg@{k}": ndcg_at_k(p, a, k),
        f"top{k}_overlap": top_k_overlap(p, a, k),
        f"regret@{k}": start_sit_regret(p, a, k),
        "mae": float(np.mean(np.abs(p - a))),
        "rmse": float(np.sqrt(np.mean((p - a) ** 2))),
    }
    if qcols:
        levels = np.array([int(c[1:]) / 100 for c in qcols])
        out["crps"] = 2 * pinball(a, d.loc[ok, qcols].to_numpy(), levels)
    if prob_col and prob_col in df.columns:
        actual_rank = pd.Series(a).rank(ascending=False, method="first").to_numpy()
        out["brier_top12"] = brier(d.loc[ok, prob_col].to_numpy(),
                                   (actual_rank <= 12).astype(float))
    return out


def compare(df: pd.DataFrame, actual_col: str, contenders: dict, k: int = 12) -> pd.DataFrame:
    """Grade several ranking sources on identical rows.

    Every contender is scored on the same subset -- rows where all of them have
    an opinion -- otherwise the comparison flatters whoever ranks fewer players.
    """
    cols = [c for c in contenders.values() if c in df.columns]
    sub = df.dropna(subset=cols + [actual_col])
    rows = []
    for name, col in contenders.items():
        if col not in sub.columns:
            continue
        sign = -1.0 if "rank" in col else 1.0  # a rank is better when smaller
        r = grade(sub.assign(_p=sign * sub[col]), "_p", actual_col, k=k)
        r["source"] = name
        rows.append(r)
    return pd.DataFrame(rows).set_index("source") if rows else pd.DataFrame()
