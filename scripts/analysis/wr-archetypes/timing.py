"""Does it matter WHEN in the season a receiver's points arrived?

    python3 timing.py > TIMING.txt

Two receivers finish the same. One front-loaded it and faded; the other was
quiet until November and closed hot. A third was on the injury report for half
his games. Fantasy discussion treats all three as different. This asks whether
season N+1 does.

Adds two nflverse sources to the panel: the weekly injury report (2009-2025) and
offensive snap share (2012-2025), so "he was playing hurt" and "his role shrank"
stop being assertions and become columns.
"""
import os
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm

from horse_race import loso_r2, sample
from panel import build

warnings.filterwarnings("ignore")
pd.set_option("display.width", 220)
HERE = os.path.dirname(os.path.abspath(__file__))
MIN_GAMES = 10   # a season needs enough games for halves to mean anything


def weekly_splits():
    """Per player-season: how the year broke down, in the order it was played."""
    wk = pd.read_parquet(f"{HERE}/wr_weeks.parquet").copy()
    wk["fantasy_points_ppr"] = wk.fantasy_points_ppr.fillna(0.0)

    # Was he on that week's injury report, and how limited was he?
    ipath = f"{HERE}/injuries.parquet"
    if os.path.exists(ipath):
        inj = pd.read_parquet(ipath)
        # season_type is only populated from 2025 on, so a plain equality filter
        # silently deletes every earlier year. Keep unlabelled rows and lean on
        # the week number instead - postseason weeks never merge onto a
        # regular-season game line anyway.
        if "season_type" in inj.columns:
            inj = inj[inj.season_type.isna() | inj.season_type.eq("REG")]
        inj = inj[inj.week <= 18]
        inj = inj.rename(columns={"gsis_id": "player_id"})
        inj["listed"] = 1.0
        inj["limited"] = inj.practice_status.astype(str).str.contains(
            "Limited|Did Not", case=False, na=False).astype(float)
        inj = inj.drop_duplicates(["season", "week", "player_id"])
        wk = wk.merge(inj[["season", "week", "player_id", "listed", "limited"]],
                      on=["season", "week", "player_id"], how="left")
    wk["listed"] = wk.get("listed", pd.Series(index=wk.index, dtype=float)).fillna(0.0)
    wk["limited"] = wk.get("limited", pd.Series(index=wk.index, dtype=float)).fillna(0.0)

    # Snap share (2012+). The Two Doors study makes snap share the gate a
    # receiver has to pass before targets are even possible, so a snap-share
    # trend is the closest thing in the data to "his role changed mid-season" -
    # as opposed to the same role producing more or fewer points.
    spath = f"{HERE}/snaps.parquet"
    if os.path.exists(spath):
        sn = pd.read_parquet(spath)
        sn = sn[sn.position.eq("WR")] if "position" in sn.columns else sn
        sn = sn.drop_duplicates(["season", "week", "player", "team"])
        wk = wk.merge(
            sn[["season", "week", "player", "team", "offense_pct"]].rename(
                columns={"player": "player_display_name"}),
            on=["season", "week", "player_display_name", "team"], how="left")
    if "offense_pct" not in wk.columns:
        wk["offense_pct"] = np.nan

    rows = []
    for (yr, pid), g in wk.groupby(["season", "player_id"], sort=False):
        g = g.sort_values("week")
        p = g.fantasy_points_ppr.to_numpy(float)
        t = g.targets.fillna(0).to_numpy(float)
        n = len(p)
        if n < MIN_GAMES:
            continue
        h = n // 2
        healthy, hurt = p[g.listed.to_numpy() == 0], p[g.listed.to_numpy() == 1]
        sn = g.offense_pct.to_numpy(float)
        rows.append({
            "season": yr, "player_id": pid,
            "ppg_first_half": p[:h].mean(), "ppg_second_half": p[-h:].mean(),
            "ppg_first4": p[:4].mean(), "ppg_last4": p[-4:].mean(),
            "tpg_first_half": t[:h].mean(), "tpg_second_half": t[-h:].mean(),
            "snap_first_half": np.nanmean(sn[:h]) if np.isfinite(sn[:h]).any() else np.nan,
            "snap_second_half": np.nanmean(sn[-h:]) if np.isfinite(sn[-h:]).any() else np.nan,
            "listed_share": g.listed.mean(), "limited_share": g.limited.mean(),
            "ppg_off_report": healthy.mean() if len(healthy) >= 4 else np.nan,
            "ppg_on_report": hurt.mean() if len(hurt) >= 4 else np.nan,
            "ended_early": float((g.week.max() < g.week.max()) if False else 0.0),
            "last_week": int(g.week.max()),
        })
    return pd.DataFrame(rows)


