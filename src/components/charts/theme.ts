// The Delta Duo chart theme — matches the published article's chart language.
// Series palette validated against the board surface (#466553): all >= 3:1
// contrast; the pink/blue CVD warning band is covered by direct labels,
// legends, and bar gaps on every chart.

export const CHALK = {
  ink: "#f2eee2",
  inkDim: "rgba(242,238,226,0.72)",
  inkFaint: "rgba(242,238,226,0.42)",
  inkGhost: "rgba(242,238,226,0.16)",
  gold: "#e9c464",
  pink: "#f4a3be",
  blue: "#7cc4ea",
  white: "#f2eee2",
  green: "#8fd98a",
  // legacy aliases (older components) — same brand values
  yellow: "#e9c464",
  salmon: "#f4a3be",
  violet: "#f2eee2",
};

// fixed categorical order — assign by entity, never cycle.
// Tier triples follow the article's waffle: gold → pink → white.
export const SERIES = [CHALK.gold, CHALK.pink, CHALK.white, CHALK.blue];

export const axisTick = { fill: CHALK.inkDim, fontSize: 12.5, fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif" };
export const axisLine = { stroke: CHALK.inkFaint };
export const gridProps = { stroke: CHALK.inkGhost, strokeDasharray: "4 6", vertical: false as const };
