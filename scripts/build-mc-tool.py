"""Build the offline board MC reorders his week on.

The output is a single self-contained file under tools/, which Next does not
serve -- only public/ and src/app/ reach the internet -- so the tool never ships
with the site and nobody can edit his list from a browser. He opens it from
disk, drags, types his takes, and hands back a CSV.

Wilson's ranks and projections are deliberately absent. The whole premise is
two independent voices and the gap between them; showing MC the data list while
he ranks would close that gap by contaminating it, and the delta would stop
meaning anything.

    python3 scripts/build-mc-tool.py --week 2

The board is seeded from the published lists for that week, ordered by whatever
sits in the vibes column. On a week MC has already ranked that is his own last
answer, so reopening the tool picks up where he left off. On a week he has not,
it is consensus, which gives him a sensible starting order to drag against
rather than an alphabetical one.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--season", type=int, default=2026)
ap.add_argument("--week", type=int, default=1)
ap.add_argument("--out", default=None)
args = ap.parse_args()

SEASON, WEEK = args.season, args.week
SRC = Path(f"data/weekly/{SEASON}/week-{WEEK:02d}")
# One file per week, so an older week's board is never silently overwritten by
# a newer one while he still has it open.
OUT = Path(args.out) if args.out else Path(f"tools/mc-rankings-week-{WEEK:02d}.html")
# Consensus is the same list in both scoring formats -- nought differing ranks
# at WR and QB, two at RB -- so he ranks once per position, not once per list.
# The membership is not identical though: the depth cut lands in a different
# place, so half-PPR reaches a few names PPR does not. Seed from every variant
# or those men arrive on the published board with no rank from MC at all.
POSITIONS = {"QB": ["qb-4pt.csv", "qb-6pt.csv"], "RB": ["rb-ppr.csv", "rb-half.csv"],
             "WR": ["wr-ppr.csv", "wr-half.csv"], "TE": ["te-ppr.csv", "te-half.csv"]}


def week_one() -> dict:
    """What each player did in the week before this one, and who he did it to.

    Returns what each player did, and separately how every defence has played,
    so a card can pair his last line with the defence he is about to face. The
    rank was briefly taken against the defence he faced last week, which
    describes a game already played rather than the one being ranked.

    Needs the model on the path (DD_MODEL). Without it the cards simply carry
    the week 2 matchup, as before.
    """
    prev = WEEK - 1
    if prev < 1:
        return {}, {}
    sys.path.insert(0, os.environ.get("DD_MODEL", "model"))
    try:
        from dd import defense, inseason
        from dd.scoring import fantasy_points
    except Exception as exc:
        print(f"  ! no week {prev} detail ({exc}); matchup only")
        return {}, {}
    import pandas as pd

    w = inseason.build()
    w = w[(w.season == SEASON) & (w.week == prev)].copy()
    if w.empty:
        return {}, {}
    w["pts"] = fantasy_points(w, "ppr")

    d = defense.build()
    d = d[(d.season == SEASON) & (d.week == prev)].copy()
    d["rk_pass"] = d.def_epa_pass.rank(method="first")
    d["rk_rush"] = d.def_epa_rush.rank(method="first")
    rk = {x.team: (int(x.rk_pass), int(x.rk_rush)) for _, x in d.iterrows()}

    # The tool is seeded from the published lists, which carry no player id, so
    # the model's own pool supplies the bridge from name to id.
    ident = {}
    model = Path(os.environ.get("DD_MODEL", "model")) / "outputs" / str(SEASON) \
        / f"week-{WEEK:02d}"
    for f in model.glob("*_pool.csv"):
        for r in csv.DictReader(f.open()):
            ident.setdefault(r["player_name"], r["player_id"])

    out = {}
    for _, x in w.iterrows():
        pos = x.position
        n = lambda c: float(x.get(c) or 0)
        if pos == "QB":
            # Rushing touchdowns and interceptions both belong here. Without
            # them Lamar Jackson read "324 yards, 1 TD, 7 carries for 40" next
            # to 27.0 points, and the two do not reconcile.
            line = f"{n('passing_yards'):.0f} pass yds, {n('passing_tds'):.0f} TD"
            if n("passing_interceptions"):
                line += f", {n('passing_interceptions'):.0f} INT"
            line += f", {n('carries'):.0f} car for {n('rushing_yards'):.0f}"
            if n("rushing_tds"):
                line += f" and {n('rushing_tds'):.0f} TD"
        elif pos == "RB":
            line = (f"{n('carries'):.0f} car, {n('rushing_yards'):.0f} yds"
                    f", {n('receptions'):.0f} rec on {n('targets'):.0f} tgt")
            tds = n("rushing_tds") + n("receiving_tds")
            if tds:
                line += f", {tds:.0f} TD"
        else:
            line = (f"{n('receptions'):.0f} rec on {n('targets'):.0f} tgt"
                    f", {n('receiving_yards'):.0f} yds")
            if n("receiving_tds"):
                line += f", {n('receiving_tds'):.0f} TD"
        opp = x.opponent_team
        out[x.player_id] = {
            "pts": round(float(x.pts), 1), "line": line, "opp": opp,
        }
    print(f"  week {prev} detail attached for {len(out)} players")
    return ({name: out[pid] for name, pid in ident.items() if pid in out},
            {t: {"pass": int(v[0]), "rush": int(v[1])} for t, v in rk.items()})


def ordinal(k: int) -> str:
    if 10 <= k % 100 <= 20:
        return f"{k}th"
    return f"{k}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(k % 10, 'th') }"


def injuries() -> dict:
    """What each man is carrying, keyed by name and by name and team.

    Anyone with a status that means he is not playing is already off the board
    before the tool is built, so what survives here is the judgement call:
    Questionable, and what body part. That is the part MC cannot get from a
    ranking, and the part that most often decides where a man belongs.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from sleeper import status
    out = {}
    for _, x in status().iterrows():
        if not x.player:
            continue
        tag = x.status + (f" ({x.part})" if x.part else "")
        out[(x.player, x.team)] = tag
        out.setdefault(x.player, tag)
    return out


