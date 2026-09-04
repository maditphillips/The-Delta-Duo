# Data sources

## Structured data — all nflverse

Everything numeric in this study comes from the
[nflverse-data](https://github.com/nflverse/nflverse-data) releases. `fetch.py`
pulls these directly:

| Release | Asset | Coverage | Used for |
|---|---|---|---|
| `pbp` | `play_by_play_{season}.parquet` | 1999-2025 | every rush and target: yards, EPA, success, first downs, TDs; game dates; team schedules; team carry/target totals for share metrics |
| `players` | `players.parquet` | all | position, birth date (age at injury), `gsis_id` ↔ `pfr_id` crosswalk |
| `snap_counts` | `snap_counts_{season}.parquet` | 2012-2025 | offensive snaps and snap share |
| `nextgen_stats` | `ngs_rushing.parquet` | 2016-2025 | rush yards over expected per attempt, NGS efficiency, % of carries against 8+ defenders |

Two nflverse tables were pulled during exploration and are **not** used in the
final pipeline: `injuries` (2009-2025 weekly injury reports) and
`weekly_rosters` (2002-2025). The injury reports were the obvious place to look
for the cohort and are the reason this study needs an external one — see below.

### Why the cohort could not come from nflverse

`injuries` records `report_primary_injury` / `practice_primary_injury` as a body
part. Across 90,752 injury-report rows from 2009-2025 the top values are `Knee`
(11,135), `Ankle`, `Hamstring`, `Shoulder`. The string "ACL" appears **zero
times** in any of the four injury-description fields. An ACL rupture, an MCL
sprain, a meniscus tear and a bone bruise are all just `Knee`.

What nflverse *can* do — and what was used — is find every running back who
missed a long stretch and then measure exactly what he did before and after.
A screen for RBs who missed 6+ team games with 30+ touches in their prior 8
games returns 209 modern-era absences; that list was used to make sure no
qualifying ACL tear was missed, and to pin down last-game and return-game dates
to the day. But deciding *which* of those absences were ACL tears required
naming each injury from reporting.

## Cohort — hand-built, individually sourced

`acl_cohort.csv`. Each row carries a `confidence` and a `date_basis`:
`reported` = the date comes from contemporaneous reporting; `lastgame` = the
date is the last game the back played, which for an in-game tear is the tear
itself; `approx` = an offseason tear dated to within a few weeks.

Diagnoses were confirmed against contemporaneous reporting. Confirmations that
resolved a genuine uncertainty, or that corrected an assumption:

- **Olandis Gary** (2000) — torn ACL, right knee, in the season opener vs. St. Louis. [ESPN](http://www.espn.com/nfl/news/2000/0905/724439.html), [Grokipedia](https://grokipedia.com/page/Olandis_Gary)
- **Jerious Norwood** (2010) — torn ACL on a kickoff return vs. Arizona; often mis-remembered as the hip problem that dogged him. [NFL.com](https://www.nfl.com/news/torn-acl-ends-season-for-falcons-backup-rb-norwood-09000d5d81ab9863), [ESPN](https://www.espn.com/nfl/news/story?id=5601262)
- **Bernard Scott** (2012) — torn ACL vs. Miami in early October. [Fox](https://www.foxnews.com/sports/bengals-rb-bernard-scott-out-for-season-with-knee-injury-suspended-lb-dontay-moch-activated), [Bengals.com](https://www.bengals.com/news/scott-back-in-fold-says-knee-responding-bengals-close-in-on-te-smith-9871268)
- **Vick Ballard** (2013) — torn ACL in practice; IR Sept 13. [SI](https://www.si.com/si-wire/2013/09/13/colts-vick-ballard-out-for-season-injures-knee)
- **Mike Goodson** (2013) — torn ACL *and* MCL vs. Pittsburgh, Oct 13. [House of Sparky](https://www.houseofsparky.com/nfl/2013/10/14/4837338/mike-goodson-injury-torn-acl-mcl-jets)
- **Isaiah Pead** (2014) — torn ACL in the preseason vs. Green Bay. [SI](https://www.si.com/nfl/2014/08/17/rams-isaiah-pead-out-season-torn-acl)
- **Stevan Ridley** (2014) — ACL and MCL, Oct 12 vs. Buffalo. [NFL.com](https://www.nfl.com/news/stevan-ridley-tears-acl-mcl-lost-for-patriots-season-0ap3000000410505)
- **Lance Dunbar** (2015) — ACL (and MCL) returning the second-half kickoff at New Orleans, Oct 4. [Dallas Morning News](https://www.dallasnews.com/sports/cowboys/2015/10/05/dallas-cowboys-rb-lance-dunbar-will-have-season-ending-surgery-for-torn-left-acl/), [ESPN](https://www.espn.com/nfl/story/_/id/13817879/lance-dunbar-dallas-cowboys-season-torn-acl)
- **Dion Lewis** (2015) — torn left ACL vs. Washington, Nov 8. [ESPN](https://www.espn.com/nfl/story/_/id/14091073/dion-lewis-new-england-patriots-torn-acl), [Boston.com](https://www.boston.com/sports/new-england-patriots/2015/11/09/patriots-dion-lewis-out-for-season-with-torn-acl)
- **Jay Ajayi** (2018) — torn left ACL while pass protecting vs. Minnesota, Oct 7. [Philadelphia Inquirer](https://www.inquirer.com/philly/sports/eagles/jay-ajayi-philadelphia-eagles-injured-reserve-running-backs-acl-tear-20181008.html), [NFL.com](https://www.nfl.com/news/eagles-rb-jay-ajayi-out-for-season-with-torn-acl-0ap3000000971941)
- **J.K. Dobbins** (2021) — torn ACL in the preseason finale vs. Washington, Aug 28. [CBS](https://www.cbssports.com/nfl/news/ravens-j-k-dobbins-carted-off-with-knee-injury-in-preseason-game-vs-washington)
- **Gus Edwards** (2021) — torn ACL in practice. [CBS](https://www.cbssports.com/nfl/news/ravens-starters-gus-edwards-marcus-peters-out-for-season-after-tearing-acls-in-practice/)
- **Keaton Mitchell** (2023) — full ACL tear, left knee, Week 15 vs. Jacksonville; activated Week 10 of 2024. [NFL.com](https://www.nfl.com/news/ravens-activated-keaton-mitchell-knee-from-injured-reserve-rb-set-to-play-vs-bengals), [ESPN](https://www.espn.com/nfl/story/_/id/42250562/sources-ravens-keaton-mitchell-set-return-active-roster)
- **Jonathon Brooks** (2024) — second ACL tear in the same right knee, Week 14 vs. Philadelphia; missed all of 2025 on PUP. [NFL.com](https://www.nfl.com/news/panthers-rb-jonathon-brooks-suffered-another-torn-acl-loss-eagles-ending-rookie-season), [Forbes](https://www.forbes.com/sites/brucelee/2024/12/10/panthers-rb-jonathon-brooks-suffers-acl-tear-in-right-knee-again/), [SI](https://www.si.com/nfl/panthers-rb-jonathon-brooks-to-miss-entire-2025-nfl-season)
- **Terrell Davis** (1999) — two ligaments in the right knee vs. the Jets, Oct 3. [Baltimore Sun](https://www.baltimoresun.com/news/bs-xpm-1999-10-05-9910050146-story.html), [CBS](https://www.cbsnews.com/news/davis-injury-finally-identified/)
- **Deuce McAllister** — right knee 2005 (IR Oct 10); left knee Sept 24, 2007 vs. Tennessee. [ESPN](https://www.espn.com/nfl/news/story?id=3035134), [CBC](https://www.cbc.ca/sports/football/saints-lose-deuce-mcallister-with-torn-acl-1.638664)
- **Kevin Smith** (2009, and again in 2010) — torn ACL, left knee, Week 14 2009; a second one the following season. [Pride of Detroit](https://www.prideofdetroit.com/2009/12/14/1199639/kevin-smith-likely-has-torn-acl), [NFL.com](https://www.nfl.com/news/lions-rb-smith-done-for-season-because-of-knee-injury-09000d5d814fa0ed)
- **Tim Hightower** (Week 7, 2011) and **Knowshon Moreno** (Week 10, 2011) — both confirmed as ACL tears. [Bleacher Report](https://bleacherreport.com/articles/1264721-fantasy-football-2012-rbs-returning-from-torn-acls-and-where-to-draft-them), [CBS](https://www.cbssports.com/college-football/news/broncos-knowshon-moreno-returns-to-work-eight-months-after-acl-tear)
- **Correll Buckhalter** — torn ACL in a minicamp practice on April 26, 2002. His 2004 and 2005 lost seasons were **patellar tendon**, not ACL, and are excluded. [UPI](https://www.upi.com/Archives/2002/04/26/Buckhalter-suffers-serious-knee-injury/5181019793600/), [Deseret News](https://www.deseret.com/2005/8/25/19908804/injuries-taking-toll-on-eagles/)

Checks that kept players **out** of the cohort:

- **Devonta Freeman** (2018) — groin surgery, not a knee. [NFL.com](https://www.nfl.com/news/falcons-devonta-freeman-to-undergo-groin-surgery-0ap3000000975040)
- **Justice Hill** (2021) — torn Achilles in practice, not an ACL, despite being lost in the same week as Dobbins. [ESPN](https://www.espn.com/nfl/story/_/id/32161482/source-baltimore-ravens-lose-rb-justice-hill-season-ending-injury)
- **Trey Benson** (2025) — arthroscopic meniscus surgery. **Braelon Allen** (2025) — MCL sprain. [Yahoo](https://sports.yahoo.com/articles/trey-benson-injury-cardinals-rb-000428774.html), [Jets](https://www.newyorkjets.com/news/jets-braelon-allen-reflects-after-abrupt-end-to-second-season-01-20-2026)
- **Steven Jackson** (2014) — thigh. **Chris Johnson** (2016) — groin. **Terrance West** (2015) — traded, not hurt. [NBC](https://www.nbcnews.com/news/amp/wbna53019052)
- **Antonio Gibson** (2025) — a genuine ACL tear, on a kickoff return vs. Buffalo, but too recent to have a first year back. [ESPN](https://www.espn.com/nfl/story/_/id/46511646/patriots-lose-rb-antonio-gibson-torn-acl-sources-say)

## Published literature used for comparison

Not inputs to any calculation — context for the return-to-play numbers.

- Manoharan A, Barton D, Khwaja A, Latt LD. *Return to Play Rates in NFL Wide Receivers and Running Backs After ACL Reconstruction: An Updated Analysis.* Orthop J Sports Med, 2021. 2009-10 through 2015-16 seasons; 64.5% of running backs returned, at a mean of 13.6 months after reconstruction. [PubMed](https://pubmed.ncbi.nlm.nih.gov/33553449/) · [journal](https://journals.sagepub.com/doi/10.1177/2325967120974743)
- *NFL Wide Receivers and Running Backs Have Decreased Production Following ACL Reconstruction: An Evaluation of Fantasy Football Performance as an Outcome Measure.* Arthrosc Sports Med Rehabil, 2021. [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S2666061X21001875)
- *Return to Play and Performance After Anterior Cruciate Ligament Reconstruction in National Football League Players.* 2022. [PubMed](https://pubmed.ncbi.nlm.nih.gov/35284583/)

Note the definitional gap: the literature measures **surgery**-to-return, this
study measures **injury**-to-return, and this study requires an actual regular-
season game rather than clearance. That makes the numbers here run a few weeks
long relative to a surgery-anchored figure.

## Sources that were not reachable

Egress from this environment is allowlisted. `prosportstransactions.com` — the
free-text injury/transaction database that the academic papers above use to
identify diagnoses — is blocked here, as are `pro-football-reference.com`,
`espn.com` and `wikipedia.org` for direct fetching. Reporting was therefore
confirmed through web search results rather than by scraping. If this study is
ever rerun somewhere with open egress, scraping Pro Sports Transactions for
`torn ACL` is the way to make the cohort exhaustive rather than hand-built.
