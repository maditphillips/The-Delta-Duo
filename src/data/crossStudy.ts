// The running list of cross-study callbacks — the connective tissue of the series.

export const anchorClaim =
  "Three positions, three studies, roughly 1,350 drafted players — and per-opportunity quality is flat across draft capital at all three. The draft decides who plays. It does not decide who is good.";

export const crossStudy: { finding: string; rb: string; wr: string; qb: string }[] = [
  { finding: "Magic round exists?", rb: "No", wr: "No (p = 0.16)", qb: "No (p = 0.59–0.87)" },
  { finding: "Per-opportunity quality flat across draft days?", rb: "Yes (0 of 9 sig.)", wr: "Yes (0 of 15 sig.)", qb: "Yes (0 of 16 sig. at primary bar)" },
  { finding: "Wider outcome spread on Day 3?", rb: "Yes (p = 0.02–0.05)", wr: "not tested", qb: "No (all Holm p = 1.00)" },
  { finding: "Elite conversion once volume is earned", rb: "n/a", wr: "Same by round (p = 0.61)", qb: "Same by round (CI straddles zero)" },
  { finding: "Early-1st buys floor or ceiling?", rb: "n/a", wr: "Floor (ceiling OR 0.99, p = 0.79)", qb: "Marginal ceiling only" },
  { finding: "“Ever” outcomes explained by duration?", rb: "not tested", wr: "not tested", qb: "Yes — 103% shrinkage on log(pick)" },
  { finding: "Early Day 3 sweet spot?", rb: "Slight floor edge", wr: "Yes (15.7% vs 3.9%)", qb: "No (11.9% vs 7.7%, n.s.)" },
  { finding: "Hard prerequisite gate", rb: "50 carries", wr: "80 targets", qb: "10 starts (0 of 104)" },
  { finding: "Late-round elite share, era trend", rb: "n/a", wr: "Flat (21.7% → 21.3%)", qb: "Flat (14.8% → 14.8%)" },
  { finding: "Middle class, era trend", rb: "n/a", wr: "Collapsed (top-24 32.5% → 17.5%)", qb: "Day 2 marginal (p = 0.058); undrafted eliminated" },
  { finding: "Vacancy fills from inside?", rb: "n/a", wr: "Yes (OR 2.79, 12.5% first-feed)", qb: "No — 7.6%, and 4.3% for Day 3 backups" },
  { finding: "Does the role travel on a move?", rb: "n/a", wr: "Alpha yes, fringe no (58.7% → 32.4%)", qb: "Full-season yes (87% → 87%), part-season no (74.6% → 46.8%)" },
  { finding: "Pre-draft signal that survives", rb: "College receiving", wr: "Draft age (Day 3 only)", qb: "College rushing — STRENGTHENS under control" },
  { finding: "College-to-NFL skill transfer", rb: "r = 0.27 (receiving)", wr: "r = 0.27 (receiving)", qb: "ρ = 0.83 (rushing)" },
];
