// The Two Doors of Fantasy Relevance — full dataset from the published article
// (getinsidethelab.com, Aug 2026). Population: 580 WRs drafted 2008–2025;
// headline analyses use the 481 from the 2008–2022 classes, outcomes through
// 2025, PPR. Snap layer 2016–2025. ~220 statistical tests across 13 blocks.

export const wrMeta = {
  title: "The Two Doors of Fantasy Relevance",
  subtitle:
    "What every drafted wide receiver since 2008 reveals about getting on the field — and getting the ball.",
  population:
    "580 wide receivers drafted 2008–2025. Headline analyses use the 481 from the 2008–2022 classes, outcomes through 2025, PPR scoring.",
};

// Act One, Table 1 — what each draft day buys
export const funnel = [
  { day: "Round 1", n: 57, everWr1: 45.6, everStartable: 70.2, medianCareerTargets: 520 },
  { day: "Day 2", n: 145, everWr1: 19.3, everStartable: 37.2, medianCareerTargets: 220 },
  { day: "Day 3", n: 279, everWr1: 3.2, everStartable: 9.3, medianCareerTargets: 29 },
];

export const rampNotCliff = {
  lrtP: 0.16,
  note: "A smooth curve on √pick fits best; round boundaries add nothing (p = 0.16). The decline is continuous, steep, and merciless — the 'cliff' between Day 2 and Day 3 is presentational.",
  day3FloorSplit: { rounds45: 15.7, rounds67: 3.9, p: 0.0008, top12FlatP: 0.74 },
};

// Inside Round 1 — the floor drops, the ceiling does not
export const insideRound1 = {
  floorEarly: 88.9,
  floorLate: 61.5,
  floorVerdict: "significant — top-10 picks are meaningfully more likely to be startable",
  ceilingOR: 0.99,
  ceilingP: 0.79,
  ceilingEarlyRate: 62.5,
  ceilingLateRate: 66.7,
  ceilingVerdict:
    "among the 40 Round 1 WRs who became startable, pick number does not predict who becomes a WR1 at all",
  contrast:
    "At receiver, capital buys safety, not stardom. (At quarterback the same test points the opposite way — a marginal ceiling edge, no floor edge. The positions genuinely differ.)",
};

// Act Two, Table 2 — per-target production at the 150-career-target bar
export const equalityMetrics = [
  { day: "Round 1", n: 47, yardsPerTarget: 8.2, catchPct: 60.1, yacPerRec: 4.16, pprPerTarget: 1.746 },
  { day: "Day 2", n: 86, yardsPerTarget: 7.82, catchPct: 61.5, yacPerRec: 4.21, pprPerTarget: 1.722 },
  { day: "Day 3", n: 58, yardsPerTarget: 7.68, catchPct: 60.6, yacPerRec: 4.28, pprPerTarget: 1.703 },
];

export const equalityHeadline = {
  survivors: "0 of 15 per-target metrics separate Day 2 from Day 3 after Holm correction",
  round1PprPerTarget: 1.746,
  round7PprPerTarget: 1.743,
  volumeShareOfGap: 94,
  medianPpg: { round1: 12.35, day3: 7.49 },
  targetsPerGame: { round1: 6.8, day3: 4.6 },
};

// Zero-usage games — played the whole game, no targets, no catches, no points
export const zeroTargetGames = [
  { day: "Round 1", pct: 1.5 },
  { day: "Day 2", pct: 5.4 },
  { day: "Day 3", pct: 17.1 },
];

// Act Three, Table 3 — the snap gate (2016–2025)
export const snapGate = [
  { share: "under 25%", n: 484, medianTargets: 9, reached80: 0.0 },
  { share: "25-50%", n: 265, medianTargets: 42, reached80: 4.5 },
  { share: "50-70%", n: 197, medianTargets: 65, reached80: 27.9 },
  { share: "70-85%", n: 206, medianTargets: 96, reached80: 78.6 },
  { share: "85%+", n: 184, medianTargets: 132, reached80: 98.4 },
];

export const residual = {
  medianSnapShare: { round1: 71.7, day2: 64.8, day3: 46.7 },
  note: "Even holding field time constant, Day 3 receivers are targeted less at every level of snap share. 97% of the per-snap production gap between Round 1 and Day 3 is being targeted more often while on the field — not doing more with each target.",
};

// The two doors framework
export const twoDoors = [
  {
    door: "Door 1 — Get on the field",
    gate: "The snap gate",
    detail:
      "No receiver under 25% of his team's pass snaps has ever reached 80 targets (0 of 484 seasons). Above 85% of snaps, the 80-target season is nearly automatic (98.4%). You cannot earn the volume that makes you relevant without first being on the field.",
    stat: "0 → 98.4%",
  },
  {
    door: "Door 2 — Get into the read progression",
    gate: "The target gate (80 targets)",
    detail:
      "0 of the 317 drafted receivers who never posted an 80-target season were ever fantasy relevant. All 72 receivers with four or more 80-target seasons were. Draft capital holds both doors open; a late-round receiver must force each one separately.",
    stat: "0 of 317 · 72 of 72",
  },
];

