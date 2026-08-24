"use client";

import { useEffect, useMemo, useState } from "react";
import Papa from "papaparse";
import ChalkCard from "@/components/ChalkCard";
import { CHALK } from "@/components/charts/theme";
import { SCOPES, normalizeCsvRows, scopeLabels, type RankingRow, type RankingSet, type Scope } from "@/lib/rankings";

type LoadState =
  | { status: "loading" }
  | { status: "unconfigured"; hint?: string }
  | { status: "error"; message: string }
  | { status: "ready"; set: RankingSet | null };

async function fetchBoard(scope: Scope): Promise<LoadState> {
  try {
    const res = await fetch(`/api/rankings?scope=${scope}`);
    const json = await res.json();
    if (res.status === 503) return { status: "unconfigured", hint: json.hint };
    if (!res.ok) return { status: "error", message: json.error ?? `HTTP ${res.status}` };
    return { status: "ready", set: json.set };
  } catch (e) {
    return { status: "error", message: e instanceof Error ? e.message : "network error" };
  }
}

export default function RankingsBoard() {
  const [scope, setScope] = useState<Scope>("overall");
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [showUpload, setShowUpload] = useState(false);
  const [filter, setFilter] = useState("");

  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    let cancelled = false;
    fetchBoard(scope).then((next) => {
      if (!cancelled) setState(next);
    });
    return () => {
      cancelled = true;
    };
  }, [scope, refresh]);

  const rows = useMemo(() => {
    if (state.status !== "ready" || !state.set) return [];
    const q = filter.trim().toLowerCase();
    if (!q) return state.set.rows;
    return state.set.rows.filter(
      (r) =>
        r.player.toLowerCase().includes(q) ||
        (r.team ?? "").toLowerCase().includes(q) ||
        (r.position ?? "").toLowerCase().includes(q)
    );
  }, [state, filter]);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center gap-2">
        {SCOPES.map((s) => (
          <button
            key={s}
            className={`chalk-btn ${scope === s ? "selected" : ""}`}
            onClick={() => {
              setScope(s);
              setState({ status: "loading" });
            }}
          >
            {scopeLabels[s]}
          </button>
        ))}
        <span className="grow" />
        <button className="chalk-btn" onClick={() => setShowUpload((v) => !v)}>
          {showUpload ? "Hide upload" : "✏️ Upload rankings"}
        </button>
      </div>

      {showUpload && <UploadPanel scope={scope} onUploaded={() => setRefresh((r) => r + 1)} />}

      {state.status === "loading" && (
        <div className="py-14 text-center text-xl" style={{ color: "var(--ink-dim)" }}>
          Chalking up the board…
        </div>
      )}

      {state.status === "unconfigured" && (
        <ChalkCard title="Supabase isn't connected yet" alt>
          <p style={{ color: "var(--ink-dim)" }}>
            Rankings are stored in Supabase so they can be updated without redeploying the site. To turn this on:
          </p>
          <ol className="mt-3 flex list-decimal flex-col gap-2 pl-6" style={{ color: "var(--ink-dim)" }}>
            <li>Create a free project at supabase.com.</li>
            <li>
              Run the SQL in <code>supabase/migrations/0001_rankings.sql</code> (in this repo) in the Supabase SQL editor.
            </li>
            <li>
              Set <code>NEXT_PUBLIC_SUPABASE_URL</code>, <code>NEXT_PUBLIC_SUPABASE_ANON_KEY</code>,{" "}
              <code>SUPABASE_SERVICE_ROLE_KEY</code>, and <code>RANKINGS_UPLOAD_KEY</code> (any passphrase you choose) in your
              Cloudflare project settings, then redeploy once.
            </li>
          </ol>
          {state.hint && (
            <p className="mt-3 text-sm" style={{ color: "var(--ink-faint)" }}>
              {state.hint}
            </p>
          )}
        </ChalkCard>
      )}

      {state.status === "error" && (
        <ChalkCard title="Couldn't load the board" alt>
          <p style={{ color: CHALK.salmon }}>{state.message}</p>
        </ChalkCard>
      )}

      {state.status === "ready" && !state.set && (
        <ChalkCard title={`No ${scopeLabels[scope]} rankings yet`} alt>
          <p style={{ color: "var(--ink-dim)" }}>
            Nothing on the board for this scope. Hit “Upload rankings” above to chalk up the first set — a CSV with columns like{" "}
            <code>rank, player, team, position, note</code> (only <code>player</code> is required; row order stands in for rank).
          </p>
        </ChalkCard>
      )}

      {state.status === "ready" && state.set && (
        <ChalkCard
          title={`${scopeLabels[scope]} board`}
          note={`Uploaded ${new Date(state.set.created_at).toLocaleString()}${state.set.filename ? ` · ${state.set.filename}` : ""} · ${state.set.rows.length} players`}
        >
          <input
            className="chalk-input mb-4 w-full max-w-sm"
            placeholder="Find a player, team, or position…"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
          <div className="scroll-x" style={{ maxHeight: 560, overflowY: "auto" }}>
            <table className="chalk-table">
              <thead>
                <tr>
                  <th className="num">Rank</th>
                  <th>Player</th>
                  <th>Team</th>
                  <th>Pos</th>
                  <th>Note</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={`${r.rank}-${r.player}`}>
                    <td className="num font-display text-xl" style={{ color: r.rank <= 12 ? CHALK.yellow : "var(--ink)" }}>
                      {r.rank}
                    </td>
                    <td>{r.player}</td>
                    <td>{r.team ?? ""}</td>
                    <td>{r.position ?? ""}</td>
                    <td style={{ color: "var(--ink-dim)" }}>{r.note ?? ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </ChalkCard>
      )}
    </div>
  );
}

