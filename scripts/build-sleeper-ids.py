"""Resolve this week's players to Sleeper ids, so the site can show their faces.

Sleeper publishes one endpoint for the whole league -- 12,226 players, 14.6 MB
-- and asks that it be pulled no more than once a day. Fetching that from a
visitor's browser to put 211 photographs on a page would be indefensible, so it
is resolved here and the ids are committed. The page then renders plain <img>
tags against sleepercdn and makes no API call at all.

Matching is on name and position with suffixes stripped, which resolves 211 of
212 players with nothing ambiguous. Raw name matching misses eleven -- every
Jr., Sr. and III -- and the last one is a nickname, which is what ALIASES is
for. Every name-matching scheme needs that list eventually; better to have it
from the start than to discover it silently mid-season.

    python3 scripts/build-sleeper-ids.py
"""
from __future__ import annotations

import csv
import json
import re
import urllib.request
from pathlib import Path

SEASON, WEEK = 2026, 1
SRC = Path(f"data/weekly/{SEASON}/week-{WEEK:02d}")
OUT = Path("data/sleeper-ids.csv")
API = "https://api.sleeper.app/v1/players/nfl"
FILES = {"QB": "qb-4pt.csv", "RB": "rb-ppr.csv", "WR": "wr-ppr.csv", "TE": "te-ppr.csv"}

# Our name -> the name Sleeper files him under.
ALIASES = {"Bam Knight": "Zonovan Knight"}

SUFFIX = re.compile(r"\b(jr|sr|ii|iii|iv|v)\b")


def norm(name: str) -> str:
    name = name.lower().replace(".", " ").replace("'", "")
    return re.sub(r"[^a-z]", "", SUFFIX.sub(" ", name))


def main() -> None:
    with urllib.request.urlopen(API, timeout=120) as fh:
        players = json.load(fh)
    print(f"  sleeper: {len(players)} players")

    index: dict[tuple[str, str], list[dict]] = {}
    for p in players.values():
        if p.get("full_name") and p.get("position") in FILES:
            index.setdefault((norm(p["full_name"]), p["position"]), []).append(p)

    rows, missing = [], []
    for pos, fname in FILES.items():
        for r in csv.DictReader((SRC / fname).open()):
            name = ALIASES.get(r["player"], r["player"])
            hits = index.get((norm(name), pos), [])
            if not hits:
                missing.append(f"{r['player']} ({r['team']} {pos})")
                continue
            # A duplicated name is separated by his team; if that fails too,
            # the first is as good a guess as any and the count is reported.
            same = [p for p in hits if (p.get("team") or "").upper() == r["team"].upper()]
            pick = (same or hits)[0]
            rows.append({"player": r["player"], "team": r["team"], "position": pos,
                         "sleeper_id": pick["player_id"],
                         "ambiguous": int(len(hits) > 1 and not same)})

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["player", "team", "position",
                                           "sleeper_id", "ambiguous"])
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r["position"], r["player"])))
    amb = sum(r["ambiguous"] for r in rows)
    print(f"  wrote {OUT}  ({len(rows)} resolved, {amb} ambiguous, {len(missing)} missing)")
    for m in missing:
        print(f"    no sleeper match: {m}  <- add to ALIASES")


if __name__ == "__main__":
    main()
