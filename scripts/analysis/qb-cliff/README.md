# The Quarterback Cliff — quadrant rosters

Names for the Act Three 2×2: which quarterback seasons sit in each cell of
efficiency × rushing, who migrates between cells over a career, and who lives
in the 10–15 yards-per-game dead zone.

## Running it

```bash
pip install pandas pyarrow numpy
python3 qb_cliff_01_build_panel.py          # ~5 min, downloads 18 seasons of pbp
python3 qb_cliff_02_quadrant_rosters.py > ROSTERS.txt
```

`01` writes `cache/qb_season.parquet` (gitignored): every QB season 2008–2025
with starts, kneel-excluded rushing split into designed runs and scrambles,
EPA per dropback, ANY/A, fantasy points and league-wide fantasy rank, joined to
draft round and pick. Each season's play-by-play file is downloaded, aggregated
and deleted, so peak disk use stays around 25 MB.

`02` is a port of the original R script `qb_cliff_02_quadrant_rosters.R`. It
prints six parts and writes three CSVs to `outputs/`.

All three scripts take an era window. The per-season numbers — EPA per
dropback, rushing yards per game, fantasy rank — are computed within a season
and do not move with the window. What the window changes is the population the
medians are taken over, and so where the two splits fall:

```bash
QB_CLIFF_FROM=2017 python3 qb_cliff_02_quadrant_rosters.py > ROSTERS_2017_2025.txt
```

Outputs from a non-default window carry an era suffix, so both sets coexist.

`03` expands Part 4 of that script. Part 4 only reported a QB's first cell and
his last one; `03` prints every starter season he had and which quadrant it
landed in, so the whole path through the 2x2 is visible.

```bash
python3 qb_cliff_03_migration_detail.py > MIGRATION_DETAIL.txt
```

## Definitions

| Field | Definition |
|---|---|
| starter season | 10+ starts; a start is the passer with the most dropbacks for his team that game |
| rush_yd_pg | rushing yards per game played, **kneels excluded**, designed runs + scrambles |
| designed / scramble | `qb_scramble == 0` vs `== 1` on rush attempts |
| epa_per_db | mean EPA over dropbacks (pass attempts, sacks, scrambles), spikes and kneels dropped |
| fp | standard scoring: 4 pt pass TD, 1/25 pass yd, 1/10 rush yd, 6 pt rush TD, −2 INT, −2 fumble lost, 2 pt conversions |
| qb_rank | rank by total fantasy points among all QBs that season, league-wide |
| is_qb1 / is_sfx | qb_rank ≤ 12 / ≤ 24 |

Both quadrant splits are the **median of the panel**, computed fresh at run
time rather than hardcoded, and printed at the top of the output.

## Reconciliation with the published Act Three figures

The R pipeline that produced `src/data/qb.ts` is not in this repo, so the panel
is rebuilt from nflverse here. It lands on the same numbers:

| | published | rebuilt |
|---|---|---|
| starter seasons | 504 | 503 |
| median EPA/dropback | 0.0674 | 0.0676 |
| 2×2 counts | 121 / 131 / 131 / 121 | 120 / 131 / 131 / 121 |
| 2×2 top-12 rate | 76.0 / 66.4 / 19.8 / 9.1 | 76.7 / 66.4 / 20.6 / 8.3 |
| 2×2 median FP/G | 19.3 / 17.5 / 15.0 / 13.2 | 19.3 / 17.5 / 14.8 / 13.2 |
| dead zone (10–15) | n = 67, 29.8% | n = 67, 29.9% |
| top-12 seasons | 216 | 216 |

One season of difference at the 10-start bar, and the rushing split lands at
10.36 yds/game against the R pipeline's 10.47 — a slightly different per-game
denominator, not a different definition. Everything downstream reconciles.

## The 2008-2025 splits understate rushing

Rushing rose sharply across the study window; passing efficiency did not.

| split | 2008-2016 | 2017-2025 |
|---|---|---|
| median rushing yds/game | 7.67 | 14.18 |
| median EPA/dropback | 0.0693 | 0.0663 |

Pooling all 18 seasons puts the rushing bar at 10.36, which is above the old
era's median and well below the new one. Re-cutting on 2017-2025 alone widens
the 2x2 rather than flattening it:

| quadrant | top-12, 2008-2025 | top-12, 2017-2025 |
|---|---|---|
| Efficient + legs | 76.7% | 83.9% |
| Efficient + no legs | 66.4% | 51.5% |
| Inefficient + legs | 20.6% | 22.7% |
| Inefficient + no legs | 8.3% | 11.3% |

The gap between the two efficient cells goes from 10.3 points to 32.4. Among
efficient quarterbacks in the modern game, legs are close to the whole story.

## Outputs

- `ROSTERS.txt` — the full printed run
- `outputs/qb_quadrants_by_season.csv` — 503 starter seasons, one row each
- `outputs/qb_quadrants_by_career.csv` — career quadrant, 3+ starter seasons
- `outputs/qb_quadrant_migration.csv` — first cell → last cell per QB
- `QUADRANT_PLAYERS.txt`, `outputs/qb_quadrants_all_players.csv` — all 123 QBs placed by career median
- `MIGRATION_DETAIL.txt` — season-by-season timeline per QB, grouped by career cell
- `outputs/qb_quadrant_by_season_long.csv` — one row per QB season, with his career cell alongside
- `outputs/qb_quadrant_grid.csv` — 123 QBs down the side, 2008–2025 across the top, quadrant number in each cell