def game_log(player, season=None):
    """Week by week: snap share, injury report, targets, points."""
    wk = pd.read_parquet(f"{HERE}/wr_weeks.parquet")
    g = wk[wk.player_display_name.str.lower() == player.lower()]
    if not len(g):
        print(f"    no game lines for {player}")
        return
    season = int(season or g.season.max())
    g = g[g.season == season].sort_values("week").copy()
    tg = pd.read_parquet(f"{HERE}/team_games.parquet")
    played_by_team = sorted(tg[(tg.season == season)
                               & (tg.team == g.team.iloc[-1])].week.unique())

    inj = pd.read_parquet(f"{HERE}/injuries.parquet")
    inj = inj[(inj.season == season) & (inj.gsis_id == g.player_id.iloc[0])]
    inj = inj[inj.week <= 18].set_index("week")

    snaps = pd.DataFrame()
    spath = f"{HERE}/snaps.parquet"
    if os.path.exists(spath):
        sn = pd.read_parquet(spath)
        snaps = sn[(sn.season == season) & (sn.player.str.lower() == player.lower())]
        snaps = snaps.drop_duplicates("week").set_index("week")

    print(f"    {player}, {season}\n")
    print(f"      {'wk':>3}  {'opp':<4} {'snap%':>6}  {'tgt':>4} {'pts':>6}   injury report")
    by_week = g.set_index("week")
    for w in played_by_team:
        if w in by_week.index:
            r = by_week.loc[w]
            sp = f"{100 * snaps.loc[w].offense_pct:.0f}%" if w in snaps.index else "-"
            line = f"      {w:>3}  {r.opponent_team:<4} {sp:>6}  {r.targets:>4.0f} {r.fantasy_points_ppr:>6.1f}"
        else:
            line = f"      {w:>3}  {'-':<4} {'-':>6}  {'-':>4} {'DNP':>6}"
        if w in inj.index:
            i = inj.loc[w]
            note = " / ".join(str(x) for x in
                              [i.report_primary_injury, i.report_status, i.practice_status]
                              if pd.notna(x) and str(x) != "nan")
            line += f"   {note}"
        print(line)


def split_at_report(player, season):
    """Before vs after the first week he shows up on the injury report."""
    wk = pd.read_parquet(f"{HERE}/wr_weeks.parquet")
    g = wk[(wk.player_display_name.str.lower() == player.lower())
           & (wk.season == season)].sort_values("week")
    inj = pd.read_parquet(f"{HERE}/injuries.parquet")
    inj = inj[(inj.season == season) & (inj.gsis_id == g.player_id.iloc[0]) & (inj.week <= 18)]
    if not len(inj):
        print(f"    {player:<20} never appeared on the {season} injury report")
        return
    first = int(inj.week.min())
    pre, post = g[g.week < first], g[g.week >= first]
    for lab, x in (("before", pre), ("from wk %d" % first, post)):
        if not len(x):
            continue
        print(f"    {player:<20} {lab:<10} {len(x):>2}g  {x.targets.mean():>4.1f} tgt/g"
              f"  {x.fantasy_points_ppr.mean():>5.2f} ppg"
              f"  {x.receiving_yards.mean():>5.1f} yds/g"
              f"  {x.receiving_tds.sum():>2.0f} TD")
    print()


def rule(title, char="="):
    print("\n" + char * 78)
    print(title)
    print(char * 78)


def race(s, specs, y="next_ppg_c"):
    for cols in specs:
        r2, _ = loso_r2(s, cols, y)
        print(f"    {' + '.join(cols):<44} cv R2 = {r2:.4f}")


