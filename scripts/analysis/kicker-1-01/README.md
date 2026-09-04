# Would you spend the 1.01 on a kicker who never misses inside 60?

The question, off a post: your team uses the first overall pick on a kicker,
and in exchange he is guaranteed to make **every attempt of 60 yards or
closer** for his entire career. Worth it?

Short answer: he is worth about **one extra win a season, guaranteed**, and
the first overall pick has historically returned about **1.3 wins a season**
with a 41% chance of returning less than the kicker. It is a much closer
call than it sounds, and it is still not quite a good idea.

## Running it

```bash
pip install pandas pyarrow statsmodels scipy
python3 fetch_plays.py 1999 2025    # 27 season files, one at a time
python3 fetch_draft.py              # PFR draft-pick table via nflverse
python3 kicker_value.py > FINDINGS.txt
python3 pick_value.py   > PICK.txt
```

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
| perfect kicker, vs an average leg | **+0.94, guaranteed** |
| perfect kicker, vs a replacement leg | **+1.14, guaranteed** |
| 1.01 quarterback, mean 1999-2021 | +1.28 |
| 1.01 quarterback, median | +1.59 |
| best (Burrow) | +3.08 |
| 25th percentile (Vick, Bradford) | +0.10 |
| worst (JaMarcus Russell) | −0.65 |

41% of first overall quarterbacks since 1999 failed to clear the kicker's
1.14 over their rookie deal. The pick is a draw with a standard deviation of
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
