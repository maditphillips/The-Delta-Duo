// Build the Buy Low / Sell High boards.
//
//   node scripts/build-buysell.mjs
//
// Reads data/buy-sell/<season>/week-<NN>.csv, written by `python -m dd.cli`
// on the model side, and emits public/data/buysell-<season>-w<NN>.json plus
// an index. Sleeper ids are already on each row, so headshots come from the
// same store the weekly boards use.

import fs from "node:fs";
import path from "node:path";

const SRC = path.join(process.cwd(), "data", "buy-sell");
const OUT = path.join(process.cwd(), "public", "data");
const IDS = path.join(process.cwd(), "data", "sleeper-ids.csv");

function parseCsv(text) {
  const rows = [];
  let row = [], field = "", inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') { if (text[i + 1] === '"') { field += '"'; i++; } else inQuotes = false; }
      else field += c;
    } else if (c === '"') inQuotes = true;
    else if (c === ",") { row.push(field); field = ""; }
    else if (c === "\n") { row.push(field); rows.push(row); row = []; field = ""; }
    else if (c !== "\r") field += c;
  }
  if (field !== "" || row.length) { row.push(field); rows.push(row); }
  const header = rows[0].map((h) => h.trim().toLowerCase());
  return rows.slice(1)
    .filter((r) => r.length === header.length && r.some((v) => v !== ""))
    .map((r) => Object.fromEntries(header.map((h, j) => [h, r[j].trim()])));
}

const num = (v) => (v != null && v !== "" && Number.isFinite(Number(v)) ? Number(v) : null);

// Our own board carries the better team abbreviation and the photo we already
// resolved; Sleeper's roster team can lag a trade by a day or two.
const ours = new Map();
if (fs.existsSync(IDS))
  for (const r of parseCsv(fs.readFileSync(IDS, "utf8")))
    ours.set(r.sleeper_id, { team: r.team, photo: r.sleeper_id });

if (!fs.existsSync(SRC)) { console.log("no data/buy-sell directory"); process.exit(0); }
fs.mkdirSync(OUT, { recursive: true });

const index = [];
for (const season of fs.readdirSync(SRC).filter((d) => /^\d{4}$/.test(d)).sort()) {
  for (const file of fs.readdirSync(path.join(SRC, season)).filter((f) => /^week-\d+\.csv$/.test(f)).sort()) {
    const week = Number(file.match(/week-(\d+)/)[1]);
    const rows = parseCsv(fs.readFileSync(path.join(SRC, season, file), "utf8")).map((r) => ({
      player: r.player,
      position: r.position,
      team: ours.get(r.sleeper_id)?.team || r.team || null,
      photo: r.sleeper_id || null,
      actual: num(r.a_pts_ppr),
      projected: num(r.p_pts_ppr),
      resid: num(r.resid),
      predChange: num(r.pred_change),
      verdict: r.verdict,
      why: r.why || null,
      snapShare: num(r.snap_share),
      level: num(r.level),
      injuryStatus: r.injury_status || null,
      injuryPart: r.injury_part || null,
      leftEarly: r.left_early === "True" || r.left_early === "true",
    })).filter((r) => r.player && r.verdict);
    if (!rows.length) continue;
    const cuts = JSON.parse(parseCsv(fs.readFileSync(path.join(SRC, season, file), "utf8"))[0].cuts || "{}");
    const key = `${season}-w${String(week).padStart(2, "0")}`;
    fs.writeFileSync(path.join(OUT, `buysell-${key}.json`),
      JSON.stringify({ season: Number(season), week, label: `Week ${week}`, cuts, rows }));
    index.push({ key, season: Number(season), week, label: `Week ${week}`, count: rows.length });
    const by = rows.reduce((a, r) => ((a[r.verdict] = (a[r.verdict] || 0) + 1), a), {});
    console.log(`${key}: ${rows.length} players ${JSON.stringify(by)}`);
  }
}
index.sort((a, b) => a.season - b.season || a.week - b.week);
fs.writeFileSync(path.join(OUT, "buysell-index.json"), JSON.stringify({ weeks: index }));
console.log(`index: ${index.length} week(s)`);
