// Build the Player Explorer panels from nflverse data.
//
//   node scripts/build-explorer.mjs [cacheDir]
//
// Downloads (or reads from cacheDir) nflverse draft picks and seasonal player
// stats, then emits per-position player-season panels to public/data/.
//
// Definitions follow the Delta Duo studies:
//   - Positional finish = rank of PPR points among all players at the position
//     that season (regular season, full player pool including undrafted).
//   - WR "fed" = 80+ targets. RB "real role" = 50+ carries.
//   - Moved = primary team differs from prior season. The seasonal stats carry
//     one team per player-season (most recent), so mid-season trades attribute
//     to the later team.
//   - Vacancy ahead = the player's team's leading WR/RB (by targets/carries)
//     from the prior season is no longer on that team.
//   - Draft age = nflverse draft age.

import fs from "node:fs";
import path from "node:path";

const SEASONS_FROM = 2007; // one season before the first panel year, for priors
const SEASONS_TO = 2025;
const PANEL_FROM = 2008;
const OUT_DIR = path.join(process.cwd(), "public", "data");
const cacheDir = process.argv[2] ?? path.join(process.cwd(), ".nflverse-cache");

const DRAFT_URL = "https://github.com/nflverse/nflverse-data/releases/download/draft_picks/draft_picks.csv";
const statsUrl = (y) => `https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_reg_${y}.csv`;

async function fetchCsv(url, cacheName) {
  const cachePath = path.join(cacheDir, cacheName);
  if (fs.existsSync(cachePath)) return fs.readFileSync(cachePath, "utf8");
  const res = await fetch(url, { redirect: "follow" });
  if (!res.ok) throw new Error(`${res.status} for ${url}`);
  const text = await res.text();
  fs.mkdirSync(cacheDir, { recursive: true });
  fs.writeFileSync(cachePath, text);
  return text;
}

// Minimal CSV parser (handles quoted fields with commas/newlines).
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
  const header = rows[0];
  return rows.slice(1).filter((r) => r.length === header.length).map((r) => {
    const o = {};
    for (let j = 0; j < header.length; j++) o[header[j]] = r[j];
    return o;
  });
}

const num = (v) => (v === "" || v == null ? 0 : Number(v));
const dayOf = (round) => (round === 1 ? "Round 1" : round <= 3 ? "Day 2" : "Day 3");

const POSITIONS = {
  WR: { volumeKey: "targets", roleBar: 80, roleLabel: "80+ targets" },
  RB: { volumeKey: "carries", roleBar: 50, roleLabel: "50+ carries" },
  QB: { volumeKey: "attempts", roleBar: 224, roleLabel: "224+ attempts" },
};

