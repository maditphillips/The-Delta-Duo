# Audit: "Consistency vs. Boom/Bust" (Michael Reedy, @MikeReedyFF)

Replication and stress-test of the Reedy Score consistency study using nflverse data.

## Setup

```bash
pip install pandas pyarrow
python fetch.py     # downloads nflverse pbp + weekly player stats, 2012-2025
python build.py     # -> hppr_weekly.parquet (half-PPR player-weeks, QB/RB/WR/TE, REG)
python run_all.py   # reproduces every number in REPORT.md
```

## Files

- `fetch.py` — pulls nflverse release assets (`stats_player`, `pbp`, `players`, `draft_picks`, NGS)
- `build.py` — half-PPR weekly table. Half-PPR = mean of nflverse `fantasy_points` and `fantasy_points_ppr`
- `lib.py` — qualifying-season table (mean, median, SD, CV, boom/bust/floor rates, skew)
- `sim.py` — matched-pair construction and head-to-head roster simulation
- `run_all.py` — the full battery
- `REPORT.md` — findings

## Reedy's sample, recovered

Filter is **≥14 games played in Weeks 1–17**, 2024–2025, QB/RB/WR/TE. That yields exactly
**368** qualifying player-seasons, matching his stated count.
- `league_and_gradient.py` — §5 matchup gradient and §9 full-league title simulation

## Headline

The conclusion holds (14/14 seasons, +1.17 pp), but the effect is half the advertised size,
driven by skew rather than variance, dilutes in deeper lineups, and mostly disappears when you
restrict yourself to information available *before* the season. See `REPORT.md`.
