// The Quarterback Cliff — data transcribed from the Delta Duo study outline.
// Population: 212 QBs drafted 2008-2025; headline analyses on the 173 mature
// 2008-2022 picks (45 Round 1, 34 Day 2, 94 Day 3). Outcomes through 2025.

export const qbMeta = {
  title: "The Quarterback Cliff",
  subtitle: "The draft decides who plays. It does not decide who is good.",
  population:
    "212 quarterbacks drafted 2008–2025. Headline analyses run on the 173 mature 2008–2022 picks: 45 Round 1, 34 Day 2, 94 Day 3.",
};

// Act One, Table 1 — outcomes by draft day
export const funnel = [
  { day: "Round 1", n: 45, everStarted: 91.1, everTop24: 75.6, everTop12: 60.0, medianStarts: 74, medianAttempts: 2389, medianStarterSeasons: 4 },
  { day: "Day 2", n: 34, everStarted: 55.9, everTop24: 41.2, everTop12: 20.6, medianStarts: 17, medianAttempts: 576, medianStarterSeasons: 1 },
  { day: "Day 3", n: 94, everStarted: 9.6, everTop24: 7.5, everTop12: 4.3, medianStarts: 1, medianAttempts: 20.5, medianStarterSeasons: 0 },
];

// Chart 2 — hit rate by pick bucket, n = 173
export const pickBuckets = [
  { bucket: "1-5", n: 21, everStarted: 95.2, everTop24: 90.5, everTop12: 76.2 },
  { bucket: "6-10", n: 8, everStarted: 100, everTop24: 62.5, everTop12: 62.5 },
  { bucket: "11-20", n: 9, everStarted: 88.9, everTop24: 66.7, everTop12: 44.4 },
  { bucket: "21-32", n: 7, everStarted: 71.4, everTop24: 57.1, everTop12: 28.6 },
  { bucket: "33-64", n: 15, everStarted: 73.3, everTop24: 53.3, everTop12: 33.3 },
  { bucket: "65-105", n: 25, everStarted: 36.0, everTop24: 28.0, everTop12: 12.0 },
  { bucket: "106-150", n: 19, everStarted: 21.1, everTop24: 15.8, everTop12: 5.3 },
  { bucket: "151-200", n: 35, everStarted: 5.7, everTop24: 5.7, everTop12: 2.9 },
  { bucket: "201+", n: 34, everStarted: 5.9, everTop24: 2.9, everTop12: 2.9 },
];

export const roundByRound = [
  { round: 1, n: 45, everStarted: 91.1, everTop24: 75.6, everTop12: 60.0, medianCareerStarts: 74 },
  { round: 2, n: 15, everStarted: 73.3, everTop24: 53.3, everTop12: 33.3, medianCareerStarts: 32 },
  { round: 3, n: 19, everStarted: 42.1, everTop24: 31.6, everTop12: 10.5, medianCareerStarts: 11 },
  { round: 4, n: 21, everStarted: 14.3, everTop24: 14.3, everTop12: 9.5, medianCareerStarts: 2 },
  { round: 5, n: 21, everStarted: 9.5, everTop24: 4.8, everTop12: 0.0, medianCareerStarts: 2 },
  { round: 6, n: 27, everStarted: 7.4, everTop24: 7.4, everTop12: 3.7, medianCareerStarts: 1 },
  { round: 7, n: 25, everStarted: 8.0, everTop24: 4.0, everTop12: 4.0, medianCareerStarts: 0 },
];

// 1.6 — the two absolutes
export const absolutes = {
  neverTenStarts: { n: 104, everTop24: 0, everTop12: 0 },
  fourPlusStarterSeasons: { n: 33, everTop24: 33, everTop12: 29 },
};

// 1.6c — the ladder (peak season starts)
export const ladder = [
  { peakStarts: "0-7", n: 102, everTop24: 0, everTop12: 0 },
  { peakStarts: "8-11", n: 10, everTop24: 20.0, everTop12: 10.0 },
  { peakStarts: "12-14", n: 14, everTop24: 50.0, everTop12: 0.0 },
  { peakStarts: "15-17", n: 47, everTop24: 97.9, everTop12: 78.7 },
];

