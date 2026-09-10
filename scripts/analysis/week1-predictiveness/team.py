"""Week 1 as a team-level signal: wins, margin, EPA, playoffs, and the market.

Sections
  1. 1-0 vs 0-1: rest-of-season win rate, final wins, playoff and division rates.
  2. Week 1 margin and Week 1 EPA/play as continuous predictors of the rest of
     the season, each against a prior-season baseline and then jointly.
  3. Score vs process: does Week 1 EPA per play beat the Week 1 scoreboard? The same
     race is run at 1, 2, 4 and 8 weeks of data. Note the EPA here is offensive minus
     defensive pass-and-rush EPA per play, so it excludes special teams and penalty
     plays that the scoreboard does capture.
  4. Blowouts: does the size of a Week 1 win carry more than the fact of it?
  5. The market test. Betting lines already price everything the public knew in
     August. If Week 1 carried information the market underrated, 1-0 teams would
     beat the closing spread over the rest of the season. Do they?

Written to TEAM.txt.
"""
import numpy as np
import pandas as pd
import common as C


def team_games(g):
    """One row per team-game, from each team's own point of view."""
    home = g.assign(team=g.home_team, opp=g.away_team,
                    pts=g.home_score, pts_opp=g.away_score,
                    spread=g.spread_line)          # spread_line is home-team points favoured
    away = g.assign(team=g.away_team, opp=g.home_team,
                    pts=g.away_score, pts_opp=g.home_score,
                    spread=-g.spread_line)
    cols = ["season", "week", "game_type", "team", "opp", "pts", "pts_opp", "spread"]
    d = pd.concat([home[cols], away[cols]], ignore_index=True)
    d["margin"] = d.pts - d.pts_opp
    d["win"] = np.where(d.margin > 0, 1.0, np.where(d.margin < 0, 0.0, 0.5))
    d["ats_margin"] = d.margin - d.spread          # >0 = covered
    return d


def team_epa():
    """Offensive and defensive EPA per play per team-game, from team week stats."""
    t = pd.read_parquet(f"{C.HERE}/team_week.parquet")
    t = t[(t.season_type == "REG") & (t.season <= C.LAST_SEASON)].copy()
    for c in ("attempts", "carries", "sacks_suffered", "passing_epa", "rushing_epa"):
        t[c] = pd.to_numeric(t[c], errors="coerce").fillna(0)
    t["plays"] = t.attempts + t.carries + t.sacks_suffered
    t["epa"] = t.passing_epa + t.rushing_epa
    t["off_epa"] = np.where(t.plays > 0, t.epa / t.plays, np.nan)
    o = t[["season", "week", "team", "off_epa", "plays"]]
    d = t[["season", "week", "opponent_team", "off_epa"]].rename(
        columns={"opponent_team": "team", "off_epa": "def_epa"})
    m = o.merge(d, on=["season", "week", "team"], how="inner")
    m["epa_diff"] = m.off_epa - m.def_epa
    return m


def build(g):
    tg = team_games(g)
    reg = tg[tg.game_type == "REG"]
    post = tg[tg.game_type != "REG"].groupby(["season", "team"]).size().rename("post_games")

    w1 = reg[reg.week == 1].set_index(["season", "team"])
    ros = reg[reg.week >= 2].groupby(["season", "team"]).agg(
        ros_games=("win", "size"), ros_win=("win", "mean"),
        ros_margin=("margin", "mean"), ros_ats=("ats_margin", "mean"),
        ros_cover=("ats_margin", lambda s: float((s > 0).mean())))
    full = reg.groupby(["season", "team"]).agg(
        wins=("win", "sum"), games=("win", "size"), margin=("margin", "mean"))

    epa = team_epa()
    e1 = epa[epa.week == 1].set_index(["season", "team"])[["off_epa", "def_epa", "epa_diff"]]
    eros = epa[epa.week >= 2].groupby(["season", "team"])[["off_epa", "def_epa", "epa_diff"]].mean()
    efull = epa.groupby(["season", "team"])[["off_epa", "def_epa", "epa_diff"]].mean()

    d = pd.DataFrame(index=full.index)
    d["w1_win"] = w1.win
    d["w1_margin"] = w1.margin
    d["w1_spread"] = w1.spread
    d["w1_epa_diff"] = e1.epa_diff
    d["w1_off_epa"] = e1.off_epa
    d["w1_def_epa"] = e1.def_epa
    d = d.join(ros).join(full[["wins", "games", "margin"]])
    d["ros_epa_diff"] = eros.epa_diff
    d["playoffs"] = post.reindex(d.index).notna().astype(int)

    prior = full.join(efull).reset_index()
    prior["season"] = prior.season + 1
    prior = prior.set_index(["season", "team"])
    d["prior_win_pct"] = (prior.wins / prior.games).reindex(d.index)
    d["prior_margin"] = prior.margin.reindex(d.index)
    d["prior_epa_diff"] = prior.epa_diff.reindex(d.index)
    return d.reset_index().dropna(subset=["w1_win", "ros_win"])