async function main() {
  console.log("loading draft picks…");
  const draft = parseCsv(await fetchCsv(DRAFT_URL, "draft_picks.csv"));
  const drafted = new Map(); // gsis_id -> draft info
  for (const d of draft) {
    const season = num(d.season);
    if (season < PANEL_FROM || season > SEASONS_TO) continue;
    if (!POSITIONS[d.position]) continue;
    if (!d.gsis_id) continue;
    drafted.set(d.gsis_id, {
      pos: d.position,
      draftYear: season,
      round: num(d.round),
      pick: num(d.pick),
      day: dayOf(num(d.round)),
      draftAge: d.age ? num(d.age) : null,
      college: d.college || null,
      name: d.pfr_player_name || null,
    });
  }
  console.log(`drafted 2008+ at WR/RB/QB: ${drafted.size}`);

  // season -> pos -> rows (all players at position, for ranking + leaders)
  const seasonRows = new Map();
  for (let y = SEASONS_FROM; y <= SEASONS_TO; y++) {
    console.log(`loading stats ${y}…`);
    const raw = parseCsv(await fetchCsv(statsUrl(y), `stats_${y}.csv`));
    const byPos = { WR: [], RB: [], QB: [] };
    for (const r of raw) {
      const pos = r.position_group;
      if (!byPos[pos]) continue;
      byPos[pos].push({
        id: r.player_id,
        name: r.player_display_name,
        team: r.recent_team,
        games: num(r.games),
        targets: num(r.targets),
        receptions: num(r.receptions),
        recYards: num(r.receiving_yards),
        carries: num(r.carries),
        rushYards: num(r.rushing_yards),
        attempts: num(r.attempts),
        passYards: num(r.passing_yards),
        ppr: Math.round(num(r.fantasy_points_ppr) * 10) / 10,
      });
    }
    for (const pos of Object.keys(byPos)) {
      byPos[pos].sort((a, b) => b.ppr - a.ppr);
      byPos[pos].forEach((r, i) => (r.rank = i + 1));
    }
    seasonRows.set(y, byPos);
  }

  fs.mkdirSync(OUT_DIR, { recursive: true });

  for (const [pos, cfg] of Object.entries(POSITIONS)) {
    // team leader by volume, per season
    const leaders = new Map(); // season -> team -> row
    for (let y = SEASONS_FROM; y <= SEASONS_TO; y++) {
      const m = new Map();
      for (const r of seasonRows.get(y)[pos]) {
        const cur = m.get(r.team);
        if (!cur || r[cfg.volumeKey] > cur[cfg.volumeKey]) m.set(r.team, r);
      }
      leaders.set(y, m);
    }
    // per-player season index for priors / careers
    const byPlayer = new Map();
    for (let y = SEASONS_FROM; y <= SEASONS_TO; y++) {
      for (const r of seasonRows.get(y)[pos]) {
        if (!byPlayer.has(r.id)) byPlayer.set(r.id, new Map());
        byPlayer.get(r.id).set(y, r);
      }
    }

    const panel = [];
    for (const [id, seasons] of byPlayer) {
      const info = drafted.get(id);
      if (!info || info.pos !== pos) continue;
      const years = [...seasons.keys()].sort((a, b) => a - b);
      // career flags
      let bestRank = Infinity;
      for (const y of years) bestRank = Math.min(bestRank, seasons.get(y).rank);
      let firstRoleSeason = null;
      for (const y of years) {
        if (seasons.get(y)[cfg.volumeKey] >= cfg.roleBar) { firstRoleSeason = y; break; }
      }
      for (const y of years) {
        if (y < PANEL_FROM || y < info.draftYear) continue;
        const r = seasons.get(y);
        const prior = seasons.get(y - 1) ?? null;
        const leader = leaders.get(y - 1)?.get(r.team) ?? null;
        let vacancy = false;
        if (leader && leader.id !== id) {
          const leaderNow = byPlayer.get(leader.id)?.get(y) ?? null;
          vacancy = !leaderNow || leaderNow.team !== r.team;
        }
        const hadRoleBefore = years.some((yy) => yy < y && seasons.get(yy)[cfg.volumeKey] >= cfg.roleBar);
        panel.push({
          id,
          n: r.name ?? info.name,
          s: y,
          tm: r.team,
          yr: info.draftYear,
          rd: info.round,
          pk: info.pick,
          dy: info.day,
          ag: info.draftAge,
          g: r.games,
          tg: r.targets,
          rec: r.receptions,
          ry: r.recYards,
          ca: r.carries,
          ruy: r.rushYards,
          att: r.attempts,
          ppr: r.ppr,
          rk: r.rank,
          ptg: prior ? prior[cfg.volumeKey] : null,
          ptm: prior ? prior.team : null,
          mv: prior ? prior.team !== r.team : null,
          vac: vacancy,
          role: r[cfg.volumeKey] >= cfg.roleBar,
          risk: !hadRoleBefore,
          ff: firstRoleSeason === y,
          bestRk: bestRank,
          seasonYears: undefined,
        });
      }
    }
    panel.sort((a, b) => a.s - b.s || a.rk - b.rk);
    const out = {
      pos,
      roleBar: cfg.roleBar,
      roleLabel: cfg.roleLabel,
      volumeKey: cfg.volumeKey,
      seasons: [PANEL_FROM, SEASONS_TO],
      source: "nflverse draft_picks + stats_player_reg, regular season, PPR",
      rows: panel,
    };
    const file = path.join(OUT_DIR, `explorer-${pos.toLowerCase()}.json`);
    fs.writeFileSync(file, JSON.stringify(out));
    console.log(`${pos}: ${panel.length} player-seasons → ${file} (${Math.round(fs.statSync(file).size / 1024)} KB)`);
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
