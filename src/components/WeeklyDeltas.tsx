"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ChalkCard from "@/components/ChalkCard";
import { deltaColor, deltaOf, type WeeklyBoard as Board, type WeeklyIndex, type WeeklyRow } from "@/lib/weekly";

type Pick = WeeklyRow & { pos: string };

/**
 * The week's biggest disagreements, across every position at once.
 *
 * This lives on the home page rather than the weekly board: the page is called
 * The Deltas, and the deltas are the point of the whole exercise. The weekly
 * board is for working through a position; this is the argument worth reading
 * even if you never open it.
 */
export default function WeeklyDeltas({ limit = 6 }: { limit?: number }) {
  const [picks, setPicks] = useState<Pick[] | null>(null);
  const [label, setLabel] = useState<string>("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const idxRes = await fetch("/data/weekly-index.json");
        if (!idxRes.ok) return;
        const idx: WeeklyIndex = await idxRes.json();
        const latest = idx.weeks[idx.weeks.length - 1];
        if (!latest) return;
        const res = await fetch(`/data/weekly-${latest.key}.json`);
        if (!res.ok) return;
        const board: Board = await res.json();
        if (cancelled) return;

        // Biggest first, but guarantee every position a seat before the
        // deepest list takes them all -- receiver has 80 ranked players and
        // would otherwise sweep the card every week.
        const byPos = Object.entries(board.positions).map(([pos, rows]) =>
          rows
            .map((r) => ({ ...r, pos }))
            .filter((r) => Math.abs(deltaOf(r)) >= 2)
            .sort((a, b) => Math.abs(deltaOf(b)) - Math.abs(deltaOf(a)))
        );
        const seeded = byPos.map((rs) => rs[0]).filter(Boolean) as Pick[];
        const rest = byPos
          .flatMap((rs) => rs.slice(1))
          .sort((a, b) => Math.abs(deltaOf(b)) - Math.abs(deltaOf(a)));
        const top = [...seeded, ...rest]
          .slice(0, limit)
          .sort((a, b) => Math.abs(deltaOf(b)) - Math.abs(deltaOf(a)));
        setLabel(board.label);
        setPicks(top);
      } catch {
        /* the home page should never fail because a board is missing */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [limit]);

  if (!picks || picks.length === 0) return null;

  return (
    <ChalkCard
      kicker={label ? `${label} · every position` : "This week"}
      title="The deltas — where we disagree"
      source="positive = MC has him higher · negative = Wilson has him higher"
    >
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {picks.map((r) => {
          const d = deltaOf(r);
          return (
            <div key={`${r.pos}-${r.player}`} className="chalk-inset px-4 py-3">
              <div className="flex items-baseline justify-between gap-2">
                <span style={{ color: "var(--ink)" }}>{r.player}</span>
                <span className="font-retro text-xl" style={{ color: deltaColor(d) }}>
                  {d > 0 ? `+${d}` : d}
                </span>
              </div>
              <div className="mt-1 flex flex-wrap items-baseline gap-3 text-xs" style={{ color: "var(--ink-dim)" }}>
                <span style={{ color: "var(--accent-3)" }}>
                  Wilson {r.pos}
                  {r.rankData}
                </span>
                <span style={{ color: "var(--accent-2-lt)" }}>
                  MC {r.pos}
                  {r.rankVibes}
                </span>
                {r.team && (
                  <span>
                    {r.team}
                    {r.opponent ? ` ${r.isHome ? "vs." : "@"} ${r.opponent}` : ""}
                  </span>
                )}
              </div>
              {r.noteData && (
                <p className="mt-2 text-xs leading-snug" style={{ color: "var(--ink-dim)" }}>
                  <span style={{ color: "var(--accent-3)" }}>Data: </span>
                  {r.noteData}
                </p>
              )}
            </div>
          );
        })}
      </div>
      <p className="mt-4 text-sm">
        <Link href="/data-vs-vibes" style={{ color: "var(--accent)" }}>
          See both full lists →
        </Link>
      </p>
    </ChalkCard>
  );
}
