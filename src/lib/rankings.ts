export const FORMATS = ["ppr", "halfppr", "superflex"] as const;
export type Format = (typeof FORMATS)[number];

export const formatLabels: Record<Format, string> = {
  ppr: "PPR",
  halfppr: "Half PPR",
  superflex: "Superflex",
};

export const formatSublabels: Record<Format, string> = {
  ppr: "1QB · full point per reception",
  halfppr: "1QB · half point per reception",
  superflex: "2QB/Superflex · full PPR",
};

export const POSITION_FILTERS = ["All", "QB", "RB", "WR", "TE"] as const;
export type PositionFilter = (typeof POSITION_FILTERS)[number];

export type RankingRow = {
  rank: number;
  player: string;
  pos?: string | null;
  posRank?: string | null;
  team?: string | null;
  bye?: number | null;
  tier?: string | null;
  note?: string | null;
  flag?: string | null;
};

export type RankingSet = {
  format: Format;
  label?: string;
  updated?: string; // baked build date or upload timestamp
  filename?: string | null;
  rows: RankingRow[];
};

export const tierColors: Record<string, string> = {
  Elite: "var(--chalk-gold)",
  "Tier 1": "var(--chalk-pink)",
  "Tier 2": "var(--chalk-blue)",
  "Tier 3": "var(--ink)",
  "Tier 4": "var(--ink-dim)",
  "Tier 5": "var(--ink-dim)",
  "Tier 6": "var(--ink-dim)",
  "Tier 7": "var(--ink-faint)",
  "Tier 8": "var(--ink-faint)",
  Flex: "var(--ink-dim)",
  Streamer: "var(--ink-dim)",
  Depth: "var(--ink-faint)",
};

export const flagColors: Record<string, string> = {
  Target: "var(--chalk-green)",
  Riser: "var(--chalk-blue)",
  Faller: "var(--chalk-pink)",
  Avoid: "var(--chalk-pink)",
  Injury: "var(--chalk-gold)",
};

// Map loosely-named CSV headers onto our schema. Row order is the fallback rank.
export function normalizeCsvRows(records: Record<string, unknown>[]): RankingRow[] {
  const pick = (rec: Record<string, unknown>, keys: string[]) => {
    for (const k of Object.keys(rec)) {
      if (keys.includes(k.trim().toLowerCase())) {
        const v = rec[k];
        if (v != null && `${v}`.trim() !== "") return `${v}`.trim();
      }
    }
    return undefined;
  };

  const rows: RankingRow[] = [];
  for (const rec of records) {
    const player = pick(rec, ["player", "name", "player name", "player_name"]);
    if (!player) continue;
    const rankStr = pick(rec, ["overall_rank", "rank", "rk", "#", "overall", "ovr"]);
    const rank = rankStr ? parseInt(rankStr, 10) : rows.length + 1;
    const byeStr = pick(rec, ["bye", "bye week", "bye_week"]);
    rows.push({
      rank: Number.isFinite(rank) ? rank : rows.length + 1,
      player,
      pos: pick(rec, ["pos", "position"]) ?? null,
      posRank: pick(rec, ["pos_rank", "positional rank", "posrank"]) ?? null,
      team: pick(rec, ["team", "tm", "nfl team"]) ?? null,
      bye: byeStr ? parseInt(byeStr, 10) : null,
      tier: pick(rec, ["tier"]) ?? null,
      note: pick(rec, ["delta_note", "note", "notes", "comment", "comments", "blurb"]) ?? null,
      flag: pick(rec, ["flag"]) ?? null,
    });
  }
  rows.sort((a, b) => a.rank - b.rank);
  return rows;
}
