# Poking holes in the Reedy consistency study

**Source:** Michael Reedy (@MikeReedyFF), *"Consistency vs. Boom/Bust: Which Type of Player Helps
Fantasy Teams Win More Often?"*
**Data:** nflverse `stats_player_week`, 2012–2025, regular season, half-PPR, QB/RB/WR/TE.
**Verdict:** The headline conclusion is **correct**. The evidence he presents for it does not
establish it, and the practical advice he draws from it is the part that doesn't survive testing.

---

## 0. His sample, recovered exactly

His filter is **≥14 games played in Weeks 1–17**, 2024–2025, QB/RB/WR/TE. That yields **368**
qualifying player-seasons — his stated number, to the player.

| | QB | RB | TE | WR |
|---|---|---|---|---|
| 2024 | 20 | 52 | 35 | 75 |
| 2025 | 19 | 58 | 29 | 80 |

Everything below is run against that same definition, then extended.

---

## 1. What he gets right

**The core claim replicates.** Matching players within position and season on points per game
(±5%) and splitting on CV, then simulating 100,000 head-to-head weeks:

| Season | Consistent roster wins | His number |
|---|---|---|
| 2024 | 50.8% | 51.4% |
| 2025 | 51.3% | 51.2% |

**And it holds far beyond his two seasons.** Running the identical test on every season 2012–2025:

> **14 of 14 seasons favor the consistent roster.** Mean edge **+1.17 pp**, 95% CI **[+0.91, +1.43]**.

That is a genuinely robust finding, and it is stronger evidence than anything in his article.

**His secondary descriptions are all accurate:**
- Consistent rosters post higher medians (64.3 vs 63.8 in 2024) ✓
- Boom/bust rosters post higher ceilings (90th pct 85.4 vs 90.9) and lower floors (10th pct 45.8 vs 41.4) ✓
- Average scoring is highly stable year to year — he says 0.79, I get **0.79** across 13 transitions ✓
- The favored/underdog gradient is directionally right (see §5) ✓

**Two critiques I expected to land, and didn't** — worth stating because they'd be the obvious
attacks:
- *"He resamples weeks independently, destroying real week-to-week correlation."* Re-running with
  week-aligned sampling (every player draws his actual score from the same real NFL week):
  **51.04% either way.** No effect.
- *"CV computed only on games played ignores injury zeros."* Adding 0-point weeks for missed games
  moves mean CV 0.792 → 0.845 and leaves the **rank correlation at 0.99**. Immaterial.

---

## 2. He doubles his own effect size

> *"A two-to-three percentage point advantage may appear small…"*

51.4% vs 48.5% is not a 2.9-point advantage. It is a **1.4-point edge over a coin flip**. In a
zero-sum head-to-head, the gap between the two sides double-counts the same effect. Same for 2025:
51.2% vs 48.9% is a **1.2-point** edge, not 2.3.

Every conclusion in the piece is drawn against a number that is 2× too big.

---

## 3. 100,000 simulations is not a sample size

This is the central statistical error. Monte Carlo error at 100,000 sims is ±0.3 pp — which is
what lets him report "51.4%" to a tenth of a point. But simulations don't create information. The
sampling error that matters comes from the **~50 matched pairs** the sims draw from.

Bootstrapping over the player pool instead of the simulation draws:

| Sample | Point estimate | 95% CI over players |
|---|---|---|
| 2024 | 50.8% | **[49.5%, 52.3%]** |
| 2025 | 51.3% | **[49.7%, 52.4%]** |
| Both | 50.8% | **[49.7%, 52.2%]** |

**Every interval contains 50%.** His two seasons cannot establish the effect he reports. It took
me 14 seasons to pin it down. He was right, but he could not have known it from his own data.

---

## 4. CV is mostly a quality proxy, and the mechanism isn't variance

> *"Using CV instead of a fixed-point range allowed players with different scoring averages and
> positions to be compared more fairly."*

CV has the mean in the denominator, so it is strongly mean-dependent:

`corr(CV, PPG)` = **−0.64** pooled; −0.62 (QB), −0.72 (RB), −0.69 (TE), −0.63 (WR).

