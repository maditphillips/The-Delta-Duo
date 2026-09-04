# Running backs after an ACL tear

What happens to an NFL running back's *volume* and *efficiency* in the first
season he plays again after tearing an ACL — and how long does getting back
actually take?

nflverse can answer the second half of that question precisely and the first
half completely. It cannot answer the *cohort* question at all: the league's
injury reports are body-part only, so a torn ACL and a bruised knee both come
back as `Knee`. Across every injury report from 2009-2025 the string "ACL"
appears zero times. So the cohort here is hand-built and individually sourced
(see `SOURCES.md`), then every date in it is checked against the game logs.

## Running it

```bash
pip install pandas pyarrow scipy
python3 fetch.py               # nflverse pulls; pbp is filtered a season at a time
python3 build.py               # -> player_gamelog.parquet, team_games.parquet
python3 analyze.py > FINDINGS.txt
```

Data lands in `.data/` (gitignored, ~35 MB — play-by-play is column-filtered on the way in). `RB_ACL_DATA=/some/path` moves it.
`analyze.py` takes about 35 seconds once the data is local.

## Cohort

`acl_cohort.csv` — 44 ACL tears by 40 running backs, 1999-2024, every one of
them sustained *while under an NFL contract* by a back who had already played
at least one NFL regular-season game. Four backs appear twice (Jamal Anderson,
Deuce McAllister, Kevin Smith, Jamaal Charles, Knowshon Moreno tore one and
then the other or the same knee again).

Deliberately out of scope, and why:

- **College tears** (Willis McGahee, Frank Gore, Todd Gurley, Marcus Lattimore,
  Bryce Love) and **rookie tears before a first snap** (Derrius Guice, 2018).
  There is no NFL baseline to compare a return against.
- **2025 tears** (Antonio Gibson). The 2026 season is one week old, so there is
  no first year back to measure yet.
- **Knee injuries that were not ACLs**, several of which are routinely
  mis-remembered as ACL tears: Le'Veon Bell (2015, MCL+PCL), Spencer Ware
  (2017, PCL), Correll Buckhalter (2004 and 2005, patellar tendon both times),
  Adrian Peterson (2016, meniscus), Trey Benson (2025, meniscus), Braelon
  Allen (2025, MCL), Cadillac Williams (2007/2008, patellar tendon),
  Justice Hill (2021, Achilles), Cam Akers (2021 and 2023, Achilles).

## Method

**Windows.** `PRE` is the 8 regular-season games the back played immediately
before the tear. For an in-game tear the injury game itself is dropped — he
left it partway through, so it is not a clean baseline. `Y1` is every
regular-season game he played in the first season he returned; `Y2` is the
season after that.

**Participation.** A back "played" a game if he recorded a rush attempt, a
target, or an offensive snap. The first two come from play-by-play (1999+), the
third from snap counts (2012+). Pure kick-return or blocking appearances before
2012 are invisible to this, which is why injury dates are cross-checked against
reporting rather than inferred from the logs alone.

**Return to play** is days from the injury date to the first regular-season
game played. Team games missed counts the actual games his team(s) played in
between, from the real schedule, so byes and 16- vs 17-game seasons are handled.

**Controls.** A raw pre-vs-post comparison overstates the damage, because
running backs decline year over year anyway. So every Y1 change is netted
against 1,307 *healthy* RB season-to-season transitions built the same way
(last 8 games of season S vs all of season S+1, for backs who missed 2 or fewer
team games in between and were carrying 5+ touches a game). Each ACL case is
matched to controls within ±2 years of age, ±30% of pre-injury touches per game,
and ±8 seasons; the band widens if fewer than 15 controls qualify. The `excess`
column in `FINDINGS.txt` is case-minus-matched-control, tested with a Wilcoxon
signed-rank.

## Limitations

- **n = 32** for the productivity analysis (44 episodes, minus 6 who never
  returned and 6 with too thin a pre-injury baseline to compare against).
  Direction is clear; individual medians are not precise.
- **Injury dates.** 15 are from contemporaneous reporting. The rest are the
  date of the last game the back played, which is the injury game for an
  in-game tear. Two offseason dates (Jamal Lewis 2001, Nyheim Hines 2023) are
  approximate to within a few weeks; both players missed a full season either
  way, so nothing downstream turns on them.
- **Surgery dates are not public**, so "time to return" here is injury-to-play,
  not surgery-to-play. Surgery typically follows a tear by 1-4 weeks, so
  surgery-to-play runs roughly 2-4 weeks shorter than the numbers reported.
- **Return timing confounds medicine with employment.** Tim Hightower (1,477
  days), Jerick McKinnon (743) and Nyheim Hines (831) were out of the league
  for stretches, not merely rehabbing. They are reported separately.
- **Snap share is 2012+ only** (n=15 of the 32), and NGS rush-yards-over-
  expected is 2016+ (n=6). Treat both as directional.
- **Pre-injury windows for 1999-2000 tears are short** — play-by-play starts in
  1999, so Terrell Davis and Jamal Anderson have 3 and 1 prior games. Both fall
  below the baseline bar and are excluded from the productivity sample.
