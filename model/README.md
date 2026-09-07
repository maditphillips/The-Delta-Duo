# Weekly Rankings Model

Four position models — QB, RB, WR, TE — that project week 1 of 2026 using only
information that existed before kickoff, and rank players inside each position
for eight published lists:

| Position | Lists |
|---|---|
| QB | 4-point passing TD, 6-point passing TD |
| RB | PPR, half-PPR |
| WR | PPR, half-PPR |
| TE | PPR, half-PPR |

Output lands in `outputs/2026/week-01/`. Nothing here writes to `data/weekly/`
yet — the site pipeline is untouched until the rankings earn it.

---

## 1. The idea

The three offseason studies in `src/data/` all point the same direction:

- **WR (*Two Doors*)** — 97% of the per-snap production gap between Round 1 and
  Day 3 receivers is *being targeted more often while on the field*, not doing
  more with each target.
- **RB (*The Cliff*)** — among backs who clear 50 carries, not one efficiency
  comparison is significant. The only separator is volume: 16.3 touches a game
  versus 7.2.
- **QB (*The Cliff*)** — 104 quarterbacks never reached ten starts; exactly zero
  of them ever finished top-24.

So the model spends its effort on **opportunity** and treats **efficiency** as a
lightly-held secondary term that gets shrunk hard. Most public fantasy models do
the reverse and get eaten by touchdown noise.

Concretely, that shows up in three design choices:

1. **A hurdle structure.** Roughly half of every rankable week-1 pool scores
   nothing — the backup who never sees the field. Mixing those rows in with
   starters produces a model that mostly predicts *whether a man plays*. So the
   two questions are modelled separately: `P(plays a real role)` on the whole
   pool, and `E[points | plays]` on players only. The projection is the product.
2. **Expected volume is handed to the learner directly.** A player's week is his
   share of his team's work times how much work his team is projected to have.
   The product (`expected_targets`, `expected_carries`, `expected_gl_carries`,
   `naive_points_ppr`) is computed explicitly rather than left for a
   thousand-row gradient booster to discover.
3. **Touchdown equity comes from field position, never from last year's
   touchdown count** — the noisiest number in fantasy. `expected_rec_td` is a
   function of projected red-zone targets; `expected_rush_td` of projected
   goal-line carries.

---

## 2. Does a play-caller's style travel? (measured, not assumed)

This was the core question behind the request, so it is answered empirically
rather than by labelling offences "Shanahan tree" or "Air Raid". Labels do not
regress and cannot be blended. A **vector** can.

Every team-season gets a 22-dimension offensive fingerprint and a 14-dimension
defensive one, z-scored within season, built from play-by-play 2006–2025 plus
FTN charting 2022–2025 (motion, play-action, RPO, screens, box counts,
blitzers). The fingerprint then attaches to the *person* calling plays, not the
team.

Two regressions are fitted per dimension — separately, because when the same
person stays, "the team's last year" and "the caller's history" are the same
observation:

```
continuity      y_t  ~  a  * y_{t-1}
caller change   y_t  ~  b1 * y_{t-1}  +  b2 * caller_prior_history
```

`b2` is the carryover weight. Results (`outputs/carryover/`, n = 37 regime
changes with prior history):

| Dimension | team's own last year (b1) | incoming caller's history (b2) | reading |
|---|---|---|---|
| early-down pass rate | 0.24 | **0.81** | the person brings it |
| neutral pass rate | 0.27 | **0.79** | the person brings it |
| no-huddle rate | 0.01 | **0.57** | almost entirely the person |
| plays per game | 0.34 | **0.56** | mostly the person |
| RB target share | 0.47 | 0.45 | split evenly |
| PROE | 0.31 | 0.38 | mostly the person |
| aDOT | **0.49** | 0.07 | the roster owns it |
| deep rate | **0.48** | −0.06 | the roster owns it |
| QB designed-run rate | **1.20** | −0.00 | entirely the quarterback |
| TE / WR target share | 0.38 / 0.36 | 0.12 / 0.11 | mostly the roster |

