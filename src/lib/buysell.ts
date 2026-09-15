export type BuySellRow = {
  player: string;
  position: string;
  team?: string | null;
  /** Sleeper id, for the headshot. */
  photo?: string | null;
  /** What he actually scored, and what Sleeper had him down for. */
  actual: number | null;
  projected: number | null;
  /** actual minus projected. The size of the miss. */
  resid: number | null;
  /** Points a game against his current level over the rest of the season. */
  predChange: number | null;
  verdict: "INJURED" | "SELL HIGH" | "BUY LOW" | "BREAKOUT" | "HOLD" | string;
  /** Sleeper's live status, when he carries one. */
  injuryStatus?: string | null;
  injuryPart?: string | null;
  /** A projected starter who played almost none of the snaps, so the week
   *  ended early even if the report has not caught up yet. */
  leftEarly?: boolean;
  /** The week in one line: what he was given and what he did with it. */
  why?: string | null;
  snapShare?: number | null;
  /** His projection going in, which is the level everything is measured from. */
  level?: number | null;
};

export type BuySellBoard = {
  season: number;
  week: number;
  label: string;
  /** Where the flags were set, learned from 2022-2025 rather than guessed. */
  cuts?: { resid_lo?: number; resid_hi?: number; sell_cut?: number; buy_cut?: number };
  rows: BuySellRow[];
};

export type BuySellIndex = {
  weeks: { key: string; season: number; week: number; label: string; count: number }[];
};

export const SELL_COLOR = "var(--accent-2-lt)";
export const BUY_COLOR = "var(--accent-3)";
export const BREAKOUT_COLOR = "var(--chalk-gold)";

export const HURT_COLOR = "var(--accent-gold)";
/** A sell the rankings say you cannot make. */
export const PEAK_COLOR = "var(--chalk-blue)";

export function verdictColor(v: string) {
  if (v === "SELL HIGH") return SELL_COLOR;
  if (v === "BUY LOW") return BUY_COLOR;
  if (v === "BREAKOUT") return BREAKOUT_COLOR;
  if (v === "INJURED") return HURT_COLOR;
  if (v === "PEAK") return PEAK_COLOR;
  return "var(--ink-faint)";
}

/** Why he is off the boards, in as few words as the feed allows. */
export function hurtReason(r: BuySellRow): string {
  const part = r.injuryPart ? ` (${r.injuryPart.toLowerCase()})` : "";
  if (r.injuryStatus) return `${r.injuryStatus}${part}`;
  return "left the game early";
}

/** What the verdict means in a sentence, for the lookup. */
export function verdictLine(r: BuySellRow): string {
  // The verb carries the direction so the number does not need a sign too,
  // which means every branch has to supply one. Leave it off and a miss of
  // 6.9 prints as "a 6.9 week", which reads as the number he scored.
  const miss = r.resid == null ? "" : Math.abs(r.resid).toFixed(1);
  const by = r.resid != null && r.resid > 0
    ? `beat his projection by ${miss}`
    : `missed his projection by ${miss}`;
  switch (r.verdict) {
    case "INJURED":
      return `Off the board: ${hurtReason(r)}. He did not play a full game, so this week is not a performance and there is nothing in it to trade on either way.`;
    case "SELL HIGH":
      return `Sell high. He ${by} points and the model expects it back.`;
    case "BUY LOW":
      return `Buy low. He ${by} points and the model expects a rebound.`;
    case "BREAKOUT":
      return `Go and get him. He ${by} points and the model does not expect it back, which is the opposite trade to a sell high.`;
    case "PEAK":
      return `Peak price, no upgrade. He ${by} points and the model expects it back, but he is already near the top of his position, so there is nobody better to trade him for. Hold him.`;
    default:
      return r.resid != null && Math.abs(r.resid) >= 5
        ? `Hold. He ${by} points, and the model does not read that as a turning point.`
        : "Hold. Nothing in this week worth trading on.";
  }
}

