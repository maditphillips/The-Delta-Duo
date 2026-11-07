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
