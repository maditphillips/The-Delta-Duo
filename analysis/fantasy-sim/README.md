# 2026 season simulation: fantasy finish odds

nflseedr simulates the rest of a season game by game to get playoff odds. This does
the same thing for **fantasy finishes**: it takes 2026 as it stands after week 4,
simulates the remaining 14 weeks 10,000 times, and counts how often each player
finishes #1, top 12, top 24, etc. at his position (full PPR, regular season).

Results for every player: `sim_2026.csv`. Charts (made with nflplotR):

![QB](plots/finish_odds_qb_2026.png)
![RB](plots/finish_odds_rb_2026.png)
![WR](plots/finish_odds_wr_2026.png)
![TE](plots/finish_odds_te_2026.png)

## Running it

```sh
./fetch.sh                                   # nflverse schedule + weekly player stats, 2020-2026
python3 fit.py 4 2025                        # fit on 2022-2025 at week 4   -> params_2025.json
python3 sim.py 2026 params_2025.json 10000   # simulate 2026               -> sim_2026.csv
Rscript plot.R 2026                          # charts                      -> plots/*.png

# out-of-sample checks
python3 fit.py 4 2024 && python3 calibrate.py 2025 params_2024.json
python3 fit.py 4 2023 && python3 calibrate.py 2024 params_2023.json
```

The simulation is Python standard library only. The charts need R with `ggplot2` and
`nflplotR` (`install.packages("nflplotR")`); team logos ship inside nflplotR. 10,000 seasons run in about 6 seconds. To update after week 5,
rerun `fetch.sh`, then `fit.py 5 2025`, `sim.py` and `plot.R`. Update `overrides.csv`
first: a player who sat out the week has one fewer game left to miss.

## Method

1. **Pool.** Every QB, RB, WR and TE who recorded a stat in weeks 1–4. Team is his
   team in his latest game; team games left come from the 2026 schedule (byes handled).
2. **Expected points per remaining team game.** A linear regression per position,
   fit on 2022–2025 at the same point in the season (after week 4). Inputs: PPR
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
   rest is pulled toward the position average. Four weeks is not much signal.
3. **Uncertainty.** Each simulated season, each player gets his expected rate plus an
   error drawn from the 40 backtest players whose expectation was closest to his
   (how far off they actually came in). That one draw covers injury, role change and
   simply playing better or worse. Points already scored are kept.
4. **Finish.** Rank season totals within position in every simulation and count.

## Does it work?

Simulate a finished season from week 3 or 4 using a fit that never saw that season,
then check the odds against what happened. "Skill" is improvement over guessing the
base rate (0 = no better, 1 = perfect).

| Season tested | From week | QB top 12 | RB top 24 | WR top 24 | TE top 12 |
|---|--:|--:|--:|--:|--:|
| 2025 (fit on 2022–24) | 3 | +0.46 | +0.40 | +0.35 | +0.37 |
| 2025 (fit on 2022–24) | 4 | +0.55 | +0.46 | +0.37 | +0.43 |
| 2024 (fit on 2022–23) | 3 | +0.37 | +0.53 | +0.20 | +0.37 |
| 2024 (fit on 2022–23) | 4 | +0.42 | +0.58 | +0.30 | +0.41 |

One more week of data helps everywhere. Calibration is reasonable for the sample
size: from week 3 in 2025, RB-top-24 calls of 30–50% came in 44% of the time and
WR-top-36 calls of 70–90% came in 74%. WR top 12 is the weakest call (skill +0.09
from week 3 in 2024). Full bins: `python3 calibrate.py`.

At most 2 of 240 actual top-24/top-36 finishers in a test were missing from the
early-season pool, so leaving out not-yet-active players costs little.

## Known injuries: `overrides.csv`

General injury risk is already built in (the backtest counts missed games as zero).
A specific injury is not, so enter it by hand: `player,team,out_min,out_max,note`.
Each simulated season draws a whole number of missed games between `out_min` and
`out_max` (inclusive, equally likely) and those games score zero. Names must match
nflverse exactly; `sim.py` warns if one doesn't. Remove the row once he's back. For a season-ending injury set both to his team's games left.

Currently:

