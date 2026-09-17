"""Grade FantasyPros' published top-N graphics against Wilson and MC.

The board in data/weekly/<season>/week-NN/fantasypros.csv is transcribed from
the images FantasyPros publishes, which are not the ECR pages the
DynastyProcess mirror carries: neither the weekly board nor the preseason
redraft board matches them. Rather than guess at which product they are, the
ranking is taken as given.

Each voice is graded on the players IT put in its own top N, so selection
counts as well as ordering. A man nobody could have started still costs the
list that ranked him.

    DD_MODEL=../rankings/model python3 scripts/grade-fantasypros.py
"""
import csv, json, os, sys
from pathlib import Path
import numpy as np

SCRATCH = Path("/tmp/claude-0/-home-user-The-Delta-Duo/8c91f04b-24b4-5638-8c4d-a7fd7c62ef31/scratchpad")
WEEK = Path("data/weekly/2026/week-01")
st = json.load(open(SCRATCH / "st1.json"))

ids = {(r["player"], r["team"]): r["sleeper_id"]
       for r in csv.DictReader(open("data/sleeper-ids.csv"))}
by_name = {}
for (p, t), s in ids.items():
    by_name.setdefault(p, s)
# Two of the men on the graphics were never on our boards, so they are not in
# our id file. Sleeper's roster has everyone.
# The notes script already keeps Sleeper's roster warm; reuse that copy.
for k, v in json.loads(Path("/tmp/sleeper-players.json").read_text()).items():
    if v.get("position") in ("QB", "RB", "WR", "TE") and v.get("full_name"):
        by_name.setdefault(v["full_name"], k)


def actual(sid, variant):
    s = st.get(sid) or {}
    if not isinstance(s, dict):
        return 0.0
    pts = float(s.get("pts_ppr") or 0.0) - float(s.get("pass_int") or 0.0)
    if variant == "6pt":
        pts += 2 * float(s.get("pass_td") or 0.0)
    return pts


def pairwise(rank, pts):
    n = len(rank); right = total = 0
    for i in range(n):
        for j in range(i + 1, n):
            if pts[i] == pts[j]:
                continue
            total += 1
            better = i if pts[i] > pts[j] else j
            ahead = i if rank[i] < rank[j] else j
            right += (better == ahead)
    return right, total


TOPN = {"qb": 12, "rb": 12, "wr": 24, "te": 12}
FILES = {"qb": "qb-4pt", "rb": "rb-ppr", "wr": "wr-ppr", "te": "te-ppr"}

fp = {}
for r in csv.DictReader(open(WEEK / "fantasypros.csv")):
    fp.setdefault(r["pos"], []).append((int(r["rank"]), r["player"], r["team"]))

tot = {}
print(f"{'':<5} {'voice':<14} {'pairwise':>9} {'fraction':>11}")
for pos, k in TOPN.items():
    board = {}
    rows = list(csv.DictReader(open(WEEK / f"{FILES[pos]}.csv")))
    for who, col in (("Wilson", "rank_data"), ("MC", "rank_vibes")):
        picked = sorted(rows, key=lambda r: int(r[col]))[:k]
        board[who] = [(i + 1, r["player"], r["team"]) for i, r in enumerate(picked)]
    board["FantasyPros"] = sorted(fp[pos])[:k]
    print(f"{pos.upper()} (top {k})")
    out = []
    for who, lst in board.items():
        sids = [ids.get((p, t)) or by_name.get(p) for _, p, t in lst]
        pts = [actual(s, "4pt" if pos == "qb" else "ppr") for s in sids]
        rk = [r for r, _, _ in lst]
        right, total = pairwise(rk, pts)
        out.append((right / total, who, right, total))
        a, b = tot.get(who, (0, 0)); tot[who] = (a + right, b + total)
    for frac, who, right, total in sorted(out, reverse=True):
        print(f"      {who:<14} {frac:>9.3f} {right:>5}/{total:<5}")
    print()
print("all four pooled")
for who, (a, b) in sorted(tot.items(), key=lambda x: -x[1][0] / x[1][1]):
    print(f"      {who:<14} {a/b:>9.3f} {a:>5}/{b:<5}")