**How to read it:** pass-rate identity, tempo and no-huddle travel with the
play-caller. Downfield aggressiveness does not — aDOT and deep rate belong to
the quarterback and the receivers, not the coordinator. Designed quarterback
runs are a pure quarterback trait; a new play-caller changes them essentially
not at all.

On defence the same test is much weaker across the board (best change-regime
R² is 0.20, for aDOT allowed) — defensive identity travels far less cleanly
than offensive identity, which is itself a useful thing to know before leaning
on "new DC" narratives.

A first-time play-caller with no history gets shrunk to the league mean rather
than assigned a guess, and carries an explicit low-confidence flag.

### Does the scheme layer actually improve rankings? Mostly no.

The coefficients above measure how well a play-caller's tendencies predict his
next team's tendencies. That is a fact about **scheme**, and it does not
automatically mean the layer improves **player rankings**. Tested by ablation —
same backtest, same seasons, scheme projection and regime features removed:

| Position | Δ Spearman from keeping the play-caller layer | seasons it helped |
|---|---|---|
| TE | **+0.090** | 5 of 7 |
| QB | +0.000 | 3 of 7 |
| RB | −0.001 | 5 of 7 |
| WR | −0.014 | 2 of 7 |
| **All** | **+0.019** | **15 of 28** |

Paired across 28 position-seasons: t = 1.44, p = 0.16; Wilcoxon p = 0.55. That
is indistinguishable from noise. Only tight end shows a consistent gain, and
that is one position on seven observations.

**So the honest position is:** play-caller tendencies demonstrably travel, but
in this build that knowledge does not translate into better weekly rankings
except possibly at TE. Two readings are both live — either team-level scheme is
largely already priced into a player's own prior-season usage, or the
head-coach proxy is too blunt to carry the signal. Filling
`config/playcallers.csv` with real coordinators is the experiment that
separates them.

### The curated input, and what it could and could not do

**No public dataset lists NFL play-callers.** What *is* verified data is the
head coach of every team-season, which nflverse carries in `schedules`. So the
module keeps the two apart:

- **Verified backbone** — head coach per team-season, straight from nflverse.
  For 2026 this identifies seven head-coaching changes: BAL (Jesse Minter),
  CLE (Todd Monken), LV (Klint Kubliak), MIA (Jeff Hafley), NYG (John Harbaugh),
  PIT (Mike McCarthy), TEN (Robert Saleh).
- **Curated overlay** — `config/playcallers.csv`, one row per team-season with
  blank `off_playcaller` / `def_playcaller` columns. When a row is filled in it
  wins; when it is blank the head coach stands in and the row is flagged
  `head_coach_proxy`.

`config/coordinators_2026.csv` now holds a user-supplied 2026 coordinator list
for all 32 teams, written into the overlay as the 2026 play-callers. Two things
it does not fix, both structural:

1. **It is one season.** The backtest runs 2019–2025 and needs *historical*
   play-caller assignments to change anything. A 2026-only list cannot move a
   single backtest number, so it cannot be used to test whether the layer helps.
2. **The fingerprint table only knows head coaches**, so a 2026 coordinator has
   prior history only if he was previously a head coach. After a recency guard
   (below), that is **2 of 32** on offence — Mike McDaniel at LAC and Brian
   Daboll at TEN — and **3 of 32** on defence: Jonathan Gannon at GB, Raheem
   Morris at SF, Todd Bowles at TB. Everyone else falls back to the league mean.

Two bugs the list exposed, both fixed:

- **Stale name collisions.** Matching a coordinator by name across the whole
  table pulled in ancient head-coaching stints — Steve Spagnuolo's 2009–11 Rams
  were about to become the prior for Kansas City's 2026 defence. Recency weights
  decayed those seasons but the averaging renormalised them back to full
  strength. Histories whose total unnormalised weight falls below a floor are
  now dropped entirely.
- **False play-caller turnover.** With only 2026 curated and 2025 still on
  head-coach names, every team read as a play-caller change, because a
  coordinator's name never equals last year's head coach's name. Continuity is
  now compared like with like: play-caller against play-caller where both
  seasons are curated, head coach against head coach everywhere else.

