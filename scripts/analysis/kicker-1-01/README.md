# Would you spend the 1.01 on a kicker who never misses inside 60?

The question, off a post: your team uses the first overall pick on a kicker,
and in exchange he is guaranteed to make **every attempt of 60 yards or
closer** for his entire career. Worth it?

Short answer: he is worth **0.94 wins a season if the coach uses him
optimally, 0.70 wins if the coach behaves the way real coaches actually
behave** when handed an elite leg. The first overall pick has historically
returned about **1.3 wins a season** with a 41% chance of returning less
than the kicker. Closer than it sounds, and still not a good idea.

## Running it

```bash
pip install pandas pyarrow statsmodels scipy
python3 fetch_plays.py 1999 2025    # 27 season files, one at a time
python3 fetch_draft.py              # PFR draft-pick table via nflverse
python3 kicker_value.py > FINDINGS.txt     # what the guarantee is worth
python3 pick_value.py   > PICK.txt         # what the 1.01 is worth
python3 opportunity.py  > OPPORTUNITY.txt  # does the extra work arrive?
python3 simple_rule.py  > RULE.txt         # the same thing, one plain rule
python3 threshold.py    > THRESHOLD.txt    # the 3-vs-7 break-even, swept
```

`epa_common.py` holds the shared expected-points machinery all three use.

`fetch_plays.py` writes `plays_1999_2025.parquet` (gitignored, ~100 MB):
every play from 1999 through 2025, 1.28 million of them, in the ~70 columns
these two scripts use. Each season's file is downloaded, trimmed and deleted,
so peak disk stays around 120 MB.

## Method

Everything is priced in **adjusted expected points added** and then converted
to wins with a points-per-win regression fit on the same seasons
(2018-2025: 35.8 points of season margin per win, R² = 0.81).

The one adjustment that matters: nflverse charges a scoring play only the
points it scored, and charges the ensuing kickoff to the kickoff play. A punt,
by contrast, already carries the cost of handing the ball over. So to compare
a field goal against a punt, the kickoff has to be charged back to the kick.
Every scoring play here is debited **K**, the expected points the opponent
gets from the possession that follows the score — measured directly from the
data (1.13 pre-2024, 1.39 after the dynamic kickoff), smoothed against the
clock so a kick as the half expires is credited the full 3.

The guarantee reaches the opponent's 42-yard line, because nflverse
`kick_distance` is `yardline_100 + 18`.

Value is counted in four channels, kept disjoint so nothing is double-counted:

| Channel | What it is | Points per team-season |
|---|---|---|
| 1 | the kicks he already takes: every miss inside 60 becomes a make | 17.8 |
| 3 | fourth downs inside the 42 where the team punted or went for it | 13.7 |
| 5 | extra points, a 33-yard kick, also inside the guarantee | 2.2 |
| 4 | halves that expired with the offence in range | 1.5, *not counted* |

Channel 3 is the interesting one and it needs a decision rule. Two are
reported throughout:

- **A, "take the free three."** The coach changes his behaviour in exactly
  one way: when a guaranteed make beats the expected value of the play he
  actually called, he kicks instead. Nothing else about the team changes.
- **B, "pure kicker premium."** Both teams are optimally coached and the only
  difference is who is kicking. The perfect team takes `max(perfect, go)`, the
  baseline team takes `max(average kicker, punt, go)`. B strips out the credit
  for fixing bad fourth-down decisions, so it lands lower.

The going-for-it baseline is selection-biased upward — coaches go for it when
they like their chances — which makes every number here a floor.

## Headline numbers

- **33.7 points a season, 0.94 wins** (A, against an average NFL leg).
  1.14 wins against a replacement leg, the baseline the quarterback
  comparison uses. 0.74 wins on the strict B definition. A frozen-history
  count of games that actually flip says 1.13.
