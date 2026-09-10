"""Week 1 from a fantasy manager's chair.

1. Which Week 1 number best predicts rest-of-season fantasy scoring -- the fantasy
   total itself, or the usage underneath it?
2. Rank buckets: if a player finishes top-5 / top-12 in Week 1, how often does he
   finish there over the rest of the way? Compared with the base rate, and with
   what last season already implied.
3. The panic table: last season's stud who lays an egg in Week 1, vs the same stud
   who delivers. How different are their rest-of-season outcomes really?
4. How much of a Week 1 surprise is real -- the weight Week 1 earns against a
   prior-season baseline, which is the same thing as how far to move a projection.
5. The waiver spike: a Week 1 usage jump from a player who had no role last year.

Written to FANTASY.txt.
"""
import numpy as np
import pandas as pd
import common as C

BUCKETS = [(1, 5, "top 5"), (6, 12, "WR2/RB2 (6-12)"), (13, 24, "13-24"),
           (25, 36, "25-36"), (37, 999, "37+")]
FULL_ROS_GAMES = {True: 16, False: 15}      # games left after Week 1, 2021+ / before


def bucket(rank):
    for lo, hi, lab in BUCKETS:
        if lo <= rank <= hi:
            return lab
    return "unranked"


def add_ranks(panel, pos, weekly):
    """Week 1, rest-of-season and prior-season positional ranks, by PPR."""
    p = weekly[weekly.position == pos]
    w1 = p[p.week == 1].groupby(["player_id", "season"]).fantasy_points_ppr.sum()
    ros_tot = p[p.week >= 2].groupby(["player_id", "season"]).fantasy_points_ppr.sum()
    ros_g = p[p.week >= 2].groupby(["player_id", "season"]).size()
    prior = p.groupby(["player_id", "season"]).fantasy_points_ppr.sum()

    d = panel.set_index(["player_id", "season"]).copy()
    d["w1_pts"] = w1
    d["ros_pts"] = ros_tot.reindex(d.index).fillna(0)
    d["ros_g"] = ros_g.reindex(d.index).fillna(0)
    pr = prior.reset_index()
    pr["season"] = pr.season + 1
    d["prior_pts"] = pr.set_index(["player_id", "season"]).fantasy_points_ppr.reindex(d.index)
    d["ros_ppg"] = np.where(d.ros_g > 0, d.ros_pts / d.ros_g, 0.0)

    d = d.reset_index()
    for col, out in (("w1_pts", "w1_rank"), ("ros_pts", "ros_rank"),
                     ("ros_ppg", "ros_ppg_rank"), ("prior_pts", "prior_rank")):
        d[out] = d.groupby("season")[col].rank(ascending=False, method="min")
    for out in ("w1_rank", "ros_rank", "ros_ppg_rank", "prior_rank"):
        d[out.replace("rank", "bucket")] = d[out].apply(
            lambda r: bucket(r) if np.isfinite(r) else "unranked")
    return d


def best_week1_signal(panel, pos):
    """Rank every Week 1 metric by how well it predicts rest-of-season fantasy points."""
    tgt_ppg = "ros_fantasy_ppg_ppr" if pos != "QB" else "ros_fantasy_ppg"
    rows = []
    for m, kind in C.metric_list(pos):
        col = "w1_" + m
        if col not in panel:
            continue
        d = panel[panel.played_ros]
        ok = d[col].notna() & d[tgt_ppg].notna() & np.isfinite(d[col])
        if ok.sum() < 60:
            continue
        rows.append(dict(metric=m, kind=kind, n=int(ok.sum()),
                         r=float(np.corrcoef(d.loc[ok, col], d.loc[ok, tgt_ppg])[0, 1]),
                         rho=float(d.loc[ok, col].rank().corr(d.loc[ok, tgt_ppg].rank()))))
    return pd.DataFrame(rows).sort_values("r", key=abs, ascending=False)


USAGE = {"QB": ["w1_pass_attempts", "w1_qb_carries"],
         "RB": ["w1_rush_share", "w1_target_share"],
         "WR": ["w1_target_share", "w1_air_yards"],
         "TE": ["w1_target_share", "w1_air_yards"]}


