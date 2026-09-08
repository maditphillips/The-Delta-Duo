"""Head-to-head restricted to each source's top N.

The full board flatters everybody: ranking a starter above a third-string tight
end is not a skill anyone is paying for. What decides a week is the order inside
the group you would actually consider starting, so this grades only there.

Two framings, because they answer different questions:

  shared   Union of both sources' top N, graded on identical rows. This is the
           only way Spearman is comparable between two sources -- different row
           sets have different denominators.
  own      Each source's own top N judged on what those players actually did:
           how many of the real top 12 it captured, how many points its top 12
           delivered against a perfect twelve, where its picks truly finished.
           No matched rows needed, and it is the number that maps to a lineup.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULT_N = 36


def _actual_rank(g: pd.DataFrame, actual: str) -> pd.Series:
    return g[actual].rank(ascending=False, method="first")


def compare_top_n(preds: pd.DataFrame, n: int = DEFAULT_N) -> pd.DataFrame:
    """One row per (seed, position, scoring, season, source)."""
    out = []
    group_cols = [c for c in ("seed", "position", "scoring") if c in preds.columns]
    for keys, g in preds.groupby(group_cols + ["season"]):
        rec = dict(zip(group_cols + ["season"], keys))
        sc = rec["scoring"]
        actual = f"actual_{sc}"
        g = g.copy()
        if g["consensus_rank"].notna().sum() < n:
            continue
        g["model_rank"] = g["proj"].rank(ascending=False, method="first")
        g["ppg_rank"] = g["ppg_ppr"].rank(ascending=False, method="first")
        g["true_rank"] = _actual_rank(g, actual)

        sources = {"model": "model_rank", "consensus": "consensus_rank",
                   "prior_ppg": "ppg_rank"}
        tops = {s: g[g[c] <= n] for s, c in sources.items()}
        union = pd.concat(tops.values()).drop_duplicates("player_id")

        ideal12 = np.sort(g[actual].to_numpy())[::-1][:12].sum()
        for s, col in sources.items():
            t = tops[s].sort_values(col)
            if len(t) < 12:
                continue
            top12 = t.head(12)
            row = dict(rec)
            row["source"] = s
            # --- own top N, judged on outcomes ---
            row["captured_top12"] = float((top12["true_rank"] <= 12).sum())
            row["captured_top24_in_top24"] = float((t.head(24)["true_rank"] <= 24).sum())
            row["set_overlap_topN"] = float((t["true_rank"] <= n).sum())
            row["pts_top12"] = float(top12[actual].sum())
            row["regret_per_starter"] = float((ideal12 - top12[actual].sum()) / 12)
            row["median_true_finish_of_top12"] = float(top12["true_rank"].median())
            row["busts_in_top12"] = float((top12[actual] < 5).sum())
            # --- shared pool, so Spearman is comparable ---
            u = union.copy()
            r = u[col]
            ok = r.notna()
            from scipy.stats import spearmanr
            row["spearman_shared"] = float(spearmanr(-r[ok], u.loc[ok, actual]).statistic)
            row["n_shared"] = int(ok.sum())
            out.append(row)
    return pd.DataFrame(out)


def summarise(d: pd.DataFrame) -> pd.DataFrame:
    cols = ["captured_top12", "set_overlap_topN", "pts_top12", "regret_per_starter",
            "busts_in_top12", "median_true_finish_of_top12", "spearman_shared"]
    return d.groupby(["position", "source"])[cols].mean().round(3)


if __name__ == "__main__":
    import glob
    from .config import OUTPUTS
    frames = [pd.read_parquet(f) for f in sorted(glob.glob("/tmp/preds_*.parquet"))]
    preds = pd.concat(frames, ignore_index=True)
    d = compare_top_n(preds, DEFAULT_N)
    out = OUTPUTS / "backtest"
    out.mkdir(parents=True, exist_ok=True)
    d.to_csv(out / "top36_head_to_head.csv", index=False)
    print(summarise(d).to_string())
