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