def compare(d, target, preds, labels):
    """R2 of each predictor set for the same target on the same rows."""
    cols = [target] + sorted({c for p in preds for c in p})
    dd = d[np.isfinite(d[cols]).all(axis=1)]
    y = C.z(dd[target])
    out = [("n", len(dd))]
    for p, lab in zip(preds, labels):
        _, r2 = C.ols(y, np.column_stack([C.z(dd[c]) for c in p]))
        out.append((lab, r2))
    return out


def crossover(k):
    """Margin vs EPA/play over the first k weeks, predicting the margin after them."""
    g = C.load_games()
    tg = team_games(g)
    reg = tg[tg.game_type == "REG"]
    early = reg[reg.week <= k].groupby(["season", "team"]).margin.mean().rename("e_margin")
    late = reg[reg.week > k].groupby(["season", "team"]).margin.mean().rename("l_margin")
    epa = team_epa()
    e_epa = epa[epa.week <= k].groupby(["season", "team"]).epa_diff.mean().rename("e_epa")
    d = pd.concat([early, late, e_epa], axis=1).dropna()
    y = C.z(d.l_margin)
    _, r2m = C.ols(y, np.column_stack([C.z(d.e_margin)]))
    _, r2e = C.ols(y, np.column_stack([C.z(d.e_epa)]))
    beta, _ = C.ols(y, np.column_stack([C.z(d.e_margin), C.z(d.e_epa)]))
    return dict(k=k, n=len(d), r2_margin=r2m, r2_epa=r2e,
                b_margin=beta[1], b_epa=beta[2])


def champions(g):
    """Where did the eventual conference and Super Bowl winners stand after Week 1?"""
    tg = team_games(g)
    w1 = tg[(tg.game_type == "REG") & (tg.week == 1)].set_index(["season", "team"]).win
    sb = g[g.game_type == "SB"]
    winners = pd.DataFrame({
        "season": sb.season,
        "team": np.where(sb.home_score > sb.away_score, sb.home_team, sb.away_team)})
    out = {}
    for lab, frame in (("Super Bowl winners", winners),
                       ("Super Bowl teams", pd.DataFrame({
                           "season": list(sb.season) * 2,
                           "team": list(sb.home_team) + list(sb.away_team)}))):
        w = w1.reindex(pd.MultiIndex.from_frame(frame[["season", "team"]])).dropna()
        out[lab] = (len(w), float((w == 0).mean()))
    return out


