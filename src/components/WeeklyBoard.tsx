"use client";

import { Fragment, useEffect, useMemo, useState } from "react";
import ChalkCard from "@/components/ChalkCard";
import {
  WEEKLY_POSITIONS,
  MC_COLOR,
  WILSON_COLOR,
  deltaColor,
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
  open,
  onToggle,
}: {
  title: string;
  who: string;
  color: string;
  rows: WeeklyRow[];
  orderBy: "rankData" | "rankVibes";
  noteKey: "noteData" | "noteVibes";
  open: string | null;
  onToggle: (player: string) => void;
}) {
  const ordered = useMemo(() => [...rows].sort((a, b) => a[orderBy] - b[orderBy]), [rows, orderBy]);
  return (
    <ChalkCard kicker={who} title={title} source={`${ordered.length} players ranked`}>
      <div className="scroll-x" style={{ maxHeight: 620, overflowY: "auto" }}>
        {/* Fixed layout so the take column gets the room rather than whatever
            the short columns leave over -- by default the browser sized
            Matchup and Player to their content and left the prose 140px of
            464. On mobile .cards-on-mobile makes these blocks, so the colgroup
            stops applying. */}
        <table className="chalk-table cards-on-mobile" style={{ tableLayout: "fixed", width: "100%" }}>
          <colgroup>
            <col style={{ width: "8%" }} />
            <col style={{ width: "44%" }} />
            <col style={{ width: "26%" }} />
            <col style={{ width: "22%" }} />
          </colgroup>
          <thead>
            <tr>
              <th className="num">#</th>
              <th>Player</th>
              <th>Matchup</th>
              <th className="num">Δ</th>
            </tr>
          </thead>
          <tbody>
            {ordered.map((r) => {
              const d = deltaOf(r);
              // On each list, Δ shows how far the OTHER voice is from this one.
              const shown = orderBy === "rankData" ? d : -d;
              const isOpen = open === r.player;
              const note = r[noteKey];
              // Wilson's list shows Wilson's projection; MC's shows what his
              // own rank is worth, so the points descend with the list you
              // are actually reading.
              const points = orderBy === "rankVibes" ? r.projVibes ?? null : r.proj ?? null;
              return (
                <Fragment key={r.player}>
                  <tr
                    onClick={() => onToggle(r.player)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        onToggle(r.player);
                      }
                    }}
                    tabIndex={0}
                    role="button"
                    aria-expanded={isOpen}
                    style={{ cursor: "pointer" }}
                  >
                    <td className="num font-retro text-lg" data-label="Rank" style={{ color }}>
                      {r[orderBy]}
                    </td>
                    <td data-primary="" style={{ overflowWrap: "anywhere" }}>
                      {r.player}
                      <span aria-hidden="true" style={{ color: "var(--ink-faint)", marginLeft: 6, fontSize: "0.8em" }}>
                        {isOpen ? "▾" : "▸"}
                      </span>
                    </td>
                    <td
                      data-label="Matchup"
                      style={{ color: "var(--ink-dim)", whiteSpace: "nowrap", paddingLeft: 6, paddingRight: 6 }}
                    >
                      {r.team ? <strong style={{ color: "var(--ink)", fontWeight: 600 }}>{r.team}</strong> : null}
                      {r.opponent ? (
                        <span style={{ fontSize: "0.88em" }}>{` ${r.isHome ? "vs." : "@"} ${r.opponent}`}</span>
                      ) : ""}
                    </td>
                    <td
                      className="num"
                      data-label="Delta"
                      style={{ color: deltaColor(d), fontWeight: Math.abs(d) >= 4 ? 600 : 400, paddingLeft: 4, paddingRight: 6 }}
                    >
                      {shown === 0 ? "—" : shown > 0 ? `+${shown}` : shown}
                    </td>
                  </tr>
                  {isOpen && (
                    <tr data-detail="">
                      <td colSpan={4} data-label="Take" style={{ background: "rgba(0,0,0,0.14)" }}>
                        {points != null && (
                          <div className="mb-1 flex items-baseline gap-2">
                            <span className="font-retro text-lg" style={{ color: "var(--chalk-gold)" }}>
                              {points.toFixed(1)}
                            </span>
                            <span className="text-xs uppercase tracking-wider" style={{ color: "var(--ink-faint)" }}>
                              projected points
                            </span>
                          </div>
                        )}
                        <p className="text-sm leading-snug" style={{ color: "var(--ink-dim)", margin: 0 }}>
                          {note || "No take written for this one yet."}
                        </p>
                      </td>
                    </tr>
                  )}
                </Fragment>
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
  const [scoring, setScoring] = useState<string>("");
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState<string | null>(null);
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

  // Scoring variants for this position, when it ships more than one list.
  const scorings = useMemo(
    () => Object.keys(board?.variants?.[pos] ?? {}),
    [board, pos]
  );
  // Derived rather than synced in an effect: switching position can leave the
  // stored choice pointing at a scoring that position does not offer, so fall
  // back to its first one instead of writing state during render.
  const activeScoring = scorings.includes(scoring) ? scoring : scorings[0] ?? "";
  const view = `${weekKey}|${pos}|${activeScoring}`;
  const [lastView, setLastView] = useState(view);
  if (view !== lastView) {
    // Reset the expanded row when the week, position or scoring changes --
    // done during render rather than in an effect so it lands in the same
    // paint as the new list.
    setLastView(view);
    setOpen(null);
  }

  const allRows = useMemo(() => {
    const byScoring = board?.variants?.[pos];
    if (byScoring && byScoring[activeScoring]) return byScoring[activeScoring];
    return board?.positions[pos] ?? [];
  }, [board, pos, activeScoring]);

  // One search filters both lists, since they render the same players in two
  // different orders.
  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return allRows;
    return allRows.filter(
      (r) =>
        r.player.toLowerCase().includes(q) ||
        (r.team ?? "").toLowerCase().includes(q) ||
        (r.opponent ?? "").toLowerCase().includes(q)
    );
  }, [allRows, query]);

  // A search that misses on this position but hits on another is a dead end
  // otherwise -- someone looking for a receiver from the QB tab just sees
  // nothing. Count the matches elsewhere so the empty state can offer them.
  const elsewhere = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q || rows.length > 0 || !board) return [] as { pos: Pos; count: number }[];
    return (Object.keys(board.positions) as Pos[])
      .filter((p) => p !== pos)
      .map((p) => ({
        pos: p,
        count: (board.positions[p] ?? []).filter((r) => r.player.toLowerCase().includes(q)).length,
      }))
      .filter((x) => x.count > 0);
  }, [board, pos, query, rows.length]);

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
      {/* One control row: week, scoring, position, search -- in the order you
          work through them. The week becomes a dropdown once there is more
          than one to pick from. */}
      <div className="flex flex-wrap items-end gap-x-5 gap-y-3">
        <div className="flex flex-col gap-1">
          <span className="text-xs uppercase tracking-wider" style={{ color: "var(--ink-faint)" }}>
            Week
          </span>
          {(index?.weeks ?? []).length > 1 ? (
            <select
              className="chalk-input"
              value={weekKey ?? ""}
              onChange={(e) => setWeekKey(e.target.value)}
              aria-label="Week"
            >
              {(index?.weeks ?? []).map((w) => (
                <option key={w.key} value={w.key}>
                  {w.label}
                </option>
              ))}
            </select>
          ) : (
            <span className="chalk-btn selected" style={{ cursor: "default" }}>
              {index?.weeks?.[0]?.label ?? "—"}
            </span>
          )}
        </div>

        {scorings.length > 1 && (
          <div className="flex flex-col gap-1">
            <span className="text-xs uppercase tracking-wider" style={{ color: "var(--ink-faint)" }}>
              Scoring
            </span>
            <div className="flex flex-wrap gap-2">
              {scorings.map((s) => (
                <button
                  key={s}
                  className={`chalk-btn ${activeScoring === s ? "selected" : ""}`}
                  onClick={() => setScoring(s)}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="flex flex-col gap-1">
          <span className="text-xs uppercase tracking-wider" style={{ color: "var(--ink-faint)" }}>
            Position
          </span>
          <div className="flex flex-wrap gap-2">
            {(Object.keys(board?.positions ?? {}) as Pos[]).map((p) => (
              <button key={p} className={`chalk-btn ${pos === p ? "selected" : ""}`} onClick={() => setPos(p)}>
                {p}
              </button>
            ))}
          </div>
        </div>

        <div className="flex flex-col gap-1">
          <span className="text-xs uppercase tracking-wider" style={{ color: "var(--ink-faint)" }}>
            Search
          </span>
          <div className="flex items-center gap-2">
            <input
              className="chalk-input"
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Player, team or opponent…"
              aria-label="Search players"
              style={{ maxWidth: 240 }}
            />
            {query && (
              <span className="text-sm" style={{ color: "var(--ink-faint)" }}>
                {rows.length}/{allRows.length}
              </span>
            )}
          </div>
        </div>
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

      {board && rows.length === 0 && query && (
        <ChalkCard title="Nobody by that name" alt>
          <p style={{ color: "var(--ink-dim)" }}>
            No player on the {pos} board matches “{query}”.
            {elsewhere.length === 0 && " Try a different spelling, or clear the search."}
          </p>
          {elsewhere.length > 0 && (
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <span className="text-sm" style={{ color: "var(--ink-dim)" }}>
                Found on:
              </span>
              {elsewhere.map((x) => (
                <button key={x.pos} className="chalk-btn" onClick={() => setPos(x.pos)}>
                  {x.pos} ({x.count})
                </button>
              ))}
            </div>
          )}
        </ChalkCard>
      )}

      {board && rows.length > 0 && (
        <>
          <div className="grid gap-5 lg:grid-cols-2">
            <RankList
              who="Wilson · the data"
              title={`${pos} — by the numbers`}
              color={WILSON_COLOR}
              rows={rows}
              orderBy="rankData"
              noteKey="noteData"
              open={open}
              onToggle={(name) => setOpen((cur) => (cur === name ? null : name))}
            />
            <RankList
              who="MC · the vibes"
              title={`${pos} — by the vibes`}
              color={MC_COLOR}
              rows={rows}
              orderBy="rankVibes"
              noteKey="noteVibes"
              open={open}
              onToggle={(name) => setOpen((cur) => (cur === name ? null : name))}
            />
          </div>
        </>
      )}
    </div>
  );
}
