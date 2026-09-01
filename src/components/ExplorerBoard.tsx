"use client";

import { useEffect, useMemo, useState } from "react";
import ChalkCard from "@/components/ChalkCard";
import { CHALK } from "@/components/charts/theme";
import {
  presets,
  volumeBands,
  volumeOf,
  type ExplorerPanel,
} from "@/lib/explorer";

type Pos = ExplorerPanel["pos"];

const AGE_BANDS = ["All", "≤22", "23", "24+"] as const;
const OUTCOMES = ["All", "Top-12", "Top-24", "Top-36", "Outside top-36"] as const;
type SortKey = "s" | "ppr" | "rk" | "vol";

function Chip({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="chalk-inset px-3 py-2 text-center">
      <div className="font-sketch text-2xl leading-none" style={{ color: color ?? "var(--ink)" }}>
        {value}
      </div>
      <div className="mt-1 text-xs" style={{ color: "var(--ink-dim)" }}>
        {label}
      </div>
    </div>
  );
}

function Select({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: readonly string[];
  onChange: (v: string) => void;
}) {
  return (
    <label className="flex flex-col gap-1 text-xs" style={{ color: "var(--ink-dim)" }}>
      {label}
      <select className="chalk-input" value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </label>
  );
}

export default function ExplorerBoard() {
  const [pos, setPos] = useState<Pos>("WR");
  const [panels, setPanels] = useState<Partial<Record<Pos, ExplorerPanel>>>({});
  const [error, setError] = useState<string | null>(null);

  const [day, setDay] = useState("All");
  const [ageBand, setAgeBand] = useState("All");
  const [seasonFrom, setSeasonFrom] = useState(2008);
  const [seasonTo, setSeasonTo] = useState(2025);
  const [moved, setMoved] = useState("All");
  const [vacancy, setVacancy] = useState("All");
  const [atRisk, setAtRisk] = useState("All");
  const [priorBand, setPriorBand] = useState("All");
  const [outcome, setOutcome] = useState("All");
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("ppr");

  useEffect(() => {
    if (panels[pos]) return;
    fetch(`/data/explorer-${pos.toLowerCase()}.json`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((json: ExplorerPanel) => setPanels((p) => ({ ...p, [pos]: json })))
      .catch((e) => setError(e instanceof Error ? e.message : "failed to load"));
  }, [pos, panels]);

  const panel = panels[pos];

  const resetFilters = () => {
    setDay("All");
    setAgeBand("All");
    setMoved("All");
    setVacancy("All");
    setAtRisk("All");
    setPriorBand("All");
    setOutcome("All");
    setSearch("");
    setSeasonFrom(2008);
    setSeasonTo(2025);
  };

  const applyPreset = (p: (typeof presets)[number]) => {
    resetFilters();
    setPos(p.pos);
    if (p.filters.day) setDay(p.filters.day);
    if (p.filters.ageBand) setAgeBand(p.filters.ageBand);
    if (p.filters.moved) setMoved(p.filters.moved === "moved" ? "Moved" : "Stayed");
    if (p.filters.vacancy) setVacancy(p.filters.vacancy === "yes" ? "Yes" : "No");
    if (p.filters.atRisk) setAtRisk(p.filters.atRisk === "yes" ? "Yes" : "No");
    if (p.filters.priorBand) setPriorBand(p.filters.priorBand);
  };

  const filtered = useMemo(() => {
    if (!panel) return [];
    const bands = volumeBands[pos];
    const q = search.trim().toLowerCase();
    let rows = panel.rows.filter((r) => {
      if (r.s < seasonFrom || r.s > seasonTo) return false;
      if (day !== "All" && r.dy !== day) return false;
      if (ageBand !== "All") {
        if (r.ag == null) return false;
        if (ageBand === "≤22" && r.ag > 22) return false;
        if (ageBand === "23" && r.ag !== 23) return false;
        if (ageBand === "24+" && r.ag < 24) return false;
      }
      if (moved !== "All") {
        if (r.mv == null) return false;
        if (moved === "Moved" && !r.mv) return false;
        if (moved === "Stayed" && r.mv) return false;
      }
      if (vacancy !== "All" && r.vac !== (vacancy === "Yes")) return false;
      if (atRisk !== "All" && r.risk !== (atRisk === "Yes")) return false;
      if (priorBand !== "All") {
        const b = bands.find((x) => x.label === priorBand);
        if (!b) return false;
        if (r.ptg == null || r.ptg < b.lo || r.ptg > b.hi) return false;
      }
      if (outcome !== "All") {
        if (outcome === "Top-12" && r.rk > 12) return false;
        if (outcome === "Top-24" && r.rk > 24) return false;
        if (outcome === "Top-36" && r.rk > 36) return false;
        if (outcome === "Outside top-36" && r.rk <= 36) return false;
      }
      if (q && !r.n.toLowerCase().includes(q) && !r.tm.toLowerCase().includes(q)) return false;
      return true;
    });
    rows = [...rows].sort((a, b) => {
      if (sortKey === "s") return b.s - a.s || a.rk - b.rk;
      if (sortKey === "rk") return a.rk - b.rk;
      if (sortKey === "vol") return volumeOf(b, panel) - volumeOf(a, panel);
      return b.ppr - a.ppr;
    });
    return rows;
  }, [panel, pos, day, ageBand, seasonFrom, seasonTo, moved, vacancy, atRisk, priorBand, outcome, search, sortKey]);

  const summary = useMemo(() => {
    if (!panel || filtered.length === 0) return null;
    const n = filtered.length;
    const pctRole = (100 * filtered.filter((r) => r.role).length) / n;
    const pct36 = (100 * filtered.filter((r) => r.rk <= 36).length) / n;
    const pct12 = (100 * filtered.filter((r) => r.rk <= 12).length) / n;
    const pprs = filtered.map((r) => r.ppr).sort((a, b) => a - b);
    const medPpr = pprs[Math.floor(pprs.length / 2)];
    return { n, pctRole, pct36, pct12, medPpr };
  }, [panel, filtered]);

  const years = Array.from({ length: 2025 - 2008 + 1 }, (_, i) => `${2008 + i}`);
  const volHeader = pos === "WR" ? "Targets" : pos === "RB" ? "Carries" : "Attempts";

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center gap-2">
        {(["WR", "RB", "QB"] as Pos[]).map((p) => (
          <button key={p} className={`chalk-btn ${pos === p ? "selected" : ""}`} onClick={() => setPos(p)}>
            {p === "WR" ? "Wide Receivers" : p === "RB" ? "Running Backs" : "Quarterbacks"}
          </button>
        ))}
        <span className="grow" />
        <button className="chalk-btn" onClick={resetFilters}>
          Clear filters
        </button>
      </div>

      <div className="flex flex-wrap gap-2">
        {presets.map((p) => (
          <button key={p.name} className="chalk-btn" style={{ borderStyle: "dashed" }} onClick={() => applyPreset(p)}>
            ✏️ {p.name}
          </button>
        ))}
      </div>

      <ChalkCard
        kicker="Player Explorer"
        title="Build a category, get the names"
        source="nflverse · regular season · PPR · drafted 2008-2025"
        note={
          panel
            ? `Filters combine (AND). "${panel.roleLabel}" is the ${pos} role bar from the studies; "at risk" means the player had never cleared it entering that season; "vacancy ahead" means his team's leading ${pos} from the prior season departed. Seasonal team = latest team that season, so lists can differ at the margins from the published panels.`
            : undefined
        }
      >
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          <Select label="Draft day" value={day} options={["All", "Round 1", "Day 2", "Day 3"]} onChange={setDay} />
          <Select label="Draft age" value={ageBand} options={AGE_BANDS} onChange={setAgeBand} />
          <Select
            label={`Prior-season ${volHeader.toLowerCase()}`}
            value={priorBand}
            options={["All", ...volumeBands[pos].map((b) => b.label)]}
            onChange={setPriorBand}
          />
          <Select label="Moved teams?" value={moved} options={["All", "Moved", "Stayed"]} onChange={setMoved} />
          <Select label="Vacancy ahead?" value={vacancy} options={["All", "Yes", "No"]} onChange={setVacancy} />
          <Select label="Never fed before? (at risk)" value={atRisk} options={["All", "Yes", "No"]} onChange={setAtRisk} />
          <Select label="Season finish" value={outcome} options={OUTCOMES} onChange={setOutcome} />
          <Select label="From season" value={`${seasonFrom}`} options={years} onChange={(v) => setSeasonFrom(Number(v))} />
          <Select label="To season" value={`${seasonTo}`} options={years} onChange={(v) => setSeasonTo(Number(v))} />
          <label className="flex flex-col gap-1 text-xs" style={{ color: "var(--ink-dim)" }}>
            Find player / team
            <input className="chalk-input" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="e.g. Nacua or MIA" />
          </label>
        </div>

        {error && (
          <p className="mt-4" style={{ color: CHALK.pink }}>
            Couldn&apos;t load the {pos} panel: {error}
          </p>
        )}
        {!panel && !error && (
          <p className="mt-6 text-center text-lg" style={{ color: "var(--ink-dim)" }}>
            Chalking up the {pos} board…
          </p>
        )}

        {panel && summary && (
          <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-5">
            <Chip label="player-seasons" value={summary.n.toLocaleString()} />
            <Chip label={`cleared ${panel.roleLabel}`} value={`${summary.pctRole.toFixed(1)}%`} color={CHALK.gold} />
            <Chip label="finished top-36" value={`${summary.pct36.toFixed(1)}%`} color={CHALK.blue} />
            <Chip label="finished top-12" value={`${summary.pct12.toFixed(1)}%`} color={CHALK.pink} />
            <Chip label="median PPR points" value={`${summary.medPpr.toFixed(1)}`} />
          </div>
        )}
        {panel && !summary && <p className="mt-6 text-center text-lg" style={{ color: "var(--ink-dim)" }}>No player-seasons match — loosen a filter.</p>}

        {panel && summary && (
          <>
            <div className="mt-5 flex flex-wrap items-center gap-2 text-xs" style={{ color: "var(--ink-dim)" }}>
              Sort by:
              {(
                [
                  ["ppr", "PPR points"],
                  ["rk", "Finish"],
                  ["vol", volHeader],
                  ["s", "Season"],
                ] as [SortKey, string][]
              ).map(([k, label]) => (
                <button key={k} className={`chalk-btn ${sortKey === k ? "selected" : ""}`} onClick={() => setSortKey(k)}>
                  {label}
                </button>
              ))}
              {filtered.length > 300 && <span>showing top 300 of {filtered.length.toLocaleString()}</span>}
            </div>
            <div className="scroll-x mt-3" style={{ maxHeight: 560, overflowY: "auto" }}>
              <table className="chalk-table">
                <thead>
                  <tr>
                    <th className="num">Season</th>
                    <th>Player</th>
                    <th>Team</th>
                    <th className="num">Draft</th>
                    <th className="num">Age</th>
                    <th className="num">{volHeader}</th>
                    <th className="num">Prior</th>
                    <th className="num">PPR</th>
                    <th className="num">Finish</th>
                    <th>Flags</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.slice(0, 300).map((r) => (
                    <tr key={`${r.id}-${r.s}`}>
                      <td className="num">{r.s}</td>
                      <td>{r.n}</td>
                      <td>
                        {r.tm}
                        {r.mv && r.ptm ? (
                          <span style={{ color: "var(--ink-faint)" }}> ← {r.ptm}</span>
                        ) : null}
                      </td>
                      <td className="num">
                        {r.yr} · {r.rd}.{r.pk}
                      </td>
                      <td className="num">{r.ag ?? "—"}</td>
                      <td className="num" style={{ color: r.role ? CHALK.gold : "var(--ink)" }}>
                        {volumeOf(r, panel)}
                      </td>
                      <td className="num" style={{ color: "var(--ink-dim)" }}>
                        {r.ptg ?? "—"}
                      </td>
                      <td className="num">{r.ppr.toFixed(1)}</td>
                      <td className="num" style={{ color: r.rk <= 12 ? CHALK.pink : r.rk <= 36 ? CHALK.blue : "var(--ink-dim)" }}>
                        {pos}
                        {r.rk}
                      </td>
                      <td className="text-xs" style={{ color: "var(--ink-dim)" }}>
                        {[r.vac ? "vacancy" : null, r.ff ? "first feed" : null, r.risk && !r.role ? "unfed" : null]
                          .filter(Boolean)
                          .join(" · ")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </ChalkCard>
    </div>
  );
}
