# Week 1 splits: shotgun, tackles for loss, and who moves the chains

`week1_splits.py` pulls nflverse play-by-play plus the weekly roster (for
positions), prints the five tables below, and writes each to `tables/` as CSV.
Defaults to 2026 week 1:

    python3 week1_splits.py            # or: python3 week1_splits.py 2026 1

Definitions, because each one has a judgement call in it:

- **Scrimmage snap** - any play flagged `pass` or `rush`, two-point tries
  excluded. Penalty-wiped plays stay in: the offence still lined up, and
  `shotgun` is recorded for them.
- **Tackle for loss** - nflverse only charges `tackled_for_loss` on runs
  (sacks live in their own column), so the denominator is opponent carries,
  kneels removed, not total plays.
- **Target** - a pass attempt with a charged receiver, so throwaways and sacks
  are out and every incompletion counts against the rate.
- **First down** - `first_down_rush` / `first_down_pass`, which are 1 when the
  play moved the chains or scored. First downs handed over by penalty on the
  play are not counted.

Week 1 is 16 games, so every rate below rests on 50-90 snaps, 5-39 carries or
5-14 targets. Read it as description, not as a skill estimate.


## Shotgun rate, 2026 week 1 (offence)

| team | snaps | shotgun | shotgun_rate |
|---|---|---|---|
| TEN | 50 | 43 | 86.0 |
| MIA | 55 | 43 | 78.2 |
| DEN | 50 | 39 | 78.0 |
| DAL | 58 | 45 | 77.6 |
| LAC | 55 | 42 | 76.4 |
| NO | 88 | 64 | 72.7 |
| WAS | 69 | 50 | 72.5 |
| HOU | 79 | 56 | 70.9 |
| CIN | 63 | 44 | 69.8 |
| CLE | 51 | 35 | 68.6 |
| CAR | 68 | 45 | 66.2 |
| PHI | 53 | 35 | 66.0 |
| IND | 54 | 35 | 64.8 |
| ATL | 60 | 38 | 63.3 |
| GB | 68 | 41 | 60.3 |
| KC | 66 | 39 | 59.1 |
| PIT | 65 | 38 | 58.5 |
| ARI | 72 | 40 | 55.6 |
| NE | 71 | 39 | 54.9 |
| SEA | 49 | 25 | 51.0 |
| BUF | 55 | 28 | 50.9 |
| TB | 56 | 28 | 50.0 |
| LA | 60 | 30 | 50.0 |
| NYG | 66 | 33 | 50.0 |
| CHI | 75 | 37 | 49.3 |
| MIN | 61 | 30 | 49.2 |
| NYJ | 64 | 30 | 46.9 |
| BAL | 64 | 29 | 45.3 |
| SF | 65 | 28 | 43.1 |
| JAX | 54 | 22 | 40.7 |
| LV | 65 | 24 | 36.9 |
| DET | 77 | 26 | 33.8 |

## Tackle-for-loss rate, 2026 week 1 (defence)

| team | carries_faced | tfl | tfl_rate |
|---|---|---|---|
| BAL | 20 | 4 | 20.0 |
| MIN | 21 | 4 | 19.0 |
| MIA | 34 | 6 | 17.6 |
| WAS | 23 | 4 | 17.4 |
| LV | 18 | 3 | 16.7 |
| SEA | 31 | 5 | 16.1 |
| ARI | 21 | 3 | 14.3 |
| TB | 26 | 3 | 11.5 |
| ATL | 18 | 2 | 11.1 |
| CLE | 29 | 3 | 10.3 |
| HOU | 20 | 2 | 10.0 |
| PIT | 31 | 3 | 9.7 |
| BUF | 32 | 3 | 9.4 |
| NO | 33 | 3 | 9.1 |
| JAX | 22 | 2 | 9.1 |
| SF | 28 | 2 | 7.1 |
| GB | 31 | 2 | 6.5 |
| CIN | 19 | 1 | 5.3 |
| CAR | 39 | 2 | 5.1 |
| NE | 21 | 1 | 4.8 |
| DET | 25 | 1 | 4.0 |
| LAC | 31 | 1 | 3.2 |
| DAL | 34 | 1 | 2.9 |
| DEN | 35 | 1 | 2.9 |
| TEN | 36 | 1 | 2.8 |
| KC | 14 | 0 | 0.0 |
| CHI | 22 | 0 | 0.0 |
| IND | 34 | 0 | 0.0 |
| NYG | 18 | 0 | 0.0 |
| LA | 30 | 0 | 0.0 |
| NYJ | 14 | 0 | 0.0 |
| PHI | 32 | 0 | 0.0 |