The consequence of that second fix is worth stating plainly: **a team that kept
its head coach but changed coordinator is currently not flagged as a change at
all.** Only the seven head-coaching changes are. Fixing that needs the 2025
coordinator list, and testing the layer at all needs 2016–2025.

The overlay previously shipped empty, and that was deliberate. This sandbox can only reach
GitHub, so coordinator names could not be checked against a primary source, and
half-verified names in a data file are worse than an honest blank. Filling that
CSV is the single highest-leverage manual input to the whole model, and it needs
no code change — drop names in, re-run `python -m dd.cli carryover`.

Until it is filled, every carryover number above is measured on **head-coach**
changes, which misses standalone coordinator changes. Expect the true carryover
coefficients to move once real play-caller data goes in.

---

## 3. Features

Roughly 90 per position, all point-in-time.

**Market** — implied team total, spread, total, home, dome, rest, divisional.
The implied team total is the strongest free weekly signal in existence and it
is public days before kickoff.

**Scheme (projected)** — the carryover model's 2026 projection for the team's
offence, and the opponent's defence, in all fingerprint dimensions.

**Scheme (measured)** — the team's actual prior-season rates, so the model can
weigh continuity against projection itself.

**Regime** — play-caller continuity, head-coach continuity, how many prior
seasons of history the incoming caller has.

**Offseason churn** — vacated target share, rush share, red-zone target share,
goal-line carry share and air-yards share: last season's work whose owner is no
longer on the roster. Fully observable before week 1 and the number that
actually moves a depth chart.

**Player role** — 2026 depth-chart rank (pulled live, timestamped
`2026-09-07T13:13:25Z`), team change, rookie flag, draft pick, experience, age,
week-1 injury report.

**Prior usage, empirically shrunk** — target share, rush share, air-yards share,
WOPR, snap share, red-zone target share, third-down target share, goal-line
carry share, targets per unit of snap share (the *Two Doors* second gate), plus
two-seasons-back versions.

**Prior efficiency, shrunk harder** — yards per target, catch rate, aDOT, YAC
per reception, yards per carry, YPA, sack rate.

**Opponent** — prior-season defensive EPA split pass/run, pass-funnel index,
success rate, sack rate, YPA and YPC allowed, red-zone TD rate allowed, plus the
projected defensive scheme vector.

### Shrinkage

Shares go through a method-of-moments beta-binomial: prior strength `k` is set
so observed between-player variance matches binomial sampling noise plus true
spread. A player with 20 targets ends up mostly prior; one with 150 ends up
mostly himself. This is what stops a four-game 2025 sample being treated like a
seventeen-game one.

---

## 4. Estimators

Week 1 gives roughly a thousand usable rows per position across nine seasons.
That budget does not support anything deep, so:

| Stage | Estimator |
|---|---|
| `P(plays)` | `HistGradientBoostingClassifier`, depth 3, early stopping |
| `E[points \| plays]` | ridge (CV-tuned α) **or** depth-3 GBM — chosen per position by backtest |
| Distribution | nine quantile GBMs on the played-only subset |
| Full predictive law | mixture: point mass at 0 with weight `1−P`, conditional quantiles with weight `P` |

The learner choice is made on the most recent *training* season only, so the
test season never influences which model is used. Across the backtest, GBM wins
for QB, ridge and GBM split for RB/WR/TE.

`P(top-12)` comes from 4,000 draws of the mixture. **Players are sampled
independently**, which understates real team-mate correlation — one hot offence
lifts everyone in it — so treat those probabilities as approximate.

---

## 4a. Run-to-run variance — read this before any other number

Boosting here is stochastic: early stopping carves a random validation split out
of a few hundred rows, so the fitted model depends on the random seed. That was
not a rounding concern. Refitting the **identical model on identical data** with
only the seed changed produced:

| Position | seed 17 | seed 101 | seed 2024 |
|---|---|---|---|
| QB | 0.362 | 0.502 | 0.477 |
| RB | 0.503 | 0.514 | 0.526 |
| TE | 0.292 | 0.360 | 0.353 |
| WR | 0.349 | 0.370 | 0.372 |

