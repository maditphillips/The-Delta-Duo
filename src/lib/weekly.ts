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
  /** Scoring variants, present only where a position ships more than one list
   *  (QB at 4-pt and 6-pt passing TDs; RB/WR/TE in PPR and half-PPR). Keyed by
   *  position, then by the label shown on the button. */
  variants?: Record<string, Record<string, WeeklyRow[]>>;
};

export type WeeklyIndex = {
  weeks: { key: string; season: number; week: number; label: string; positions: string[] }[];
};

export const WEEKLY_POSITIONS = ["QB", "RB", "WR", "TE", "K"] as const;

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