def main():
    g = C.load_games()
    d = build(g)
    print("=" * 100)
    print("WEEK 1 AS A TEAM SIGNAL")
    print(f"regular seasons {C.FIRST_SEASON}-{C.LAST_SEASON}, {len(d)} team-seasons")
    print("=" * 100)

    print("\n1. 1-0 VS 0-1")
    print(f"   {'week 1':<12}{'n':>6}{'ROS win%':>10}{'final wins':>12}"
          f"{'playoffs':>10}{'11+ win szn':>13}{'ROS margin':>12}")
    for lab, sub in (("won", d[d.w1_win == 1]), ("lost", d[d.w1_win == 0]),
                     ("tied", d[d.w1_win == 0.5])):
        if len(sub) < 5:
            continue
        pct = sub.wins / sub.games
        print(f"   {lab:<12}{len(sub):>6}{sub.ros_win.mean()*100:>9.1f}%"
              f"{(pct*17).mean():>12.1f}{sub.playoffs.mean()*100:>9.1f}%"
              f"{(pct >= 11/17).mean()*100:>12.1f}%{sub.ros_margin.mean():>12.2f}")
    won, lost = d[d.w1_win == 1], d[d.w1_win == 0]
    print(f"\n   gap in rest-of-season win rate: "
          f"{(won.ros_win.mean()-lost.ros_win.mean())*100:.1f} points"
          f"  ({(won.ros_win.mean()-lost.ros_win.mean())*16:.1f} wins over a 16-game stretch)")
    print(f"   playoff rate: {won.playoffs.mean()*100:.0f}% at 1-0 vs "
          f"{lost.playoffs.mean()*100:.0f}% at 0-1")

    print("\n   ... and split by whether last season was already good:")
    print(f"   {'prior season':<22}{'week 1':<8}{'n':>6}{'ROS win%':>10}{'playoffs':>10}")
    for plab, pm in (("winning record", d.prior_win_pct > 0.5),
                     ("losing record", d.prior_win_pct <= 0.5)):
        for wlab, wm in (("won", d.w1_win == 1), ("lost", d.w1_win == 0)):
            s = d[pm & wm & d.prior_win_pct.notna()]
            print(f"   {plab:<22}{wlab:<8}{len(s):>6}{s.ros_win.mean()*100:>9.1f}%"
                  f"{s.playoffs.mean()*100:>9.1f}%")

    print("\n2. WEEK 1 AS A CONTINUOUS PREDICTOR")
    for target, tlab in (("ros_win", "rest-of-season win rate"),
                         ("ros_margin", "rest-of-season point margin/game"),
                         ("ros_epa_diff", "rest-of-season EPA/play differential")):
        res = compare(
            d, target,
            [["w1_margin"], ["w1_epa_diff"], ["prior_margin"], ["prior_epa_diff"],
             ["prior_epa_diff", "w1_margin"], ["prior_epa_diff", "w1_epa_diff"],
             ["prior_epa_diff", "w1_epa_diff", "w1_margin"]],
            ["W1 margin", "W1 EPA/play", "last yr margin", "last yr EPA/play",
             "last yr EPA + W1 margin", "last yr EPA + W1 EPA", "last yr EPA + both W1"])
        print(f"\n   target: {tlab}   (n={res[0][1]})")
        for lab, r2 in res[1:]:
            print(f"     R2  {lab:<28}{r2:>7.3f}")

    print("\n3. SCORE VS PROCESS")
    dd = d[np.isfinite(d[["w1_margin", "w1_epa_diff", "ros_margin"]]).all(axis=1)]
    print(f"   r(W1 margin,   ROS margin) = {np.corrcoef(dd.w1_margin, dd.ros_margin)[0,1]:.3f}")
    print(f"   r(W1 EPA/play, ROS margin) = {np.corrcoef(dd.w1_epa_diff, dd.ros_margin)[0,1]:.3f}")
    beta, r2 = C.ols(C.z(dd.ros_margin),
                     np.column_stack([C.z(dd.w1_epa_diff), C.z(dd.w1_margin)]))
    print(f"   both together: beta(EPA)={beta[1]:.3f}  beta(margin)={beta[2]:.3f}  R2={r2:.3f}")
    print("\n   the same race at k weeks of data, target = margin over weeks k+1 onward:")
    print(f"   {'k weeks':<10}{'n':>6}{'R2 margin':>12}{'R2 EPA/play':>13}"
          f"{'| beta margin':>15}{'beta EPA':>11}")
    for k in (1, 2, 4, 8):
        r = crossover(k)
        print(f"   {k:<10}{r['n']:>6}{r['r2_margin']:>12.3f}{r['r2_epa']:>13.3f}"
              f"{r['b_margin']:>15.3f}{r['b_epa']:>11.3f}")
    print("   -> point margin matches or beats this EPA/play measure at every sample")
    print("      size tested, and takes most of the weight when both are in the model.")
    print("      Caveat: the EPA measure covers pass and rush plays only, so special")
    print("      teams and penalties count for the scoreboard and not for EPA. The")
    print("      honest read is that over one game they are interchangeable -- there is")
    print("      no Week 1 'process beats results' edge to be had here.")

    print("\n4. BLOWOUTS")
    print(f"   {'week 1 result':<24}{'n':>6}{'ROS win%':>10}{'playoffs':>10}{'ROS margin':>12}")
    bins = [(-99, -21, "lost by 21+"), (-21, -9, "lost by 9-20"), (-9, 0, "lost by 1-8"),
            (0, 9, "won by 1-8"), (9, 21, "won by 9-20"), (20, 99, "won by 21+")]
    for lo, hi, lab in bins:
        s = d[(d.w1_margin > lo) & (d.w1_margin <= hi)]
        if len(s) < 20:
            continue
        print(f"   {lab:<24}{len(s):>6}{s.ros_win.mean()*100:>9.1f}%"
              f"{s.playoffs.mean()*100:>9.1f}%{s.ros_margin.mean():>12.2f}")

    print("\n5. THE MARKET TEST  (does Week 1 tell you something the betting market missed?)")
    m = d[d.ros_ats.notna() & d.ros_cover.notna()]
    print(f"   {'week 1':<16}{'n':>6}{'ROS cover %':>13}{'ROS margin vs spread':>23}")
    for lab, sub in (("won", m[m.w1_win == 1]), ("lost", m[m.w1_win == 0])):
        print(f"   {lab:<16}{len(sub):>6}{sub.ros_cover.mean()*100:>12.1f}%"
              f"{sub.ros_ats.mean():>23.2f}")
    for lab, sub in (("won by 21+", m[m.w1_margin >= 21]),
                     ("lost by 21+", m[m.w1_margin <= -21])):
        print(f"   {lab:<16}{len(sub):>6}{sub.ros_cover.mean()*100:>12.1f}%"
              f"{sub.ros_ats.mean():>23.2f}")
    mm = m[np.isfinite(m[["w1_margin", "ros_ats"]]).all(axis=1)]
    print(f"   r(W1 margin, ROS margin against the spread) = "
          f"{np.corrcoef(mm.w1_margin, mm.ros_ats)[0,1]:.3f}"
          f"   (n={len(mm)}, seasons with lines only)")
    print("   -> the market absorbs Week 1 almost immediately; the residual edge is ~0.")

    print("\n6. WHERE THE EVENTUAL CHAMPIONS STOOD AFTER WEEK 1")
    for lab, (n, share) in champions(g).items():
        print(f"   {lab:<22}n={n:>4}   started 0-1: {share*100:>5.1f}%")

    d.to_csv("out_team.csv", index=False)


if __name__ == "__main__":
    main()
