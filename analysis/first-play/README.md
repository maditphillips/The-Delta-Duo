# Does a team's first offensive play predict the game?

**Short answer:** almost not at all.

- **Yards on play one don't predict a team's other yards.** Correlation is 0.01. A 20+ yard
  first play is followed by about the same yardage as a 2-yard run.
- **A big first play does go with winning a bit more** (57% after 20+ yards, 46% after a
  loss). But that's the opening drive: a 20+ yard first play leads to points on that drive
  68% of the time vs 29% after zero or a loss. Hold the opening drive's points fixed and the
  first play predicts nothing (p = 0.64).
- **Head to head:** the team whose first play gained more won 52.1% of games (p = 0.04).
  Real, but tiny, and only noticeable when the gap is 20+ yards (59%).
- **Run vs pass on play one tells you almost nothing about play calling.** Run-first teams
  passed 58.2% of the rest of the game, pass-first teams 59.0%. In close games the gap is
  0.3 points and not significant. Teams that pass the most over a season don't pass first
  any more often than average.
- **Run vs pass doesn't predict the winner either.** Pass-first 50.7%, run-first 49.4%
  (p = 0.32). When one team passes first and the other runs, the passer wins 51.4% (p = 0.33).
- **Both pass / both run / one each:** no meaningful difference in total points, total yards
  or how close the game was.

Full output: `results.txt`. Charts: `yards_win_and_total.png`, `head_to_head.png`, `play_type.png`.

## Running it

```sh
./fetch.sh          # nflverse play-by-play 2016-2025 (~200 MB, gitignored)
python3 build.py    # -> team_games.csv (one row per team per game)
python3 analyze.py  # tables to stdout (saved as results.txt), -> summary CSVs
python3 plot.py     # -> PNGs
```

Needs pandas, numpy, scipy, statsmodels, pyarrow, matplotlib.

## Method

- **Sample.** Every 2016-2025 regular-season game with a final score: 2,639 games, 5,278
  team-games (the cancelled 2022 Bills-Bengals game is out).
- **First offensive play** = the team's first snap that counts as a run or pass. Plays wiped
  out by penalty, kneels, spikes and 2-point tries are skipped. A play with an accepted
  penalty that still counts (e.g. a run with offsetting holding) keeps its yards.
- **Run or pass goes by result:** a QB scramble is a run, a sack is a pass with its lost yards.
  Overall 44% of first plays are passes.
- **Rest-of-game yards and pass rate leave out the first play**, so it can't predict itself.
  Yards are net yards on runs and passes (sack yards subtracted).
- **Close-game pass rate** = quarters 1-3, score within 7, so game script isn't driving the calls.
- **Ties** count as half a win. Win models cluster by game (each game appears once per team).
- **No Vegas adjustment.** These are raw relationships.

## Files

| File | What it is |
|---|---|
| `team_games.csv` | one row per team per game: first play, totals, pass rates, score |
| `games.csv` | one row per game: both teams' first plays and the score |
| `by_first_yds.csv`, `by_type_and_yds.csv`, `by_first_down.csv` | win %, other yards, points, pass rate by first-play result |
| `head_to_head_gap.csv` | win % of the team with the bigger first play, by size of gap |
| `by_first_type.csv`, `win_by_both_types.csv`, `combos.csv` | the run/pass splits and the four game combos |
