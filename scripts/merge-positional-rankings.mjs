// Merge updated positional ranking lists into the format boards.
//
//   node scripts/merge-positional-rankings.mjs
//
// Reads:
//   data/rankings/positions/{qb,rb,wr,te}.csv  — new positional orders
//     (Rank, Tier, Player, Position, Team, Flag, Note)
//   data/rankings/{ppr,halfppr,superflex}.csv  — current boards, used as
//     (a) the cross-position slot template per format,
//     (b) the source of carried-over delta notes and team→bye mapping.
// Writes:
//   data/rankings/{ppr,halfppr,superflex}.csv  — rebuilt boards
//
// Rules:
//   - Each format keeps its existing interleave: the i-th POS slot in the old
//     board is refilled with the i-th player of the new POS list. Players
//     beyond the old slot count are appended at the tail, ordered by mapped
//     tier then positional depth.
//   - Tiers map ordinally per position: 1st distinct tier → Elite, 2nd →
//     Tier 1, 3rd → Tier 2, and so on.
//   - Delta notes carry over by (position, normalized player name), except
//     notes listed in DROPPED_NOTES (they contradict the new order).
//   - Byes come from the old boards' team→bye map, keyed by the NEW team.
// Then run: node scripts/build-rankings.mjs

import fs from "node:fs";
import path from "node:path";

const DIR = path.join(process.cwd(), "data", "rankings");
const POS_DIR = path.join(DIR, "positions");
const FORMATS = ["ppr", "halfppr", "superflex"];
const POSITIONS = ["QB", "RB", "WR", "TE"];

// Notes that contradict the new positional order — dropped pending rewrites.
const DROPPED_NOTES = new Set([
  "TE|trey mcbride", // said "TE1 and it is not close"; Bowers is now TE1
  "RB|derrick henry", // said "we fade to RB13"; he is now RB6
  "WR|alec pierce", // said model WR19 buy; he is now WR81
  "WR|tre tucker", // said target-share riser; he is now WR101 with a Faller flag
  "WR|rashee rice", // bullish buy case; he is now WR35 with an Avoid flag
]);

function parseCsv(text) {
  const rows = [];
  let row = [], field = "", inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; }
        else inQuotes = false;
      } else field += c;
    } else if (c === '"') inQuotes = true;
    else if (c === ",") { row.push(field); field = ""; }
    else if (c === "\n") { row.push(field); rows.push(row); row = []; field = ""; }
    else if (c !== "\r") field += c;
  }
  if (field !== "" || row.length) { row.push(field); rows.push(row); }
  const header = rows[0].map((h) => h.trim());
  return rows.slice(1).filter((r) => r.length === header.length && r.some((v) => v !== "")).map((r) => {
    const o = {};
    for (let j = 0; j < header.length; j++) o[header[j]] = r[j].trim();
    return o;
  });
}

const csvField = (v) => {
  const s = v == null ? "" : String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};

