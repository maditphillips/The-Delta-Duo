"""Does Week 1 mean something different for a rookie, and does out-carrying your own
backfield mean more than your raw snap share?

Three things the main study does not cover, all of which matter for reading a
rookie back's debut:

1. ROOKIES. A rookie has no prior season, so Week 1 is a much larger share of
   everything known about him. Does that make his Week 1 more predictive? The
   substitute for a prior season is where he was drafted, so draft round enters
   the rookie models in the slot a prior-season line occupies for a veteran.

2. BACKFIELD-RELATIVE ROLE. "48% of snaps" and "the most snaps of any back on the
   roster" are different facts. Share of the team's RB-room snaps and carries, the
   RB1 flag, and the size of the lead over RB2 are tested against raw team snap
   share as predictors of the rest of the season.

3. EFFICIENCY AS A CLAIM ON FUTURE WORK. The intuition behind "he was clearly the
   best back out there" is not that Week 1 efficiency predicts future efficiency --
   the main study already shows it barely does -- but that it predicts a BIGGER
   ROLE later. That is a different regression, run here: the change in snap share
   from Week 1 to the rest of the season, on Week 1 efficiency, holding Week 1 snap
   share fixed. Efficiency is measured as rush yards over expected per attempt
   (Next Gen, 2016+), which adjusts a carry for its blocking and box count, as well
   as by raw yards per carry.

Written to ROOKIES.txt.
"""
import numpy as np
import pandas as pd
from scipy import stats
import common as C

W1_CARRY_MIN = 5


def build():
    w = C._derived(C.load_weekly())
    rb = w[w.position == "RB"].copy()

    # ---- backfield-room aggregates, from snap counts
    s = pd.read_parquet(f"{C.HERE}/snaps.parquet")
    s = s[(s.game_type == "REG") & s.offense_snaps.notna()].copy()
    room = s[s.position.isin(["RB", "FB"])].copy()
    grp = room.groupby(["season", "week", "team"]).offense_snaps
    room["room_snaps"] = grp.transform("sum")
    room["room_rank"] = grp.rank(ascending=False, method="min")
    room["rb2_snaps"] = grp.transform(
        lambda x: x.sort_values(ascending=False).iloc[1] if len(x) > 1 else 0.0)
    cw = pd.read_parquet(f"{C.HERE}/players.parquet")
    key = cw[cw.pfr_id.notna()].drop_duplicates("pfr_id")[["gsis_id", "pfr_id"]]
    room = room.merge(key, left_on="pfr_player_id", right_on="pfr_id", how="left")
    room = room[room.gsis_id.notna()].rename(columns={"gsis_id": "player_id"})
    room["room_snap_share"] = room.offense_snaps / room.room_snaps.replace(0, np.nan)
    room["snap_gap"] = (room.offense_snaps - room.rb2_snaps) / room.room_snaps.replace(0, np.nan)
    room = room[["season", "week", "player_id", "room_snap_share", "room_rank", "snap_gap"]]
    rb = rb.merge(room.drop_duplicates(["season", "week", "player_id"]),
                  on=["season", "week", "player_id"], how="left")

    rc = rb.groupby(["season", "week", "team"]).carries.sum().rename("room_carries")
    rb = rb.merge(rc, on=["season", "week", "team"], how="left")
    rb["room_carry_share"] = rb.carries / rb.room_carries.replace(0, np.nan)

    # ---- next gen: rush yards over expected per attempt (blocking-adjusted)
    n = pd.read_parquet(f"{C.HERE}/ngs_rushing.parquet")
    n = n[(n.season_type == "REG") & (n.week > 0)][
        ["season", "week", "player_gsis_id", "rush_yards_over_expected_per_att",
         "efficiency", "percent_attempts_gte_eight_defenders"]]
    n = n.rename(columns={"player_gsis_id": "player_id",
                          "rush_yards_over_expected_per_att": "ryoe_att"})
    rb = rb.merge(n.drop_duplicates(["season", "week", "player_id"]),
                  on=["season", "week", "player_id"], how="left")

    d = rb[rb.week == 1].copy()
    d["yards_per_carry"] = np.where(d.carries > 0, d.rushing_yards / d.carries, np.nan)
    d["ppr"] = d.fantasy_points_ppr
    W1 = ["snap_pct", "carries", "targets", "yards_per_carry", "ppr", "room_snap_share",
          "room_carry_share", "room_rank", "snap_gap", "ryoe_att", "rush_share"]
    w1 = d.set_index(["player_id", "season"])[W1].add_prefix("w1_")

    r = rb[rb.week >= 2]
    g = r.groupby(["player_id", "season"])
    ros = pd.DataFrame(index=w1.index)
    ros["ros_games"] = g.size()
    ros["ros_snap_pct"] = g.snap_pct.mean()
    ros["ros_room_snap_share"] = g.room_snap_share.mean()
    ros["ros_ppg"] = g.fantasy_points_ppr.mean()
    ros["ros_carries"] = g.carries.mean()
    ros["ros_ypc"] = g.rushing_yards.sum() / g.carries.sum().replace(0, np.nan)
    ros["ros_ryoe_att"] = g.ryoe_att.mean()

    meta = pd.read_parquet(f"{C.HERE}/players.parquet")[
        ["gsis_id", "display_name", "rookie_season", "draft_round", "draft_pick"]]
    meta = meta.drop_duplicates("gsis_id").set_index("gsis_id")

    p = w1.join(ros).reset_index().merge(meta, left_on="player_id", right_index=True,
                                         how="left")
    p["rookie"] = p.season == p.rookie_season
    p["delta_snap"] = p.ros_snap_pct - p.w1_snap_pct
    p = p[(p.w1_carries >= W1_CARRY_MIN) & (p.ros_games >= C.MIN_ROS_GAMES)
          & (p.season >= C.SNAP_FIRST) & (p.season <= C.LAST_SEASON)]
    return p[np.isfinite(p.w1_snap_pct) & np.isfinite(p.ros_snap_pct)]