/* ------------------------------------------------------------------ *
 *  Two corrections applied on top of the model's own verdict.
 *
 *  Both exist because `pred_change` carries a term it should not. The
 *  model reverts every player toward one pool-wide anchor of about 7.5
 *  points, so `level` — which is just his projection going in — decides
 *  most of the call before the week is looked at. Fitting the board,
 *  pred_change lands within a rounding error of
 *
 *      1.85 - 0.246 * level
 *
 *  which is why nobody projected 15 and up ever cleared the sell cut and
 *  nobody under 5 ever failed it. Positions inherit that: quarterbacks
 *  are projected 17 on average and tight ends 5, so on the raw number a
 *  quarterback could not be a breakout and a tight end could hardly be
 *  anything else.
 *
 *  The honest fix is on the model side, in the reversion anchor itself.
 *  What follows is the display-side stand-in: strip the level trend, then
 *  ask the same question of what is left. Every row keeps its original
 *  verdict in `verdict`, so nothing here is destructive.
 * ------------------------------------------------------------------ */

/** Least-squares pred_change = a + b * level, fitted per position. */
type LevelFit = { a: number; b: number; n: number };

/** Below this a position is too thin to fit on its own and borrows the
 *  board-wide line. A partial slate is the case that matters: on a
 *  Thursday board a position can be three players deep. */
const MIN_FIT = 8;

function fitLevel(rows: BuySellRow[]): LevelFit | null {
  const pts = rows.filter(
    (r) => r.level != null && r.predChange != null && Number.isFinite(r.level) && Number.isFinite(r.predChange)
  ) as (BuySellRow & { level: number; predChange: number })[];
  if (pts.length < MIN_FIT) return null;
  const mx = pts.reduce((s, r) => s + r.level, 0) / pts.length;
  const my = pts.reduce((s, r) => s + r.predChange, 0) / pts.length;
  const sxx = pts.reduce((s, r) => s + (r.level - mx) ** 2, 0);
  // Every player projected the same: no trend to remove, and dividing
  // through would hand back an infinity.
  if (sxx < 1e-9) return null;
  const b = pts.reduce((s, r) => s + (r.level - mx) * (r.predChange - my), 0) / sxx;
  return { a: my - b * mx, b, n: pts.length };
}

/** One line per position, each falling back to the board-wide line.
 *  Fitting per position rather than pooling is what makes the residuals
 *  mean-zero within a position, which is the whole point: it is the only
 *  way a quarterback is measured against quarterbacks. */
export function levelFits(rows: BuySellRow[]): { byPos: Map<string, LevelFit>; all: LevelFit | null } {
  const live = rows.filter((r) => r.verdict !== "INJURED");
  const all = fitLevel(live);
  const byPos = new Map<string, LevelFit>();
  for (const pos of new Set(live.map((r) => r.position))) {
    const fit = fitLevel(live.filter((r) => r.position === pos));
    if (fit) byPos.set(pos, fit);
  }
  return { byPos, all };
}

/** How his rest-of-season outlook compares to the players projected where
 *  he is projected. Positive means the model likes him more than his level
 *  alone would explain; that is the part of pred_change the week earned. */
export function adjustedOutlook(
  r: BuySellRow,
  fits: { byPos: Map<string, LevelFit>; all: LevelFit | null }
): number | null {
  if (r.level == null || r.predChange == null) return null;
  const fit = fits.byPos.get(r.position) ?? fits.all;
  if (!fit) return null;
  return r.predChange - (fit.a + fit.b * r.level);
}

export type GradedRow = BuySellRow & {
  /** pred_change with his own position's level trend removed. */
  adj: number | null;
  /** The verdict after that adjustment. Equal to `verdict` when the board
   *  is too thin to fit, so the fallback is always the model's own call. */
  adjVerdict: string;
  /** Where the rankings board has him overall, and at his position. Overall
   *  is what the gate reads; the positional rank is for the card to print. */
  overallRank: number | null;
  posRank: number | null;
  /** The verdict actually shown, after the rank gate. */
  shown: string;
};

/**
 * Re-split the flagged weeks on the level-adjusted number.
 *
 * The count of each verdict is preserved exactly. The sell and buy cuts
 * were learned from 2022-2025 and that calibration is worth keeping; what
 * is wrong is not how many players get flagged but which ones. So this
 * reorders rather than re-thresholds, and a board it cannot fit comes back
 * untouched.
 */
