"use client";

import { useEffect, useMemo, useState } from "react";
import ChalkCard from "@/components/ChalkCard";
import { initials, photoUrl } from "@/lib/startSit";
import {
  BREAKOUT_COLOR,
  BUY_COLOR,
  DEFAULT_RANK_GATE,
  HURT_COLOR,
  PEAK_COLOR,
  SELL_COLOR,
  adjustBoard,
  applyRankGate,
  hurtReason,
  nameKey,
  posRankNumber,
  verdictColor,
  verdictLine,
  type BuySellIndex,
  type BuySellBoard as Board,
  type BuySellRow,
  type GradedRow,
  type RankEntry,
} from "@/lib/buysell";
import { FORMATS, formatLabels, formatSublabels, type Format, type RankingSet } from "@/lib/rankings";

function Face({ row, size = 40 }: { row: BuySellRow; size?: number }) {
  const [failed, setFailed] = useState(false);
  const src = photoUrl(row.photo);
  const box = {
    width: size, height: size, borderRadius: "50%",
    border: "1px solid var(--ink-ghost)", background: "rgba(255,255,255,0.04)",
    flexShrink: 0,
  } as const;
  if (!src || failed)
    return (
      <div style={{ ...box, display: "grid", placeItems: "center",
                    color: "var(--ink-faint)", fontSize: size * 0.32 }}>
        {initials(row.player)}
      </div>
    );
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={src} alt="" loading="lazy" onError={() => setFailed(true)}
         style={{ ...box, objectFit: "cover", objectPosition: "top center" }} />
  );
}

function Card({ row, accent }: { row: GradedRow; accent: string }) {
  const miss = row.resid ?? 0;
  return (
    <div className="chalk-inset px-4 py-3">
      <div className="flex items-center gap-3">
        <Face row={row} />
        <div className="min-w-0 flex-1">
          <div className="truncate" style={{ color: "var(--ink)" }}>{row.player}</div>
          <div className="text-xs" style={{ color: "var(--ink-faint)" }}>
            {row.position} ·{" "}
            <strong style={{ color: "var(--ink)", fontWeight: 600 }}>{row.team}</strong>
            {row.posRank != null && ` · ${row.position}${row.posRank}`}
            {row.overallRank != null && ` · ${row.overallRank} overall`}
          </div>
        </div>
        <div className="text-right">
          <div className="font-retro text-xl" style={{ color: accent }}>
            {miss > 0 ? "+" : ""}{miss.toFixed(1)}
          </div>
          <div className="text-[0.62rem] uppercase tracking-widest"
               style={{ color: "var(--ink-faint)" }}>
            vs projection
          </div>
        </div>
      </div>
      <div className="mt-2 flex flex-wrap gap-x-4 text-xs" style={{ color: "var(--ink-dim)" }}>
        <span>Scored <strong style={{ color: "var(--ink)" }}>{row.actual?.toFixed(1)}</strong></span>
        <span>Projected {row.projected?.toFixed(1)}</span>
        {row.predChange != null && (
          <span>
            Rest of season {row.predChange > 0 ? "+" : ""}{row.predChange.toFixed(1)}/gm vs his level
          </span>
        )}
      </div>
      {row.why && (
        <p className="mt-2 text-sm leading-snug" style={{ color: "var(--ink-dim)", margin: 0 }}>
          {row.why}
        </p>
      )}
    </div>
  );
}

/**
 * Four boards and a lookup, off one model and two corrections.
 *
 * The model hands us a verdict per player. We change it in two places, both
 * in `lib/buysell.ts` and both reversible, because the raw verdict answers a
 * slightly different question than the tab asks:
 *
 *   1. It measures every player's outlook against one pool-wide average, so
 *      his projection going in decides most of the call. `adjustBoard` strips
 *      that trend within each position before splitting, which is the only
 *      reason a quarterback can appear on the breakout card at all.
 *   2. It ranks a week, not a roster, so it will tell you to sell the best
 *      player at his position. `applyRankGate` moves those to their own card:
 *      the week was real, but there is no trade to make.
 *
 * Neither touches how many players get flagged. The cuts were learned from
 * 2022-2025 and that calibration is kept; only who fills them changes.
 */
