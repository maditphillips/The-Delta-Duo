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

## Outputs

- `ROSTERS.txt` — the full printed run
- `outputs/qb_quadrants_by_season.csv` — 503 starter seasons, one row each
- `outputs/qb_quadrants_by_career.csv` — career quadrant, 3+ starter seasons
- `outputs/qb_quadrant_migration.csv` — first cell → last cell per QB
