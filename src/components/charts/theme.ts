// Chalk chart theme — colors validated against the board surface (#2d4a3e)
// for CVD separation, chroma, and >= 3:1 contrast.

export const CHALK = {
  ink: "#f2eee2",
  inkDim: "rgba(242,238,226,0.72)",
  inkFaint: "rgba(242,238,226,0.38)",
  inkGhost: "rgba(242,238,226,0.14)",
  yellow: "#e3bd3a",
  blue: "#5cb0de",
  salmon: "#e88062",
  violet: "#bda5ec",
  green: "#7fd07a",
};

// fixed categorical order — assign by entity, never cycle
export const SERIES = [CHALK.yellow, CHALK.blue, CHALK.salmon, CHALK.violet];

export const axisTick = { fill: CHALK.inkDim, fontSize: 14, fontFamily: "Patrick Hand, cursive" };
export const axisLine = { stroke: CHALK.inkFaint };
export const gridProps = { stroke: CHALK.inkGhost, strokeDasharray: "4 6", vertical: false as const };
