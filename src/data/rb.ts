// Third Down and Down Distribution for NFL Running Backs — data transcribed
// from the Delta Duo findings reference (companion to The Running Back Cliff).
// Population: drafted and undrafted RBs, 2016–2025 regular season. Full PPR
// computed at the play level. 1,001 player-seasons with 100+ snaps.

export const rbMeta = {
  title: "The Running Back Cliff",
  subtitle: "Third down is a low-value down for running backs — uniquely so.",
  population:
    "Drafted and undrafted RBs, 2016–2025. 1,001 player-seasons with 100+ snaps (732 drafted, 269 undrafted). Full PPR, attributed play-by-play to specific downs.",
};

// League play distribution — the denominator for every value index
export const leagueDistribution = [
  { down: "First", plays: 144876, share: 44.15 },
  { down: "Second", plays: 109143, share: 33.26 },
  { down: "Third & short", plays: 13559, share: 4.13 },
  { down: "Third & long", plays: 53856, share: 16.41 },
  { down: "Fourth", plays: 6708, share: 2.04 },
];

// 1.1 — points per snap by down (all RB snaps 2016-2025)
export const pointsPerSnap = [
  { bucket: "Early (1st/2nd)", snaps: 284789, points: 100896, ptsPerSnap: 0.354, touchRate: 43.7, targetRate: 9.1 },
  { bucket: "Third & short", snaps: 15495, points: 5619, ptsPerSnap: 0.363, touchRate: 42.0, targetRate: 5.2 },
  { bucket: "Third & long", snaps: 54227, points: 12748, ptsPerSnap: 0.235, touchRate: 16.2, targetRate: 12.1 },
  { bucket: "Fourth", snaps: 7224, points: 1771, ptsPerSnap: 0.245, touchRate: 22.0, targetRate: 5.6 },
];

// 1.4 — where RB points come from, with value index
export const valueByDown = [
  { down: "Early (1st/2nd)", snapShare: 78.8, pointShare: 83.49, valueIndex: 1.059 },
  { down: "Third", snapShare: 19.26, pointShare: 15.07, valueIndex: 0.783 },
  { down: "Fourth", snapShare: 1.94, pointShare: 1.44, valueIndex: 0.74 },
];

// Section 2 — the gate tables. Fantasy outcome rate by snap-share bucket.
export type GateRow = { share: string; n: number; medianPpg: number; rb3: number; rb2: number; rb1: number };
export const gateTables: Record<string, { label: string; note?: string; rows: GateRow[] }> = {
  thirdAll: {
    label: "All third-down snaps",
    rows: [
      { share: "under 10%", n: 186, medianPpg: 3.73, rb3: 2.7, rb2: 2.2, rb1: 0.0 },
      { share: "10-25%", n: 312, medianPpg: 6.64, rb3: 23.4, rb2: 13.8, rb1: 5.1 },
      { share: "25-50%", n: 289, medianPpg: 9.09, rb3: 47.1, rb2: 28.4, rb1: 11.4 },
      { share: "50-70%", n: 144, medianPpg: 11.7, rb3: 66.0, rb2: 48.6, rb1: 29.2 },
      { share: "70%+", n: 70, medianPpg: 13.1, rb3: 78.6, rb2: 61.4, rb1: 42.9 },
    ],
  },
  thirdLong: {
    label: "Third-and-long snaps",
    note: "The only gate table that reverses at the top — heavy third-and-long usage is not a marker of quality.",
    rows: [
      { share: "under 10%", n: 279, medianPpg: 4.72, rb3: 14.3, rb2: 8.2, rb1: 2.9 },
      { share: "10-25%", n: 240, medianPpg: 6.72, rb3: 25.0, rb2: 17.1, rb1: 7.5 },
      { share: "25-50%", n: 262, medianPpg: 9.07, rb3: 45.8, rb2: 27.5, rb1: 11.5 },
      { share: "50-70%", n: 127, medianPpg: 11.6, rb3: 66.1, rb2: 48.8, rb1: 28.3 },
      { share: "70%+", n: 93, medianPpg: 10.1, rb3: 64.5, rb2: 47.3, rb1: 31.2 },
    ],
  },
  thirdShort: {
    label: "Third-and-short snaps",
    rows: [
      { share: "under 10%", n: 110, medianPpg: 3.99, rb3: 0.0, rb2: 0.0, rb1: 0.0 },
      { share: "10-25%", n: 308, medianPpg: 5.23, rb3: 7.1, rb2: 2.9, rb1: 0.3 },
      { share: "25-50%", n: 362, medianPpg: 8.78, rb3: 41.4, rb2: 21.0, rb1: 7.2 },
      { share: "50-70%", n: 161, medianPpg: 12.8, rb3: 83.2, rb2: 62.1, rb1: 31.1 },
      { share: "70%+", n: 60, medianPpg: 17.2, rb3: 96.7, rb2: 95.0, rb1: 73.3 },
    ],
  },
  early: {
    label: "Early-down snaps",
    note: "Early down separates outcomes more cleanly than third down at every tier.",
    rows: [
      { share: "under 10%", n: 44, medianPpg: 3.15, rb3: 0.0, rb2: 0.0, rb1: 0.0 },
      { share: "10-25%", n: 389, medianPpg: 4.62, rb3: 0.8, rb2: 0.3, rb1: 0.0 },
      { share: "25-50%", n: 349, medianPpg: 9.06, rb3: 43.6, rb2: 16.3, rb1: 3.4 },
      { share: "50-70%", n: 163, medianPpg: 14.1, rb3: 94.5, rb2: 79.1, rb1: 39.3 },
      { share: "70%+", n: 56, medianPpg: 17.9, rb3: 98.2, rb2: 98.2, rb1: 80.4 },
    ],
  },
  fourth: {
    label: "Fourth-down snaps",
    rows: [
      { share: "under 10%", n: 165, medianPpg: 5.41, rb3: 9.1, rb2: 3.0, rb1: 0.6 },
      { share: "10-25%", n: 297, medianPpg: 6.1, rb3: 18.9, rb2: 12.1, rb1: 3.0 },
      { share: "25-50%", n: 354, medianPpg: 8.49, rb3: 43.5, rb2: 25.7, rb1: 11.9 },
      { share: "50-70%", n: 134, medianPpg: 11.6, rb3: 69.4, rb2: 51.5, rb1: 28.4 },
      { share: "70%+", n: 51, medianPpg: 15.5, rb3: 90.2, rb2: 80.4, rb1: 60.8 },
    ],
  },
};

