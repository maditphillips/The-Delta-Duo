"use client";

import { useEffect, useMemo, useState } from "react";
import ChalkCard from "@/components/ChalkCard";
import {
  MC_COLOR,
  WILSON_COLOR,
  type WeeklyBoard as Board,
  type WeeklyIndex,
  type WeeklyRow,
} from "@/lib/weekly";
import {
  BASES,
  NEEDS,
  initials,
  photoUrl,
  pointsOn,
  rowsFor,
  toPick,
  verdicts,
  type Basis,
  type Need,
  type Pick,
} from "@/lib/startSit";

/** The pink reads hot against the green board, so the player card takes a
 *  slightly deeper, slightly less neon version of it. */
const WILSON_ON_CHALK = "#ef4b9f";
const CHOSEN = "var(--accent-gold)";

type Entry = { pos: string; row: WeeklyRow; key: string };

const btn = (on: boolean) =>
  `chalk-tab${on ? " active" : ""} whitespace-nowrap text-xs sm:text-sm`;

/** A two-line choice: the short name, then what it actually asks. */
function Choice({ on, tag, label, onClick }: {
  on: boolean; tag: string; label: string; onClick: () => void;
}) {
  return (
    <button onClick={onClick} className={`chalk-tab${on ? " active" : ""} text-left`}
            style={{ padding: "8px 14px", lineHeight: 1.25 }}>
      <span className="block text-sm font-semibold sm:text-base">{tag}</span>
      <span className="block text-xs sm:text-sm" style={{ color: "var(--ink-dim)" }}>{label}</span>
    </button>
  );
}

function Face({ row, size = 52 }: { row: WeeklyRow; size?: number }) {
  const [failed, setFailed] = useState(false);
  const src = photoUrl(row.photo);
  const box = {
    width: size,
    height: size,
    borderRadius: "50%",
    border: "1px solid var(--ink-ghost)",
    background: "var(--paper-2, rgba(255,255,255,0.04))",
    flexShrink: 0,
  } as const;
  // Sleeper has no headshot for some players and simply 404s; an initials
  // circle keeps the row the same shape either way.
  if (!src || failed)
    return (
      <div
        style={{ ...box, display: "grid", placeItems: "center", color: "var(--ink-faint)",
                 fontSize: size * 0.32 }}
      >
        {initials(row.player)}
      </div>
    );
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt=""
      loading="lazy"
      onError={() => setFailed(true)}
      style={{ ...box, objectFit: "cover", objectPosition: "top center" }}
    />
  );
}