def points_vs_usage(panel, pos, add_snaps=False):
    """Head to head: Week 1 fantasy points, Week 1 usage, and both together."""
    tgt = "ros_fantasy_ppg_ppr" if pos != "QB" else "ros_fantasy_ppg"
    pts = "w1_fantasy_ppg_ppr" if pos != "QB" else "w1_fantasy_ppg"
    usage = USAGE[pos] + (["w1_snap_pct"] if add_snaps else [])
    if any(c not in panel for c in usage):
        return None
    prior = "prior_fantasy_ppg_ppr" if pos != "QB" else "prior_fantasy_ppg"
    d = panel[panel.played_ros].copy()
    cols = [tgt, pts, prior] + usage
    d = d[np.isfinite(d[cols]).all(axis=1)]
    if len(d) < 80:
        return None
    y = C.z(d[tgt])
    out = {}
    out["W1 fantasy pts"] = C.ols(y, np.column_stack([C.z(d[pts])]))[1]
    out["W1 usage only"] = C.ols(y, np.column_stack([C.z(d[c]) for c in usage]))[1]
    out["W1 pts + usage"] = C.ols(y, np.column_stack([C.z(d[pts])] + [C.z(d[c]) for c in usage]))[1]
    out["last season only"] = C.ols(y, np.column_stack([C.z(d[prior])]))[1]
    out["last season + W1 pts"] = C.ols(y, np.column_stack([C.z(d[prior]), C.z(d[pts])]))[1]
    out["last season + W1 usage"] = C.ols(
        y, np.column_stack([C.z(d[prior])] + [C.z(d[c]) for c in usage]))[1]
    out["everything"] = C.ols(
        y, np.column_stack([C.z(d[prior]), C.z(d[pts])] + [C.z(d[c]) for c in usage]))[1]
    return len(d), out


def transition(d, top=12):
    """P(rest-of-season finish | Week 1 finish), plus hit rates against the base rate."""
    tab = pd.crosstab(d.w1_bucket, d.ros_bucket, normalize="index")
    order = [l for _, _, l in BUCKETS] + ["unranked"]
    tab = tab.reindex(index=[o for o in order if o in tab.index],
                      columns=[o for o in order if o in tab.columns])
    counts = d.w1_bucket.value_counts()
    return tab, counts


def panic_table(d, top=12):
    """Last season's top-12 who flopped in Week 1 vs the ones who delivered."""
    rows = []
    for prior_top in (True, False):
        for w1_top in (True, False):
            s = d[((d.prior_rank <= top) == prior_top) & ((d.w1_rank <= top) == w1_top)]
            s = s[s.prior_rank.notna()]
            if len(s) < 15:
                continue
            rows.append(dict(
                prior=f"top-{top} last yr" if prior_top else f"outside top-{top} last yr",
                week1=f"top-{top} wk1" if w1_top else f"outside top-{top} wk1",
                n=len(s),
                ros_top12=float((s.ros_rank <= top).mean()),
                ros_top24=float((s.ros_rank <= 24).mean()),
                med_ros_rank=float(s.ros_rank.median()),
                med_ros_ppg=float(s.ros_ppg.median())))
    return pd.DataFrame(rows)


def surprise_weight(panel, pos, metric):
    """Standardised weight Week 1 earns next to last season = how far to move."""
    cols = ["w1_" + metric, "ros_" + metric, "prior_" + metric]
    if any(c not in panel for c in cols):
        return None
    d = panel[panel.played_ros]
    if "w1_den_" + metric in d:                    # rate metric: hold it to a real sample
        for pre in ("ros", "prior"):
            d = d[d[pre + "_den_" + metric].fillna(0) >= C.RATE_MIN_DEN[pos]]
    d = d[np.isfinite(d[cols]).all(axis=1)]
    if len(d) < 80:
        return None
    beta, r2 = C.ols(C.z(d[cols[1]]), np.column_stack([C.z(d[cols[0]]), C.z(d[cols[2]])]))
    w = beta[1] / (beta[1] + beta[2]) if (beta[1] + beta[2]) != 0 else np.nan
    return dict(metric=metric, n=len(d), beta_w1=beta[1], beta_prior=beta[2],
                week1_weight=w, r2=r2)


def waiver_spike(panel, pos):
    """No role last season, big Week 1 role. Does it stick?"""
    role = {"RB": "rush_share", "WR": "target_share", "TE": "target_share",
            "QB": "pass_attempts"}[pos]
    d = panel[panel.played_ros].copy()
    d = d[np.isfinite(d[["w1_" + role, "ros_" + role]]).all(axis=1)]
    had_role = d["prior_" + role].fillna(0)  # no prior line reads as no prior role
    thresh = {"RB": 0.35, "WR": 0.18, "TE": 0.15, "QB": 25}[pos]
    low = {"RB": 0.15, "WR": 0.10, "TE": 0.08, "QB": 15}[pos]
    spike = d[(d["w1_" + role] >= thresh) & (had_role < low)]
    known = d[(d["w1_" + role] >= thresh) & (had_role >= thresh)]
    tgt = "ros_fantasy_ppg_ppr" if pos != "QB" else "ros_fantasy_ppg"
    def line(s, lab):
        if len(s) < 10:
            return f"    {lab:<34} n<10"
        return (f"    {lab:<34} n={len(s):>4}  kept {s['ros_'+role].mean():.3f} of that role"
                f"  ({s['ros_'+role].mean()/s['w1_'+role].mean()*100:>5.1f}% of the Week 1 rate)"
                f"   ROS {s[tgt].mean():.1f} ppg")
    return [line(spike, "out of nowhere in Week 1"),
            line(known, "already had the job last year")]


