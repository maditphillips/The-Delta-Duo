"use client";

import { useEffect, useMemo, useState } from "react";
import Papa from "papaparse";
import ChalkCard from "@/components/ChalkCard";
import { CHALK } from "@/components/charts/theme";
import {
  FORMATS,
  POSITION_FILTERS,
  formatLabels,
  formatSublabels,
  normalizeCsvRows,
  tierColors,
  type Format,
  type PositionFilter,
  type RankingRow,
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
  const [showUpload, setShowUpload] = useState(false);
  const [filter, setFilter] = useState("");
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    let cancelled = false;
    fetchBoard(format).then((next) => {
      if (!cancelled) setState(next);
    });
    return () => {
      cancelled = true;
    };
  }, [format, refresh]);

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
        <span className="grow" />
        <button className="chalk-btn" onClick={() => setShowUpload((v) => !v)}>
          {showUpload ? "Hide upload" : "✏️ Upload update"}
        </button>
      </div>

      {showUpload && <UploadPanel format={format} onUploaded={() => setRefresh((r) => r + 1)} />}

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

function UploadPanel({ format, onUploaded }: { format: Format; onUploaded: () => void }) {
  const [rows, setRows] = useState<RankingRow[]>([]);
  const [filename, setFilename] = useState<string>("");
  const [key, setKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);

  const onFile = (file: File) => {
    setMessage(null);
    setFilename(file.name);
    Papa.parse<Record<string, unknown>>(file, {
      header: true,
      skipEmptyLines: true,
      complete: (result) => {
        const normalized = normalizeCsvRows(result.data);
        setRows(normalized);
        if (normalized.length === 0) {
          setMessage({ ok: false, text: "No usable rows found — the CSV needs at least a player column." });
        }
      },
      error: (err) => setMessage({ ok: false, text: `Couldn't parse that file: ${err.message}` }),
    });
  };

  const upload = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const res = await fetch("/api/rankings", {
        method: "POST",
        headers: { "content-type": "application/json", "x-upload-key": key },
        body: JSON.stringify({ format, filename, rows }),
      });
      const json = await res.json();
      if (!res.ok) {
        setMessage({ ok: false, text: json.hint ? `${json.error} — ${json.hint}` : (json.error ?? `HTTP ${res.status}`) });
      } else {
        setMessage({ ok: true, text: `Board updated — ${json.rows} players on the ${formatLabels[format]} board.` });
        setRows([]);
        setFilename("");
        onUploaded();
      }
    } catch (e) {
      setMessage({ ok: false, text: e instanceof Error ? e.message : "network error" });
    } finally {
      setBusy(false);
    }
  };

  return (
    <ChalkCard title={`Upload a ${formatLabels[format]} update`} alt>
      <p className="mb-4 text-sm" style={{ color: "var(--ink-dim)" }}>
        CSV in the board format — <code>overall_rank, player, pos, pos_rank, team, bye, tier, delta_note</code> (headers matched
        loosely; only <code>player</code> is required). The upload replaces the live {formatLabels[format]} board instantly, no
        redeploy; the committed CSVs in <code>data/rankings/</code> remain the fallback. Requires Supabase +{" "}
        <code>RANKINGS_UPLOAD_KEY</code> to be configured.
      </p>
      <div className="flex flex-wrap items-center gap-3">
        <label className="chalk-btn cursor-pointer">
          Choose CSV
          <input
            type="file"
            accept=".csv,text/csv"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])}
          />
        </label>
        {filename && (
          <span style={{ color: "var(--ink-dim)" }}>
            {filename} · {rows.length} players parsed
          </span>
        )}
      </div>
      {rows.length > 0 && (
        <>
          <div className="scroll-x mt-4" style={{ maxHeight: 220, overflowY: "auto" }}>
            <table className="chalk-table">
              <thead>
                <tr>
                  <th className="num">Rank</th>
                  <th>Player</th>
                  <th>Pos</th>
                  <th>Team</th>
                  <th className="num">Bye</th>
                  <th>Tier</th>
                </tr>
              </thead>
              <tbody>
                {rows.slice(0, 12).map((r) => (
                  <tr key={`${r.rank}-${r.player}`}>
                    <td className="num">{r.rank}</td>
                    <td>{r.player}</td>
                    <td>{r.posRank ?? r.pos ?? ""}</td>
                    <td>{r.team ?? ""}</td>
                    <td className="num">{r.bye ?? ""}</td>
                    <td>{r.tier ?? ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {rows.length > 12 && (
              <div className="py-2 text-sm" style={{ color: "var(--ink-faint)" }}>
                …and {rows.length - 12} more
              </div>
            )}
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <input
              className="chalk-input"
              type="password"
              placeholder="Upload key"
              value={key}
              onChange={(e) => setKey(e.target.value)}
            />
            <button className="chalk-btn" disabled={busy || !key || rows.length === 0} onClick={upload}>
              {busy ? "Chalking it up…" : `Publish ${rows.length} players`}
            </button>
          </div>
        </>
      )}
      {message && (
        <p className="mt-3" style={{ color: message.ok ? CHALK.green : CHALK.pink }}>
          {message.text}
        </p>
      )}
    </ChalkCard>
  );
}
