# ==============================================================================
# THE QUARTERBACK CLIFF - QUADRANT ROSTERS
#
# Names for the Act Three 2x2. Python port of the R script; run after
# qb_cliff_01_build_panel.py.
#
# THRESHOLDS (identical to Act Three 3.3, so the counts reconcile):
#   rushing split at the median of all 10+ start seasons  (~10.36 rush yds/game)
#   efficiency split at the median EPA per dropback       (~0.0676)
#
# The split is computed fresh from the data rather than hardcoded, so if the
# panel changes the thresholds move with it. Both are PRINTED.
#
# OUTPUTS:
#   1. Season-level lists for all four quadrants (503 seasons)
#   2. Top-12 seasons only, by quadrant (216 seasons) - the shareable version
#   3. Career-level classification for QBs with 3+ starter seasons
#   4. Quadrant MIGRATION - do quarterbacks move between cells over a career?
#   5. Current quarterbacks only (2023-2025) - the dynasty-actionable version
#   6. The dead zone roster (10-15 rushing yards per game)
#
# Everything is also written to CSV in ./outputs/ so you can pull names for posts.
# ==============================================================================
import os

import numpy as np
import pandas as pd

from qb_cliff_00_setup import CONFIG, ERA, load_panel, out_path

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 50)


def show(df, n=None):
    if n is not None and len(df) > n:
        print(df.head(n).to_string(index=False))
        print(f"# ... {len(df) - n} more rows")
    else:
        print(df.to_string(index=False))


szn, MED_RUSH, MED_EFF = load_panel()

print("\n================ QUADRANT DEFINITIONS ================")
print(f"  era: {ERA} starter seasons ({CONFIG['start_bar_season']}+ starts)")
print(f"  rushing split (kneel-excluded):  {MED_RUSH:.3f} yds/game")
print(f"  efficiency split:                {MED_EFF:.5f} EPA/dropback")
print(f"  population: {len(szn)} starter seasons, {szn.qb_id.nunique()} quarterbacks")
print("=====================================================")

print("\n[COUNTS]")
cnt = szn.quadrant.value_counts().sort_index().rename("n").to_frame().reset_index()
cnt["share"] = (cnt.n / cnt.n.sum()).round(3)
show(cnt)


# ---- 1. SEASON-LEVEL LISTS --------------------------------------------------
def print_quadrant(qd, top_only=False, n_show=200):
    d = szn[szn.quadrant == qd]
    if top_only:
        d = d[d.is_qb1]
    print("\n\n############################################################")
    print(f"### {qd}{' -- TOP-12 SEASONS ONLY' if top_only else ''}")
    rate = 100 * szn.is_qb1[szn.quadrant == qd].mean()
    print(f"### n = {len(d)} | top-12 rate = {rate:.1f}%")
    print("############################################################")
    out = d.sort_values("fp_per_game", ascending=False).assign(
        player=lambda x: x.player_name,
        rush_pg=lambda x: x.rush_yd_pg.round(1),
        designed_pg=lambda x: x.designed_yd_pg.round(1),
        scramble_pg=lambda x: x.scramble_yd_pg.round(1),
        epa_db=lambda x: x.epa_per_db.round(3),
        fp_pg=lambda x: x.fp_per_game.round(1),
        rank=lambda x: x.qb_rank,
    )[["player", "season", "rd", "pk", "starts", "rush_pg", "designed_pg",
       "scramble_pg", "epa_db", "fp_pg", "rank"]]
    show(out, n_show)
    return d


QUADS = ["1. Efficient + legs", "2. Efficient + no legs",
         "3. Inefficient + legs", "4. Inefficient + no legs"]

print("\n\n\n=========== PART 1: ALL STARTER SEASONS BY QUADRANT ===========")
for qd in QUADS:
    print_quadrant(qd)


# ---- 2. TOP-12 SEASONS ONLY -------------------------------------------------
print("\n\n\n=========== PART 2: TOP-12 SEASONS ONLY ===========")
print("This is the version for a post. 216 seasons, and where they came from.")
for qd in QUADS:
    print_quadrant(qd, top_only=True, n_show=120)


# ---- 3. CAREER-LEVEL CLASSIFICATION -----------------------------------------
# A quarterback's quadrant, using the MEDIAN of his starter seasons against the
# same population thresholds. Restricted to 3+ starter seasons so one outlier
# year cannot define a career.
print("\n\n\n=========== PART 3: CAREER CLASSIFICATION (3+ starter seasons) ===========")