function Slot({
  label,
  pick,
  entries,
  onPick,
  onClear,
}: {
  label: string;
  pick: Pick | null;
  entries: Entry[];
  onPick: (e: Entry) => void;
  onClear: () => void;
}) {
  const [q, setQ] = useState("");
  const matches = useMemo(() => {
    const t = q.trim().toLowerCase();
    if (t.length < 2) return [];
    return entries
      .filter(
        (e) =>
          e.row.player.toLowerCase().includes(t) ||
          (e.row.team ?? "").toLowerCase().includes(t)
      )
      .slice(0, 8);
  }, [q, entries]);

  if (pick) {
    const r = pick.row;
    return (
      <div className="chalk-inset px-4 py-3">
        <div className="chalk-kicker mb-2">{label}</div>
        <div className="flex items-center gap-3">
          <Face row={r} />
          <div className="min-w-0 flex-1">
            <div className="truncate" style={{ color: "var(--ink)" }}>
              {r.player}
            </div>
            <div className="text-xs" style={{ color: "var(--ink-dim)" }}>
              {pick.pos} · {r.team}
              {r.opponent ? ` ${r.isHome ? "vs." : "@"} ${r.opponent}` : ""}
            </div>
            <div className="mt-1 flex flex-wrap gap-x-3 text-xs">
              <span style={{ color: WILSON_COLOR }}>
                Wilson {pick.pos}
                {r.rankData}
              </span>
              <span style={{ color: MC_COLOR }}>
                MC {pick.pos}
                {r.rankVibes}
              </span>
            </div>
          </div>
          <button
            onClick={() => { setQ(""); onClear(); }}
            className="chalk-tab text-xs"
          >
            Change
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="chalk-inset px-4 py-3">
      <div className="chalk-kicker mb-2">{label}</div>
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Type a player's name"
        className="w-full rounded border px-3 py-2 text-sm"
        style={{ background: "transparent", borderColor: "var(--ink-ghost)", color: "var(--ink)" }}
      />
      {matches.length > 0 && (
        <ul className="mt-2 space-y-1">
          {matches.map((e) => (
            <li key={e.key}>
              <button
                onClick={() => { setQ(""); onPick(e); }}
                className="flex w-full items-center gap-2 rounded px-2 py-1 text-left text-sm hover:opacity-80"
                style={{ color: "var(--ink)" }}
              >
                <Face row={e.row} size={26} />
                <span className="truncate">{e.row.player}</span>
                <span className="ml-auto text-xs" style={{ color: "var(--ink-faint)" }}>
                  {e.pos} · {e.row.team}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {q.trim().length >= 2 && matches.length === 0 && (
        <p className="mt-2 text-xs" style={{ color: "var(--ink-faint)" }}>
          Nobody by that name in this week&apos;s lists.
        </p>
      )}
    </div>
  );
}

/**
 * Two players in, one decision out -- and the three other decisions it could
 * have been, because "who is better" and "who do I need this week" are not the
 * same question. The chosen need is promoted to the headline; the rest stay
 * visible underneath, since when they disagree that disagreement *is* the
 * answer.
 */
export default function StartSit() {
  const [board, setBoard] = useState<Board | null>(null);
  const [ppr, setPpr] = useState(true);
  const [sixPt, setSixPt] = useState(false);
  const [need, setNeed] = useState<Need>("call");
  const [basis, setBasis] = useState<Basis>("blend");
  const [chosen, setChosen] = useState<(Entry | null)[]>([null, null]);

  useEffect(() => {
    let off = false;
    (async () => {
      try {
        const idx: WeeklyIndex = await (await fetch("/data/weekly-index.json")).json();
        const latest = idx.weeks[idx.weeks.length - 1];
        if (!latest) return;
        const b: Board = await (await fetch(`/data/weekly-${latest.key}.json`)).json();
        if (!off) setBoard(b);
      } catch {
        /* the page renders its empty state rather than throwing */
      }
    })();
    return () => { off = true; };
  }, []);

  // A QB list is scored on passing touchdowns and everyone else on receptions,
  // so the two toggles are independent and the QB one only appears when a
  // quarterback is actually in the comparison.
  const scoringFor = (pos: string) =>
    pos === "QB" ? (sixPt ? "6-PT TD" : "4-PT TD") : ppr ? "PPR" : "HALF-PPR";

  const entries = useMemo(() => {
    if (!board) return [];
    const out: Entry[] = [];
    for (const pos of Object.keys(board.positions))
      for (const row of rowsFor(board, pos, scoringFor(pos)))
        out.push({ pos, row, key: `${pos}-${row.player}` });
    return out;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [board, ppr, sixPt]);

  // Re-resolve each pick against the current scoring rather than holding a
  // stale row: flipping PPR to half-PPR must change the numbers on screen.
  const picks = useMemo(() => {
    if (!board) return [];
    return chosen
      .map((c) => {
        if (!c) return null;
        const rows = rowsFor(board, c.pos, scoringFor(c.pos));
        const row = rows.find((r) => r.player === c.row.player);
        return row ? toPick(c.pos, rows, row) : null;
      })
      .filter((p): p is Pick => p != null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [board, chosen, ppr, sixPt]);

  const hasQb = chosen.some((c) => c?.pos === "QB");
  const answers = useMemo(
    () => (picks.length === 2 ? verdicts(picks, basis) : []),
    [picks, basis]
  );
  const active = NEEDS.find((n) => n.key === need)!;
  const chosenBasis = BASES.find((b) => b.key === basis)!;
  const headline = answers.find((a) => a.need === need);
  const rest = answers.filter((a) => a.need !== need);

  const set = (i: number, e: Entry | null) =>
    setChosen((c) => c.map((x, j) => (j === i ? e : x)));

  return (
    <div className="flex flex-col gap-5">
      <div>
        <div className="chalk-kicker mb-2 text-sm sm:text-base">What do you need?</div>
        <div className="flex flex-wrap gap-2">
          {NEEDS.map((n) => (
            <Choice key={n.key} on={need === n.key} tag={n.tag} label={n.label}
                    onClick={() => setNeed(n.key)} />
          ))}
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {[0, 1].map((i) => (
          <Slot
            key={i}
            label={i === 0 ? "Player A" : "Player B"}
            pick={picks.length === 2 ? picks[i] : chosen[i] && board
              ? toPick(chosen[i]!.pos,
                       rowsFor(board, chosen[i]!.pos, scoringFor(chosen[i]!.pos)),
                       chosen[i]!.row)
              : null}
            entries={entries.filter((e) => e.key !== chosen[1 - i]?.key)}
            onPick={(e) => set(i, e)}
            onClear={() => set(i, null)}
          />
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <span className="chalk-kicker">Scoring</span>
        <span className="flex gap-1">
          <button className={btn(ppr)} onClick={() => setPpr(true)}>PPR</button>
          <button className={btn(!ppr)} onClick={() => setPpr(false)}>HALF-PPR</button>
        </span>
        {hasQb && (
          <>
            <span className="chalk-kicker">QB TDs</span>
            <span className="flex gap-1">
              <button className={btn(!sixPt)} onClick={() => setSixPt(false)}>4-PT</button>
              <button className={btn(sixPt)} onClick={() => setSixPt(true)}>6-PT</button>
            </span>
          </>
        )}
      </div>

      <div>
        <div className="chalk-kicker mb-2 text-sm sm:text-base">How should we decide?</div>
        <div className="flex flex-wrap gap-2">
          {BASES.map((b) => (
            <Choice key={b.key} on={basis === b.key} tag={b.tag} label={b.label}
                    onClick={() => setBasis(b.key)} />
          ))}
        </div>
      </div>

      {picks.length < 2 ? (
        <ChalkCard kicker="Start / sit" title="Pick two players">
          <p className="text-sm" style={{ color: "var(--ink-dim)" }}>
            Any two on this week&apos;s boards, at any position. The comparison runs on
            projected points, so a flex call between a back and a receiver works the same
            as two backs.
          </p>
        </ChalkCard>
      ) : (
        <ChalkCard
          kicker={active.tag}
          kickerRight={chosenBasis.tag}
          title={headline?.line ?? ""}
          source="Wilson's projection and MC's rank, priced on the same scale"
        >
          <div className="grid gap-3 sm:grid-cols-2">
            {picks.map((p) => {
              const won = !headline?.tied && headline?.winner === p;
              // The number is boxed on the man it picked, so the box is the
              // answer rather than a pair of numbers to compare. A tie has no
              // winner, so both are boxed: that is the point being made.
              const shows = won || !!headline?.tied;
              const box = (on: boolean) =>
                on && shows
                  ? { outline: `2px solid ${CHOSEN}`, outlineOffset: 2, borderRadius: 4 }
                  : undefined;
              return (
                <div
                  key={p.pos + p.row.player}
                  className="chalk-inset px-4 py-3"
                  style={won ? { outline: `3px solid ${CHOSEN}`, outlineOffset: 2 } : undefined}
                >
                  <div className="flex items-center gap-3">
                    <Face row={p.row} size={44} />
                    <div className="min-w-0">
                      <div className="truncate" style={{ color: "var(--ink)" }}>{p.row.player}</div>
                      <div className="text-xs" style={{ color: "var(--ink-faint)" }}>
                        {p.pos} ·{" "}
                        <strong style={{ color: "var(--ink)", fontWeight: 600 }}>{p.row.team}</strong>
                        {p.row.opponent ? ` ${p.row.isHome ? "vs." : "@"} ${p.row.opponent}` : ""}
                      </div>
                    </div>
                    <div className="ml-auto text-right" style={box(active.stat === "points")}>
                      <div className="font-retro text-xl" style={{ color: "var(--ink)" }}>
                        {pointsOn(p, basis)?.toFixed(1) ?? "n/a"}
                      </div>
                      {/* Not .chalk-kicker: it prefixes a dash, which reads as
                          part of the number once the box is outlined. */}
                      <div className="text-[0.62rem] uppercase tracking-widest"
                           style={{ color: "var(--chalk-gold)" }}>
                        Proj. Pts
                      </div>
                    </div>
                  </div>
                  <div className="mt-2 text-[0.68rem] uppercase tracking-wider"
                       style={{ color: "var(--ink-faint)" }}>
                    Projected points, and his odds of a top-12 week
                  </div>
                  <dl className="mt-1 grid grid-cols-4 gap-1 text-center text-xs">
                    {([
                      ["Floor", p.row.floor?.toFixed(1), "floor"],
                      ["Median", p.row.median?.toFixed(1), "median"],
                      ["Ceiling", p.row.ceiling?.toFixed(1), "ceiling"],
                      ["Top-12", p.row.pTop12 != null ? `${Math.round(p.row.pTop12 * 100)}%` : null, "pTop12"],
                    ] as const).map(([k, v, stat]) => (
                      <div key={k} style={box(active.stat === stat)}>
                        <dt style={{ color: "var(--ink-faint)" }}>{k}</dt>
                        <dd style={{ color: "var(--ink)" }}>{v ?? "n/a"}</dd>
                      </div>
                    ))}
                  </dl>
                  <div className="mt-2 flex gap-3 text-xs">
                    <span style={{ color: WILSON_ON_CHALK }}>
                      Wilson {p.pos}{p.row.rankData} · {p.wilson?.toFixed(1) ?? "n/a"}
                    </span>
                    <span style={{ color: MC_COLOR }}>
                      MC {p.pos}{p.row.rankVibes} · {p.mc?.toFixed(1) ?? "n/a"}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="mt-4 space-y-2">
            {rest.map((a) => (
              <p key={a.need} className="text-sm leading-snug" style={{ color: "var(--ink-dim)" }}>
                <span className="chalk-kicker mr-2">
                  {NEEDS.find((n) => n.key === a.need)?.tag}
                </span>
                {a.line}
              </p>
            ))}
            <p className="pt-1 text-xs" style={{ color: "var(--ink-faint)" }}>
              Ceiling, consistency and the floor are Wilson&apos;s numbers under every
              setting. MC ranks players, he does not model a range of outcomes, so only
              the Simple call changes when you switch to Vibes.
            </p>
          </div>
        </ChalkCard>
      )}
    </div>
  );
}
