"""Turn a weekly_kickers.py ranking into the website's weekly board CSV.

    data/weekly/<season>/week-<NN>/k.csv
    rank_data,rank_vibes,player,team,note_data,note_vibes

rank_data is the model. rank_vibes is a placeholder for MC: the same kickers
ordered by their unshrunk career accuracy, which he edits by hand.

    WEEK=2 python3 emit_weekly_csv.py
"""
import csv
import json
import os
import re

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..", "..")
STADIUMS = os.path.join(ROOT, "src", "data", "stadiums.ts")

SEASON = int(os.environ.get("SEASON", 2026))
WEEK = int(os.environ.get("WEEK", 2))
W_VENUE = float(os.environ.get("W_VENUE", 0.50))
K_SHRINK = float(os.environ.get("K_SHRINK", 100))
SHRINK_MODE = os.environ.get("SHRINK_MODE", "onesided")

tag = (f"{int(100 * W_VENUE)}_{int(100 * (1 - W_VENUE))}"
       f"_k{K_SHRINK:.0f}_{SHRINK_MODE}")
SRC = os.path.join(HERE, f"week{WEEK}_{SEASON}_kickers_{tag}.csv")
OUT = os.path.join(ROOT, "data", "weekly", str(SEASON),
                   f"week-{WEEK:02d}", "k.csv")


def main():
    ts = open(STADIUMS).read()
    names = {v["id"]: v["name"].replace("\u00ae", "") for v in json.loads(
        re.search(r"export const stadiums[^=]*=\s*(\[.*?\]);", ts, re.S).group(1))}

    r = pd.read_csv(SRC).sort_values("rank")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rank_data", "rank_vibes", "player", "team",
                    "note_data", "note_vibes"])
        for _, x in r.iterrows():
            where = ("at home" if x.role == "home"
                     else f"at {names.get(x.venue_id, x.venue)}")
            note = f"{x.venue_rate * 100:.1f}% venue rate {where}."
            if x.k_att == 0:
                note += (" No NFL attempts yet, so his own rate is the "
                         "league average.")
            else:
                note += (f" {x.kicker_rate * 100:.1f}% on {int(x.k_att)} career "
                         f"kicks, weighted {x.shrink_w:.2f}.")
            w.writerow([int(x["rank"]), int(x.rank_acc), x.kicker, x.team,
                        note, ""])
    print(f"wrote {os.path.relpath(OUT, ROOT)} ({len(r)} rows)")


if __name__ == "__main__":
    main()
