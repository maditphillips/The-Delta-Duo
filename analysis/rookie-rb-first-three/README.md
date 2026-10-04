# Do a rookie RB's first three games predict his career?

**Short answer:** a little, but almost all of what they seem to tell you, draft capital
already told you. Usage in the first three games carries a small amount of extra signal.
Efficiency in those games mostly doesn't repeat. A full rookie season is worth about nine
times as much as the first three games. Among first-round picks alone, the first three
games predict nothing (see `analyze_round1.py`).

Full output: `results.txt`, `results_round1.txt`, `results_groups.txt`, `results_ppg_groups.txt`, `results_cut30.txt` and `results_groups_r12.txt`. `analyze.py` also writes `report_data.json` (gitignored, like other analysis JSON).

## Running it

```sh
./fetch.sh            # nflverse weekly stats, players, snaps, slimmed pbp (~250 MB, gitignored)
python3 build.py      # -> rbs.csv  (one row per rookie RB)
python3 analyze.py    # all tables to stdout, -> report_data.json
python3 analyze_round1.py   # first-round-only version, split into pick groups
python3 choose_groups.py    # how many round-1 groups the data supports
python3 test_ppg_groups.py  # is the PPG drop across round-1 groups significant?
python3 test_cut30.py       # tests the data-chosen picks 1-29 vs 30-32 split
python3 choose_groups.py 2  # same grouping search over rounds 1-2 pooled
```

Needs pandas, numpy, scipy, scikit-learn, statsmodels, pyarrow.

## Method

- **Sample.** Every RB who debuted 2000-2020 and played 3+ regular-season games as a
  rookie: **503 backs**. 2021-2026 rookies are scored at the end but not used to fit.
  "Played" means he shows up in the nflverse weekly box score. A back drafted the year
  before his debut (injured rookie year, e.g. McGahee, Etienne) counts as a rookie in his
  debut season; players drafted at another position (e.g. Cordarrelle Patterson) are out.
  Supplemental-draft picks (Tony Hollings, 2003) are placed mid-round.
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
| Touches / game | 0.42 | 0.17 |
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
| Draft + age | 0.288 | 0.757 | 0.791 |
| First 3 games only | 0.148 | 0.712 | 0.726 |
| Draft + first-3 usage | 0.297 | 0.765 | 0.793 |
| Draft + first-3 efficiency | 0.299 | 0.766 | 0.788 |
| Draft + first 3 games (all) | **0.300** | **0.772** | 0.791 |
| Draft + full rookie season | **0.411** | **0.808** | 0.828 |
| Draft + full rookie + first 3 | 0.396 | 0.804 | 0.818 |

- First three games add **+0.013 R²** and **+0.015 AUC** over draft capital. Real (it
  holds in every CV repeat) but small. It adds nothing for predicting top-12 seasons.
- A full rookie season adds **+0.12 R²**, about 9x more.
- Once you have the full rookie season, the first three games add nothing.
- Gradient boosting did worse than linear (0.23), so there's no hidden nonlinear signal.
- On 2021-22 rookies (n=49, not used in fitting) the first three games didn't improve
  on draft capital (AUC 0.775 vs 0.775).

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
| Round 1 | 80% (n=5) | 86% (14) | 68% (28) |
| Rounds 2-3 | 45% (31) | 50% (40) | 59% (34) |
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

### 6. How many groups should round 1 have?

`choose_groups.py` scores 1-4 groups two ways.

- **Clustering on pick number alone** (elbow, silhouette, gap statistic) picks 2 groups
  (silhouette 0.71 for k=2, about 0.64 for k=3). It means little: picks run evenly from
  1 to 32, so the "clusters" are just equal slices of the round, chosen without looking
  at careers.
- **Groups chosen to explain careers.** For each k, every set of contiguous cut points
  is tried (6+ players per group) and the best is kept. Each k is scored by BIC and by
  cross-validation, with the cut points re-chosen inside each training fold.

  | Outcome | Best by BIC | Best by CV | Best cut |
  |---|---|---|---|
  | Year-2+ PPR points (total) | 2 groups | 2 groups | picks 1-29 vs 30-32 |
  | Year-2+ PPR points per game | 1 group | 1 group (tied with a straight line in pick) | none |
  | Any top-12 season | 1 group | 1 group | none |
  | Any top-24 season | 1 group | 1 group | none |

  3 groups never wins. For PPR points, the 2-group split doesn't land at the middle of
  the round. It cuts off the last three picks: 8 backs (Kevin Jones, Joseph Addai,
  Chris Wells, Jahvid Best, David Wilson, Doug Martin, Sony Michel, Clyde Edwards-Helaire)
  with a median 350 year-2+ PPR points vs 1,248 for picks 1-29. That is probably a cluster
  of busts more than a real cliff at pick 30. For points per game and for top-12 and top-24
  hit rates, splitting round 1 at all does worse out of sample than treating it as one
  group. PPG does drift down a little with pick (13.7 for picks 1-10, 12.0 for 11-24,
  10.3 for 25-32), but that drift is gradual and noisy (rho -0.27, p = 0.07), so a
  smooth trend describes it as well as groups do.

So 2 groups beats 3, but the honest answer is that the data barely supports splitting
round 1. The 1-16 / 17-32 and 1-10 / 11-24 / 25-32 splits above were set by hand, and
neither changes the main finding: early usage doesn't predict career within round 1.

