"""Players who may be back and whom the board is likely to underprice.

The playing-time model has learned that a man with no recent games usually
does not play, and for most such men it is right. It is wrong for one who has
been cleared: Zach Charbonnet came off his ACL with no 2026 games, shipped at
0.0 in week 8 and scored 5.9. Pricing every returner as playing was tested and
lost (2022-2025 Spearman 0.8202 -> 0.8180 even when told who suited up), so
the call stays a human one. This lists the candidates so none slips by.

A player is listed when all three hold:
  1. Sleeper has no Out, IR or equivalent tag on him this week.
  2. He has played no games this season, or has missed his team's last two or
     more games (byes not counted).
  3. The games he missed were for injury or a list stay: on IR, PUP, the
     exempt list or reserve, or ruled Out on an official report, earlier this
     season. Without it the list fills with healthy backups who simply have
     not played (Brady Cook, Joe Flacco).
  4. He had a real role, last season (4+ games) or earlier this season:
     a quarterback throwing 20+ passes a game, a back with 8+ carries plus
     targets, a receiver or tight end with 4+ targets.

Marking one as playing is model/data/returning.csv; easing him in is a
role.csv "scale" row. Backs returning from two or more missed games have
historically had about 81% of their usual opportunities and 86% of their
snaps in the first game back, and close to all of it by the second.
"""
from __future__ import annotations

import pandas as pd

from . import ingest, inseason as ins
from .heirs import OUT, TEAM_FIX, bare


def check(season: int, week: int) -> pd.DataFrame:
    from .rebound import _players
    rows = ins.target_rows(season, week)
    rows = rows[rows.position.isin(["QB", "RB", "WR", "TE"])].copy()

    w = ins.build()
    # A stats row is a game played; the snap file misses some players (Kirk).
    w = w[(w.season == season) & (w.week < week)]
    played = w.groupby("player_id").week.apply(lambda x: sorted(set(x)))

    sched = ingest.load("schedules")
    sched = sched[(sched.season == season) & (sched.week < week) & sched.game_type.eq("REG")]
    tw = pd.concat([sched[["week", "home_team"]].rename(columns={"home_team": "team"}),
                    sched[["week", "away_team"]].rename(columns={"away_team": "team"})])
    team_weeks = tw.groupby("team").week.apply(lambda x: sorted(set(x)))

    def gap(pid, team):
        games = played.get(pid, [])
        teamw = team_weeks.get(team, [])
        if not games:
            return 0, None, len(teamw)
        return len(games), games[-1], len([x for x in teamw if x > games[-1]])

    g = [gap(p, t) for p, t in zip(rows.player_id, rows.team)]
    rows["games_now"] = [x[0] for x in g]
    rows["last_game"] = [x[1] for x in g]
    rows["missed"] = [x[2] for x in g]
    rows = rows[(rows.games_now == 0) | (rows.missed >= 2)]

    ros = ingest.load("rosters", [season])
    ros = ros[(ros.week < week) & ros.status.isin(["RES", "EXE", "PUP"])]
    inj = ingest.load("injuries", [season])
    inj = inj[(inj.week < week) & inj.report_status.isin(["Out", "Doubtful"])]
    hurt = set(ros.gsis_id) | set(inj.gsis_id)
    rows = rows[rows.player_id.isin(hurt)]

    # A real role: this season before the absence, or last season.
    snaps_now = rows.get("sd_snap_share").fillna(0)
    snaps_prev = rows.get("snap_share_eb").fillna(0)
    def role(att, car, tgt):
        return ((rows.position.eq("QB") & (att >= 20)) | (rows.position.eq("RB") & (car + tgt >= 8))
                | (rows.position.isin(["WR", "TE"]) & (tgt >= 4)))
    now_role = role(rows.sd_attempts.fillna(0), rows.sd_carries.fillna(0), rows.sd_targets.fillna(0))
    prev_role = role(rows.attempts_per_game.fillna(0), rows.carries_per_game.fillna(0),
                     rows.targets_per_game.fillna(0)) & rows.get("games").fillna(0).ge(4)
    rows = rows[(rows.games_now.gt(0) & now_role) | prev_role].copy()

    # No Out or IR tag on Sleeper today.
    sl = _players()
    sl["team"] = sl.team.replace(TEAM_FIX)
    sl["key"] = sl.player.map(bare)
    tag = dict(zip(zip(sl.key, sl.team), sl.injury_status))
    rows["key"] = rows.player_name.map(bare)
    rows["sleeper"] = [tag.get((k, t)) for k, t in zip(rows.key, rows.team)]
    rows = rows[~rows.sleeper.isin(OUT)]

    back = set()
    if ins.RETURNING.exists():
        r = pd.read_csv(ins.RETURNING)
        back = set(r[(r.season == season) & (r.week == week)].player)
    rows["marked_playing"] = rows.player_name.isin(back)
    rows["role_basis"] = ["this season" if n > 0 and nr else "last season"
                          for n, nr in zip(rows.games_now, now_role.loc[rows.index])]
    rows["snaps"] = [s if b == "this season" else p for s, p, b in
                     zip(snaps_now.loc[rows.index], snaps_prev.loc[rows.index], rows.role_basis)]
    rows["carries"] = [s if b == "this season" else p for s, p, b in
                       zip(rows.sd_carries.fillna(0), rows.carries_per_game.fillna(0), rows.role_basis)]
    rows["targets"] = [s if b == "this season" else p for s, p, b in
                       zip(rows.sd_targets.fillna(0), rows.targets_per_game.fillna(0), rows.role_basis)]
    rows["attempts"] = [s if b == "this season" else p for s, p, b in
                        zip(rows.sd_attempts.fillna(0), rows.attempts_per_game.fillna(0), rows.role_basis)]
    rows = rows.rename(columns={"games": "games_last_season"}).rename(columns={"games_now": "games"})
    cols = ["player_name", "position", "team", "sleeper", "games", "last_game", "missed",
            "role_basis", "snaps", "attempts", "carries", "targets", "marked_playing"]
    return rows[cols].sort_values(["position", "snaps"], ascending=[True, False]).reset_index(drop=True)