- He is not mostly a better kicker, he is **a different weapon**. Only 17.8 of
  the 33.7 points come from making kicks a real kicker misses. The other half
  comes from the 4,366 fourth downs inside the opponent's 42 where teams
  punted or went for it — from the 38-to-42 yard line, teams punt 57% of the
  time and kick 6%.
- His workload goes from **1.92 to 2.46 attempts a game**.
- **The 60-yard line is the cliff.** Guaranteed to 55 yards he is worth 0.62
  wins; to 60, 0.94; to 65, 1.34. Almost all of that swing is channel 3,
  because 55 yards is inside where teams already kick and 65 is deep into
  where they still punt.
- Real kickers are not the problem people think. The median kicker-season
  leaves 16.1 points on the field; a top-decile season leaves 6.7. Make rates
  are up three points since 1999 and the points left over have barely moved,
  because attempts got longer at the same time.

## The other side of the trade

`pick_value.py` prices the first overall pick in the same currency: adjusted
EPA per snap for every quarterback taken 1.01 from 1999 on, against a
replacement quarterback (pooled rate of quarterback-seasons of 50-320 plays,
−0.106 adjusted EPA per play), over the five years of the rookie deal.

| | wins a season |
|---|---|
| perfect kicker, optimally used, vs an average leg | **+0.94, guaranteed** |
| perfect kicker, one simple rule (4th & 4+ inside the 42) | **+0.83, guaranteed** |
| perfect kicker, used the way coaches actually use one | **+0.70, guaranteed** |
| perfect kicker, vs a replacement leg | **+1.14, guaranteed** |
| 1.01 quarterback, mean 1999-2021 | +1.28 |
| 1.01 quarterback, median | +1.59 |
| best (Burrow) | +3.08 |
| 25th percentile (Vick, Bradford) | +0.10 |
| worst (JaMarcus Russell) | −0.65 |

41% of first overall quarterbacks since 1999 failed to clear the kicker's
1.14 over their rookie deal — 35% failed to clear 0.70. The pick is a draw with a standard deviation of
1.28 wins; the kicker is a certainty.

The obvious argument for the kicker is duration: the guarantee runs for his
whole career, while the pick's *surplus* runs only for the rookie deal. Ten
seasons at 0.94 wins is 9.4 wins, against 6.4 wins of rookie-deal surplus
from the average 1.01 quarterback.

**That argument does not survive a matched comparison.** Kickers in the top
quartile of career make rate last a median of 10 seasons as starters, 90th
percentile 17. Quarterbacks in the top quartile of career EPA per play last a
median of 10 and a 90th percentile of 17. Identical. The raw medians (5 for
kickers, 2 for quarterbacks) look like a kicker edge only because they are
dominated by people who were not good. Good players at both positions last a
long time, and the kicker's extra years are matched by a quarterback you keep
and pay — who is still better than the alternative once you do.

The 1.01 also buys optionality the kicker does not: you can trade it for
multiple firsts.

## The plain-English version: one rule on a wristband

`simple_rule.py` drops the expected-points arithmetic and uses a rule you
could tell a coach in one sentence: *inside the opponent's 42, if the league
converts this yards-to-go less than X% of the time, kick it — regardless of
how long the field goal is.*

Fourth-down conversion rates, 2018-2025. Third down at the same distance is
shown alongside, because fourth-down rates are flattered by selection —
coaches go for it when they like the look. They agree closely, which says the
selection problem is small:

| To go | 4th down, all field | 4th down, inside the 42 | 3rd down, all field |
|---|---|---|---|
| 4th & 1 | 67.6% | 65.5% | 69.2% |
| 4th & 2 | 58.6% | 60.2% | 57.5% |
| 4th & 3 | 51.3% | 50.8% | 51.2% |
| 4th & 4 | 49.9% | 51.0% | 47.7% |
| 4th & 5 | 47.2% | 41.6% | 42.5% |
| 4th & 6 | 41.3% | 38.0% | 41.6% |
| 4th & 7 | 42.4% | 37.3% | 36.5% |
| 4th & 8 | 36.0% | 30.1% | 33.4% |
| 4th & 9 | 27.2% | 25.0% | 30.1% |
| 4th & 10 | 29.9% | 26.3% | 27.8% |
| 4th & 11+ | 19.6% | 16.9% | 15.4% |

