# Derrick Henry — The Outlier Study

**Complete findings.** Source material for an article and a post thread.
Everything below comes from nflverse: play-by-play, Next Gen Stats tracking,
weekly player stats, snap counts and participation data, 2016–2026 regular
season. Scripts that produced every number live beside this file.

Base sample: **2,686 designed carries, 13,162 yards, 125 rushing TD, 153 games.**
Verified against official records — 2020 reads 378/2,027/17 and 2024 reads
325/1,921/16, both exact.

---

## 0. The short version

His outlier quality is not efficiency. It is the **distance between the
situation he is handed and the result he returns**. Five findings say the same
thing from five directions.

| # | Finding | The number | Strength |
|---|---|---|---|
| 1 | Runs into the most crowded boxes in football and beats them | 36.4% of carries vs 8+ defenders (97th pct); expected 3.99 YPC (30th pct); +0.90 RYOE (94th pct) | Very strong |
| 2 | Gets better as the game goes on | −0.16 YPC vs peers on carries 1–5, +1.54 by carries 11–15 | Strong |
| 3 | Aged up when the position ages down | Median peer loses −0.52 YPC after 29; he gained +0.33. Owns 3 of the 17 age-29+ 200-carry seasons in 11 years | Strong, small sample |
| 4 | Used least on the down he is best on | On field for 22.7% of third downs (peers ~49%), converts 67.5% of third-down carries (peers 52.9%) | Strong |
| 5 | Being favoured lifts him ~3.5× more than other backs | +0.84 YPC favoured vs underdog; league gap +0.24. Survives a game-script control | Real but noisy |

**Best single sentence for a lead:** he faces eight-man boxes on 36.4% of his
carries against a peer average of 23.6%, the blocking in front of him predicts
3.99 yards a carry — 30th percentile — and he returns 4.90.

**The honest counterweight, which belongs in the piece:** his median carry is
**3.0 yards, the 69th percentile**. He is not a consistently efficient back. He
is a tail-risk machine (93rd percentile on 40+ yard runs) who never leaves the
field and never gets hurt.

---

## 1. How we measured it

| Source | Covers | Used for |
|---|---|---|
| `nfldata/games.csv` | 1999+ | Spreads, moneylines, totals, roof, rest |
| Play-by-play | 1999+ | Per-carry EPA, success, score state, live win probability |
| Next Gen Stats rushing | 2016+ | Expected rush yards, RYOE, 8+ box rate, time to line |
| `stats_player_week` | 2016+ | Targets, air yards, YAC, target share, fantasy points |
| `snap_counts` | 2016+ | Share of offensive snaps played |
| `pbp_participation` | 2016–2025 | Who was on the field, play by play |
| `players` | all | Position filter and birth dates |

### Definitions that matter

- **Designed runs only.** No scrambles, kneels, or two-point plays.
- **Peer group: 101 backs** with 400+ designed carries, 2016–2026, RB/FB only.
  The position filter is load-bearing — without it Lamar Jackson and Josh Allen
  top every efficiency board, which answers a different question.
- **Favoured is from his team's side.** nflverse quotes the spread from the home
  team's perspective, so it flips on away games.
- **Moneylines are de-vigged.** The home/away pair implies more than 100%; the
  two are normalised to sum to 1 before any win probability is read off them.
- **Age is computed per game**, not per season. Born 1994-01-04; 32.7 today.
- **`fantasy_points` in nflverse is STANDARD scoring**, not half-PPR. Half-PPR
  is built as `fantasy_points + 0.5 × receptions` rather than assumed. The
  format decides whether he ranks 1st or 2nd — it matters.
- **Presence ≠ usage.** Presence is participation data (was he one of the
  eleven). Usage is what happened once he was there. A back looks like a
  two-down player either by sitting on third down or by staying in to block,
  and only the first shows up in presence.

### Coverage gaps to respect

- **RYOE and expected yards start in 2018**, not 2016. Box counts go to 2016.
- **Participation stops after 2025**, so the down section excludes 2026.
- **2026 is one game.** Ignore every number attached to it.

---

## 2. Favoured vs underdog

When favoured he gains **23.1 more yards per game**, and only about 8 of those
come from extra carries. The rest is efficiency.

| Split | Games | Att/g | Yds/g | YPC | EPA/carry | Success | TD rate | 10+ yd | 15+ yd | Stuffed |
|---|---|---|---|---|---|---|---|---|---|---|
| **Favoured** | 91 | 18.4 | **95.8** | **5.22** | +0.035 | 42.9% | 4.8% | 13.0% | 6.5% | 16.3% |
| **Underdog** | 61 | 16.6 | 72.7 | 4.38 | −0.005 | 40.7% | 4.4% | 9.9% | 4.1% | 16.4% |

His **stuffed rate is identical** either way (16.3% vs 16.4%). He is not being
stopped less often when favoured — he is breaking more long ones.

### By the size of the line

| Line | Games | Att/g | Yds/g | YPC | EPA | Success | TD rate | 10+ yd |
|---|---|---|---|---|---|---|---|---|
| Dog 7+ | 6 | 16.0 | 64.2 | 4.01 | −0.078 | 33.3% | 5.2% | 9.4% |
| Dog 3.5–6.5 | 38 | 17.1 | 77.1 | 4.52 | +0.017 | 41.5% | 4.6% | 10.5% |
| Dog 1–3 | 17 | 15.8 | 65.9 | 4.18 | −0.032 | 41.4% | 3.7% | 8.6% |
| Fav 1–3 | 43 | 18.4 | 87.7 | 4.77 | −0.004 | 41.3% | 4.3% | 12.8% |
| Fav 3.5–6.5 | 32 | 18.5 | 104.8 | 5.68 | +0.041 | 42.5% | 4.7% | 13.5% |
| **Fav 7+** | 16 | 18.0 | 99.6 | **5.53** | **+0.133** | **47.9%** | **6.2%** | 12.5% |