Mean spread across seeds, per position-season: **0.124 Spearman**. Every feature
effect worth testing in this model is 0.02–0.09. The noise was three to five
times the signal, which means single-run ablation results here were not
measuring anything.

Two consequences, both now baked in:

1. **The ranking estimators are bagged across five seeds.** `P(plays)` and
   `E[points | plays]` are each an average of five fits. That halves the spread
   to 0.061.
2. **Every reported comparison is seed-averaged over three seed families**, and
   any feature-block decision is a paired test on those averages. Single-seed
   numbers are not quoted.

Residual spread of 0.061 is still not small next to a 0.03 feature effect, so
differences below roughly 0.05 Spearman in this model should be read as "not
established", regardless of what a p-value says.

## 5. Validation

**Expanding window.** To project season S, the model trains only on seasons
before S. No leave-one-season-out, no shuffled folds. A model that has seen 2024
while projecting 2022 is not the model that will project 2026. Test seasons:
2019–2025.

**Fair head-to-head pool.** Every source is graded on the same rows — anyone
either the model or consensus places inside its published depth — otherwise the
comparison flatters whoever ranks fewer players.

**Metrics.** Spearman ρ and Kendall τ; NDCG@12; top-12 overlap; start/sit
regret@12 (points per starter left on the bench by trusting the order); MAE and
RMSE; CRPS via the quantile ladder; Brier score on `P(top-12)`.

> **Status:** the tables in this section are single-seed numbers taken before
> the variance problem in §4a was found and the estimators were bagged. Read them
> as directional only; the seed-averaged refresh replaces them, and
> `outputs/backtest/per_season_by_seed.csv` will carry the per-seed spread.

### Results against actual finishes

Everything is graded against **real week-1 stat lines** from nflverse, scored in
the relevant format. Consensus is not the target — it is a second contestant
graded against the same reality, and it is never a model feature.

Model alone, on its own published depth, mean over 2019–2025:

| Position | Spearman vs actual | of my top 12, finished top 12 | mean rank error | MAE (pts) |
|---|---|---|---|---|
| QB | 0.428 | 4.8 / 12 | 8.6 places | 6.3 |
| RB | 0.514 | 5.1 / 12 | 13.0 places | 5.6 |
| WR | 0.355 | 3.7 / 12 | 20.5 places | 6.4 |
| TE | 0.436 | 6.4 / 12 | 8.6 places | 4.4 |

That is what week 1 looks like honestly. Note the pool matters enormously: on
the full rankable population — starters plus deep backups — Spearman reads
0.69–0.77, but most of that is the trivial skill of ranking starters above men
who never take a snap. Every number published here is on the narrower pool of
players actually worth ranking.

### Results against consensus

Mean across 2019–2025 (`outputs/backtest/summary.csv`; MAE is omitted because consensus publishes a rank, not a points projection):

| Position | Source | Spearman | NDCG@12 | Top-12 overlap | Regret@12 |
|---|---|---|---|---|---|
| QB (4pt) | consensus | **0.485** | **0.780** | 0.533 | 5.63 |
| | **model** | 0.451 | 0.705 | 0.533 | **5.35** |
| | prior-year PPG | 0.273 | 0.674 | 0.483 | 7.04 |
| RB (PPR) | consensus | **0.599** | **0.717** | 0.417 | **5.47** |
| | **model** | 0.534 | 0.685 | **0.433** | 5.53 |
| | prior-year PPG | 0.505 | 0.701 | **0.450** | 5.49 |
| WR (PPR) | consensus | **0.427** | **0.646** | 0.317 | **8.02** |
| | **model** | 0.377 | 0.616 | **0.333** | 8.99 |
| | prior-year PPG | 0.341 | 0.573 | 0.300 | 9.25 |
| TE (PPR) | consensus | **0.418** | **0.661** | **0.567** | **3.78** |
| | **model** | 0.369 | 0.642 | 0.533 | 4.05 |
| | prior-year PPG | 0.300 | 0.597 | 0.517 | 4.46 |

**Read this honestly.**

- The model beats the naive baseline — last season's points per game — at every
  position on every metric. That part works.
