# ==============================================================================
# THE QUARTERBACK CLIFF - PLAYER-LEVEL QUADRANT LISTS
#
# Every quarterback in the panel, placed by the MEDIAN of his starter seasons
# against the same splits. Part 3 of the roster script caps this at 3+ starter
# seasons; this covers all of them.
#
#   python3 qb_cliff_04_player_lists.py > QUADRANT_PLAYERS.txt
# ==============================================================================
import os

from qb_cliff_00_setup import CONFIG, ERA, career_cell, era_path, load_panel, out_path

NAMES = {
    "1": "EFFICIENT + RUSHING",
    "2": "EFFICIENT + NOT RUSHING",
    "3": "NOT EFFICIENT + RUSHING",
    "4": "NOT EFFICIENT + NOT RUSHING",
}

z, MED_RUSH, MED_EFF = load_panel()

c = z.groupby(["qb_id", "player_name", "rd", "pk"], dropna=False).agg(
    seasons=("season", "size"),
    rush=("rush_yd_pg", "median"),
    designed=("designed_yd_pg", "median"),
    scramble=("scramble_yd_pg", "median"),
    epa=("epa_per_db", "median"),
    fpg=("fp_per_game", "median"),
    qb1=("is_qb1", "sum"),
    best=("qb_rank", "min"),
    y0=("season", "min"),
    y1=("season", "max"),
).reset_index()
c = c.merge(career_cell(z, MED_RUSH, MED_EFF)[["qb_id", "career_q"]], on="qb_id")
c["quadrant"] = c.career_q.map(NAMES)

c.sort_values(["career_q", "fpg"], ascending=[True, False]).to_csv(
    out_path("qb_quadrants_all_players.csv"), index=False)

print(f"Career quadrant by the median of a QB's {CONFIG['start_bar_season']}+ "
      f"start seasons, {ERA}.")
print(f"Splits: rushing {MED_RUSH:.2f} yds/game, EPA/dropback {MED_EFF:.4f}. "
      f"{len(c)} quarterbacks.")

for k in "1234":
    d = c[c.career_q == k].sort_values("fpg", ascending=False)
    print(f"\n\n=== {NAMES[k]} — {len(d)} QBs ===")
    t = d.assign(
        yrs=d.y0.astype(str) + "-" + d.y1.astype(str),
        rush=d.rush.round(1), epa=d.epa.round(3), fpg=d.fpg.round(1),
    )[["player_name", "yrs", "seasons", "rush", "epa", "fpg", "qb1", "best"]]
    t.columns = ["player", "yrs", "szns", "rush/g", "epa/db", "fp/g", "qb1", "best"]
    print(t.to_string(index=False))

print(f"\n\nWrote {os.path.basename(out_path('qb_quadrants_all_players.csv'))} "
      f"to {CONFIG['out_dir']}")