### By pre-game moneyline win probability (de-vigged)

| Implied win % | Games | Att/g | Yds/g | YPC | EPA | Success | TD rate |
|---|---|---|---|---|---|---|---|
| Under 35% | 25 | 16.7 | 78.6 | 4.70 | +0.002 | 39.2% | 5.5% |
| 35–50% | 37 | 16.2 | 67.0 | 4.15 | −0.013 | 41.6% | 3.7% |
| 50–65% | 52 | 18.2 | 88.1 | 4.84 | +0.001 | 41.1% | 4.7% |
| **65–80%** | 34 | **18.7** | **110.6** | **5.90** | **+0.089** | 46.3% | 4.9% |
| Over 80% | 5 | 17.4 | 75.2 | 4.32 | +0.019 | 36.8% | 5.7% |

Over-80% is five games. Ignore it.

### The caveat that belongs with this

Game to game the line is a **weak** predictor. Correlation across his 153 games:
yards 0.19, attempts 0.10, EPA 0.10, touchdowns 0.06. This is an aggregate
effect, not a weekly betting tool.

### Playoffs, counted separately

198 carries in 9 games.

| Split | Games | Att/g | Yds/g | YPC | EPA | Success | TD rate |
|---|---|---|---|---|---|---|---|
| Favoured | 3 | 20.7 | 110.7 | 5.35 | +0.054 | 46.8% | 6.5% |
| Underdog | 6 | 22.7 | 111.7 | 4.93 | +0.041 | 40.4% | 2.2% |

The favoured effect **disappears** in the playoffs — he is given the ball *more*
as an underdog and produces the same yardage.

---

## 3. Is it just "his team was winning"?

No. This is the check that should have killed the finding and did not.

Reweighting his underdog carries to match the score-state mix of his favoured
carries (direct standardisation):

| Metric | Favoured | Underdog (raw) | Underdog (adjusted) | Raw gap | Gap after control | % surviving |
|---|---|---|---|---|---|---|
| Yards per carry | 5.2204 | 4.3824 | 4.3649 | 0.8379 | 0.8554 | **102%** |
| EPA per carry | +0.0353 | −0.0052 | −0.0108 | 0.0404 | 0.0460 | **114%** |
| Success rate | 42.87% | 40.71% | 40.51% | 2.16pp | 2.36pp | 109% |
| TD per carry | 4.79% | 4.45% | 4.08% | 0.34pp | 0.71pp | 206% |
| 10+ yard rate | 12.99% | 9.88% | 9.84% | 3.11pp | 3.15pp | 101% |

The whole gap survives. The same control on all other RBs (65,011 favoured
carries, 60,719 underdog):

| Metric | Favoured | Underdog (raw) | Underdog (adj.) | Raw gap | Gap after control |
|---|---|---|---|---|---|
| Yards per carry | 4.3846 | 4.1434 | 4.1166 | 0.2412 | 0.2679 |
| EPA per carry | −0.0456 | −0.0891 | −0.0983 | 0.0435 | 0.0528 |
| 10+ yard rate | 11.24% | 10.09% | 9.95% | 1.14pp | 1.29pp |

**League gap +0.24 YPC. Henry's +0.84. About 3.5×.**

### Where his carries come from (% by score state)

| Split | Down 9+ | Down 1–8 | Tied | Up 1–8 | Up 9+ | Carries |
|---|---|---|---|---|---|---|
| Favoured | 9.2% | 19.3% | 21.9% | 29.6% | 20.0% | 1,670 |
| Underdog | 17.1% | 26.9% | 22.9% | 18.8% | 14.3% | 1,012 |

### Two-way: YPC by favoured × score state (carries in brackets)

| Split | Down 9+ | Down 1–8 | Tied | Up 1–8 | Up 9+ |
|---|---|---|---|---|---|
| Favoured | 4.63 (153) | 5.12 (323) | 4.27 (365) | 5.03 (495) | **6.89 (334)** |
| Underdog | 5.22 (173) | 4.03 (272) | 4.09 (232) | 4.73 (190) | 4.06 (145) |

### Two-way: EPA by favoured × score state

| Split | Down 9+ | Down 1–8 | Tied | Up 1–8 | Up 9+ |
|---|---|---|---|---|---|
| Favoured | −0.025 | +0.063 | −0.056 | +0.002 | **+0.185** |
| Underdog | +0.084 | −0.007 | −0.060 | +0.041 | −0.080 |

### Henry vs the field inside each score state

| Score state | Henry YPC | League RB | Edge | Henry carries |
|---|---|---|---|---|
| Down 9+ | 4.91 | 4.29 | +0.63 | 327 |
| Down 1–8 | 4.63 | 4.21 | +0.42 | 597 |
| Tied | 4.20 | 4.27 | **−0.07** | 598 |
| Up 1–8 | 4.95 | 4.33 | +0.61 | 685 |
| **Up 9+** | **6.04** | 4.24 | **+1.79** | 479 |

### By live win probability

| Win prob | Henry YPC | League RB | Edge | Henry carries |
|---|---|---|---|---|
| <20% | 5.32 | 4.31 | +1.01 | 300 |
| 20–40% | 3.96 | 4.25 | −0.29 | 365 |
| 40–60% | 4.72 | 4.25 | +0.47 | 556 |
| 60–80% | 4.74 | 4.36 | +0.38 | 568 |
| >80% | 5.35 | 4.20 | +1.15 | 897 |

