# 2026 season simulation: fantasy finish odds

nflseedr simulates the rest of a season game by game to get playoff odds. This does
the same thing for **fantasy finishes**: it takes 2026 as it stands after week 3,
simulates the remaining 15 weeks 10,000 times, and counts how often each player
finishes #1, top 12, top 24, etc. at his position (full PPR, regular season).

Results for every player: `sim_2026.csv`. Charts (made with nflplotR):

![QB](plots/finish_odds_qb_2026.png)
![RB](plots/finish_odds_rb_2026.png)
![WR](plots/finish_odds_wr_2026.png)
![TE](plots/finish_odds_te_2026.png)

## Running it

```sh
./fetch.sh                                   # nflverse schedule + weekly player stats, 2020-2026
python3 fit.py 3 2025                        # fit on 2022-2025 at week 3   -> params_2025.json
python3 sim.py 2026 params_2025.json 10000   # simulate 2026               -> sim_2026.csv
Rscript plot.R 2026                          # charts                      -> plots/*.png

# out-of-sample checks
python3 fit.py 3 2024 && python3 calibrate.py 2025 params_2024.json
python3 fit.py 3 2023 && python3 calibrate.py 2024 params_2023.json
```

The simulation is Python standard library only. The charts need R with `ggplot2` and
`nflplotR` (`install.packages("nflplotR")`); team logos ship inside nflplotR. 10,000 seasons run in about 6 seconds. To update after week 4,
rerun `fetch.sh`, then `fit.py 4 2025`, `sim.py` and `plot.R`.

## Method

1. **Pool.** Every QB, RB, WR and TE who recorded a stat in weeks 1–3. Team is his
   team in his latest game; team games left come from the 2026 schedule (byes handled).
2. **Expected points per remaining team game.** A linear regression per position,
   fit on 2022–2025 at the same point in the season (after week 3). Inputs: PPR
   points per game so far, share of games played so far, last season's points per game
   and games played, and two seasons ago's points per game. The target counts missed
   games as zero, so injury risk is built in. It beats "keep scoring at this pace":

   | | QB | RB | WR | TE |
   |---|--:|--:|--:|--:|
   | Model error (pts/game, RMSE) | 5.3 | 3.6 | 3.3 | 2.5 |
   | "Same pace" error | 7.2 | 4.7 | 4.7 | 3.3 |

   Rough weights: each point of this season's pace is worth about 0.2–0.4 points of
   expectation and each point of last season's about 0.2–0.3 (QB: under 0.1, where
   being a full-time starter last year matters more than how well he scored). The
   rest is pulled toward the position average. Three weeks is not much signal.
3. **Uncertainty.** Each simulated season, each player gets his expected rate plus an
   error drawn from the 40 backtest players whose expectation was closest to his
   (how far off they actually came in). That one draw covers injury, role change and
   simply playing better or worse. Points already scored are kept.
4. **Finish.** Rank season totals within position in every simulation and count.

## Does it work?

Simulate a finished season from week 3 using a fit that never saw that season, then
check the odds against what happened. "Skill" is improvement over guessing the base
rate (0 = no better, 1 = perfect).

| Season tested | QB top 12 | RB top 24 | WR top 24 | TE top 12 |
|---|--:|--:|--:|--:|
| 2025 (fit on 2022–24) | +0.46 | +0.40 | +0.35 | +0.37 |
| 2024 (fit on 2022–23) | +0.37 | +0.53 | +0.20 | +0.37 |

Calibration is reasonable for the sample size: in 2025, RB-top-24 calls of 30–50%
came in 44% of the time, WR-top-36 calls of 70–90% came in 74%. WR top 12 is the
weakest call (skill +0.09 in 2024). Full bins: `python3 calibrate.py`.

Only 2 of 240 actual top-24/top-36 finishers in the two test seasons were missing from the
week-1–3 pool, so leaving out not-yet-active players costs little.

## Known injuries: `overrides.csv`

General injury risk is already built in (the backtest counts missed games as zero).
A specific injury is not, so enter it by hand: `player,team,out_min,out_max,note`.
Each simulated season draws a whole number of missed games between `out_min` and
`out_max` (inclusive, equally likely) and those games score zero. Names must match
nflverse exactly; `sim.py` warns if one doesn't. Remove the row once he's back.

Currently: **Breece Hall** (NYJ), quad injury in week 3, week-to-week, did not
practice in week 4 -> misses 1-3 games. It moves him from median RB19 to RB23 and
his top-24 odds from 66% to 54%.

