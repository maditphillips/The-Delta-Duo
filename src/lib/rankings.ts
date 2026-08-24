export const SCOPES = ["overall", "qb", "rb", "wr"] as const;
export type Scope = (typeof SCOPES)[number];

export const scopeLabels: Record<Scope, string> = {
  overall: "All Players",
  qb: "Quarterbacks",
  rb: "Running Backs",
  wr: "Wide Receivers",
};

export type RankingRow = {
  rank: number;
  player: string;
  team?: string | null;
  position?: string | null;
  note?: string | null;
};

export type RankingSet = {
  id: string;
  scope: Scope;
  filename: string | null;
  created_at: string;
  rows: RankingRow[];
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
    const rankStr = pick(rec, ["rank", "rk", "#", "overall", "ovr"]);
    const rank = rankStr ? parseInt(rankStr, 10) : rows.length + 1;
    rows.push({
      rank: Number.isFinite(rank) ? rank : rows.length + 1,
      player,
      team: pick(rec, ["team", "tm", "nfl team"]) ?? null,
      position: pick(rec, ["position", "pos"]) ?? null,
      note: pick(rec, ["note", "notes", "comment", "comments", "blurb"]) ?? null,
    });
  }
  rows.sort((a, b) => a.rank - b.rank);
  return rows;
}