| Player | Expected absence | Missed so far | Still to miss |
|---|---|---|---|
| Breece Hall (NYJ) | 1-3 games (quad, week 3) | week 4 | 0-2 games |
| Travis Etienne (NO) | 1-3 games | week 4 | 0-2 games |
| De'Von Achane (MIA) | rest of season | week 4 | all 13 |

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

## 2026 after week 4: top 15 at each position

**QB**

| Player | Tm | Pts wk 1–4 | Median total (10th–90th) | Median finish | #1 | Top 6 | Top 12 | Top 24 |
|---|---|--:|--:|--:|--:|--:|--:|--:|
| Josh Allen | BUF | 112.5 | 380 (248–445) | 1 | 53% | 79% | 84% | 99% |
| Jared Goff | DET | 86.1 | 317 (162–382) | 6 | 11% | 54% | 76% | 91% |
| Brock Purdy | SF | 100.5 | 311 (149–373) | 6 | 6% | 51% | 75% | 88% |
| Bryce Young | CAR | 90.6 | 302 (144–376) | 7 | 7% | 45% | 75% | 87% |
| Tyler Shough | NO | 85.3 | 293 (138–358) | 8 | 2% | 38% | 68% | 86% |
| Lamar Jackson | BAL | 79.1 | 290 (132–364) | 9 | 4% | 36% | 68% | 85% |
| Patrick Mahomes | KC | 83.6 | 290 (133–357) | 9 | 3% | 36% | 67% | 85% |
| Dak Prescott | DAL | 81.2 | 290 (139–359) | 9 | 2% | 35% | 66% | 86% |
| Jalen Hurts | PHI | 67.0 | 270 (119–339) | 12 | 1% | 24% | 53% | 82% |
| Joe Burrow | CIN | 76.6 | 250 (151–325) | 14 | 2% | 18% | 43% | 83% |
| Trevor Lawrence | JAX | 65.1 | 251 (102–328) | 14 | 1% | 14% | 42% | 81% |
| Cam Ward | TEN | 56.7 | 246 (101–328) | 15 | 1% | 14% | 39% | 81% |
| Kirk Cousins | LV | 78.8 | 240 (144–338) | 16 | 1% | 17% | 40% | 79% |
| Bo Nix | DEN | 57.3 | 239 (99–319) | 16 | 1% | 10% | 34% | 79% |
| Matthew Stafford | LA | 61.7 | 235 (93–320) | 16 | 1% | 12% | 33% | 76% |

**RB**

| Player | Tm | Pts wk 1–4 | Median total (10th–90th) | Median finish | #1 | Top 12 | Top 24 | Top 36 |
|---|---|--:|--:|--:|--:|--:|--:|--:|
| Jahmyr Gibbs | DET | 116.0 | 389 (313–469) | 2 | 47% | 99% | 100% | 100% |
| Bijan Robinson | ATL | 105.4 | 363 (287–443) | 3 | 26% | 97% | 100% | 100% |
| Kenneth Walker III | KC | 110.1 | 337 (261–417) | 4 | 12% | 95% | 99% | 100% |
| Derrick Henry | BAL | 90.8 | 310 (237–386) | 5 | 5% | 89% | 98% | 100% |
| Jonathan Taylor | IND | 86.2 | 310 (232–386) | 5 | 5% | 89% | 98% | 100% |
| Kyren Williams | LA | 89.7 | 301 (227–376) | 6 | 3% | 85% | 98% | 100% |
| Christian McCaffrey | SF | 74.0 | 280 (209–366) | 7 | 1% | 79% | 96% | 100% |
| Javonte Williams | DAL | 81.8 | 263 (188–318) | 9 | <1% | 74% | 93% | 99% |
| Chuba Hubbard | CAR | 79.0 | 254 (172–316) | 11 | <1% | 63% | 89% | 97% |
| Ashton Jeanty | LV | 73.9 | 252 (144–306) | 11 | <1% | 65% | 89% | 98% |
| James Cook | BUF | 66.5 | 246 (172–301) | 11 | <1% | 61% | 91% | 98% |
| D'Andre Swift | CHI | 63.5 | 227 (130–290) | 14 | <1% | 40% | 82% | 94% |
| Chase Brown | CIN | 58.0 | 223 (115–289) | 14 | <1% | 39% | 81% | 92% |
| Kyle Monangai | CHI | 59.3 | 187 (100–249) | 21 | <1% | 17% | 60% | 85% |
| Jaylen Warren | PIT | 56.2 | 182 (97–239) | 22 | <1% | 15% | 57% | 84% |

