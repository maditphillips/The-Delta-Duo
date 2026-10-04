# Do a rookie RB's first three games predict his career?

**Short answer:** a little, but almost all of what they seem to tell you, draft capital
already told you. Usage in the first three games carries a small amount of extra signal.
Efficiency in those games mostly doesn't repeat. A full rookie season is worth about eight
times as much as the first three games. Among first-round picks alone, the first three
games predict nothing (see `analyze_round1.py`).

Full output: `results.txt` and `results_round1.txt`. `analyze.py` also writes `report_data.json` (gitignored, like other analysis JSON).

## Running it

```sh
./fetch.sh            # nflverse weekly stats, players, snaps, slimmed pbp (~250 MB, gitignored)
python3 build.py      # -> rbs.csv  (one row per rookie RB)
python3 analyze.py    # all tables to stdout, -> report_data.json
python3 analyze_round1.py   # first-round-only version, split into pick groups
```

Needs pandas, numpy, scipy, scikit-learn, statsmodels, pyarrow.

## Method

- **Sample.** Every RB who debuted 2000-2020 and played 3+ regular-season games as a
  rookie: **503 backs**. 2021-2026 rookies are scored at the end but not used to fit.
  "Played" means he shows up in the nflverse weekly box score. A back drafted the year
  before his debut (injured rookie year, e.g. McGahee, Etienne) counts as a rookie in his
  debut season; players drafted at another position (e.g. Cordarrelle Patterson) are out.
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
| Scrimmage yds / game | 0.45 | 0.23 |
| PPR pts / game | 0.44 | 0.23 |
| Touches / game | 0.42 | 0.18 |
| Carry share | 0.41 | 0.16 |
| Receptions / game | 0.32 | 0.15 |
| Yards / carry (10+ car.) | 0.23 | 0.25 |
| Rush EPA / carry (10+ car.) | 0.20 | 0.25 |
| Rush success rate (10+ car.) | 0.18 | 0.19 |
| Yards / target (4+ tgt.) | -0.02 | -0.06 |
| *Draft pick, for reference* | *0.54* | |

Usage roughly halves once you account for where he was drafted. Efficiency, oddly,
holds its partial correlation: a Day 3 back who runs well early does a bit better
than his draft slot suggests.

### 2. Out of sample, the first three games add very little

| Model | CV R² (log PPR, yr 2+) | AUC: any top-24 season | AUC: any top-12 |
|---|---|---|---|
| Draft + age | 0.276 | 0.757 | 0.790 |
| First 3 games only | 0.148 | 0.712 | 0.726 |
| Draft + first-3 usage | 0.291 | 0.764 | 0.793 |
| Draft + first-3 efficiency | 0.286 | 0.764 | 0.786 |
| Draft + first 3 games (all) | **0.293** | **0.771** | 0.789 |
| Draft + full rookie season | **0.409** | **0.806** | 0.827 |
| Draft + full rookie + first 3 | 0.394 | 0.802 | 0.817 |

- First three games add **+0.017 R²** and **+0.014 AUC** over draft capital. Real (it
  holds in every CV repeat) but small. It adds nothing for predicting top-12 seasons.
- A full rookie season adds **+0.13 R²**, about 8x more.
- Once you have the full rookie season, the first three games add nothing.
- Gradient boosting did worse than linear (0.23), so there's no hidden nonlinear signal.
- On 2021-22 rookies (n=49, not used in fitting) the first three games didn't improve
  on draft capital (AUC 0.769 vs 0.778).

### 3. Usage sticks. Efficiency doesn't.

Correlation between a first-3-game metric and the same metric for the rest of his
career (backs with 50+ later carries):

| Metric | First 3 games | Full rookie year |
|---|---|---|
| Target share | 0.59 | 0.68 |
| Carry share | 0.50 | 0.62 |
| Carries / game | 0.47 | 0.63 |
| Receptions / game | 0.47 | 0.62 |
| PPR pts / game | 0.45 | 0.63 |
| Rush success rate | 0.17 | 0.48 |
| Rush EPA / carry | 0.12 | 0.44 |
| Yards / carry | 0.10 | 0.49 |

Role shows up immediately. Efficiency on ~15-40 carries is close to noise; you need
about a full season before it means much.