career_q = szn.groupby(["qb_id", "player_name", "rd", "pk", "draft_day"],
                       dropna=False).agg(
    seasons=("season", "size"),
    med_rush_pg=("rush_yd_pg", "median"),
    med_designed_pg=("designed_yd_pg", "median"),
    med_scramble_pg=("scramble_yd_pg", "median"),
    med_epa_db=("epa_per_db", "median"),
    med_fp_pg=("fp_per_game", "median"),
    qb1_seasons=("is_qb1", "sum"),
    best_rank=("qb_rank", "min"),
    first_season=("season", "min"),
    last_season=("season", "max"),
).reset_index()
career_q = career_q[career_q.seasons >= 3].copy()
career_q["quadrant"] = np.select(
    [(career_q.med_epa_db > MED_EFF) & (career_q.med_rush_pg > MED_RUSH),
     (career_q.med_epa_db > MED_EFF) & (career_q.med_rush_pg <= MED_RUSH),
     (career_q.med_epa_db <= MED_EFF) & (career_q.med_rush_pg > MED_RUSH)],
    ["1. Efficient + legs", "2. Efficient + no legs", "3. Inefficient + legs"],
    default="4. Inefficient + no legs")

print("\n[Career quadrant counts and how often they produced a QB1 season]")
g = career_q.groupby("quadrant").apply(lambda d: pd.Series({
    "players": int(len(d)),
    "total_seasons": int(d.seasons.sum()),
    "total_qb1_seasons": int(d.qb1_seasons.sum()),
    "qb1_per_season": round(d.qb1_seasons.sum() / d.seasons.sum(), 3),
    "pct_with_any_qb1": round((d.qb1_seasons > 0).mean(), 3),
    "median_fp_pg": round(d.med_fp_pg.median(), 1),
}), include_groups=False).reset_index()
for c in ("players", "total_seasons", "total_qb1_seasons"):
    g[c] = g[c].astype(int)
show(g)

for qd in QUADS:
    d = career_q[career_q.quadrant == qd].sort_values("med_fp_pg", ascending=False)
    print(f"\n\n### CAREER: {qd} -- {len(d)} quarterbacks")
    out = d.assign(
        player=lambda x: x.player_name,
        yrs=lambda x: x.first_season.astype(str) + "-" + x.last_season.astype(str),
        rush_pg=lambda x: x.med_rush_pg.round(1),
        epa_db=lambda x: x.med_epa_db.round(3),
        fp_pg=lambda x: x.med_fp_pg.round(1),
        qb1_szns=lambda x: x.qb1_seasons,
        best=lambda x: x.best_rank,
    )[["player", "rd", "pk", "seasons", "yrs", "rush_pg", "epa_db", "fp_pg",
       "qb1_szns", "best"]]
    show(out, 100)


# ---- 4. MIGRATION -----------------------------------------------------------
# Do quarterbacks stay in one cell? This matters for the article: if a QB can
# move from "inefficient + legs" to "efficient + legs", that is a development
# path and it is the single most valuable thing that can happen to a dynasty asset.
print("\n\n\n=========== PART 4: DO QUARTERBACKS MIGRATE? ===========")

mig = szn.sort_values("season").groupby(["qb_id", "player_name"]).agg(
    seasons=("season", "size"),
    n_quadrants=("quadrant", "nunique"),
    first_q=("quadrant", "first"),
    last_q=("quadrant", "last"),
).reset_index()
mig = mig[mig.seasons >= 3].copy()

print("\n[How many distinct quadrants does a QB occupy across his career?]")
nq = mig.n_quadrants.value_counts().sort_index().rename("n").to_frame().reset_index()
nq["share"] = (nq.n / nq.n.sum()).round(3)
show(nq)

print("\n[First quadrant -> last quadrant transitions]")
tr = mig.groupby(["first_q", "last_q"]).size().rename("n").reset_index()
show(tr.sort_values("n", ascending=False), 30)

cols = ["player_name", "seasons", "n_quadrants", "first_q", "last_q"]
print("\n[The valuable move: QBs who ENTERED inefficient and ENDED efficient]")
show(mig[mig.first_q.str.match("^[34]") & mig.last_q.str.match("^[12]")]
     .sort_values("player_name")[cols], 50)

print("\n[The warning sign: QBs who ENTERED efficient and ENDED inefficient]")
show(mig[mig.first_q.str.match("^[12]") & mig.last_q.str.match("^[34]")]
     .sort_values("player_name")[cols], 50)

