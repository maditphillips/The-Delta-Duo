# Why do the Ravens fade in second halves? (2020–2026)

Data: nflverse play-by-play, regular season + playoffs. 2026 is through Week 10.
"Second half" = 3rd + 4th quarters (overtime left out). "Leading" = up 1–16 points.

## 1. How unusual is the fade?

| Season | Coach | 1st half | 2nd half | Drop | Drop rank of 32 | Flag |
|---|---|---|---|---|---|---|
| 2020 | Harbaugh | +130 | +34 | −96 | **5th** | Big drop |
| 2021 | Harbaugh | −5 | 0 | +5 | 16th | — |
| 2022 | Harbaugh | +53 | **−25** | −78 | **5th** | Won 1st half, lost 2nd + big drop |
| 2023 | Harbaugh | +132 | +85 | −47 | **6th** | Big drop |
| 2024 | Harbaugh | +109 | +57 | −52 | **7th** | Big drop |
| 2025 | Harbaugh | +5 | +21 | +16 | 20th | — |
| 2026 | Minter | +35 | **−92** | −127 | **1st** | Won 1st half, lost 2nd + biggest drop in NFL; 2nd half is last in NFL |

- **Over 2020–2026 combined, the Ravens' drop (+459 first halves → +80 second halves, −379) is the biggest in the NFL.**
  League average drop is 0.
- Best comparison: Buffalo had the same first-half margin (+455) and was **+606** in second halves.
- Fair caveat: no team keeps all of its first-half edge. League-wide, teams carry about 35% of
  their first-half margin into the second half. Against that yardstick the Ravens are 74 points
  below expected over the span (11th worst). Most of that shortfall comes from 2022 and 2026; in
  2023–2025 their second halves were about as good as expected. The pattern is real, but it
  isn't every year.

![halves](chart_halves_by_season.png)

## 2. It's a 4th-quarter problem

Average point margin per game by quarter: Q1 +1.64 (**1st**), Q2 +2.25 (**1st**), Q3 +1.35 (4th), **Q4 −0.67 (24th)**.

![quarters](chart_by_quarter.png)

## 3. Blown leads

| | Ravens | NFL rate | Ravens rank |
|---|---|---|---|
| Lost after leading by 10+ | **17** of 75 (23%) | 17% | **Most in NFL** (9th by rate) |
| Lost after 85%+ win probability | **18** of 87 (21%) | 12% | **Most in NFL** (3rd by rate) |
| Led at half, lost the game | 19 of 72 (26%) | 23% | 11th |
| Led at half, lost the 2nd half | 31 of 72 (43%) | 49% | 27th (better than average) |

Two things stand out. First, they get big leads more than almost anyone, so the raw count is
inflated. But the *rate* of losing after an 85% win chance is nearly double the league's.
Second, they don't lose the second half more often after leading at the half. When they do lose
it, they lose the whole game.

![blown](chart_blown_leads.png)

Full list of flagged games: `game_flags.csv` (filter team = BAL).

## 4. What they do differently when leading

### Defense: the main problem
4th quarter, leading by 1–16, pass plays (`pass_run_by_period.csv`, `q4_pass_defense_by_season.csv`):

- EPA per dropback allowed: **Ravens +0.153 vs NFL +0.013. Worst in the NFL over 2020–2026.**
- Worse than league average in 6 of 7 seasons (all but 2023). That holds across three defensive
  coordinators (Martindale, Macdonald, Orr) and the 2026 staff.
- Same defense in the 1st half with a lead is good: −0.047 EPA per play allowed, better than the NFL's +0.016.

Second half with a lead (`behavior.csv`), Ravens vs NFL, rank of 32:
- EPA allowed per play +0.062 vs +0.001 (**5th worst**)
- 3rd downs allowed 43% vs 40% (**4th worst**); 34% when leading in the 1st half
- Explosive plays allowed 10.2% vs 8.8% (**3rd worst**)
- Takeaways 1.9% of plays vs 2.6% (**28th**)
- Points allowed per opponent drive: 2.52 vs 2.08 (**4th most**). Above league average every season except 2023.

![q4 pass d](chart_q4_pass_defense.png)

### Offense: the most conservative in the league, but efficient
Second half with a lead:
- Pass rate 42% vs NFL 50% (**32nd: lowest in the NFL**)
- Early-down pass rate 37% vs 43% (30th). Pass rate over expected −6.7% (30th).
- In the 4th quarter specifically: 31.5% pass rate vs the NFL's 44%.
- Pace: 30.8 seconds per snap (4th slowest).

They run a lot and burn clock. On average it still works: success rate is **1st** in the NFL,
EPA per play 3rd, and points per drive 2.39 vs 1.80 (3rd). The conservatism alone doesn't explain
the fades. It does mean fewer possessions, so each defensive breakdown counts for more.