// Table 4 — the ladder: fantasy outcomes by best career depth-chart role
export const ladder = [
  { role: "Alpha (140+ peak targets)", n: 51, everWr1: 84.3, everStartable: 98.0 },
  { role: "Depth-chart WR2 (110-139)", n: 50, everWr1: 38.0, everStartable: 84.0 },
  { role: "Depth-chart WR3 (80-109)", n: 63, everWr1: 1.6, everStartable: 39.7 },
];

export const alphaConversion = {
  round1: 86.4,
  day3: 77.8,
  p: 0.61,
  note: "Tyreek Hill and Antonio Brown were not efficiency miracles — they were Day 3 receivers who got alpha volume, and alpha volume converts to WR1 seasons at the same rate no matter where a player was drafted.",
};

// Act Four — the pre-draft board (~220 tests, draft position controlled)
export const preDraftBoard = [
  { family: "Athletic testing (9 metrics)", survives: false, note: "best sits at adjusted p = 0.10 and points the wrong direction" },
  { family: "College production (6 signals)", survives: false, note: "priced in — career college yards raw OR 1.85 shrinks by half and dies once pick is controlled; dominator rating shrinks 51%" },
  { family: "Level of competition", survives: false, note: "p = 0.60" },
  { family: "Landing spot at draft (5 specs)", survives: false, note: "73% of first feeds happen in year two or later — the depth chart he's drafted into isn't the one he breaks through" },
  { family: "College return usage", survives: false, note: "not significant" },
  { family: "Rookie QB change", survives: false, note: "not significant" },
  { family: "Pick number", survives: true, note: "circumstantial, not a measurement of ability" },
  { family: "Draft age (Day 3 only)", survives: true, note: "p = 0.0012 in the joint model; on Day 2 the effect flips slightly and is n.s." },
];

// Table 5 — Day 3 outcomes by draft age
export const day3Age = [
  { age: "21 or under", n: 29, everStartable: 17.2, reached150: 37.9 },
  { age: "22", n: 116, everStartable: 12.1, reached150: 28.4 },
  { age: "23", n: 107, everStartable: 6.5, reached150: 14.0 },
  { age: "24 or over", n: 22, everStartable: 0.0, reached150: 0.0 },
];

// Table 6 — the sweet-spot cell: Day 3 pick half × draft age
export const day3SweetSpot = [
  { bucket: "Early Day 3, age ≤22", n: 73, realRole: 32.9, everStartable: 20.5, sweetSpot: true },
  { bucket: "Early Day 3, age 23+", n: 68, realRole: 14.7, everStartable: 7.4 },
  { bucket: "Late Day 3, age ≤22", n: 72, realRole: 15.3, everStartable: 5.6 },
  { bucket: "Late Day 3, age 23+", n: 61, realRole: 3.3, everStartable: 3.3 },
];

export const playYourWayIn = {
  efficiencyEarns: "one SD of yards/target buys ~0.44 targets/game the following season",
  volumeStickiness: 0.764,
  unfedYear3: 7.5,
  note: "Roles are sticky. Closing the 2–3 target/game gap requires multiple years of sustained elite efficiency — of the Day 3 receivers still unfed entering year three, 7.5% are ever fed at all.",
};

// Act Five, Table 7 — the timeline (rookie-year rates, 2016-2025 classes)
export const rookieRates = [
  { day: "Round 1", top12: 11.6, top36: 44.2, targets80: 55.8 },
  { day: "Day 2", top12: 2.1, top36: 13.7, targets80: 18.9 },
  { day: "Day 3", top12: 0.5, top36: 1.6, targets80: 3.8 },
];

export const timeline = {
  noHitByYear2: { round1: 21.4, day2: 13.3, day3: 3.2 },
  firstFeedByYear2: 61.5,
  firstFeedByYear3: 78.8,
  day2Window: "Among Day 2 WRs who ever became startable, 37% broke out in year one and 41% in year two — year two is the Day 2 breakout window, and the cheapest buy is after a quiet rookie year.",
};

// Act Six, Table 8 — the acquisition rule
export const acquisitionRule = {
  departed: { n: 168, firstFeedRate: 12.5 },
  noDeparture: { n: 637, firstFeedRate: 4.9 },
  or: 2.79,
  p: 0.0011,
  declineNote: "It is departure, not decline: an aging alpha who merely slows down opens nothing (6.3% vs 6.5%, p = 1.00).",
  compounding: "A vacancy plus draft age ≤22 feeds at 16.1%; no vacancy plus age 23+ feeds at 2.0%.",
  qbRule: {
    kept: 49,
    keptAfterQbLeft: 26,
    or: 0.43,
    p: 0.026,
    note: "Among receivers who already hold a role, a departing QB roughly halves the odds of keeping it — and it's about turnover itself, not the quality of the replacement.",
  },
};

