"""Sleeper's roster, for the one field on it that changes by the hour.

nflverse publishes the official injury report and for this season it is all but
empty: eleven rows for the whole of 2026, none past week 1. is_out and
is_questionable are dead columns, and a man on IR shipped in the rankings with
no flag on him at all. Sleeper carries the same field, keeps it current, and
had Ja'Kobi Lane as Doubtful with a wrist when ours had nothing.

Shared by the notes builder, which drops the ruled-out from the boards, and by
MC's tool, which shows him what is left so he can rank around it. One cache
file between them, so the 14 MB document is fetched once.
"""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

import pandas as pd

SLEEPER = "https://api.sleeper.app/v1"
CACHE = Path("/tmp/sleeper-players.json")
MAX_AGE = 6 * 3600
COLS = ["player", "team", "pos", "status", "part"]
# A status that means he is not playing. Questionable is deliberately absent: a
# hundred and twenty players carry it in a normal week and most of them start.
NOT_PLAYING = {"Out", "IR", "PUP", "Doubtful", "NA", "DNR", "Sus"}


def status() -> pd.DataFrame:
    """Every skill player carrying an injury tag right now."""
    stale = not CACHE.exists() or time.time() - CACHE.stat().st_mtime > MAX_AGE
    if stale:
        try:
            with urllib.request.urlopen(f"{SLEEPER}/players/nfl", timeout=180) as fh:
                CACHE.write_text(json.dumps(json.load(fh)))
        except Exception as exc:
            if not CACHE.exists():
                print(f"  ! could not reach Sleeper ({exc}); no injury pass")
                return pd.DataFrame(columns=COLS)
            print(f"  ! Sleeper unreachable ({exc}); using the cached copy")
    d = json.loads(CACHE.read_text())
    return pd.DataFrame([{"player": v.get("full_name"), "team": v.get("team"),
                          "pos": (v.get("position") or "").lower(),
                          "status": v.get("injury_status"),
                          "part": v.get("injury_body_part") or ""}
                         for v in d.values()
                         if v.get("position") in ("QB", "RB", "WR", "TE")
                         and v.get("injury_status")], columns=COLS)