// 4.6 — absolute points per game by tier
export const tierPpg = [
  { tier: "RB1", n: 121, total: 17.71, early: 15.12, third: 2.28, thirdLong: 1.47, thirdShort: 0.74 },
  { tier: "RB2", n: 121, total: 13.09, early: 11.3, third: 1.72, thirdLong: 0.93, thirdShort: 0.57 },
  { tier: "RB3", n: 122, total: 10.07, early: 8.74, third: 1.34, thirdLong: 0.99, thirdShort: 0.28 },
  { tier: "Non-hit", n: 608, total: 5.21, early: 3.88, third: 0.66, thirdLong: 0.43, thirdShort: 0.1 },
];

// 4.7 — where the tier-to-tier gap is created
export const gapCreation = [
  { step: "RB2 → RB1", totalGap: 4.62, fromEarly: 3.82, fromThird: 0.56, pctFromThird: 12.1 },
  { step: "RB3 → RB2", totalGap: 3.02, fromEarly: 2.56, fromThird: 0.38, pctFromThird: 12.6 },
  { step: "Non-hit → RB3", totalGap: 4.86, fromEarly: 4.86, fromThird: 0.68, pctFromThird: 14.0 },
];

// 5.2 — value index by position, the strongest single table in the study
export const valueIndexByPosition = [
  { position: "QB", first: 0.832, second: 0.977, thirdShort: 1.199, thirdLong: 1.372, fourth: 1.609 },
  { position: "WR", first: 0.853, second: 0.969, thirdShort: 0.795, thirdLong: 1.476, fourth: 1.276 },
  { position: "TE", first: 0.888, second: 1.051, thirdShort: 0.944, thirdLong: 1.189, fourth: 1.191 },
  { position: "RB", first: 1.104, second: 1.041, thirdShort: 1.124, thirdLong: 0.642, fourth: 0.717 },
];

// 5.4 — per player-season medians
export const perSeasonByPosition = [
  { position: "QB", seasons: 464, medianPctThird: 27.45, medianPctThirdLong: 22.91, medianPctEarly: 69.16 },
  { position: "RB", seasons: 894, medianPctThird: 13.85, medianPctThirdLong: 8.83, medianPctEarly: 84.35 },
  { position: "TE", seasons: 622, medianPctThird: 22.6, medianPctThirdLong: 18.71, medianPctEarly: 74.68 },
  { position: "WR", seasons: 1366, medianPctThird: 27.36, medianPctThirdLong: 23.82, medianPctEarly: 70.36 },
];

