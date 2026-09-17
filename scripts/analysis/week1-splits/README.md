# Week 1 splits: shotgun, tackles for loss, and backs moving the chains

`week1_splits.py` pulls nflverse play-by-play plus the weekly roster (for
positions) and prints the four tables below. Defaults to 2026 week 1:

    python3 week1_splits.py            # or: python3 week1_splits.py 2026 1

Definitions, because each one has a judgement call in it:

- **Scrimmage snap** - any play flagged `pass` or `rush`, two-point tries
  excluded. Penalty-wiped plays stay in: the offence still lined up, and
  `shotgun` is recorded for them.
- **Tackle for loss** - nflverse only charges `tackled_for_loss` on runs
  (sacks live in their own column), so the denominator is opponent carries,
  kneels removed, not total plays.
- **First down on a carry** - `first_down_rush`, which is 1 when the run moved
  the chains or scored. First downs handed over by penalty on a run play are
  not counted.

Week 1 is 16 games, so every rate below rests on 50-90 snaps or 5-39 carries.
Read it as description, not as a skill estimate.


## Shotgun rate, 2026 week 1 (offence)

| Team | Snaps | Shotgun | Rate |
|---|---|---|---|
| TEN | 50 | 43 | 86.0% |
| MIA | 55 | 43 | 78.2% |
| DEN | 50 | 39 | 78.0% |
| DAL | 58 | 45 | 77.6% |
| LAC | 55 | 42 | 76.4% |
| NO | 88 | 64 | 72.7% |
| WAS | 69 | 50 | 72.5% |
| HOU | 79 | 56 | 70.9% |
| CIN | 63 | 44 | 69.8% |
| CLE | 51 | 35 | 68.6% |
| CAR | 68 | 45 | 66.2% |
| PHI | 53 | 35 | 66.0% |
| IND | 54 | 35 | 64.8% |
| ATL | 60 | 38 | 63.3% |
| GB | 68 | 41 | 60.3% |
| KC | 66 | 39 | 59.1% |
| PIT | 65 | 38 | 58.5% |
| ARI | 72 | 40 | 55.6% |
| NE | 71 | 39 | 54.9% |
| SEA | 49 | 25 | 51.0% |
| BUF | 55 | 28 | 50.9% |
| TB | 56 | 28 | 50.0% |
| LA | 60 | 30 | 50.0% |
| NYG | 66 | 33 | 50.0% |
| CHI | 75 | 37 | 49.3% |
| MIN | 61 | 30 | 49.2% |
| NYJ | 64 | 30 | 46.9% |
| BAL | 64 | 29 | 45.3% |
| SF | 65 | 28 | 43.1% |
| JAX | 54 | 22 | 40.7% |
| LV | 65 | 24 | 36.9% |
| DET | 77 | 26 | 33.8% |

## Tackle-for-loss rate, 2026 week 1 (defence)

| Team | Carries faced | TFL | Rate |
|---|---|---|---|
| BAL | 20 | 4 | 20.0% |
| MIN | 21 | 4 | 19.0% |
| MIA | 34 | 6 | 17.6% |
| WAS | 23 | 4 | 17.4% |
| LV | 18 | 3 | 16.7% |
| SEA | 31 | 5 | 16.1% |
| ARI | 21 | 3 | 14.3% |
| TB | 26 | 3 | 11.5% |
| ATL | 18 | 2 | 11.1% |
| CLE | 29 | 3 | 10.3% |
| HOU | 20 | 2 | 10.0% |
| PIT | 31 | 3 | 9.7% |
| BUF | 32 | 3 | 9.4% |
| NO | 33 | 3 | 9.1% |
| JAX | 22 | 2 | 9.1% |
| SF | 28 | 2 | 7.1% |
| GB | 31 | 2 | 6.5% |
| CIN | 19 | 1 | 5.3% |
| CAR | 39 | 2 | 5.1% |
| NE | 21 | 1 | 4.8% |
| DET | 25 | 1 | 4.0% |
| LAC | 31 | 1 | 3.2% |
| DAL | 34 | 1 | 2.9% |
| DEN | 35 | 1 | 2.9% |
| TEN | 36 | 1 | 2.8% |
| KC | 14 | 0 | 0.0% |
| CHI | 22 | 0 | 0.0% |
| IND | 34 | 0 | 0.0% |
| NYG | 18 | 0 | 0.0% |
| LA | 30 | 0 | 0.0% |
| NYJ | 14 | 0 | 0.0% |
| PHI | 32 | 0 | 0.0% |

## Tackle-for-loss rate allowed, 2026 week 1 (offence)