export default function BuySell() {
  const [board, setBoard] = useState<Board | null>(null);
  const [ranks, setRanks] = useState<Map<string, RankEntry>>(new Map());
  const [format, setFormat] = useState<Format>("ppr");
  const [query, setQuery] = useState("");

  useEffect(() => {
    let off = false;
    (async () => {
      try {
        const idx: BuySellIndex = await (await fetch("/data/buysell-index.json")).json();
        const latest = idx.weeks[idx.weeks.length - 1];
        if (!latest) return;
        const b: Board = await (await fetch(`/data/buysell-${latest.key}.json`)).json();
        if (!off) setBoard(b);
      } catch {
        /* the page shows its empty state rather than throwing */
      }
    })();
    return () => { off = true; };
  }, []);

  // The gate is a claim about what you could get back, so it has to be read
  // in the scoring the league actually uses. Josh Allen is QB1 on all three
  // boards; he is the 22nd asset in one-quarterback and the 3rd in superflex,
  // and only the second of those is unsellable.
  useEffect(() => {
    let off = false;
    (async () => {
      try {
        const set: RankingSet = await (await fetch(`/data/rankings-${format}.json`)).json();
        const m = new Map<string, RankEntry>();
        for (const r of set.rows) {
          if (Number.isFinite(r.rank)) m.set(nameKey(r.player), { rank: r.rank, posRank: posRankNumber(r.posRank) });
        }
        if (!off) setRanks(m);
      } catch {
        // Without the board every player reads as unranked, which leaves the
        // gate open and the sell card exactly as the model wrote it.
        if (!off) setRanks(new Map());
      }
    })();
    return () => { off = true; };
  }, [format]);

  const rows = useMemo<GradedRow[]>(
    () => (board ? applyRankGate(adjustBoard(board), ranks) : []),
    [board, ranks]
  );

  // One pass, so the cards cannot disagree about who is on them. Each board
  // leads with its biggest miss, which for the buys means the most negative.
  const { sells, buys, breakouts, peak, hurt, moved } = useMemo(() => {
    const pick = (v: string, dir: 1 | -1) =>
      rows.filter((r) => r.shown === v)
        .sort((a, b) => dir * ((b.resid ?? 0) - (a.resid ?? 0)));
    return {
      sells: pick("SELL HIGH", 1),
      buys: pick("BUY LOW", -1),
      // A big week the model does not expect back. The opposite trade to a sell.
      breakouts: pick("BREAKOUT", 1),
      // Sells you cannot make: still the best thing on the board at his spot.
      peak: pick("PEAK", 1),
      // Off every board. A man who left on the fifth play scored nothing
      // because he was not on the field, and the miss says nothing either way.
      hurt: pick("INJURED", -1),
      // How far the level correction moved things, counted rather than claimed.
      moved: rows.filter((r) => r.verdict !== r.adjVerdict).length,
    };
  }, [rows]);

  const found = useMemo(() => {
    const t = query.trim().toLowerCase();
    if (t.length < 2) return [];
    return rows
      .filter((r) => r.player.toLowerCase().includes(t) ||
                     (r.team ?? "").toLowerCase().includes(t))
      .slice(0, 6);
  }, [query, rows]);

  if (!board)
    return (
      <ChalkCard kicker="Buy low / sell high" title="Nothing to read yet">
        <p className="text-sm" style={{ color: "var(--ink-dim)" }}>
          This board fills in once a week has been played.
        </p>
      </ChalkCard>
    );

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center gap-2">
        <span className="chalk-kicker mr-1 text-sm">Scoring</span>
        {FORMATS.map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => setFormat(f)}
            className={`chalk-btn ${format === f ? "selected" : ""}`}
            title={formatSublabels[f]}
          >
            {formatLabels[f]}
          </button>
        ))}
      </div>

      <div>
        <div className="chalk-kicker mb-2 text-sm sm:text-base">Look up a player</div>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Any player who has played this week"
          className="w-full max-w-md rounded border px-3 py-2 text-sm"
          style={{ background: "transparent", borderColor: "var(--ink-ghost)", color: "var(--ink)" }}
        />
        {found.length > 0 && (
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            {found.map((r) => (
              <div key={r.player} className="chalk-inset px-4 py-3">
                <div className="flex items-center gap-3">
                  <Face row={r} size={34} />
                  <div className="min-w-0 flex-1">
                    <div className="truncate" style={{ color: "var(--ink)" }}>{r.player}</div>
                    <div className="text-xs" style={{ color: "var(--ink-faint)" }}>
                      {r.position} · {r.team}
                      {r.posRank != null && ` · ${r.position}${r.posRank}`}
                    </div>
                  </div>
                  <span className="font-retro text-sm" style={{ color: verdictColor(r.shown) }}>
                    {r.shown === "PEAK" ? "HOLD" : r.shown}
                  </span>
                </div>
                <p className="mt-2 text-sm leading-snug" style={{ color: "var(--ink-dim)", margin: 0 }}>
                  {verdictLine({ ...r, verdict: r.shown })}
                </p>
                {r.why && (
                  <p className="mt-1 text-xs leading-snug" style={{ color: "var(--ink-faint)", margin: 0 }}>
                    {r.why}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
        {query.trim().length >= 2 && found.length === 0 && (
          <p className="mt-2 text-xs" style={{ color: "var(--ink-faint)" }}>
            Nobody by that name has played yet this week.
          </p>
        )}
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <ChalkCard
          kicker={`${board.label} · sell high`}
          title={sells.length ? "Cash in while the number is loud" : "Nobody to sell this week"}
          source={`${sells.length} of ${rows.length} players who have played`}
        >
          {sells.length ? (
            <div className="flex flex-col gap-3">
              {sells.map((r) => <Card key={r.player} row={r} accent={SELL_COLOR} />)}
            </div>
          ) : (
            <p className="text-sm" style={{ color: "var(--ink-dim)" }}>
              No week big enough to sell into, on the games played so far.
            </p>
          )}
          {peak.length > 0 && (
            <p className="mt-4 text-xs leading-snug" style={{ color: "var(--ink-faint)" }}>
              {peak.length} more had the week for it but are already inside the top{" "}
              {DEFAULT_RANK_GATE} overall, so there is nothing better to trade them for.
              They are below.
            </p>
          )}
        </ChalkCard>

        <ChalkCard
          kicker={`${board.label} · buy low`}
          title={buys.length ? "Bad week, intact player" : "Nobody to buy this week"}
          source="a bad week with the role intact"
        >
          {buys.length ? (
            <div className="flex flex-col gap-3">
              {buys.map((r) => <Card key={r.player} row={r} accent={BUY_COLOR} />)}
            </div>
          ) : (
            <p className="text-sm" style={{ color: "var(--ink-dim)" }}>
              Nobody cleared the bar on the games played so far.
            </p>
          )}
          <p className="mt-4 text-xs leading-snug" style={{ color: "var(--ink-faint)" }}>
            Both calls held in every season and every projection band from 2022 to 2025,
            worth about a point and a half a game against the players the model declined
            to flag.
          </p>
        </ChalkCard>
      </div>

      {peak.length > 0 && (
        <ChalkCard
          kicker={`${board.label} · peak price`}
          title="Loud week, nobody better to get"
          source={`top ${DEFAULT_RANK_GATE} overall · ${formatLabels[format]}`}
        >
          <div className="grid gap-3 sm:grid-cols-2">
            {peak.map((r) => <Card key={r.player} row={r} accent={PEAK_COLOR} />)}
          </div>
          <p className="mt-4 text-xs leading-snug" style={{ color: "var(--ink-faint)" }}>
            The model expects these weeks back, and on the number alone each of these men
            is a sell. But a sell is a trade, and there is no trade here: they are already
            inside the first two rounds, so anything you could realistically get back is
            worse than what you gave up. You can only sell so high. Hold them and take the
            regression. Who lands here moves with the scoring above — a quarterback is
            unsellable in superflex and a fair sell in one-quarterback.
          </p>
        </ChalkCard>
      )}

      {breakouts.length > 0 && (
        <ChalkCard
          kicker={`${board.label} · not a fluke`}
          title="The week the model believes"
          source="a big week it does not expect back"
        >
          <div className="grid gap-3 sm:grid-cols-2">
            {breakouts.map((r) => <Card key={r.player} row={r} accent={BREAKOUT_COLOR} />)}
          </div>
          <p className="mt-4 text-xs leading-snug" style={{ color: "var(--ink-faint)" }}>
            The opposite trade to a sell high, off the same split: among big weeks, the
            half the model declines to call a sell goes on to beat the half it does.
            These are the men to go and get, not the ones to cash in.
          </p>
        </ChalkCard>
      )}

      {hurt.length > 0 && (
        <ChalkCard
          kicker={`${board.label} · not a performance`}
          title="Taken off both boards"
          source="an injury is not a bad game"
        >
          <div className="grid gap-2 sm:grid-cols-2">
            {hurt.map((r) => (
              <div key={r.player} className="chalk-inset flex items-center gap-3 px-4 py-2">
                <Face row={r} size={32} />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm" style={{ color: "var(--ink)" }}>
                    {r.player}
                  </div>
                  <div className="text-xs" style={{ color: "var(--ink-faint)" }}>
                    {r.position} · {r.team} · {r.actual?.toFixed(1)} of {r.projected?.toFixed(1)} projected
                    {r.snapShare != null ? ` on ${Math.round(r.snapShare * 100)}% of the snaps` : ""}
                  </div>
                </div>
                <span className="text-xs whitespace-nowrap" style={{ color: HURT_COLOR }}>
                  {hurtReason(r)}
                </span>
              </div>
            ))}
          </div>
        </ChalkCard>
      )}

      {moved > 0 && (
        <p className="text-xs leading-snug" style={{ color: "var(--ink-faint)" }}>
          A note on the method: the model measures a player&apos;s rest-of-season outlook
          against one league-wide average, so a man&apos;s projection going in decides most
          of his verdict before the week is read — which is why, on the raw number, no
          quarterback could ever be called a breakout and almost every tight end was.
          This board strips that trend out within each position before splitting, which
          moved {moved} of {rows.length} players. The counts the model calibrated on four
          seasons are unchanged; only who fills them.
        </p>
      )}
    </div>
  );
}
