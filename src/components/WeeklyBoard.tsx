"use client";

import { useEffect, useMemo, useState } from "react";
import ChalkCard from "@/components/ChalkCard";
import {
  WEEKLY_POSITIONS,
  deltaColor,
  deltaLabel,
  deltaOf,
  type WeeklyBoard as Board,
  type WeeklyIndex,
  type WeeklyRow,
} from "@/lib/weekly";

type Pos = (typeof WEEKLY_POSITIONS)[number];

function RankList({
  title,
  who,
  color,
  rows,
  orderBy,
  noteKey,
}: {
  title: string;
  who: string;
  color: string;
  rows: WeeklyRow[];
  orderBy: "rankData" | "rankVibes";
  noteKey: "noteData" | "noteVibes";
}) {
  const ordered = useMemo(() => [...rows].sort((a, b) => a[orderBy] - b[orderBy]), [rows, orderBy]);
  return (
    <ChalkCard kicker={who} title={title} source={`${ordered.length} players ranked`}>
      <div className="scroll-x" style={{ maxHeight: 620, overflowY: "auto" }}>
        <table className="chalk-table cards-on-mobile">
          <thead>
            <tr>
              <th className="num">#</th>
              <th>Player</th>
              <th>Tm</th>
              <th className="num">Δ</th>
              <th>Take</th>
            </tr>
          </thead>
          <tbody>
            {ordered.map((r) => {
              const d = deltaOf(r);
              // On each list, Δ shows how far the OTHER voice is from this one.
              const shown = orderBy === "rankData" ? d : -d;
              return (
                <tr key={r.player}>
                  <td className="num font-retro text-lg" data-label="Rank" style={{ color }}>
                    {r[orderBy]}
                  </td>
                  <td data-primary="">{r.player}</td>
                  <td data-label="Team" style={{ color: "var(--ink-dim)" }}>{r.team ?? ""}</td>
                  <td className="num" data-label="Delta" style={{ color: deltaColor(d), fontWeight: Math.abs(d) >= 4 ? 600 : 400 }}>
                    {shown === 0 ? "—" : shown > 0 ? `+${shown}` : shown}
                  </td>
                  <td className="text-sm" data-label="Take" data-block="" style={{ color: "var(--ink-dim)", minWidth: 200 }}>
                    {r[noteKey] ?? ""}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </ChalkCard>
  );
}

export default function WeeklyBoard() {
  const [index, setIndex] = useState<WeeklyIndex | null>(null);
  const [weekKey, setWeekKey] = useState<string | null>(null);
  const [loaded, setLoaded] = useState<{ key: string; data: Board } | null>(null);
  const [pos, setPos] = useState<Pos>("QB");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch("/data/weekly-index.json")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((json: WeeklyIndex) => {
        if (cancelled) return;
        setIndex(json);
        const latest = json.weeks[json.weeks.length - 1];
        if (latest) setWeekKey(latest.key);
      })
      .catch(() => !cancelled && setIndex({ weeks: [] }));
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!weekKey) return;
    let cancelled = false;
    fetch(`/data/weekly-${weekKey}.json`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((json: Board) => {
        if (cancelled) return;
        setLoaded({ key: weekKey, data: json });
        const available = Object.keys(json.positions) as Pos[];
        if (available.length && !available.includes(pos)) setPos(available[0]);
      })
      .catch((e) => !cancelled && setError(e instanceof Error ? e.message : "failed to load"));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [weekKey]);

  // only show a board once the fetch for the selected week has landed
  const board = loaded && loaded.key === weekKey ? loaded.data : null;
  const rows = useMemo(() => board?.positions[pos] ?? [], [board, pos]);
  const biggest = useMemo(
    () => [...rows].sort((a, b) => Math.abs(deltaOf(b)) - Math.abs(deltaOf(a))).filter((r) => Math.abs(deltaOf(r)) >= 2).slice(0, 6),
    [rows]
  );

  if (index && index.weeks.length === 0) {
    return (
      <ChalkCard kicker="Weekly" title="No weeks posted yet" alt>
        <p style={{ color: "var(--ink-dim)" }}>
          Drop a CSV per position into <code>data/weekly/&lt;season&gt;/week-&lt;NN&gt;/</code> —{" "}
          <code>qb.csv</code>, <code>rb.csv</code>, <code>wr.csv</code>, <code>te.csv</code>, <code>k.csv</code> — with columns{" "}
          <code>rank_data, rank_vibes, player, team, note_data, note_vibes</code>, then run{" "}
          <code>node scripts/build-weekly.mjs</code>. Every past week stays in the picker.
        </p>
      </ChalkCard>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center gap-2">
        {(index?.weeks ?? []).map((w) => (
          <button key={w.key} className={`chalk-btn ${weekKey === w.key ? "selected" : ""}`} onClick={() => setWeekKey(w.key)}>
            {w.label}
          </button>
        ))}
        <span className="grow" />
        {(Object.keys(board?.positions ?? {}) as Pos[]).map((p) => (
          <button key={p} className={`chalk-btn ${pos === p ? "selected" : ""}`} onClick={() => setPos(p)}>
            {p}
          </button>
        ))}
      </div>

      {error && (
        <ChalkCard title="Couldn't load the week" alt>
          <p style={{ color: "var(--accent-2-lt)" }}>{error}</p>
        </ChalkCard>
      )}

      {!board && !error && (
        <div className="py-14 text-center text-xl" style={{ color: "var(--ink-dim)" }}>
          Chalking up the board…
        </div>
      )}

      {board && rows.length > 0 && (
        <>
          {biggest.length > 0 && (
            <ChalkCard
              kicker={`${board.label} · ${pos}`}
              title="The deltas — where we disagree"
              source="positive = MC has him higher · negative = Wilson has him higher"
            >
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {biggest.map((r) => {
                  const d = deltaOf(r);
                  return (
                    <div key={r.player} className="chalk-inset px-4 py-3">
                      <div className="flex items-baseline justify-between gap-2">
                        <span style={{ color: "var(--ink)" }}>{r.player}</span>
                        <span className="font-retro text-xl" style={{ color: deltaColor(d) }}>
                          {d > 0 ? `+${d}` : d}
                        </span>
                      </div>
                      <div className="mt-1 flex items-baseline gap-3 text-xs" style={{ color: "var(--ink-dim)" }}>
                        <span style={{ color: "var(--accent-3)" }}>Wilson {pos}
                          {r.rankData}</span>
                        <span style={{ color: "var(--accent-2-lt)" }}>MC {pos}
                          {r.rankVibes}</span>
                        <span>{deltaLabel(d)}</span>
                      </div>
                      {(r.noteData || r.noteVibes) && (
                        <p className="mt-2 text-xs leading-snug" style={{ color: "var(--ink-dim)" }}>
                          {r.noteData ? <span style={{ color: "var(--accent-3)" }}>Data: </span> : null}
                          {r.noteData}
                          {r.noteData && r.noteVibes ? <br /> : null}
                          {r.noteVibes ? <span style={{ color: "var(--accent-2-lt)" }}>Vibes: </span> : null}
                          {r.noteVibes}
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            </ChalkCard>
          )}

          <div className="grid gap-5 lg:grid-cols-2">
            <RankList
              who="Wilson · the data"
              title={`${pos} — by the numbers`}
              color="var(--accent-3)"
              rows={rows}
              orderBy="rankData"
              noteKey="noteData"
            />
            <RankList
              who="MC · the vibes"
              title={`${pos} — by the vibes`}
              color="var(--accent-2-lt)"
              rows={rows}
              orderBy="rankVibes"
              noteKey="noteVibes"
            />
          </div>
        </>
      )}
    </div>
  );
}
