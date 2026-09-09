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

export type Verdict = {
  need: Need;
  /** Null only when nobody has the number the question needs. */
  winner: Pick | null;
  runnerUp: Pick | null;
  /** The two are level on this question once the numbers are rounded to what
   *  the card actually prints. */
  tied: boolean;
  /** One sentence a person can act on. */
  line: string;
};

const pts = (v: number | null | undefined) => (v == null ? "n/a" : v.toFixed(1));
const pct = (v: number | null | undefined) =>
  v == null ? "n/a" : `${Math.round(v * 100)}%`;

/**
 * How each question reads its number and says its answer.
 *
 * Only the first line spells out "projected points". The others sit under a
 * kicker naming the question and beside a card that labels every figure, so
 * repeating it there just pushed the sentence onto a second line, and a
 * headline nobody finishes is worse than a short one.
 */
const SHAPE: Record<
  Need,
  {
    value: (p: Pick, basis: Basis) => number | null;
    fmt: (v: number | null | undefined) => string;
    win: (w: string, a: string, b: string, how: string) => string;
    solo: (w: string, a: string) => string;
    tie: (a: string) => string;
  }
> = {
  call: {
    value: (p, basis) => pointsOn(p, basis),
    fmt: pts,
    win: (w, a, b, how) => `${w} ${how}: ${a} projected points to ${b}.`,
    solo: (w, a) => `${w}: ${a} projected points.`,
    tie: (a) => `Nothing in it: both on ${a} projected points.`,
  },
  ceiling: {
    value: (p) => p.row.ceiling ?? null,
    fmt: pts,
    win: (w, a, b) => `${w} for the big week: ${a} ceiling to ${b}.`,
    solo: (w, a) => `${w} tops out around ${a}.`,
    tie: (a) => `Nothing in it: both top out around ${a}.`,
  },
  reliable: {
    value: (p) => p.row.pTop12 ?? null,
    fmt: pct,
    win: (w, a, b) => `${w} more often: ${a} top-12 to ${b}.`,
    solo: (w, a) => `${w} hits a top-12 week ${a} of the time.`,
    tie: (a) => `Nothing in it: both hit a top-12 week ${a} of the time.`,
  },
  floor: {
    value: (p) => p.row.floor ?? null,
    fmt: pts,
    win: (w, a, b) => `${w} is the safer floor: ${a} to ${b}.`,
    solo: (w, a) => `${w} floors out around ${a}.`,
    tie: (a) => `Nothing in it: both floor at ${a}.`,
  },
};

const num = (v: number | null | undefined) => (v == null ? -Infinity : v);

/**
 * Answer all four questions, every time.
 *
 * Deliberately no "too close to call" branch on a margin. When two players are
 * half a point apart the margin is real information, and a shrug is the one
 * thing nobody can act on. The four answers are always computed and always
 * shown; when they split, that split is the decision.
 *
 * A genuine tie is different and does get its own wording. It is judged on the
 * rounded figures rather than the raw ones, because two backs printing 7.7 and
 * 7.7 on their cards cannot be described as one beating the other, whatever the
 * third decimal place says.
 *
 * Only the first question takes the basis. Ceiling, consistency and the floor
 * are read off a distribution, and MC does not have one: he ranks, he does not
 * model a range of outcomes. Those three are Wilson's numbers under every
 * setting, and the tool says so rather than inventing a spread for MC.
 */
export function verdicts(picks: Pick[], basis: Basis): Verdict[] {
  return NEEDS.map(({ key }) => {
    const shape = SHAPE[key];
    const ranked = [...picks].sort(
      (a, b) => num(shape.value(b, basis)) - num(shape.value(a, basis))
    );
    const [winner, runnerUp] = ranked;
    if (!winner || shape.value(winner, basis) == null)
      return { need: key, winner: null, runnerUp: null, tied: false,
               line: "Not enough data for this one." };

    const a = shape.fmt(shape.value(winner, basis));
    if (!runnerUp) return { need: key, winner, runnerUp: null, tied: false,
                            line: shape.solo(winner.row.player, a) };

    const b = shape.fmt(shape.value(runnerUp, basis));
    if (a === b)
      return { need: key, winner, runnerUp, tied: true, line: shape.tie(a) };

    const gap = num(shape.value(winner, basis)) - num(shape.value(runnerUp, basis));
    const how = gap < 0.75 ? "barely" : gap < 2 ? "narrowly" : "clearly";
    return { need: key, winner, runnerUp, tied: false,
             line: shape.win(winner.row.player, a, b, how) };
  });
}

/** Sleeper's CDN, addressed by the id resolved offline at build time. */
export const photoUrl = (id?: string | null) =>
  id ? `https://sleepercdn.com/content/nfl/players/${id}.jpg` : null;

export const initials = (name: string) =>
  name.split(/\s+/).slice(0, 2).map((w) => w[0]).join("").toUpperCase();
