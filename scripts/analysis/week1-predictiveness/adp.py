"""Is Week 1 as predictive for an early-round pick as for a late one?

Draft position is the market's summary of everything known in August. So the
question is really: where does one game of new information matter most -- on top of
a strong prior (a top-5 pick) or a weak one (the 40th player at his position)?

WHAT STANDS IN FOR ADP. Real ADP feeds are not reachable from this environment, so
this uses FantasyPros preseason redraft POSITIONAL expert consensus rank, taken from
the last scrape strictly BEFORE that season's first kickoff. It is a consensus
ranking rather than a draft-board average, but it is the same kind of object: the
market's pre-season ordering. Coverage is 2020-2025, six seasons.

Because six seasons is thin, the whole analysis is also run on a proxy available
for 1999-2025 -- the player's prior-season positional finish in points per game --
and the proxy is first validated against real ECR in the overlapping years. If both
tell the same story, the thin sample is not carrying the conclusion.

Two tests, since "is Week 1 as predictive" can mean two different things:
  1. Within a draft tier, how far apart do a good and a bad Week 1 end up?
  2. Does the SLOPE on Week 1 change with draft position? That is an interaction
     term, and it avoids having to pick tier boundaries at all.

Written to ADP.txt.
"""
import numpy as np
import pandas as pd
from scipy import stats
import common as C

POS = ("RB", "WR", "TE", "QB")
TIERS = [(1, 5, "top 5"), (6, 12, "6-12"), (13, 24, "13-24"),
         (25, 40, "25-40"), (41, 999, "41+")]
MIN_ROS_GAMES = 4


def season_start(games):
    g = games[games.game_type == "REG"]
    return pd.to_datetime(g.groupby("season").gameday.min())


def fantasy_panel(weekly, pos):
    p = weekly[weekly.position == pos]
    w1 = p[p.week == 1].groupby(["player_id", "season"]).fantasy_points_ppr.sum().rename("w1_pts")
    r = p[p.week >= 2].groupby(["player_id", "season"])
    ros = pd.DataFrame(dict(ros_pts=r.fantasy_points_ppr.sum(), ros_games=r.size()))
    f = p.groupby(["player_id", "season"])
    full = pd.DataFrame(dict(full_pts=f.fantasy_points_ppr.sum(), full_games=f.size()))
    d = pd.concat([w1, ros, full], axis=1).reset_index()
    d = d[d.w1_pts.notna()]
    d["ros_games"] = d.ros_games.fillna(0)
    d["ros_pts"] = d.ros_pts.fillna(0)
    d["ros_ppg"] = np.where(d.ros_games > 0, d.ros_pts / d.ros_games, 0.0)
    d["full_ppg"] = d.full_pts / d.full_games
    # prior-season positional finish in ppg, the long-history stand-in for ADP
    prior = p.groupby(["player_id", "season"]).agg(
        pp=("fantasy_points_ppr", "sum"), pg=("fantasy_points_ppr", "size")).reset_index()
    prior["prior_ppg"] = prior.pp / prior.pg
    prior = prior[prior.pg >= 6]
    prior["prior_rank"] = prior.groupby("season").prior_ppg.rank(ascending=False, method="min")
    prior["season"] = prior.season + 1
    d = d.merge(prior[["player_id", "season", "prior_ppg", "prior_rank"]],
                on=["player_id", "season"], how="left")
    names = p[["player_id", "season", "player_display_name"]].drop_duplicates(
        ["player_id", "season"])
    return d.merge(names, on=["player_id", "season"], how="left")


def ecr_ranks(games):
    e = pd.read_parquet(f"{C.HERE}/ecr_preseason.parquet")
    e["scrape_date"] = pd.to_datetime(e.scrape_date)
    e["season"] = e.scrape_date.dt.year
    start = season_start(games)
    e = e[e.season.isin(start.index)]
    e = e[e.scrape_date < e.season.map(start)]            # strictly before kickoff
    last = e.groupby(["season", "pos"]).scrape_date.transform("max")
    e = e[e.scrape_date == last]
    ids = pd.read_csv(f"{C.HERE}/player_ids.csv", low_memory=False)
    ids = ids[ids.gsis_id.notna() & ids.fantasypros_id.notna()]
    ids = ids.assign(fp=ids.fantasypros_id.astype(float)).drop_duplicates("fp")
    e = e.merge(ids[["fp", "gsis_id"]], left_on=e.id.astype(float), right_on="fp", how="left")
    e = e[e.gsis_id.notna()].rename(columns={"gsis_id": "player_id"})
    e["adp_rank"] = e.groupby(["season", "pos"]).ecr.rank(method="min")
    return e[["season", "pos", "player_id", "player", "ecr", "adp_rank"]]


def tier(rank):
    for lo, hi, lab in TIERS:
        if lo <= rank <= hi:
            return lab
    return None


