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

Quarterbacks: each team's starter is the top healthy name on Sleeper's depth
chart (or a hand qb_starts row). If he has not been the starter (under 80% of
the snaps), he is priced on his career starts ("qb_starts" basis,
inseason.career_starts). Every other quarterback is a "backup" and is priced
at zero: a backup is assumed to take no snaps.
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


def fullbacks() -> set:
    """Sleeper's fullbacks, by name key; the roster store keeps only QB-TE."""
    import json
    from .rebound import STORE
    path = STORE / "players.json"
    if not path.exists():
        return set()
    d = json.loads(path.read_text())
    return {bare(v.get("full_name")) for v in d.values() if v.get("position") == "FB" and v.get("full_name")}


def ruled_out(season: int | None = None, week: int | None = None) -> pd.DataFrame:
    from .rebound import _players
    p = _players()
    p = p[p.position.isin(POSITIONS + ("QB",)) & p.injury_status.isin(OUT)].copy()
    p["team"] = p.team.replace(TEAM_FIX)
    p["key"] = p.player.map(bare)
    # A man in returning.csv is playing whatever Sleeper still says: Jordan
    # Mason sat on IR with his thumb after practicing in full, and pricing his
    # backfield for his absence boosted the backs he is about to take work from.
    if ins.RETURNING.exists():
        back = pd.read_csv(ins.RETURNING)
        back = back[(back.season == season) & (back.week == week)]
        p = p[~p.key.isin(set(back.player.map(bare)))]
    return p


def generate(season: int, week: int, verbose: bool = True) -> pd.DataFrame:
    rows = ins.target_rows(season, week)
    weekly = ins.build()
    weekly = weekly[(weekly.season == season) & (weekly.week < week)]
    played = weekly[weekly.snap_share.fillna(0) > 0]
    present = played.groupby("player_id").week.apply(set).to_dict()
    # The weeks each man played for each team. A player traded mid-season
    # (Marvin Harrison Jr., Kaytron Allen) carries his old team's games in the
    # rows above, and pricing his new room for his absence would hand them a
    # boost for losing a teammate they never had.
    with_team = played.groupby(["player_id", "team"]).week.apply(set).to_dict()
    out = ruled_out(season, week)
    entries = []
    for pos in POSITIONS:
        # rankable() drops anyone the official report has marked out, which is
        # exactly who this function is looking for. From Friday's final report
        # on, Mike Evans, Rashee Rice and the rest vanished here and their
        # teammates got nothing. Sleeper's list decides who is out below.
        te = ins.blend(rankable(rows.assign(is_out=0), pos), ins.K_ROLE, ins.K_EFF)
        te = te[te.sd_games.fillna(0) > 0].copy()
        te["key"] = te.player_name.map(bare)
        te["touches"] = te.sd_targets.fillna(0) + te.sd_carries.fillna(0)
        gone = set(zip(out.key, out.team))
        te["is_out"] = [(k, t) in gone for k, t in zip(te.key, te.team)]
        absent = te[te.is_out & ((te.touches >= 2) | (te.sd_snap_share >= 0.30))]
        for a in absent.itertuples():
            room = te[(te.team == a.team) & ~te.is_out & (te.touches >= 0.5)
                      & ((te.sd_snap_share >= 0.10) | (te.touches >= 2))
                      # A fullback blocks on most of his snaps and does not
                      # take a back's carries: Patrick Ricard's 77% of the
                      # snaps ranked him first in Cam Skattebo's room.
                      & ~te.key.isin(fullbacks())]
            if room.empty:
                continue
            a_weeks = with_team.get((a.player_id, a.team), set())
            if not a_weeks:
                if verbose:
                    print(f"  {pos} {a.player_name} ({a.team}): no games for this team this season, "
                          f"so nobody in the room is priced for his absence")
                continue
            lead = (room.sd_snap_share.max() if len(room) else 0) <= a.sd_snap_share
            role = "starter" if lead else "no2"
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
    # Quarterbacks: one starter per team, and every other quarterback is a
    # backup priced at zero. The starter is a hand qb_starts row if there is
    # one, otherwise the healthiest top name on Sleeper's depth chart. A man
    # who has not been the starter (his own numbers under 80% of the snaps)
    # is priced on his career starts, whether the old starter is hurt, traded
    # (Kirk Cousins out of Las Vegas) or benched. Backups were reaching the
    # top 32 on their relief and spot-start games (Joe Fagnano, Shedeur
    # Sanders) above starters with thin histories (Fernando Mendoza).
    from .rebound import _players
    qb = ins.blend(rankable(rows.assign(is_out=0), "QB"), ins.K_ROLE, ins.K_EFF).copy()
    qb["key"] = qb.player_name.map(bare)
    gone = set(zip(out.key, out.team))
    qb["is_out"] = [(k, t) in gone for k, t in zip(qb.key, qb.team)]
    sl = _players()
    sl = sl[sl.position.eq("QB") & sl.team.notna()].copy()
    sl["team"] = sl.team.replace(TEAM_FIX)
    sl["key"] = sl.player.map(bare)
    sl = sl[~sl.injury_status.isin(OUT)]
    hand = pd.read_csv(ins.ROLE_FILE) if ins.ROLE_FILE.exists() else pd.DataFrame()
    if len(hand):
        hand = hand[(hand.season == season) & (hand.week == week) & hand.basis.eq("qb_starts")
                    & ~hand.reason.fillna("").str.contains("dd/heirs.py")]
    for team, room in qb.groupby("team"):
        pick = hand[hand.team.eq(team)].player.map(bare).tolist() if len(hand) else []
        if not pick:
            depth = sl[sl.team.eq(team) & sl.depth.notna()].sort_values("depth")
            pick = depth.key.head(1).tolist()
        if not pick:
            if verbose:
                print(f"  QB {team}: no starter on Sleeper's depth chart, nobody zeroed")
            continue
        top = room[room.key.eq(pick[0])]
        if top.empty:
            if verbose:
                print(f"  QB {team}: starter {pick[0]} is not in the rows, nobody zeroed")
            continue
        h = top.iloc[0]
        others = room[room.key.ne(h.key)]
        if verbose:
            print(f"  QB {team}: {h.player_name} starts")
        if (h.b_snap_share if pd.notna(h.b_snap_share) else 0) < 0.8 and not len(hand[hand.team.eq(team)] if len(hand) else []):
            lead = others.sort_values("b_snap_share", ascending=False, na_position="last")
            hurt = lead[lead.is_out]
            a = hurt.iloc[0].player_name if len(hurt) and (hurt.iloc[0].b_snap_share or 0) >= 0.5 else ""
            why = (f"{a} is out. " if a else
                   f"He is the starter on the depth chart. ")
            entries.append({
                "season": season, "week": week, "position": "QB", "team": team,
                "player": h.player_name, "basis": "qb_starts", "from_player": a,
                "absent_role": "starter", "weight": 1.0, "depth_rank": 1,
                "reason": why + "Priced on his own career starts, part of the boost applied by how many "
                                "he has made. Written by dd/heirs.py from Sleeper's depth chart."})
        for b in others.itertuples():
            entries.append({
                "season": season, "week": week, "position": "QB", "team": team,
                "player": b.player_name, "basis": "backup", "from_player": h.player_name,
                "absent_role": "", "weight": 0.0, "depth_rank": None,
                "reason": f"Backup: {h.player_name} starts, and a backup is assumed to take no snaps. "
                          f"Written by dd/heirs.py from Sleeper's depth chart."})
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
