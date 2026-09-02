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

## Part two: why is Gillette actually hard to kick at?

`fetch_punts.py` and `fetch_fourth.py` pull two more slices of nflverse — punts
and kickoffs (57,813 punts, 1,869 at Gillette) and every 4th-down play — chosen
because neither has anything to do with uprights, video boards, or aiming.

| Script | Output | What it tests |
|---|---|---|
| `why_hard.py` | `WHY_HARD.txt` | punt gross distance and kickoff touchbacks by venue; wind sensitivity; the grass→turf break; gust mentions; quarter parity |
| `ends.py` | `ENDS.txt` | the same directional test on punts, kickoffs and extra points, where the samples are far larger |
| `direction.py` | `DIRECTION.txt` | is the quarter-parity split Gillette-specific, and does it survive a clock-pressure control |
| `decisions.py` | `DECISIONS.txt` | 4th-down kick/no-kick rates — did New England decline kicks at home that other teams took |

### What holds up

1. **The air at Gillette really is heavier than average, but only modestly.**
   Gross punt distance runs 0.94 yards below expectation — 7th worst of 38
   venues, 1.2 sd below the mean, behind NYG, CHI, PIT, PHI, GB and BUF.
   Kickoff touchbacks rank 12th of 35. Real, but nowhere near enough to
   explain a 6.5 pp field-goal penalty.

2. **One direction of play is worse than the other, for everybody.** Punts at
   Gillette lose 1.29 yds in Q2+Q4 versus 0.56 yds in Q1+Q3, and the Patriots'
   own punters lose 1.05 yds in that direction (p = 0.007). Visiting kickers'
   FG penalty sits almost entirely in the same half of the rotation: −9.5% in
   Q2+Q4 against −2.7% in Q1+Q3, a split that appears at no other stadium.

3. **It is not simply wind speed.** The penalty is −4.9% in games recorded at
   0–5 mph, and the wind × Gillette interaction is *positive* (+0.031/mph,
   p = 0.12) — Gillette is, if anything, less sensitive to measured wind than
   other outdoor venues. Recorded wind is one scalar from outside the bowl, so
   this argues against measured wind, not against swirl.

4. **Not the surface.** Grass 2002–05: −12.5%. FieldTurf years: −6.2%. Grass
   again 2019–20: +2.7%.

5. **New England's real, measurable edge was declining kicks.** On 4th down in
   competitive spots with a 50+ yard attempt available, the Patriots kicked
   6.9% of the time at Gillette, against 14.7% for themselves on the road
   (p = 0.052), 16.7% for visitors in the same building (p = 0.017), and 18.7%
   for all home teams elsewhere (p = 0.0006). Visitors at Gillette behaved
   exactly like a normal home team. This is selection, not deception, and it
   explains part of why New England's raw 87% looks good — but the distance
   controls mean it does not manufacture the visitor penalty.

## Part three: any venue

`venue_profile.py <stadium_id>` runs the whole battery against any stadium,
refitting the expected-make baseline each time to exclude the target venue.

```bash
python3 venue_profile.py NYC01   # MetLife      -> METLIFE.txt
python3 venue_profile.py BOS00   # Gillette     -> GILLETTE_PROFILE.txt
python3 venue_profile.py NYC00   # Giants Stadium
```

### MetLife (2010-2025): the reputation does not survive contact

MetLife is widely called one of the hardest places in the league to kick. Over
16 seasons and 550 visiting-kicker attempts it is the most precisely average
venue in the dataset: **86.55% actual against 86.54% expected**, z = +0.01,
19th of 29. Its home-minus-visitor gap is *negative* (−1.9%, 24th of 29) — the
resident teams kick slightly worse there than their visitors do, and Giants
kickers are 2.7 pp below expectation at home against +0.6 pp everywhere else.

Ball flight is mildly suppressed (punts −0.25 yds, 15th of 38; kickoff distance
8th) but visiting kickers there are *less* wind-sensitive than the league, not
more: −0.6% in 15+ mph games against −3.6% league-wide. The home teams show no
sign of local knowledge either — 18.8% of 50+ yard 4th-down chances kicked,
against a league home rate of 18.3% (p = 0.92).

The reputation appears to be inherited from the building it replaced. **Giants
Stadium (2002-09), on the same site, was genuinely hard**: visitors −2.2% vs
expectation (7th of 29) and punt distance −1.73 yds, the worst of all 38 venues
in the dataset. MetLife opened in 2010 and the effect largely went away.

## Part four: the site tab

`export_all.py` computes the profile for every venue clearing 150 visiting-kicker
attempts (36 of them) and writes `src/data/stadiums.ts`, which backs the
**Stadiums** tab at `/stadiums`.

```bash
python3 export_all.py    # regenerates src/data/stadiums.ts
```

Two things differ from the single-venue scripts above, both deliberate:

- **Leave-one-out baselines.** The expected-make model is refit 36 times, once
  per venue with that venue's own kicks held out, so no stadium is ever graded
  against itself. The spline basis is computed once over the full sample and
  reused, so every refit shares identical knots and a held-out venue can never
  fall outside them.
- **A hard NaN gate.** Dome and closed-roof venues have no recorded wind and
  some have too few coded misses, so several fields are genuinely absent. Every
  value is scrubbed to `null` if non-finite and serialised with
  `allow_nan=False`, which fails the run rather than emitting a bare `NaN`
  literal into TypeScript. The UI renders those as `—`.

The tab itself is `src/app/stadiums/page.tsx` +
`src/components/dashboards/StadiumDashboard.tsx`.
