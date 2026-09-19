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
| `nflverse-data` players | all | position filter, so QB keepers stay out |

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

The prose writeup of the full findings is still open; see the session discussion
for the tables this README summarises.
