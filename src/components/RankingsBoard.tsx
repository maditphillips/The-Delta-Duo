"use client";

import { useEffect, useMemo, useState } from "react";
import ChalkCard from "@/components/ChalkCard";
import { CHALK } from "@/components/charts/theme";
import {
  FORMATS,
  POSITION_FILTERS,
  flagColors,
  formatLabels,
  formatSublabels,
  tierColors,
  type Format,
  type PositionFilter,
  type RankingSet,
} from "@/lib/rankings";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; set: RankingSet; source: "uploaded" | "baked" };

async function fetchBoard(format: Format): Promise<LoadState> {
  // Prefer a Supabase-uploaded set; fall back to the baked-in board.
  try {
    const res = await fetch(`/api/rankings?format=${format}`);
    if (res.ok) {
      const json = await res.json();
      if (json.set && Array.isArray(json.set.rows) && json.set.rows.length > 0) {
        return { status: "ready", set: json.set as RankingSet, source: "uploaded" };
      }
    }
  } catch {
    // fall through to the baked board
  }
  try {
    const res = await fetch(`/data/rankings-${format}.json`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const set = (await res.json()) as RankingSet;
    return { status: "ready", set, source: "baked" };
  } catch (e) {
    return { status: "error", message: e instanceof Error ? e.message : "failed to load" };
  }
}

export default function RankingsBoard() {
  const [format, setFormat] = useState<Format>("ppr");
  const [position, setPosition] = useState<PositionFilter>("All");
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [filter, setFilter] = useState("");

  useEffect(() => {
    let cancelled = false;
    fetchBoard(format).then((next) => {
      if (!cancelled) setState(next);
    });
    return () => {
      cancelled = true;
    };
  }, [format]);

  const rows = useMemo(() => {
    if (state.status !== "ready") return [];
    let r = state.set.rows;
    if (position !== "All") r = r.filter((x) => (x.pos ?? "").toUpperCase() === position);
    const q = filter.trim().toLowerCase();
    if (q) {
      r = r.filter(
        (x) =>
          x.player.toLowerCase().includes(q) ||
          (x.team ?? "").toLowerCase().includes(q) ||
          (x.tier ?? "").toLowerCase().includes(q)
      );
    }
    return r;
  }, [state, position, filter]);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center gap-2">
        {FORMATS.map((f) => (
          <button
            key={f}
            className={`chalk-btn ${format === f ? "selected" : ""}`}
            onClick={() => {
              setFormat(f);
              setState({ status: "loading" });
            }}
            title={formatSublabels[f]}
          >
            {formatLabels[f]}
          </button>
        ))}
      </div>

      {state.status === "loading" && (
        <div className="py-14 text-center text-xl" style={{ color: "var(--ink-dim)" }}>
          Chalking up the board…
        </div>
      )}

      {state.status === "error" && (
        <ChalkCard title="Couldn't load the board" alt>
          <p style={{ color: CHALK.pink }}>{state.message}</p>
        </ChalkCard>
      )}

      {state.status === "ready" && (
        <ChalkCard
          kicker={`${formatLabels[format]} board`}
          title={`2026 Redraft — ${formatLabels[format]}`}
          source={`${formatSublabels[format]} · ${
            state.source === "uploaded"
              ? `uploaded ${state.set.updated ? new Date(state.set.updated).toLocaleDateString() : ""}${state.set.filename ? ` · ${state.set.filename}` : ""}`
              : `The Delta Duo 2026 board`
          } · ${state.set.rows.length} players`}
        >
          <div className="mb-4 flex flex-wrap items-center gap-2">
            {POSITION_FILTERS.map((p) => (
              <button key={p} className={`chalk-btn ${position === p ? "selected" : ""}`} onClick={() => setPosition(p)}>
                {p === "All" ? "All Players" : p}
              </button>
            ))}
            <span className="grow" />
            <input
              className="chalk-input w-full max-w-xs"
              placeholder="Find a player, team, or tier…"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            />
          </div>

          <div className="scroll-x" style={{ maxHeight: 640, overflowY: "auto" }}>
            <table className="chalk-table">
              <thead>
                <tr>
                  <th className="num">{position === "All" ? "Rank" : "Pos rank"}</th>
                  {position === "All" && <th>Pos</th>}
                  <th>Player</th>
                  <th>Team</th>
                  <th className="num">Bye</th>
                  <th>Tier</th>
                  <th>Flag</th>
                  <th>Delta note</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={`${r.rank}-${r.player}`}>
                    <td className="num font-sketch text-lg" style={{ color: r.rank <= 24 ? "var(--chalk-gold)" : "var(--ink)" }}>
                      {position === "All" ? r.rank : (r.posRank ?? r.rank)}
                    </td>
                    {position === "All" && (
                      <td style={{ color: "var(--ink-dim)" }}>{r.posRank ?? r.pos ?? ""}</td>
                    )}
                    <td style={{ whiteSpace: "nowrap" }}>{r.player}</td>
                    <td>{r.team ?? ""}</td>
                    <td className="num">{r.bye ?? ""}</td>
                    <td style={{ whiteSpace: "nowrap", color: tierColors[r.tier ?? ""] ?? "var(--ink-dim)" }}>{r.tier ?? ""}</td>
                    <td style={{ whiteSpace: "nowrap" }}>
                      {r.flag ? (
                        <span
                          className="rounded px-1.5 py-0.5 text-xs"
                          style={{
                            color: flagColors[r.flag] ?? "var(--ink-dim)",
                            border: `1px solid ${flagColors[r.flag] ?? "var(--ink-ghost)"}`,
                          }}
                        >
                          {r.flag}
                        </span>
                      ) : null}
                    </td>
                    <td className="text-sm" style={{ color: "var(--ink-dim)", minWidth: 260 }}>
                      {r.note ?? ""}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {rows.length === 0 && (
              <div className="py-8 text-center" style={{ color: "var(--ink-dim)" }}>
                No players match.
              </div>
            )}
          </div>
        </ChalkCard>
      )}
    </div>
  );
}