const norm = (name) =>
  name
    .toLowerCase()
    .replace(/[’']/g, "")
    .replace(/[.’]/g, "")
    .replace(/\s+(jr|sr|ii|iii|iv)\.?$/i, "")
    .replace(/^nicholas /, "nick ")
    .replace(/\s+/g, " ")
    .trim();

// ————— load new positional lists —————
// Base lists live in data/rankings/positions/{pos}.csv (PPR order, also used
// for Superflex). A format can override any position with its own list at
// data/rankings/positions/{format}/{pos}.csv — e.g. positions/halfppr/wr.csv
// reorders only the Half PPR receivers.
function loadList(file) {
  const rows = parseCsv(fs.readFileSync(file, "utf8"));
  const tierOrder = [];
  for (const r of rows) if (!tierOrder.includes(r.Tier)) tierOrder.push(r.Tier);
  const list = rows.map((r) => {
    const tierIdx = tierOrder.indexOf(r.Tier);
    return {
      rank: Number(r.Rank),
      tierIdx,
      tier: tierIdx === 0 ? "Elite" : `Tier ${tierIdx}`,
      player: r.Player,
      team: r.Team || null,
      flag: r.Flag || null,
      csvNote: r.Note || null,
    };
  });
  list.sort((a, b) => a.rank - b.rank);
  return list;
}

const baseLists = {};
for (const pos of POSITIONS) {
  baseLists[pos] = loadList(path.join(POS_DIR, `${pos.toLowerCase()}.csv`));
}

function listsForFormat(format) {
  const lists = {};
  for (const pos of POSITIONS) {
    const override = path.join(POS_DIR, format, `${pos.toLowerCase()}.csv`);
    if (fs.existsSync(override)) {
      lists[pos] = loadList(override);
      console.log(`${format}: using override for ${pos} (${lists[pos].length} players)`);
    } else {
      lists[pos] = baseLists[pos];
    }
  }
  return lists;
}
const newLists = baseLists; // used for the adds/drops report below

// ————— load old boards —————
const oldBoards = {};
for (const f of FORMATS) {
  oldBoards[f] = parseCsv(fs.readFileSync(path.join(DIR, `${f}.csv`), "utf8"));
}

// team → bye map from the old boards
const teamBye = new Map();
for (const f of FORMATS) {
  for (const r of oldBoards[f]) {
    if (r.team && r.bye) teamBye.set(r.team, Number(r.bye));
  }
}

// notes per format: pos|normname -> note
const oldNotes = {};
for (const f of FORMATS) {
  oldNotes[f] = new Map();
  for (const r of oldBoards[f]) {
    if (r.delta_note) oldNotes[f].set(`${r.pos}|${norm(r.player)}`, r.delta_note);
  }
}

// track adds/drops for the report
const oldPlayers = new Set();
for (const r of oldBoards.ppr) oldPlayers.add(`${r.pos}|${norm(r.player)}`);
const newPlayers = new Set();
for (const pos of POSITIONS) for (const p of newLists[pos]) newPlayers.add(`${pos}|${norm(p.player)}`);
const dropped = [...oldPlayers].filter((k) => !newPlayers.has(k));
const added = [...newPlayers].filter((k) => !oldPlayers.has(k));

// ————— rebuild each format —————
for (const f of FORMATS) {
  const formatLists = listsForFormat(f);
  const template = oldBoards[f].map((r) => r.pos); // slot sequence
  const queues = {};
  for (const pos of POSITIONS) queues[pos] = [...formatLists[pos]];

  const filled = [];
  for (const pos of template) {
    const next = queues[pos]?.shift();
    if (next) filled.push({ pos, ...next });
    // if a position ran out of players, the slot is dropped
  }
  // leftovers → tail, ordered by tier depth then relative positional depth
  const leftovers = [];
  for (const pos of POSITIONS) {
    const total = formatLists[pos].length;
    for (const p of queues[pos]) leftovers.push({ pos, depth: p.rank / total, ...p });
  }
  leftovers.sort((a, b) => a.tierIdx - b.tierIdx || a.depth - b.depth || a.rank - b.rank);
  const board = [...filled, ...leftovers];

  const posCounters = {};
  const lines = ["overall_rank,player,pos,pos_rank,team,bye,tier,delta_note,flag"];
  board.forEach((p, i) => {
    posCounters[p.pos] = (posCounters[p.pos] ?? 0) + 1;
    const key = `${p.pos}|${norm(p.player)}`;
    const note = DROPPED_NOTES.has(key) ? (p.csvNote ?? "") : (p.csvNote || oldNotes[f].get(key) || "");
    lines.push(
      [
        i + 1,
        csvField(p.player),
        p.pos,
        `${p.pos}${posCounters[p.pos]}`,
        p.team ?? "",
        p.team && teamBye.has(p.team) ? teamBye.get(p.team) : "",
        p.tier,
        csvField(note),
        p.flag ?? "",
      ].join(",")
    );
  });
  fs.writeFileSync(path.join(DIR, `${f}.csv`), lines.join("\n") + "\n");
  console.log(`${f}: ${board.length} players (${board.length - filled.length} appended at tail)`);
}

console.log(`\nDropped from the boards (${dropped.length}):`, dropped.map((k) => k.split("|")[1]).join(", "));
console.log(`\nNew to the boards (${added.length}):`, added.map((k) => k.split("|")[1]).join(", "));
console.log(`\nNotes dropped as contradictory (need rewrites): ${[...DROPPED_NOTES].map((k) => k.split("|")[1]).join(", ")}`);