def rr(x, y):
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 25:
        return np.nan, np.nan, int(m.sum())
    r = float(np.corrcoef(x[m], y[m])[0, 1])
    t = r * np.sqrt(m.sum() - 2) / np.sqrt(1 - r * r)
    return r, float(2 * stats.t.sf(abs(t), m.sum() - 2)), int(m.sum())


def reg(d, target, preds, labels, min_n=40):
    d = d[np.isfinite(d[[target] + preds]).all(axis=1)]
    if len(d) < min_n:
        return None
    X = np.column_stack([np.ones(len(d))] + [C.z(d[c]) for c in preds])
    y = C.z(d[target])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ beta
    dof = len(d) - X.shape[1]
    se = np.sqrt(np.diag(np.linalg.pinv(X.T @ X)) * float(res @ res) / dof)
    t = beta / se
    p = 2 * stats.t.sf(np.abs(t), dof)
    r2 = 1 - float(res @ res) / float(((y - y.mean()) ** 2).sum())
    return dict(n=len(d), r2=r2, terms=list(zip(labels, beta[1:], se[1:], t[1:], p[1:])))


def show(out):
    return ("   ".join(f"{t[0]} {t[1]:+.3f} (p {t[4]:.3f})" for t in out["terms"])
            + f"   n={out['n']}  R2 {out['r2']:.3f}")


