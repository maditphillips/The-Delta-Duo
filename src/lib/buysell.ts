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
  verdict: "INJURED" | "SELL HIGH" | "BUY LOW" | "HOLD" | "NO CALL" | string;
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

/** Below this projection the backtest could not call a rebound, so the tab
 *  does not pretend to. See model/dd/rebound.py. */
export const BUY_LEVEL_FLOOR = 15;

export const SELL_COLOR = "var(--accent-2-lt)";
export const BUY_COLOR = "var(--accent-3)";

export const HURT_COLOR = "var(--accent-gold)";

export function verdictColor(v: string) {
  if (v === "SELL HIGH") return SELL_COLOR;
  if (v === "BUY LOW") return BUY_COLOR;
  if (v === "INJURED") return HURT_COLOR;
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
  // The verb says which way it went, so the number does not need a sign too:
  // "missed by -6.9" reads as a double negative.
  const miss = r.resid == null ? "" : Math.abs(r.resid).toFixed(1);
  switch (r.verdict) {
    case "INJURED":
      return `Off the board: ${hurtReason(r)}. He did not play a full game, so this week is not a performance and there is nothing in it to trade on either way.`;
    case "SELL HIGH":
      return `Sell high. He beat his projection by ${miss} and the model expects it back.`;
    case "BUY LOW":
      return `Buy low. He missed by ${miss} and the model expects a rebound.`;
    case "NO CALL":
      return `No call. He missed by ${miss}, but under ${BUY_LEVEL_FLOOR} projected points the model could not pick rebounds from declines in backtest, so it says nothing rather than guessing.`;
    default:
      return r.resid != null && Math.abs(r.resid) >= 5
        ? `Hold. A ${miss} week, and the model does not read it as a turning point.`
        : "Hold. Nothing in this week worth trading on.";
  }
}
