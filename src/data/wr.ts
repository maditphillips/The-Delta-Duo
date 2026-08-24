// The Two Doors of Fantasy Relevance — wide receiver findings.
// NOTE: this module currently carries the WR Cliff numbers as cited in the
// companion QB and RB studies (cross-study callbacks). The full article
// dataset from getinsidethelab.com is pending import — sections that will
// expand once it lands are marked below.

export const wrMeta = {
  title: "The Two Doors of Fantasy Relevance",
  subtitle:
    "What every drafted wide receiver since 2008 reveals about getting on the field — and getting the ball.",
  population: "Every drafted wide receiver since 2008.",
  pendingNote:
    "This tab currently shows the WR findings cited across the Delta Duo series. The full article dataset is queued for import and will expand these sections.",
};

// The two doors framework
export const twoDoors = [
  {
    door: "Door 1 — Getting on the field",
    gate: "The snap gate",
    detail:
      "Playing time is the first filter: no drafted receiver became fantasy-relevant without first clearing a meaningful snap share. The gate closes absolutely — 0 of 317 receivers below it ever hit.",
    stat: "0 of 317",
  },
  {
    door: "Door 2 — Getting the ball",
    gate: "The target gate (80 targets)",
    detail:
      "Volume is the second filter, and it converts at the same rate for everyone: once alpha target volume is earned, it becomes WR1 seasons at the same rate regardless of draft slot (86.4% vs 77.8%, p = 0.61). Every receiver who cleared it hit — 72 of 72.",
    stat: "72 of 72",
  },
];

// Round 1 vs Day 3 — outcomes (cross-study comparison table)
export const roundOutcomes = [
  { day: "Round 1", startable: 70.2, elite: 45.6 },
  { day: "Day 3", startable: 9.3, elite: 3.2 },
];

// Cross-position Round 1 / Day 3 comparison
export const crossPositionR1 = [
  { position: "RB", r1Startable: 93.5, r1Elite: 67.7, day3Startable: 21.4, day3Elite: 6.0, startableDef: "top-36", eliteDef: "top-12" },
  { position: "WR", r1Startable: 70.2, r1Elite: 45.6, day3Startable: 9.3, day3Elite: 3.2, startableDef: "top-36", eliteDef: "top-12" },
  { position: "QB", r1Startable: 75.6, r1Elite: 60.0, day3Startable: 7.5, day3Elite: 4.3, startableDef: "top-24", eliteDef: "top-12" },
];

// Inside Round 1 — capital buys safety, not stardom
export const insideRound1 = {
  floorEarly: 88.9,
  floorLate: 61.5,
  floorVerdict: "significant — moving up inside Round 1 buys a real floor",
  ceilingOR: 0.99,
  ceilingP: 0.79,
  ceilingVerdict: "nothing — early first-rounders hit the elite tier no more often",
  contrast:
    "At receiver, capital buys safety. At quarterback, the same test points the opposite way (a marginal ceiling edge, no floor edge). The positions genuinely differ.",
};

// Inside Day 3 — the sweet spot that QBs don't have
export const day3SweetSpot = {
  rounds45Startable: 15.7,
  rounds67Startable: 3.9,
  p: 0.0008,
  note: "Early Day 3 buys a real floor at receiver — the Nacua-style archetype: early half of Day 3, young, good landing spot. No QB equivalent exists.",
};

// Draft age — the signal that survives on Day 3
export const draftAgeSignal = {
  note: "Draft age is the pre-draft signal that survives at receiver — but only within Day 3, where age is not a proxy for draft slot.",
};

// The movers finding
export const movers = {
  alphaStay: 58.7,
  alphaMove: 32.4,
  note: "An alpha's role travels; a fringe receiver's does not — first-feed rate drops from 58.7% to 32.4% on a move. Damage concentrates entirely at the fringe.",
};

// Vacancy: filled from inside the building
export const vacancy = {
  or: 2.79,
  p: 0.0011,
  firstFeedRate: 12.5,
  note: "A vacancy ahead of a receiver roughly triples his first-feed odds. WR jobs are filled from inside the building — the opposite of quarterback, where the incumbent backup gets the job less than 1 time in 13.",
};

// Era trends
export const eraTrends = [
  { finding: "Late-round elite share", early: 21.7, late: 21.3, verdict: "flat — the lottery ticket pays at the same rate it always did" },
  { finding: "Middle class (top-24 rate)", early: 32.5, late: 17.5, verdict: "collapsed — the WR middle class has been squeezed" },
];

// Value by down (from the RB study's cross-position tables)
export const wrByDown = {
  pointShares: { first: 37.64, second: 32.23, thirdShort: 3.29, thirdLong: 24.23, fourth: 2.61 },
  valueIndex: { first: 0.853, second: 0.969, thirdShort: 0.795, thirdLong: 1.476, fourth: 1.276 },
  medianPctThird: 27.36,
  note: "Third-and-long is the most valuable down in football for a wide receiver — value index 1.476, the highest of any position on any down.",
};

// Shared series findings that include WR
export const wrSeriesFindings = [
  { finding: "Magic round exists?", answer: "No (p = 0.16). Hit rates fall smoothly with pick number — round boundaries add nothing." },
  { finding: "Per-opportunity quality flat across draft days?", answer: "Yes — 0 of 15 metrics separate Round 1 from Day 3 once receivers clear the audition bar." },
  { finding: "Elite conversion once volume is earned", answer: "Same by round (86.4% vs 77.8%, p = 0.61). Alpha volume converts to WR1 seasons at the same rate regardless of draft slot." },
  { finding: "College-to-NFL skill transfer", answer: "r = 0.27 (receiving) — real but modest; the QB rushing transfer (ρ = 0.83) dwarfs it." },
  { finding: "Hard prerequisite gate", answer: "80 targets. 0-of-317 below the snap gate ever hit; 72-of-72 above the target gate did." },
];
