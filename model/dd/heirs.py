"""Write the week's injury entries for role.csv from Sleeper's injury list.

Every RB, WR or TE with a real role this season who is ruled out has his work
priced onto the teammates still in his room, on the rank-based rates in
inseason.RANK_RATES ("ranked" basis). Done by hand for week 4 and moved here
so nobody has to spot them one at a time.

  established absent player  played this season, at least 2 touches a game or
                             30% of the snaps
  heir                       same team and position, not ruled out, played
                             this season, a real touch or 10% of the snaps
  starter / backup           whether the absent player led the room by snaps
  weight                     share of the heir's games the absent player also
                             played in. A man out for weeks is already missing
                             from his teammates' numbers, and pricing him in
                             again would count the change twice.

Quarterbacks are left alone: a backup who has already started is priced as a
starter by his own numbers, and one who has not is a call for a person.
"""
from __future__ import annotations

import pandas as pd

from . import inseason as ins
from .features import rankable

OUT = {"Out", "IR", "PUP", "Doubtful", "NA", "DNR", "Sus", "COV"}
POSITIONS = ("RB", "WR", "TE")
TEAM_FIX = {"LAR": "LA"}            # Sleeper's code -> nflverse's
SUFFIXES = (" jr.", " jr", " sr.", " sr", " ii", " iii", " iv", " v")


def bare(name: str) -> str:
    n = str(name).strip().lower().replace(".", "").replace("'", "")
    for suf in (s.replace(".", "") for s in SUFFIXES):
        if n.endswith(suf):
            return n[: -len(suf)].strip()
    return n


def ruled_out() -> pd.DataFrame:
    from .rebound import _players
    p = _players()
    p = p[p.position.isin(POSITIONS) & p.injury_status.isin(OUT)].copy()
    p["team"] = p.team.replace(TEAM_FIX)
    p["key"] = p.player.map(bare)
    return p


def generate(season: int, week: int, verbose: bool = True) -> pd.DataFrame:
    rows = ins.target_rows(season, week)
    weekly = ins.build()
    weekly = weekly[(weekly.season == season) & (weekly.week < week)]
    present = (weekly[weekly.snap_share.fillna(0) > 0]
               .groupby("player_id").week.apply(set).to_dict())
    out = ruled_out()
    entries = []
    for pos in POSITIONS:
        te = ins.blend(rankable(rows, pos), ins.K_ROLE, ins.K_EFF)
        te = te[te.sd_games.fillna(0) > 0].copy()
        te["key"] = te.player_name.map(bare)
        te["touches"] = te.sd_targets.fillna(0) + te.sd_carries.fillna(0)
        gone = set(zip(out.key, out.team))
        te["is_out"] = [(k, t) in gone for k, t in zip(te.key, te.team)]
        absent = te[te.is_out & ((te.touches >= 2) | (te.sd_snap_share >= 0.30))]
        for a in absent.itertuples():
            room = te[(te.team == a.team) & ~te.is_out & (te.touches >= 0.5)
                      & ((te.sd_snap_share >= 0.10) | (te.touches >= 2))]
            if room.empty:
                continue
            lead = (room.sd_snap_share.max() if len(room) else 0) <= a.sd_snap_share
            role = "starter" if lead else "no2"
            a_weeks = present.get(a.player_id, set())
            for h in room.itertuples():
                hw = present.get(h.player_id, set())
                # Weight 0 is kept: no boost, but the board then knows he has
                # only played without the absent man and can say so.
                wt = round(len(hw & a_weeks) / len(hw), 3) if hw else 0.0
                entries.append({
                    "season": season, "week": week, "position": pos, "team": a.team,
                    "player": h.player_name,
                    "basis": "ranked", "from_player": a.player_name, "absent_role": role,
                    "weight": wt, "depth_rank": None,
                    "reason": f"{a.player_name} is out. Priced on what a player in his spot in the "
                              f"room has historically gained when a {'starter' if role == 'starter' else 'backup'} "
                              f"at his position sat"
                              + (", no boost: he has only played without him" if wt == 0 else
                                 f", scaled to {wt:.0%} because {a.player_name} has already missed games" if wt < 1 else "")
                              + ". Written by dd/heirs.py from Sleeper's injury list."})
    e = pd.DataFrame(entries)
    if verbose and len(e):
        for (pos, frm), g in e.groupby(["position", "from_player"]):
            print(f"  {pos} {frm} ({g.absent_role.iloc[0]}): "
                  + ", ".join(f"{p} x{w:.2f}" for p, w in zip(g.player, g.weight)))
    return e


def write(season: int, week: int) -> pd.DataFrame:
    """Replace this week's automatic rows in role.csv, keep every hand row."""
    e = generate(season, week)
    path = ins.ROLE_FILE
    r = pd.read_csv(path) if path.exists() else pd.DataFrame()
    if len(r):
        auto = (r.week == week) & (r.season == season) & r.reason.fillna("").str.contains("dd/heirs.py")
        r = r[~auto]
    r = pd.concat([r, e], ignore_index=True)
    r.to_csv(path, index=False)
    print(f"  role.csv: {len(e)} automatic rows for {season} week {week}")
    return e