// 6.2 — share of RB points through the air, by down
export const airShare = [
  { down: "First", pctReceiving: 34.11 },
  { down: "Second", pctReceiving: 44.72 },
  { down: "Third short", pctReceiving: 23.35 },
  { down: "Third long", pctReceiving: 78.78 },
  { down: "Fourth", pctReceiving: 42.3 },
];

export const targetValue = {
  carriesCoef: 0.588,
  targetsCoef: 1.57,
  targetWorthInCarries: 2.67,
  adjR2: 0.8312,
};

// 7.2 — absolute snaps per game by tier
export const snapsPerGame = [
  { tier: "RB1", first: 19.91, second: 14.33, thirdShort: 1.72, thirdLong: 5.51, fourth: 0.75, thirdTotal: 7.23, earlyTotal: 34.24 },
  { tier: "RB2", first: 16.28, second: 12.0, thirdShort: 1.41, thirdLong: 4.43, fourth: 0.59, thirdTotal: 5.84, earlyTotal: 28.28 },
  { tier: "RB3", first: 13.53, second: 10.23, thirdShort: 1.29, thirdLong: 4.67, fourth: 0.6, thirdTotal: 5.96, earlyTotal: 23.76 },
  { tier: "Non-hit", first: 8.58, second: 6.27, thirdShort: 0.86, thirdLong: 3.35, fourth: 0.44, thirdTotal: 4.21, earlyTotal: 14.85 },
];

// 7.5 — non-involvement on third-and-long dropbacks
export const uninvolved = [
  { tier: "RB1", dropbacks: 8977, targetRate: 16.13, pctUninvolved: 83.87 },
  { tier: "RB2", dropbacks: 6865, targetRate: 14.67, pctUninvolved: 85.33 },
  { tier: "RB3", dropbacks: 7205, targetRate: 13.96, pctUninvolved: 86.04 },
  { tier: "Non-hit", dropbacks: 20798, targetRate: 13.21, pctUninvolved: 86.79 },
];

// 7.7 — points per involved snap, blocking snaps removed
export const perInvolvedSnap = [
  { tier: "RB1", early: 0.8704, third: 1.1811, ratio: 1.357 },
  { tier: "RB2", early: 0.7727, third: 1.1435, ratio: 1.48 },
  { tier: "RB3", early: 0.7518, third: 0.9946, ratio: 1.323 },
  { tier: "Non-hit", early: 0.7527, third: 1.0374, ratio: 1.378 },
];

// 7.8 — two kinds of third-down back (40+ third-and-long dropbacks, target-rate terciles)
export const thirdDownBackTypes = [
  { role: "Receiving role", n: 152, medianTargetRate: 0.1925, medianPpg: 11.87, rb3: 64.5, rb2: 46.1, rb1: 29.6 },
  { role: "Mixed", n: 151, medianTargetRate: 0.1348, medianPpg: 9.09, rb3: 51.7, rb2: 32.5, rb1: 17.9 },
  { role: "Blocking role", n: 152, medianTargetRate: 0.0882, medianPpg: 9.07, rb3: 49.3, rb2: 30.9, rb1: 13.8 },
];

// 8.2 / 8.3 — the existence proof
export const existenceProof = [
  { threshold: "under 20%", rb1Third: 6.6, rb1Early: 0.0, top24Third: 11.2, top24Early: 0.4 },
  { threshold: "under 30%", rb1Third: 18.2, rb1Early: 0.8, top24Third: 26.4, top24Early: 1.2 },
  { threshold: "under 40%", rb1Third: 28.9, rb1Early: 0.8, top24Third: 40.1, top24Early: 5.4 },
  { threshold: "under 50%", rb1Third: 40.5, rb1Early: 9.9, top24Third: 52.5, top24Early: 24.0 },
];

// 8.4 / 8.5 — hit-rate matrices (early-down share rows × third-down share cols)
export const hitMatrix = {
  cols: ["3rd under 30%", "3rd 30-50%", "3rd 50%+"],
  rows: ["under 35%", "35-50%", "50-65%", "65%+"],
  rb1: [
    [0.0, 1.0, 0.0],
    [1.3, 9.8, 9.8],
    [17.9, 25.6, 46.3],
    [82.4, 58.8, 81.1],
  ],
  top24: [
    [0.7, 2.0, 1.5],
    [24.0, 29.5, 39.0],
    [66.7, 74.4, 79.6],
    [100.0, 94.1, 100.0],
  ],
  counts: [
    [411, 99, 66],
    [75, 61, 41],
    [39, 39, 54],
    [17, 17, 53],
  ],
  medianPpg: [
    [4.96, 6.08, 6.43],
    [8.69, 10.92, 10.5],
    [13.11, 12.72, 14.39],
    [16.55, 15.94, 17.65],
  ],
};

