# Three receivers, one roster spot

Three wide receivers, described by profile rather than by name:

- **A — the five-week WR1.** Finished around WR8 last year on the back of five
  enormous games. Quiet in the other twelve, and quiet for his whole career
  before that.
- **B — the sophomore crash.** Finished WR4 as a rookie. Year two brought injury
  and a slump and he came out at WR40. He is entering year three.
- **C — the hurt efficient one.** Third year, always well targeted, efficiency
  metrics that grade out near the top of the league, missed real time to injury —
  his per-game pace says he was on a top-five season. Behind him, a young
  second-year receiver on his own team finished the year strong.

Which one finishes higher next season, and — the more useful question — **which
of the metrics that make them different is actually carrying the prediction?**

## Running it

```bash
pip install pandas numpy scipy statsmodels pyarrow
python3 fetch.py                      # ~26 weekly files, downloaded and filtered one at a time
python3 horse_race.py > HORSE_RACE.txt # which metrics predict next season at all
python3 archetypes.py > ARCHETYPES.txt # the three profiles, run against every season
```

`fetch.py` writes three gitignored files: `wr_weeks.parquet` (57,110 regular-season
WR game lines, 2000–2025), `team_games.parquet` (so games missed is measured
against the games the player's team actually played) and `players.parquet`
(rookie year, birth date, draft slot).

`panel.py` turns those into 5,466 WR-seasons. Everything a fantasy manager could
have known on the morning after season N sits on the same row as what happened in
season N+1, so no feature ever peeks forward.

## Method

The sample is every WR-season **2009–2024** with 6+ games and 40+ targets — 1,592
seasons, 464 receivers. Two bars, both deliberate:

- **The usage bar is low.** An 8-game / 50-target screen quietly deletes the
  collapsed seasons, and a collapsed season is exactly what archetypes B and C
  are about.
- **2009 is a hard floor.** nflverse carries no target or air-yards data for
  2003–2008, so every volume and efficiency metric is empty there. The panel
  itself still starts in 2000, so career history (best prior finish, earlier
  top-24 seasons) is right for players who debuted before the sample does.

A receiver with no season N+1 line did not play. That is a fantasy outcome, not
missing data, so he stays in at 0 points per game with his finish censored at the
bottom of the pool. 8.4% of the sample.

Nothing is scored in sample. Every R² is **leave-one-season-out**: fit on 15
seasons, predict the 16th, rotate. The reference model is not hand-picked either —
it is whatever survives greedy forward selection under that same rule, so a metric
enters only if it earns its place on seasons the model has never seen. That
matters with 34 correlated candidates: six of them get to within 0.004 R² of what
all 34 together manage (0.5004 against 0.5042), so the other 28 are, jointly,
worth almost nothing.

Two ideas in the panel are worth naming:

- **Health-adjusted finish** (`pace_finish`). Project every receiver in the season
  to his per-game pace over a full slate, then re-rank. The pool stays the same
  size as the real one, so this is "where would he have finished if everyone
  stayed healthy" — the counterfactual archetype C's case rests on.
- **Weekly Gini** (`gini`). Concentration of a season's points across its weeks:
  0 if every week is identical, 1 if one week is the whole season. Unlike a "top
  five games" share it does not drift with games played, so 8-game and 17-game
  seasons can be pooled.

## What predicts next season

| Rank | Metric | cv R² alone | AUC (top-24) |
|---|---|---|---|
| 1 | PPR points per game | 0.430 | 0.831 |
| 2 | health-adjusted finish | 0.411 | 0.832 |
| 3 | positional finish | 0.403 | 0.824 |
| 4 | share of games under 8 PPR | 0.360 | 0.812 |
| 5 | total targets | 0.353 | 0.807 |
| … | | | |
| 15 | yards per target | 0.117 | 0.659 |
| 16 | PPR per target | 0.115 | 0.659 |
| 17 | EPA per target | 0.113 | 0.657 |

Forward selection stops at six:

| Step | Metric | cv R² | Gain |
|---|---|---|---|
| 1 | PPR points per game | 0.4298 | +0.4298 |
| 2 | **age** | 0.4696 | +0.0398 |
| 3 | positional finish | 0.4837 | +0.0141 |
| 4 | points per game, season N−1 | 0.4932 | +0.0095 |
| 5 | count of earlier top-24 seasons | 0.4982 | +0.0050 |
| 6 | best finish among his 1st/2nd-year teammates | 0.5004 | +0.0021 |

Six metrics, cv R² = 0.500, AUC 0.859 on a top-24 finish. **Per-game scoring, age,
and how good he has been before. Everything else is rounding.**

By family — R² alone, and R² lost when the family is dropped from the model that
holds all 34:

| Family | Alone | Adds on top |
|---|---|---|
| Health / profile (age, games, draft slot) | 0.112 | **+0.0247** |
| Production | 0.468 | +0.0138 |
| Volume | 0.380 | +0.0047 |
| Efficiency | 0.134 | +0.0028 |
| Team context | 0.030 | +0.0018 |
| Weekly shape | 0.425 | −0.0003 |

Production and volume are the big movers on their own and almost entirely
redundant with each other. Age is the one thing nothing else contains.

## What holds up

**1. Weekly spikiness is not a warning sign.** Every concentration metric looks
predictive on its own (Gini cv R² 0.172), and all of it is borrowed from scoring
and games played. Hold points per game, targets per game and games played fixed
and no measure of spike structure moves next season at all — Gini +0.13 ppg/sd
(p = 0.35), top-5-game share +0.17 (p = 0.40), boom rate +0.10 (p = 0.69). Every
sign that reaches even marginal significance points the *wrong* way for the
mirage story. The weekly-shape family contributes −0.0003 R² on top of the rest.

**2. Efficiency matters, but only at fixed volume.** Mean next-season points per
game, by tercile of PPR per target inside each quartile of targets per game:

| | low eff | mid | high |
|---|---|---|---|
| tgt/g Q1 | 4.44 | 4.73 | 6.64 |
| Q2 | 5.54 | 7.22 | 8.43 |
| Q3 | 7.16 | 9.92 | 12.67 |
| Q4 | 11.63 | 14.47 | 15.21 |

Monotone in every row. But the efficiency family adds only +0.0028 R² over the
rest of the model, because at the top of the target distribution the spread
narrows and volume has already said most of it.

**3. Health-adjusting the finish helps a little; points per game helps more.**
Pace-adjusted finish beats raw finish (0.411 vs 0.403), and both lose to plain
points per game (0.430). Adding games missed on top of points per game and
pace-adjusted finish gets to 0.445 — the best three-metric combination tested.
Per-game scoring already encodes most of what the injury adjustment is for.

**4. A young teammate coming off a strong finish does nothing.** Among receivers
who finished top-30, having a first- or second-year teammate finish inside WR24,
WR36 or WR60 moves next-season points per game by less than half a point in every
case (p = 0.27, 0.59, 0.32). The variable does enter the reference model at step
six, but its contribution is +0.002 R².

**5. Pedigree is worth an enormous amount after a collapse.** Receivers coming off
a finish outside the top 30: with an earlier top-12 season, 15.7% finish top-24
next year; with no earlier top-24 season, 5.6%.

## The three profiles

| Cohort | n | Median next finish | Top-12 | Top-24 | Next ppg |
|---|---|---|---|---|---|
| **C** hurt + efficient | 15 | **WR12** | **53%** | **73%** | 15.65 |
| **A** five-week WR1 | 33 | WR19 | 24% | 64% | 14.76 |
| **B** young ex-WR1, off a collapse | 14 | WR34 | 21% | 50% | 12.36 |
| every WR season in the sample | 1,592 | WR64 | 11% | 21% | 8.98 |

Over every ordered pair of members, C finishes ahead of A 61% of the time and
ahead of B 64%; A finishes ahead of B 60%. The ordering is stable but the samples
are small and none of the three pairwise gaps clears significance (Mann-Whitney
p = 0.13 to 0.21).

Each is a ladder in `ARCHETYPES.txt`, so you can see which condition does the work:

**A — the five-week WR1.** 33 matches. The spike does not cost him anything: WR4-15
finishers who are *not* spike-built and *do* have a top-24 season behind them land
at median WR22 and 54% top-24, against WR19 and 64% for archetype A. If anything
the dose-response runs the other way — inside the WR4-15 group, receivers whose
top five games were over 55% of their points went on to a median WR15 and 73%
top-24. Being a first-time producer is not a penalty either, once you account for
the fact that first-time producers are younger.

**B — the sophomore crash.** The exact scenario has **never happened**. Since 2000
only ten receivers have finished top-12 as a rookie, and none has followed it with
a season outside the top 30 that also had a year-three season on the books to
judge. What the ten did next:

| Rookie year | | Year 2 | Year 3 |
|---|---|---|---|
| 2003 | Anquan Boldin WR4 | WR52 (10g) | **WR4** |
| 2014 | Odell Beckham Jr. WR7 | WR5 | WR4 |
| 2016 | Michael Thomas WR7 | WR6 | WR6 |
| 2020 | Justin Jefferson WR6 | WR4 | WR1 |
| 2021 | Jaylen Waddle WR12 | WR8 | WR34 |
| 2021 | Ja'Marr Chase WR5 | WR11 (12g) | WR11 |
| 2023 | Puka Nacua WR4 | WR26 (11g) | **WR1** |
| 2024 | Malik Nabers WR6 | WR101 (4g) | — |
| 2024 | Brian Thomas Jr. WR4 | WR42 | — |
| 2024 | Ladd McConkey WR12 | WR30 | — |

Two of them — Boldin and Nacua — had the injury-shortened sophomore dip, and both
came back WR4 and WR1. The nearest workable cohort widens it to "years 1-4, a
top-12 season already on the shelf, now finished outside the top 30": 14 matches,
median WR34, 50% top-24, against 10% for same-aged receivers who collapsed without
that pedigree. The pedigree is real and large; the *specific* rookie-to-sophomore
version of it has essentially no track record.

**C — the hurt efficient one.** 15 matches, and the best of the three on every
measure. The condition doing the work is the health-adjusted pace: hurt receivers
in years 2-4 whose pace was *not* top-18 finish at a median WR79 with a 6% top-12
rate; the ones whose pace was top-18 land at WR14 and 50%. Adding top-third
efficiency on top takes it to WR12 and 53%. The teammate condition leaves n = 2
and cannot be tested at cohort level, but the league-wide test in section 4(d)
says it does not matter. Members include Cooper Kupp 2018 → WR4, Tyreek Hill 2019
→ WR2, Calvin Ridley 2019 → WR5, Justin Jefferson 2023 → WR2 and Puka Nacua 2024
→ WR1, against Percy Harvin 2012 → WR179 and Sammy Watkins 2015 → WR90.

## The answer

**C, then A, then B** — and the reason is one metric, not three profiles.

C's per-game pace was top-five. A's was top-ten but over a full season, so his
points per game is real but lower. B's per-game pace in the down year was
genuinely bad, and a bad per-game rate is the single strongest negative signal in
the dataset; his top-12 rookie pedigree pulls him back up a long way but not past
the other two.

Everything the three profiles are *described* by — the five spike weeks, the
sophomore-slump narrative, the elite efficiency, the young receiver behind him —
is either already contained in points per game and age, or does not predict
anything. The one description that changes the answer is "had he not been hurt he
would have finished very high," because that is a claim about a rate, and rates
are what carry.

## Caveats

- Cohort sizes are 14 to 33. The ordering is consistent across every threshold
  tried, but no pairwise difference is significant.
- Positional finish is computed among receivers nflverse labels WR, roughly 210
  per season. A player listed at another position in a given season is not in the
  pool for that season.
- Games played is games with a stat line. A receiver who dressed and was never
  targeted does not count as having played, which slightly understates games for
  low-usage receivers and barely touches the ones studied here.
- Target share and WOPR are averaged over games played, not weighted by team pass
  attempts.
- The reference model is deliberately linear. It is a yardstick for whether an
  archetype is mispriced by ordinary metrics, not a projection system.
