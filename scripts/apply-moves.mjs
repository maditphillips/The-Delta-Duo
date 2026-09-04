// Apply hand-ordered moves to the format boards.
//
//   node scripts/apply-moves.mjs data/rankings/adjustments/<file>.json
//
// The spec is a list of ops applied in order:
//   { "op": "swap",      "a": "Player A", "b": "Player B", "formats": ["ppr", ...] }
//   { "op": "moveToSpot","player": "P", "spot": 23,        "formats": [...] }
//   { "op": "moveBelow", "player": "P", "below": ["X","Y"],"formats": [...] }
//   { "op": "set",       "player": "P", "note": "...", "flag": "...", "tier": "...", "formats": [...] }
// Rows keep their tier/flag/note unless a "set" op changes them; overall_rank
// and pos_rank are recomputed.

import fs from "node:fs";
import path from "node:path";

const specPath = process.argv[2];
if (!specPath) {
  console.error("usage: node scripts/apply-moves.mjs <spec.json>");
  process.exit(1);
}
const spec = JSON.parse(fs.readFileSync(specPath, "utf8"));
const DIR = path.join(process.cwd(), "data", "rankings");

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
    for (let j = 0; j < header.length; j++) o[header[j]] = r[j];
    return o;
  });
}
const csvField = (v) => {
  const s = v == null ? "" : String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};

const idx = (rows, player) => {
  const i = rows.findIndex((r) => r.player === player);
  if (i < 0) throw new Error(`player not found: ${player}`);
  return i;
};

for (const format of ["ppr", "halfppr", "superflex"]) {
  const file = path.join(DIR, `${format}.csv`);
  const rows = parseCsv(fs.readFileSync(file, "utf8"));

  for (const op of spec) {
    if (!op.formats.includes(format)) continue;
    if (op.op === "swap") {
      const ia = idx(rows, op.a), ib = idx(rows, op.b);
      [rows[ia], rows[ib]] = [rows[ib], rows[ia]];
      console.log(`${format}: swapped ${op.a} (now #${ib + 1}) and ${op.b} (now #${ia + 1})`);
    } else if (op.op === "moveToSpot") {
      const i = idx(rows, op.player);
      const [r] = rows.splice(i, 1);
      rows.splice(op.spot - 1, 0, r);
      console.log(`${format}: moved ${op.player} to #${op.spot}`);
    } else if (op.op === "moveBelow") {
      const i = idx(rows, op.player);
      const [r] = rows.splice(i, 1);
      const target = Math.max(...op.below.map((p) => idx(rows, p)));
      rows.splice(target + 1, 0, r);
      console.log(`${format}: moved ${op.player} below ${op.below.join(" & ")} (now #${target + 2})`);
    } else if (op.op === "set") {
      const r = rows[idx(rows, op.player)];
      if (op.note !== undefined) r.delta_note = op.note;
      if (op.flag !== undefined) r.flag = op.flag;
      if (op.tier !== undefined) r.tier = op.tier;
      console.log(`${format}: updated ${op.player} (${[op.note !== undefined && "note", op.flag !== undefined && "flag", op.tier !== undefined && "tier"].filter(Boolean).join(", ")})`);
    } else {
      throw new Error(`unknown op: ${op.op}`);
    }
  }

  // recompute overall_rank and pos_rank
  const posCounters = {};
  rows.forEach((r, i) => {
    r.overall_rank = `${i + 1}`;
    posCounters[r.pos] = (posCounters[r.pos] ?? 0) + 1;
    r.pos_rank = `${r.pos}${posCounters[r.pos]}`;
  });

  const header = "overall_rank,player,pos,pos_rank,team,bye,tier,delta_note,flag";
  const lines = [header, ...rows.map((r) =>
    [r.overall_rank, csvField(r.player), r.pos, r.pos_rank, r.team, r.bye, r.tier, csvField(r.delta_note), r.flag].join(",")
  )];
  fs.writeFileSync(file, lines.join("\n") + "\n");
}
console.log("done — run: node scripts/build-rankings.mjs");
