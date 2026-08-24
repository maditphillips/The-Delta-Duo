export type ExplorerRow = {
  id: string;
  n: string; // player name
  s: number; // season
  tm: string; // team
  yr: number; // draft year
  rd: number; // draft round
  pk: number; // draft pick
  dy: "Round 1" | "Day 2" | "Day 3";
  ag: number | null; // draft age
  g: number; // games
  tg: number; // targets
  rec: number;
  ry: number; // receiving yards
  ca: number; // carries
  ruy: number; // rushing yards
  att: number; // pass attempts
  ppr: number;
  rk: number; // positional PPR finish
  ptg: number | null; // prior-season volume (targets/carries/attempts by position)
  ptm: string | null; // prior-season team
  mv: boolean | null; // moved teams vs prior season
  vac: boolean; // team's leading player at position departed this offseason
  role: boolean; // cleared the position's role bar this season
  risk: boolean; // entered season never having cleared the role bar
  ff: boolean; // first career season clearing the role bar
  bestRk: number; // best career positional finish through 2025
};

export type ExplorerPanel = {
  pos: "WR" | "RB" | "QB";
  roleBar: number;
  roleLabel: string;
  volumeKey: "targets" | "carries" | "attempts";
  seasons: [number, number];
  source: string;
  rows: ExplorerRow[];
};

export const volumeOf = (r: ExplorerRow, panel: ExplorerPanel) =>
  panel.volumeKey === "targets" ? r.tg : panel.volumeKey === "carries" ? r.ca : r.att;

export const volumeBands: Record<ExplorerPanel["pos"], { label: string; lo: number; hi: number }[]> = {
  WR: [
    { label: "under 50", lo: 0, hi: 49 },
    { label: "50-79", lo: 50, hi: 79 },
    { label: "80-99 (fringe)", lo: 80, hi: 99 },
    { label: "100-119 (mid)", lo: 100, hi: 119 },
    { label: "120+ (high)", lo: 120, hi: 9999 },
  ],
  RB: [
    { label: "under 50", lo: 0, hi: 49 },
    { label: "50-99", lo: 50, hi: 99 },
    { label: "100-199", lo: 100, hi: 199 },
    { label: "200+", lo: 200, hi: 9999 },
  ],
  QB: [
    { label: "under 100", lo: 0, hi: 99 },
    { label: "100-299", lo: 100, hi: 299 },
    { label: "300-449", lo: 300, hi: 449 },
    { label: "450+", lo: 450, hi: 9999 },
  ],
};

export type Preset = {
  name: string;
  pos: ExplorerPanel["pos"];
  filters: Partial<{
    day: string;
    ageBand: string;
    moved: string;
    vacancy: string;
    atRisk: string;
    priorBand: string;
    outcome: string;
  }>;
};

export const presets: Preset[] = [
  {
    name: "Day 3 WRs, vacancy ahead, stayed put",
    pos: "WR",
    filters: { day: "Day 3", vacancy: "yes", moved: "stayed", atRisk: "yes" },
  },
  {
    name: "Fringe movers (80-99 prior targets)",
    pos: "WR",
    filters: { priorBand: "80-99 (fringe)", moved: "moved" },
  },
  {
    name: "The Nacua cell: early Day 3, age ≤22",
    pos: "WR",
    filters: { day: "Day 3", ageBand: "≤22" },
  },
  {
    name: "Never-fed WRs who moved teams",
    pos: "WR",
    filters: { atRisk: "yes", moved: "moved" },
  },
];
