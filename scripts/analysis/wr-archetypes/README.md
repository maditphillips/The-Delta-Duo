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

## The three receivers, named

Parker Washington (JAX), Brian Thomas Jr. (JAX), Rome Odunze (CHI).

```bash
python3 profile.py "Parker Washington" "Brian Thomas Jr." "Rome Odunze" > PROFILES.txt
```

`profile.py` finds each receiver's nearest historical seasons on within-season
percentile ranks, weighted by |standardised coefficient| in a regression of next
season on the whole matching set — what each metric is worth *alongside* the
others. Weighting by solo predictive power instead would give age 0.8% of the
distance when the horse race says it is the second most valuable metric, and
would match a 22-year-old coming off a bad year to 31-year-olds coming off the
same bad year.

### Where the described profiles and the data disagree

**Parker Washington finished WR27, not WR8.** The five-big-games part is right —
his top five games were 55% of his points and the other eleven averaged 7.6 ppg.
The WR8 is a *stretch*, not a season: his last five games ran 15.4 ppg, a WR11
full-season pace, and his last eight ran 14.6, a WR13 pace. Over the whole year
he was WR27 with a health-adjusted pace of WR35.

**Brian Thomas Jr. matches exactly.** WR4 as a rookie, WR42 in year two, three
games missed. Worth separating what actually broke: his target share held
(25.5% → 19.3%, still 60th percentile) while his efficiency collapsed — 2.14 →
1.53 PPR per target, 9.64 → 7.77 yards per target, 0.41 → 0.19 EPA per target.
He lost the per-target production, not the role.

**Rome Odunze's efficiency is not fantastic, and his pace was not top-15.** The
target volume claim holds: 24% target share and 7.5 targets a game, 79th and 82nd
percentile. But 7.34 yards per target is 36th percentile and 1.62 PPR per target
is 31st. His health-adjusted finish is WR28, not top-15. The "very high finish"
impression comes from weeks 1-4, where he ran 19.9 ppg — a WR3 pace — against
8.3 ppg over weeks 6-13. The young teammate is Luther Burden III, who finished
WR49 as a 2025 rookie: real competition for targets, but not a strong finisher.

On the cohort definitions above, **none of the three is archetype C**. Odunze is
the closest and fails on both of the conditions that made that cohort look good —
top-18 healthy pace and top-third efficiency. He belongs in its control group:
hurt receivers in years 2-4 whose pace was outside WR18 finish at a median WR79
with a 6% top-12 rate.

### What the comparables say

Each receiver's 40 nearest seasons since 2009:

