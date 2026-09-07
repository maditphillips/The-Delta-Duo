export type WeeklyRow = {
  player: string;
  team?: string | null;
  rankData: number;
  rankVibes: number;
  noteData?: string | null;
  noteVibes?: string | null;
};

export type WeeklyBoard = {
  season: number;
  week: number;
  label: string;
  positions: Record<string, WeeklyRow[]>;
};

export type WeeklyIndex = {
  weeks: { key: string; season: number; week: number; label: string; positions: string[] }[];
};

export const WEEKLY_POSITIONS = ["QB", "RB", "WR", "TE"] as const;

/** Signed delta: positive means the vibes list is HIGHER on him than the data. */
export const deltaOf = (r: WeeklyRow) => r.rankData - r.rankVibes;

export function deltaColor(d: number) {
  if (d >= 4) return "var(--accent-2-lt)"; // vibes much higher
  if (d <= -4) return "var(--accent-3)"; // data much higher
  return "var(--ink-faint)";
}

export function deltaLabel(d: number) {
  if (d === 0) return "agree";
  return d > 0 ? `MC +${d}` : `Wilson +${Math.abs(d)}`;
}