## Caveats

- **Little news.** Beyond `overrides.csv`, the model sees box scores only. It does
  not know about depth-chart changes, trades, or a player returning from IR. Anyone
  who has not played yet in 2026 is not in the pool.
- **Players are independent.** If a WR1 gets hurt, his teammates do not get a bump in
  the same simulation, and there is no team-level boom or bust shared by teammates.
  nflseedr's game-by-game structure would add that; this version does not.
- **Rookies** get only their 2026 games plus the position average, so they are
  pulled hard toward the middle.
- Two backtest seasons is a small check. Treat odds near 50% as coin flips with lean.

## 2026 after week 3: top 15 at each position

**QB**

| Player | Tm | Pts wk 1–3 | Median total (10th–90th) | Median finish | #1 | Top 6 | Top 12 | Top 24 |
|---|---|--:|--:|--:|--:|--:|--:|--:|
| Josh Allen | BUF | 93.9 | 386 (212–449) | 2 | 49% | 77% | 84% | 99% |
| Brock Purdy | SF | 80.9 | 303 (193–380) | 7 | 8% | 43% | 75% | 92% |
| Jared Goff | DET | 65.6 | 311 (143–380) | 7 | 8% | 45% | 70% | 88% |
| Bryce Young | CAR | 69.2 | 301 (200–369) | 9 | 5% | 36% | 70% | 92% |
| Patrick Mahomes | KC | 66.6 | 293 (133–385) | 9 | 6% | 36% | 68% | 89% |
| Dak Prescott | DAL | 63.1 | 288 (129–366) | 10 | 4% | 32% | 64% | 88% |
| Lamar Jackson | BAL | 60.2 | 287 (179–381) | 10 | 5% | 32% | 62% | 89% |
| Tyler Shough | NO | 69.4 | 280 (159–353) | 10 | 2% | 28% | 60% | 88% |
| Jalen Hurts | PHI | 53.5 | 280 (170–371) | 11 | 3% | 28% | 58% | 88% |
| Trevor Lawrence | JAX | 52.0 | 266 (136–335) | 13 | 1% | 20% | 48% | 84% |
| Matthew Stafford | LA | 52.0 | 264 (135–358) | 13 | 2% | 21% | 46% | 84% |
| Bo Nix | DEN | 43.7 | 246 (132–348) | 15 | 1% | 18% | 39% | 83% |
| Jordan Love | GB | 51.8 | 242 (132–348) | 16 | 1% | 17% | 37% | 79% |
| Geno Smith | NYJ | 50.9 | 237 (127–343) | 17 | 1% | 16% | 35% | 75% |
| Deshaun Watson | CLE | 54.0 | 240 (94–335) | 17 | 1% | 17% | 36% | 67% |

**RB**

| Player | Tm | Pts wk 1–3 | Median total (10th–90th) | Median finish | #1 | Top 12 | Top 24 | Top 36 |
|---|---|--:|--:|--:|--:|--:|--:|--:|
| Jahmyr Gibbs | DET | 98.3 | 414 (324–495) | 1 | 57% | 99% | 100% | 100% |
| Bijan Robinson | ATL | 77.7 | 357 (272–436) | 3 | 17% | 96% | 99% | 100% |
| Derrick Henry | BAL | 74.9 | 329 (239–410) | 4 | 9% | 92% | 98% | 100% |
| Kenneth Walker III | KC | 79.2 | 321 (236–400) | 5 | 7% | 90% | 98% | 100% |
| Jonathan Taylor | IND | 63.5 | 310 (217–390) | 5 | 5% | 86% | 97% | 100% |
| Christian McCaffrey | SF | 58.0 | 293 (200–372) | 6 | 3% | 81% | 96% | 99% |
| James Cook | BUF | 50.2 | 258 (150–339) | 9 | <1% | 66% | 87% | 96% |
| Kyren Williams | LA | 53.0 | 258 (152–302) | 9 | 1% | 66% | 87% | 97% |
| D'Andre Swift | CHI | 56.1 | 254 (140–319) | 11 | 1% | 58% | 82% | 96% |
| Ashton Jeanty | LV | 55.3 | 247 (138–317) | 11 | 1% | 57% | 82% | 95% |
| Chuba Hubbard | CAR | 53.1 | 214 (126–299) | 15 | <1% | 41% | 75% | 93% |
| Javonte Williams | DAL | 50.5 | 225 (145–278) | 15 | <1% | 40% | 76% | 95% |
| Chase Brown | CIN | 38.9 | 200 (117–285) | 18 | <1% | 30% | 69% | 90% |
| Bucky Irving | TB | 41.1 | 194 (91–259) | 20 | <1% | 25% | 63% | 83% |
| David Montgomery | HOU | 40.1 | 193 (96–241) | 21 | <1% | 19% | 58% | 78% |