// The mediation test — the single most important number in the study
export const mediation = {
  rawCoef: -0.45,
  rawP: 0.0065,
  controlledCoef: 0.012,
  controlledP: 0.961,
  shrinkage: 103,
  starterSeasonsCoef: 1.071,
  starterSeasonsP: 0.0004,
};

// Act Two — the equality test, 16+ career start bar
export const equalityMetrics = [
  { metric: "EPA per dropback", round1: "0.0294", day3: "−0.0181", p: 0.356 },
  { metric: "ANY/A", round1: "6.89", day3: "6.52", p: 0.45 },
  { metric: "Completion %", round1: "62.8%", day3: "62.7%", p: 0.877 },
  { metric: "Fantasy pts per dropback", round1: "0.426", day3: "0.389", p: 0.528 },
  { metric: "Interception rate", round1: "2.30%", day3: "2.43%", p: 0.861 },
  { metric: "Dropbacks per game", round1: "36.6", day3: "37.7", p: 0.78 },
];

export const equalityHeadline = {
  round1FpPerGame: 15.7,
  day3FpPerGame: 15.6,
  gap: 0.028,
  survivorsSummary: "0 of 48 comparisons separate Round 1 from Day 3 at the 16-start bar. 0 of 48 at the 400-dropback bar.",
};

// 2.5 — per starter-season rates
export const perSeasonRates = [
  { day: "Round 1", starterSeasons: 222, top12Rate: 43.2, top24Rate: 82.9, medianFpg: 16.5 },
  { day: "Day 2", starterSeasons: 72, top12Rate: 29.2, top24Rate: 77.8, medianFpg: 15.5 },
  { day: "Day 3", starterSeasons: 30, top12Rate: 50.0, top24Rate: 86.7, medianFpg: 17.5 },
];

// Act Three — rushing, the multiplier
export const rushing2x2 = [
  { quadrant: "Efficient + runs", n: 121, top12Rate: 76.0, top24Rate: 99.2, medianFpg: 19.3 },
  { quadrant: "Efficient + no legs", n: 131, top12Rate: 66.4, top24Rate: 97.0, medianFpg: 17.5 },
  { quadrant: "Inefficient + runs", n: 131, top12Rate: 19.8, top24Rate: 75.6, medianFpg: 15.0 },
  { quadrant: "Inefficient + no legs", n: 121, top12Rate: 9.1, top24Rate: 67.8, medianFpg: 13.2 },
];

// 3.2 — rushing gradient (U-shaped, the dead zone)
export const rushGradient = [
  { band: "0-5", n: 133, top12Rate: 42.1, medianAtt: 35.1, medianEpa: 0.094 },
  { band: "5-10", n: 110, top12Rate: 35.4, medianAtt: 34.2, medianEpa: 0.057 },
  { band: "10-15", n: 67, top12Rate: 29.8, medianAtt: 33.3, medianEpa: 0.044, deadZone: true },
  { band: "15-20", n: 60, top12Rate: 38.3, medianAtt: 32.8, medianEpa: 0.055 },
  { band: "20-30", n: 71, top12Rate: 52.1, medianAtt: 33.1, medianEpa: 0.059 },
  { band: "30-45", n: 38, top12Rate: 57.9, medianAtt: 31.0, medianEpa: 0.074 },
  { band: "45+", n: 25, top12Rate: 76.0, medianAtt: 28.8, medianEpa: 0.124 },
];

export const attemptsMirror = [
  { band: "<25", n: 13, top12Rate: 15.4 },
  { band: "25-30", n: 86, top12Rate: 31.4 },
  { band: "30-33", n: 130, top12Rate: 30.8 },
  { band: "33-36", n: 147, top12Rate: 48.3 },
  { band: "36-40", n: 101, top12Rate: 57.4 },
  { band: "40+", n: 27, top12Rate: 66.7 },
];