### What one guaranteed kick is actually worth

Before the rule sweep, the raw material. Every fourth down inside the 42 that
was not already a field goal, split by what the team actually did. "Gain" is
the points a guaranteed make adds over that choice:

| To go | Conv% | Went for it (per gm) | Gain vs going | Punted (per gm) | Gain vs punting |
|---|---|---|---|---|---|
| 4th & 1 | 65% | 1,480 (0.33) | **−0.99** | 10 (0.00) | +1.61 |
| 4th & 2 | 60% | 578 (0.13) | **−0.71** | 16 (0.00) | +1.69 |
| 4th & 3 | 51% | 372 (0.08) | −0.14 | 24 (0.01) | +1.78 |
| 4th & 4 | 51% | 292 (0.07) | −0.10 | 38 (0.01) | +1.70 |
| 4th & 5 | 42% | 197 (0.04) | **+0.59** | 43 (0.01) | +2.00 |
| 4th & 6 | 38% | 142 (0.03) | +0.91 | 46 (0.01) | +2.00 |
| 4th & 7 | 37% | 110 (0.02) | +0.82 | 70 (0.02) | +2.05 |
| 4th & 8 | 30% | 73 (0.02) | +1.27 | 75 (0.02) | +2.13 |
| 4th & 9 | 25% | 44 (0.01) | +1.64 | 73 (0.02) | +2.12 |
| 4th & 10 | 26% | 114 (0.03) | +1.56 | 79 (0.02) | +2.04 |
| 4th & 11+ | 17% | 160 (0.04) | +1.85 | 330 (0.07) | +2.25 |

**Replacing a punt with a guaranteed 3 wins at every distance.** All 804 of
them, worst single case +0.60, mean +2.10. Punting from the 39-42 is worth
−0.42 points; a guaranteed 3 from there is +1.73. Long punts are not the
problem.

**Replacing a go-for-it flips sign at 4th & 5.** At 4th & 1 the guaranteed 3
is worth 0.99 points *less* than going, because 65% of the time you get a
first down worth close to a touchdown. Of the 2,041 fourth downs where the
guaranteed kick loses points, **zero are punts** — every one is a go-for-it,
46% are inside the opponent's 10, and 76% are 4th & 1 or 4th & 2.

### The rule swept

Since the rate falls with distance, a threshold is the same thing as "kick on
fourth and N or longer". **Lower N means more kicking**: N=1 kicks on every
fourth down inside the 42, N=11 kicks only on fourth and 11 or longer. Each
row is the cumulative sum of the table above from N downward, and is charged
for its own mistakes.

| Kick if to-go ≥ | Conv% at N | Extra att/gm | Total att/gm | Bad kicks | Points/season | **Wins** | Same rule, normal leg |
|---|---|---|---|---|---|---|---|
| **1** (kick always) | 65% | 0.98 | 2.90 | 47% | 2.7 | 0.63 | 0.21 |
| **2** | 60% | 0.65 | 2.56 | 32% | 8.3 | 0.79 | 0.45 |
| **3** | 51% | 0.51 | 2.43 | 22% | 9.7 | 0.83 | 0.53 |
| **4** *(best)* | **51%** | **0.42** | **2.34** | **15%** | **9.7** | **0.83** | 0.56 |
| **5** | 42% | 0.35 | 2.27 | 9% | 9.6 | 0.83 | 0.59 |
| **7** | 37% | 0.25 | 2.17 | 4% | 8.0 | 0.78 | 0.60 |
| **9** | 25% | 0.18 | 2.10 | 0% | 6.1 | 0.73 | 0.59 |
| **11** | 17% | 0.11 | 2.03 | 0% | 4.0 | 0.67 | 0.58 |