def ci(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    m, se = x.mean(), x.std(ddof=1) / np.sqrt(len(x))
    h = stats.t.ppf(.975, len(x) - 1) * se
    return m, m - h, m + h


METS = [("snap_pct", "team snap share"), ("room_snap_share", "share of RB-room snaps"),
        ("room_carry_share", "share of RB-room carries"),
        ("rush_share", "share of team carries"), ("snap_gap", "snap lead over RB2"),
        ("carries", "carries"), ("targets", "targets"), ("ppr", "PPR points"),
        ("yards_per_carry", "yards per carry"), ("ryoe_att", "rush yds over expected/att")]


def predict_from(d, target, preds, x_new, min_n=30):
    """Fitted value and 95% prediction interval for one new observation."""
    d = d[np.isfinite(d[[target] + preds]).all(axis=1)]
    if len(d) < min_n:
        return None
    mu = {c: d[c].mean() for c in preds}
    sd = {c: d[c].std(ddof=0) for c in preds}
    X = np.column_stack([np.ones(len(d))] + [(d[c] - mu[c]) / sd[c] for c in preds])
    y = d[target].values
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ beta
    dof = len(d) - X.shape[1]
    s2 = float(res @ res) / dof
    x0 = np.array([1.0] + [(x_new[c] - mu[c]) / sd[c] for c in preds])
    xtx = np.linalg.pinv(X.T @ X)
    fit = float(x0 @ beta)
    se_pred = np.sqrt(s2 * (1 + float(x0 @ xtx @ x0)))
    se_mean = np.sqrt(s2 * float(x0 @ xtx @ x0))
    tc = stats.t.ppf(0.975, dof)
    return dict(n=len(d), fit=fit, resid_sd=np.sqrt(s2),
                pi=(fit - tc * se_pred, fit + tc * se_pred),
                ci=(fit - tc * se_mean, fit + tc * se_mean))


# the Week 1 2026 line this was built to read
CASE = dict(name="Jadarian Price", w1_snap_pct=24 / 50, w1_room_snap_share=24 / 67,
            w1_snap_gap=(24 - 23) / 67, w1_carries=10, w1_yards_per_carry=5.2,
            w1_ryoe_att=0.683, w1_targets=2, w1_ppr=7.8, draft_round=1.0, draft_pick=32.0)


def predict(p, rook):
    print("\n\n## APPLIED TO ONE ACTUAL WEEK 1 LINE")
    c = CASE
    print(f"   {c['name']}, 2026 week 1: {c['w1_carries']} carries for "
          f"{c['w1_yards_per_carry']:.1f} a pop, {c['w1_targets']} targets, "
          f"{c['w1_ppr']:.1f} PPR")
    print(f"   snap share {c['w1_snap_pct']:.0%} of team, {c['w1_room_snap_share']:.0%} of "
          f"the RB room, lead over RB2 {c['w1_snap_gap']:.1%} of the room")
    print(f"   RYOE/att {c['w1_ryoe_att']:+.2f}, drafted round "
          f"{int(c['draft_round'])} pick {int(c['draft_pick'])}")
    print("\n   Fitted values with 95% PREDICTION intervals (the range for one player,")
    print("   not the range for the group average, which is the narrower CI):")
    specs = [("ros_snap_pct", ["w1_snap_pct"], "rookies", 100),
             ("ros_snap_pct", ["w1_snap_pct", "draft_round"], "rookies", 100),
             ("ros_snap_pct", ["w1_snap_pct", "w1_snap_gap"], "rookies", 100),
             ("ros_snap_pct", ["w1_snap_pct", "draft_round"], "all backs", 100),
             ("ros_ppg", ["w1_snap_pct"], "rookies", 1),
             ("ros_ppg", ["w1_snap_pct", "draft_round"], "rookies", 1),
             ("ros_ppg", ["w1_snap_pct", "w1_snap_gap"], "rookies", 1),
             ("ros_ppg", ["w1_snap_pct", "w1_ppr"], "all backs", 1),
             ("ros_ypc", ["w1_yards_per_carry"], "all backs", 1),
             ("ros_ypc", ["w1_yards_per_carry", "w1_ryoe_att"], "all backs", 1)]
    tl = {"ros_snap_pct": "ROS snap share", "ros_ppg": "ROS PPR ppg",
          "ros_ypc": "ROS yards/carry"}
    pl = {"w1_snap_pct": "wk1 snap%", "draft_round": "draft rd", "w1_snap_gap": "RB2 gap",
          "w1_ppr": "wk1 PPR", "w1_yards_per_carry": "wk1 YPC", "w1_ryoe_att": "RYOE/att"}
    print(f"   {'target':<17}{'from':<30}{'pool':<11}{'n':>5}{'fitted':>9}"
          f"{'95% prediction interval':>26}")
    for tgt, preds, pool, f in specs:
        d = rook if pool == "rookies" else p
        out = predict_from(d, tgt, preds, c)
        if not out:
            print(f"   {tl[tgt]:<17}{' + '.join(pl[x] for x in preds):<30}{pool:<11}"
                  f"{'':>5}   n too small")
            continue
        u = "%" if f == 100 else ""
        print(f"   {tl[tgt]:<17}{' + '.join(pl[x] for x in preds):<30}{pool:<11}"
              f"{out['n']:>5}{out['fit']*f:>8.1f}{u}"
              f"{f'[{out[chr(112)+chr(105)][0]*f:.1f}, {out[chr(112)+chr(105)][1]*f:.1f}]{u}':>26}")


def main():
    p = build()
    rook, vet = p[p.rookie], p[~p.rookie]
    print("=" * 100)
    print("WEEK 1 FOR A ROOKIE BACK, AND THE BACKFIELD-RELATIVE VIEW")
    print(f"RB-seasons {C.SNAP_FIRST}-{C.LAST_SEASON}, Week 1 carries >= {W1_CARRY_MIN}, "
          f"4+ games after Week 1")
    print(f"n = {len(p)}  ({len(rook)} rookie seasons, {len(vet)} veteran)")
    print("Rush yards over expected is Next Gen and starts in 2016, so its rows carry "
          "a smaller n.")
    print("=" * 100)

    for tgt, tlab in (("ros_snap_pct", "REST-OF-SEASON TEAM SNAP SHARE"),
                      ("ros_ppg", "REST-OF-SEASON PPR POINTS PER GAME")):
        print(f"\n\n## {tlab}: r from each Week 1 metric")
        print(f"   {'week 1 metric':<30}{'rookies':>22}{'veterans':>22}{'   gap':>8}")
        print(f"   {'':<30}{'r':>8}{'p':>8}{'n':>6}{'r':>8}{'p':>8}{'n':>6}")
        print("   " + "-" * 80)
        for m, lab in METS:
            a, pa, na = rr(rook["w1_" + m].values, rook[tgt].values)
            b, pb, nb = rr(vet["w1_" + m].values, vet[tgt].values)
            f = lambda v: "     n/a" if not np.isfinite(v) else f"{v:>8.3f}"
            fp = lambda v: "     n/a" if not np.isfinite(v) else (
                "   <1e-9" if v < 1e-9 else f"{v:>8.2g}")
            gap = f"{a-b:>+8.3f}" if np.isfinite(a) and np.isfinite(b) else "     n/a"
            print(f"   {lab:<30}{f(a)}{fp(pa)}{na:>6}{f(b)}{fp(pb)}{nb:>6}{gap}")

    print("\n\n## DOES WEEK 1 EFFICIENCY BUY A BIGGER ROLE LATER?")
    print("   target: change in team snap share, Week 1 to the rest of the season")
    print("   (standardised; Week 1 snap share held fixed in every model)")
    for lab, d in (("rookies", rook), ("veterans", vet), ("all", p)):
        for eff, elab in (("w1_ryoe_att", "RYOE/att"), ("w1_yards_per_carry", "YPC")):
            out = reg(d, "delta_snap", ["w1_snap_pct", eff], ["w1 snap share", elab],
                      min_n=20)
            if out:
                flag = "  (small n)" if out["n"] < 40 else ""
                print(f"     {lab:<10}{elab:<10}{show(out)}{flag}")

    print("\n   rookies only, draft round added")
    out = reg(rook, "delta_snap", ["w1_snap_pct", "w1_ryoe_att", "draft_round"],
              ["w1 snap share", "RYOE/att", "draft round"], min_n=20)
    print("     " + (show(out) + "  (small n)" if out else "n below 20, not reported"))

    print("\n   predicting the LEVEL of rest-of-season snap share, rookies only")
    for preds, labs in ((["w1_snap_pct"], ["w1 snap share"]),
                        (["draft_round"], ["draft round"]),
                        (["w1_snap_pct", "draft_round"], ["w1 snap share", "draft round"]),
                        (["w1_snap_pct", "draft_round", "w1_ryoe_att"],
                         ["w1 snap share", "draft round", "RYOE/att"]),
                        (["w1_room_snap_share", "draft_round"],
                         ["room snap share", "draft round"])):
        out = reg(rook, "ros_snap_pct", preds, labs)
        if out:
            print("     " + show(out))

    print("\n\n## HOW STICKY IS A NARROW WEEK 1 BACKFIELD LEAD?")
    print("   backs who led their room in Week 1 snaps, split by the size of the lead")
    lead = p[(p.w1_room_rank == 1) & np.isfinite(p.w1_snap_gap)]
    print(f"   {'week 1 lead over RB2':<26}{'n':>5}{'still room leader in ROS':>27}"
          f"{'ROS snap share':>17}{'ROS ppg':>10}")
    for lo, hi, lab in ((0, .05, "under 5 pts of the room"), (.05, .15, "5-15 pts"),
                        (.15, .30, "15-30 pts"), (.30, 1.01, "30+ pts")):
        b = lead[(lead.w1_snap_gap >= lo) & (lead.w1_snap_gap < hi)]
        if len(b) < 12:
            continue
        print(f"   {lab:<26}{len(b):>5}{(b.ros_room_snap_share > .5).mean()*100:>26.0f}%"
              f"{b.ros_snap_pct.mean()*100:>16.1f}%{b.ros_ppg.mean():>10.1f}")

    print("\n\n## THE COMPARABLE COHORT")
    print("   rookie backs, Week 1 team snap share 40-56%, led their RB room")
    wide = rook[(rook.w1_snap_pct >= 0.40) & (rook.w1_snap_pct <= 0.56)
                & (rook.w1_room_rank == 1)]
    coh = wide[wide.w1_ryoe_att > 0]
    d1 = wide[wide.draft_round <= 2]
    for lab, b in (("all such rookies", wide), ("+ positive RYOE/att", coh),
                   ("+ drafted round 1-2", d1)):
        if len(b) < 5:
            print(f"\n     {lab}: n={len(b)} — too few to report")
            continue
        print(f"\n     {lab}   n = {len(b)}")
        for col, cl, f in (("ros_snap_pct", "ROS team snap share", 100),
                           ("ros_ppg", "ROS PPR points/game", 1),
                           ("ros_ypc", "ROS yards per carry", 1),
                           ("ros_carries", "ROS carries/game", 1)):
            m, lo, hi = ci(b[col])
            q = b[col].quantile([.25, .5, .75]).values
            u = "%" if f == 100 else ""
            print(f"       {cl:<22}mean {m*f:.2f}{u}  95% CI [{lo*f:.2f}, {hi*f:.2f}]{u}"
                  f"   p25 {q[0]*f:.2f}  p50 {q[1]*f:.2f}  p75 {q[2]*f:.2f}")
        print(f"       reached 60%+ ROS snap share: "
              f"{(b.ros_snap_pct >= .60).mean()*100:.0f}%"
              f"   |  fell under 35%: {(b.ros_snap_pct < .35).mean()*100:.0f}%"
              f"   |  12+ ppg: {(b.ros_ppg >= 12).mean()*100:.0f}%")
        print("       cases: " + ", ".join(
            f"{r.display_name} {int(r.season)} ({r.w1_snap_pct:.0%}->{r.ros_snap_pct:.0%}, "
            f"{r.ros_ppg:.1f} ppg)"
            for _, r in b.sort_values("ros_ppg", ascending=False).head(14).iterrows()))
    predict(p, rook)
    p.to_csv("out_rookies.csv", index=False)


if __name__ == "__main__":
    main()