### In the blown games specifically
Second half while leading, blown games vs games where they held on:
- Offense EPA per play −0.07 vs +0.19; 3rd downs 34% vs 51%; turnovers 2.4% vs 0.6% of plays.
- Defense EPA allowed +0.22 vs −0.16; 3rd downs allowed 52% vs 35%; takeaways 0.7% vs 3.5%.

Note: this split is partly circular. A game is "blown" *because* the other team scored, so the
defense will look worse in those games by definition. The league comparisons above are the
stronger evidence.

### Not the cause
- 4th-down decisions: go-for-it rate when leading in the 2nd half is 11% vs NFL 11%. They convert 89% vs the NFL's 60% (small sample: about 18 attempts).
- Penalties: about league average *when leading* (but see section 10: across all 4th quarters, the Ravens commit the 4th-most defensive penalties and 2nd-most pass interference).
- Sacks: about league average on both sides.

## 5. Deep dive: 4th-quarter pass defense — what are they calling?
Tracking data: nflverse participation (coverage, man/zone, rushers, pressure, time to throw; 2020–2025)
and FTN charting (blitzers; 2022–2026). Opponent dropbacks, Ravens up 1–16 in the 4th quarter (764 plays),
vs. the same defense with a 1st-half lead and vs. the other 31 teams in the 4th with a lead.
Files: `deep_defense*.csv`.

**It is not a soft prevent defense. It's the opposite.**

| 4th quarter, leading | Ravens | NFL | Ravens rank of 32 |
|---|---|---|---|
| Man coverage rate | **44%** | 34% | **2nd most** |
| Cover 0 (all-out man, no deep safety) | **12%** | 4% | Top 3 in 5 of 6 seasons |
| Prevent coverage | 0.4% | 0.6% | about average |
| Rushers sent / blitz rate | 4.3 / 22% | 4.2 / 25% | about average |
| Pressure rate | 30% | 32% | 25th |
| Opponent time to throw | 2.70s | 2.79s | quickest in NFL |
| EPA per dropback allowed | **+0.15** | +0.01 | **worst** |
| 20+ yard completions allowed | **11.3%** | 8.0% | **worst** |
| Completion % over expected allowed | +2.2 | −0.6 | 4th worst |
| Interception rate | 1.6% | 2.7% | 30th |
| Contested-catch rate | 16% | 14% | 6th |

What it shows:
- **The call stays the same, and opponents beat it.** Ravens man coverage allows −0.01 EPA per
  dropback in the 1st half and **+0.22 in the 4th**. The NFL average in man in the 4th is +0.05. Cover 0
  goes from −0.18 (1st half) to +0.32 (4th). Small samples per coverage (50–180 plays each), but the
  direction is the same for every man-based call.
- **Correction on timing:** opponents do *not* throw much faster late. Against the Ravens, time to throw is
  2.64s in the 1st half and 2.70s in the 4th. Across the league, QBs hold the ball about 0.09s longer in the
  4th; against the Ravens they don't. So the Ravens rank quickest in the 4th mostly because everyone else
  slows down. What actually changes is the result of the throws: air yards per completion rise from 5.8 to
  7.4, completion % over expected goes from −0.6 to +2.2, and 20+ yard completions go from 6.9% to 11.3%.
  Pressure actually goes *up* (26% → 30%). The man coverage is getting beaten in coverage, not just outrun
  by the clock.
- Zone isn't a fix either: +0.15 EPA in the 4th, still worse than the league.
- **Not fatigue or backups.** Ravens defenders have played about the same number of snaps by the 4th
  quarter as the league (42 vs 44). Their top-11 defenders are on the field as often in the 4th as the
  league norm.
- **Why it survives coordinator changes:** man-heavy, blitz-and-Cover-0 has been the Ravens' defensive
  identity for years, and each coordinator in this span (Martindale, Macdonald, Orr) was promoted from
  inside the Ravens' own staff. Cover 0 in the 4th with a lead was top 3 in the NFL in 2020, 2021, 2023,
  2024 and 2025. The data can't prove why the staff keeps calling it. It does show the same aggressive
  approach carrying into situations where offenses are set up to beat it.

![defense calls](chart_q4_defense_calls.png)

## 6. Deep dive: the run-heavy offense — choice or situation?
Files: `deep_offense*.csv`. Plays the Ravens run while up 1–16.

**It's a choice.** nflverse's expected pass rate model accounts for down, distance, field position,
score and time. In the 4th quarter with a lead the Ravens pass **9.2 points below expected, last in the NFL**.
The league is at +0.7. They are below expected in every season 2020–2026, under both offensive
coordinators in the Harbaugh years and in 2026. 2024 was the extreme: −14.7 in the 2nd half, most
run-heavy in the league.

