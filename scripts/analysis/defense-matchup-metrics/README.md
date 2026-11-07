# Which defensive metric best predicts a fantasy matchup?

For running backs, wide receivers and quarterbacks: which number about the
opposing defense — EPA per play, EPA in competitive games, yards allowed, TDs
allowed, fantasy points allowed, and ~50 others — best tells you before kickoff
whether a player will beat or miss his usual output?

## Answer

| Position | Use this | Avoid leaning on | Softest vs toughest quarter of defenses |
|---|---|---|---|
| **RB** | **RB scrimmage yards allowed / game** (rush + receiving yards by RBs). RB fantasy points allowed and rush yards allowed / game are close behind. | EPA / rush in competitive games, rush TDs allowed | about **+1.8 PPR pts** |
| **WR** | Nothing works well. Opponent-adjusted **WR fantasy points allowed** or **QB fantasy points allowed** are least bad. | All of them, for start/sit | about **+0.8-1.0 PPR pts** |
| **QB** | Opponent-adjusted **QB fantasy points allowed**, **EPA / dropback**, **ANY/A allowed** or **points allowed** — a four-way tie. | Sack rate, INT rate, pass TDs allowed | about **+2.0 PPR pts** |

Full numbers: `FINDINGS.txt`. Current-season board built from these picks: `BOARD.txt`.

### What the data says

1. **Matchups matter less than most fantasy content implies.** The best metric
   for any position explains about 1% of a player's week-to-week over/under
   (correlation ~0.10). A player's weekly score swings by ~7.5 PPR points; the
   matchup moves the average by ~2. Use matchups to break ties between similar
   players, not to bench a clearly better one.

2. **RB: volume beats efficiency.** Per-game yardage allowed to RBs predicts
   better than any per-play efficiency stat. EPA / rush in competitive games —
   the metric in the question — ranks near the bottom of the rushing group
   (r 0.05 vs 0.10). It is also one of the least stable (odd-week vs even-week
   reliability 0.18; the stricter "neutral" version is 0.09): filtering to
   competitive snaps throws away a large share of an already small sample. RB fantasy output depends on how many
   carries and targets the back gets, and that depends on game script, which
   per-game totals capture and per-play rates don't.

3. **Overall defense quality beats run-defense quality for RBs.** EPA / play
   allowed (all plays) and EPA / dropback both beat EPA / rush. Backs score
   more against bad defenses overall, because their team leads, runs more and
   reaches the red zone more.

4. **TDs allowed are noise.** TDs allowed are among the least stable numbers
   in the study (reliability 0.05-0.19) and the weakest of the metrics asked
   about at every position.

5. **WR matchups are close to unpredictable from defense-level data.** Even in
   hindsight — measuring the defense on every other game that season — the
   best correlation is 0.04. Defenses do shift the *total* WR room output
   (team-level r ≈ 0.09), but which receiver gets those points is random from
   the defense's side. Cornerback/shadow matchups, which this data cannot see,
   are the likely missing piece.

6. **QB: almost any good summary of pass defense works.** Fantasy points
   allowed, EPA / dropback, ANY/A and points allowed all land at r ≈ 0.10. The
   competitive-game filter does not help. Pressure stats (sack rate, hit rate)
   work in the right direction but are weaker.

7. **Opponent adjustment helps a little for WR and QB, not for RB.** Adjusting
   for the offenses a defense has faced moves WR from 0.032 to 0.040 and QB
   from 0.098 to 0.103. For RB the raw number is already as good.

8. **Use last season's number early, and keep some of it all year.** In weeks
   2-4, last season's number beats this season's at every position. Even late
   in the year, blending this season with last season (counted as ~8 extra
   games) beats this season alone. `BOARD.txt` does this.

9. **Vegas is as good as the best defensive metric.** The offense's implied
   team total *relative to its usual implied total* matches or beats every
   defensive metric (RB 0.101, WR 0.044, QB 0.109). Adding the best defensive
   metric to it lifts out-of-sample R² from ~1.0% to ~1.35% for RB and QB, so
   both are worth checking.

## How big is a matchup, really? (`MATCHUP_SIZE.txt`)

Correlation understates it, because one game's score is so noisy. Measured other ways:

| | RB | WR | QB |
|---|---|---|---|
| True spread of defenses (sd, noise removed) | 1.1 PPR | 0.7 PPR | 1.5 PPR |
| Softest 10% vs toughest 10% of defenses, true gap | 2.9 PPR | 1.7 PPR | 3.9 PPR |
| 3 toughest defenses that week, vs baseline | -12.9% | -10.5% | -13.6% |
| 3 softest defenses that week, vs baseline | +6.4% | -0.2% | +6.2% |
| Best-vs-worst-tenth matchup is worth this much baseline | 2.6 pts | 1.4 pts | 5.0 pts |
| Similar players: softer matchup outscores the other (largest 5% of gaps) | 57.6% | 53.8% | 57.5% |

- **Matchups are real but modest.** The true difference between the softest
  and toughest defenses is about 3 PPR for an RB and 4 for a QB — 10-15% of a
  typical baseline. Correlations look tiny only because a single game swings
  by ~7.5 points either way. For scale: a 3-4 point gap in season average
  only picks the higher scorer 58-62% of the time.
- **Tough matchups hurt more than soft ones help.** The 3 toughest defenses
  cost RBs and QBs ~13%; the 3 softest add ~6%. For WRs the soft side adds
  nothing. Use matchups mainly to *avoid* bad spots, not to chase good ones.
