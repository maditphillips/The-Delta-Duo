# Do a rookie RB's first three games predict his career?

**Short answer:** a little, but almost all of what they seem to tell you, draft capital
already told you. Usage in the first three games carries a small amount of extra signal.
Efficiency in those games mostly doesn't repeat. A full rookie season is worth about five
times as much as the first three games.

Full output: `results.txt`. `analyze.py` also writes `report_data.json` (gitignored, like other analysis JSON).

## Running it

```sh
./fetch.sh            # nflverse weekly stats, players, snaps, slimmed pbp (~250 MB, gitignored)
python3 build.py      # -> rbs.csv  (one row per rookie RB)
python3 analyze.py    # all tables to stdout, -> report_data.json
```

Needs pandas, numpy, scipy, scikit-learn, statsmodels, pyarrow.

## Method

- **Sample.** Every RB who debuted 2000-2020 and played 3+ regular-season games as a
  rookie: **484 backs**. 2021-2026 rookies are scored at the end but not used to fit.
  "Played" means he shows up in the nflverse weekly box score.
- **First three games.** His first three rookie-year appearances.
  - Usage: carries/game, carry share of team rushes, receptions/game, reception share,
    target share (not available 2003-2008: nflverse has no receiver on incompletions
    those years), snap share (2013+ only).
  - Efficiency: yards/carry, rushing EPA/carry, rushing success rate (from pbp),
    first downs/carry, yards/target.
  - Production: PPR points/game, scrimmage yards/game.
- **Career outcome.** Measured **from year 2 on**, so it never overlaps the games used to
  predict it: total PPR points, whether he ever had a top-24 or top-12 PPR RB season,
  and games played.
- **Control.** Draft pick (log; undrafted = 260 plus a flag) and age at the rookie
  season. The question is not "do early stats correlate with careers" (they do,
  because first-round picks get the ball) but "do they tell you anything the draft
  didn't."
- **Small-sample efficiency.** For the models, efficiency rates are shrunk toward the
  league mean with a prior of 30 carries. Raw efficiency correlations only use backs with
  10+ carries over the three games.
- **Validation.** 20x repeated 10-fold cross-validation; every gain is out-of-sample
  against the draft-only model on the same folds.

## Results

### 1. Raw correlations look strong. Most of it is draft capital.

Spearman correlation with year-2+ PPR points (partial = after removing draft pick and age):

| First-3 metric | rho | partial rho |
|---|---|---|
| Scrimmage yds / game | 0.48 | 0.26 |
| PPR pts / game | 0.46 | 0.26 |
| Touches / game | 0.45 | 0.20 |
| Carry share | 0.44 | 0.19 |
| Receptions / game | 0.34 | 0.17 |
| Yards / carry (10+ car.) | 0.24 | 0.25 |
| Rush EPA / carry (10+ car.) | 0.19 | 0.24 |
| Rush success rate (10+ car.) | 0.19 | 0.20 |
| Yards / target (4+ tgt.) | 0.05 | 0.02 |
| *Draft pick, for reference* | *0.56* | |

Usage roughly halves once you account for where he was drafted. Efficiency, oddly,
holds its partial correlation: a Day 3 back who runs well early does a bit better
than his draft slot suggests.

### 2. Out of sample, the first three games add very little

| Model | CV R² (log PPR, yr 2+) | AUC: any top-24 season | AUC: any top-12 |
|---|---|---|---|
| Draft + age | 0.300 | 0.762 | 0.801 |
| First 3 games only | 0.179 | 0.717 | 0.736 |
| Draft + first-3 usage | 0.324 | 0.772 | 0.801 |
| Draft + first-3 efficiency | 0.309 | 0.769 | 0.796 |
| Draft + first 3 games (all) | **0.327** | **0.778** | 0.798 |
| Draft + full rookie season | **0.431** | **0.810** | 0.828 |
| Draft + full rookie + first 3 | 0.417 | 0.804 | 0.817 |

- First three games add **+0.027 R²** and **+0.016 AUC** over draft capital. Real (it
  holds in every CV repeat) but small. It adds nothing for predicting top-12 seasons.
- A full rookie season adds **+0.13 R²**, about 5x more.
- Once you have the full rookie season, the first three games add nothing.
- Gradient boosting did worse than linear (0.27), so there's no hidden nonlinear signal.
- On 2021-22 rookies (n=48, not used in fitting) the first three games didn't improve
  on draft capital (AUC 0.758 vs 0.765).

### 3. Usage sticks. Efficiency doesn't.

Correlation between a first-3-game metric and the same metric for the rest of his
career (backs with 50+ later carries):

| Metric | First 3 games | Full rookie year |
|---|---|---|
| Target share | 0.60 | 0.68 |
| Carry share | 0.50 | 0.62 |
| Carries / game | 0.48 | 0.62 |
| Receptions / game | 0.47 | 0.63 |
| PPR pts / game | 0.46 | 0.62 |
| Rush success rate | 0.16 | 0.48 |
| Rush EPA / carry | 0.12 | 0.46 |
| Yards / carry | 0.10 | 0.47 |

Role shows up immediately. Efficiency on ~15-40 carries is close to noise; you need
about a full season before it means much.

### 4. Where it actually matters: late picks

Hit rate = had at least one top-24 PPR season in year 2+. Base rate 29%.

| Draft tier | First-3 carry share <15% | 15-35% | 35%+ |
|---|---|---|---|
| Round 1 | 83% (n=6) | 79% (14) | 68% (28) |
| Rounds 2-3 | 46% (28) | 53% (38) | 64% (28) |
| Rounds 4-7 | 17% (113) | 22% (50) | 40% (15) |
| Undrafted | 10% (117) | 12% (33) | 29% (14) |

For first-rounders, early usage tells you nothing; they hit either way. For Day 3 and
undrafted backs, a 35%+ carry share out of the gate roughly doubles the hit rate.
Small cells, so treat as directional.

Same idea with efficiency (backs with 15+ first-3 carries, split at median success rate):
Rd 1-3 70% vs 58%; Rd 4+/UDFA 29% vs 18%.

## Caveats

- Requires 3 rookie games, so backs who never got on the field are out of the sample.
  That slightly flatters how predictive "any first three games" are.
- Usage partly reflects the coaching staff's opinion, which is also what drives the
  draft pick. Some of the "signal" is the team telling you what it thinks.
- Fantasy points include TDs, which are noisy and situation-driven.
- 2026 rookie scores (end of `results.txt`) use only four weeks of 2026 data.