// 3.3 — year-over-year stickiness (Spearman), 338 pairs, 77 QBs
export const stickiness = [
  { input: "Rushing yards/game", r: 0.864, kind: "rushing" },
  { input: "Scramble yards/game", r: 0.812, kind: "rushing" },
  { input: "Designed run yards/game", r: 0.742, kind: "rushing" },
  { input: "Completion %", r: 0.554, kind: "passing" },
  { input: "Attempts/game", r: 0.533, kind: "volume" },
  { input: "Fantasy points/game", r: 0.505, kind: "outcome" },
  { input: "CPOE", r: 0.495, kind: "passing" },
  { input: "Rushing touchdowns", r: 0.462, kind: "rushing" },
  { input: "EPA per dropback", r: 0.413, kind: "passing" },
  { input: "Yards per attempt", r: 0.366, kind: "passing" },
  { input: "ANY/A", r: 0.347, kind: "passing" },
];

// 3.4 — what buys a top finish (odds ratio per SD, n = 504)
export const oddsRatios = [
  { input: "EPA per dropback", top12: 10.13, top24: 7.72, fpgPerSd: 2.56 },
  { input: "Passing attempts/game", top12: 3.09, top24: 1.98, fpgPerSd: 1.35 },
  { input: "Rushing yards/game", top12: 3.05, top24: 2.0, fpgPerSd: 1.95 },
];

// 3.5 — rushing terciles: floor and ceiling
export const rushTerciles = [
  { tercile: "Bottom", n: 168, medianFpg: 15.5, p10: 11.3, p90: 19.5, top12Rate: 39.9 },
  { tercile: "Middle", n: 168, medianFpg: 15.5, p10: 11.5, p90: 19.1, top12Rate: 32.7 },
  { tercile: "Top", n: 168, medianFpg: 17.9, p10: 12.8, p90: 23.1, top12Rate: 56.0 },
];

// 3.6 — age decay
export const ageDecay = [
  { age: "<24", n: 91, medianRushYds: 17.9, top12Rate: 35.2 },
  { age: "24-26", n: 86, medianRushYds: 17.2, top12Rate: 41.9 },
  { age: "26-28", n: 52, medianRushYds: 16.3, top12Rate: 50.0 },
  { age: "28-30", n: 42, medianRushYds: 11.9, top12Rate: 47.6 },
  { age: "30-32", n: 21, medianRushYds: 8.1, top12Rate: 33.3 },
  { age: "32+", n: 32, medianRushYds: 8.0, top12Rate: 34.4 },
];

// 3.9 — the era shift: quadrant composition of top-12 seasons
export const eraShift = [
  { quadrant: "Efficient + no legs", early: 54.6, late: 25.9 },
  { quadrant: "Efficient + runs", early: 31.5, late: 53.7 },
  { quadrant: "Inefficient + runs", early: 9.3, late: 14.8 },
  { quadrant: "Inefficient + no legs", early: 4.6, late: 5.6 },
];

// Act Four — the pre-draft board
export const preDraftBoard = [
  { family: "Athletic testing", tested: 7, survivors: 0 },
  { family: "College passing production", tested: 10, survivors: 0 },
  { family: "College rushing production", tested: 4, survivors: 4 },
  { family: "Draft age", tested: 1, survivors: 0 },
  { family: "Landing spot at draft", tested: 3, survivors: 0 },
  { family: "Level of competition", tested: 1, survivors: 0 },
];

// 4.2 — the shrinkage runs backwards
export const shrinkage = [
  { signal: "College rush yds/game → ever started", rawOR: 2.34, controlledOR: 2.67, shrinkage: -16 },
  { signal: "College rush yds/game → ever top-24", rawOR: 2.38, controlledOR: 2.72, shrinkage: -15 },
  { signal: "College rush att/game → ever top-12", rawOR: 1.89, controlledOR: 2.75, shrinkage: -59 },
  { signal: "Career college rush yds/game → ever top-24", rawOR: 2.32, controlledOR: 2.43, shrinkage: -6 },
  { signal: "Designed rush share → ever top-24", rawOR: 1.7, controlledOR: 2.13, shrinkage: -43 },
];