- **The board metric captures ~60% of the true signal.** The rest is lost to
  measuring defenses on small samples. No defensive stat can get much better.

## Vegas implied totals (`IMPLIED.txt`)

**Short answer: the threshold is the player's own team's usual implied total,
not one fixed number.** If you need one number, it's **~23 points** (the league
average): players on teams implied above 23 beat their average slightly, below
23 they miss it. But that hides the real pattern:

| Team's usual implied total | Break-even (RB / WR / QB) |
|---|---|
| under 21 (avg 19.5) | 18.0 / 19.9 / 19.0 |
| 21 to 24 (avg 22.6) | 22.2 / 21.8 / 22.3 |
| 24+ (avg 25.9) | 27.1 / 27.2 / 27.4 |

So a 24-point total is a good spot for a player on a weak offense and a bad
one for a player on an elite offense. Compare this week's implied total with
the team's average implied total so far this season:

| Implied vs team norm | RB | WR | QB |
|---|---|---|---|
| 5+ below | -15.7% | -9.3% | -17.2% |
| 3 to 5 below | -8.4% | -5.1% | -11.0% |
| within 1 | -0.6% | +1.1% | -0.3% |
| 3 to 5 above | +9.2% | +3.1% | +7.3% |
| 5+ above | +12.8% | +3.7% | +10.3% |
| **PPR per +1 point vs norm** | **+0.27** | **+0.13** | **+0.37** |

Rule of thumb: 3+ points above the team's norm is a good matchup, 3+ below is
a bad one. The break-even has not moved between 2012-17 and 2018-25.

### Does the weekly model already use this? (`IMPLIED_IN_MODEL.txt`)

The in-season model (`model/dd/inseason.py`, weekly-rankings branch) reads the
raw implied team total, spread and game total. It has no "vs team norm" column.
`implied_in_model.py` tests that without changing the model: it reruns the
model's own 2022-2025 backtest three ways.

| | QB | RB | WR | TE |
|---|---|---|---|---|
| A. model as shipped (ranking accuracy) | 0.8191 | 0.8514 | 0.8115 | 0.7976 |
| B. + implied vs team norm as an input | -0.0001 | +0.0001 | -0.0001 | -0.0006 |
| C. A x percentage adjustment | -0.0000 | -0.0001 | -0.0001 | -0.0004 |

**No gain.** The model already prices it. Its misses do not follow the
implied-vs-norm gap, and the fitted adjustment is under 1% per point and points
the wrong way for QB and WR. The reason: the model sees each player's own usage
and production, which already encodes his team's usual scoring level, plus
this week's raw implied total. The gradient-boosted model learns the
difference itself.

So the implied-vs-norm finding is worth *showing* (it explains why a projection
moved), not adding to the model.

## Method

**Target.** For each player-game, PPR points minus that player's average in
his other regular-season games that season (needs 4+ other games). This removes
player quality so only the matchup is left. Included: RBs and WRs with a 7+ PPR
baseline who touched the ball; QBs who were the listed starter with a 10+
baseline. 2012-2025, weeks 5+: 7,912 RB, 12,043 WR and 4,905 QB games.

**Predictor.** Each defensive metric measured only from that defense's games
*before* kickoff — what you'd actually have that week. Rates are play-weighted.
Opponent-adjusted versions subtract how far above or below league average each
offense faced was in its other games.

**Score.** Pearson r between metric and over/under, computed per season and
averaged across 14 seasons (±95% across seasons). "Soft-tough" is the average
over/under against the softest quarter of defenses that week minus the
toughest quarter. "Stab" is how well a defense's odd-week number predicts its
even-week number — a metric that doesn't agree with itself can't predict
anything.

**Checks** (`FINDINGS.txt` section G). Rankings hold under standard scoring, a
baseline from earlier games only (no hindsight), star players only, weeks 10+
only, and with the whole position room as the unit instead of one player.

**Competitive / neutral.** "Competitive" = win probability 10-90% at the snap.
"Neutral" = 20-80% and not in the final two minutes of a half.

## Running it

```bash
pip install pandas pyarrow scipy
python3 fetch.py               # nflverse pbp, weekly player stats, schedules with lines, 2011-2026
python3 build.py               # -> team_games.parquet, player_games.parquet
python3 analyze.py > FINDINGS.txt
python3 board.py > BOARD.txt   # current-season matchup board
python3 matchup_size.py > MATCHUP_SIZE.txt
python3 implied.py > IMPLIED.txt
DD_MODEL=/path/to/model python3 implied_in_model.py > IMPLIED_IN_MODEL.txt   # needs the weekly model's data built
```

Data lands in `.data/` (gitignored, ~30 MB). `DMM_DATA=/some/path` moves it.
`fetch.py` re-downloads the in-progress season every run so the board stays
current. `analyze.py` takes about 40 seconds.

## Limitations

- **No coverage or personnel data.** Cornerback matchups, slot vs outside, and
  defensive injuries are invisible here. That is most likely why WR is so weak.
- **Baseline uses the full season.** A player's role can change mid-season
  (injury to a teammate, trade). The trailing-baseline check (section G) gives
  the same ranking, so this does not change the answer.
- **Additive, not proportional.** The over/under is in points, not percent. A
  soft matchup may help a star more in raw points; the star-only check shows
  rankings are the same.
- **TE not covered**, though TE fantasy points allowed is computed and can be
  added to the targets in `analyze.py`.
