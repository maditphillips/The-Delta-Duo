"""Command line entry points.

    python -m dd.cli ingest              # warm the nflverse cache
    python -m dd.cli panel               # build the point-in-time training panel
    python -m dd.cli backtest            # expanding-window backtest + metrics
    python -m dd.cli carryover           # 'does the play-caller's style travel?'
    python -m dd.cli predict             # write the eight week-1 lists
    python -m dd.cli skeleton            # regenerate config/playcallers.csv
"""
from __future__ import annotations

import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from . import benchmark, dataset, evaluate, ingest, pipeline, playcaller as pc, scheme
from .config import (BACKTEST_SEASONS, CACHE, LIST_DEPTH, LISTS, OUTPUTS, POSITIONS,
                     SCHEME_FIRST_SEASON, TARGET_SEASON, TARGET_WEEK)
from .scheme import DEF_DIMS, OFF_DIMS

TRAIN_SEASONS = range(pipeline.FIRST_TRAIN_SEASON, TARGET_SEASON)


def cmd_ingest():
    ingest.warm_cache()


def cmd_panel():
    panel = pipeline.build_panel(TRAIN_SEASONS, refresh=True)
    panel = pipeline.attach_consensus(panel)
    panel.to_parquet(CACHE / "panel.parquet")
    print(f"panel: {panel.shape[0]} player-weeks, {panel.shape[1]} columns, "
          f"seasons {panel.season.min()}-{panel.season.max()}")


def _panel():
    p = CACHE / "panel_allweeks.parquet"
    if not p.exists():
        cmd_panel()
    return pd.read_parquet(p)


def cmd_backtest():
    panel = _panel()
    res = pipeline.backtest(panel, verbose=True)
    out = OUTPUTS / "backtest"
    out.mkdir(parents=True, exist_ok=True)
    res.to_csv(out / "per_season.csv", index=False)

    preds = pd.read_parquet(CACHE / "backtest_preds.parquet")
    rows = []
    for (pos, sc), g in preds.groupby(["position", "scoring"]):
        for season, gs in g.groupby("season"):
            gs = gs.copy()
            gs["model_rank"] = gs["proj"].rank(ascending=False, method="first")
            if gs["consensus_rank"].notna().sum() < 20:
                continue
            depth = LIST_DEPTH[pos]
            pool = gs[(gs.model_rank <= depth) | (gs.consensus_rank <= depth)]
            cmp = evaluate.compare(pool, f"actual_{sc}",
                                   {"model": "proj", "consensus": "consensus_rank",
                                    "prior_ppg": "ppg_ppr"}, k=12)
            for src in cmp.index:
                rows.append({"position": pos, "scoring": sc, "season": season, "source": src,
                             **cmp.loc[src].to_dict()})
    head = pd.DataFrame(rows)
    head.to_csv(out / "head_to_head.csv", index=False)
    # MAE is omitted from the head-to-head: consensus publishes a rank, not a
    # points projection, so a points error is undefined for it.
    summary = head.groupby(["position", "scoring", "source"])[
        ["spearman", "ndcg@12", "top12_overlap", "regret@12"]].mean().round(3)
    summary.to_csv(out / "summary.csv")
    print(summary.to_string())


def cmd_carryover():
    off, dfn = dataset.fingerprints()
    reg = dataset.regime_table()
    out = OUTPUTS / "carryover"
    out.mkdir(parents=True, exist_ok=True)
    for side, fp, dims in (("off", off, OFF_DIMS), ("def", dfn, DEF_DIMS)):
        proj, model, rep = pc.project(fp, reg, side, dims, TARGET_SEASON)
        rep.to_csv(out / f"{side}_carryover_coefficients.csv", index=False)
        proj.to_csv(out / f"{side}_projected_scheme_{TARGET_SEASON}.csv", index=False)
        cols = [c for c in ["dim", "cont_team_lag", "cont_r2", "cont_n",
                            "chg_team_lag", "chg_caller_prior", "chg_r2", "chg_n"]
                if c in rep.columns]
        print(f"\n=== {side.upper()} carryover ===")
        print(rep[cols].round(3).to_string(index=False))


def cmd_predict():
    panel = _panel()
    rows = dataset.build_rows(TARGET_SEASON)
    cons = benchmark.preseason_consensus(TARGET_SEASON)
    rows = rows.merge(cons[["player_id", "consensus_rank"]], on="player_id", how="left")
    lists = pipeline.predict_week1(panel, rows, TARGET_SEASON)

    outdir = OUTPUTS / str(TARGET_SEASON) / f"week-{TARGET_WEEK:02d}"
    outdir.mkdir(parents=True, exist_ok=True)
    for (pos, scoring), df in lists.items():
        keep = ["rank_data", "player_name", "team", "opponent", "proj", "floor_q20",
                "ceiling_q90", "p_top12", "consensus_rank", "depth_rank",
                "expected_targets", "expected_carries", "implied_team_total",
                "off_continuity", "hc_continuity", "changed_team", "is_rookie", "learner"]
        keep = [c for c in keep if c in df.columns]
        out = df[keep].copy()
        out["delta_vs_consensus"] = out["consensus_rank"] - out["rank_data"]
        out = out.round(3)
        path = outdir / f"{pos.lower()}_{scoring}.csv"
        out.to_csv(path, index=False)
        print(f"  wrote {path.relative_to(OUTPUTS.parent)}  ({len(out)} players)")


def cmd_skeleton():
    sk = pc.write_overlay_skeleton()
    print(f"wrote {pc.OVERLAY} ({len(sk)} team-seasons)")


COMMANDS = {"ingest": cmd_ingest, "panel": cmd_panel, "backtest": cmd_backtest,
            "carryover": cmd_carryover, "predict": cmd_predict, "skeleton": cmd_skeleton}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(1)
    COMMANDS[sys.argv[1]]()
