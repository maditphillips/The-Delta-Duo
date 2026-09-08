"""Build the offline board MC reorders his week on.

The output is a single self-contained file under tools/, which Next does not
serve -- only public/ and src/app/ reach the internet -- so the tool never ships
with the site and nobody can edit his list from a browser. He opens it from
disk, drags, types his takes, and hands back a CSV.

Wilson's ranks and projections are deliberately absent. The whole premise is
two independent voices and the gap between them; showing MC the data list while
he ranks would close that gap by contaminating it, and the delta would stop
meaning anything.

    python3 scripts/build-mc-tool.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

SEASON, WEEK = 2026, 1
SRC = Path(f"data/weekly/{SEASON}/week-{WEEK:02d}")
OUT = Path("tools/mc-rankings.html")
# Consensus is the same list in both scoring formats -- nought differing ranks
# at WR and QB, two at RB -- so he ranks once per position, not once per list.
POSITIONS = [("QB", "qb-4pt.csv"), ("RB", "rb-ppr.csv"),
             ("WR", "wr-ppr.csv"), ("TE", "te-ppr.csv")]


def load() -> dict:
    board = {}
    for pos, fname in POSITIONS:
        rows = list(csv.DictReader((SRC / fname).open()))
        rows.sort(key=lambda r: int(r["rank_vibes"]))
        board[pos] = [{
            "player": r["player"],
            "team": r["team"],
            "opp": r["opponent"],
            "home": int(r["is_home"] or 0),
            "consensus": int(r["rank_vibes"]),
            "note": r["note_vibes"] or "",
        } for r in rows]
    return board


HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MC's Week __WEEK__ Rankings</title>
<style>
  :root {
    --bg:#0c0c0e; --card:#15151a; --line:#2a2a33; --ink:#ece9e4;
    --dim:#9a968f; --faint:#6a675f; --mc:#01def3; --warn:#f6a02c;
  }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--ink);
         font:15px/1.45 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif; }
  header { padding:20px 20px 0; max-width:900px; margin:0 auto; }
  h1 { margin:0 0 4px; font-size:22px; letter-spacing:.02em; }
  .sub { color:var(--dim); font-size:13px; margin:0 0 16px; }
  main { max-width:900px; margin:0 auto; padding:0 20px 80px; }
  .bar { display:flex; flex-wrap:wrap; gap:8px; align-items:center;
         padding:12px 0; position:sticky; top:0; background:var(--bg); z-index:5;
         border-bottom:1px solid var(--line); }
  button { font:inherit; color:var(--ink); background:var(--card);
           border:1px solid var(--line); border-radius:6px; padding:6px 12px;
           cursor:pointer; }
  button:hover { border-color:var(--mc); }
  button.on { border-color:var(--mc); color:var(--mc); }
  button.primary { background:var(--mc); color:#06232a; border-color:var(--mc);
                   font-weight:600; }
  .spacer { flex:1; }
  .count { color:var(--faint); font-size:12px; }
  ol { list-style:none; margin:14px 0 0; padding:0; }
  li { display:block; border:1px solid var(--line); border-radius:7px;
       margin-bottom:5px; background:var(--card); }
  li.drag { opacity:.35; }
  li.over { border-color:var(--mc); }
  li.moved { border-left:3px solid var(--warn); }
  .row { display:flex; align-items:center; gap:10px; padding:8px 10px;
         cursor:grab; }
  .grip { color:var(--faint); font-size:15px; letter-spacing:-2px; width:12px; }
  .rank { width:30px; text-align:right; color:var(--mc); font-variant-numeric:tabular-nums;
          font-weight:600; }
  .name { flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis;
          white-space:nowrap; }
  .match { color:var(--dim); font-size:12px; width:120px; }
  .delta { width:52px; text-align:right; font-size:12px; color:var(--faint);
           font-variant-numeric:tabular-nums; }
  li.moved .delta { color:var(--warn); }
  .jump { width:52px; background:#0c0c0e; color:var(--ink); border:1px solid var(--line);
          border-radius:4px; padding:3px 5px; font:inherit; font-size:12px;
          text-align:center; }
  .notebtn { background:none; border:none; color:var(--faint); padding:2px 6px;
             font-size:12px; }
  .notebtn.has { color:var(--mc); }
  .note { display:none; padding:0 10px 10px 62px; }
  li.open .note { display:block; }
  textarea { width:100%; min-height:56px; resize:vertical; background:#0c0c0e;
             color:var(--ink); border:1px solid var(--line); border-radius:5px;
             padding:7px 9px; font:inherit; font-size:13px; }
  .hint { color:var(--faint); font-size:12px; margin:10px 0 0; }
  .saved { color:var(--faint); font-size:12px; }
  dialog { background:var(--card); color:var(--ink); border:1px solid var(--line);
           border-radius:8px; max-width:640px; width:92%; padding:16px; }
  dialog textarea { min-height:280px; font-family:ui-monospace,Menlo,Consolas,monospace;
                    font-size:12px; }
</style>
</head>
<body>
<header>
  <h1>MC&rsquo;s Week __WEEK__ Rankings</h1>
  <p class="sub">Everyone starts in consensus order. Move only the players you
  disagree with &mdash; anyone you leave alone stays at consensus. Wilson&rsquo;s
  list is deliberately not shown here.</p>
</header>
<main>
  <div class="bar">
    <span id="tabs"></span>
    <span class="spacer"></span>
    <span class="count" id="count"></span>
    <button id="reset">Reset position</button>
    <button id="copy">Copy for Claude</button>
    <button id="dl" class="primary">Download CSV</button>
  </div>
  <ol id="list"></ol>
  <p class="hint">Drag a row, or type a number in its box and press Enter to send
  him straight there. Click <b>note</b> to write his take. Work saves in this
  browser automatically. <span class="saved" id="saved"></span></p>
</main>

<dialog id="fallback">
  <p style="margin:0 0 8px">Copy this and paste it back to Claude.</p>
  <textarea id="fbtext" readonly></textarea>
  <p style="margin:10px 0 0;text-align:right"><button onclick="fallback.close()">Close</button></p>
</dialog>

<script>
const WEEK = "__WEEK__", SEASON = "__SEASON__";
const SEED = __DATA__;
const KEY = "mc-rankings-" + SEASON + "-w" + WEEK;
const POS = Object.keys(SEED);
let active = POS[0];
let board = load();

function load() {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) {
      const saved = JSON.parse(raw);
      // Seed order is authoritative for who is on the board; a player dropped
      // from this week's list must not survive in a stale save.
      const out = {};
      for (const p of POS) {
        const by = new Map((saved[p] || []).map(
          (r, i) => [r.player, {i, note: r.note || "", touched: !!r.touched}]));
        out[p] = SEED[p].map(r => ({...r, note: (by.get(r.player) || {}).note || "",
                                    touched: !!(by.get(r.player) || {}).touched}))
          .sort((a, b) => {
            const ai = by.has(a.player) ? by.get(a.player).i : a.consensus + 1000;
            const bi = by.has(b.player) ? by.get(b.player).i : b.consensus + 1000;
            return ai - bi;
          });
      }
      return out;
    }
  } catch (e) { /* a corrupt save should not brick the tool */ }
  return JSON.parse(JSON.stringify(SEED));
}

function save() {
  try {
    localStorage.setItem(KEY, JSON.stringify(board));
    document.getElementById("saved").textContent =
      "Saved " + new Date().toLocaleTimeString();
  } catch (e) {
    document.getElementById("saved").textContent = "Could not save in this browser";
  }
}

function tabs() {
  const el = document.getElementById("tabs");
  el.innerHTML = "";
  for (const p of POS) {
    const b = document.createElement("button");
    b.textContent = p + " (" + board[p].length + ")";
    if (p === active) b.className = "on";
    b.onclick = () => { active = p; render(); };
    el.appendChild(b);
  }
}

function render() {
  tabs();
  const rows = board[active];
  // Only what he actually dragged. Sending one man from 11 to 2 shifts nine
  // others by a place, and marking those as changes buries the edit that
  // mattered under the displacement it caused.
  const moved = rows.filter(r => r.touched).length;
  const noted = rows.filter(r => r.note.trim()).length;
  document.getElementById("count").textContent =
    moved + " moved \\u00b7 " + noted + " with takes";
  const ol = document.getElementById("list");
  ol.innerHTML = "";
  rows.forEach((r, i) => {
    const rank = i + 1, d = r.consensus - rank;
    const li = document.createElement("li");
    li.draggable = true;
    li.dataset.i = i;
    if (r.touched) li.classList.add("moved");
    li.innerHTML =
      '<div class="row">' +
        '<span class="grip">&#9776;</span>' +
        '<span class="rank">' + rank + '</span>' +
        '<span class="name"></span>' +
        '<span class="match"></span>' +
        '<span class="delta">' + (d === 0 ? "" : (d > 0 ? "+" + d : d)) + '</span>' +
        '<input class="jump" type="number" min="1" max="' + rows.length +
          '" placeholder="' + rank + '">' +
        '<button class="notebtn' + (r.note.trim() ? " has" : "") + '">note</button>' +
      '</div>' +
      '<div class="note"><textarea placeholder="Why MC has him here"></textarea></div>';
    li.querySelector(".name").textContent = r.player;
    li.querySelector(".match").textContent =
      r.team + (r.opp ? (r.home ? " vs " : " @ ") + r.opp : "");
    const ta = li.querySelector("textarea");
    ta.value = r.note;
    ta.oninput = () => { r.note = ta.value; save(); };
    ta.onblur = render;
    li.querySelector(".notebtn").onclick = e => {
      e.stopPropagation();
      li.classList.toggle("open");
      if (li.classList.contains("open")) ta.focus();
    };
    const jump = li.querySelector(".jump");
    jump.onkeydown = e => {
      if (e.key !== "Enter") return;
      const to = Math.min(Math.max(parseInt(jump.value, 10), 1), rows.length);
      if (!isNaN(to)) move(i, to - 1);
    };
    jump.onclick = e => e.stopPropagation();
    li.ondragstart = e => {
      e.dataTransfer.setData("text/plain", String(i));
      e.dataTransfer.effectAllowed = "move";
      li.classList.add("drag");
    };
    li.ondragend = () => li.classList.remove("drag");
    li.ondragover = e => { e.preventDefault(); li.classList.add("over"); };
    li.ondragleave = () => li.classList.remove("over");
    li.ondrop = e => {
      e.preventDefault();
      li.classList.remove("over");
      move(parseInt(e.dataTransfer.getData("text/plain"), 10), i);
    };
    ol.appendChild(li);
  });
}

function move(from, to) {
  if (isNaN(from) || isNaN(to) || from === to) return;
  const rows = board[active];
  const [r] = rows.splice(from, 1);
  r.touched = true;
  rows.splice(to, 0, r);
  save();
  render();
}

function csv() {
  const q = v => {
    v = String(v == null ? "" : v);
    return /[",\\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v;
  };
  const out = ["position,rank,player,team,consensus_rank,moved,note"];
  for (const p of POS)
    board[p].forEach((r, i) =>
      out.push([p, i + 1, r.player, r.team, r.consensus,
                r.touched ? 1 : 0, r.note.trim()].map(q).join(",")));
  return out.join("\\n") + "\\n";
}

document.getElementById("dl").onclick = () => {
  const name = "mc-rankings-" + SEASON + "-week-" + WEEK + ".csv";
  try {
    const url = URL.createObjectURL(new Blob([csv()], {type: "text/csv"}));
    const a = document.createElement("a");
    a.href = url; a.download = name;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (e) {
    // Some browsers refuse a blob download from a file:// page. Show the text
    // instead rather than failing silently.
    showText();
  }
};

function showText() {
  document.getElementById("fbtext").value = csv();
  document.getElementById("fallback").showModal();
  document.getElementById("fbtext").select();
}

document.getElementById("copy").onclick = async () => {
  try {
    await navigator.clipboard.writeText(csv());
    const b = document.getElementById("copy");
    b.textContent = "Copied";
    setTimeout(() => (b.textContent = "Copy for Claude"), 1500);
  } catch (e) { showText(); }
};

document.getElementById("reset").onclick = () => {
  if (!confirm("Put " + active + " back in consensus order? Takes are kept."))
    return;
  const notes = new Map(board[active].map(r => [r.player, r.note]));
  board[active] = SEED[active].map(
    r => ({...r, note: notes.get(r.player) || "", touched: false}));
  save();
  render();
};

render();
</script>
</body>
</html>
"""


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    board = load()
    html = (HTML.replace("__DATA__", json.dumps(board, separators=(",", ":")))
                .replace("__WEEK__", str(WEEK))
                .replace("__SEASON__", str(SEASON)))
    OUT.write_text(html)
    total = sum(len(v) for v in board.values())
    print(f"  wrote {OUT}  ({total} players: "
          + ", ".join(f"{p} {len(v)}" for p, v in board.items()) + ")")


if __name__ == "__main__":
    main()