## Tackle-for-loss rate allowed, 2026 week 1 (offence)

| team | carries | tfl_allowed | tfl_rate_allowed |
|---|---|---|---|
| BAL | 34 | 0 | 0.0 |
| CAR | 22 | 0 | 0.0 |
| DEN | 14 | 0 | 0.0 |
| DAL | 18 | 0 | 0.0 |
| SF | 30 | 0 | 0.0 |
| TEN | 14 | 0 | 0.0 |
| WAS | 32 | 0 | 0.0 |
| NYJ | 36 | 1 | 2.8 |
| KC | 35 | 1 | 2.9 |
| NYG | 34 | 1 | 2.9 |
| ARI | 31 | 1 | 3.2 |
| NO | 25 | 1 | 4.0 |
| SEA | 21 | 1 | 4.8 |
| CHI | 39 | 2 | 5.1 |
| TB | 19 | 1 | 5.3 |
| MIN | 31 | 2 | 6.5 |
| LA | 28 | 2 | 7.1 |
| CLE | 22 | 2 | 9.1 |
| DET | 33 | 3 | 9.1 |
| HOU | 32 | 3 | 9.4 |
| ATL | 31 | 3 | 9.7 |
| BUF | 20 | 2 | 10.0 |
| JAX | 29 | 3 | 10.3 |
| PIT | 18 | 2 | 11.1 |
| CIN | 26 | 3 | 11.5 |
| LAC | 21 | 3 | 14.3 |
| NE | 31 | 5 | 16.1 |
| MIA | 18 | 3 | 16.7 |
| PHI | 23 | 4 | 17.4 |
| LV | 34 | 6 | 17.6 |
| GB | 21 | 4 | 19.0 |
| IND | 20 | 4 | 20.0 |

## First-down rate per carry, 2026 week 1 (RB/FB, >= 5 carries)