def main():
    weekly = C._derived(C.load_weekly())
    print("=" * 100)
    print("WEEK 1 AS A FANTASY SIGNAL")
    print("=" * 100)

    for pos in ("QB", "RB", "WR", "TE"):
        panel = C.build_panel(pos, weekly=weekly)
        d = add_ranks(panel, pos, weekly)

        print(f"\n\n{'#'*100}\n## {pos}\n{'#'*100}")

        print("\n1. Which Week 1 number best predicts rest-of-season fantasy points per game?")
        b = best_week1_signal(panel, pos)
        print(f"   {'week 1 metric':<22}{'type':<9}{'n':>6}{'r':>8}{'rho':>8}")
        for _, r in b.head(10).iterrows():
            print(f"   {r.metric:<22}{r.kind:<9}{int(r.n):>6}{r.r:>8.3f}{r.rho:>8.3f}")

        for add_snaps, lab in ((False, f"{C.FIRST_SEASON}+"),
                               (True, f"snap-share era, {C.SNAP_FIRST}+, usage includes snap %")):
            pv = points_vs_usage(panel, pos, add_snaps=add_snaps)
            if not pv:
                continue
            n, out = pv
            print(f"\n   R2 predicting rest-of-season fantasy ppg  [{lab}]  (n={n}):")
            for k, v in out.items():
                print(f"     {k:<26}{v:>7.3f}")

        print("\n2. Week 1 finish -> rest-of-season finish (share of each Week 1 group), PPR totals")
        tab, counts = transition(d)
        print(f"   {'week 1':<18}{'n':>5}  " + "".join(f"{c:>16}" for c in tab.columns))
        for idx, r in tab.iterrows():
            print(f"   {idx:<18}{counts.get(idx, 0):>5}  "
                  + "".join(f"{v*100:>15.0f}%" for v in r.values))
        base12 = float((d.ros_rank <= 12).mean())
        h12 = float((d[d.w1_rank <= 12].ros_rank <= 12).mean())
        hp12 = float((d[d.prior_rank <= 12].ros_rank <= 12).mean())
        print(f"\n   P(top-12 rest of season)      base rate {base12*100:.0f}%"
              f"   | given top-12 in Week 1 {h12*100:.0f}%"
              f"   | given top-12 last season {hp12*100:.0f}%")

        print("\n3. The panic table (players with a prior-season line)")
        pt = panic_table(d)
        if len(pt):
            print(f"   {'last season':<26}{'week 1':<20}{'n':>5}{'top12 ROS':>11}"
                  f"{'top24 ROS':>11}{'med rank':>10}{'med ppg':>9}")
            for _, r in pt.iterrows():
                print(f"   {r.prior:<26}{r.week1:<20}{int(r.n):>5}{r.ros_top12*100:>10.0f}%"
                      f"{r.ros_top24*100:>10.0f}%{r.med_ros_rank:>10.0f}{r.med_ros_ppg:>9.1f}")

        print("\n4. How much of a Week 1 surprise is real? (weight Week 1 earns vs last season)")
        print(f"   {'metric':<22}{'n':>6}{'beta W1':>9}{'beta prior':>12}"
              f"{'W1 share':>10}{'R2':>7}")
        for m, kind in C.metric_list(pos):
            s = surprise_weight(panel, pos, m)
            if s:
                share = (f"{s['week1_weight']*100:>8.0f}%" if s["r2"] >= 0.05
                         else f"{'--':>9}")   # ratio of two ~zero betas means nothing
                print(f"   {m:<22}{s['n']:>6}{s['beta_w1']:>9.3f}{s['beta_prior']:>12.3f}"
                      f"{share}{s['r2']:>7.3f}")

        print("\n5. The waiver spike: a Week 1 role that was not there last season")
        for l in waiver_spike(panel, pos):
            print(l)

        d.to_csv(f"out_ranks_{pos}.csv", index=False)


if __name__ == "__main__":
    main()