function UploadPanel({ scope, onUploaded }: { scope: Scope; onUploaded: () => void }) {
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
          setMessage({ ok: false, text: "No usable rows found — the CSV needs at least a player/name column." });
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
        body: JSON.stringify({ scope, filename, rows }),
      });
      const json = await res.json();
      if (!res.ok) {
        setMessage({ ok: false, text: json.hint ? `${json.error} — ${json.hint}` : (json.error ?? `HTTP ${res.status}`) });
      } else {
        setMessage({ ok: true, text: `Board updated — ${json.rows} players on the ${scopeLabels[scope]} board.` });
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
    <ChalkCard title={`Upload ${scopeLabels[scope]} rankings`} alt>
      <p className="mb-4 text-sm" style={{ color: "var(--ink-dim)" }}>
        CSV with columns like <code>rank, player, team, position, note</code> — headers are matched loosely and only{" "}
        <code>player</code> is required. Each upload replaces the live board for this scope (history is kept in Supabase).
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
        {filename && <span style={{ color: "var(--ink-dim)" }}>{filename} · {rows.length} players parsed</span>}
      </div>
      {rows.length > 0 && (
        <>
          <div className="scroll-x mt-4" style={{ maxHeight: 220, overflowY: "auto" }}>
            <table className="chalk-table">
              <thead>
                <tr>
                  <th className="num">Rank</th>
                  <th>Player</th>
                  <th>Team</th>
                  <th>Pos</th>
                  <th>Note</th>
                </tr>
              </thead>
              <tbody>
                {rows.slice(0, 15).map((r) => (
                  <tr key={`${r.rank}-${r.player}`}>
                    <td className="num">{r.rank}</td>
                    <td>{r.player}</td>
                    <td>{r.team ?? ""}</td>
                    <td>{r.position ?? ""}</td>
                    <td style={{ color: "var(--ink-dim)" }}>{r.note ?? ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {rows.length > 15 && (
              <div className="py-2 text-sm" style={{ color: "var(--ink-faint)" }}>
                …and {rows.length - 15} more
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
        <p className="mt-3" style={{ color: message.ok ? CHALK.green : CHALK.salmon }}>
          {message.text}
        </p>
      )}
    </ChalkCard>
  );
}