// Table 9 — movers: retention of an 80-target role
export const movers = [
  { band: "Fringe (80-99 targets)", stayed: 58.7, stayedN: 92, moved: 32.4, movedN: 37, p: 0.011 },
  { band: "Mid (100-119)", stayed: 72.8, stayedN: 92, moved: 56.5, movedN: 23, p: 0.137 },
  { band: "High volume (120+)", stayed: 81.9, stayedN: 138, moved: 85.7, movedN: 14, p: 1.0 },
];

export const moversNote =
  "An alpha carries his job with him. A fringe role-holder who moves is re-auditioning, and the re-audition fails two times in three. Never-fed movers get their first feed at 3.8% vs 6.4% for stayers — moving is not the mechanism; the man ahead of you leaving is.";

// Act Seven, Table 10 — the era turn
export const eraTurn = [
  { tier: "Top-12", early: 21.7, late: 21.3, p: 0.859, verdict: "flat — late picks still claim a fifth of elite finishes" },
  { tier: "Top-24", early: 32.5, late: 17.5, p: 0.0088, verdict: "collapsed" },
  { tier: "Top-36", early: 32.2, late: 20.6, p: 0.0048, verdict: "collapsed" },
];

export const eraDetail = {
  day3StartableEarly: 14.9,
  day3StartableLate: 4.4,
  trendP: 0.0101,
  declinePerYear: 17,
  medianPeakTargetsThen: 111,
  medianPeakTargetsNow: 81,
  note: "The roles did not disappear — the league produces the same number of 50+/80+/110+ target jobs as in 2009, and Day 3 receivers still reach 50 career targets at the same rate. What changed is who gets the good jobs. The WR2/WR3 middle class late picks used to occupy has been fenced off, while the true outlier rate has not budged. The cause is unidentified.",
};

// Who to draft — archetypes
export const archetypes = [
  {
    name: "Draft early, with confidence",
    detail:
      "Round 1 rookie receivers, redraft and dynasty both. The floor is real (70% ever startable), the volume arrives immediately (55.8% fed as rookies) — and within Round 1, don't pay a steep premium for the top-10 version: earlier picks buy floor, not ceiling.",
  },
  {
    name: "Draft on a timer",
    detail:
      "Day 2 receivers: a one-in-three career hit rate that spikes in year two. Redraft: late-round flier only. Dynasty: buy low after quiet rookie years, before the year-two window opens.",
  },
  {
    name: "The only late dart worth throwing",
    detail:
      "Early half of Day 3, draft age 22 or younger, ideally with a genuine vacancy at the destination. That cell hits startable at 20.5% — essentially Day 2 odds at a Day 3 price. Every step away from the profile collapses toward 3%.",
  },
  {
    name: "The profile to avoid entirely",
    detail:
      "Day 3, age 23 or older, late picks, full depth charts. The 24-plus cell is 0-for-22 all time in this study. Zero is a small-sample zero, not a law — but you don't have to be the one who tests it.",
  },
];

// 2026 names from the article
export const class2026 = [
  { player: "Carnell Tate", pick: "1.04", team: "TEN", age: 21, note: "Best combination in the class: elite capital, youngest age band, a room cleared and rebuilt around him. A legitimate redraft pick, not a stash." },
  { player: "Jordyn Tyson", pick: "1.08", team: "NO", age: 22, note: "The class's biggest talent reputation and its biggest injury file — the study has no injury variable, so price that risk yourself." },
  { player: "Makai Lemon", pick: "1.20", team: "PHI", age: 22, note: "Real capital, but enters a room with an established alpha (DeVonta Smith). The second read on a good offense can be a fine living." },
  { player: "KC Concepcion", pick: "1.24", team: "CLE", age: 21, note: "Youngest-band receiver in a Cleveland room with no entrenched alpha." },
  { player: "Omar Cooper Jr.", pick: "1.30", team: "NYJ", age: 22, note: "Weakest capital of the five; Garrett Wilson is a clear alpha, and pick 30 is where Round 1's floor advantage starts fading." },
];

export const darts2026 = [
  { player: "Kevin Coleman Jr.", pick: "R5 · 177", team: "MIA", age: 22, mechanism: "Miami vacated 53.0% of its 2025 target share — the largest vacancy in football. The dart aimed at the one signal that triples first-feed odds." },
  { player: "Reggie Virgil", pick: "R5 · 143", team: "ARI", age: 22, mechanism: "Squarely in the early-Day 3 sweet spot at 22 — exactly the 20.5% ticket the study says to buy with your last rookie picks. The counterweight: a modest 20.9% vacancy." },
  { player: "Cyrus Allen", pick: "R5 · 176", team: "KC", age: 23, mechanism: "Doesn't fit the age profile, but a genuine vacancy is opening ahead of him in Kansas City's banged-up receiver room — and vacancy is the one variable that historically moves the needle." },
];

export const wrVerdict =
  "Chase volume over talent every single time, because the players are equal per target while the targets are not equal per player. Pay up for Round 1 rookie capital, buy Day 2 receivers before their second season, spend your last rookie picks only on the sweet-spot cell, and audit every March for vacancies opening ahead of your young receivers and quarterbacks departing from under your established ones.";
