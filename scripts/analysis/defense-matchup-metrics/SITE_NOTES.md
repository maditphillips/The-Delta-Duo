# Matchup study — notes for the website

Source of every number: `FINDINGS.txt`, `MATCHUP_SIZE.txt`, `IMPLIED.txt`, `BOARD.txt`.

## Which metric ranks the defenses

"Soft" and "tough" always mean one metric per position, the one that tested best:

| Position | Metric |
|---|---|
| RB | RB scrimmage yards allowed per game (rushing + receiving yards by RBs) |
| WR | WR fantasy points allowed per game (PPR) |
| QB | QB fantasy points allowed per game |

Each is:
- **opponent-adjusted** — corrected for how good the offenses that defense has faced are, and
- **blended with last season**, which counts as 8 extra games. So by week 9 this
  season is about half the number; at week 2 it is mostly last season.

Defenses are then ranked 1-32 each week. "3 toughest" = ranks 30-32 that week.

## Headline numbers

| | RB | WR | QB |
|---|---|---|---|
| vs 3 toughest defenses that week | -13% | -10% | -14% |
| vs 3 softest defenses that week | +6% | 0% | +6% |
| True gap, softest 10% vs toughest 10% of defenses | 2.9 pts | 1.7 pts | 3.9 pts |
| Best-tenth vs worst-tenth matchup is worth this much season average | 2.6 pts | 1.4 pts | 5.0 pts |

% = points scored vs the player's own season average.

**How to read the last row:** an RB averaging 14 PPR against a bottom-tenth (toughest)
defense projects about the same as an RB averaging 11.4 against a top-tenth (softest)
one. For QBs the swing is 5 points of average.

**Scale:** even a 3-4 point higher season average only means outscoring the other
player about 60% of the time. Weekly scoring is very random, so every edge is small.

## Implied team total

- Break-even = the team's own usual implied total (league-wide that averages ~23).
- Per +1 point above the team's norm: RB +0.27 PPR, WR +0.13, QB +0.37.
- 3+ above norm = good spot (RB +9%, QB +7%, WR +3%); 3+ below = bad spot
  (RB -8%, QB -11%, WR -5%).

## Display options

**Player cards** (fits best with the weekly boards): one matchup chip per player.
- Defense rank vs his position this week (1-32), coloured soft / neutral / tough.
- Implied total vs team norm, e.g. "24.5 implied, +3.0 vs usual".
- Only call out the extremes (bottom 3 / top 3 defenses, or 3+ points off the
  implied norm). Everything in between is close to noise.

**Own tab**: the weekly board (32 defenses x QB / RB / WR) plus the study's
findings — the deciles chart and the "tough hurts more than soft helps" point.

Both can read one weekly JSON built by `board.py`.
