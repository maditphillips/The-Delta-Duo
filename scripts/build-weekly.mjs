// Build the Weekly Data vs. Vibes boards.
//
//   node scripts/build-weekly.mjs
//
// Reads data/weekly/<season>/week-<NN>/{qb,rb,wr,te}.csv — one CSV per
// position per week, with both lists in one file:
//
//   rank_data,rank_vibes,player,team,note_data,note_vibes
//
// (headers matched loosely: rank_wilson/wilson → rank_data, rank_mc/mc →
// rank_vibes, note_wilson → note_data, note_mc → note_vibes). Missing
// positions are simply skipped for that week.
//
// Writes public/data/weekly-index.json (the week list) and one
// public/data/weekly-<season>-w<NN>.json per week.

import fs from "node:fs";
import path from "node:path";

const SRC = path.join(process.cwd(), "data", "weekly");
const OUT = path.join(process.cwd(), "public", "data");
const POSITIONS = ["qb", "rb", "wr", "te"];

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
  const header = rows[0].map((h) => h.trim().toLowerCase());
  return rows.slice(1).filter((r) => r.length === header.length && r.some((v) => v !== "")).map((r) => {
    const o = {};
    for (let j = 0; j < header.length; j++) o[header[j]] = r[j].trim();
    return o;
  });
}

const pick = (rec, keys) => {
  for (const k of keys) if (rec[k] != null && rec[k] !== "") return rec[k];
  return null;
};

if (!fs.existsSync(SRC)) {
  console.log("no data/weekly directory — nothing to build");
  process.exit(0);
}

fs.mkdirSync(OUT, { recursive: true });
const index = [];
for (const season of fs.readdirSync(SRC).filter((d) => /^\d{4}$/.test(d)).sort()) {
  for (const weekDir of fs.readdirSync(path.join(SRC, season)).filter((d) => /^week-\d+/.test(d)).sort()) {
    const week = Number(weekDir.match(/week-(\d+)/)[1]);
    const label = fs.existsSync(path.join(SRC, season, weekDir, "LABEL.txt"))
      ? fs.readFileSync(path.join(SRC, season, weekDir, "LABEL.txt"), "utf8").trim()
      : `Week ${week}`;
    const positions = {};
    for (const pos of POSITIONS) {
      const file = path.join(SRC, season, weekDir, `${pos}.csv`);
      if (!fs.existsSync(file)) continue;
      const rows = parseCsv(fs.readFileSync(file, "utf8")).map((r) => {
        const player = pick(r, ["player", "name"]);
        const rd = Number(pick(r, ["rank_data", "rank_wilson", "wilson", "data"]));
        const rv = Number(pick(r, ["rank_vibes", "rank_mc", "mc", "vibes"]));
        return player && Number.isFinite(rd) && Number.isFinite(rv)
          ? {
              player,
              team: pick(r, ["team", "tm"]),
              rankData: rd,
              rankVibes: rv,
              noteData: pick(r, ["note_data", "note_wilson", "wilson_note"]),
              noteVibes: pick(r, ["note_vibes", "note_mc", "mc_note"]),
            }
          : null;
      }).filter(Boolean);
      if (rows.length) positions[pos.toUpperCase()] = rows.sort((a, b) => a.rankData - b.rankData);
    }
    if (Object.keys(positions).length === 0) continue;
    const key = `${season}-w${String(week).padStart(2, "0")}`;
    fs.writeFileSync(path.join(OUT, `weekly-${key}.json`), JSON.stringify({ season: Number(season), week, label, positions }));
    index.push({ key, season: Number(season), week, label, positions: Object.keys(positions) });
    console.log(`${key} (${label}): ${Object.keys(positions).join(", ")}`);
  }
}
index.sort((a, b) => a.season - b.season || a.week - b.week);
fs.writeFileSync(path.join(OUT, "weekly-index.json"), JSON.stringify({ weeks: index }));
console.log(`index: ${index.length} week(s)`);