Note the U-shape, and note he is **below average when tied** — the one state
with no script at all.

---

## 4. The mechanism — why he is an outlier

This is the core of the piece. Peer group: 70–71 backs on NGS volume.

| Metric | Henry | Rank | Percentile | Leader |
|---|---|---|---|---|
| **Expected YPC** (what blocking/box predicts) | **3.99** | 49/70 | **30th** | Achane 4.70 |
| **Rush yards over expected, per carry** | **+0.90** | 5/70 | **94th** | Crowell +1.10 |
| **% carries vs 8+ in the box** | **36.4%** | 3/71 | **97th** | D. Murray 42.6 |
| NGS efficiency (distance travelled) | 4.10 | 29/71 | 60th | G. Edwards 3.50 |
| Avg time to line of scrimmage | 2.77s | 36/71 | 50th | Gore 2.49 |

Peer average box rate is **23.6%**. He is handed below-average rushing
situations against the third-most-stacked boxes of the tracking era and
produces top-ten output.

### The bridge — the best finding in the study

When a peer's team is favoured, defences stack up harder. **Henry's box rate
does not move, because it is already pinned.**

| | Att | % vs 8+ box | Expected YPC | Actual YPC | RYOE/att |
|---|---|---|---|---|---|
| **Henry, favoured** | 1,619 | 36.3 | 4.08 | 5.26 | **+1.16** |
| **Henry, underdog** | 910 | 36.6 | 3.85 | 4.41 | +0.47 |
| Peer RBs, favoured | 40,399 | 24.5 | 4.16 | 4.45 | +0.30 |
| Peer RBs, underdog | 37,101 | 22.8 | 4.05 | 4.25 | +0.15 |

Favoured minus underdog, side by side:

| | Henry | Peer RBs |
|---|---|---|
| % vs 8+ box | **−0.30** | +1.70 |
| Expected YPC | +0.23 | +0.11 |
| Actual YPC | **+0.85** | +0.20 |
| RYOE/att | **+0.69** | +0.15 |

Defences have nothing left to add against him — and that is exactly where his
RYOE more than doubles.

---

## 5. The shape of the carry distribution

He is not consistent. He is explosive. Both halves are true and the piece
needs both.

| Metric | Henry | Rank | Percentile | Leader |
|---|---|---|---|---|
| Yards per carry | 4.90 | 9/101 | 92nd | Achane 5.57 |
| **Median yards per carry** | **3.0** | 32/101 | **69th** | A. Jones 4.0 |
| 10+ yard rate | 11.8% | 19/101 | 82nd | Achane 15.1% |
| 15+ yard rate | 5.5% | 19/101 | 82nd | Achane 8.5% |
| **25+ yard rate** | **2.2%** | 7/101 | **94th** | Achane 3.6% |
| **40+ yard rate** | **1.0%** | 8/101 | **93rd** | Achane 2.2% |
| Stuffed rate (≤0 yds) | 16.4% | 27/101 | 74th | J. Cook 12.2% |
| Success rate | 42.0% | 14/101 | 87th | K. Williams 46.5% |
| TD per carry | 4.7% | 3/101 | 98th | Gibbs 5.7% |

### Running with a lead, when everyone knows

| Metric | Henry | Rank | Percentile | Leader |
|---|---|---|---|---|
| YPC while up 9+ | 6.04 | 4/69 | 96th | Barkley 6.38 |
| 10+ yd rate while up 9+ | 17.1% | 3/69 | 97th | Gibbs 19.9% |
| YPC in the 4th quarter | 4.84 | 10/95 | 90th | Achane 5.78 |
| YPC, 4th quarter leading | 4.91 | 12/77 | 86th | Chubb 5.80 |

---

## 6. The wear-down curve

He is **below average on his first five carries** and pulls away after.

| Carry # in game | Henry YPC | Henry carries | Peer YPC | Peer carries | Edge |
|---|---|---|---|---|---|
| 1–5 | 4.27 | 754 | 4.43 | 32,682 | **−0.16** |
| 6–10 | 5.03 | 693 | 4.33 | 24,622 | +0.70 |
| **11–15** | **5.83** | 547 | 4.30 | 15,330 | **+1.54** |
| 16–20 | 4.66 | 383 | 4.04 | 7,071 | +0.62 |
| 21+ | 4.80 | 309 | 4.08 | 3,018 | +0.72 |

| Metric | Henry | Rank | Percentile | Leader |
|---|---|---|---|---|
| YPC on carry 16+ | 4.72 | 3/36 | 94th | Chubb 5.37 |
| Carry 16+ minus carries 1–5 | **+0.45** | 3/36 | 94th | D. Johnson +0.87 |

The folklore checks out. He is one of 36 backs with enough late-game volume to
test, and he is 3rd.

---

## 7. The age curve

Born 1994-01-04. **32.7 today.**

### Season by season