### 4. Where it actually matters: late picks

Hit rate = had at least one top-24 PPR season in year 2+. Base rate 29%.

| Draft tier | First-3 carry share <15% | 15-35% | 35%+ |
|---|---|---|---|
| Round 1 | 80% (n=5) | 80% (15) | 68% (28) |
| Rounds 2-3 | 45% (31) | 51% (39) | 59% (34) |
| Rounds 4-7 | 17% (118) | 22% (51) | 39% (18) |
| Undrafted | 10% (117) | 12% (33) | 29% (14) |

For first-rounders, early usage tells you nothing; they hit either way. For Day 3 and
undrafted backs, a 35%+ carry share out of the gate roughly doubles the hit rate.
Small cells, so treat as directional.

Same idea with efficiency (backs with 15+ first-3 carries, split at median success rate):
Rd 1-3 67% vs 57%; Rd 4+/UDFA 27% vs 20%.

### 5. First-round picks only: the first three games tell you nothing

47 first-round RBs (2000-2020). 74% had a top-24 season in year 2+, 60% a top-12.

- **No first-3 metric correlates meaningfully with career.** Usage: rho +0.07 to +0.18,
  every 95% interval spans zero. Efficiency (YPC, EPA, success rate on 10+ carries) is a
  bit higher, +0.25, p about 0.1. Suggestive, not established.
- **Out of sample, nothing beats a coin flip.** Pick + age alone explains ~0% of
  year-2+ PPR within round 1 (CV R² -0.01). Adding first-3 usage or PPR/g makes it
  *worse*. Adding YPC or success rate helps a sliver (+0.02-0.04 R²), still near zero.
- **Where in round 1 matters more than the first 3 games.**

  | Group | n | Top-24 season | Top-12 season | Median yr-2+ PPR |
  |---|---|---|---|---|
  | Picks 1-10 | 16 | 88% | 75% | 1389 |
  | Picks 11-24 | 17 | 76% | 65% | 1189 |
  | Picks 25-32 | 14 | 57% | 36% | 537 |
  | Picks 1-16 | 23 | 83% | 70% | 1189 |
  | Picks 17-32 | 24 | 67% | 50% | 641 |

- **Within each group, early usage still doesn't separate hits from misses.** Splitting
  each group at its own median first-3 carry share (share of team carries; "more" =
  at or above the median):

  | Group | Split at | More early carries: top-24 / top-12 | Fewer: top-24 / top-12 |
  |---|---|---|---|
  | Picks 1-10 (n=16) | 68% | 75% / 63% (n=8) | 100% / 88% (n=8) |
  | Picks 11-24 (n=17) | 39% | 67% / 56% (n=9) | 88% / 75% (n=8) |
  | Picks 25-32 (n=14) | 42% | 57% / 29% (n=7) | 57% / 43% (n=7) |
  | Picks 1-16 (n=23) | 52% | 83% / 75% (n=12) | 82% / 64% (n=11) |
  | Picks 17-32 (n=24) | 32% | 58% / 42% (n=12) | 75% / 58% (n=12) |

  Late firsts who got the ball right
    away did slightly *worse*: Jahvid Best, Sony Michel, Doug Martin, Clyde Edwards-Helaire.
    Several who barely played early became stars: Steven Jackson, Larry Johnson,
    Deuce McAllister, Rashard Mendenhall, DeAngelo Williams.
- **The groups don't differ from each other either.** Tests of whether the
  first-3-to-career slope differs by group: p = 0.80 (two groups, carry share), 0.13
  (two groups, PPR/g), 0.67 and 0.94 (three groups). The one hint, PPR/g mattering a bit
  for picks 1-16 and not 17-32, isn't significant.
- With 14-24 players per group, only a large effect would show up. "No evidence of an
  effect" here is not the same as "proven no effect," but there is nothing to act on.

## Caveats

- Requires 3 rookie games, so backs who never got on the field are out of the sample.
  That slightly flatters how predictive "any first three games" are.
- Usage partly reflects the coaching staff's opinion, which is also what drives the
  draft pick. Some of the "signal" is the team telling you what it thinks.
- Fantasy points include TDs, which are noisy and situation-driven.
- 2026 rookie scores (end of `results.txt`) use only four weeks of 2026 data.