- **It does not beat FantasyPros expert consensus on rank correlation at any
  position.** It edges consensus on QB start/sit regret and on top-12 overlap
  for RB and WR, and it is close at WR, but consensus wins the headline metric
  four times out of four.
- Blending model and consensus in rank space peaks around 25–30% model weight
  and looks like an improvement (ρ 0.487 → 0.500) — but when the blend weight is
  fitted **out-of-sample** on prior seasons only, it stops beating consensus
  (0.477 vs 0.487) while winning 15 of 24 position-season tests. The in-sample
  peak was partly overfit. The blend is not shipped as a result.

The gap is explainable and not mysterious: consensus embeds camp reports, beat
writers, coach quotes, holdouts and preseason usage. No free historical dataset
contains any of that. The model sees only what happened on the field last year
plus who is on the depth chart.

---

## 6. Known limitations

- **Routes run do not exist in free data.** The *Two Doors* second gate is
  approximated by target share divided by snap share. True targets-per-route
  needs PFF or FantasyPoints.
- **Snap-level participation is gone.** nflverse pulled it when NGS stopped
  publishing. That means the RB third-down study's down-split snap share — the
  best RB role feature available — cannot be rebuilt from public data. Third-down
  *target* rate is the substitute. If the raw dataset from that study still
  exists, it is worth wiring in.
- **No TE study exists yet**, so the TE model runs on general priors and is the
  least informed of the four. It is also the position where consensus beats the
  model by the widest margin on top-12 overlap.
- **`config/playcallers.csv` is empty** (see §2). Every carryover number is
  currently measured on head-coach changes, which misses standalone coordinator
  moves. This is also the open question behind the ablation result: the scheme
  layer may be failing because the proxy is blunt, not because scheme is
  irrelevant.
- **n = 37** for the change-regime carryover fit. The coefficients are
  directionally useful, not precise. Bootstrap intervals are not yet computed.
- **Independent player sampling** overstates the sharpness of `P(top-12)`.
- **Rookies** get draft capital, depth-chart position and team vacancy, and
  nothing else. College production is not wired in — the RB study's finding that
  college receiving predicts NFL role is a clear addition.

---

## 7. Running it

```bash
pip install -r requirements.txt

python -m dd.cli ingest      # warm the nflverse cache (~600 MB, once)
python -m dd.cli panel       # build the point-in-time training panel
python -m dd.cli backtest    # expanding-window backtest -> outputs/backtest/
python -m dd.cli carryover   # scheme carryover report -> outputs/carryover/
python -m dd.cli predict     # the eight lists -> outputs/2026/week-01/
python -m dd.cli skeleton    # regenerate config/playcallers.csv
```

## 8. Layout

```
model/
  config/playcallers.csv     the one curated input (currently blank)
  dd/
    ingest.py                nflverse downloads, cached
    scheme.py                offensive + defensive fingerprints
    playcaller.py            regimes, caller histories, the carryover model
    usage.py                 player usage + empirical-Bayes shrinkage
    context.py               Vegas lines and schedule context
    dataset.py               point-in-time assembly + expected opportunity
    features.py              per-position feature sets and rankable population
    model.py                 the hurdle model and quantile ladder
    benchmark.py             FantasyPros consensus, the thing to beat
    evaluate.py              ranking metrics
    pipeline.py              backtest + prediction runners
    cli.py                   entry points
  outputs/
    2026/week-01/            the eight published lists
    backtest/                per-season and head-to-head metrics
    carryover/               carryover coefficients + projected 2026 schemes
```

## 9. Data sources

All free and public.

- **nflverse-data** — play-by-play (2006–2025), weekly player stats, snap counts,
  FTN charting, depth charts, weekly rosters, injuries, schedules with betting
  lines, draft picks, contracts, Next Gen Stats.
- **DynastyProcess** — FantasyPros expert-consensus ranking history, used purely
  as the benchmark. It is never a model feature; feeding consensus into the
  model would just make the model track consensus.

## 10. In-season

From week 2 the same structure holds and the prior-season terms get progressively
replaced by current-season usage, shrunk toward the preseason prior with weight
that decays as the sample grows. The empirical-Bayes machinery in `usage.py`
already does exactly this; it just needs pointing at current-season rows.
