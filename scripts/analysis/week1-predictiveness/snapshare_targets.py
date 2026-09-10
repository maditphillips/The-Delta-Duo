"""Three different rest-of-season targets for snap share, and what a Week 1 value
actually buys you as a prediction.

The main study's target for a share metric is the MEAN OF WEEKLY VALUES over weeks
2 onward, and it excludes Week 1 by construction. Two other targets someone might
reasonably mean are computed here for comparison:

  A  mean of weekly snap %, weeks 2+            (what the study used)
  B  pooled snaps / team snaps, weeks 2+        (cumulative rest of season)
  C  pooled snaps / team snaps, ALL weeks       (end-of-season cumulative)

C contains Week 1 inside it, so part of its correlation with Week 1 is definitional
overlap rather than prediction. The size of that inflation is reported.

Then, for the concrete question -- a player at 78% in Week 1, what happens next --
the regression line, the residual spread, and the observed distribution of players
who actually opened in that band.

Written to SNAPSHARE.txt.
"""
import numpy as np
import pandas as pd
from scipy import stats
import common as C

BANDS = [(0.30, 0.45), (0.45, 0.60), (0.60, 0.72), (0.72, 0.82), (0.82, 1.01)]


def snap_panel():
    """One row per player-season: Week 1 snap share plus the three targets."""
    s = pd.read_parquet(f"{C.HERE}/snaps.parquet")
    s = s[(s.game_type == "REG") & s.offense_snaps.notna() & (s.offense_pct > 0)].copy()
    s["team_snaps"] = s.offense_snaps / s.offense_pct
    team = s.groupby(["season", "week", "team"]).team_snaps.median().round()
    s = s.merge(team.rename("team_off_snaps"), on=["season", "week", "team"], how="left")

    cw = pd.read_parquet(f"{C.HERE}/players.parquet")
    cw = cw[cw.pfr_id.notna()].drop_duplicates("pfr_id")[["gsis_id", "pfr_id"]]
    s = s.merge(cw, left_on="pfr_player_id", right_on="pfr_id", how="left")
    s = s[s.gsis_id.notna()].rename(columns={"gsis_id": "player_id"})
    s = s.drop_duplicates(["season", "week", "player_id"])

    # position from the weekly stats file, so it matches the rest of the study
    s = s.drop(columns=[c for c in ("position", "pfr_id") if c in s.columns])
    w = C.load_weekly(with_snaps=False)
    pos = w[["player_id", "season", "position"]].drop_duplicates(["player_id", "season"])
    s = s.merge(pos, on=["player_id", "season"], how="inner")
    s = s[s.season <= C.LAST_SEASON]

    g = ["player_id", "season", "position"]
    w1 = s[s.week == 1].groupby(g).agg(
        w1_pct=("offense_pct", "mean"), w1_snaps=("offense_snaps", "sum"),
        w1_team=("team_off_snaps", "sum"))
    ros = s[s.week >= 2].groupby(g).agg(
        A_mean_weekly=("offense_pct", "mean"), ros_snaps=("offense_snaps", "sum"),
        ros_team=("team_off_snaps", "sum"), ros_games=("offense_snaps", "size"))
    full = s.groupby(g).agg(all_snaps=("offense_snaps", "sum"),
                            all_team=("team_off_snaps", "sum"))
    d = w1.join(ros, how="inner").join(full, how="inner").reset_index()
    d["B_pooled_ros"] = d.ros_snaps / d.ros_team
    d["C_pooled_season"] = d.all_snaps / d.all_team
    return d[d.ros_games >= C.MIN_ROS_GAMES]


def fit(x, y):
    sl, ic, r, p, se = stats.linregress(x, y)
    resid = y - (ic + sl * x)
    return dict(n=len(x), slope=sl, intercept=ic, r=r, r2=r * r, p=p,
                se_slope=se, resid_sd=float(resid.std(ddof=2)))


