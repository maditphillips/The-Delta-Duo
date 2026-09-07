"""Feature ablation: does a block of features actually earn its place?

Run with `python -m dd.ablate`. Re-fits the whole expanding-window backtest with
a block of features removed and reports the paired difference across
position-seasons, so a block that only looks useful stays out of the model.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from . import evaluate, features, pipeline
from .config import CACHE, LIST_DEPTH, OUTPUTS

# One scoring format per position keeps the run cheap; the formats barely
# differ in rank order for this purpose.
ONE_FORMAT = {"QB": ("qb_4pt",), "RB": ("ppr",), "WR": ("ppr",), "TE": ("ppr",)}

BLOCKS = {
    "full": [],
    "no_playcaller_layer": features.SCHEME_PROJ + features.REGIME,
    "no_scheme_at_all": features.SCHEME_PROJ + features.REGIME + features.SCHEME_PREV,
}


def run(panel: pd.DataFrame, blocks=None) -> pd.DataFrame:
    blocks = blocks or BLOCKS
    base = {k: list(v) for k, v in features.FEATURES.items()}
    original_lists = dict(pipeline.LISTS)
    rows = []
    try:
        pipeline.LISTS = ONE_FORMAT
        for name, drop in blocks.items():
            dropped = set(drop)
            features.FEATURES.update({p: [c for c in v if c not in dropped]
                                      for p, v in base.items()})
            pipeline.backtest(panel, verbose=False)
            preds = pd.read_parquet(CACHE / "backtest_preds.parquet")
            for (pos, sc), g in preds.groupby(["position", "scoring"]):
                for season, gs in g.groupby("season"):
                    gs = gs.copy()
                    gs["model_rank"] = gs["proj"].rank(ascending=False, method="first")
                    pool = gs[gs["model_rank"] <= LIST_DEPTH[pos]].copy()
                    pool["actual_rank"] = pool[f"actual_{sc}"].rank(ascending=False,
                                                                    method="first")
                    r = evaluate.grade(pool, "proj", f"actual_{sc}", k=12)
                    rows.append({
                        "variant": name, "position": pos, "season": season,
                        "spearman": r["spearman"], "top12": r["top12_overlap"],
                        "regret": r["regret@12"], "mae_pts": r["mae"],
                        "mean_abs_rank_err": float(
                            (pool["model_rank"] - pool["actual_rank"]).abs().mean()),
                    })
    finally:
        features.FEATURES.update(base)
        pipeline.LISTS = original_lists
    return pd.DataFrame(rows)


def report(d: pd.DataFrame) -> None:
    from scipy import stats
    print(d.groupby(["position", "variant"])[
        ["spearman", "top12", "mean_abs_rank_err", "mae_pts"]].mean().round(3).to_string())
    piv = d.pivot_table(index=["position", "season"], columns="variant", values="spearman")
    for v in [c for c in piv.columns if c != "full"]:
        delta = (piv["full"] - piv[v]).dropna()
        t = stats.ttest_1samp(delta, 0)
        w = stats.wilcoxon(delta)
        print(f"\n{v}: mean delta rho {delta.mean():+.3f}  wins {int((delta > 0).sum())}"
              f"/{len(delta)}  t={t.statistic:.2f} p={t.pvalue:.3f}  wilcoxon p={w.pvalue:.3f}")


if __name__ == "__main__":
    panel = pd.read_parquet(CACHE / "panel.parquet")
    d = run(panel)
    out = OUTPUTS / "ablation"
    out.mkdir(parents=True, exist_ok=True)
    d.to_csv(out / "playcaller_layer_ablation.csv", index=False)
    report(d)
