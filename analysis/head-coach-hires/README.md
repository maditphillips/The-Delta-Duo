# Head-coach hires: does the coordinator you hire predict the bounce?

Tests the claim that hiring an **offensive coordinator** as head coach is worth about
**three more wins** than the previous season, and compares it against defensive
coordinators, college coaches, previous NFL head coaches, and everyone else.

**Short answer:** not as stated. Pooled over 2000–2025, OC hires gained **+1.7 wins**
in year one (95% CI +0.7 to +2.6), and every other hiring lane gained about the same,
because nearly all of it is regression to the mean. But since 2017 the OC lane
*has* run at **+3.3 wins** and held it for three seasons, which is very likely where
the number came from.

Full write-up with charts: `report.html`.

## Running it

```sh
./fetch.sh          # downloads nflverse games.csv (~2 MB)
python3 build_seasons.py   # -> team_seasons.json   (861 team-seasons, 1999-2025)
python3 hires.py           # -> hires_raw.json      (181 opening-day coach changes)
python3 analyze.py         # all tables to stdout
python3 detail.py          # per-hire detail, distribution, outliers
python3 era.py             # era splits
python3 export.py          # -> report_data.json    (figures used by report.html)
python3 trace_back.py      # audits the hand labels against games.csv itself
```

Standard library only — no pandas, no R.

## Method

- **Sample.** Every change of *opening-day* head coach, 2000–2025, regular season only.
  181 changes; two dropped (NO 2012 and 2013, the Payton suspension caretaker years),
  leaving **179**. Franchise moves (STL/LA, SD/LAC, OAK/LV) are treated as continuous.
- **Baseline.** The team's own record in the season before the hire. Years 2 and 3
  measure the *team* against that same baseline regardless of who is coaching by
  then — that scores the decision to hire, not the coach's personal record.
- **17-game seasons.** Seasons went 16 → 17 games in 2021. Headline win figures are
  win-percentage change scaled to a 17-game pace; raw counts are reported alongside.
- **Mean-reversion control.** The catch is that teams which fire a coach are bad by
  construction (5.5 wins on average), and bad teams improve on their own. Fitting the
  648 team-seasons in this window where the coach did *not* change gives

  ```
  win%_next = 0.336 + 0.334 * win%_prior
  ```

  Two-thirds of a team's distance from .500 evaporates in one season with no
  intervention. Every "residual" column is actual minus that expectation — the part
  attributable to the change itself. It is roughly zero for every lane.

## coach_labels.csv

nflverse has the coach names but not the job each held immediately before, and
Wikipedia/PFR were unreachable when this was built, so all 179 prior roles were
assigned **by hand**. This file is the one part of the analysis most likely to contain
errors — corrections are welcome and rerunning is cheap.

| column | meaning |
|---|---|
| `prior_role` | `OC`, `DC`, `NFL_HC`, `COLLEGE`, `OTHER` |
| `prior_detail` | the actual title, so a call can be checked |
| `prior_nfl_hc` | had been an NFL head coach before, whatever the immediate prior job |
| `ambiguous` | flagged as a judgment call (15 of them — assistant-HC and interim titles) |
| `exclude` | dropped from the sample, with `exclude_reason` |

`analyze.py` reports a sensitivity pass with all 15 ambiguous hires dropped; no bucket
mean moves more than 0.1 wins except "Other".

## What can be traced instead of asserted

`away_coach`/`home_coach` in `games.csv` is the **only** staff field in the entire
nflverse — the string `coordinator` does not appear anywhere in `nflreadr` or
`nfldata`, and none of nflreadr's 21 datasets carries assistant staff. So the OC/DC
distinction cannot be traced; it has to come from outside.

But every coach's NFL *head*-coaching record from 1999 on is right there in that
column, which settles two of the hand-labeled columns without judgment.
`trace_back.py` derives them and audits the hand labels against the result:

| | |
|---|---|
| `prior_nfl_hc` | **162 / 179 machine-confirmed** |
| `internal_promo` | derived outright for all 179 |
| OC / DC / college / ST | 0 / 179 — nothing to trace |

All 17 disagreements resolve, none of them silently:

- **6 are trace-blind.** Their only head-coaching job ended before 1999, so `games.csv`
  cannot see it (Belichick's Browns, Gibbs' first Washington run, Schottenheimer's
  Chiefs, Wannstedt's Bears, Shell's Raiders, Erickson's Seahawks). The hand label
  stands.
- **11 are definitional.** The prior stint was an interim/caretaker run. These labels
  answer *what job was he hired from*, and a caretaker run is not a lane you get
  hired out of, so they are deliberately not counted as retreads. Counting them the
  other way moves the first-time-vs-retread residual from −0.14/−0.49 to −0.14/−0.46
  — the finding (no difference) is unchanged either way.

### One trap worth knowing

`games.csv` stores **Jim Mora Sr.** (Colts, 1999–2001) and **Jim Mora Jr.** (Falcons
2004–06, Seahawks 2009) under the identical string `Jim Mora`. Any name-keyed trace
will call the 2004 Falcons hire a retread; it was not. Every other 5+ season gap in
the file was checked and is a genuine same-person hiatus. `trace_back.py` carries the
exception explicitly in `ALIASED`.

## Caveats

- The 2017 era boundary was chosen **after** seeing the data, so its p-values
  (p = 0.003 vs. other modern hires) are optimistic. Treat the modern OC premium as a
  strong hypothesis, not a settled result.
- No control for quarterback change, roster turnover, draft position, or schedule
  strength. A team that hires a coach and drafts a franchise QB in the same offseason
  credits both to the coach here.