| 4th quarter, leading | Ravens | NFL | Ravens rank of 32 |
|---|---|---|---|
| Pass rate | 32% | 44% | 32nd (lowest) |
| Pass over expected | −9.2 | +0.7 | 32nd |
| 1st-down pass rate | 21% | 27% | 30th |
| Under center | 27% | 47% | 31st (they stay in the gun and run) |
| 3+ WR personnel | 29% | 49% | 31st |
| QB designed runs (share of runs) | 19% | — | 1st |
| Defenders in the box | 6.9 | 6.7 | most in NFL |
| 8+ man box | 27% | 20% | 4th most |

**But the running works.** Run EPA in the 4th with a lead is +0.02 vs the NFL's −0.09 (**1st**).
Run success 44% vs 36% (1st). Stuffs 15% vs 21%. They gain 5.0 yards a carry even against 8+ man boxes (NFL 3.6).
Because of that, they face shorter 3rd downs (5.6 yards vs 6.8; 3rd-and-7+ only 34% of the time vs 46%).
Their 4th-quarter EPA per play (+0.02) is still above the NFL's (−0.02).

Where it arguably costs them: in 2020, 2024 and 2025 their early-down *passing* in 2nd halves with
a lead was much better than their running (2024: +0.32 vs +0.15; 2025: +0.52 vs +0.01), and they still
passed far less than expected. The offense isn't what's losing these games. It is choosing the
lower-variance option even when passing is working, which keeps the score close and puts the game on
the defense.

![offense](chart_offense_proe.png)

## 7. 2026: the first head-coach change in the span
Files: `defense_2026.csv`, `defense_2026_games.csv`, `off_def_split.csv`. nflverse has no 2026 participation
data yet, so **coverage (man/zone, Cover 0), pressure and time to throw can't be checked for 2026.** FTN
charting (blitzers, rushers, contested balls) is available. 2026 is 10 games, so samples are small.

**Is the 2nd-half drop the offense or the defense?** (`split_2026.py`)

| Season | Offense: 2nd-half pts minus 1st-half pts | Rank (1 = biggest drop) | Defense: extra pts allowed in 2nd half | Rank (1 = biggest) |
|---|---|---|---|---|
| 2020 | −65 | 3rd | +31 | 7th |
| 2021 | +38 | 28th | +33 | 10th |
| 2022 | −21 | 15th | +57 | **1st** |
| 2023 | −35 | 10th | +12 | 9th |
| 2024 | +2 | 16th | +54 | 5th |
| 2025 | +58 | 29th | +42 | 6th |
| **2026** | **−74** | **1st** | **+53** | **1st** |

- **The defense allowed more points after halftime in all 7 seasons, top 10 in the league every year.**
  League average is close to zero. This is the most consistent part of the whole pattern.
- The offense's 2nd-half drop comes and goes (big in 2020, absent in 2021, 2024, 2025).
- **2026 is the first season where both sides are the worst in the NFL at once.** The offense scored 138
  in 1st halves and 64 in 2nd halves (shut out after halftime in 3 of 10 games). The defense allowed 103 → 156.
  So 2026's −92 is about 58% offense, 42% defense.

**The 2026 defense, compared with past Ravens defenses and the 2026 NFL**

| | 1st half 2026 | 2nd half 2026 | 2nd half, Ravens 2022–25 | 2nd half, NFL 2026 |
|---|---|---|---|---|
| Pass EPA allowed | **−0.09** (5th best) | **+0.20** (5th worst) | +0.02 | +0.04 |
| Pass success allowed | 39% (2nd best) | **51%** (4th worst) | 43% | 45% |
| Completion % over expected | −4.3 | **+7.1** (6th highest) | +1.3 | +1.1 |
| 20+ yard completions | 8.7% | 7.8% (20th) | 9.2% | 8.4% |
| Takeaways per dropback | 3.7% | **1.0%** (31st) | 2.7% | 3.1% |
| Blitz rate | 30% | **36%** (11th) | 25% | 32% |
| Sack rate | 5.6% | 5.2% (23rd) | 7.0% | 6.7% |

What's the same and what's different in 2026:
- **Same:** an excellent 1st-half pass defense that turns into one of the worst after halftime, with almost no
  takeaways. Late-game aggression goes *up*, not down: blitz rate rises from 30% to 36% after halftime,
  above the league, but sacks fall to 23rd.
- **Different:** 2020–2025's problem was big plays. In 2026 big plays are about average. Instead, opponents
  complete almost everything (+7.1% over expected) and move the chains steadily.