def ci(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 3:
        return np.nan, np.nan, np.nan, len(x)
    m, se = x.mean(), x.std(ddof=1) / np.sqrt(len(x))
    h = stats.t.ppf(.975, len(x) - 1) * se
    return m, m - h, m + h, len(x)


def interaction(d, rank_col):
    """Does the slope on Week 1 depend on draft position?

    Rank runs 1 to 200+ and is heavily right-skewed, so a linear interaction is
    driven almost entirely by the mass of late-round players and disagrees with the
    tier tables. log(rank) linearises the tier spacing -- the gap from pick 1 to 5
    is treated like the gap from 40 to 200 -- which is the structure the tiers
    assume. Marginal effects at named ranks are reported so the sign is readable.
    """
    d = d[np.isfinite(d[["ros_ppg", "w1_pts", rank_col]]).all(axis=1)]
    if len(d) < 60:
        return None
    lr = np.log(d[rank_col].values)
    zr, zw = (lr - lr.mean()) / lr.std(), C.z(d.w1_pts)
    X = np.column_stack([np.ones(len(d)), zr, zw, zr * zw])
    y = C.z(d.ros_ppg)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ beta
    dof = len(d) - 4
    se = np.sqrt(np.diag(np.linalg.pinv(X.T @ X)) * float(res @ res) / dof)
    t = beta / se
    p = 2 * stats.t.sf(np.abs(t), dof)
    r2 = 1 - float(res @ res) / float(((y - y.mean()) ** 2).sum())
    # marginal effect of Week 1 at a few named ranks
    marg = {}
    for rk in (3, 12, 30, 80):
        zz = (np.log(rk) - lr.mean()) / lr.std()
        marg[rk] = beta[2] + beta[3] * zz
    return dict(n=len(d), r2=r2, b_rank=beta[1], p_rank=p[1], b_w1=beta[2], p_w1=p[2],
                b_int=beta[3], p_int=p[3], marg=marg)


def tier_table(d, rank_col, label):
    """Within each draft tier: how far apart do a good and a bad Week 1 finish?"""
    print(f"\n   {'draft tier':<12}{'n':>5}{'good wk1 -> ROS ppg':>24}"
          f"{'bad wk1 -> ROS ppg':>23}{'gap':>18}{'r(w1,ROS)':>12}{'dR2':>7}")
    print("   " + "-" * 101)
    rows = []
    for lo, hi, lab in TIERS:
        b = d[(d[rank_col] >= lo) & (d[rank_col] <= hi)]
        b = b[np.isfinite(b[["ros_ppg", "w1_pts"]]).all(axis=1)]
        if len(b) < 25:
            continue
        med = b.w1_pts.median()
        hi_g, lo_g = b[b.w1_pts > med], b[b.w1_pts <= med]
        mh, lh, hh, nh = ci(hi_g.ros_ppg)
        ml, ll, hl, nl = ci(lo_g.ros_ppg)
        gap = mh - ml
        va, vb = hi_g.ros_ppg.var(ddof=1) / nh, lo_g.ros_ppg.var(ddof=1) / nl
        sed = np.sqrt(va + vb)
        r = float(np.corrcoef(b.w1_pts, b.ros_ppg)[0, 1])
        # dR2: Week 1 on top of the exact rank, inside the tier
        zz = np.column_stack([C.z(b[rank_col])])
        _, r2a = C.ols(C.z(b.ros_ppg), zz)
        _, r2b = C.ols(C.z(b.ros_ppg), np.column_stack([C.z(b[rank_col]), C.z(b.w1_pts)]))
        print(f"   {lab:<12}{len(b):>5}{mh:>12.2f} [{lh:.1f},{hh:.1f}]"
              f"{ml:>12.2f} [{ll:.1f},{hl:.1f}]"
              f"{gap:>+9.2f} +/-{1.96*sed:>4.2f}{r:>12.3f}{r2b-r2a:>7.3f}")
        rows.append(dict(tier=lab, n=len(b), gap=gap, se=sed, r=r, d_r2=r2b - r2a))
    return pd.DataFrame(rows)


def main():
    weekly = C._derived(C.load_weekly())
    games = C.load_games()
    ecr = ecr_ranks(games)
    print("=" * 104)
    print("WEEK 1 THROUGH THE LENS OF DRAFT POSITION")
    print("=" * 104)
    print(f"\nPreseason positional ECR: {ecr.season.min()}-{ecr.season.max()}, "
          f"{len(ecr)} player-seasons, taken from the last scrape before kickoff.")
    print("Prior-season positional finish is the 1999-2025 stand-in, validated below.")

    print("\n\n## 0. IS THE LONG-HISTORY STAND-IN ANY GOOD?")
    print("   preseason ECR rank vs prior-season positional finish, in the overlap years")
    panels = {}
    for pos in POS:
        d = fantasy_panel(weekly, pos)
        e = ecr[ecr.pos == pos][["season", "player_id", "adp_rank", "ecr"]]
        d = d.merge(e, on=["season", "player_id"], how="left")
        panels[pos] = d
        ov = d[np.isfinite(d[["adp_rank", "prior_rank"]]).all(axis=1)]
        r = float(np.corrcoef(ov.adp_rank, ov.prior_rank)[0, 1])
        rho = float(ov.adp_rank.rank().corr(ov.prior_rank.rank()))
        cov = float(d[d.season >= 2020].adp_rank.notna().mean())
        print(f"     {pos}: r {r:.3f}, rho {rho:.3f} (n={len(ov)})"
              f"   | ECR matched to {cov*100:.0f}% of {pos} week-1 players since 2020")

    for rank_col, lab, span in (("adp_rank", "PRESEASON ECR", "2020-2025"),
                                ("prior_rank", "PRIOR-SEASON FINISH", "1999-2025")):
        print(f"\n\n{'='*104}\n## {lab} ({span})\n{'='*104}")
        print("\n   Within each draft tier, players are split at that tier's own median")
        print("   Week 1 score. 'gap' is how much further ahead the good-Week-1 half")
        print("   finished, with a 95% interval. 'dR2' is what Week 1 adds on top of the")
        print("   exact rank inside the tier.")
        for pos in POS:
            d = panels[pos]
            d = d[d.ros_games >= MIN_ROS_GAMES]
            if rank_col == "adp_rank":
                d = d[d.season >= 2020]
            n_ok = np.isfinite(d[rank_col]).sum()
            if n_ok < 120:
                print(f"\n   {pos}: only {n_ok} player-seasons with a rank, skipped")
                continue
            print(f"\n   {pos}   ({n_ok} player-seasons)")
            tier_table(d, rank_col, lab)
            it = interaction(d, rank_col)
            if it:
                print(f"     interaction on log(rank): log rank {it['b_rank']:+.3f} "
                      f"(p {it['p_rank']:.3f})   week 1 {it['b_w1']:+.3f} "
                      f"(p {it['p_w1']:.3f})   log rank x week 1 {it['b_int']:+.3f} "
                      f"(p {it['p_int']:.3f})   n={it['n']}  R2 {it['r2']:.3f}")
                print("       week 1 slope at rank " + ",  ".join(
                    f"{k}: {v:+.3f}" for k, v in it["marg"].items()))

    print("\n\n## 2. READING THE INTERACTION")
    print("   Rank is coded so a HIGHER number is a LATER pick. A POSITIVE log rank x")
    print("   week 1 term means Week 1 carries MORE weight for later picks; negative means")
    print("   more for early picks; near zero with a large p means the data cannot")
    print("   separate them. The marginal-slope line is the same thing in readable form.")

    print("\n\n## 3. IS THE TOP-TIER RESULT REAL, OR JUST THIN?")
    print("   The two rank measures disagree most in the top-5 tier, so both the effect")
    print("   and the sample behind it are shown side by side.")
    print(f"   {'pos':<5}{'measure':<16}{'n':>5}{'gap ppg':>10}{'95% interval':>18}"
          f"{'dR2':>8}")
    print("   " + "-" * 62)
    for pos in POS:
        for rank_col, lab in (("adp_rank", "preseason ECR"), ("prior_rank", "prior finish")):
            d = panels[pos][panels[pos].ros_games >= MIN_ROS_GAMES]
            if rank_col == "adp_rank":
                d = d[d.season >= 2020]
            b = d[(d[rank_col] >= 1) & (d[rank_col] <= 5)]
            b = b[np.isfinite(b[["ros_ppg", "w1_pts"]]).all(axis=1)]
            if len(b) < 15:
                continue
            med = b.w1_pts.median()
            h, l = b[b.w1_pts > med], b[b.w1_pts <= med]
            mh, _, _, nh = ci(h.ros_ppg)
            ml, _, _, nl = ci(l.ros_ppg)
            sed = np.sqrt(h.ros_ppg.var(ddof=1)/nh + l.ros_ppg.var(ddof=1)/nl)
            zz = np.column_stack([C.z(b[rank_col])])
            _, r2a = C.ols(C.z(b.ros_ppg), zz)
            _, r2b = C.ols(C.z(b.ros_ppg), np.column_stack([C.z(b[rank_col]), C.z(b.w1_pts)]))
            print(f"   {pos:<5}{lab:<16}{len(b):>5}{mh-ml:>+10.2f}"
                  f"{f'[{mh-ml-1.96*sed:+.2f}, {mh-ml+1.96*sed:+.2f}]':>18}{r2b-r2a:>8.3f}")
    print("\n   Prior-season finish is not the market's view: a back who finished top-5")
    print("   last year but turns 30 behind a new line is in its top tier and nowhere")
    print("   near the top of a real draft board. That tier therefore holds uncertainty")
    print("   an actual ADP had already priced out, which is why Week 1 looks more useful")
    print("   there. Where the two measures disagree, prefer the ECR rows.")

    out = []
    for rank_col in ("adp_rank", "prior_rank"):
        for pos in POS:
            d = panels[pos][panels[pos].ros_games >= MIN_ROS_GAMES]
            if rank_col == "adp_rank":
                d = d[d.season >= 2020]
            it = interaction(d, rank_col)
            if it:
                out.append(dict(rank=rank_col, position=pos, **it))
    pd.DataFrame(out).to_csv("out_adp_interaction.csv", index=False)
    pd.concat([d.assign(position=p) for p, d in panels.items()]).to_csv(
        "out_adp.csv", index=False)


if __name__ == "__main__":
    main()