| | Year | 2025 | Median next | Top-12 | Top-24 | Model projection |
|---|---|---|---|---|---|---|
| Brian Thomas Jr. | 2 | WR42 | WR46 | **18%** | **32%** | **12.45 ppg (#18)** |
| Parker Washington | 3 | WR27 | WR47 | 8% | 15% | 11.29 ppg (#29) |
| Rome Odunze | 2 | WR41 | WR48 | 10% | 22% | 11.14 ppg (#31) |

**Thomas, then Odunze, then Washington** — the reverse of the archetype-level
answer, because two of the three do not match the profiles they were described
as. But the separation is thin. Over every ordered pair of comparable seasons,
Thomas's comps finish ahead of Washington's 53% of the time and Odunze's 53%;
Washington and Odunze split 50/50. The three have near-identical *median*
outcomes around WR46-48. What separates them is the upside tail, and Thomas owns
it at every neighbourhood size tested (top-24 rate 45% / 32% / 28% at k = 20 / 40
/ 80, against 30% / 22% / 30% for Odunze and 0% / 15% / 25% for Washington).

**Nothing Thomas did in 2025 supports him.** His 2025 rate metrics are the worst
of the three — 18th percentile in PPR per target, 38th in EPA per target. The
entire case is age (22.9, the youngest) and a WR4 season already banked, which
is exactly the pair of things the horse race says nothing else contains. Section
4(c): 15.7% of receivers coming off a sub-WR30 season with an earlier top-12
finish reach top-24 the next year, against 5.6% with no top-24 history.

**Washington ranks last despite the best 2025 finish** because he is the oldest
of the three, has the smallest target share (18%, 48th percentile), no pedigree,
and his season is built the way the study says carries no independent signal. His
nearest comps are a list of one-year role spikes: Willie Snead 2015 and 2016,
Gabe Davis 2022, Nelson Agholor 2017, Kenny Stills 2014, Quentin Johnston 2024.

### What this cannot see

Everything here is prior-season box score. It knows nothing about 2026 quarterback
play, scheme, or target competition. Two of the three are on the same team and
will take targets from each other; the `young_mate_finish` term sees only the 2025
room. Treat the numbers as a prior to be updated by offseason news, not a
forecast that has already priced it.

## Does it matter WHEN in the season the points arrived?

```bash
python3 timing.py > TIMING.txt
```

`fetch.py` also pulls the weekly injury report (2009-2025) and offensive snap
share (2012-2025), so "he was playing hurt" and "his role changed mid-season"
become columns rather than assertions. `timing.py` splits every season of 10+
games into the order it was actually played and asks whether the shape carries
anything.

**It does not. Nothing about timing survives.**

| Predictor of next-season ppg | cv R² |
|---|---|
| full-season points per game | **0.4557** |
| first half only | 0.3544 |
| second half only | 0.3778 |
| both halves as separate terms | 0.4539 |
| first four games only | 0.2800 |
| last four games only | 0.3182 |
| full season + last four | 0.4562 |
| full season + the first-to-second-half trend | 0.4555 |

Put both halves in one regression and they come out nearly equal — first half
+1.99 ppg/sd, second half +2.28. The second half is worth a shade more, and the
gap is far too small to justify throwing away the first. Add the trend on top of
full-season scoring and it contributes +0.078 ppg/sd (p = 0.47).

The same holds for every other way of measuring the fade:

| Trend measured on | Coefficient on next-season ppg | p |
|---|---|---|
| points per game | +0.086 ppg/sd | 0.58 |
| targets per game | −0.011 ppg/sd | 0.95 |
| snap share (2012+) | +0.174 ppg/sd | 0.17 |

Snap share *level* does add a little (+0.346 ppg/sd, p = 0.045) — the role he
holds matters. The *change* in it does not, and by quartile the receivers whose
snap share grew through the year finished slightly worse the following season
(median WR29, 42% top-24) than the ones whose role shrank (WR26, 50%).

**Touchdowns are the mechanism, and they are worth about a sixth as much.**
Strip receiving touchdowns out of the scoring rate and race the two:
non-touchdown points per game carries +3.69 ppg/sd against +0.57 for touchdown
rate — both real, but a point scored on a touchdown tells you roughly a sixth of
what a point scored on volume does. This is what a hot start usually is.

**Being shut down at the end of the year is not worse than being interrupted in
the middle.** Among receivers who missed 3+ games: shut down (n = 45) median next
WR88, 15.6% top-24; interrupted (n = 357) median WR87, 15.1%. Holding scoring rate
fixed, the shutdown flag moves next season by −0.11 ppg/sd (p = 0.62).

**Games played on the injury report do count for less — but not enough to act
on.** For the 462 receiver-seasons with at least four games on each side, points
per game off the report ran 12.39 against 11.29 on it. In one regression the
healthy games carry +2.88 ppg/sd against +1.17 for the games he entered listed —
so injury-report games really are the noisier half. But out of sample the split
(cv R² 0.424) does not beat simply averaging everything (0.428); the best you get
is full-season ppg *plus* off-report ppg, at 0.431. Being listed often is at most
a faint negative on its own (−0.27 ppg/sd, p = 0.09).

### What the 2025 logs actually say

**Rome Odunze was not hurt in week 6.** Chicago's bye was week 5. He first appears
on the injury report in **week 9** (heel, full participation in practice), adds an
ankle in weeks 10-11, and is listed with the season-ending foot injury from
**week 14**. His snap share never dropped below 76% and hit 100% in week 9. He
returned for both playoff games.

His season came apart in two separate pieces, and only the second one is about
health:

| | Games | Targets/g | Yards/target | TDs | PPG |
|---|---|---|---|---|---|
| weeks 1-4 | 4 | 8.8 | 8.46 | **5** | **19.90** |
| weeks 6-8 | 3 | 7.0 | **8.43** | 0 | 9.57 |
| weeks 9-13 (on the report) | 5 | 6.8 | 5.53 | 1 | 7.56 |

Weeks 6-8 are **pure touchdown regression**: identical yards per target, roughly
the same targets, five touchdowns became zero. The efficiency collapse only
arrives in week 9, alongside the heel. So the injury story is real but starts
three weeks after the fall does, and covers five games, not eight.

The other thing in those weeks was not injury either. Luther Burden III's snap
share went 17-29% through week 7 to 44-71% from week 8, and his target share 7.8%
to 12.9%. Odunze's own target share barely moved (24.7% weeks 1-7, 22.6% weeks
8-13). Burden's real takeover is weeks 14-18 with Odunze out — 21.1% target share
and 15.18 ppg — which is a 2026 concern, not a 2025 cause.

**Parker Washington's late surge is a role change, not five spike weeks.** He
played 24-33% of snaps in weeks 1, 2, 5 and 6 and 71-88% from week 7 on.

| | Games | Targets/g | Yards/target | PPG | Snap share |
|---|---|---|---|---|---|
| weeks 1-6 | 6 | 4.2 | 6.20 | 6.73 | ~44% |
| weeks 7-18 | 10 | 7.0 | 9.89 | **14.43** | ~75% |

That is a different thing from a spiky season, and it is the one honest argument
for weighting his back half. The tests above are the answer to it: no measure of
a role trend — points, targets or snaps — adds anything to full-season scoring.
The market will price his last ten games; the data says price the season.

**Brian Thomas Jr.'s slump preceded his injury.** He missed weeks 10-12 with an
ankle. Through week 9, before it, he was at 10.70 ppg on 7.5 targets a game — down
from 16.71 as a rookie. After returning, 8.87 ppg on 5.2 targets. The injury cost
him three games and made a bad year worse; it did not cause the drop.

### What this changes about the three

Nothing, which is the point. Every adjustment the three receivers' stories invite
— credit Odunze's hot start, credit Washington's promotion, discount Thomas's
injury — is one the data says not to make. Full-season points per game, age, and
what he has done before are still the whole model, and the ordering from the
comparables stands: Thomas, then Odunze, then Washington, all within a coin flip
of each other on median outcome.

The one legitimate adjustment sits outside the model. Burden's weeks 14-18 are a
forward-looking claim on Chicago's targets that a 2025 box score cannot see, and
Washington and Thomas will keep taking targets from each other in Jacksonville.
Those are offseason facts, not timing effects.

## The quarterback question, and which kind of decline comes back

```bash
python3 fetch_charting.py          # pbp joined to FTN charting, 2022-2025
python3 decline.py > DECLINE.txt
```

`fetch_charting.py` joins nflverse play-by-play to FTN's charting so every target
carries who threw it, whether the charters called it catchable, whether it was
contested, and whether it was dropped. That turns two arguments that are normally
assertions into measurements: *his good year was a backup quarterback* and *the
throws were bad*.

### "Thomas's rookie year was Mac Jones" is backwards

Jacksonville split 2024 almost evenly — Lawrence 287 dropbacks (weeks 1-9 and 13),
Mac Jones 265 (weeks 10-18 plus relief in 3, 6 and 13). Thomas by passer:

| Brian Thomas Jr. | Targets | Yds/target | PPR/target | aDOT | Catchable | Drop rate | Catch on catchable |
|---|---|---|---|---|---|---|---|
| 2024, Lawrence | 55 | **10.55** | **2.20** | 13.19 | 74.5% | 5.5% | 80.5% |
| 2024, Mac Jones | 80 | 8.78 | 1.93 | 10.54 | 71.2% | 2.5% | 94.7% |
| 2025, Lawrence | 91 | 7.77 | 1.44 | 14.45 | **74.7%** | **11.0%** | **70.6%** |

He was **better with Lawrence**, on a deeper route tree. The rookie season was not
a backup-quarterback illusion.

That cuts both ways, and the second edge is sharper. It removes the worry that his
WR4 season was fake — but it also removes the excuse for 2025, which happened with
the quarterback who had made him look best.

### The 2025 collapse was conversion, not opportunity and not the throws

Same offence, same quarterback, one season:

| 2025 Jacksonville | Targets | PPR/target | Catchable | Contested | Drop rate | Catch on catchable |
|---|---|---|---|---|---|---|
| Parker Washington | 97 | **1.78** | 66.0% | 19.6% | 4.1% | **90.6%** |
| Brian Thomas Jr. | 91 | 1.44 | **74.7%** | 24.2% | **11.0%** | **70.6%** |
| Jakobi Meyers | 60 | 1.78 | 71.7% | 18.3% | 3.3% | 95.3% |

Thomas got the **most catchable** targets on the team and converted them the
**worst** by a distance. That is not a quarterback problem and it is not a role
problem — his target share held at 19.3%. Washington, on the identical passer in
the identical offence, out-produced him by 24% per target.

### Does that kind of decline come back?

Two answers, pointing opposite ways.

**Drop rate barely persists, so the drops should mostly go away.** Year over year,
for receivers with 40+ targets in both seasons, r = +0.152 (R² = 0.023). The worst
decile of droppers averages 8.7% one year and **4.5%** the next, against a 3.7%
league mean. Drop rate also adds nothing to next-season prediction once points per
game is in (cv R² 0.4881 against 0.4884 without it).

**Catch rate on catchable balls persists much better** — r = +0.383, R² = 0.147,
six times the signal. That is the number Thomas is worst on, and it is the half
that carries forward.

And the historical base rate for his exact failure mode is not encouraging. Among
receivers whose points per game fell 20%+ from the prior year:

| | n | Median next | Top-24 | Fully recovered |
|---|---|---|---|---|
| lost the role only | 73 | WR88 | 15% | **18%** |
| kept the role, stopped converting | 101 | WR104 | 16% | **5%** |
| lost both | 105 | WR111 | 9% | 10% |
| every season with a prior year | 1,267 | WR65 | 22% | 38% |

"Fully recovered" means beating his season N−1 points per game two years later.
Losing the job and keeping it but not converting land in the same place on median
(p = 0.87), but the receivers who kept the job and stopped converting almost never
get back to what they were. Neither decomposition adds anything to plain points
per game as a predictor (d_share p = 0.18, d_eff p = 0.93) — the size of the fall
is what matters, not its anatomy.

### One thing this reframes about Odunze

Chicago throws him the hardest targets on the roster. His catchable rate was
**59.0%** in 2024 and **62.2%** in 2025, lowest among the Bears' pass catchers both
years, on the team's highest aDOT (13.65, 13.92). Luther Burden III's 2025 line —
10.97 yards per target, 2.08 PPR per target — came on an **89.8% catchable rate**
at a 7.78 aDOT. They are not doing the same job, which weakens the assumption that
Burden's finish comes straight out of Odunze's role.

### So is Thomas still the pick?

The premise fails but the conclusion mostly survives, by a different route.

The model's case for Thomas never rested on 2025 — it rested on age and an
already-banked WR4 season, and the quarterback split makes that pedigree *more*
credible, not less. Nothing in the model inputs changed.

What changed is the confidence around it. He has no quarterback excuse, his
failure is on the more persistent of the two conversion metrics, and a teammate
beat him per target on the same passer. Against that, the drops are the single
most regression-prone thing he could have been bad at.

Call it a coin flip between Thomas and Washington, which is what the comparables
said before any of this: over every ordered pair, Thomas's comps finish ahead of
Washington's **53%** of the time. Thomas keeps the wider range — 18% top-12
against 8% — so he is the pick where upside is what you are buying, and Washington
is the pick where you need the floor. Odunze sits between them and is the one whose
2026 depends most on something outside his control.

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
- The injury report says who was listed, not how hurt anyone was. A receiver can
  play through something he is never listed with, and the practice-participation
  field is the only severity signal in it.
- Snap counts start in 2012, so the snap-share tests run on 1,027 seasons rather
  than the full 1,502.
- FTN charting starts in 2022. The drop and catchable-ball work runs on 262
  receiver-seasons and three year-pairs, which is enough for a persistence
  estimate and not enough for anything finer.
- Catchable, contested and drop are charter judgements, not measurements. They
  are consistent within FTN's own work, which is what the year-over-year
  persistence test needs, but they are not ground truth.