| Team | Carries | TFL allowed | Rate |
|---|---|---|---|
| BAL | 34 | 0 | 0.0% |
| CAR | 22 | 0 | 0.0% |
| DEN | 14 | 0 | 0.0% |
| DAL | 18 | 0 | 0.0% |
| SF | 30 | 0 | 0.0% |
| TEN | 14 | 0 | 0.0% |
| WAS | 32 | 0 | 0.0% |
| NYJ | 36 | 1 | 2.8% |
| KC | 35 | 1 | 2.9% |
| NYG | 34 | 1 | 2.9% |
| ARI | 31 | 1 | 3.2% |
| NO | 25 | 1 | 4.0% |
| SEA | 21 | 1 | 4.8% |
| CHI | 39 | 2 | 5.1% |
| TB | 19 | 1 | 5.3% |
| MIN | 31 | 2 | 6.5% |
| LA | 28 | 2 | 7.1% |
| CLE | 22 | 2 | 9.1% |
| DET | 33 | 3 | 9.1% |
| HOU | 32 | 3 | 9.4% |
| ATL | 31 | 3 | 9.7% |
| BUF | 20 | 2 | 10.0% |
| JAX | 29 | 3 | 10.3% |
| PIT | 18 | 2 | 11.1% |
| CIN | 26 | 3 | 11.5% |
| LAC | 21 | 3 | 14.3% |
| NE | 31 | 5 | 16.1% |
| MIA | 18 | 3 | 16.7% |
| PHI | 23 | 4 | 17.4% |
| LV | 34 | 6 | 17.6% |
| GB | 21 | 4 | 19.0% |
| IND | 20 | 4 | 20.0% |

## First-down rate per carry, 2026 week 1 (RB/FB, >= 5 carries)

| Player | Team | Carries | First downs | Rate | Yards |
|---|---|---|---|---|---|
| J.Gibbs | DET | 29 | 14 | 48.3% | 156 |
| W.Marks | HOU | 9 | 4 | 44.4% | 42 |
| J.Croskey-Merritt | WAS | 16 | 7 | 43.8% | 63 |
| O.Hampton | LAC | 12 | 5 | 41.7% | 43 |
| J.Price | SEA | 10 | 4 | 40.0% | 52 |
| B.Irving | TB | 8 | 3 | 37.5% | 45 |
| J.Taylor | IND | 19 | 7 | 36.8% | 98 |
| K.Walker | KC | 23 | 8 | 34.8% | 173 |
| Bi.Robinson | ATL | 21 | 7 | 33.3% | 83 |
| C.Skattebo | NYG | 18 | 6 | 33.3% | 81 |
| J.Hill | BAL | 6 | 2 | 33.3% | 18 |
| B.Hall | NYJ | 22 | 7 | 31.8% | 102 |
| A.Jeanty | LV | 23 | 7 | 30.4% | 102 |
| J.Warren | PIT | 10 | 3 | 30.0% | 46 |
| B.Allen | NYJ | 10 | 3 | 30.0% | 40 |
| D.Henry | BAL | 24 | 7 | 29.2% | 144 |
| D.Swift | CHI | 18 | 5 | 27.8% | 124 |
| K.Williams | LA | 11 | 3 | 27.3% | 41 |
| B.Tuten | JAX | 15 | 4 | 26.7% | 66 |
| C.Brown | CIN | 16 | 4 | 25.0% | 56 |
| A.Jones | MIN | 12 | 3 | 25.0% | 40 |
| J.Cook | BUF | 13 | 3 | 23.1% | 57 |
| T.Etienne | NO | 9 | 2 | 22.2% | 46 |
| Br.Robinson | ATL | 9 | 2 | 22.2% | 31 |
| K.Miller | NO | 9 | 2 | 22.2% | 30 |
| K.Black | SF | 14 | 3 | 21.4% | 65 |
| D.Montgomery | HOU | 20 | 4 | 20.0% | 60 |
| C.McCaffrey | SF | 10 | 2 | 20.0% | 68 |
| C.Hubbard | CAR | 10 | 2 | 20.0% | 49 |
| B.Corum | LA | 10 | 2 | 20.0% | 54 |
| K.Monangai | CHI | 10 | 2 | 20.0% | 100 |
| S.Perine | CIN | 5 | 1 | 20.0% | 20 |
| A.Dillon | CAR | 5 | 1 | 20.0% | 28 |
| K.Gainwell | TB | 5 | 1 | 20.0% | 15 |
| R.Rivers | LA | 5 | 1 | 20.0% | 19 |
| D.Achane | MIA | 11 | 2 | 18.2% | 36 |
| J.Love | ARI | 11 | 2 | 18.2% | 41 |
| J.Williams | DAL | 12 | 2 | 16.7% | 41 |
| C.Rodriguez | JAX | 6 | 1 | 16.7% | 23 |
| M.Lloyd | GB | 13 | 2 | 15.4% | 37 |
| T.Pollard | TEN | 7 | 1 | 14.3% | 35 |
| R.White | WAS | 7 | 1 | 14.3% | 22 |
| C.Brooks | GB | 7 | 1 | 14.3% | 29 |
| M.Washington | LV | 7 | 1 | 14.3% | 41 |
| S.Barkley | PHI | 15 | 2 | 13.3% | 83 |
| J.Mason | MIN | 15 | 2 | 13.3% | 59 |
| J.Dobbins | DEN | 8 | 1 | 12.5% | 36 |
| E.Johnson | KC | 8 | 1 | 12.5% | 24 |
| T.Allgeier | ARI | 17 | 2 | 11.8% | 61 |
| R.Stevenson | NE | 18 | 2 | 11.1% | 51 |
| Q.Judkins | CLE | 12 | 1 | 8.3% | 33 |
| R.Dowdle | PIT | 8 | 0 | 0.0% | 15 |
| G.Holani | SEA | 8 | 0 | 0.0% | 29 |
| D.Singletary | NYG | 6 | 0 | 0.0% | 16 |
| C.Kiner | NE | 6 | 0 | 0.0% | 11 |