// 8.6 — logistic tests
export const logisticPower = [
  { outcome: "RB1 (top-12)", earlyOddsPer10: 3.857, thirdOddsPer10: 1.243 },
  { outcome: "Top-24 cumulative", earlyOddsPer10: 5.332, thirdOddsPer10: 1.179 },
];

// 8.7 — named RB1 seasons with the lowest third-down share
export const namedRb1Seasons = [
  { season: 2020, player: "Nick Chubb", team: "CLE", earlyShare: 0.467, thirdShare: 0.108, ppg: 17.31 },
  { season: 2023, player: "Derrick Henry", team: "TEN", earlyShare: 0.67, thirdShare: 0.11, ppg: 14.51 },
  { season: 2024, player: "James Cook", team: "BUF", earlyShare: 0.552, thirdShare: 0.126, ppg: 16.67 },
  { season: 2016, player: "LeGarrette Blount", team: "NE", earlyShare: 0.572, thirdShare: 0.131, ppg: 14.56 },
  { season: 2019, player: "Derrick Henry", team: "TEN", earlyShare: 0.729, thirdShare: 0.133, ppg: 19.64 },
  { season: 2016, player: "Frank Gore", team: "IND", earlyShare: 0.717, thirdShare: 0.162, ppg: 13.39 },
  { season: 2018, player: "Kareem Hunt", team: "KC", earlyShare: 0.557, thirdShare: 0.188, ppg: 20.93 },
  { season: 2022, player: "Derrick Henry", team: "TEN", earlyShare: 0.767, thirdShare: 0.189, ppg: 18.92 },
  { season: 2025, player: "James Cook", team: "BUF", earlyShare: 0.692, thirdShare: 0.205, ppg: 17.78 },
  { season: 2022, player: "Nick Chubb", team: "CLE", earlyShare: 0.69, thirdShare: 0.211, ppg: 16.55 },
  { season: 2020, player: "Derrick Henry", team: "TEN", earlyShare: 0.771, thirdShare: 0.211, ppg: 20.82 },
  { season: 2022, player: "Joe Mixon", team: "CIN", earlyShare: 0.653, thirdShare: 0.225, ppg: 17.11 },
  { season: 2025, player: "Travis Etienne", team: "JAX", earlyShare: 0.71, thirdShare: 0.237, ppg: 14.94 },
  { season: 2021, player: "Joe Mixon", team: "CIN", earlyShare: 0.745, thirdShare: 0.242, ppg: 17.99 },
  { season: 2024, player: "Derrick Henry", team: "BAL", earlyShare: 0.657, thirdShare: 0.249, ppg: 19.79 },
  { season: 2019, player: "Mark Ingram", team: "BAL", earlyShare: 0.52, thirdShare: 0.25, ppg: 16.17 },
  { season: 2025, player: "Derrick Henry", team: "BAL", earlyShare: 0.655, thirdShare: 0.269, ppg: 16.44 },
  { season: 2021, player: "Antonio Gibson", team: "WAS", earlyShare: 0.61, thirdShare: 0.277, ppg: 14.32 },
  { season: 2017, player: "Leonard Fournette", team: "JAX", earlyShare: 0.568, thirdShare: 0.278, ppg: 17.71 },
  { season: 2022, player: "Josh Jacobs", team: "LV", earlyShare: 0.877, thirdShare: 0.282, ppg: 19.31 },
  { season: 2023, player: "Joe Mixon", team: "CIN", earlyShare: 0.805, thirdShare: 0.29, ppg: 15.71 },
  { season: 2020, player: "Josh Jacobs", team: "LV", earlyShare: 0.635, thirdShare: 0.299, ppg: 15.42 },
  { season: 2024, player: "James Conner", team: "ARI", earlyShare: 0.629, thirdShare: 0.307, ppg: 15.86 },
  { season: 2021, player: "Josh Jacobs", team: "LV", earlyShare: 0.609, thirdShare: 0.307, ppg: 15.07 },
  { season: 2023, player: "James Cook", team: "BUF", earlyShare: 0.627, thirdShare: 0.307, ppg: 13.69 },
];

// 8.9 — profile buckets, third-to-early snap share ratio
export const profiles = [
  { profile: "Two-down (ratio < 0.60)", n: 320, medianEarlyShare: 0.313, medianPpg: 7.22, rb3: 33.4, top24: 24.1, rb1: 10.0 },
  { profile: "Tilted early (0.60-0.85)", n: 153, medianEarlyShare: 0.348, medianPpg: 8.61, rb3: 44.4, top24: 30.7, rb1: 13.7 },
  { profile: "Balanced (0.85-1.10)", n: 186, medianEarlyShare: 0.465, medianPpg: 11.79, rb3: 62.9, top24: 44.1, rb1: 27.4 },
  { profile: "Third-down tilted (1.10+)", n: 313, medianEarlyShare: 0.203, medianPpg: 6.18, rb3: 23.0, top24: 11.5, rb1: 5.4 },
];