**WR**

| Player | Tm | Pts wk 1–4 | Median total (10th–90th) | Median finish | #1 | Top 12 | Top 24 | Top 36 |
|---|---|--:|--:|--:|--:|--:|--:|--:|
| Jaxon Smith-Njigba | SEA | 116.7 | 369 (256–444) | 2 | 38% | 92% | 100% | 100% |
| CeeDee Lamb | DAL | 112.2 | 341 (217–416) | 3 | 21% | 88% | 95% | 100% |
| Amon-Ra St. Brown | DET | 91.3 | 308 (196–383) | 4 | 9% | 82% | 90% | 96% |
| Chris Olave | NO | 90.1 | 292 (194–361) | 5 | 7% | 79% | 91% | 96% |
| Nico Collins | HOU | 52.0 | 268 (149–337) | 7 | 4% | 65% | 81% | 88% |
| Zay Flowers | BAL | 67.2 | 255 (159–331) | 8 | 4% | 64% | 82% | 90% |
| Davante Adams | LA | 73.0 | 252 (154–328) | 9 | 3% | 64% | 81% | 90% |
| Puka Nacua | LA | 40.1 | 250 (132–320) | 10 | 3% | 59% | 78% | 88% |
| Tee Higgins | CIN | 71.1 | 245 (131–322) | 10 | 3% | 58% | 75% | 86% |
| Ja'Marr Chase | CIN | 60.2 | 242 (151–330) | 11 | 3% | 55% | 75% | 87% |
| Tetairoa McMillan | CAR | 74.5 | 243 (129–330) | 11 | 3% | 54% | 71% | 83% |
| Christian Watson | GB | 77.1 | 247 (139–290) | 11 | 1% | 59% | 79% | 88% |
| Drake London | ATL | 57.4 | 222 (59–268) | 18 | <1% | 26% | 66% | 81% |
| Garrett Wilson | NYJ | 63.0 | 212 (63–255) | 19 | <1% | 24% | 62% | 79% |
| DeVonta Smith | PHI | 48.5 | 212 (48–247) | 21 | <1% | 14% | 61% | 78% |

**TE**

| Player | Tm | Pts wk 1–4 | Median total (10th–90th) | Median finish | #1 | Top 6 | Top 12 | Top 24 |
|---|---|--:|--:|--:|--:|--:|--:|--:|
| Trey McBride | ARI | 69.2 | 244 (196–313) | 2 | 35% | 85% | 99% | 100% |
| Brock Bowers | LV | 48.2 | 212 (166–283) | 5 | 14% | 61% | 88% | 100% |
| George Kittle | SF | 64.4 | 210 (160–281) | 5 | 13% | 59% | 86% | 100% |
| Juwan Johnson | NO | 60.2 | 179 (133–251) | 10 | 5% | 35% | 63% | 93% |
| Sam LaPorta | DET | 56.8 | 174 (128–247) | 11 | 5% | 33% | 56% | 91% |
| Travis Kelce | KC | 52.6 | 170 (125–245) | 12 | 4% | 31% | 54% | 91% |
| Harold Fannin Jr. | CLE | 50.3 | 163 (115–238) | 13 | 3% | 26% | 48% | 87% |
| Tyler Warren | IND | 48.5 | 159 (113–231) | 14 | 3% | 23% | 45% | 85% |
| Isaiah Likely | NYG | 53.0 | 158 (104–230) | 16 | 1% | 17% | 41% | 76% |
| T.J. Hockenson | MIN | 47.5 | 139 (106–234) | 17 | 2% | 19% | 40% | 70% |
| Mike Gesicki | CIN | 44.5 | 152 (98–224) | 17 | 1% | 14% | 35% | 69% |
| Tyler Higbee | LA | 33.1 | 144 (83–200) | 18 | 1% | 9% | 28% | 72% |
| Michael Mayer | LV | 42.9 | 142 (89–188) | 18 | 1% | 5% | 24% | 76% |
| Dalton Kincaid | BUF | 46.0 | 142 (108–218) | 19 | 2% | 15% | 35% | 74% |
| Dalton Schultz | HOU | 42.4 | 140 (104–219) | 19 | 2% | 14% | 34% | 70% |