| Season | Age | Team | G | Att | Yds | TD | YPC | EPA | Yds/g |
|---|---|---|---|---|---|---|---|---|---|
| 2016 | 22.7 | TEN | 14 | 110 | 490 | 5 | 4.46 | −0.003 | 35.0 |
| 2017 | 23.7 | TEN | 16 | 176 | 744 | 5 | 4.23 | −0.080 | 46.5 |
| 2018 | 24.7 | TEN | 16 | 215 | 1,059 | 12 | 4.93 | +0.049 | 66.2 |
| 2019 | 25.7 | TEN | 15 | 303 | 1,540 | 16 | 5.08 | −0.013 | 102.7 |
| 2020 | 26.7 | TEN | 16 | 378 | 2,027 | 17 | 5.36 | +0.089 | 126.7 |
| 2021 | 27.7 | TEN | 8 | 219 | 937 | 10 | 4.28 | −0.027 | 117.1 |
| 2022 | 28.7 | TEN | 16 | 349 | 1,538 | 13 | 4.41 | −0.064 | 96.1 |
| 2023 | 29.7 | TEN | 17 | 280 | 1,167 | 12 | 4.17 | −0.007 | 68.6 |
| **2024** | **30.7** | BAL | 17 | 325 | **1,921** | 16 | **5.91** | **+0.125** | 113.0 |
| 2025 | 31.7 | BAL | 17 | 307 | 1,595 | 16 | 5.20 | +0.030 | 93.8 |
| 2026 | 32.7 | BAL | 1 | 24 | 144 | 3 | 6.00 | +0.282 | 144.0 |

### The league's RB age curve vs his

| Age | Peer YPC | Peer carries | Peer backs | Henry YPC | Henry carries | Edge |
|---|---|---|---|---|---|---|
| 21–22 | 4.57 | 11,122 | 58 | 4.45 | 110 | −0.11 |
| 23–24 | 4.40 | 24,814 | 83 | 4.61 | 391 | +0.21 |
| 25 | 4.41 | 12,182 | 83 | 5.08 | 303 | +0.67 |
| 26 | 4.29 | 10,912 | 78 | 5.36 | 378 | +1.07 |
| 27 | 4.28 | 8,026 | 67 | 4.28 | 219 | 0.00 |
| 28 | 4.09 | 5,566 | 50 | 4.48 | 319 | +0.39 |
| 29 | 4.09 | 4,410 | 41 | 3.86 | 291 | **−0.23** |
| **30** | 4.05 | 1,990 | 23 | **5.98** | 324 | **+1.92** |
| **31+** | 3.87 | 3,701 | 16 | **5.35** | 351 | **+1.48** |

**His curve is not a smooth ascent.** Age 27 was dead level and age 29 was
below average. "Aged like wine" is really "had a poor age-29 season, changed
teams, then became the best old back on record."

### How much of the position even survives

Percentage of the age 21–22 cohort still taking carries:

| Age | Still playing |
|---|---|
| 21–22 | 100% |
| 23–24 | 143% |
| 25 | 143% |
| 26 | 134% |
| 27 | 116% |
| 28 | 86% |
| 29 | 71% |
| **30** | **40%** |
| **31+** | **28%** |

(Over 100% early because backs enter the pool after 22.)

### Every 200+ carry season at age 29 or older, 2016–2026

Seventeen exist in eleven years, from thirteen different backs. **Henry has
three of them, ranked 1st, 2nd and 4th.**

| Player | Age | Att | Yds | TD | YPC | EPA |
|---|---|---|---|---|---|---|
| **D. Henry** | 30.7 | 325 | **1,921** | 16 | **5.91** | **+0.125** |
| **D. Henry** | 31.7 | 307 | **1,595** | 16 | 5.20 | +0.030 |
| C. McCaffrey | 29.3 | 311 | 1,202 | 10 | 3.87 | −0.068 |
| **D. Henry** | 29.7 | 280 | 1,167 | 12 | 4.17 | −0.007 |
| L. Blount | 29.8 | 299 | 1,161 | 18 | 3.88 | −0.062 |
| A. Jones | 29.8 | 255 | 1,138 | 5 | 4.46 | −0.053 |
| L. McCoy | 29.2 | 287 | 1,138 | 6 | 3.97 | −0.140 |
| J. Conner | 29.3 | 236 | 1,094 | 8 | 4.64 | 0.000 |
| A. Peterson | 33.5 | 251 | 1,042 | 7 | 4.15 | −0.097 |
| F. Gore | 33.3 | 263 | 1,025 | 4 | 3.90 | −0.093 |
| M. Ingram | 29.7 | 202 | 1,018 | 10 | 5.04 | +0.071 |
| R. Mostert | 31.4 | 209 | 1,012 | 18 | 4.84 | +0.082 |
| F. Gore | 34.3 | 261 | 961 | 3 | 3.68 | −0.092 |
| A. Kamara | 29.1 | 228 | 950 | 6 | 4.17 | −0.080 |
| A. Peterson | 34.5 | 211 | 898 | 5 | 4.26 | −0.121 |
| J. Stewart | 29.5 | 218 | 824 | 9 | 3.78 | −0.077 |
| K. Hunt | 29.1 | 200 | 728 | 7 | 3.64 | +0.011 |

### Henry before and after 29

| Period | Games | Att | Att/g | YPC | EPA | Success | 10+ | TD/carry |
|---|---|---|---|---|---|---|---|---|
| Age 22–28 | 100 | 1,720 | 17.2 | 4.78 | +0.002 | 41.7% | 12.1% | 4.5% |
| **Age 29+** | 53 | 966 | **18.2** | **5.11** | **+0.051** | 42.5% | 11.4% | 4.9% |

Volume went **up**. Efficiency went **up**.

### The within-player test — every peer with 150+ carries either side of 29