| CV quartile | PPG | median | (mean − median)/mean | skew |
|---|---|---|---|---|
| low CV | 15.2 | 14.8 | 3% | 0.35 |
| 2 | 9.9 | 9.0 | 10% | 0.69 |
| 3 | 6.6 | 5.3 | 19% | 1.03 |
| high CV | 3.6 | 2.1 | **52%** | 1.81 |

His "low CV" bucket is just *good players*. The matched-pair design rescues him — but the roster
simulation is framed as "consistent rosters vs boom/bust rosters," which invites exactly the
confusion the CV metric creates.

**More important: the mechanism he describes is wrong.** If two players have equal means and
symmetric distributions, variance has *literally zero* effect on P(win) — it cancels by symmetry.
The entire edge comes from **right-skew**: a volatile player's mean is inflated by rare booms, so
his *median* is far below it. Matching on mean therefore hands the consistent player a median
advantage of up to 52%.

The actionable restatement is not "prefer low CV." It is: **mean overrates right-skewed players —
compare medians, not averages.** That's a different and more useful piece of advice, and it's
measurable directly instead of through a noisy volatility statistic.

---

## 5. The edge dilutes across a lineup — it does not compound

> *"Applied across an entire season and multiple lineup decisions, a modest weekly advantage can
> affect playoff qualification…"*

Backwards. Summing more players averages volatility away:

| Starters | Consistent roster win rate |
|---|---|
| 4 | 51.63% |
| 6 | 51.43% |
| 7 | 51.20% |
| 10 | **51.09%** |

The deeper your lineup, the *less* consistency matters. Superflex and deep-flex formats should
care about this least — the opposite of the implication.

**The matchup gradient is also hump-shaped, not monotone.** Swapping one volatile WR for an
equal-PPG consistent WR, by projected margin:

| Projected margin | Δ win prob |
|---|---|
| < −20 (big underdog) | −0.30 pp |
| −20 to −12 | −0.38 pp |
| −12 to −6 | −0.16 pp |
| −2 to +2 (even) | −0.19 pp |
| +2 to +6 | +0.58 pp |
| +6 to +12 | +0.54 pp |
| +12 to +20 | **+0.82 pp** |
| > +20 (big favorite) | +0.20 pp |

His −0.14 / +0.39 / +0.84 numbers are close to mine, and the sign flip is real. But the effect
**collapses at both extremes** — when you're a 20-point favorite you win regardless, so consistency
buys nothing. "When favored, prefer consistency" is right only in the moderate zone.

---

## 6. The stability numbers got a lucky draw, and the comparison is rigged

He reports three year-to-year correlations from a **single** transition (2024→2025):

| Metric | His number | 2024→25 (mine) | **13 transitions** |
|---|---|---|---|
| Average scoring | 0.79 | 0.80 | **0.79** ✓ |
| Coefficient of variation | 0.63 | 0.65 | **0.52** |
| Boom rate | 0.26 | 0.38 | **0.25** |

CV is meaningfully *less* stable than he reports — 0.52, not 0.63. He drew a high year.

The comparison is also not apples-to-apples. Average scoring is a continuous mean; boom rate is a
**thresholded proportion**, and binarizing throws away most of the information. Of course it's less
reliable. Split-half within a single season (odd weeks vs even weeks), which removes real
year-over-year change and measures pure signal-to-noise:

| Metric | Split-half reliability |
|---|---|
| Average scoring | 0.84 |
| CV | 0.62 |
| Boom rate | **0.19** |

Boom rate is ~80% noise *within the same season*. It isn't an unstable trait; it's barely a
measurement.

---

## 7. The big one: his advice is not actionable

His conclusion is a decision rule:

> *"Consistency should serve as a tiebreaker among players with comparable projections."*

But every number in the study uses **same-season** CV. That's hindsight. At a draft you have last
year's CV, not this year's.

**How much consistency signal survives once you hold quality constant?**

| | raw y/y corr | partial, controlling for PPG both years |
|---|---|---|
| CV | 0.52 | **0.29** |
| Boom rate | 0.25 | **0.04** |

Among players with comparable projections — which is exactly the situation his tiebreaker is for —
CV carries over at 0.29 and boom rate at **0.04, i.e. nothing**.

**The direct test.** Same matched-pair simulation, but label the "consistent" player by his
**prior** season's CV instead of the current one:

| Test | Edge | 95% CI | Seasons > 50% |
|---|---|---|---|
| **Oracle** (same-season CV — what he did) | **+1.16 pp** | [+0.90, +1.42] | **13/13** |
| **Ex-ante** (prior-season CV, tight match) | +0.21 pp | **[−0.43, +0.85]** | 8/13 |
| Ex-ante (looser match) | +0.15 pp | [−0.37, +0.66] | 9/13 |
| Ex-ante (loosest match) | +0.78 pp | [+0.24, +1.31] | 11/13 |

The real, usable edge is somewhere between **zero and +0.8 pp**, spec-dependent, and in the
cleanest specification it is statistically indistinguishable from zero. The study measures the
value of knowing consistency *in hindsight* — roughly 3–5× the value of the signal you can
actually act on.

---

## 8. Survivorship: the study runs on the tamest third of the player pool

The ≥14-game filter removes **65%** of player-seasons (7,351 → 2,567 across 2012–2025), and what
it removes is systematically the volatile end:

| | PPG | CV | bust rate |
|---|---|---|---|
| Kept (≥14 g) | 9.08 | 0.792 | 0.284 |
| Dropped (8–13 g) | 5.36 | **1.078** | **0.391** |

Missing games *is* the dominant form of bust risk for a real roster, and it's been filtered out.
Note this cuts **in his favor** — the true consistency advantage is probably larger than he
measured, not smaller.

---

## 9. What he should have led with

He measures weekly win rate. Fantasy is won by titles. Simulating 4,000 full 12-team leagues
(14-week round robin, 6 playoff teams, 3-week bracket), six mean-matched all-consistent teams
against six all-boom/bust teams:

| | Consistent | Boom/bust | Gap |
|---|---|---|---|
| Weekly H2H win rate | 51.03% | 48.97% | +1.03 pp |
| Regular-season wins | 7.08 | 6.92 | +0.17 |
| Points for | 917.3 | 918.3 | −1.1 |
| Made playoffs | 51.0% | 49.0% | +1.9 pp *(CI +1.03 to +2.82)* |
| **Won the title** | **8.78%** | **7.88%** | **+0.90 pp** *(CI +0.41 to +1.39)* |

Consistency raises title odds from 7.9% to 8.8% — an **11% relative improvement**, on identical
expected points. Notably the tournament format does *not* flip the result the way variance
strategy usually does; the regular-season seeding advantage outweighs the bracket's variance
premium.

That's the number that makes his case. "+11% relative championship odds" is both more honest and
more persuasive than "a two-to-three percentage point advantage."

---

## Scorecard

| Claim | Verdict |
|---|---|
| Consistency beats boom/bust at equal expected points | ✅ **Right** — and holds 14/14 seasons |
| Consistent rosters have higher medians, lower ceilings | ✅ Right |
| Average production > consistency; scoring is more stable | ✅ Right (0.79 confirmed) |
| Favored → prefer consistency; underdog → prefer volatility | ✅ Right in direction, ❌ collapses at both extremes |
| "A two-to-three percentage point advantage" | ❌ **It's 1.2–1.4 pp** — double-counted |
| 100,000 sims establish the result | ❌ **CI over players includes 50%** in both his seasons |
| CV allows fair comparison across scoring averages | ❌ `corr(CV, PPG) = −0.64` |
| Variance is the mechanism | ❌ **Skew is** — at equal means, symmetric variance does nothing |
| Effect compounds across lineup decisions | ❌ **It dilutes** (+1.63 pp at 4 starters → +1.09 at 10) |
| CV year-to-year ≈ 0.63 | ❌ **0.52** over 13 transitions; he drew a high year |
| Boom rate is unstable (0.26) at trait level | ⚠️ Number right, comparison rigged — 0.19 split-half *within* season |
| Use consistency as a draft tiebreaker | ❌ **The ex-ante edge is ~0 to +0.8 pp**, CI spans zero |

**Bottom line:** He's right that consistency wins, and more right than his own evidence could
show. But the effect is half the size he claims, driven by skew rather than variance, weaker in
deeper lineups rather than stronger, and — most importantly — mostly unavailable to you at the
moment you'd have to use it.