def load() -> dict:
    last, defrank = week_one()
    hurt = injuries()
    board = {}
    for pos, fnames in POSITIONS.items():
        seen, rows = set(), []
        for fname in fnames:
            for r in csv.DictReader((SRC / fname).open()):
                if r["player"] not in seen:
                    seen.add(r["player"])
                    rows.append(r)
        rows.sort(key=lambda r: int(r["rank_vibes"]))
        board[pos] = [{
            "player": r["player"],
            "team": r["team"],
            "opp": r["opponent"],
            "home": int(r["is_home"] or 0),
            "consensus": int(r["rank_vibes"]),
            "note": r["note_vibes"] or "",
            "last": last.get(r["player"]),
            # The defence he is about to face, on the side that matters to
            # him. This was the defence he faced LAST week, which described a
            # game already played rather than the one being ranked.
            "def": (defrank.get(r["opponent"], {}).get(
                "rush" if pos == "RB" else "pass")),
            "inj": hurt.get((r["player"], r["team"])) or hurt.get(r["player"]),
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
  /* Last week sits under the row rather than in it, so the drag target and the
     column widths are exactly what they were. */
  .last { padding:0 10px 8px 46px; color:var(--dim); font-size:12.5px;
          line-height:1.5; }
  .last b { color:var(--ink); font-weight:600; }
  .last .vs { display:block; color:var(--faint); }
  /* The defence he is about to face. Kept apart from last week's line so the
     two are not read as one sentence. */
  .dfn { padding:0 10px 8px 46px; color:var(--warn); font-size:12.5px; }
  /* Beside the name rather than below it: everyone still on this board has
     been cleared to play, so the tag is a caveat on the man, not a headline. */
  .inj { flex:0 0 auto; color:var(--warn); border:1px solid var(--warn);
         border-radius:3px; padding:1px 5px; font-size:11px; white-space:nowrap; }
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
const ord = k => k + ({1: "st", 2: "nd", 3: "rd"}[k % 10] &&
  !(k % 100 >= 10 && k % 100 <= 20) ? {1: "st", 2: "nd", 3: "rd"}[k % 10] : "th");
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
        (r.inj ? '<span class="inj"></span>' : "") +
        '<span class="match"></span>' +
        '<span class="delta">' + (d === 0 ? "" : (d > 0 ? "+" + d : d)) + '</span>' +
        '<input class="jump" type="number" min="1" max="' + rows.length +
          '" placeholder="' + rank + '">' +
        '<button class="notebtn' + (r.note.trim() ? " has" : "") + '">note</button>' +
      '</div>' +
      (r.last ? '<div class="last"></div>' : "") +
      (r.def ? '<div class="dfn"></div>' : "") +
      '<div class="note"><textarea placeholder="Why MC has him here"></textarea></div>';
    li.querySelector(".name").textContent = r.player;
    if (r.inj) li.querySelector(".inj").textContent = r.inj;
    li.querySelector(".match").textContent =
      r.team + (r.opp ? (r.home ? " vs " : " @ ") + r.opp : "");
    if (r.def) {
      const side = active === "RB" ? "run" : "pass";
      li.querySelector(".dfn").textContent =
        r.opp + " rank " + ord(r.def) + " of 32 against the " + side +
        " through week " + (WEEK - 1);
    }
    if (r.last) {
      const L = li.querySelector(".last");
      L.innerHTML = '<b>Wk ' + (WEEK - 1) + '</b> ' + r.last.pts + ' pts &middot; ' +
        r.last.line + ' vs ' + r.last.opp;
    }
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