| player | team | position | carries | first_downs | first_down_rate | yards |
|---|---|---|---|---|---|---|
| J.Gibbs | DET | RB | 29 | 14 | 48.3 | 156 |
| W.Marks | HOU | RB | 9 | 4 | 44.4 | 42 |
| J.Croskey-Merritt | WAS | RB | 16 | 7 | 43.8 | 63 |
| O.Hampton | LAC | RB | 12 | 5 | 41.7 | 43 |
| J.Price | SEA | RB | 10 | 4 | 40.0 | 52 |
| B.Irving | TB | RB | 8 | 3 | 37.5 | 45 |
| J.Taylor | IND | RB | 19 | 7 | 36.8 | 98 |
| K.Walker | KC | RB | 23 | 8 | 34.8 | 173 |
| Bi.Robinson | ATL | RB | 21 | 7 | 33.3 | 83 |
| C.Skattebo | NYG | RB | 18 | 6 | 33.3 | 81 |
| J.Hill | BAL | RB | 6 | 2 | 33.3 | 18 |
| B.Hall | NYJ | RB | 22 | 7 | 31.8 | 102 |
| A.Jeanty | LV | RB | 23 | 7 | 30.4 | 102 |
| J.Warren | PIT | RB | 10 | 3 | 30.0 | 46 |
| B.Allen | NYJ | RB | 10 | 3 | 30.0 | 40 |
| D.Henry | BAL | RB | 24 | 7 | 29.2 | 144 |
| D.Swift | CHI | RB | 18 | 5 | 27.8 | 124 |
| K.Williams | LA | RB | 11 | 3 | 27.3 | 41 |
| B.Tuten | JAX | RB | 15 | 4 | 26.7 | 66 |
| C.Brown | CIN | RB | 16 | 4 | 25.0 | 56 |
| A.Jones | MIN | RB | 12 | 3 | 25.0 | 40 |
| J.Cook | BUF | RB | 13 | 3 | 23.1 | 57 |
| T.Etienne | NO | RB | 9 | 2 | 22.2 | 46 |
| Br.Robinson | ATL | RB | 9 | 2 | 22.2 | 31 |
| K.Miller | NO | RB | 9 | 2 | 22.2 | 30 |
| K.Black | SF | RB | 14 | 3 | 21.4 | 65 |
| D.Montgomery | HOU | RB | 20 | 4 | 20.0 | 60 |
| C.McCaffrey | SF | RB | 10 | 2 | 20.0 | 68 |
| C.Hubbard | CAR | RB | 10 | 2 | 20.0 | 49 |
| B.Corum | LA | RB | 10 | 2 | 20.0 | 54 |
| K.Monangai | CHI | RB | 10 | 2 | 20.0 | 100 |
| S.Perine | CIN | RB | 5 | 1 | 20.0 | 20 |
| A.Dillon | CAR | RB | 5 | 1 | 20.0 | 28 |
| K.Gainwell | TB | RB | 5 | 1 | 20.0 | 15 |
| R.Rivers | LA | RB | 5 | 1 | 20.0 | 19 |
| D.Achane | MIA | RB | 11 | 2 | 18.2 | 36 |
| J.Love | ARI | RB | 11 | 2 | 18.2 | 41 |
| J.Williams | DAL | RB | 12 | 2 | 16.7 | 41 |
| C.Rodriguez | JAX | RB | 6 | 1 | 16.7 | 23 |
| M.Lloyd | GB | RB | 13 | 2 | 15.4 | 37 |
| T.Pollard | TEN | RB | 7 | 1 | 14.3 | 35 |
| R.White | WAS | RB | 7 | 1 | 14.3 | 22 |
| C.Brooks | GB | RB | 7 | 1 | 14.3 | 29 |
| M.Washington | LV | RB | 7 | 1 | 14.3 | 41 |
| S.Barkley | PHI | RB | 15 | 2 | 13.3 | 83 |
| J.Mason | MIN | RB | 15 | 2 | 13.3 | 59 |
| J.Dobbins | DEN | RB | 8 | 1 | 12.5 | 36 |
| E.Johnson | KC | RB | 8 | 1 | 12.5 | 24 |
| T.Allgeier | ARI | RB | 17 | 2 | 11.8 | 61 |
| R.Stevenson | NE | RB | 18 | 2 | 11.1 | 51 |
| Q.Judkins | CLE | RB | 12 | 1 | 8.3 | 33 |
| R.Dowdle | PIT | RB | 8 | 0 | 0.0 | 15 |
| G.Holani | SEA | RB | 8 | 0 | 0.0 | 29 |
| D.Singletary | NYG | RB | 6 | 0 | 0.0 | 16 |
| C.Kiner | NE | RB | 6 | 0 | 0.0 | 11 |

## First-down rate per target, 2026 week 1 (RB/WR, >= 5 targets)