**WR**

| Player | Tm | Pts wk 1–3 | Median total (10th–90th) | Median finish | #1 | Top 12 | Top 24 | Top 36 |
|---|---|--:|--:|--:|--:|--:|--:|--:|
| Jaxon Smith-Njigba | SEA | 104.1 | 396 (267–489) | 1 | 55% | 95% | 100% | 100% |
| Amon-Ra St. Brown | DET | 75.8 | 316 (188–409) | 3 | 14% | 83% | 89% | 95% |
| Chris Olave | NO | 70.5 | 279 (164–372) | 5 | 6% | 78% | 87% | 92% |
| CeeDee Lamb | DAL | 70.9 | 282 (167–375) | 6 | 7% | 77% | 88% | 93% |
| Davante Adams | LA | 65.8 | 271 (156–364) | 6 | 5% | 73% | 87% | 91% |
| Ja'Marr Chase | CIN | 54.5 | 267 (154–360) | 7 | 5% | 70% | 88% | 91% |
| Christian Watson | GB | 69.4 | 251 (136–324) | 9 | 3% | 60% | 81% | 87% |
| Garrett Wilson | NYJ | 57.3 | 230 (116–301) | 13 | 1% | 48% | 74% | 86% |
| DeVonta Smith | PHI | 48.5 | 224 (124–260) | 15 | <1% | 38% | 70% | 86% |
| Zay Flowers | BAL | 41.4 | 223 (110–296) | 16 | 2% | 38% | 68% | 84% |
| Tee Higgins | CIN | 44.4 | 222 (135–255) | 16 | <1% | 33% | 71% | 86% |
| Drake London | ATL | 42.8 | 222 (124–261) | 17 | <1% | 33% | 71% | 86% |
| Rashee Rice | KC | 38.0 | 214 (138–250) | 17 | <1% | 29% | 70% | 84% |
| Justin Jefferson | MIN | 44.9 | 216 (119–255) | 18 | <1% | 28% | 67% | 84% |
| Stefon Diggs | WAS | 44.5 | 213 (140–246) | 18 | <1% | 28% | 68% | 83% |

**TE**

| Player | Tm | Pts wk 1–3 | Median total (10th–90th) | Median finish | #1 | Top 6 | Top 12 | Top 24 |
|---|---|--:|--:|--:|--:|--:|--:|--:|
| Trey McBride | ARI | 59.1 | 250 (209–347) | 2 | 38% | 88% | 99% | 100% |
| Brock Bowers | LV | 27.6 | 207 (166–299) | 6 | 15% | 57% | 85% | 100% |
| George Kittle | SF | 47.4 | 211 (146–289) | 7 | 11% | 48% | 78% | 99% |
| Travis Kelce | KC | 49.1 | 200 (146–284) | 8 | 10% | 43% | 73% | 97% |
| Juwan Johnson | NO | 48.3 | 188 (133–266) | 10 | 6% | 35% | 61% | 93% |
| Dalton Kincaid | BUF | 44.3 | 178 (117–254) | 12 | 4% | 29% | 51% | 85% |
| Tyler Warren | IND | 39.4 | 169 (115–253) | 13 | 3% | 27% | 49% | 84% |
| Harold Fannin Jr. | CLE | 38.6 | 169 (114–252) | 13 | 3% | 27% | 49% | 83% |
| Dalton Schultz | HOU | 39.5 | 163 (108–246) | 14 | 2% | 25% | 46% | 79% |
| Sam LaPorta | DET | 34.4 | 162 (100–233) | 16 | 1% | 21% | 41% | 73% |
| Isaiah Likely | NYG | 39.4 | 154 (96–232) | 16 | 1% | 20% | 40% | 74% |
| Kenyon Sadiq | NYJ | 38.6 | 151 (89–216) | 17 | <1% | 15% | 38% | 71% |
| Dallas Goedert | PHI | 25.1 | 147 (93–225) | 18 | 1% | 18% | 36% | 67% |
| Jake Ferguson | DAL | 32.2 | 156 (94–227) | 18 | 1% | 18% | 35% | 66% |
| Pat Freiermuth | PIT | 28.1 | 144 (83–217) | 18 | <1% | 13% | 34% | 65% |
