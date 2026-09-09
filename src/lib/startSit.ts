import type { WeeklyBoard, WeeklyRow } from "@/lib/weekly";

/** The four questions a start/sit decision is actually asking. */
export type Need = "call" | "ceiling" | "reliable" | "floor";

export const NEEDS: { key: Need; label: string; hint: string }[] = [
  { key: "call", label: "Just tell me who's better", hint: "the blended projection" },
  { key: "ceiling", label: "I need a blowup week", hint: "highest ceiling" },
  { key: "reliable", label: "I just need a solid start", hint: "most often startable" },
  { key: "floor", label: "I can't afford a zero", hint: "highest floor" },
];

export type Pick = {
  pos: string;
  row: WeeklyRow;
  /** Wilson's projection, straight from the model. */
  wilson: number | null;
  /** MC's rank priced on Wilson's scale -- see mcPoints. */
  mc: number | null;
  /** The half-and-half of the two, and what "call" ranks on. */
  blend: number | null;
};

/**
 * Price MC's rank in points by borrowing the scale of Wilson's list.
 *
 * MC ranks; he does not project. To average the two voices they have to be in
 * the same units, and the honest conversion is to give his RB9 whatever Wilson's
 * RB9 is worth. It uses MC's order and Wilson's scale, which means MC can never
 * produce a number outside the range Wilson already published -- the blend is a
 * little conservative by construction, and two lists that agree on order while
 * disagreeing on the size of the gap will read as agreeing.
 */
export function mcPoints(rows: WeeklyRow[], rank: number): number | null {
  const scale = rows
    .map((r) => r.proj)
    .filter((p): p is number => p != null)
    .sort((a, b) => b - a);
  if (!scale.length) return null;
  return scale[Math.min(Math.max(rank, 1), scale.length) - 1];
}

/** The rows for one position under the chosen scoring, falling back to the
 *  single list a position without variants ships. */
export function rowsFor(board: WeeklyBoard, pos: string, scoring: string): WeeklyRow[] {
  return board.variants?.[pos]?.[scoring] ?? board.positions[pos] ?? [];
}

export function toPick(pos: string, rows: WeeklyRow[], row: WeeklyRow): Pick {
  const wilson = row.proj ?? null;
  const mc = mcPoints(rows, row.rankVibes);
  return {
    pos,
    row,
    wilson,
    mc,
    blend: wilson != null && mc != null ? (wilson + mc) / 2 : (wilson ?? mc),
  };
}

const num = (v: number | null | undefined) => (v == null ? -Infinity : v);

const METRIC: Record<Need, (p: Pick) => number> = {
  call: (p) => num(p.blend),
  ceiling: (p) => num(p.row.ceiling),
  reliable: (p) => num(p.row.pTop12),
  floor: (p) => num(p.row.floor),
};

export type Verdict = {
  need: Need;
  /** Null only when nobody has the number the question needs. */
  winner: Pick | null;
  runnerUp: Pick | null;
  /** One sentence a person can act on. */
  line: string;
};

const pts = (v: number | null | undefined) => (v == null ? "—" : v.toFixed(1));
const pct = (v: number | null | undefined) =>
  v == null ? "—" : `${Math.round(v * 100)}%`;

/**
 * Answer all four questions, every time.
 *
 * Deliberately no "too close to call" branch. When two players are half a point
 * apart the margin is real information, but on its own it is a shrug -- and a
 * shrug is the one thing nobody can act on. The four answers are always
 * computed and always shown; when they split, that split is the decision.
 */
export function verdicts(picks: Pick[]): Verdict[] {
  return NEEDS.map(({ key }) => {
    const ranked = [...picks].sort((a, b) => METRIC[key](b) - METRIC[key](a));
    const [winner, runnerUp] = ranked;
    if (!winner || METRIC[key](winner) === -Infinity)
      return { need: key, winner: null, runnerUp: null, line: "Not enough data for this one." };
    const w = winner.row.player, r = runnerUp?.row.player;
    const line = {
      call: () => {
        const gap = num(winner.blend) - num(runnerUp?.blend);
        const how = gap < 0.75 ? "barely" : gap < 2 ? "narrowly" : "clearly";
        return r
          ? `${w} ${how} — ${pts(winner.blend)} projected to ${pts(runnerUp.blend)}.`
          : `${w} — ${pts(winner.blend)} projected.`;
      },
      ceiling: () =>
        r
          ? `${w} has the bigger week in him: ${pts(winner.row.ceiling)} at his ceiling to ${pts(runnerUp.row.ceiling)}.`
          : `${w} tops out around ${pts(winner.row.ceiling)}.`,
      reliable: () =>
        r
          ? `${w} clears a startable week more often: ${pct(winner.row.pTop12)} top-12 to ${pct(runnerUp.row.pTop12)}, on a median of ${pts(winner.row.median)} to ${pts(runnerUp.row.median)}.`
          : `${w} hits a top-12 week ${pct(winner.row.pTop12)} of the time.`,
      floor: () =>
        r
          ? `${w} is likelier to save you from a zero: ${pts(winner.row.floor)} at his floor to ${pts(runnerUp.row.floor)}.`
          : `${w} floors out around ${pts(winner.row.floor)}.`,
    }[key]();
    return { need: key, winner, runnerUp: runnerUp ?? null, line };
  });
}

/** Sleeper's CDN, addressed by the id resolved offline at build time. */
export const photoUrl = (id?: string | null) =>
  id ? `https://sleepercdn.com/content/nfl/players/${id}.jpg` : null;

export const initials = (name: string) =>
  name.split(/\s+/).slice(0, 2).map((w) => w[0]).join("").toUpperCase();