export function adjustBoard(board: BuySellBoard): GradedRow[] {
  const fits = levelFits(board.rows);
  const rows: GradedRow[] = board.rows.map((r) => ({
    ...r,
    adj: adjustedOutlook(r, fits),
    adjVerdict: r.verdict,
    overallRank: null,
    posRank: null,
    shown: r.verdict,
  }));
  if (!fits.all) return rows;

  const hi = board.cuts?.resid_hi;
  const lo = board.cuts?.resid_lo;
  // With the cuts we can see every week that cleared the bar, including the
  // ones held. Without them we can only reshuffle what the model flagged,
  // which still fixes the split but cannot promote a held week.
  const big = rows.filter((r) =>
    r.verdict === "INJURED" || r.adj == null ? false
      : hi != null && r.resid != null ? r.resid >= hi
      : r.verdict === "SELL HIGH" || r.verdict === "BREAKOUT"
  );
  const bad = rows.filter((r) =>
    r.verdict === "INJURED" || r.adj == null ? false
      : lo != null && r.resid != null ? r.resid <= lo
      : r.verdict === "BUY LOW"
  );

  const split = (pool: GradedRow[], top: string, rest: string, n: number) => {
    // Highest adjusted outlook first: those are the weeks the model keeps.
    pool.sort((a, b) => (b.adj ?? 0) - (a.adj ?? 0));
    pool.forEach((r, i) => { r.adjVerdict = i < n ? top : rest; r.shown = r.adjVerdict; });
  };
  split(big, "BREAKOUT", "SELL HIGH", big.filter((r) => r.verdict === "BREAKOUT").length);
  split(bad, "BUY LOW", "HOLD", bad.filter((r) => r.verdict === "BUY LOW").length);
  return rows;
}

/** "RB7" -> 7. The rankings board writes it as a string. */
export function posRankNumber(posRank?: string | null): number | null {
  const m = /(\d+)\s*$/.exec(posRank ?? "");
  return m ? Number(m[1]) : null;
}

/** Names come from two feeds, so match on letters alone. */
export function nameKey(name: string): string {
  return name.toLowerCase().normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/\b(jr|sr|ii|iii|iv|v)\b/g, "")
    .replace(/[^a-z]/g, "");
}

/** Where a man stops being tradeable up on overall value. Twenty-four is the
 *  first two rounds of a twelve-team draft: above that line you are asking
 *  somebody to hand you a better asset than the one you are giving away. */
export const DEFAULT_RANK_GATE = 24;

/** And the other way in: the top of a scarce position, whatever the overall
 *  board says. One-quarterback and one-tight-end scoring discounts those
 *  positions into the thirties and forties overall, so the rank gate alone
 *  calls QB1 and TE2 sellable — but the next man at those positions is a real
 *  drop, not a lateral move, so there is still nothing to trade up to. Two
 *  deep, because that is where the drop is; by TE3 you are trading inside a
 *  tier and the gate should not be shut. */
export const DEFAULT_POS_GATE = 2;

export type RankEntry = { rank: number; posRank: number | null };

/**
 * Take the unsellable off the sell board.
 *
 * A sell high is advice to trade, and advice to trade is only worth printing
 * if somebody better is available to trade for. The model ranks a week, not a
 * roster, so it will tell you to sell the best player in the league after a
 * big game — which cannot be acted on, and reads as nonsense next to the
 * calls that can.
 *
 * Two ways a man is held back, because one number cannot catch both cases.
 * Overall rank catches the elite running backs and receivers, and moves with
 * the scoring, which it has to: a quarterback is the 22nd asset in PPR and
 * the 3rd in superflex. Positional rank catches the top of the thin
 * positions, which overall rank prices below what they can actually be
 * traded for. A player inside either is shown at peak price instead.
 */
export function applyRankGate(
  rows: GradedRow[],
  ranks: Map<string, RankEntry>,
  gate = DEFAULT_RANK_GATE,
  posGate = DEFAULT_POS_GATE
): GradedRow[] {
  for (const r of rows) {
    const found = ranks.get(nameKey(r.player));
    r.overallRank = found?.rank ?? null;
    r.posRank = found?.posRank ?? null;
    // Unranked means deep, not elite, so neither gate catches him.
    const held =
      (r.overallRank != null && r.overallRank <= gate) ||
      (r.posRank != null && r.posRank <= posGate);
    if (r.shown === "SELL HIGH" && held) r.shown = "PEAK";
  }
  return rows;
}