| player | team | position | targets | catches | first_downs | first_down_rate | yards |
|---|---|---|---|---|---|---|---|
| M.Evans | SF | WR | 7 | 6 | 6 | 85.7 | 49 |
| Z.Flowers | BAL | WR | 6 | 5 | 5 | 83.3 | 150 |
| L.McConkey | LAC | WR | 7 | 5 | 5 | 71.4 | 82 |
| J.Coker | CAR | WR | 9 | 8 | 6 | 66.7 | 138 |
| A.Pierce | IND | WR | 6 | 4 | 4 | 66.7 | 61 |
| P.Washington | JAX | WR | 6 | 5 | 4 | 66.7 | 83 |
| K.Bourne | ARI | WR | 8 | 8 | 5 | 62.5 | 75 |
| C.Lamb | DAL | WR | 8 | 5 | 5 | 62.5 | 44 |
| C.Watson | GB | WR | 8 | 6 | 5 | 62.5 | 147 |
| J.Nailor | LV | WR | 5 | 3 | 3 | 60.0 | 27 |
| K.Raymond | CHI | WR | 9 | 8 | 5 | 55.6 | 84 |
| J.Jefferson | MIN | WR | 9 | 8 | 5 | 55.6 | 92 |
| C.Olave | NO | WR | 13 | 10 | 7 | 53.8 | 182 |
| D.Moore | BUF | WR | 8 | 5 | 4 | 50.0 | 100 |
| T.McMillan | CAR | WR | 8 | 5 | 4 | 50.0 | 75 |
| T.Higgins | CIN | WR | 6 | 3 | 3 | 50.0 | 59 |
| W.Robinson | TEN | WR | 6 | 5 | 3 | 50.0 | 38 |
| E.Egbuka | TB | WR | 6 | 5 | 3 | 50.0 | 63 |
| P.Bryant | DEN | WR | 6 | 4 | 3 | 50.0 | 42 |
| J.Smith-Njigba | SEA | WR | 11 | 8 | 5 | 45.5 | 122 |
| S.Diggs | WAS | WR | 9 | 4 | 4 | 44.4 | 55 |
| D.Samuel | SF | WR | 7 | 6 | 3 | 42.9 | 48 |
| G.Wilson | NYJ | WR | 7 | 6 | 3 | 42.9 | 79 |
| Mi.Wilson | ARI | WR | 7 | 5 | 3 | 42.9 | 56 |
| C.Douglas | MIA | WR | 7 | 5 | 3 | 42.9 | 94 |
| J.Williams | DAL | RB | 5 | 5 | 2 | 40.0 | 31 |
| L.Burden | CHI | WR | 5 | 5 | 2 | 40.0 | 63 |
| K.Concepcion | CLE | WR | 5 | 4 | 2 | 40.0 | 43 |
| M.Golden | GB | WR | 12 | 6 | 4 | 33.3 | 95 |
| M.Nabers | NYG | WR | 9 | 6 | 3 | 33.3 | 69 |
| D.Vele | NO | WR | 9 | 7 | 3 | 33.3 | 69 |
| G.Pickens | DAL | WR | 6 | 3 | 2 | 33.3 | 28 |
| K.Shakir | BUF | WR | 6 | 4 | 2 | 33.3 | 40 |
| K.Walker | KC | RB | 6 | 3 | 2 | 33.3 | 18 |
| A.Jeanty | LV | RB | 6 | 6 | 2 | 33.3 | 45 |
| N.Collins | HOU | WR | 10 | 7 | 3 | 30.0 | 75 |
| A.St. Brown | DET | WR | 14 | 10 | 4 | 28.6 | 67 |
| D.Douglas | NE | WR | 7 | 5 | 2 | 28.6 | 20 |
| B.Irving | TB | RB | 7 | 7 | 2 | 28.6 | 48 |
| T.Etienne | NO | RB | 9 | 7 | 2 | 22.2 | 32 |
| J.Williams | DET | WR | 9 | 4 | 2 | 22.2 | 45 |
| P.Nacua | LA | WR | 9 | 5 | 2 | 22.2 | 74 |
| D.Metcalf | PIT | WR | 10 | 4 | 2 | 20.0 | 40 |
| Bi.Robinson | ATL | RB | 10 | 8 | 2 | 20.0 | 90 |
| M.Hollins | NE | WR | 5 | 4 | 1 | 20.0 | 51 |
| D.Achane | MIA | RB | 5 | 4 | 1 | 20.0 | 30 |
| J.Gibbs | DET | RB | 5 | 5 | 1 | 20.0 | 30 |
| K.Allen | IND | WR | 6 | 6 | 1 | 16.7 | 32 |
| D.Adams | LA | WR | 6 | 3 | 1 | 16.7 | 26 |
| R.Stevenson | NE | RB | 6 | 5 | 1 | 16.7 | 44 |
| D.Smith | PHI | WR | 6 | 3 | 1 | 16.7 | 53 |
| J.Warren | PIT | RB | 6 | 5 | 1 | 16.7 | 27 |
| X.Hutchinson | HOU | WR | 6 | 3 | 1 | 16.7 | 32 |
| R.Wilson | PIT | WR | 6 | 3 | 1 | 16.7 | 26 |
| X.Worthy | KC | WR | 6 | 3 | 1 | 16.7 | 18 |
| C.Tate | TEN | WR | 6 | 4 | 1 | 16.7 | 38 |
| J.Reed | GB | WR | 7 | 3 | 1 | 14.3 | 20 |
| M.Washington | MIA | WR | 8 | 3 | 1 | 12.5 | 53 |
| C.McCaffrey | SF | RB | 8 | 5 | 0 | 0.0 | 20 |
| Q.Johnston | LAC | WR | 6 | 2 | 0 | 0.0 | 17 |
| C.Brown | CIN | RB | 6 | 5 | 0 | 0.0 | 22 |
| T.Harris | LAC | WR | 6 | 3 | 0 | 0.0 | 20 |
| C.Sutton | DEN | WR | 5 | 2 | 0 | 0.0 | 11 |
| R.Dowdle | PIT | RB | 5 | 2 | 0 | 0.0 | 6 |
