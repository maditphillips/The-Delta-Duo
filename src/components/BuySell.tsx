"use client";

import { useEffect, useMemo, useState } from "react";
import ChalkCard from "@/components/ChalkCard";
import { initials, photoUrl } from "@/lib/startSit";
import {
  BUY_COLOR,
  BUY_LEVEL_FLOOR,
  HURT_COLOR,
  SELL_COLOR,
  hurtReason,
  verdictColor,
  verdictLine,
  type BuySellBoard as Board,
  type BuySellIndex,
  type BuySellRow,
} from "@/lib/buysell";

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

function Card({ row, accent }: { row: BuySellRow; accent: string }) {
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
 * Two boards and a lookup, off one model.
 *
 * The buy side is deliberately thinner than the sell side. Across 2022-2025 the
 * regression call held in every season and every projection band, while the
 * rebound call only held for players projected 15 and up: a huge week is
 * usually touchdowns and touchdowns come back, whereas a terrible week is
 * injury or game script or genuine decline and one box score cannot separate
 * those. So under that line the tab says nothing instead of guessing, and says
 * why.
 */
export default function BuySell() {
  const [board, setBoard] = useState<Board | null>(null);
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

  const sells = useMemo(
    () => (board?.rows ?? []).filter((r) => r.verdict === "SELL HIGH")
      .sort((a, b) => (b.resid ?? 0) - (a.resid ?? 0)),
    [board]
  );
  const buys = useMemo(
    () => (board?.rows ?? []).filter((r) => r.verdict === "BUY LOW")
      .sort((a, b) => (a.resid ?? 0) - (b.resid ?? 0)),
    [board]
  );
  // Off both boards. A man who left on the fifth play scored nothing because
  // he was not on the field, and the miss says nothing about him either way.
  const hurt = useMemo(
    () => (board?.rows ?? []).filter((r) => r.verdict === "INJURED")
      .sort((a, b) => (a.resid ?? 0) - (b.resid ?? 0)),
    [board]
  );
  const found = useMemo(() => {
    const t = query.trim().toLowerCase();
    if (t.length < 2) return [];
    return (board?.rows ?? [])
      .filter((r) => r.player.toLowerCase().includes(t) ||
                     (r.team ?? "").toLowerCase().includes(t))
      .slice(0, 6);
  }, [query, board]);

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
                    </div>
                  </div>
                  <span className="font-retro text-sm" style={{ color: verdictColor(r.verdict) }}>
                    {r.verdict}
                  </span>
                </div>
                <p className="mt-2 text-sm leading-snug" style={{ color: "var(--ink-dim)", margin: 0 }}>
                  {verdictLine(r)}
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
          source={`${sells.length} of ${board.rows.length} players who have played`}
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
        </ChalkCard>

        <ChalkCard
          kicker={`${board.label} · buy low`}
          title={buys.length ? "Bad week, intact player" : "Nobody to buy this week"}
          source={`only players projected ${BUY_LEVEL_FLOOR}+ are eligible`}
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
            The buy side only covers players projected {BUY_LEVEL_FLOOR} points or more.
            Below that the backtest could not tell a rebound from a decline, so the
            model says nothing rather than guessing. The sell side has no such limit:
            it held in every season and every projection band from 2022 to 2025.
          </p>
        </ChalkCard>
      </div>

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
    </div>
  );
}
