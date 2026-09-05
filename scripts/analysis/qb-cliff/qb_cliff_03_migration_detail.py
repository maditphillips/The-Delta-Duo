# ==============================================================================
# THE QUARTERBACK CLIFF - MIGRATION, SEASON BY SEASON
#
# Part 4 of the roster script only reported first cell -> last cell. This prints
# every starter season a quarterback had and which quadrant it landed in, so the
# path through the 2x2 is visible rather than just its endpoints.
#
# OUTPUTS:
#   MIGRATION_DETAIL.txt              one block per QB, season by season
#   outputs/qb_quadrant_by_season_long.csv   one row per QB season
#   outputs/qb_quadrant_grid.csv      QBs down the side, 2008-2025 across the top
# ==============================================================================
import os

import numpy as np
import pandas as pd

from qb_cliff_00_setup import CONFIG, ERA, career_cell, load_panel, out_path

QUAD = {
    "1": "1 Efficient + rushing",
    "2": "2 Efficient + no legs",
    "3": "3 Inefficient + rushing",
    "4": "4 Inefficient + no legs",
}

z, MED_RUSH, MED_EFF = load_panel()
z = z.sort_values(["player_name", "season"])
z = z.merge(career_cell(z, MED_RUSH, MED_EFF)[["qb_id", "career_q"]], on="qb_id")
z["quadrant"] = z.q.map(QUAD)

# ---- long CSV, one row per QB season
long = z.assign(
    quadrant_n=z.q,
    rush_yd_pg=z.rush_yd_pg.round(2),
    designed_yd_pg=z.designed_yd_pg.round(2),
    scramble_yd_pg=z.scramble_yd_pg.round(2),
    epa_per_db=z.epa_per_db.round(4),
    fp_per_game=z.fp_per_game.round(2),
)[["player_name", "season", "round", "pick", "starts", "quadrant_n", "quadrant",
   "career_q", "rush_yd_pg", "designed_yd_pg", "scramble_yd_pg", "epa_per_db",
   "fp_per_game", "qb_rank", "is_qb1"]]
long.to_csv(out_path("qb_quadrant_by_season_long.csv"), index=False)

# ---- grid: quadrant number per QB per season, blank where he did not start 10
grid = z.pivot_table(index="player_name", columns="season", values="q",
                     aggfunc="first").fillna("")
grid = grid.reindex(sorted(grid.columns), axis=1)
grid.to_csv(out_path("qb_quadrant_grid.csv"))

# ---- printed timelines, ordered by career cell then by career FP/game
order = z.groupby(["qb_id", "player_name", "career_q"]).fp_per_game.median() \
         .reset_index().sort_values(["career_q", "fp_per_game"], ascending=[True, False])

print(f"QUADRANT MIGRATION, SEASON BY SEASON — {ERA}")
print(f"Splits: rushing {MED_RUSH:.2f} yds/game, EPA/dropback {MED_EFF:.4f}")
print(f"{len(z)} starter seasons, {z.qb_id.nunique()} quarterbacks")
print("Quadrants: 1 eff+rush | 2 eff+no legs | 3 ineff+rush | 4 ineff+no legs")
print("A season only appears if he started 10+ games that year.\n")

for career_q in "1234":
    block = order[order.career_q == career_q]
    print("\n" + "=" * 78)
    print(f"CAREER CELL {QUAD[career_q]} — {len(block)} quarterbacks")
    print("=" * 78)
    for _, row in block.iterrows():
        d = z[z.qb_id == row.qb_id]
        path = " -> ".join(d.q)
        moved = "stayed put" if d.q.nunique() == 1 else f"{d.q.nunique()} cells"
        szn = "season" if len(d) == 1 else "seasons"
        print(f"\n{row.player_name}  ({len(d)} starter {szn}, {moved})   path: {path}")
        t = d.assign(
            q=d.q, rush=d.rush_yd_pg.round(1), des=d.designed_yd_pg.round(1),
            scr=d.scramble_yd_pg.round(1), epa=d.epa_per_db.round(3),
            fpg=d.fp_per_game.round(1), qb1=np.where(d.is_qb1, "QB1", ""),
        )[["season", "q", "starts", "rush", "des", "scr", "epa", "fpg", "qb_rank", "qb1"]]
        t.columns = ["season", "q", "st", "rush/g", "des", "scr", "epa/db", "fp/g", "rank", ""]
        print(t.to_string(index=False))

print(f"\n\nWrote to {CONFIG['out_dir']}:")
print(f"  {os.path.basename(out_path('qb_quadrant_by_season_long.csv')):40s} one row per QB season")
print(f"  {os.path.basename(out_path('qb_quadrant_grid.csv')):40s} QBs x seasons, quadrant per cell")