// 9.1 — outcomes by role archetype
export const archetypes = [
  { role: "Three-down", n: 109, pctUndrafted: 5.5, medianPpg: 15.49, rb3: 98.2, rb2: 89.9, rb1: 62.4 },
  { role: "Early-down only", n: 110, pctUndrafted: 17.3, medianPpg: 13.66, rb3: 92.7, rb2: 78.2, rb1: 37.3 },
  { role: "Timeshare", n: 177, pctUndrafted: 17.5, medianPpg: 9.88, rb3: 68.4, rb2: 29.4, rb1: 6.2 },
  { role: "Third-down specialist", n: 66, pctUndrafted: 21.2, medianPpg: 6.43, rb3: 10.6, rb2: 1.5, rb1: 0.0 },
  { role: "Rotational", n: 539, pctUndrafted: 36.9, medianPpg: 5.25, rb3: 5.0, rb2: 0.9, rb1: 0.2 },
];

// 9.2 — promotion the following season
export const promotion = [
  { role: "Early-down only", nPairs: 90, becameThreeDown: 15.6, stayedSame: 40.0 },
  { role: "Timeshare", nPairs: 129, becameThreeDown: 14.7, stayedSame: 24.0 },
  { role: "Rotational", nPairs: 265, becameThreeDown: 4.2, stayedSame: 64.9 },
  { role: "Third-down specialist", nPairs: 42, becameThreeDown: 0.0, stayedSame: 42.9 },
  { role: "Three-down", nPairs: 90, becameThreeDown: 46.7, stayedSame: 46.7 },
];

// 9.3 — true third-down specialists, 2025
export const specialists2025 = [
  { player: "Tyjae Spears", team: "TEN", earlyShare: 0.266, thirdShare: 0.591, ppg: 8.59 },
  { player: "Ty Johnson", team: "BUF", earlyShare: 0.173, thirdShare: 0.717, ppg: 5.9 },
  { player: "Samaje Perine", team: "CIN", earlyShare: 0.223, thirdShare: 0.615, ppg: 5.19 },
  { player: "Jeremy McNichols", team: "WAS", earlyShare: 0.196, thirdShare: 0.706, ppg: 4.54 },
  { player: "Isaiah Davis", team: "NYJ", earlyShare: 0.19, thirdShare: 0.507, ppg: 4.45 },
  { player: "LeQuint Allen Jr.", team: "JAX", earlyShare: 0.099, thirdShare: 0.678, ppg: 1.55 },
];

// Section 10 — publication-ready claims
export const rbClaims = [
  "Third down is a low-value down for running backs, uniquely so. Value index 0.642 on third-and-long — the only position in football below 1.0 — against 1.476 for WRs, 1.372 for QBs, 1.189 for TEs.",
  "Roughly 87% of every tier-to-tier PPG gap is built on first and second down.",
  "A running back is uninvolved on 84–87% of third-and-long dropbacks, elite backs included.",
  "When he IS involved on third down, the touch is worth about 35% more than an early-down touch — because third-down involvements are overwhelmingly targets, and a target is worth 2.67 carries.",
  "On third-and-long, 78.78% of RB points come through the air. Rushing there has a value index of 0.234.",
  "40.5% of RB1 seasons and 52.5% of top-24 seasons came with the back on the field for under half his team's third downs. Only 9.9% and 24.0% did so on early downs.",
  "Early-down deployment is 3 to 4.5 times more powerful per unit of snap share than third-down deployment.",
  "Third-down snap share carries no predictive information beyond overall snap share for next-season PPG (p = 0.918).",
  "Third-down work predicts slightly LESS early-down work the following season (−0.0849, p = 0.0102).",
  "Zero of 66 third-down-specialist seasons finished as an RB1. Zero of 42 became three-down backs the next year.",
  "Two-down workhorses cost about 2 points per game and still hit RB1 more than half the time (51.7%).",
  "Third-down-tilted backs are the worst profile in the study: 5.4% RB1 rate across 313 player-seasons.",
];

export const rbSummaryLine =
  "A running back touches the ball on roughly a quarter of his third-down snaps, versus half on first down. That non-use is what makes third down look worthless. But third-down involvements are almost all targets, and targets pay 2.7 times what carries do — so the rare third-down touch is the most valuable one he gets.";