- Run defense is about average in 2026 2nd halves. It's still the pass defense.
- The 2026 2nd-half damage is lumpy: Cincinnati (35 points, +1.05 EPA per dropback) and Buffalo (20) make up
  much of it. Jacksonville and the Chargers were held well below average.

## 8. Does the fade follow Ravens coaches to other teams?
Files: `coaching_tree.py` → `coaching_tree.csv`, `team_season_defense.csv`. Ranks are within each season,
1 = worst of 32. "2nd-half extra points" = points allowed in 2nd halves minus 1st halves.
Coaching history as supplied by the user: Jesse Minter (Ravens assistant / DBs coach 2017–2020, Chargers DC
2024–2025, Ravens HC and defensive play caller 2026); Anthony Weaver (Ravens 2021–2023, Dolphins DC 2024–2025,
not the play caller; Ravens DC 2026, not the play caller).

| Defense | Seasons | 2nd-half extra points allowed (rank) | Q4-with-lead pass EPA (rank) | Man rate Q4 lead (rank) |
|---|---|---|---|---|
| Ravens, Martindale | 2020, 2021 | 7th, 10th | 13th, 1st | 3rd, 8th |
| Ravens, Macdonald | 2022, 2023 | **1st**, 9th | 2nd, 23rd | 15th, 5th |
| Ravens, Orr | 2024, 2025 | 5th, 6th | 16th, 6th | 1st, 11th |
| **Ravens, Minter (play caller)** | 2026 | **1st** | 4th | no data yet |
| Giants, Martindale | 2022, 2023 | 15th, 18th | 21st, 15th | 2nd, 9th |
| Seahawks, Macdonald | 2024, 2025, 2026 | 22nd, 5th, 28th | 23rd, 15th, 19th | 9th, 12th |
| **Chargers, Minter** | 2024, 2025 | 8th, 22nd | 11th, 23rd | 31st, 27th |
| Dolphins, Weaver (not play caller) | 2024, 2025 | 14th, 2nd | 25th, 7th | 23rd, 30th |

- **In Baltimore, the defense ranked top 10 in 2nd-half extra points allowed in 7 of 7 seasons.**
- **The same coaches elsewhere did it in 3 of 9 seasons**, about what you'd expect by chance (10 of 32
  teams land in the top 10 every year).
- **Minter is the cleanest test.** Calling plays for the Chargers, his defenses played very little man
  (31st, 27th) and faded only mildly (8th, then 22nd). Calling plays for the Ravens in 2026, the defense has the
  worst 2nd-half fade in the NFL.
- Martindale kept calling heavy man and Cover 0 late with the Giants (2nd in both in 2022), and the Giants'
  late pass defense was fine. So the aggressive call isn't doomed by itself. It fails in Baltimore.
- Roster: only Marlon Humphrey was a regular in the Q4-with-a-lead defense in at least 5 of the 6 seasons
  with tracking data (Kyle Hamilton since 2022, Roquan Smith since late 2022). The roster has turned over a lot,
  so it isn't one or two players.

**What this means:** the fade doesn't travel with the coaches. It stays in Baltimore across three
defensive coordinators, a new head coach, a new defensive play caller and a mostly new roster. The data
can't say exactly what the Baltimore constant is. Candidates: the front office and how it builds the
roster (especially the secondary), a defensive identity that new staffs adopt when they arrive, or the
game situations the Ravens offense creates. When nflverse publishes 2026 coverage data, check whether Minter's
Ravens are calling the Ravens' man-heavy style or his low-man Chargers style. That would separate
"coaches adopt the Ravens identity" from "same calls, different results in Baltimore."

## 9. Does the run-heavy offense put the defense in bad spots?
Files: `game_situation.py` → `situation_offense.csv`, `situation_handoff.csv`. Every 4th-quarter Ravens drive
that starts with a 1–16 point lead (135 drives), and the opponent drive that follows it.

| 4th quarter, leading | Ravens | NFL | Ravens rank of 32 |
|---|---|---|---|
| Run share of plays | **69%** | 59% | **1st** |
| Minutes used per drive | 2.46 | 2.27 | 7th most |
| Points per drive | 1.57 | 1.44 | 9th |
| 3-and-out rate | 19% | 21% | 23rd (fewer than most) |
| Punt rate | 31% | 35% | 25th (fewer than most) |
| Ran out the clock (last 5 min) | 63% | 54% | — |
| Opponent's next drive starts (yards from end zone) | 54 | 58 | 4th shortest field |
| **Opponent's next drive scores** | **35%** | 27% | **1st (worst)** |

