# Do alpha WRs on bad teams get hurt more?

**Short answer:** a little, yes. About half a game a season, and it's borderline significant.

- **Using a team-quality measure set before injuries happen** (Vegas spread, weeks 1-4), the
  WR1 on a bad team missed **1.6 games per 17** to injury vs **1.1** on a good team
  (+0.5, 95% CI +0.06 to +0.96, p = 0.03). 48% vs 39% missed at least one game.
- **Bad-team WR1s get hurt more often, not for longer.** They had more separate injury absences
  (0.65 vs 0.48 a season, p = 0.04); each absence lasted about the same (2.4 vs 2.2 games).
- **Part of it is late-season shutdowns.** Weeks 13+ the gap is 0.69 vs 0.43 games. Some of that
  is likely bad teams resting a hurt star instead of playing through it.
- **Final win % overstates it** (1.75 vs 1.07 games). Losing your WR1 makes you lose, so that
  split mixes cause and effect. Don't use it as the headline.
- **Prior-season record shows nothing** (+0.27, p = 0.23): last year's record is a weak read on
  this year's team.
- **Not explained by workload.** Bad-team WR1s actually saw slightly fewer targets per game
  (7.9 vs 8.5). They're also younger (26.0 vs 27.2), so it isn't age. Adding targets and age to
  the model shrinks the effect a bit (rate ratio 0.90 per SD better team, p = 0.11).

Full output: `results.txt`.

## Running it

```sh
./fetch.sh          # nflverse injuries, weekly stats, weekly rosters, schedules 2009-2025 (~375 MB, gitignored)
python3 build.py    # -> alpha_wrs.csv (one row per team-season)
python3 analyze.py  # tables to stdout (saved as results.txt), -> summary_by_spread.csv
```

Needs pandas, numpy, scipy, statsmodels.

## Method

- **Sample.** 2009-2025 regular seasons (injury reports start in 2009): 544 team-seasons.
- **Alpha WR** = the team's WR with the most targets per game played, min 6 games. Position comes
  from that season's roster (stats files sometimes carry a stale position).
- **Team quality**, split in thirds: average Vegas spread over weeks 1-4 (main), final win %,
  and prior-season win %.
- **Injury game missed** = team played, he had no stat line, and either he was on the injury
  report / an injury reserve list (IR, IR-return, PUP, NFI) that week, or the last thing we saw
  was an injury (players on IR drop off the report). Missing the rest of the season with no
  report, 2+ games, also counts (in-game injury, IR before the next report). Suspensions,
  holdouts and pre-debut weeks don't count. Trades end his tenure with the team.
- Counts are scaled to 17 team games. Tests: Mann-Whitney on games missed, bootstrap CI on the
  difference, negative binomial with player-clustered errors for the continuous version.

## Caveats

- Small sample: ~180 seasons per group. The effect is real-looking but not large or certain.
- "Injury" is what teams report. Bad teams may list or shelve players more freely late in the
  year, which looks like injury risk but is partly a choice.
- No snap data, so exposure is targets per game, not plays on the field.
