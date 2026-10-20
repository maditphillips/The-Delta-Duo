"""Build one row per team-season: the team's alpha WR, team quality, and his injury-missed games."""
import pandas as pd

YEARS = range(2009, 2026)
D = "data/"

# ---- team games and quality ----
g = pd.read_csv(D + "games.csv")
g = g[(g.game_type == "REG") & g.result.notna() & g.season.between(2008, 2025)]
home = pd.DataFrame({"season": g.season, "week": g.week, "team": g.home_team,
                     "margin": g.result, "spread": g.spread_line})
away = pd.DataFrame({"season": g.season, "week": g.week, "team": g.away_team,
                     "margin": -g.result, "spread": -g.spread_line})
tg = pd.concat([home, away])  # spread > 0 = team favored
tg["win"] = (tg.margin > 0) + 0.5 * (tg.margin == 0)
# team abbreviations changed (OAK->LV, SD->LAC, STL->LA); map old to new so prior year lines up
REN = {"OAK": "LV", "SD": "LAC", "STL": "LA"}
tg["team"] = tg.team.replace(REN)
tq = tg.groupby(["season", "team"]).agg(win_pct=("win", "mean"), games=("win", "size")).reset_index()
early = tg[tg.week <= 4].groupby(["season", "team"]).spread.mean().rename("early_spread").reset_index()
tq = tq.merge(early, on=["season", "team"])
prior = tq[["season", "team", "win_pct"]].assign(season=lambda d: d.season + 1).rename(columns={"win_pct": "prior_win_pct"})
tq = tq.merge(prior, on=["season", "team"], how="left")

def fix_team(s):
    return s.replace(REN | {"LAR": "LA", "JAC": "JAX", "ARZ": "ARI", "BLT": "BAL", "CLV": "CLE", "HST": "HOU"})

rows = []
for y in YEARS:
    s = pd.read_csv(D + f"stats_player_week_{y}.csv", low_memory=False)
    s = s[s.season_type == "REG"].copy()
    s["team"] = fix_team(s.team)
    inj = pd.read_csv(D + f"injuries_{y}.csv")
    inj = inj[inj.game_type == "REG"]
    inj["team"] = fix_team(inj.team)
    ros = pd.read_csv(D + f"roster_weekly_{y}.csv", low_memory=False)
    ros = ros[ros.game_type == "REG"]
    ros["team"] = fix_team(ros.team)
    weeks = tg[tg.season == y]

    # stats position can be stale (2015 Jordan Matthews shows as TE); use that season's roster position
    rpos = ros.dropna(subset=["position"]).groupby("gsis_id").position.agg(lambda x: x.mode().iloc[0])
    s = s.assign(pos=s.player_id.map(rpos).fillna(s.position))
    # team WR targets; alpha = most targets per game played for that team (min 6 games)
    wr = s[s.pos == "WR"]
    per = wr.groupby(["team", "player_id"]).agg(name=("player_display_name", "first"), gp=("week", "nunique"),
                                                tgt=("targets", "sum"), ppr=("fantasy_points_ppr", "sum"),
                                                first_week=("week", "min"), last_week=("week", "max")).reset_index()
    per = per[per.gp >= 6]
    per["tpg"] = per.tgt / per.gp
    team_wk_tgt = s.groupby(["team", "week"]).targets.sum()
    alpha = per.sort_values("tpg", ascending=False).groupby("team").head(1)
    # also flag who led in raw season targets (robustness)
    lead_raw = per.sort_values("tgt", ascending=False).groupby("team").head(1).set_index("team").player_id

    for _, a in alpha.iterrows():
        t, pid = a.team, a.player_id
        tw = weeks[weeks.team == t].week.sort_values()
        r = ros[(ros.gsis_id == pid)]
        pinj = inj[(inj.gsis_id == pid)]
        ps = s[s.player_id == pid]
        # tenure: whole season unless he shows up for another team (trade / release)
        seen = pd.concat([ps[["week", "team"]], r[["week", "team"]], pinj[["week", "team"]]])
        here, other = seen[seen.team == t].week, seen[seen.team != t].week
        lo = other[other < here.min()].max() + 1 if (other < here.min()).any() else 1
        hi = other[other > here.max()].min() - 1 if (other > here.max()).any() else 99
        tw = tw[(tw >= lo) & (tw <= hi)]
        played = set(ps[ps.team == t].week)
        out_wk = set(pinj[pinj.report_status.isin(["Out", "Doubtful"])].week)
        listed_wk = set(pinj.week)
        # reserve weeks that are injury-related: IR, IR-return, PUP, NFI, injury settlement.
        # Older seasons have no code; plain RES then is almost always IR. Suspension (R40),
        # left squad / illness (R27, R30) and the like don't count.
        code = r.status_description_abbr.fillna("") if "status_description_abbr" in r else pd.Series("", index=r.index)
        res_wk = set(r[r.status.isin(["RES", "PUP"]) & code.isin(["", "R01", "R04", "R05", "R23", "R48"])].week)
        sus_wk = set(r[(r.status == "SUS") | (code == "R40")].week)
        missed = [w for w in tw if w not in played]
        # a missed game is an injury game if he was on the injury report / reserve list that week,
        # or the last thing we saw before it was an injury (players on IR drop off the report)
        inj_missed, hurt = [], False
        for w in tw:
            if w in played:
                hurt = False
            elif w in listed_wk or w in res_wk:
                hurt = True
                inj_missed.append(w)
            elif hurt:
                inj_missed.append(w)
            elif played and w > max(played) and w not in sus_wk and sum(x > max(played) for x in tw) >= 2:
                # gone for the rest of the season with no report: in-game injury, IR before the next
                # report (2015 Keenan Allen kidney, 2014 Brandin Cooks thumb). Needs 2+ games left so
                # a healthy starter resting in the finale isn't counted.
                hurt = True
                inj_missed.append(w)
            # otherwise (pre-debut weeks, suspensions, healthy scratches) it's not an injury game
        # injury spells = runs of consecutive injury-missed team games
        spells, prev = 0, None
        tw_list = list(tw)
        for w in tw_list:
            if w in inj_missed:
                if prev is None or tw_list.index(w) - tw_list.index(prev) > 1:
                    spells += 1
                prev = w
        dob = r.birth_date.dropna()
        age = (pd.Timestamp(f"{y}-09-01") - pd.to_datetime(dob.iloc[0])).days / 365.25 if len(dob) else None
        ever_res = bool(res_wk & set(tw))
        rows.append(dict(season=y, team=t, player_id=pid, name=a["name"], age=age,
                         team_games=len(tw), games_played=len(played & set(tw)),
                         missed=len(missed), inj_missed=len(inj_missed), inj_spells=spells,
                         inj_missed_late=sum(w >= 13 for w in inj_missed),
                         ir=ever_res, tgt_per_game=a.tpg, tgt_share=a.tgt / team_wk_tgt[t].reindex(sorted(played & set(tw))).sum(),
                         ppr_per_game=a.ppr / a.gp, also_raw_leader=lead_raw[t] == pid))

df = pd.DataFrame(rows).merge(tq, on=["season", "team"], how="left")
df.to_csv("alpha_wrs.csv", index=False)
print(len(df), "team-seasons;", df.win_pct.isna().sum(), "missing team quality")
print(df.describe().T[["mean", "min", "max"]])