**There is an interior optimum, and it is a 50% threshold.** Kick on fourth
and 4 or longer inside the 42 and the guarantee is worth **0.83 wins**.

Reading the columns: *extra att/gm* is new attempts per team-game on top of
the 1.92 teams already take. *Bad kicks* is the share of those new kicks
where the guaranteed 3 was worth less than the play the team actually called
— the rule's own mistakes, charged against its total. *Same rule, normal leg*
runs the identical rule with an average NFL kicker, so the gap between the
last two columns is the guarantee itself.

The rule gets worse in both directions, but not symmetrically. Going *more*
conservative than N=4 just leaves money on the table — every kick it skips
was worth having. Going *more* aggressive actively destroys value: at N=1,
47% of the extra kicks lose points, all of them short-yardage snaps near the
goal line where a touchdown was still live.

Where the value sits under that rule:

| From | Avg kick | Extra kicks/gm | Was a punt | Pts/kick | Pts/season |
|---|---|---|---|---|---|
| inside 15 | 27 yd | 0.06 | 0% | **−0.40** | −0.4 |
| 16-25 | 39 yd | 0.04 | 0% | +0.27 | +0.2 |
| 26-32 | 47 yd | 0.05 | 3% | +0.93 | +0.8 |
| 33-38 | 54 yd | 0.09 | 30% | +1.64 | +2.6 |
| **39-42** | **59 yd** | **0.18** | **77%** | **+2.14** | **+6.6** |

**9.2 of the 9.7 points come from between the 33 and the 42 — a 51-to-60 yard
kick — on 0.27 attempts a game.** Three-quarters of those snaps were punts.
Adding a "don't kick from inside the 25" clause cuts the bad kicks from 15% to
2% and is worth 0.01 wins, so the simple rule is already at its ceiling.

The cost of the simplicity is small: 0.83 wins for the rule against 0.94 for
deciding every fourth down on expected points.

## The 3-vs-7 break-even, and why it is not one number

The obvious shortcut: a touchdown is 7, a guaranteed field goal is 3, so
going for it needs `P x 7 > 3`, break-even `3/7 = 42.9%`. `threshold.py`
tests it.

**The premise is wrong in one place.** Converting a fourth down does not buy a
touchdown, it buys a *first down*, and a first down is worth wildly different
amounts depending on where you are:

| Fresh 1st & 10 at | Expected points |
|---|---|
| opponent's 10 | 5.08 |
| opponent's 20 | 4.89 |
| opponent's 30 | 4.09 |
| opponent's 42 | 3.38 |
| midfield | 2.88 |
| own 40 | 2.33 |

Never 7. Seven is what you get if the conversion *becomes* a touchdown, which
is a different event. Because the prize shrinks as you move back while the
field goal stays worth 3, **the break-even conversion rate rises as you move
away from the end zone**:

| Yard line | Convert (prize) | Fail (cost) | Guaranteed FG | **Break-even P\*** |
|---|---|---|---|---|
| inside 5 | +2.09 | −3.64 | −1.49 | **38%** |
| 5-10 | +2.49 | −3.20 | −1.05 | **38%** |
| 10-20 | +2.11 | −3.32 | −0.84 | **46%** |
| 20-32 | +2.28 | −3.19 | −0.11 | **56%** |
| 32-42 | +2.84 | −2.71 | +1.10 | **69%** |

All in adjusted EPA. `P* = (FG − fail) / (convert − fail)`. So inside the 10
you should go for it on nearly anything; out at the 42 you should kick on
nearly anything, because you would need to convert 69% of the time to beat a
guaranteed three, and nobody converts 69% of anything except 4th & 1.

### Sweeping the threshold over every fourth down in the game