### 7. Is the PPG drop across round-1 groups real?

Year-2+ PPR per game: picks 1-10 **13.7**, 11-24 **12.0**, 25-32 **10.3** (n = 16, 17, 14;
player-to-player sd about 4).

| Test | Question | p |
|---|---|---|
| ANOVA / permutation | Do the 3 groups differ at all? | 0.07 |
| Kruskal-Wallis (ranks) | Same, robust to outliers | 0.08 |
| Trend test | Steady decline across the 3 groups? (two-sided) | **0.02** |
| Spearman on raw pick | Decline with pick number, no groups? | 0.07 |
| 1-10 vs 11-24 | gap 1.7 PPG, 95% CI -0.8 to +4.4 | 0.23 (Holm 0.45) |
| 11-24 vs 25-32 | gap 1.7 PPG, 95% CI -0.9 to +4.2 | 0.22 (Holm 0.45) |
| 1-10 vs 25-32 | gap 3.4 PPG, 95% CI +0.6 to +6.3 | 0.03 (Holm 0.09) |

Borderline. There is some evidence that PPG slides as you go later in round 1 (the trend
test passes), but no single step between neighboring groups is distinguishable from
noise, and the top-vs-bottom gap doesn't survive correction for testing three pairs.
The group cut points were set by hand, which also makes the trend p a bit optimistic.
Group explains about 11% of PPG variation. With this sample, a 1-10 vs 25-32 gap would
need to be about 4.2 PPG to be detected reliably; the observed 3.4 is just under that.

Read it as: earlier first-round backs probably score a bit more per game, by roughly
1-2 PPG per tier, but the data can't pin down where (or whether) the steps are.

### 8. The data-chosen split: picks 1-29 vs 30-32

No back in the sample went 29th, so this is the same as 1-28 vs 30-32. Picks 30-32 are
8 backs: Kevin Jones, Jahvid Best, Joseph Addai, Chris Wells, Doug Martin, Sony Michel,
David Wilson, Clyde Edwards-Helaire.

The split was found by searching every possible cut, so a plain test overstates it. The
search-adjusted p repeats that whole search on shuffled data and asks how often the best
split of pure noise does as well.

| Outcome (yr 2+) | Picks 1-29 | Picks 30-32 | Plain p | Search-adjusted p |
|---|---|---|---|---|
| PPR per game | 12.5 | 10.1 | 0.19 | 0.64 |
| Total PPR (geometric mean) | 1,022 | 264 | 0.015 | 0.048 |
| Any top-12 season | 67% | 25% | 0.04 | 0.21 |
| Any top-24 season | 79% | 50% | 0.18 | 0.61 |

- For **PPG** this split means nothing, not even before adjusting.
- It only holds up for **total career PPR**, and only barely (0.048). Those 8 backs had
  short careers (Best, Wilson, Wells, Michel, Edwards-Helaire) more than low per-game
  output. With 8 players, that is as likely bad luck with injuries as anything about
  picks 30-32.
- Taking those 8 out, PPG barely moves with pick across picks 1-29 (rho -0.13, p = 0.44).
  Much of the 1-10 / 11-24 / 25-32 slide in section 7 comes from this one cluster.

### 9. Rounds 1-2 together: do picks 30-32 belong with round 2?

`choose_groups.py 2` reruns the grouping search on the 99 backs taken in rounds 1-2
(picks 2-63). Three round-2 backs who never played after year 1 are left out of the
PPG test only (PPG is undefined for them).

| Outcome (yr 2+) | Best model | Best 2-group cut, if forced |
|---|---|---|
| Total PPR points | smooth line in pick (no groups) | 1-29 vs 30-63 |
| PPR per game | smooth line in pick (no groups) | 1-48 vs 49-63 |
| Any top-24 season | smooth line in pick (no groups) | 1-49 vs 50-63 |
| Any top-12 season | 2 groups, tied with the line | 1-29 vs 30-63 |

Picks 30-32 next to their neighbors:

| Picks | n | PPG (mean) | Total PPR (median) | Top-12 | Top-24 |
|---|---|---|---|---|---|
| 1-29 | 39 | 12.5 | 1,248 | 67% | 79% |
| 30-32 | 8 | 10.1 | 350 | 25% | 50% |
| 33-48 | 20 | 11.3 | 664 | 35% | 75% |
| 49-64 | 32 | 7.9 | 349 | 28% | 47% |

- Whenever a split is forced on total PPR or top-12, the line falls right after pick 29,
  so picks 30-32 land with round 2, not round 1.
- On total PPR and top-12, picks 30-32 differ from 1-29 (p = 0.02, 0.05) and look like
  33-48 (p = 0.40, 1.00). On PPG they sit between the two and differ from neither.
- But across rounds 1-2 a smooth decline by pick beats any set of groups for PPG, total
  PPR and top-24. Value falls off gradually through the second round; there's no clear
  cliff. Picks 30-32 fit that slope better than they fit "round 1."

## Caveats

- Requires 3 rookie games, so backs who never got on the field are out of the sample.
  That slightly flatters how predictive "any first three games" are.
- Usage partly reflects the coaching staff's opinion, which is also what drives the
  draft pick. Some of the "signal" is the team telling you what it thinks.
- Fantasy points include TDs, which are noisy and situation-driven.
- 2026 rookie scores (end of `results.txt`) use only four weeks of 2026 data.
