"""Shared configuration for the Quarterback Cliff scripts.

Python port of qb_cliff_00_setup.R. The original R pipeline is not in this
repo, so the season panel is rebuilt from nflverse here (01_build_panel.py)
to the same definitions the study outline in src/data/qb.ts describes:

  population   212 quarterbacks drafted 2008-2025, outcomes through 2025
  starter bar  10+ starts in a season  ->  504 starter seasons
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))

CONFIG = {
    "draft_first": 2008,
    "draft_last": 2025,
    "season_first": 2008,
    "season_last": 2025,
    "start_bar_season": 10,       # starts needed for a "starter season"
    "qb1_rank": 12,               # top-12 = fantasy QB1
    "sfx_rank": 24,               # top-24 = superflex-relevant
    "cache_dir": os.path.join(HERE, "cache"),
    "out_dir": os.path.join(HERE, "outputs"),
    "tmp_dir": os.environ.get("NFLVERSE_TMP", "/tmp/nflverse"),
}

for k in ("cache_dir", "out_dir", "tmp_dir"):
    os.makedirs(CONFIG[k], exist_ok=True)

NFLVERSE = "https://github.com/nflverse/nflverse-data/releases/download"

# ---- era window ------------------------------------------------------------
# The per-season numbers (EPA per dropback, rushing yards per game, fantasy
# rank) are computed within a season and do not depend on the window. What the
# window changes is the POPULATION the medians are taken over, and so where the
# quadrant splits fall. Set with QB_CLIFF_FROM / QB_CLIFF_TO.
CONFIG["panel_first"] = int(os.environ.get("QB_CLIFF_FROM", CONFIG["season_first"]))
CONFIG["panel_last"] = int(os.environ.get("QB_CLIFF_TO", CONFIG["season_last"]))

FULL_ERA = (CONFIG["panel_first"] == CONFIG["season_first"]
            and CONFIG["panel_last"] == CONFIG["season_last"])
ERA = f"{CONFIG['panel_first']}-{CONFIG['panel_last']}"
SUFFIX = "" if FULL_ERA else f"_{CONFIG['panel_first']}_{CONFIG['panel_last']}"

QUAD_LABEL = {
    "1": "1. Efficient + legs",
    "2": "2. Efficient + no legs",
    "3": "3. Inefficient + legs",
    "4": "4. Inefficient + no legs",
}


def out_path(name):
    """outputs/ path with the era suffix inserted before the extension."""
    stem, ext = os.path.splitext(name)
    return os.path.join(CONFIG["out_dir"], f"{stem}{SUFFIX}{ext}")


def era_path(name):
    """Top-level path with the era suffix inserted before the extension."""
    stem, ext = os.path.splitext(name)
    return os.path.join(HERE, f"{stem}{SUFFIX}{ext}")


def load_panel():
    """The starter-season panel for the configured era, with quadrants.

    Returns (df, med_rush, med_eff). Splits are the medians of THIS era's
    panel, so they move with the window.
    """
    import numpy as np
    import pandas as pd

    s = pd.read_parquet(os.path.join(CONFIG["cache_dir"], "qb_season.parquet"))
    z = s[s.season.between(CONFIG["panel_first"], CONFIG["panel_last"])
          & (s.starts >= CONFIG["start_bar_season"])
          & s.rush_yd_pg.notna() & s.epa_per_db.notna() & s.fp.notna()].copy()

    med_rush = z.rush_yd_pg.median()
    med_eff = z.epa_per_db.median()
    z["rush_hi"] = z.rush_yd_pg > med_rush
    z["eff_hi"] = z.epa_per_db > med_eff
    z["q"] = np.select(
        [z.eff_hi & z.rush_hi, z.eff_hi & ~z.rush_hi, ~z.eff_hi & z.rush_hi],
        ["1", "2", "3"], default="4")
    z["quadrant"] = z.q.map(QUAD_LABEL)
    z["rd"] = z["round"].astype("Int64")
    z["pk"] = z["pick"].astype("Int64")
    z["draft_day"] = z.draft_day.fillna("Undrafted")
    return z, med_rush, med_eff


def career_cell(d, med_rush, med_eff, by="qb_id"):
    """Career quadrant per QB: the median of his starter seasons vs the same
    splits. Returns a frame with the grouping key and career_q."""
    import numpy as np

    c = d.groupby(by).agg(med_rush_pg=("rush_yd_pg", "median"),
                          med_epa_db=("epa_per_db", "median")).reset_index()
    c["career_q"] = np.select(
        [(c.med_epa_db > med_eff) & (c.med_rush_pg > med_rush),
         (c.med_epa_db > med_eff) & (c.med_rush_pg <= med_rush),
         (c.med_epa_db <= med_eff) & (c.med_rush_pg > med_rush)],
        ["1", "2", "3"], default="4")
    return c