**Mostly no.** The run-heavy offense does its job late: it uses more clock, punts less, goes three-and-out
less, and closes out games in the last 5 minutes more often than the league. The defense doesn't face more
late dropbacks than normal either (10.8 per game vs 10.3).
The one cost: opponents start their next drive about 4 yards closer than normal. That's small next to the
gap in what happens on that drive: opponents score on 35% of them against the Ravens vs 27% league-wide,
the worst in the NFL. The game situation isn't the main cause. The late defense is.

## 10. Outside sources (verified by reading the pages)
Read in full unless noted. CBS and AP pages would not load; those items are marked.

**2026: Minter changed the scheme, and the late fade stayed**
- Minter's 2025 Chargers (Ravens.com, Jan 23 2026, NGS): 80.7% zone (5th most), 21.4% blitz (3rd fewest),
  49.6% two-high safety (4th most). https://www.baltimoreravens.com/news/jesse-minter-defensive-scheme-film-ravens-head-coach-hire
- Man coverage over 2024–25 (SI, Jun 7 2026, TruMedia): Ravens under Orr 30.3% (7th), Minter's Chargers 14.4%
  (lowest in NFL), league 24%. https://www.si.com/nfl/ravens/onsi/a-change-of-coaches-and-scheme-should-prompt-a-breakout-for-one-young-ravens-corner-01kthe7568vs
- 2026 Ravens through Week 3 (Banner, Sep 30 2026, NGS): two-high safety 54.7% (8th) vs 32.6% in 2025 (2nd lowest).
  "Minter has opted to try to stop the run without pushing a safety toward the box." Only 5 throws of 20+ air
  yards allowed (2nd fewest). https://www.thebanner.com/sports/ravens-nfl/ravens-september-statistics-lamar-jackson-jesse-minter-UPHAT5NLAFCSJMK3ORYRWLMYIM/
- 2026 pressure-rate rank fell from 10th (Weeks 1–4) to 19th (Weeks 5–9) (Ravens.com, Nov 10 2026, source not named).
  https://www.baltimoreravens.com/news/ravens-first-half-stats-2026-season-lamar-jackson-zay-flowers-defense
- **2026 defense EPA per play by quarter (Banner, Oct 26 2026, through Week 7): 3rd in Q1, 3rd in Q2, 22nd in Q3,
  32nd in Q4.** Opponent QBs: 59.4% completions, 1 TD, 2 INT in 1st halves; 71.3%, 8 TD, 0 INT in 2nd halves.
  https://www.thebanner.com/sports/ravens-nfl/ravens-bengals-first-half-second-half-lamar-jackson-joe-burrow-jesse-minter-defense-WQX4OAUQEFB37KTWITAV6FYAAI/
- Ravens.com, Nov 10 2026: most 4th-quarter points allowed in the NFL (11.4 per game), a 4th-quarter TD allowed in
  8 of 9 games. Minter on explosive plays: "major concern No. 1… It's all lip service right now." A lineup and
  scheme shake-up is being considered. https://www.baltimoreravens.com/news/jesse-minter-ravens-defense-shake-up-marlon-humphrey-fourth-quarter-woes-explosive-plays-jaguars
- No public source has 2026 man/zone, Cover 0–6 rates, or any 4th-quarter / leading split. SumerSports keeps
  situational splits behind a paid tier; the NGS data API needs a login.

**2020–2025 4th-quarter record (SI, May 29 2026, La Canfora)**
https://www.si.com/nfl/ravens/onsi/jesse-minter-must-succeed-where-many-others-have-failed-fixing-ravens-fourth-quarter-defense-01ksr6ez3x22
- Through three quarters: 1st in points allowed, +609 point differential. In 4th quarters since 2020: 29th in yards
  per play, 28th in points allowed, 30th in defensive EPA, 30th in 15+ yard completions allowed (185 vs league
  average 139), 20th in pressure rate, 28th in interception rate.
- 2nd-highest 4th-quarter Cover-0 rate; Orr led the NFL in Cover-0 in 2024–25; Minter's Chargers ran 50% more
  4th-quarter Cover-4 than average.
- Worst 4th-quarter penalty margin (−35) and 2nd-most DPI flags. The author: "a collective mindset and mentality that was hardwired to collapse."
- **Checked in our data (`penalties.py` → `penalties_q4.csv`):** Ravens defensive penalties per game are below
  average in quarters 1–3 (24th) but 4th most in the 4th quarter. Defensive pass interference in the 4th: 0.25 per
  game vs 0.15 league (**2nd most**). This corrects section 4, which found penalties about average using only
  plays where the Ravens led.

**What players and coaches say happens late (2026)**
- After CIN (Banner, Oct 26): Minter: "We're missing some tackles… plays that were maybe third-and-5… in the first
  half are now second-and-1… starting with me — it was just a bad effort by the defense in the second half."
  11 missed tackles (PFF). Burrow got the ball out faster: "Which we figured they would."
  https://www.thebanner.com/sports/ravens-nfl/things-we-learned-ravens-bengals-7Y7VMFXKHVGCVDXDMIFGV4E7YY/
