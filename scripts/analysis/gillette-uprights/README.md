# The Gillette "yellow uprights" question

Claim under test: for years the Patriots' video board showed a reverse view of
opposing field goal attempts, putting a second, offset set of yellow uprights
(and streamers pointing the wrong way) in the kicker's field of view — and
never did it on Patriots kicks.

Does nflverse play-by-play show visiting kickers actually missing more at
Gillette, and did it win New England games?

## Running it

```bash
pip install pandas pyarrow statsmodels scipy
python3 fetch_kicks.py     # ~24 season files, downloaded and filtered one at a time
python3 analyze.py > FINDINGS.txt
```

`fetch_kicks.py` writes `kicks_2002_2025.parquet` (gitignored, ~4 MB): every
field goal and extra point from 2002 (Gillette's first season) through 2025,
55,073 plays.

## Method

Every kick is scored against a baseline logistic model — a 5-knot spline in
kick distance plus season fixed effects — **fit only on kicks outside
Gillette**, so Gillette is measured against the rest of the league rather than
against itself. Blocked kicks are dropped from the primary sample (a block is a
line-of-scrimmage failure, not an aiming failure) and reported separately.

The point of the design is that "visitors kick worse here" is not enough. If the
video board is the cause, the data should carry its fingerprint:

| Section | Test | What the claim predicts |
|---|---|---|
| 7 | miss direction | lateral (wide) misses, not short ones; a consistent left/right bias from the offset |
| 6 | extra points | a 33-yard XP into the same uprights should also suffer |
| 9 | timing | effect should track the video boards, and fade once the alleged operator left |
| 2, 14 | Patriots kickers | New England should be unaffected at home |
| 8, 10 | weather | effect should survive wind/temperature and show up in calm, warm games |
| 15, 16 | 29 venues | someone had to be the worst venue; is Gillette beyond that |

## Headline numbers

- Visiting kickers at Gillette, 2002-2025: **79.3%** against an expected 85.8%
  — 23.5 makes short over 24 seasons, z = -3.75. Hardest venue in the NFL on
  visiting kickers, and still hardest over 2016-2025 alone.
- It survives wind, temperature, week-of-season, and per-yard distance controls,
  and it survives correction for having searched all 29 venues (Bonferroni
  p = 0.005; venue-level permutation p = 0.019).
- **But none of the mechanism's fingerprints are there.** See `FINDINGS.txt`.
- Win impact: 7 New England home wins over 24 seasons where a visiting make
  would have tied or flipped it, times the 31% of misses that are "excess" —
  about 2 games, roughly 0.1 wins a season.