| Player | Pre att | Pre YPC | Post att | Post YPC | Delta |
|---|---|---|---|---|---|
| D. Martin | 282 | 2.93 | 172 | 4.20 | **+1.27** |
| **D. Henry** | 1,720 | 4.78 | 966 | 5.11 | **+0.33** |
| L. Murray | 551 | 4.01 | 661 | 4.32 | +0.31 |
| J. Conner | 1,125 | 4.33 | 268 | 4.44 | +0.10 |
| C. Hyde | 659 | 4.05 | 368 | 4.09 | +0.04 |
| R. Burkhead | 195 | 4.07 | 280 | 3.87 | −0.20 |
| A. Kamara | 1,315 | 4.43 | 359 | 3.96 | −0.47 |
| A. Jones | 1,101 | 5.02 | 475 | 4.50 | −0.52 |
| K. Hunt | 1,030 | 4.31 | 363 | 3.69 | −0.62 |
| M. Ingram | 557 | 4.94 | 512 | 4.23 | −0.70 |
| C. McCaffrey | 1,347 | 4.74 | 321 | 3.96 | −0.79 |
| D. Murray | 293 | 4.39 | 184 | 3.58 | −0.81 |
| R. Mostert | 282 | 5.64 | 499 | 4.62 | −1.02 |
| B. Powell | 191 | 5.22 | 257 | 4.13 | −1.09 |
| L. McCoy | 234 | 5.41 | 559 | 3.84 | −1.57 |

**Median delta −0.52 YPC. Only 5 of 15 improved. Henry +0.33, second.** The one
man above him, Doug Martin, improved off a 2.93 base — he was bad young, not
good old. Henry is the only back who got better after 29 *from an already good
baseline*.

---

## 8. Receiving and snap share

Career receiving line, 153 games: **246 targets, 190 receptions, 1,820 yards,
5 TD.** 1.61 targets per game. **aDOT −0.66** (his targets are behind the line
of scrimmage), 10.2 YAC per catch — essentially all screens and checkdowns.

| Metric | Henry | Rank | Percentile | Extreme |
|---|---|---|---|---|
| Targets per game | 1.61 | 15/101 lowest | 86th | G. Edwards 0.53 |
| Team target share | 5.96% | 28/101 lowest | 73rd | Blount 1.92% |
| Receptions per game | 1.24 | 18/101 lowest | 83rd | G. Edwards 0.41 |
| % of his yards that are receiving | 12.1% | 8/101 lowest | 93rd | Blount 6.2% |
| **% of PPR points from passing game** | **16.3%** | 5/101 lowest | **96th** | Blount 10.9% |

### And yet

| Scoring format | Henry | Rank |
|---|---|---|
| **Standard** | 2,274 | **1st of 101** |
| **Half-PPR** | 2,369 | **1st of 101** |
| Full PPR | 2,464 | 2nd (McCaffrey 2,529) |
| PPR per game | 16.10 | 10th (McCaffrey 22.38) |
| Scrimmage yards per game | 97.92 | 6th (McCaffrey 115.64) |

**He has the most productive standard-scoring career of the era while drawing
16.3% of his value from the passing game.** The only man above him in PPR draws
54.9% of his from receiving.

### The trade, laid out — twelve most productive backs of the era

| Player | G | Car | Ru yd | Ru TD | Tgt | Rec | Re yd | Re TD | PPR | PPR/g | % PPR receiving |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C. McCaffrey | 113 | 1,668 | 7,657 | 62 | 786 | 631 | 5,410 | 36 | 2,529 | 22.4 | 54.9 |
| **D. Henry** | **153** | **2,686** | **13,162** | **125** | 246 | 190 | 1,820 | 5 | 2,464 | 16.1 | **16.3** |
| A. Kamara | 126 | 1,674 | 7,250 | 61 | 767 | 606 | 4,948 | 25 | 2,346 | 18.6 | 53.3 |
| E. Elliott | 135 | 2,139 | 9,130 | 74 | 483 | 368 | 2,718 | 14 | 2,063 | 15.3 | 35.1 |
| S. Barkley | 107 | 1,841 | 8,439 | 55 | 491 | 359 | 2,648 | 16 | 1,898 | 17.7 | 37.9 |
| A. Jones | 125 | 1,576 | 7,666 | 53 | 468 | 351 | 2,683 | 21 | 1,808 | 14.5 | 41.2 |
| A. Ekeler | 114 | 1,081 | 4,765 | 43 | 604 | 480 | 4,288 | 30 | 1,797 | 15.8 | 60.6 |
| J. Mixon | 111 | 1,816 | 7,428 | 60 | 399 | 319 | 2,448 | 14 | 1,745 | 15.7 | 37.1 |
| J. Jacobs | 105 | 1,840 | 7,803 | 74 | 341 | 269 | 2,072 | 2 | 1,689 | 16.1 | 28.9 |
| J. Taylor | 85 | 1,570 | 7,696 | 71 | 243 | 190 | 1,492 | 7 | 1,561 | 18.4 | 24.4 |
| J. Conner | 108 | 1,393 | 6,065 | 60 | 347 | 289 | 2,255 | 12 | 1,551 | 14.4 | 37.8 |
| K. Hunt | 121 | 1,393 | 5,775 | 55 | 342 | 267 | 2,209 | 18 | 1,501 | 12.4 | 39.7 |

### Snap share

**Henry: 53.7% of offensive snaps.** Top-20 backs by career PPR have a median
of 60.3% — he is 5th from the bottom of that group.

| Player | Snap % | PPR/g | % PPR receiving |
|---|---|---|---|
| C. McCaffrey | 80.2 | 22.4 | 54.9 |
| **D. Henry** | **53.7** | 16.1 | 16.3 |
| A. Kamara | 64.9 | 18.6 | 53.3 |
| E. Elliott | 66.0 | 15.3 | 35.1 |
| S. Barkley | 76.6 | 17.7 | 37.9 |
| A. Jones | 56.0 | 14.5 | 41.2 |
| A. Ekeler | 53.3 | 15.8 | 60.6 |
| J. Mixon | 63.0 | 15.7 | 37.1 |
| J. Jacobs | 64.8 | 16.1 | 28.9 |
| J. Taylor | 69.8 | 18.4 | 24.4 |
| J. Conner | 57.1 | 14.4 | 37.8 |
| K. Hunt | 50.7 | 12.4 | 39.7 |