print("\n[Did anyone GAIN legs mid-career? no-legs start -> legs finish]")
show(mig[mig.first_q.str.contains("no legs") & ~mig.last_q.str.contains("no legs")]
     .sort_values("player_name")[cols], 50)

print("\n[And who LOST them? legs start -> no-legs finish]")
show(mig[~mig.first_q.str.contains("no legs") & mig.last_q.str.contains("no legs")]
     .sort_values("player_name")[cols], 50)


# ---- 5. CURRENT QUARTERBACKS ------------------------------------------------
CUR_FROM = max(2023, CONFIG["panel_first"])
print(f"\n\n\n=========== PART 5: CURRENT QBs ({CUR_FROM}-{CONFIG['panel_last']} only) ===========")
print("The dynasty-actionable version.")

cur = szn[szn.season >= CUR_FROM]

g = cur.groupby("quadrant").agg(seasons=("season", "size"), qb1_n=("is_qb1", "sum"),
                                qb1_rate=("is_qb1", "mean")).round(3).reset_index()
show(g)

for qd in QUADS:
    d = cur[cur.quadrant == qd].sort_values("fp_per_game", ascending=False)
    print(f"\n\n### CURRENT: {qd} -- {len(d)} seasons")
    out = d.assign(
        player=lambda x: x.player_name,
        rush_pg=lambda x: x.rush_yd_pg.round(1),
        designed_pg=lambda x: x.designed_yd_pg.round(1),
        scramble_pg=lambda x: x.scramble_yd_pg.round(1),
        epa_db=lambda x: x.epa_per_db.round(3),
        fp_pg=lambda x: x.fp_per_game.round(1),
        rank=lambda x: x.qb_rank,
    )[["player", "season", "rd", "pk", "rush_pg", "designed_pg", "scramble_pg",
       "epa_db", "fp_pg", "rank"]]
    show(out, 60)

print(f"\n[Most recent season for every QB who started in {CONFIG['panel_last']}]")
out = szn[szn.season == CONFIG["panel_last"]].sort_values("qb_rank").assign(
    player=lambda x: x.player_name,
    rush_pg=lambda x: x.rush_yd_pg.round(1),
    epa_db=lambda x: x.epa_per_db.round(3),
    fp_pg=lambda x: x.fp_per_game.round(1),
    rank=lambda x: x.qb_rank,
)[["player", "rd", "pk", "quadrant", "rush_pg", "epa_db", "fp_pg", "rank"]]
show(out, 40)


# ---- 6. THE DEAD ZONE -------------------------------------------------------
# Act Three found 10-15 rushing yards per game is the worst band in the study
# (29.8% top-12, worse than QBs who do not run at all). Name them.
print("\n\n\n=========== PART 6: THE DEAD ZONE (10-15 rush yds/game) ===========")

dead = szn[(szn.rush_yd_pg >= 10) & (szn.rush_yd_pg < 15)]
print(f"  n = {len(dead)} seasons | top-12 rate = {100 * dead.is_qb1.mean():.1f}%")

out = dead.sort_values("fp_per_game", ascending=False).assign(
    player=lambda x: x.player_name,
    rush_pg=lambda x: x.rush_yd_pg.round(1),
    epa_db=lambda x: x.epa_per_db.round(3),
    fp_pg=lambda x: x.fp_per_game.round(1),
    rank=lambda x: x.qb_rank,
)[["player", "season", "rd", "pk", "rush_pg", "epa_db", "fp_pg", "rank"]]
show(out, 80)

print("\n[Which quarterbacks spent the MOST seasons in the dead zone?]")
show(dead.player_name.value_counts().rename("n").to_frame().reset_index(), 25)


# ---- WRITE CSVs -------------------------------------------------------------
szn[["player_name", "season", "round", "pick", "draft_day", "starts", "quadrant",
     "rush_yd_pg", "designed_yd_pg", "scramble_yd_pg", "epa_per_db", "any_a",
     "att_pg", "fp", "fp_per_game", "qb_rank", "is_qb1", "is_sfx"]].to_csv(
    out_path("qb_quadrants_by_season.csv"), index=False)

career_q.to_csv(out_path("qb_quadrants_by_career.csv"), index=False)
mig.to_csv(out_path("qb_quadrant_migration.csv"), index=False)

print(f"\n\nWrote three CSVs to {CONFIG['out_dir']}:")
for f in ("qb_quadrants_by_season.csv", "qb_quadrants_by_career.csv",
          "qb_quadrant_migration.csv"):
    print(f"  {os.path.basename(out_path(f))}")
