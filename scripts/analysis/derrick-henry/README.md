# Derrick Henry, when his team was favoured

Does being the favourite change what Henry does, and what makes him an outlier?
2016-2026 regular season, designed runs only (no scrambles, kneels, or two-point
plays). Playoffs are counted separately where they appear.

## Running it

```bash
python3 -m venv .venv && .venv/bin/pip install pandas pyarrow
.venv/bin/python fetch.py          # caches ~130k carries, gitignored
.venv/bin/python splits.py         # favoured/underdog, by tier, by moneyline
.venv/bin/python script_control.py # separates "favoured" from "was ahead"
.venv/bin/python outlier.py        # percentile rank vs 101 modern RBs
.venv/bin/python synthesis.py      # box counts and RYOE, by favoured status
.venv/bin/python robustness.py     # does it survive the Tennessee/Baltimore split
.venv/bin/python touchdowns.py     # where the TDs come from
.venv/bin/python age.py            # the age curve, and who else survives to 30
.venv/bin/python receiving.py      # receiving work, snap share, scoring formats
```

`fetch.py` is idempotent — it skips anything already cached. Play-by-play is
pulled one season at a time and deleted after filtering, so peak disk stays near
one season's file rather than eleven.

## Data

All free, all nflverse:

| Source | Covers | Used for |
|---|---|---|
| `nfldata/games.csv` | 1999+ | spreads, moneylines, totals, roof |
| `nflverse-data` play-by-play | 1999+ | per-carry EPA, success, score state, live WP |
| `nflverse-data` NGS rushing | 2016+ | expected rush yards, RYOE, 8+ box rate |
| `nflverse-data` players | all | position filter and birth dates |
| `nflverse-data` stats_player_week | 2016+ | targets, air yards, YAC, fantasy points |
| `nflverse-data` snap_counts | 2016+ | share of offensive snaps played |

Verified against official records: 2020 reads 378/2,027/17 and 2024 reads
325/1,921/16, both exact.

## Conventions worth knowing

- **Spread sign.** nflverse quotes `spread_line` from the *home* team's side, so
  it is flipped for away games. `team_spread` in `common.py` is always positive
  when Henry's own team was favoured.
- **Moneylines carry vig.** The home/away pair implies more than 100%, so the
  two are normalised to sum to 1 before any win probability is read off them.
- **Peer group** is 400+ designed carries 2016-2026, RB/FB only — 101 backs.
  Without the position filter Lamar Jackson and Josh Allen top the efficiency
  boards, which tells you nothing about running backs.
- **`fantasy_points` is STANDARD scoring**, not half-PPR. Half-PPR is built in
  `receiving.py` as `fantasy_points + 0.5 * receptions` rather than assumed.
- **Age is computed per game**, not per season, so a January birthday is not
  credited with the same age as a December one.
- **Snap counts key on player name**, not gsis id, so they are joined on
  (game_id, display name) through the weekly stats.
- **RYOE starts in 2018**, not 2016. Box counts go back to 2016. Weighted means
  drop missing weeks rather than propagating NaN (`common.wavg`).

## Caveats that belong next to any number from this

- The favoured gap is positive in only **5 of 8 seasons** with both samples
  (median +0.39 YPC). 2018 was +2.08; 2023 was −1.74.
- `Fav 7+` is 288 carries across 16 games. Bootstrap 95% CI on its 5.53 YPC is
  **[4.67, 6.53]** — real, but not a two-decimal number.
- Henry was favoured in only 59% of his games, average line +1.2. His team's
  average line jumps from roughly even in Tennessee to +6.1 in 2024 Baltimore,
  so era and favouritism are tangled; `robustness.py` splits them and the effect
  survives in both (TEN +0.62, BAL +0.97 YPC).
- The age-30+ sample is small by construction: only 17 seasons of 200+ carries
  at 29 or older exist in the whole 11-year window, and Henry owns 3 of them.
  Peer age-30 YPC rests on 23 backs, age 31+ on 16.
- 2026 is **one game**. Ignore every number attached to it.
- In the Baltimore era the EPA gap is *negative* (−0.059) despite +0.97 YPC.
  Running with a big lead produces yards without much win-probability value.

## The short version

He faces eight-man boxes on **36.4%** of carries against a peer average of 23.6%
(97th percentile), and the yardage his blocking and box predict is **3.99 per
carry — 30th percentile**. He beats that by **+0.90 per carry**, 94th percentile.
Worst situations, best results.

When his team is favoured, peers see defences stack up harder (22.8% → 24.5%
eight-man boxes). Henry's box rate does not move (36.6% → 36.3%) because it is
already pinned — and that is exactly where his RYOE goes from +0.47 to +1.16.

He is also the rare high-volume back who ages *up*: the median peer loses
**−0.52 YPC** after turning 29, Henry gained **+0.33**, and his age-30 season
(1,921 yards at 5.91 a carry) is the most productive age-29-or-older season of
the entire tracking era.

And he did it without the thing modern back value is built on. Only **16.3% of
his PPR points come from the passing game** — 5th-lowest of 101 backs — while he
finishes **1st in career standard and half-PPR points** and 2nd in full PPR. The
only back above him in PPR, Christian McCaffrey, draws **54.9%** of his points
from receiving and plays 80.2% of his offence's snaps against Henry's 53.7%.

The prose writeup of the full findings is still open; see the session discussion
for the tables this README summarises.