### His snap share by season

| Season | G | Snap % |
|---|---|---|
| 2016 | 14 | 28.9 |
| 2017 | 16 | 40.1 |
| 2018 | 16 | 40.8 |
| 2019 | 15 | 64.2 |
| 2020 | 16 | 65.5 |
| 2021 | 8 | 72.0 |
| 2022 | 16 | 66.5 |
| 2023 | 17 | 53.6 |
| 2024 | 17 | 57.4 |
| 2025 | 17 | 54.5 |
| 2026 | 1 | 54.0 |

### Receiving usage by spread

| Split | Games | Car/g | Tgt/g | Rec | Re yd | PPR/g | Std/g |
|---|---|---|---|---|---|---|---|
| Favoured | 91 | 18.4 | 1.54 | 110 | 942 | 17.1 | 15.9 |
| Underdog | 61 | 16.6 | 1.74 | 80 | 878 | 14.9 | 13.6 |

Receiving work barely moves with the spread. There was never enough there to
move.

---

## 9. Usage by down

Participation data, 2016–2025 regular season. 153 of his games are charted,
covering 2,659 carries and 245 targets.

### Presence — was he one of the eleven?

| Down | On field | Team plays | Henry presence | Peer avg presence |
|---|---|---|---|---|
| **1st** | 2,708 | 4,061 | **66.7%** | 53.3% |
| **2nd** | 1,761 | 3,004 | **58.6%** | 52.2% |
| **3rd** | 385 | 1,698 | **22.7%** | 49.3% |
| **4th** | 56 | 76 | **73.7%** | 70.5% |

The shape: heaviest first-down usage in the group, near-absent on third down,
and **back on the field for fourth down more than anyone** — the short-yardage
hammer.

### Share of each back's own snaps by down

| Player | D1 % | D2 % | D3 % | D4 % | Snaps |
|---|---|---|---|---|---|
| **Derrick Henry** | **55.2** | **35.9** | **7.8** | 1.1 | 4,910 |
| Josh Allen | 45.3 | 33.5 | 19.6 | 1.7 | 7,560 |
| Lamar Jackson | 45.6 | 33.5 | 19.4 | 1.6 | 6,390 |
| Ezekiel Elliott | 46.0 | 33.3 | 18.6 | 2.1 | 5,720 |
| C. McCaffrey | 44.9 | 32.2 | 21.2 | 1.7 | 5,570 |
| Saquon Barkley | 45.5 | 33.4 | 18.9 | 2.2 | 5,056 |
| Alvin Kamara | 42.9 | 35.0 | 20.3 | 1.7 | 5,048 |
| Jalen Hurts | 44.0 | 33.3 | 20.4 | 2.3 | 4,997 |
| Joe Mixon | 52.9 | 37.2 | 8.8 | 1.1 | 4,308 |
| Aaron Jones | 46.5 | 34.6 | 17.1 | 1.8 | 4,196 |
| Austin Ekeler | 43.6 | 32.5 | 21.1 | 2.7 | 3,907 |
| James Conner | 47.4 | 33.9 | 16.7 | 2.0 | 3,885 |

Only **7.8%** of his snaps come on third down. Joe Mixon (8.8%) is the only
comparable figure; everyone else sits at 17–21%.

(QBs are shown here as usage-context reference points, not as peer backs.)

### Usage — once on the field, did he get the ball?

| Down | Snaps | Carries | Targets | Touches | Carry % | Target % | Touch % | Peer touch % |
|---|---|---|---|---|---|---|---|---|
| 1st | 2,708 | 1,590 | 126 | 1,716 | 58.7 | 4.7 | **63.4** | 50.9 |
| 2nd | 1,761 | 891 | 97 | 988 | 50.6 | 5.5 | **56.1** | 43.4 |
| 3rd | 385 | 151 | 21 | 172 | 39.2 | 5.5 | **44.7** | 25.9 |
| 4th | 56 | 27 | 1 | 28 | 48.2 | 1.8 | **50.0** | 27.6 |

He is a **far higher-usage player than peers on every single down**, including
third. He just is not out there for third down.

### Distribution of his touches

| Down | Carries | Targets | Touches | % of his touches | Peer % of touches |
|---|---|---|---|---|---|
| 1st | 1,590 | 126 | 1,716 | **59.1** | 54.0 |
| 2nd | 891 | 97 | 988 | 34.0 | 33.9 |
| 3rd | 151 | 21 | 172 | **5.9** | 10.9 |
| 4th | 27 | 1 | 28 | 1.0 | 1.2 |

### Third down by distance

| Distance | Henry snaps | Carries | Targets | Henry touch % | Peer touch % |
|---|---|---|---|---|---|
| 3rd & 1 | 153 | 97 | 1 | **64.1** | 52.7 |
| 3rd & 2–3 | 86 | 30 | 6 | 41.9 | 31.3 |
| 3rd & 4–6 | 54 | 14 | 2 | 29.6 | 17.1 |
| 3rd & 7+ | 92 | 10 | 12 | 23.9 | 20.1 |

### What gets called when he IS out there on third down

| Play type | Henry on field | Peer RB on field |
|---|---|---|
| Run | **54.8%** | 25.8% |
| Pass | 45.2% | 74.2% |

When Henry is on the field on third down, his offence runs more than half the
time. For everyone else it is a quarter. His presence *is* the tell.

### Efficiency by down — and here is the twist

