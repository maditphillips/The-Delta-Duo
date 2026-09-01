// Convert the committed ranking CSVs (data/rankings/*.csv) into the JSON the
// rankings page ships with. Run after updating a CSV:
//
//   node scripts/build-rankings.mjs
//
// CSV columns: overall_rank, player, pos, pos_rank, team, bye, tier, delta_note

import fs from "node:fs";
import path from "node:path";

const SRC = path.join(process.cwd(), "data", "rankings");
const OUT = path.join(process.cwd(), "public", "data");

const FORMATS = {
  ppr: { file: "ppr.csv", label: "PPR (1QB)" },
  halfppr: { file: "halfppr.csv", label: "Half PPR (1QB)" },
  superflex: { file: "superflex.csv", label: "Superflex (PPR)" },
};

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

fs.mkdirSync(OUT, { recursive: true });
for (const [key, cfg] of Object.entries(FORMATS)) {
  const csv = fs.readFileSync(path.join(SRC, cfg.file), "utf8");
  const rows = parseCsv(csv).map((r) => ({
    rank: Number(r.overall_rank),
    player: r.player,
    pos: r.pos,
    posRank: r.pos_rank || null,
    team: r.team || null,
    bye: r.bye ? Number(r.bye) : null,
    tier: r.tier || null,
    note: r.delta_note || null,
  }));
  rows.sort((a, b) => a.rank - b.rank);
  const out = { format: key, label: cfg.label, updated: new Date().toISOString().slice(0, 10), rows };
  fs.writeFileSync(path.join(OUT, `rankings-${key}.json`), JSON.stringify(out));
  console.log(`${key}: ${rows.length} players`);
}