One threshold `P*`: go for it if the league converts that yards-to-go at least
`P*`, otherwise kick (inside the 42) or punt (outside). `P* = 0` is go for it
all game; `P* = 100` is never go for it. **coach** is what the policy is worth
to any team with any kicker; **leg** is what the guarantee adds on top. They
add to the total.

| P\* | Go if to-go ≤ | Go% | Kick% | Punt% | FGA/gm | **coach** | **leg** | Total |
|---|---|---|---|---|---|---|---|---|
| 0 | always | 100 | 0 | 0 | 0.00 | −1.42 | +0.12 | −1.30 |
| 30% | 10 | 74.5 | 7.0 | 18.5 | 0.49 | −0.12 | +0.32 | +0.20 |
| 40% | 6 | 48.9 | 16.6 | 34.5 | 1.17 | +0.40 | +0.55 | +0.95 |
| **42.9%** *(3/7)* | **4** | 41.7 | 19.5 | 38.8 | 1.38 | **+0.46** | **+0.61** | **+1.07** |
| **50%** *(best)* | **3** | 26.5 | 26.1 | 47.4 | 1.85 | +0.41 | **+0.74** | **+1.15** |
| 55% | 2 | 19.0 | 29.6 | 51.4 | 2.09 | +0.30 | +0.81 | +1.11 |
| 60% | 1 | 11.5 | 33.1 | 55.4 | 2.34 | +0.13 | +0.87 | +1.00 |
| 100% | never | 0 | 38.8 | 61.2 | 2.74 | −0.45 | +0.96 | +0.51 |

The 3/7 rule lands inside the plateau — every threshold from 40% to 60% is
within 0.20 wins of the best — so the shortcut gets roughly the right answer
despite the wrong premise. Both ends of the sweep are where it costs you: go
for it on everything and you lose 1.30 wins.

Dropping the single-number rule entirely and taking the best of go/kick/punt
on every snap is worth +1.25 wins total (+0.55 coach, +0.71 leg). The whole
cost of using one number instead of thinking is **0.10 wins**.

### The split that matters

| | Wins/season | Record | Win rate |
|---|---|---|---|
| the leg, under the 3/7 rule | +0.61 | 9.1-7.9 | 53.6% |
| the leg, under the best threshold | **+0.74** | 9.2-7.8 | 54.4% |
| the leg, under perfect decisions | +0.71 | 9.2-7.8 | 54.2% |
| *plus* optimal fourth-down policy | +1.25 | 9.8-7.2 | 57.4% |
| 1.01 quarterback, mean | +1.28 | 9.8-7.2 | 57.5% |
| 1.01 quarterback, median | +1.59 | 10.1-6.9 | 59.4% |

**Optimal fourth-down policy is worth about half a win to any team with any
kicker.** It is free and it is not the kicker's. Blend the two and the kicker
appears to draw level with the 1.01; separate them and he is at 0.7 against
1.28.

Three independent routes — channel accounting (0.94), the plain yards-to-go
rule (0.83), and this policy sweep (0.74) — all land the guarantee between
0.7 and 0.9 wins. None of them reach the quarterback.

## Does the extra work actually arrive?

Half the kicker's value is coaches choosing to kick where they currently
punt. `opportunity.py` tests whether that ever happens, two independent ways.

**Case studies.** Ten teams that acquired an elite leg, the four seasons
before against the whole tenure, with the league's own drift subtracted
(everyone kicks from further out now — the contested-band kick rate went from
17.8% in 1999 to 48.7% in 2025):

| Team | Kicker | From | Δ attempts/game | Δ contested-band kick rate |
|---|---|---|---|---|
| DAL | Aubrey | 2023 | +0.16 | +17.5 pts |
| PIT | Boswell | 2015 | +0.13 | +11.0 |
| BAL | Tucker | 2012 | +0.09 | +8.5 |
| KC | Butker | 2017 | +0.05 | +9.7 |
| ATL | Koo | 2020 | −0.04 | −14.1 |
| **mean of 10** | | | **+0.10** | **+6.0** |