def weights(s, cols, y="next_ppg_c", label=""):
    z = pd.DataFrame({c: (s[c] - s[c].mean()) / s[c].std(ddof=0) for c in cols})
    X = pd.concat([z, pd.get_dummies(s.season, prefix="y", drop_first=True).astype(float)], axis=1)
    f = sm.OLS(s[y].to_numpy(float), sm.add_constant(X)).fit(cov_type="HC3")
    print(f"    {label}")
    for c in cols:
        print(f"      {c:<24} {f.params[c]:+.3f} ppg/sd   t = {f.tvalues[c]:+.2f}"
              f"   p = {f.pvalues[c]:.3f}")


def main():
    df = build()
    sp = weekly_splits()
    s = sample(df).merge(sp, on=["season", "player_id"], how="inner")
    s["trend_ppg"] = s.ppg_second_half - s.ppg_first_half
    s["trend_tpg"] = s.tpg_second_half - s.tpg_first_half
    s["trend_snap"] = s.snap_second_half - s.snap_first_half
    s["snap_share"] = (s.snap_first_half + s.snap_second_half) / 2
    s["ppg_ex_td"] = (s.ppr - 6 * s.rec_tds) / s.games
    s["td_per_target"] = s.td_per_target.fillna(0.0)
    # Missed games that all sit at the end of the year: the season was shut down
    # rather than interrupted.
    s["shut_down"] = ((s.missed >= 3) & (s.last_week <= s.team_games - 3)).astype(float)
    s["interrupted"] = ((s.missed >= 3) & (s.shut_down == 0)).astype(float)

    rule("THE SAMPLE")
    print(f"WR-seasons with {MIN_GAMES}+ games, 2009-2024: {len(s):,}")
    print(f"Injury report merged for {100 * (s.listed_share > 0).mean():.0f}% of them; "
          f"the median receiver appears on it in "
          f"{100 * s.listed_share.median():.0f}% of his games.")

    # ------------------------------------------------------------------ 1 ---
    rule("1. WHICH HALF OF THE SEASON PREDICTS NEXT SEASON")
    print("Leave-one-season-out R2 on next-year points per game.\n")
    race(s, [["ppg"], ["ppg_first_half"], ["ppg_second_half"],
             ["ppg_first_half", "ppg_second_half"], ["ppg", "trend_ppg"],
             ["ppg_first4"], ["ppg_last4"], ["ppg", "ppg_last4"], ["ppg", "ppg_first4"]])
    print()
    weights(s, ["ppg_first_half", "ppg_second_half"],
            label="Both halves in one regression (season FE, HC3):")
    print()
    weights(s, ["ppg", "trend_ppg"],
            label="Full-season scoring plus the trend on top of it:")

    # ------------------------------------------------------------------ 2 ---
    rule("2. A VOLUME TREND VS A SCORING TREND")
    print("A fade in targets is a role change. A fade in points at the same")
    print("targets is variance. Do they behave differently?\n")
    race(s, [["ppg", "trend_ppg"], ["ppg", "trend_tpg"], ["ppg", "trend_ppg", "trend_tpg"]])
    print()
    weights(s, ["ppg", "trend_ppg", "trend_tpg"], label="All three together:")

    print("\n    Next season by quartile of each trend, holding the full-season")
    print("    finish inside the top 36:\n")
    top = s[s.finish <= 36]
    for col in ("trend_ppg", "trend_tpg"):
        q = pd.qcut(top[col], 4, labels=["fell hard", "fell", "rose", "rose hard"])
        g = top.groupby(q, observed=True).agg(
            n=("player_id", "size"), med_next=("next_finish_c", "median"),
            top24=("next_top24", "mean"), next_ppg=("next_ppg_c", "mean"))
        g["top24"] = 100 * g.top24
        print(f"    {col}")
        print(g.to_string(float_format="{:.1f}".format))
        print()

    snapped = s.dropna(subset=["trend_snap", "snap_share"])
    print(f"\n    And the trend in SNAP share - the role itself rather than what")
    print(f"    the role produced (2012 on, n = {len(snapped):,}):\n")
    race(snapped, [["ppg"], ["ppg", "trend_snap"], ["ppg", "snap_share"],
                   ["ppg", "snap_share", "trend_snap"],
                   ["ppg", "snap_share", "trend_snap", "trend_tpg"]])
    print()
    weights(snapped, ["ppg", "snap_share", "trend_snap"],
            label="Scoring rate, snap share, and the change in snap share:")
    print("\n    Next season by quartile of the snap-share trend, top-36 finishers:\n")
    tops = snapped[snapped.finish <= 36]
    q = pd.qcut(tops.trend_snap, 4, labels=["role shrank", "flat-", "flat+", "role grew"])
    gg = tops.groupby(q, observed=True).agg(
        n=("player_id", "size"), med_next=("next_finish_c", "median"),
        top24=("next_top24", "mean"), next_ppg=("next_ppg_c", "mean"))
    gg["top24"] = 100 * gg.top24
    print(gg.to_string(float_format="{:.1f}".format))

    # ------------------------------------------------------------------ 3 ---
    rule("3. TOUCHDOWNS: THE USUAL ENGINE OF A HOT START")
    print("Points per game with receiving touchdowns stripped out, against")
    print("points per game as scored.\n")
    race(s, [["ppg"], ["ppg_ex_td"], ["ppg", "ppg_ex_td"], ["ppg_ex_td", "td_per_target"]])
    print()
    weights(s, ["ppg_ex_td", "td_per_target"],
            label="Non-touchdown scoring rate against touchdown rate:")

    # ------------------------------------------------------------------ 4 ---
    rule("4. SHUT DOWN AT THE END VS INTERRUPTED IN THE MIDDLE")
    print("Among receivers who missed 3+ games, does it matter whether the")
    print("absence was the end of the season or a gap inside it?\n")
    hurt = s[s.missed >= 3]
    for label, sel in [("shut down (missed the last 3+)", hurt.shut_down == 1),
                       ("interrupted (played after returning)", hurt.interrupted == 1)]:
        g = hurt[sel]
        print(f"    {label:<38} n = {len(g):>4}   median next "
              f"WR{g.next_finish_c.median():>5.0f}   top-24 {100 * g.next_top24.mean():>5.1f}%"
              f"   next ppg {g.next_ppg_c.mean():>5.2f}")
    print()
    weights(hurt, ["ppg", "shut_down"], label="With scoring rate held fixed:")

    # ------------------------------------------------------------------ 5 ---
    rule("5. SHOULD YOU DISCOUNT GAMES HE PLAYED WHILE ON THE INJURY REPORT?")
    print("Points per game over the games he entered off the report, against")
    print("points per game over the games he entered on it. Both need 4+ games,")
    print("so this runs on the receivers who had a real amount of each.\n")
    sub = s.dropna(subset=["ppg_off_report", "ppg_on_report"])
    if len(sub) < 100:
        print(f"    only {len(sub)} receiver-seasons have 4+ games on each side "
              f"- not enough to run this. Skipping.")
        return
    print(f"    n = {len(sub):,} receiver-seasons with 4+ games each side")
    print(f"    mean ppg off the report {sub.ppg_off_report.mean():.2f}, "
          f"on it {sub.ppg_on_report.mean():.2f} "
          f"(difference {sub.ppg_off_report.mean() - sub.ppg_on_report.mean():+.2f})\n")
    race(sub, [["ppg"], ["ppg_off_report"], ["ppg_on_report"],
               ["ppg_off_report", "ppg_on_report"], ["ppg", "ppg_off_report"]])
    print()
    weights(sub, ["ppg_off_report", "ppg_on_report"],
            label=("Both in one regression. If the healthy games told you more, the\n"
                   "    first coefficient would carry and the second would not:"))
    weights(s, ["ppg", "listed_share", "limited_share"],
            label="\n    And whether being on the report a lot is itself a signal:")

    # ------------------------------------------------------------------ 6 ---
    rule("6. THE 2025 GAME LOGS")
    print("What the injury report and the snap counts actually say, week by week.\n")
    for who in ("Rome Odunze", "Parker Washington", "Brian Thomas Jr."):
        game_log(who, 2025)
        print()
    print("  Split around the first week each appears on the injury report:\n")
    split_at_report("Rome Odunze", 2025)
    split_at_report("Parker Washington", 2025)
    split_at_report("Brian Thomas Jr.", 2025)


if __name__ == "__main__":
    main()