export const deadSignals = [
  { signal: "Draft age (ever started)", rawOR: 0.388, controlledP: 0.32, shrinkage: 77 },
  { signal: "Broad jump (ever started)", rawOR: 2.8, controlledP: 0.2, shrinkage: 30 },
  { signal: "Forty (ever top-24)", rawOR: 0.54, controlledP: 0.2, shrinkage: 34 },
  { signal: "Completion % (ever top-24)", rawOR: 2.21, controlledP: 0.61, shrinkage: 48 },
];

export const causalChain = [
  { step: 1, claim: "College rushing predicts NFL rushing", stat: "ρ = 0.831" },
  { step: 2, claim: "NFL rushing is the most projectable input at the position", stat: "r = 0.864 vs 0.413 for efficiency" },
  { step: 3, claim: "Rushing multiplies top-12 odds", stat: "OR 3.05 per SD" },
  { step: 4, claim: "Draft capital does not price it — controlling for pick strengthens it", stat: "ρ = 0.009, p = 0.875" },
];

// 4.5 — Day 3 outcomes by draft age
export const day3Age = [
  { age: "22 or under", n: 16, everStarted: 31.3, everTop24: 25.0, note: "combined 21-and-under (n=2) and 22 (n=14); roughly 30% hit" },
  { age: "23", n: 53, everStarted: 5.7, everTop24: 3.8 },
  { age: "24 or over", n: 22, everStarted: 4.5, everTop24: 4.5 },
];

// Act Five — the leash
export const leash = [
  { day: "Round 1", n: 73, startedAgain: 60.3, medianEpa: -0.06 },
  { day: "Day 2", n: 31, startedAgain: 38.7, medianEpa: -0.075 },
  { day: "Day 3", n: 12, startedAgain: 25.0, medianEpa: -0.118 },
];

export const leashGradient = [
  { tercile: "Bottom EPA", round1: 60.3, day2: 38.7, day3: 25.0 },
  { tercile: "Middle EPA", round1: 77.0, day2: 77.8, day3: 54.5 },
  { tercile: "Top EPA", round1: 86.1, day2: 83.3, day3: 75.0 },
];

// 5.2 — the give-up curve
export const giveUpCurve = [
  { throughYear: 2, round1: 28.6, round1N: 14, day2: 10.0, day2N: 20, day3: 3.4, day3N: 87 },
  { throughYear: 3, round1: 20.0, round1N: 10, day2: 5.9, day2N: 17, day3: 3.5, day3N: 85 },
  { throughYear: 4, round1: 11.1, round1N: 9, day2: 5.9, day2N: 17, day3: 2.6, day3N: 76 },
];

// 5.6 — dynasty asset life
export const assetLife = [
  { age: "<24", n: 45, meanRemaining: 4.49 },
  { age: "24-26", n: 50, meanRemaining: 4.06 },
  { age: "26-28", n: 34, meanRemaining: 4.41 },
  { age: "28-30", n: 35, meanRemaining: 2.86 },
  { age: "30-32", n: 20, meanRemaining: 3.0 },
  { age: "32+", n: 32, meanRemaining: 1.41 },
];

// Act Six — how QB jobs change hands
export const handcuff = {
  opportunities: 471,
  overallRate: 7.6,
  byCapital: [
    { capital: "Round 1", n: 49, gotJob: 18.4 },
    { capital: "Day 2", n: 48, gotJob: 18.8 },
    { capital: "Day 3", n: 140, gotJob: 4.3 },
    { capital: "Undrafted / pre-2008", n: 234, gotJob: 5.1 },
  ],
};

export const jobSources = [
  { source: "Acquired veteran", n: 89, share: 44.1 },
  { source: "Internal promotion", n: 57, share: 28.2 },
  { source: "Rookie", n: 56, share: 27.7 },
];

export const roleTravel = [
  { prior: "Full season (16+ starts)", stayed: 87.2, stayedN: 203, moved: 86.7, movedN: 15, p: 1.0 },
  { prior: "Most of a season (10-15)", stayed: 74.6, stayedN: 169, moved: 46.8, movedN: 47, p: 0.0006 },
  { prior: "Partial (under 10)", stayed: 30.5, stayedN: 154, moved: 21.3, movedN: 108, p: 0.119 },
];

