# How predictive is NFL Week 1?

Question under test: after one game, what do you actually know? Both for normal
football analysis (is a 1-0 team better than it was in August?) and for fantasy
(does a Week 1 line tell you anything about the rest of the season?).

The specific things asked for: Week 1 usage for running backs, targets for wide
receivers, yards per carry, snap counts for RBs and WRs, completion percentage
for quarterbacks, and how well Week 1 fantasy points predict future fantasy
points.

## Running it

```bash
pip install pandas pyarrow numpy
python3 fetch.py          # nflverse, one season file at a time
python3 analyze.py        # runs all four modules, then writes FINDINGS.txt
```

Or run a module on its own: `python3 predictiveness.py > PREDICTIVENESS.txt`.
`analyze.py --skip-run` rebuilds `FINDINGS.txt` from the `out_*.csv` files
without recomputing.

## Data

From nflverse (`fetch.py`, all files gitignored):

| file | source | span |
|---|---|---|
| `player_week.parquet` | `stats_player` release | 1999– |
| `team_week.parquet` | `stats_team` release | 1999– |
| `snaps.parquet` | `snap_counts` release | 2013– |
| `games.csv` | `nflverse/nfldata` | 1999– |
| `players.parquet` | `players` release, gsis↔pfr crosswalk | — |

Analysis runs on complete regular seasons, **1999–2025**. Snap share only exists
from 2013 (the 2012 nflverse file is empty), so every snap number uses that
shorter window and says so. Half-PPR is derived (`PPR − 0.5 × receptions`); it
is not shipped in nflverse.

## Method

The unit is a player-season, with three views of every metric: `w1_` (Week 1),
`ros_` (weeks 2 onward), `prior_` (the player's previous full regular season).

**The rest-of-season target always excludes Week 1.** For a counting stat `ros_` is
the per-game mean over weeks 2 onward; for a share metric it is the mean of the
weekly shares over those weeks. It is *not* the end-of-season cumulative figure —
Week 1 sits inside that, so part of any correlation with it would be definitional
overlap rather than prediction. `snapshare_targets.py` quantifies the difference:
for snap share, the pooled rest-of-season share is interchangeable with the mean of
weekly shares (r agrees to within 0.001), while the whole-season cumulative version
runs about 0.04 higher at RB/WR/TE and 0.11 higher at QB purely from that overlap.

Correlations are also sensitive to the Week 1 gate, because gating on production
restricts the range of the predictor. Snap share at RB correlates 0.664 with the
rest of the season inside the main sample (Week 1 carries >= 6) and 0.744 across
every back who played at least 10% of snaps. Neither is wrong; they answer
different questions, and the gate is stated with every table.
Volume metrics are per game; rate metrics are pooled (sum ÷ sum) and require a
minimum rest-of-season denominator, so a 3-carry sample cannot masquerade as a
yards-per-carry.

The point of the design is that a raw `r` between Week 1 and the rest of the
season is not an answer on its own. A big number could just mean good players
are good — something you knew in August. So every metric is measured four ways:

| Test | Question it settles |
|---|---|
| `r(W1 → ROS)` | the correlation everyone quotes |
| partial F on the Week 1 term | with n in the hundreds nearly every `r` clears p&nbsp;<&nbsp;0.05, so significance separates almost nothing here; effect size does. `significance.py` reports both |
| `r(prior → ROS)` and ΔR² | what Week 1 adds *on top of* last season |
| `r(mid-season week → rest)` | is Week 1 special, or is one game just one game? |
| signal share and λ | how much of a single game's spread is real, and how many games until a metric is half signal |

The last one comes from a one-way random-effects split of game-to-game variance
into between-player and within-player parts. With λ = var_within / var_between,
a k-game sample has reliability k/(k+λ). Reliability at k=1 is the share of one
game's spread that is signal; λ is the games needed to reach 0.5. Caveat: this
holds a player's true level fixed inside a season, so a genuine mid-season role
change lands in the noise bucket, which makes λ an upper bound rather than a
floor.

Two sample conventions worth knowing, because they pull in opposite directions:

- **Conditional on playing** (the default): a player needs 4+ games after Week 1
  to enter the sample. This answers "if he stays on the field, what is he?" and
  strips out injury risk.
- **Unconditional**: missed weeks count as zero, which is what a fantasy roster
  actually feels. Reported alongside in `PREDICTIVENESS.txt`; it lowers every
  volume correlation by roughly 0.03–0.11.

Anything that looked like a clean story but was not supported by the numbers was
cut. In particular: EPA per play does **not** beat the Week 1 scoreboard at
predicting the rest of the season, at any sample size tested here.

## Files

| module | writes | what is in it |
|---|---|---|
| `predictiveness.py` | `PREDICTIVENESS.txt` | the core per-metric table, all four tests, per position |
| `stability.py` | `STABILITY.txt` | signal share, stabilisation points, and the cumulative weeks-1..k curve |
| `fantasy.py` | `FANTASY.txt` | best Week 1 signal for fantasy, rank transitions, the panic table, how much of a surprise is real, waiver spikes |
| `team.py` | `TEAM.txt` | 1-0 vs 0-1, margin and EPA as predictors, blowouts, the betting-market test |
| `band_cells.py` | `BAND_CELLS.txt` | one conditional cell in detail -- RBs who opened at 45-60% of snaps, split by whether their Week 1 YPC cleared 5.0 -- with confidence intervals on each group and on the difference |
| `snapshare_targets.py` | `SNAPSHARE.txt` | the three rest-of-season snap-share targets compared, plus fitted line, residual spread and observed outcome bands for a given Week 1 snap share |
| `significance.py` | `SIGNIFICANCE.txt` | p-values on r, the partial F on the Week 1 term next to a prior-season baseline, BH q-values across all 55 pairs, and each of weeks 1-9 correlated on its own |
| `analyze.py` | `FINDINGS.txt` | headline numbers, read back out of the `out_*.csv` files |
| `make_report_data.py` | `report_data.json` | the study's figures collapsed into one JSON |
| `report.py` | `week1-report.html` | a standalone HTML write-up of the study |

`week1-report.html` is a **self-contained offline file**, not a site page: nothing in
`src/` imports it and no route serves it. It borrows the house style from
`src/app/globals.css` so it reads like the rest of the Lab, and every figure in it
comes from `report_data.json`, so no number is typed by hand. Regenerate with
`python3 make_report_data.py && python3 report.py`.

## Re-running it on a live Week 1

`fetch.py` pulls the current season too. Once Week 1 of a season is complete,
bump `LAST_SEASON` in `common.py` to include it and the same panel logic will
score the new week against the historical baselines.