| Down | Att | YPC | EPA | Success | Peer YPC | Peer EPA | Peer success |
|---|---|---|---|---|---|---|---|
| 1st | 1,590 | 5.05 | −0.008 | 38.7% | 4.45 | −0.071 | 36.3% |
| 2nd | 891 | 4.62 | −0.008 | 42.6% | 4.37 | −0.038 | 41.8% |
| **3rd** | 151 | **5.24** | **+0.359** | **66.9%** | 4.30 | +0.045 | 55.2% |
| **4th** | 27 | 3.19 | **+0.774** | **74.1%** | 2.83 | +0.322 | 65.9% |

### Conversions

- **3rd down: 151 carries, 67.5% moved the chains** (peer backs 52.9%)
  - With 2 or fewer to go: 123 carries, **74.8%** (peers 67.3%)
- **4th down: 27 carries, 74.1% moved the chains** (peers 66.7%)
  - With 2 or fewer to go: 27 carries, 74.1% (peers 67.6%)

**He is used least on the down he is best on.** Third down is his highest EPA
per carry, his highest success rate, and his highest YPC — on 5.9% of his
touches.

### Presence by down, season by season

| Season | D1 % | D2 % | D3 % | D4 % |
|---|---|---|---|---|
| 2016 | 24.8 | 25.8 | 24.9 | 9.1 |
| 2017 | 42.7 | 39.7 | 28.9 | 50.0 |
| 2018 | 52.2 | 45.8 | 10.8 | 33.3 |
| 2019 | 76.2 | 68.2 | 13.3 | 35.7 |
| 2020 | 79.2 | 74.0 | 21.2 | 26.7 |
| 2021 | 44.0 | 40.2 | 10.7 | 25.0 |
| 2022 | 78.7 | 74.0 | 18.5 | 41.2 |
| 2023 | 69.6 | 63.7 | 11.0 | 26.3 |
| 2024 | 73.6 | 54.5 | 25.0 | 66.7 |
| 2025 | 72.0 | 56.9 | 26.9 | 36.0 |

Baltimore has used him on third down **more** than Tennessee did (25.0% and
26.9% vs a 10–21% Tennessee range).

---

## 10. Touchdowns

### Conversion by field zone

| Zone | Henry att | Henry TD% | Peer TD% | Edge |
|---|---|---|---|---|
| Inside 2 | 88 | **58.0** | 51.1 | +6.9 |
| 3–5 | 60 | **33.3** | 27.2 | +6.1 |
| 6–10 | 93 | **16.1** | 10.4 | +5.7 |
| 11–20 | 196 | 6.1 | 4.0 | +2.1 |
| Outside 20 | 2,249 | 1.2 | 0.5 | +0.7 |

He converts better in **every** zone.

### Goal-line supply and conversion, favoured vs underdog

| Split | Games | RZ carries/g | RZ TD% | Inside-5 carries/g | Inside-5 TD% | TD/game | TD outside 20/g |
|---|---|---|---|---|---|---|---|
| Favoured | 91 | 3.10 | 21.3 | 1.08 | **43.9** | 0.88 | 0.220 |
| Underdog | 61 | 2.54 | 24.5 | 0.82 | **56.0** | 0.74 | 0.115 |

### Decomposition — where the extra TD/game when favoured comes from

| Component | Effect |
|---|---|
| Extra inside-5 supply (0.82 → 1.08 carries/g) | **+0.144 TD/g** |
| Long TDs from outside the 20 | **+0.105 TD/g** |
| Goal-line conversion, which gets *worse* (56.0% → 43.9%) | **−0.099 TD/g** |

Counterintuitive and worth a line in the piece: when favoured, his touchdown
bump is volume and breakaways, **not** short-yardage finishing.

### Career TD distribution by distance

| Zone | Henry TDs | Henry % | Peer % |
|---|---|---|---|
| Inside 2 | 51 | 40.8 | 44.1 |
| 3–5 | 20 | 16.0 | 20.4 |
| 6–10 | 15 | 12.0 | 12.1 |
| 11–20 | 12 | 9.6 | 10.1 |
| **Outside 20** | **27** | **21.6** | **13.2** |

**22% of his rushing TDs come from outside the 20, vs 13% for peers.**

### Long (20+ yards out) rushing TDs per carry, top 10 of 101

| Player | Per carry | TDs |
|---|---|---|
| D. Achane | 0.0162 | 9 |
| J. Gibbs | 0.0139 | 10 |
| J. Cook | 0.0137 | 12 |
| J. Taylor | 0.0102 | 16 |
| **D. Henry** | **0.0101** | **27** |
| S. Barkley | 0.0098 | 18 |
| N. Chubb | 0.0096 | 14 |
| T. Pollard | 0.0094 | 12 |
| P. Lindsay | 0.0094 | 6 |
| B. Hall | 0.0090 | 7 |

He has **27** — nearly double the next man's count, at a top-5 rate.

---

## 11. Volume and durability

The most one-sided table in the study.

| Metric | Henry | Rank | Percentile |
|---|---|---|---|
| **Total designed carries** | **2,686** | **1/101** | **100th** |
| **Share of games with 25+ carries** | **18.3%** | **1/101** | **100th** |
| **Seasons with a carry** | **11** | **1/101** | **100th** |
| Carries per game | 17.6 | 2/101 | 99th | 
| Fumbles lost per carry | 0.0041 | 49/101 | 52nd |

Only the fumble rate is ordinary. He leads the era's peer group outright in
career carries, in the share of his games that were 25-carry workloads, and in
seasons survived.

---

## 12. Caveats, confounds and what would falsify this

Put these in the piece. They make it stronger, not weaker.

### The favoured finding is the softest one