Dallas is the cleanest case: 52.9% → 81.4% of fourth downs in the 50-to-60
yard band kicked, raw. Baltimore's raw contested-band rate went 18.9% → 40.6%
across the Tucker era.

**Fixed-effects elasticity.** 682 team-seasons where the primary kicker had a
30+ attempt prior record. Kicker quality is career makes-above-expected per
attempt from *prior seasons only*, so this season's makes cannot drive this
season's attempt counts, and every spec carries team and season fixed effects
with errors clustered by team.

| Outcome | per 1 sd better kicker | extrapolated to a perfect leg |
|---|---|---|
| attempts per game | +0.026 | **+0.11** (p = 0.06) |
| 50+ yard attempts per game | +0.013 | +0.06 (p = 0.05) |
| mean attempt distance | +0.13 yd | +0.55 yd (p = 0.17) |
| contested-band kick rate | +1.3 pts | **+5.6 pts** (p = 0.07) |

The two methods land in the same place: **+0.10 to +0.11 attempts a game.**
A leg that never misses inside 60 would sit 4.3 standard deviations beyond
the best real kicker, so that extrapolation is generous already.

## The break-even

Rank every fourth down inside the 42 that a team punted or went for by how
much a guaranteed make beats the play they called, then take them best-first:

| Extra att/game | Attempts/season | Points/season | Marginal pts/att | Wins |
|---|---|---|---|---|
| 0.05 | 0.9 | 2.5 | 2.92 | 0.63 |
| **0.11** *(observed)* | 1.9 | 5.0 | 2.48 | **0.70** |
| 0.30 | 5.1 | 11.0 | 1.62 | 0.87 |
| **0.54** *(all of it)* | 9.2 | 13.7 | 0.38 | **0.94** |

Two things fall out.

**One: the 0.94 headline already assumes a coach five times more responsive
than any real coach has ever been.** Priced at observed behaviour, the
guarantee is worth 0.70 wins.

**Two: the fourth-down supply is not big enough to reach the quarterback,
even taking all of it.** The entire positive-value supply is 13.7 points;
channels 1 and 5 give 19.9; that is 0.94 wins, still 12.2 points short of the
mean 1.01 quarterback and 23.3 short of the median. Past 0.54 attempts a game
the marginal kick is worth 0.38 points and falling, and then it goes negative
— you are kicking where going for it was better.

So the gap has to be closed with *new possessions that reach the 42*, which
means the offence gaining yards it did not gain. Each one is worth 2.01
points, so he needs:

- **+6.1 more in-range possessions a season (+0.36 a game)** to match the
  mean 1.01 quarterback
- **+11.6 a season (+0.68 a game)** to match the median

The plain-rule version says the same thing more bluntly: no threshold reaches
the quarterback. Matching the mean 1.01 needs 25.8 points from new kicks, and
the best rule any threshold produces is 9.7.

on top of taking every fourth down. In raw volume: **2.84 attempts a game,
48 a season**, against a league average of 1.94. Only two teams in 27 seasons
have ever kicked that much once — 2011 San Francisco (52) and 2025 Houston
(52) — and break-even needs it every year, from an offence that has not
improved. That is 8.3x the behavioural response the data shows, or 11.4x to
match the median.

The supply of near-misses is at least real: teams punt 1.23 times a game from
just outside the guarantee, between the 43 and the 60. Turning those into
kicks is the unmodelled channel that would have to do the work.

## What is not in here

Pushing the number up: the offence would play differently on first through
third down, which is not modelled at all; the go-for-it baseline is biased
upward; the end-of-half channel is left out.

Pushing it down: the opponent adapts — punt coverage, two-minute defence and
their own fourth-down choices all change once the other side knows the 42 is
a scoring position, and none of that survives a frozen-history study.
Expected points also count garbage-time points at full value; restricting to
snaps with win probability between 10% and 90% cuts the total by about a
quarter.
