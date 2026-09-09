import type { WeeklyBoard, WeeklyRow } from "@/lib/weekly";

/** The four questions a start/sit decision is actually asking. `stat` names the
 *  number on the player card the answer is read off, so the card can outline it. */
export type Need = "call" | "ceiling" | "reliable" | "floor";

export const NEEDS: {
  key: Need;
  tag: string;
  label: string;
  stat: "points" | "ceiling" | "pTop12" | "floor";
}[] = [
  { key: "call", tag: "Simple", label: "Just Tell Me Who is Better", stat: "points" },
  { key: "ceiling", tag: "High Ceiling", label: "I Need a HUGE Week From Him", stat: "ceiling" },
  { key: "reliable", tag: "Consistency", label: "Who Has A Top-12 Week More Often", stat: "pTop12" },
  { key: "floor", tag: "Dud Avoider", label: "Who Is Less Likely To Get Zero", stat: "floor" },
];

/** Whose opinion settles it. */
export type Basis = "blend" | "data" | "vibes";

export const BASES: { key: Basis; tag: string; label: string }[] = [
  { key: "blend", tag: "Blended", label: "Combine Wilson and MC's Ranks" },
  { key: "data", tag: "Data", label: "Decide With Wilson's Data" },
  { key: "vibes", tag: "Vibes", label: "Roll with MC's Vibes" },
];

export type Pick = {
  pos: string;
  row: WeeklyRow;
  /** Wilson's projection, straight from the model. */
  wilson: number | null;
  /** MC's rank priced on Wilson's scale, published as projVibes. */
  mc: number | null;
  /** The half-and-half of the two. */
  blend: number | null;
};

/**
 * Price MC's rank in points by borrowing the scale of Wilson's list.
 *
 * MC ranks; he does not project. To average the two voices they have to be in
 * the same units, and the honest conversion is to give his RB9 whatever Wilson's
 * RB9 is worth. It uses MC's order and Wilson's scale, which means MC can never
 * produce a number outside the range Wilson already published.
 *
 * The published board carries the same figure as projVibes, computed the same
 * way, so the weekly lists and this tool cannot drift apart. This is the
 * fallback for a board built before that column existed.
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
  const mc = row.projVibes ?? mcPoints(rows, row.rankVibes);
  return {
    pos,
    row,
    wilson,
    mc,
    blend: wilson != null && mc != null ? (wilson + mc) / 2 : (wilson ?? mc),
  };
}

/** The points the chosen voice is judging on. */
export function pointsOn(p: Pick, basis: Basis): number | null {
  return basis === "data" ? p.wilson : basis === "vibes" ? p.mc : p.blend;
}

const num = (v: number | null | undefined) => (v == null ? -Infinity : v);

export type Verdict = {
  need: Need;
  /** Null only when nobody has the number the question needs. */
  winner: Pick | null;
  runnerUp: Pick | null;
  /** One sentence a person can act on. */
  line: string;
};

const pts = (v: number | null | undefined) => (v == null ? "n/a" : v.toFixed(1));
const pct = (v: number | null | undefined) =>
  v == null ? "n/a" : `${Math.round(v * 100)}%`;

/**
 * Answer all four questions, every time.
 *
 * Deliberately no "too close to call" branch. When two players are half a point
 * apart the margin is real information, but on its own it is a shrug, and a
 * shrug is the one thing nobody can act on. The four answers are always
 * computed and always shown; when they split, that split is the decision.
 *
 * Only the first question takes the basis. Ceiling, consistency and the floor
 * are read off a distribution, and MC does not have one: he ranks, he does not
 * model a range of outcomes. Those three are Wilson's numbers under every
 * setting, and the tool says so rather than inventing a spread for MC.
 */
export function verdicts(picks: Pick[], basis: Basis): Verdict[] {
  const metric: Record<Need, (p: Pick) => number> = {
    call: (p) => num(pointsOn(p, basis)),
    ceiling: (p) => num(p.row.ceiling),
    reliable: (p) => num(p.row.pTop12),
    floor: (p) => num(p.row.floor),
  };
  return NEEDS.map(({ key }) => {
    const ranked = [...picks].sort((a, b) => metric[key](b) - metric[key](a));
    const [winner, runnerUp] = ranked;
    if (!winner || metric[key](winner) === -Infinity)
      return { need: key, winner: null, runnerUp: null, line: "Not enough data for this one." };
    const w = winner.row.player, r = runnerUp?.row.player;
    const line = {
      call: () => {
        const gap = num(pointsOn(winner, basis)) - num(pointsOn(runnerUp, basis));
        const how = gap < 0.75 ? "barely" : gap < 2 ? "narrowly" : "clearly";
        return r
          ? `${w} ${how}: ${pts(pointsOn(winner, basis))} projected points to ${pts(pointsOn(runnerUp, basis))}.`
          : `${w}: ${pts(pointsOn(winner, basis))} projected points.`;
      },
      ceiling: () =>
        r
          ? `${w} has the bigger week in him: ${pts(winner.row.ceiling)} projected points at his ceiling to ${pts(runnerUp.row.ceiling)}.`
          : `${w} tops out around ${pts(winner.row.ceiling)} projected points.`,
      reliable: () =>
        r
          ? `${w} clears a startable week more often: ${pct(winner.row.pTop12)} top-12 to ${pct(runnerUp.row.pTop12)}, on a median of ${pts(winner.row.median)} projected points to ${pts(runnerUp.row.median)}.`
          : `${w} hits a top-12 week ${pct(winner.row.pTop12)} of the time.`,
      floor: () =>
        r
          ? `${w} is likelier to save you from a zero: ${pts(winner.row.floor)} projected points at his floor to ${pts(runnerUp.row.floor)}.`
          : `${w} floors out around ${pts(winner.row.floor)} projected points.`,
    }[key]();
    return { need: key, winner, runnerUp: runnerUp ?? null, line };
  });
}

/** Sleeper's CDN, addressed by the id resolved offline at build time. */
export const photoUrl = (id?: string | null) =>
  id ? `https://sleepercdn.com/content/nfl/players/${id}.jpg` : null;

export const initials = (name: string) =>
  name.split(/\s+/).slice(0, 2).map((w) => w[0]).join("").toUpperCase();