- Positive in only **5 of 8 seasons** with both samples. Median +0.39 YPC.
  2018 was **+2.08**; 2023 was **−1.74**.
- `Fav 7+` is 288 carries across 16 games. Bootstrap 95% CI on the 5.53 YPC:
  **[4.67, 6.53]**. Real, but not a two-decimal number.
- `Up 9+ and favoured` is 334 carries, 40 games, 49% Baltimore. YPC 6.89,
  95% CI **[5.84, 8.07]**.
- He was favoured in only **59% of his games, average line +1.2**.

### The Baltimore confound is real and unresolved

His team's average line by season: TEN 0.1, 2.5, 0.2, 1.4, 2.8, −0.4, −1.4,
−2.8; then BAL **+6.1, +3.4, +3.0**. Era and favouritism are tangled.

The effect does survive splitting by era:

| Era | Favoured YPC | Underdog YPC | Gap | EPA gap |
|---|---|---|---|---|
| Tennessee 2016–23 | 4.97 (1,102 att) | 4.35 (924 att) | **+0.62** | +0.032 |
| Baltimore 2024–26 | 5.71 (568 att) | 4.74 (88 att) | **+0.97** | **−0.059** |
| Peer RBs 2016–23 | 4.33 | 4.13 | +0.20 | — |
| Peer RBs 2024–26 | 4.49 | 4.14 | +0.34 | — |

Note the Baltimore underdog sample is **88 carries**. And note the Baltimore
**EPA gap is negative** despite a +0.97 YPC gap — running with a big lead
produces yards without much win-probability value.

**What I cannot separate:** his age-30 leap coincides exactly with playing
behind Lamar Jackson, who holds the backside edge defender. No available data
resolves that. Say so in the piece.

### Sample thinness

- Age-30 peer baseline rests on **23 backs**; age 31+ on **16**.
- Only **17** age-29+ 200-carry seasons exist in the whole window.
- The late-game carry curve has **36** qualifying backs.
- **2026 is one game.**

### Things that cut against the legend

- **Median carry: 3.0 yards, 69th percentile.** Ordinary.
- **He is below average when the game is tied** (4.20 vs league 4.27).
- **Age 27 and age 29 were flat-to-poor** (4.28 and 3.86 YPC).
- **Stuffed rate 16.4%, 74th percentile** — good, not elite.
- **His EPA-based favoured gap ranks only 37/84** (56th percentile), even though
  his YPC gap ranks 11th. Yards, not value.

### What would falsify each claim

| Claim | What would kill it |
|---|---|
| Beats stacked boxes | RYOE collapsing once you control for his offence's play-action rate or Lamar's presence |
| Wears defences down | The curve flattening when you control for score state and opponent |
| Aged up | Two more seasons at 4.2 YPC — the 2024–25 run being the outlier, not the career |
| Underused on third down | Evidence he was held out for pass protection reasons that show up as team-level efficiency gains |
| Favoured effect | It is already the weakest; another 2023 season would push the median gap near zero |

---

## 13. Article and thread material

### The spine I would use

1. **Open on the box.** 36.4% vs 8+ defenders against a peer 23.6%. Everyone
   knows what is coming and it does not matter.
2. **Then the expected-yards number.** His blocking predicts 3.99 a carry,
   30th percentile. He returns 4.90. That gap *is* the player.
3. **Then the wear-down curve.** Below average on carries 1–5, +1.54 by 11–15.
   The myth is measurable.
4. **Then the age curve.** Median back loses half a yard after 29. He gained
   a third of one. Owns 3 of the 17 age-29+ volume seasons.
5. **Then the third-down paradox.** Used least on the down he is best on.
6. **Close on the trade.** #1 in career standard-scoring points, 16.3% of it
   from the passing game, 53.7% of snaps. He did it on one skill, half the time.

### Pull-quote stats, ranked by punch

| Stat | Use |
|---|---|
| 36.4% vs 8+ box (peers 23.6%) | Lead |
| Expected 3.99 YPC (30th pct), actual 4.90 | Lead |
| Box rate does NOT rise when favoured (36.6 → 36.3) because it is already pinned | Best single insight |
| −0.16 YPC on carries 1–5, +1.54 on carries 11–15 | Thread post |
| Median peer −0.52 YPC after 29; Henry +0.33 | Thread post |
| 3 of the 17 age-29+ 200-carry seasons in 11 years | Thread post |
| 22.7% third-down presence, 67.5% third-down conversion | Thread post |
| When he is on the field on 3rd down, they run 54.8% (peers 25.8%) | Thread post |
| 1st in career standard points, 16.3% from receiving | Closer |
| 53.7% of snaps vs McCaffrey's 80.2% | Closer |
| 27 TDs from outside the 20; 22% of his TDs vs 13% peers | Colour |
| Median carry 3.0 yards, 69th percentile | The honest turn |

### Claims that need hedging language

- **Anything about "favoured"** → say "in aggregate" and note it holds in 5 of
  8 seasons.
- **Anything about the 2024 leap** → name Lamar Jackson in the same breath.
- **Any age-30+ comparison** → say the peer pool is 23 backs.
- **Fav 7+ and up-9+ numbers** → round them; the CIs are a yard wide.
- **"He's efficient"** → he is not, in the median. Say explosive.

### Headline options

- *The Box Always Knew* — leads on the 36.4% and the pinned box rate
- *Thirty-Two and Getting Faster* — leads on the age curve
- *He's Never Open, He Just Doesn't Need To Be* — leads on the receiving trade
- *The Down He Never Plays* — leads on the third-down paradox

---

*Generated from `scripts/analysis/derrick-henry/`. Re-run `fetch.py` then any
analysis script to reproduce every figure above.*
