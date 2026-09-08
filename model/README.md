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

## 2. Team environment: last season, discounted by a head-coaching change

The first build projected a 22-dimension scheme vector for every team by
attaching fingerprints to play-callers and carrying them between jobs. It
failed its ablation twice (§2b), and it depended on coordinator data that does
not exist in public sources. It has been replaced by a much smaller model that
answers the question week 1 actually poses.

**The reasoning.** For week 1 the useful fact about a team is how its offence
and defence actually performed last season — measured, not projected. The one
change worth modelling is a **head-coaching change**, because that is the case
where last season is least trustworthy: a new head coach almost always brings a
new coordinator, a new play-caller and a new scheme on both sides of the ball.
It is also the only regime signal that exists in verified public data — nflverse
carries the head coach of every team-season, so nothing has to be curated.

So instead of projecting a scheme vector, two coefficients per dimension:

```
same head coach   y_t ~ a0 + a1 * y_{t-1}
new head coach    y_t ~ b0 + b1 * y_{t-1}
```

The gap `b1 − a1` is the head-coach effect, fitted on twenty seasons and **141
head-coaching changes** — versus 37 for the old play-caller approach, because
this needs no prior history for the incoming coach.

| Dimension | same HC | new HC | head-coach effect |
|---|---|---|---|
| seconds per play | 0.685 | 0.312 | **−0.373** |
| goal-line rush rate | 0.367 | 0.015 | **−0.352** |
| red-zone pass rate | 0.445 | 0.144 | **−0.301** |
| PROE | 0.487 | 0.218 | **−0.269** |
| plays per game | 0.417 | 0.202 | −0.215 |
| neutral pass rate | 0.444 | 0.312 | −0.132 |
| RB target share | 0.228 | 0.098 | −0.131 |
| WR target share | 0.282 | 0.206 | −0.076 |
| TE target share | 0.193 | 0.243 | +0.051 |

**Read it as:** a head-coaching change roughly halves how much last season's
offence tells you, and for goal-line and red-zone tendency it wipes it out
almost entirely (slope 0.015 — last year's goal-line behaviour under a new head
coach is worth nothing). Tempo is the most disrupted of the volume dimensions.
Tight end target share is the one non-result, and at that slope it is noise.

These projected rates feed expected volume directly — projected plays times
projected pass rate is what turns a player's share into expected targets — and
eleven compact columns go to the models: nine projected rates plus `hc_change`
for the player's own team and `opp_hc_change` for his opponent.

### Did the reduction cost anything?

Tested head to head against the old carryover-driven build, seed-averaged,
top-36 (§5):

| Metric | New model minus old | p |
|---|---|---|
| Captured top-12 | +0.125 | 0.11 |
| Points from top 12 | +0.72 | 0.53 |
| Regret per starter | −0.06 | 0.53 |
| Spearman (shared rows) | +0.001 | 0.88 |

Statistically a wash, marginally positive, better at QB (+0.27 captured) and TE
(+0.20), fractionally worse at RB (−0.03). **It is not a measured improvement**
and the model card does not claim one. It ships because it reaches the same
place with eleven columns instead of twenty-seven, using only measured and
verified inputs, and with no dependency on a coordinator list anybody has to
maintain.

The carryover machinery is still in the repo — `dd/playcaller.py`, and
`python -m dd.cli carryover` still produces the report — because it answers a
genuine research question about which tendencies follow a coach. It just no
longer feeds the ranking models.

## 2b. What the carryover experiment found, and why it was dropped

### The original question (measured, not assumed)

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

### Does the scheme layer improve rankings? No — and the raw columns hurt.

The coefficients above measure how well a play-caller's tendencies predict his
next team's tendencies. That is a fact about **scheme**. Whether it improves
**player rankings** is a separate question, and the answer is no.

Tested by ablation: same expanding-window backtest, feature blocks removed,
seed-averaged over three seed families (see §4a — single-seed ablations of this
model measure nothing). Paired across 28 position-seasons:

| Removed | Δ Spearman from keeping it | 95% CI | p | seasons it helped |
|---|---|---|---|---|
| Play-caller layer (scheme projection + regime flags) | −0.006 | [−0.021, +0.008] | 0.38 | 11 / 28 |
| Every scheme column (adds the team's own prior rates) | **−0.026** | [−0.041, −0.012] | **0.001** | 7 / 28 |

Two distinct findings:

1. **The play-caller layer is a null.** Adding or removing it changes nothing
   measurable. The confidence interval straddles zero and is tight enough to
   rule out anything larger than about 0.02 in either direction.
2. **The full scheme block is actively harmful.** Removing all 27 team-level
   scheme columns *improves* Spearman by 0.026, consistently, in 21 of 28
   position-seasons. Twenty-seven mostly-collinear columns on a thousand-row
   problem dilute the features that carry signal.

So the scheme columns are **not fed to the player models** — `USE_SCHEME_COLUMNS`
in `dd/features.py` is off, and the reason is recorded there.

One important qualification: this removes the scheme **columns**, not scheme's
influence. The carryover projection still reaches the model through expected
volume, because projected team plays and pass rate are exactly what convert a
player's share into expected targets and carries. The defensible claim is "raw
scheme columns do not earn a slot in a model this size", not "scheme does not
matter".

Why might the play-caller layer still be a null even though tendencies clearly
travel? Most likely because a player's own prior-season usage already encodes
his offence — a receiver in a pass-heavy scheme has a pass-heavy scheme's target
volume baked into his target share. The team-level vector then restates what the
player-level features already said. The head-coach proxy is a second candidate
explanation, and the one the coordinator history would settle.

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

### Results against actual finishes

Everything is graded against **real week-1 stat lines** from nflverse, scored in
the relevant format. Consensus is not the target — it is a second contestant
graded against the same reality, and it is never a model feature.

Model alone, on its own published depth, seed-averaged over three seed families,
mean over 2019–2025:

| Position | Spearman vs actual | of my top 12, finished top 12 | mean rank error | MAE (pts) |
|---|---|---|---|---|
| QB (4pt) | 0.438 | 6.1 / 12 | 8.6 places | 6.3 |
| RB (PPR) | 0.517 | 5.4 / 12 | 13.1 places | 5.4 |
| WR (PPR) | 0.361 | 3.6 / 12 | 20.6 places | 6.3 |
| TE (PPR) | 0.368 | 6.2 / 12 | 8.9 places | 4.4 |

That is what week 1 looks like honestly. Note the pool matters enormously: on
the full rankable population — starters plus deep backups — Spearman reads
0.69–0.77, but most of that is the trivial skill of ranking starters above men
who never take a snap. Every number published here is on the narrower pool of
players actually worth ranking.

Across-seed standard deviation of these Spearman figures is 0.024–0.052, so read
them to roughly two decimal places and no further.

### Results at the top 36 — the comparison that decides lineups

The full board flatters everyone: ranking a starter above a third-string tight
end is not a skill anyone pays for. Restricting both sources to their own top 36
and asking what those players actually did (`outputs/backtest/top36_head_to_head.csv`,
seed-averaged, seasons with consensus history):

| Position | Source | Captured top-12 | Points from its top 12 | Regret / starter | Spearman (shared rows) |
|---|---|---|---|---|---|
| QB | consensus | 6.6 / 12 | 224.5 | 5.26 | 0.688 |
| | **model** | **6.6** | **228.1** | **4.96** | **0.718** |
| RB | consensus | 4.2 | 187.1 | 5.90 | **0.486** |
| | **model** | **4.9** | **187.6** | **5.86** | 0.475 |
| TE | consensus | **5.8** | **104.2** | **4.53** | **0.451** |
| | model | 5.0 | 99.2 | 4.95 | 0.427 |
| WR | consensus | 3.6 | **196.3** | **8.92** | **0.307** |
| | model | 3.6 | 189.2 | 9.51 | 0.292 |

"Captured top-12" is how many of that source's top 12 actually finished top 12
in the position. Spearman is computed on the union of both top-36 lists, so the
row set is identical and the numbers are comparable; the outcome columns use
each source's own 36, which needs no matching.

**The picture changes at this depth.** On the full board the model trailed
consensus by 0.05–0.11 Spearman everywhere. Inside the top 36:

- **Running back — the model is better**, and on the metrics that matter most.
  It captures a full extra top-12 back (5.0 vs 4.1), delivers three more points
  from its top 12, and gives up less regret. Spearman is a dead heat.
- **Receiver is a coin flip.** The model captures marginally more top-12
  receivers; consensus squeezes slightly more points out of its twelve.
- **Quarterback and tight end still belong to consensus**, though both narrowed
  under the reduced team-environment model: QB 6.0 captured against 6.3, TE 5.0
  against 5.8. Tight end keeps the widest Spearman gap on the board, which is
  consistent with it being the one position with no study behind it.

Paired across seasons the honest verdict is that **none of this is statistically
significant** — five seasons of consensus history is a small sample, and every
p-value lands between 0.07 and 0.73 (RB captured top-12: +0.93, p = 0.13; TE
points: −8.4, p = 0.07; QB captured: −0.60, p = 0.09). Directionally the model
is at parity or better at RB and WR and behind at QB and TE; that is as strong a
claim as five seasons supports.

### Results against consensus

Same rows for every contender — anyone the model or consensus places inside its
published depth. Seed-averaged, mean over the seasons where consensus history
exists:

| Position | Source | Spearman | NDCG@12 | Top-12 overlap | Regret@12 |
|---|---|---|---|---|---|
| QB (4pt) | consensus | **0.497** | **0.788** | 0.533 | **5.37** |
| | **model** | 0.483 | 0.717 | 0.533 | 5.74 |
| | prior-year PPG | 0.259 | 0.707 | 0.500 | 6.85 |
| RB (PPR) | consensus | **0.600** | **0.735** | 0.417 | 5.05 |
| | **model** | 0.542 | 0.706 | **0.467** | **5.09** |
| | prior-year PPG | 0.499 | 0.716 | 0.450 | 5.10 |
| WR (PPR) | consensus | **0.438** | **0.647** | **0.322** | **7.99** |
| | **model** | 0.387 | 0.619 | 0.317 | 8.97 |
| | prior-year PPG | 0.347 | 0.574 | 0.300 | 9.21 |
| TE (PPR) | consensus | **0.435** | **0.644** | **0.550** | **3.99** |
| | **model** | 0.326 | 0.572 | 0.472 | 4.68 |
| | prior-year PPG | 0.323 | 0.597 | 0.533 | 4.39 |

**Read this honestly.**

- The model beats the naive baseline — last season's points per game — at every
  position on Spearman, by 0.04 to 0.22.
- **It does not beat FantasyPros expert consensus on rank correlation at any
  position.** It is close at quarterback (0.483 vs 0.497, inside the seed noise),
  behind by 0.06 at running back and receiver, and clearly behind at tight end.
  It does beat consensus on top-12 overlap at running back — 5.6 of 12 against
  5.0 — which is the metric that decides a lineup.
- Dropping the scheme columns closed roughly a third of the quarterback gap and
  helped everywhere else too; see §2.
- Blending model and consensus in rank space peaks around 25–30% model weight
  in-sample, but with the weight fitted **out-of-sample** it stops beating
  consensus while winning 15 of 24 position-season tests. The blend is not
  shipped.

The gap is explainable and not mysterious: consensus embeds camp reports, beat
writers, coach quotes, holdouts and preseason usage. No free historical dataset
contains any of that. The model sees only what happened on the field last year
plus who is on the depth chart.

### Why the benchmark is preseason consensus, and why weekly is not an option

FantasyPros publishes two different products, and they answer different
questions:

- **Preseason redraft rankings** (`redraft-qb`, `redraft-rb`, …) — "who is the
  best running back for the season". Essentially ADP. Matchup-blind: it does not
  know who plays whom in week 1.
- **Weekly start/sit rankings** (`weekly-rb`, …) — "who should you start this
  week", published days before kickoff, accounting for matchup, injury news and
  camp reports.

A weekly model should ideally be graded against the weekly list. It is not,
because that list effectively does not exist in the public mirror for week 1.
Filtering the DynastyProcess ECR archive to early September returns exactly two
scrape dates across all seasons — 2021-09-10 and 2025-09-12 — and checking them
against the schedule disqualifies both:

| Scrape | Week 1 window | Verdict |
|---|---|---|
| 2021-09-10 | Sep 9–13 (opener Sep 9) | after the Thursday game, before the other 15 — usable but contaminated |
| 2025-09-12 | Sep 4–8, week 2 opens Sep 11 | **this is a week 2 list.** Using it would leak week 1 results |

So the benchmark is the preseason list, and that cuts **against** this model,
not for it. The preseason list does not know week 1's matchups; this model does
— implied team totals, opponent defensive priors, game script. Failing to beat a
matchup-blind opponent with matchup-aware features is a worse result than
failing to beat a matchup-aware one, and it raises a question worth testing:
whether the market and opponent features are contributing anything at week 1, or
whether week-1 outcomes are dominated by player quality that the crowd simply
estimates better. That ablation has not been run.

## 5b. Training window and the target variable

Two changes were tested after the first build, both graded the same way:
expanding window, seed-averaged, week 1 at top-36.

### Training on more than week 1

Every point-in-time function now takes a week, so the panel carries all 18
weeks of every season -- 129,000 rows against 8,600. Each week is posed as the
*week-1* problem: prior-season features only, nothing from weeks 1..W-1. The
rows are extra examples of what we predict rather than a different problem, and
`week`, `is_week1` and explicit `is_week1 x prior-feature` interactions let the
model hold a separate week-1 slope.

| Position | weeks 1-6 vs week 1 | all weeks vs week 1 |
|---|---|---|
| QB | **+0.40 captured** (p = 0.18, never worse in 5 seasons, 3 seeds) | -0.07 |
| TE | +0.30 | +0.50 (p = 0.089) |
| RB | +0.10 | +0.20 |
| WR | -0.40 | -0.20 |

Overall, across 20 position-seasons, both wider windows gain +0.125 captured
top-12 with p around 0.48. **Seventeen times the data moved almost nothing.**

Only quarterback ships with a wider window. Rationale and caveat sit beside
`TRAIN_WEEKS` in `dd/config.py`: never worse on a single season across three
seeds, regret from 5.43 to 4.92, and a mechanism -- a quarterback's role is the
steadiest of the four week to week, so mid-season rows resemble week 1 more
closely than at receiver, where the wider window did the most damage.

### Within-week z-scored targets

The conditional stage trains on how far a player beat his positional peers
*that week*, not on raw points. Week-level scoring environment is noise the
model cannot predict, and raw-point training blames it for it.

Applied only among players who played -- z-scoring a distribution that is half
zeros is meaningless -- and converted back to points before multiplying by
P(plays), because a negative z-score times a small probability sorts *higher*
than the same score times a large one, which would invert the ranking silently.

Result: +0.13 / +0.10 / 0.00 / +0.10 captured top-12 for QB/RB/WR/TE, never
worse in 19 of 20 tests, every p-value between 0.37 and 0.78. Not a measured
gain. It ships as the better-motivated target, not because the backtest proved
anything.

### What both results actually say

Ridge beat the gradient booster by more than 0.10 Spearman in **all 56**
comparisons -- the blend rule never fired once -- and seventeen times the data
changed nothing. Together those say the model is **not row-limited; it is
feature-limited.** The signal available is close to linear and already
saturated by the inputs we have. More rows and more capacity are both dead ends
here; better inputs are the remaining lever.

### One number that got worse to be honest about

At running back the naive baseline -- last season's points per game -- now
captures 5.0 top-12 backs to the model's 4.9, with lower regret (5.48 vs 5.86).
The model still beats consensus at RB (4.9 vs 4.2), but it no longer clearly
beats doing nothing clever at all.

### A shrinkage bug the notes surfaced, and what it did not touch

Asked what "no rushing floor" meant for Josh Allen, the answer turned out to be
a bug rather than a wording choice. Method-of-moments picks the empirical-Bayes
prior strength from the gap between observed spread and assumed sampling noise;
for 2026 quarterback rush share that gap closed (obs_var 0.003740 against
samp_var 0.003666), k came out at 1393, and every quarterback was shrunk onto
the group mean -- projected carries between 3.0 and 3.4 for the whole position,
Josh Allen and Lamar Jackson priced like pocket passers.

k is now capped at three times the group's median sample. Quarterback rush share
reopens to 0.094-0.185 for 2026 and the rushers separate properly.

**The backtest is unaffected, and that was checked rather than assumed.** The
guard only binds when the estimator degenerates, which never happened on a
historical season -- week-1 quarterback rush share spreads 0.16 to 0.23 in every
year from 2019 to 2025, against 0.008 for the broken 2026 build. Re-running the
quarterback backtest across three seeds after the fix returns identical numbers
to three decimal places.

The root error is still there and is larger than the symptom: these are shares
of *team* volume, but the sampling term uses the player's own count as the
binomial denominator, which overstates the noise by an order of magnitude. A
second, separate problem sits alongside it -- shares divide by the team's
**full-season** volume, so a player who missed games has every share feature
deflated (Jayden Daniels reads a 0.120 rush share on 8.3 carries a game).
Fixing either properly means reworking the exposure weights and would change
every share feature at every position, so both are recorded here rather than
patched mid-week.

### The ranking and the probability came from different estimators

On the published PPR board Derrick Henry sat 13th with a 46% shot at a top-12
week while D'Andre Swift sat 12th with 25%. A list cannot rank one man above
another and simultaneously say he is less likely to finish above him.

It was not a display bug. The projection came from the mean model and the
distribution from the ladder of nine quantile GBMs, and nothing tied the two
together: the ridge put Swift's conditional week at 15.1 points while his own
quantile median said 11.2.

The obvious repair -- shift the ladder onto the mean model -- assumes the mean
model is the better estimate of level. It is not, and it is not worse either.
Across 56 position-scoring-seasons of backtest, ranking by the ladder's implied
mean instead of the mean model gains 0.005 Spearman (40-16, p = 0.003) and
nothing at all anywhere it would matter:

| metric | ladder − mean model | W/T/L | p |
|---|---|---|---|
| Spearman | +0.005 | 40/0/16 | 0.003 |
| top-12 overlap | +0.07 | 14/31/11 | 0.53 |
| points captured @12 | +0.005 | 22/4/30 | 0.67 |
| top-24 overlap | +0.05 | 18/21/17 | 0.76 |

Two estimators of equal accuracy making partly independent errors is the
textbook case for averaging them, and the average beats both parents:

| ranked by | Spearman | top-12 hits | captured |
|---|---|---|---|
| mean model | 0.7330 | 4.68 | 0.6596 |
| quantile ladder | 0.7384 | 4.75 | 0.6641 |
| **50/50 blend** | **0.7390** | **4.80** | **0.6662** |

The blend beats the mean model on Spearman 45-11 (p < 0.001) and loses to it on
nothing. `cond_points` is now that blend, and the ladder is recentred on it, so
the rank and the probability are two readings of one number. The weight is a
flat half deliberately: any other weight would have been chosen on the same
seasons it was then scored against.

### The simulator was clipping its own tails

`simulate()` interpolates the ladder, which runs only from the 10th to the 90th
percentile, and `np.interp` clamps outside its range. A fifth of every simulated
season therefore landed exactly on the q10 or q90 value -- two point masses
sitting where the tails belong, in precisely the region that decides a top-12
week. The outer deciles are now extended one decile further at the slope the
ladder was already running, floored at zero. Measured against how often a top-12
week actually happened, over 28 position-seasons: log loss 0.2257 against 0.2334,
Brier 0.0682 against 0.0684.

### What the crossings that remain actually mean

Rank and probability still do not move in lockstep, and should not. Henry now
projects 11th at 41% while Saquon Barkley projects 7th at 36%, because Henry's
median week is 16.2 and Barkley's is 14.8: Henry clears the bar more often,
while Barkley's higher projection rests on a ceiling four points taller. Top-12
is a threshold, and points past it do not count twice. `median_q50` is published
alongside the range so the weekly note can say this out loud instead of leaving
it looking like the old bug.

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
- **The benchmark is a season-long list, not a weekly one** (see above). No
  usable week-1 weekly consensus exists in public data.
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