def main():
    d = snap_panel()
    print("=" * 96)
    print("SNAP SHARE: WHICH REST-OF-SEASON TARGET, AND WHAT A WEEK 1 VALUE BUYS")
    print(f"nflverse snap counts {C.SNAP_FIRST}-{C.LAST_SEASON}")
    print("=" * 96)
    print("""
  A  mean of weekly snap %, weeks 2 onward       <- the target the main study used
  B  pooled snaps / team snaps, weeks 2 onward   (cumulative rest of season)
  C  pooled snaps / team snaps, ALL weeks        (end-of-season cumulative)

  C has Week 1 inside it. Part of r(Week 1, C) is that overlap, not prediction.
""")
    for pos in ("RB", "WR", "TE", "QB"):
        s = d[(d.position == pos) & (d.w1_pct >= 0.10)]
        if len(s) < 60:
            continue
        print(f"\n## {pos}   n = {len(s)} player-seasons")
        print(f"   {'target':<34}{'r':>8}{'R2':>8}{'slope':>8}{'intercept':>11}"
              f"{'p':>10}{'resid sd':>10}")
        print("   " + "-" * 86)
        for col, lab in (("A_mean_weekly", "A  mean weekly, weeks 2+"),
                         ("B_pooled_ros", "B  pooled, weeks 2+"),
                         ("C_pooled_season", "C  pooled, whole season")):
            f = fit(s.w1_pct.values, s[col].values)
            p = "<1e-16" if f["p"] < 1e-16 else f"{f['p']:.2g}"
            print(f"   {lab:<34}{f['r']:>8.3f}{f['r2']:>8.3f}{f['slope']:>8.3f}"
                  f"{f['intercept']:>11.3f}{p:>10}{f['resid_sd']:>10.3f}")
        fa = fit(s.w1_pct.values, s.A_mean_weekly.values)
        fc = fit(s.w1_pct.values, s.C_pooled_season.values)
        print(f"   inflation from letting Week 1 sit inside the target: "
              f"r {fa['r']:.3f} -> {fc['r']:.3f} (+{fc['r']-fa['r']:.3f}), "
              f"R2 {fa['r2']:.3f} -> {fc['r2']:.3f}")

    print("\n\n" + "=" * 96)
    print("THE CONCRETE QUESTION: A PLAYER OPENS AT X% OF SNAPS. WHAT HAPPENS NEXT?")
    print("Target A (mean weekly snap %, weeks 2 onward). Week 1 is not in the target.")
    print("=" * 96)
    for pos in ("RB", "WR", "TE"):
        s = d[(d.position == pos) & (d.w1_pct >= 0.10)]
        f = fit(s.w1_pct.values, s.A_mean_weekly.values)
        print(f"\n## {pos}   fitted line: ROS snap % = {f['intercept']:.3f} + "
              f"{f['slope']:.3f} x (Week 1 snap %)")
        print(f"   slope se {f['se_slope']:.3f}, t = {f['slope']/f['se_slope']:.1f}, "
              f"p {'<1e-16' if f['p'] < 1e-16 else f'{f[chr(112)]:.2g}'}, "
              f"residual sd {f['resid_sd']:.3f}, R2 {f['r2']:.3f}")
        print(f"   {'week 1 snap %':<18}{'n':>6}{'fitted':>9}{'observed':>10}"
              f"{'sd':>7}{'p10':>7}{'p25':>7}{'p50':>7}{'p75':>7}{'p90':>7}"
              f"{'  fell 15+ pts':>14}")
        for lo, hi in BANDS:
            b = s[(s.w1_pct >= lo) & (s.w1_pct < hi)]
            if len(b) < 15:
                continue
            mid = b.w1_pct.mean()
            y = b.A_mean_weekly
            q = y.quantile([.1, .25, .5, .75, .9]).values
            drop = float((b.A_mean_weekly < b.w1_pct - 0.15).mean())
            print(f"   {f'{lo:.0%}-{hi if hi<1 else 1:.0%}':<18}{len(b):>6}"
                  f"{f['intercept']+f['slope']*mid:>9.3f}{y.mean():>10.3f}{y.std():>7.3f}"
                  f"{q[0]:>7.2f}{q[1]:>7.2f}{q[2]:>7.2f}{q[3]:>7.2f}{q[4]:>7.2f}"
                  f"{drop*100:>13.0f}%")
        # the specific case asked about
        b = s[(s.w1_pct >= 0.73) & (s.w1_pct <= 0.83)]
        y = b.A_mean_weekly
        lo95 = f["intercept"] + f["slope"] * 0.78 - 1.96 * f["resid_sd"]
        hi95 = f["intercept"] + f["slope"] * 0.78 + 1.96 * f["resid_sd"]
        print(f"   a {pos} at 78% in Week 1: point estimate "
              f"{f['intercept']+f['slope']*0.78:.3f}, 95% prediction interval "
              f"[{max(lo95,0):.2f}, {min(hi95,1):.2f}]")
        print(f"     the {len(b)} {pos}s who actually opened 73-83%: mean "
              f"{y.mean():.3f}, median {y.median():.3f}, "
              f"{(y>=0.70).mean()*100:.0f}% held 70%+, {(y<0.55).mean()*100:.0f}% "
              f"fell under 55%")
    d.to_csv("out_snapshare.csv", index=False)


if __name__ == "__main__":
    main()