// Act Seven — the era turn
export const passingEnvironment = [
  { metric: "Attempts per game", y2008: 31.6, y2025: 31.7, rho: -0.274, p: 0.271 },
  { metric: "Interception rate", y2008: 2.55, y2025: 2.11, rho: -0.816, p: 0.00004 },
  { metric: "ANY/A", y2008: 6.72, y2025: 7.21, rho: 0.666, p: 0.0033 },
  { metric: "Rushing yards per game", y2008: 8.96, y2025: 17.7, rho: 0.951, p: 0.00001 },
];

export const starterSupply = [
  { era: "2008-2016", round1: 58.5, day2: 19.8, day3: 15.3, undrafted: 6.5 },
  { era: "2017-2025", round1: 67.2, day2: 19.1, day3: 12.1, undrafted: 1.6 },
];

// The 2026 class, with their pick-bucket base rates
export const class2026 = [
  { player: "Fernando Mendoza", round: 1, pick: 1, team: "LV", college: "Indiana", bucket: "1-5", everStarted: 95.2, everTop12: 76.2 },
  { player: "Ty Simpson", round: 1, pick: 13, team: "LAR", college: "Alabama", bucket: "11-20", everStarted: 88.9, everTop12: 44.4 },
  { player: "Carson Beck", round: 3, pick: 65, team: "ARI", college: "Miami (FL)", bucket: "65-105", everStarted: 36.0, everTop12: 12.0 },
  { player: "Drew Allar", round: 3, pick: 76, team: "PIT", college: "Penn State", bucket: "65-105", everStarted: 36.0, everTop12: 12.0 },
  { player: "Cade Klubnik", round: 4, pick: 110, team: "NYJ", college: "Clemson", bucket: "106-150", everStarted: 21.1, everTop12: 5.3 },
  { player: "Cole Payton", round: 5, pick: 178, team: "PHI", college: "North Dakota State", bucket: "151-200", everStarted: 5.7, everTop12: 2.9 },
  { player: "Taylen Green", round: 6, pick: 182, team: "CLE", college: "Arkansas", bucket: "151-200", everStarted: 5.7, everTop12: 2.9 },
  { player: "Athan Kaliakmanis", round: 7, pick: 223, team: "WAS", college: "Rutgers", bucket: "201+", everStarted: 5.9, everTop12: 2.9 },
  { player: "Behren Morton", round: 7, pick: 234, team: "NE", college: "Texas Tech", bucket: "201+", everStarted: 5.9, everTop12: 2.9 },
  { player: "Garrett Nussmeier", round: 7, pick: 249, team: "KC", college: "LSU", bucket: "201+", everStarted: 5.9, everTop12: 2.9 },
];

export const qbRules = [
  {
    rule: "Buy the legs before the arm arrives",
    detail:
      "Rushing peaks youngest (17.9 yds/game under 24) but top-12 rates peak at 26–28 (50.0%). The legs show up first; the efficiency shows up later — buy the young runner while the market prices him cheaply. Corollary: a 30+ QB whose value is built on rushing is a sell.",
  },
  {
    rule: "Pay for rushing yards, fade rushing touchdowns",
    detail:
      "Stickiness gap, yards minus TDs: +0.403 (CI +0.283 to +0.525). Among top-12 seasons, ~20.8 fantasy points come from rushing yardage and 12.0 from rushing scores. The yardage repeats; the scores do not.",
  },
  {
    rule: "The dead zone is real",
    detail:
      "The 10–15 rushing yds/game band posts the worst top-12 rate in the study (29.8%) — worse than QBs who do not run at all (42.1%). Do not pay a mobility premium for a QB who is only a little mobile.",
  },
];

export const superflexVerdict =
  "A 12-team Superflex league starts 24 QBs every week. The league produces 26–31 QBs a year who hold a job for ten games, and only 10–18 who make it through a full season. First-round QB capital is the only asset class at the position with a defensible floor, and its dominance is increasing (Round 1 share of starter-seasons rising, ρ = 0.588, p = 0.0103). The QB1-to-QB2 gap has not grown — but rushing now supplies 19–45% of it, versus 2–5% in 2008-2010.";