- After NO (Ravens.com, Sep 22): Minter: "guys start pressing a little bit… searching for that big play."
  Hendrickson: "When we had good coverage, sometimes our rush was not there." No 4th-quarter sacks vs a quick-passing
  Saints offense. https://www.baltimoreravens.com/news/ravens-defensive-identity-jesse-minter-defense-fourth-quarter-trey-hendrickson-malaki-starks-jaylinn-hawkins-poor-tackling-coverage-mistakes-pass-rush
- Mental health staff: every NFL team has had to retain a behavioral health clinician since 2019 (NFL–NFLPA
  agreement; SI, Jul 18 2019, https://www.si.com/nfl/2019/07/18/mental-health-players-pain-management-marijuana-cbd).
  The Ravens' is Dr. Tricia Bent-Goodley (Ravens.com front-office page). A *dedicated* sports psychologist or
  mental-performance coach is separate; no league-wide count was found. Other teams named in search results (Packers,
  Chiefs, Seahawks historically) were not verified. Banner, Oct 30 2026: "the Ravens do not employ a dedicated sports
  psychologist or mental performance coach"; Minter said existing staff "offers similar coverage." No evidence the
  Ravens ever had one, but their full history wasn't searched.
- Psychology (Banner, Oct 25 & 30): players describe the history seeping "into the psyche" and the team being "too much
  of a momentum team." The Ravens have no dedicated sports psychologist.
  https://www.thebanner.com/sports/ravens-nfl/ravens-jesse-minter-momentum-problem-B5Y7N23QLND5LA4SHXMWKWN4HU/
- Ravens.com Sep 20: 15th loss after a double-digit lead since 2019 (per ESPN). Minter: "Everybody is going to just
  say the same old thing of having a lead… So, we will own this." https://www.baltimoreravens.com/news/ravens-react-blown-fourth-quarter-lead-saints-2026

**Front office and roster**
- SI, Apr 3 2026: Ravens 29th in pass defense two straight seasons (246 yards per game); first-round DBs in 2024
  (Nate Wiggins) and 2025 (Malaki Starks). https://www.si.com/nfl/ravens/onsi/news/three-reasons-why-ravens-could-draft-a-defensive-back-in-third-straight-nfl-draft-01kn884r4pwj
- SI, Jul 29 2026: criticizes "the naivety of… DeCosta's roster construction" and "whiffing systematically… on
  'projectable pass rushers'"; a backup led the 2025 team in third-down sacks with 1.5.
  https://www.si.com/nfl/ravens/onsi/four-metrics-jesse-minter-must-correct-for-ravens-defense-01kynh6wbwm4
- 2026 offseason: backed out of the Maxx Crosby trade after a failed physical (knee); signed Trey Hendrickson
  (4 yr, $112M, NFL.com snippet); lost Alohi Gilman, Dre'Mont Jones, Ar'Darius Washington (Kyle Van Noy unsigned).
  Draft defense picks: Zion Young (R2), Chandler Rivers (R5), Rayshaun Benny (R7).
  https://www.baltimoreravens.com/news/free-agency-tracker/ , https://www.baltimoreravens.com/draft/draft-tracker/2026/
- Banner, Oct 30 2024: of 59 explosive passes allowed, only about a dozen came from disguise breakdowns; the rest were
  "one-on-one battles lost, zone holes punctured, open-field tackles missed."
  https://www.thebanner.com/sports/ravens-nfl/ravens-defense-zach-orr-mike-macdonald-dean-pees-disguised-coverages-XU35W74AEFB3HBIM7HEOQJ7KXE/

**Not verified at the source (pages blocked):** CBS "Ravens and blown leads" (snippets: last in EPA per play when
leading in the 4th, 22nd in pressure rate; appears to be from 2022–23); AP's count of 17 blown double-digit 2nd-half
leads under Harbaugh, most since 1991 (seen only as a Steelers Depot citation).

## 11. Are the Ravens good at drafting except pass rushers?
Files: `draft.py` → `draft_value.csv`, `draft_ravens_edge.csv`, `draft_ravens_cb.csv`. nflverse draft picks,
2010–2025 drafts. Value = Pro Football Reference weighted career Approximate Value (AV). Expected = the average
AV of picks within 6 slots in the same draft, so a 2024 pick is only compared to other 2024 picks. Positions use
PFF's position (ED = edge), so edge rushers listed as "LB" on draft day count as edge.

| Position | Newsome 2010–18: AV vs expected / hit rate | DeCosta 2019–25: AV vs expected / hit rate |
|---|---|---|
| All picks | +2.5 / 40% | +0.7 / 37% (14th of 32) |
| Edge | +10.6 / 62% | **−2.4 / 29%** (20th) |
| Cornerback | −4.3 / 12% | **−3.1 / 11%** (22nd) |
| Safety | −0.6 / 50% | +5.9 / 75% |
| Off-ball LB | −4.2 / 50% | +7.3 / 67% |
| Interior DL | +3.5 / 55% | +1.6 / 50% |
| Offensive line | +7.8 / 47% | +4.0 / 54% |

"Hit" = the player has beaten the expected AV for his draft slot. Recent picks (2024–25) have had little time, so treat them loosely.

- **Partly right: the pass-rusher problem is a DeCosta-era problem.** Under Newsome the Ravens were among the
  best at finding edge rushers in the middle rounds: Pernell McPhee (R5), John Simon (R4), Za'Darius Smith (R4),
  Matt Judon (R5). Their misses were the early picks (Courtney Upshaw, Kamalei Correa). Under DeCosta it flipped:
  6 of 7 edge picks came in rounds 1–3 (Jaylon Ferguson, Odafe Oweh, David Ojabo, Adisa Isaac, Mike Green, plus
  Malik Harrison, who moved to edge), and only 2 of 7 beat their slot.
- **The bigger blind spot is cornerback, under both GMs.** Of 20 corners drafted since 2010, only **two** beat their
  slot: Marlon Humphrey (2017) and Brandon Stephens (2021). That's an 11–12% hit rate, the worst position group in
  both eras. Humphrey is also the one defender who has been a regular in late-game defense every year.
- **The rest is genuinely good:** safeties (Kyle Hamilton, Geno Stone), linebackers (Roquan Smith came by trade;
  drafted: Patrick Queen, Trenton Simpson), offensive line and interior DL beat expectation.
- **Overall, DeCosta is about league average (14th of 32), not elite.** The positions he misses on, edge and
  corner, are exactly the two jobs that fail late in games: rushing the passer and covering one-on-one.
- Several Newsome-era edge hits (Smith, Judon, McPhee) had their best years after leaving Baltimore in free
  agency, so even good edge picks often weren't kept.

## 12. Teams with vs without a dedicated sports psychologist
Files: `psych_compare.py` → `psych_compare.csv`, `psych_compare_teams.csv`; team list in `sports_psychologists.md`.
2020–2026, regular season + playoffs.

Groups:
- **Has a psychologist (6 teams):** Packers 2020–26 (Chris Carr), Lions 2021–26 (Michelle Garvin), Bears 2022–26
  (Mike Wiley Jr.), Bills 2023–26 (Desaree Festa), Chiefs 2022–26 (Shaun Tyrance's VP role covering performance
  psychology from 2022; Tyler Bradstreet, VP of Performance Psychology, likely 2026), Titans 2026 only (Charron
  Sumler; single source, 9 games). Seasons before each hire are left out.
- **No psychologist (14 teams):** Steelers (only confirmed "no") plus 13 teams where a search found nobody (Bengals,
  Browns, Texans, Colts, Raiders, Chargers, Cowboys, Patriots, Jets, Saints, 49ers, Broncos, Dolphins). "None found" is not proof.
- **Ravens:** confirmed none.

| Per game / rate | Ravens | Has psychologist | No psychologist |
|---|---|---|---|
| Win % | .585 | .596 | .477 |
| 1st-half point diff | +3.9 | +1.6 | −0.4 |
| 2nd-half point diff | +0.7 | +1.6 | −0.4 |
| 2nd half minus 1st half | **−3.2** | 0.0 | 0.0 |
| 4th-quarter point diff | **−0.7** | +0.6 | 0.0 |
| Extra points allowed in 2nd half | **+2.4** | −0.4 | −0.4 |
| Lost after leading by 10+ | **23%** | 12% | 17% |
| Lost after 85%+ win chance | **21%** | 9% | 11% |
| Lost after leading entering the 4th | **23%** | 13% | 18% |
| Lost after leading by 7+ entering the 4th | **19%** | 8.5% | 8.5% |
| Lost after leading at half | **26%** | 15% | 25% |

- **The Ravens are worse than both groups on every measure.** Among these 21 teams they rank last in 2nd-half
  fade and extra 2nd-half points allowed, 3rd worst in losses after an 85% win chance, and 5th worst after leading by 10+.
- **The psychologist teams blow fewer leads than the no-psychologist teams on most measures.** But they also win far
  more (60% vs 48%), and better teams naturally blow fewer leads, so this can't be credited to the psychologist.
  On the cleanest late-game measure, losing a 7+ point lead in the 4th quarter, the two groups are identical (8.5%).
- **Inside the psychologist group it varies a lot.** Bills, Chiefs and Lions rarely blow leads (about 5–10%); the
  Bears blow them about as often as the Ravens (22% after leading by 10+). The Titans have only 9 games.
- **Bottom line:** the data shows no clear effect of having a dedicated psychologist, but it confirms the Ravens are
  an outlier against both groups. A hire could still be worth trying; these numbers just can't promise it would help.

![psych](chart_psych_compare.png)

## Bottom line
1. The Ravens are the best 1st-quarter and 2nd-quarter team in the NFL since 2020 and 24th in the 4th quarter.
2. The main repeated weakness is **pass defense late in games with a lead**: worst in the NFL, across
   three defensive coordinators and a new head coach.
3. **It's a play-calling identity, not a soft defense.** The Ravens keep calling man coverage and Cover 0
   at 2–3 times the league rate. Late in games those calls get beaten: bigger and more accurate completions,
   the most 20+ yard completions in the league, few takeaways. The same calls work in the 1st half.
4. **The offense turns the most run-heavy in the NFL with a lead, by choice** (last in pass rate over
   expected). The running itself is the best in the league, so it isn't the cause. But it means fewer
   points added late, and even when passing is working, the game is left on the defense.
5. **Why it hasn't been fixed:** the fade stays in Baltimore and doesn't follow coaches out. Ravens defenses
   faded in 7 of 7 seasons; the same coaches elsewhere in 3 of 9 (about chance). In 2026 Minter replaced the
   man-heavy, Cover-0 scheme with zone and two-high safeties, and the defense is still 32nd in the 4th quarter.
   **So the play calls aren't the root cause.** What stays constant is how the late plays are lost: deep
   completions and missed tackles, a pass rush that disappears late (20th in 4th-quarter pressure since 2020),
   late pass-interference flags (2nd most), and, by the players' own account, pressing and a "momentum" mindset.
   Outside critics point at the front office's record finding pass rushers and cover players.
6. **The defense allowed more points after halftime in every season 2020–2026** (top 10 in the NFL each year).
7. **2026 under the new head coach:** the same defensive shape (great 1st halves, bad 2nd halves, few
   takeaways, more blitzing late), but it shows up as opponents completing everything rather than big plays.
   2026 is also the first year the offense collapses after halftime as badly as the defense (worst in the
   NFL on both). It's 10 games, and coverage data for 2026 isn't published yet.

## Files
- `halves.py` → `team_games.csv`, `ravens_by_season.csv` (all teams, 1999–2026)
- `fade.py` → `season_fade.csv` (drop ranks, expected 2nd half)
- `blown.py` → `game_flags.csv`, `blown_by_team.csv`
- `behavior.py` → `behavior.csv`, `behavior_ranks.csv`
- `extras.py` → `quarters.csv`, `drives.csv`, `fourth_downs.csv`, `pass_run_by_period.csv`, `q4_pass_defense_by_season.csv`
- `deep_defense.py` → `deep_defense.csv`, `deep_defense_coverage.csv`, `deep_defense_by_season.csv`, `deep_defense_starters.csv`,
  `deep_defense_cover0_by_season.csv`, `deep_defense_man_zone.csv`
- `deep_offense.py` → `deep_offense.csv`, `deep_offense_by_season.csv`, `deep_offense_box.csv`
- `defense_2026.py` → `defense_2026.csv`, `defense_2026_games.csv`
- `split_2026.py` → `off_def_split.csv`
- `coaching_tree.py` → `coaching_tree.csv`, `team_season_defense.csv`
- `game_situation.py` → `situation_offense.csv`, `situation_handoff.csv`
- `penalties.py` → `penalties_q4.csv`
- `psych_compare.py` → `psych_compare.csv`, `psych_compare_teams.csv`
- `draft.py` → `draft_value.csv`, `draft_ravens_edge.csv`, `draft_ravens_cb.csv` (needs nflverse `draft_picks.csv` and `players.csv` in DATA)
- `charts.py` → `chart_*.png`

Run order: `halves.py DATA`, `fade.py`, `blown.py DATA`, `behavior.py DATA`, `extras.py DATA`,
`deep_defense.py DATA`, `deep_offense.py DATA`, `defense_2026.py DATA`, `split_2026.py`, `coaching_tree.py DATA`, `game_situation.py DATA`, `penalties.py DATA`, `draft.py DATA`, `psych_compare.py DATA`, `charts.py`.
`DATA` holds `pbp_slim.parquet` (selected columns of nflverse `play_by_play_1999`–`2026.parquet`) and
`pbp_deep.parquet` (2020–2026 play-by-play joined on game_id + play_id to nflverse `pbp_participation_2020`–`2025`
and `ftn_charting_2022`–`2026`).
