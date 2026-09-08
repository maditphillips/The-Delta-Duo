// Build the Weekly Data vs. Vibes boards.
//
//   node scripts/build-weekly.mjs
//
// Reads data/weekly/<season>/week-<NN>/{qb,rb,wr,te,k}.csv — one CSV per
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
const POSITIONS = ["qb", "rb", "wr", "te", "k"];

// A position may ship one list (k.csv) or several scoring variants
// (qb-4pt.csv, qb-6pt.csv, rb-ppr.csv, rb-half.csv...). Variants are keyed by
// the filename suffix and shown as a second row of buttons; a position with a
// single file behaves exactly as before.
const VARIANT_LABELS = { "4pt": "4-PT TD", "6pt": "6-PT TD", ppr: "PPR", half: "HALF-PPR" };
const VARIANT_ORDER = ["ppr", "half", "4pt", "6pt"];

function variantFiles(dir, pos) {
  const plain = path.join(dir, `${pos}.csv`);
  if (fs.existsSync(plain)) return [[null, plain]];
  const found = fs
    .readdirSync(dir)
    .map((f) => f.match(new RegExp(`^${pos}-(.+)\\.csv$`)))
    .filter(Boolean)
    .map((m) => [m[1], path.join(dir, m[0])]);
  found.sort((a, b) => VARIANT_ORDER.indexOf(a[0]) - VARIANT_ORDER.indexOf(b[0]));
  return found;
}

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
    const variants = {};
    for (const pos of POSITIONS) {
      const files = variantFiles(path.join(SRC, season, weekDir), pos);
      if (!files.length) continue;
      const byVariant = {};
      for (const [variant, file] of files) {
      const rows = parseCsv(fs.readFileSync(file, "utf8")).map((r) => {
        const player = pick(r, ["player", "name"]);
        const rd = Number(pick(r, ["rank_data", "rank_wilson", "wilson", "data"]));
        const rv = Number(pick(r, ["rank_vibes", "rank_mc", "mc", "vibes"]));
        return player && Number.isFinite(rd) && Number.isFinite(rv)
          ? {
              player,
              team: pick(r, ["team", "tm"]),
              opponent: pick(r, ["opponent", "opp"]),
              isHome: pick(r, ["is_home", "home"]) === "1",
              // pick() returns null when the column is absent, and Number(null)
              // is 0 -- which would give every kicker a 0.0 projection.
              proj: (() => {
                const raw = pick(r, ["proj", "points", "projection"]);
                return raw != null && Number.isFinite(Number(raw)) ? Number(raw) : null;
              })(),
              rankData: rd,
              rankVibes: rv,
              noteData: pick(r, ["note_data", "note_wilson", "wilson_note"]),
              noteVibes: pick(r, ["note_vibes", "note_mc", "mc_note"]),
            }
          : null;
      }).filter(Boolean);
      if (!rows.length) continue;
      rows.sort((a, b) => a.rankData - b.rankData);
      const label = variant ? VARIANT_LABELS[variant] ?? variant.toUpperCase() : null;
      if (label) byVariant[label] = rows;
      if (!positions[pos.toUpperCase()]) positions[pos.toUpperCase()] = rows;
      }
      if (Object.keys(byVariant).length > 1) variants[pos.toUpperCase()] = byVariant;
    }
    if (Object.keys(positions).length === 0) continue;
    const key = `${season}-w${String(week).padStart(2, "0")}`;
    const payload = { season: Number(season), week, label, positions };
    if (Object.keys(variants).length) payload.variants = variants;
    fs.writeFileSync(path.join(OUT, `weekly-${key}.json`), JSON.stringify(payload));
    index.push({ key, season: Number(season), week, label, positions: Object.keys(positions) });
    console.log(`${key} (${label}): ${Object.keys(positions).join(", ")}`);
  }
}
index.sort((a, b) => a.season - b.season || a.week - b.week);
fs.writeFileSync(path.join(OUT, "weekly-index.json"), JSON.stringify({ weeks: index }));
console.log(`index: ${index.length} week(s)`);
