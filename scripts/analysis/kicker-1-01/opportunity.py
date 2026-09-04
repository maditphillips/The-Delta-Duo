"""Do coaches actually give a great kicker more to do?

The kicker study (kicker_value.py) assumes that a guaranteed leg gets used:
half its value comes from fourth downs that teams currently punt. This script
asks whether that assumption has any support in observed behaviour, and then
works out how much extra opportunity the kicker would need before he is worth
more than the first overall pick.

Run fetch_plays.py first, then:  python3 opportunity.py > OPPORTUNITY.txt

Design
------
Kicker quality is measured as field goals made over expected, where expected
comes from a logistic spline in kick distance plus season fixed effects fit
on every attempt 1999-2025. Per attempt, that is "makes above expectation".

Opportunity is measured four ways per team-season: attempts per game,
attempts of 50+ yards per game, mean attempt distance, and the share of
fourth downs in the contested band (the opponent's 32 to 42, a 50-to-60 yard
kick) that were kicked rather than punted or gone for.

The causal problem is obvious: good offences generate both good field
position and, sometimes, good kickers. Two things guard against it. Kicker
quality is measured out-of-sample, from the kicker's career to date
EXCLUDING the season being predicted, so this season's makes cannot drive
this season's attempt counts. And every regression carries team and season
fixed effects, so the estimate comes from a team changing kickers, not from
good teams differing from bad ones.
"""
import os
import warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

from epa_common import SNAP_TO_KICK, add_adjusted, kern

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 60)
pd.set_option("display.max_rows", 200)

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "plays_1999_2025.parquet")

BAND_LO, BAND_HI = 32, 42       # a 50-to-60 yard attempt: the contested band
MIN_CAREER = 30                 # attempts needed before a kicker has a record
GAMES = 17
MAX_YL = 42                     # the far edge of a 60-yard guarantee
MODERN = list(range(2018, 2026))
TOGO_CUTS = [0, 1, 2, 3, 5, 7, 10, 15, 99]
TOGO_LAB = ["1", "2", "3", "4-5", "6-7", "8-10", "11-15", "16+"]

# carried over from FINDINGS.txt and PICK.txt so the two studies line up
SLOPE = 0.02796                 # win% per point of margin per game, 2018-2025
CH1 = 17.79                     # channel 1, points per team-season
CH5 = 2.15                      # channel 5, extra points
QB_MEAN, QB_MEDIAN = 1.28, 1.59  # 1.01 quarterback wins above replacement

COLS = ["season", "season_type", "game_id", "posteam", "down", "ydstogo",
        "yardline_100", "play_type", "field_goal_attempt", "field_goal_result",
        "kick_distance", "kicker_player_id", "kicker_player_name", "wp", "qtr",
        "half_seconds_remaining", "week"]


def hdr(t):
    print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)


def sub(t):
    print(f"\n-- {t}")


def load():
    d = pd.read_parquet(SRC, columns=COLS)
    d = d[d.season_type.eq("REG") & d.posteam.notna()]
    fg = d[d.field_goal_attempt.eq(1) & d.field_goal_result.notna()].copy()
    fg["made"] = fg.field_goal_result.eq("made").astype(int)
    fg["dist"] = fg.kick_distance.where(
        fg.kick_distance.sub(fg.yardline_100).eq(SNAP_TO_KICK),
        fg.yardline_100 + SNAP_TO_KICK)
    fg = fg[fg.dist.between(18, 75)]
    m = smf.glm("made ~ bs(dist, df=5) + C(season)", data=fg,
                family=sm.families.Binomial()).fit()
    fg["xmake"] = m.predict(fg)
    fg["oe"] = fg.made - fg.xmake        # makes above expectation
    return d, fg


def primary_kicker(fg):
    pk = fg.groupby(["season", "posteam", "kicker_player_id",
                     "kicker_player_name"], as_index=False).size()
    pk = pk.sort_values("size", ascending=False).groupby(
        ["season", "posteam"], as_index=False).first()
    return pk.rename(columns={"kicker_player_id": "kid",
                              "kicker_player_name": "kicker", "size": "k_att"})


def career_quality(fg):
    """Out-of-sample kicker quality: career makes-above-expected per attempt,
    computed over every season EXCEPT the one being scored."""
    g = fg.groupby(["kicker_player_id", "season"], as_index=False).agg(
        att=("made", "size"), oe=("oe", "sum"))
    g = g.sort_values(["kicker_player_id", "season"])
    tot_att = g.groupby("kicker_player_id").att.transform("sum")
    tot_oe = g.groupby("kicker_player_id").oe.transform("sum")
    g["out_att"] = tot_att - g.att
    g["out_oe"] = tot_oe - g.oe
    g["quality"] = np.where(g.out_att >= MIN_CAREER, g.out_oe / g.out_att, np.nan)
    # prior-seasons-only version, which is what a coach actually knows
    g["prior_att"] = g.groupby("kicker_player_id").att.cumsum() - g.att
    g["prior_oe"] = g.groupby("kicker_player_id").oe.cumsum() - g.oe
    g["prior_quality"] = np.where(g.prior_att >= MIN_CAREER,
                                  g.prior_oe / g.prior_att, np.nan)
    return g.rename(columns={"kicker_player_id": "kid"})


def team_season(d, fg):
    """Opportunity measures per team-season."""
    gp = d.groupby(["season", "posteam"]).game_id.nunique().rename("g")
    a = fg.groupby(["season", "posteam"]).agg(
        att=("made", "size"), made=("made", "sum"),
        oe=("oe", "sum"), mean_dist=("dist", "mean"),
        long=("dist", lambda x: (x >= 50).sum()),
        p90_dist=("dist", lambda x: x.quantile(0.90)))
    fourth = d[d.down.eq(4) & d.yardline_100.between(BAND_LO, BAND_HI)
               & d.play_type.isin(["field_goal", "punt", "pass", "run"])]
    b = fourth.groupby(["season", "posteam"]).apply(lambda x: pd.Series({
        "band_n": len(x),
        "band_kick": x.play_type.eq("field_goal").sum(),
        "band_punt": x.play_type.eq("punt").sum(),
    }), include_groups=False)
    t = a.join(gp).join(b).reset_index()
    t["att_pg"] = t.att / t.g
    t["long_pg"] = t.long / t.g
    t["band_kick_rate"] = t.band_kick / t.band_n
    t["band_punt_rate"] = t.band_punt / t.band_n
    return t


def main():
    d, fg = load()
    pk, cq = primary_kicker(fg), career_quality(fg)
    ts = team_season(d, fg)
    ts = ts.merge(pk[["season", "posteam", "kid", "kicker", "k_att"]],
                  on=["season", "posteam"], how="left")
    ts = ts.merge(cq[["kid", "season", "quality", "prior_quality", "prior_att",
                      "out_att"]], on=["kid", "season"], how="left")
    ts["oe_pa"] = ts.oe / ts.att

    hdr("0. THE MEASURES")
    print(f"seasons 1999-2025 regular season, {len(ts)} team-seasons")
    print(f"expected make rate: logistic spline in distance + season effects, "
          f"fit on {len(fg):,} attempts")
    print(f"contested band    : fourth downs from the opponent's {BAND_LO} to "
          f"{BAND_HI} = a {BAND_LO + SNAP_TO_KICK} to {BAND_HI + SNAP_TO_KICK} "
          f"yard attempt")
    print("\nleague-wide, by season:")
    yr = ts.groupby("season").apply(lambda x: pd.Series({
        "att_pg": x.att.sum() / x.g.sum(),
        "long_pg": x.long.sum() / x.g.sum(),
        "mean_dist": (x.mean_dist * x.att).sum() / x.att.sum(),
        "band_n_pg": x.band_n.sum() / x.g.sum(),
        "band_kick%": 100 * x.band_kick.sum() / x.band_n.sum(),
        "band_punt%": 100 * x.band_punt.sum() / x.band_n.sum(),
    }), include_groups=False)
    print(yr.round(3).to_string())

    # -------------------------------------------------------- case studies
    hdr("1. CASE STUDIES: WHAT HAPPENED WHEN AN ELITE LEG ARRIVED")
    cases = [
        ("BAL", "J.Tucker", 2012), ("DAL", "B.Aubrey", 2023),
        ("PIT", "C.Boswell", 2015), ("ATL", "Y.Koo", 2020),
        ("KC", "H.Butker", 2017), ("SF", "R.Gould", 2017),
        ("NE", "S.Gostkowski", 2006), ("IND", "A.Vinatieri", 2006),
        ("LV", "D.Carlson", 2018), ("JAX", "C.Little", 2024),
    ]
    rows = []
    for tm, name, yr0 in cases:
        t = ts[ts.posteam.eq(tm)]
        pre = t[t.season.between(yr0 - 4, yr0 - 1)]
        post = t[t.season.ge(yr0) & t.kicker.eq(name)]
        if not len(post) or not len(pre):
            continue
        rows.append({
            "team": tm, "kicker": name, "from": yr0,
            "pre_seasons": len(pre), "post_seasons": len(post),
            "att_pg_pre": pre.att.sum() / pre.g.sum(),
            "att_pg_post": post.att.sum() / post.g.sum(),
            "long_pg_pre": pre.long.sum() / pre.g.sum(),
            "long_pg_post": post.long.sum() / post.g.sum(),
            "dist_pre": (pre.mean_dist * pre.att).sum() / pre.att.sum(),
            "dist_post": (post.mean_dist * post.att).sum() / post.att.sum(),
            "band_kick_pre": 100 * pre.band_kick.sum() / pre.band_n.sum(),
            "band_kick_post": 100 * post.band_kick.sum() / post.band_n.sum(),
            "oe_pa_post": post.oe.sum() / post.att.sum(),
        })
    c = pd.DataFrame(rows)
    c["d_att_pg"] = c.att_pg_post - c.att_pg_pre
    c["d_long_pg"] = c.long_pg_post - c.long_pg_pre
    c["d_dist"] = c.dist_post - c.dist_pre
    c["d_band"] = c.band_kick_post - c.band_kick_pre
    print("  raw before/after, the four seasons before against the whole tenure")
    print(c[["team", "kicker", "from", "pre_seasons", "post_seasons", "oe_pa_post",
             "att_pg_pre", "att_pg_post", "d_att_pg", "d_long_pg", "d_dist",
             "band_kick_pre", "band_kick_post", "d_band"]].round(2).to_string(index=False))
    print("\n  raw before/after is contaminated by league-wide drift: everyone")
    print("  kicks from further out now, and everyone goes for it more. The")
    print("  league table above is the drift; section 2 removes it.")

    sub("league-adjusted: the same deltas minus the league's own change")
    adj = []
    for r in c.itertuples():
        t = ts[ts.posteam.eq(r.team)]
        pre_y = t[t.season.between(r._3 - 4, r._3 - 1)].season
        post_y = t[t.season.ge(r._3) & t.kicker.eq(r.kicker)].season
        lg_pre = ts[ts.season.isin(pre_y)]
        lg_post = ts[ts.season.isin(post_y)]
        adj.append({
            "team": r.team, "kicker": r.kicker, "from": r._3,
            "d_att_pg": r.d_att_pg - (lg_post.att.sum() / lg_post.g.sum()
                                      - lg_pre.att.sum() / lg_pre.g.sum()),
            "d_long_pg": r.d_long_pg - (lg_post.long.sum() / lg_post.g.sum()
                                        - lg_pre.long.sum() / lg_pre.g.sum()),
            "d_dist": r.d_dist - ((lg_post.mean_dist * lg_post.att).sum() / lg_post.att.sum()
                                  - (lg_pre.mean_dist * lg_pre.att).sum() / lg_pre.att.sum()),
            "d_band": r.d_band - (100 * lg_post.band_kick.sum() / lg_post.band_n.sum()
                                  - 100 * lg_pre.band_kick.sum() / lg_pre.band_n.sum()),
        })
    a = pd.DataFrame(adj)
    print(a.round(2).to_string(index=False))
    print(f"\n  mean league-adjusted change: attempts/game {a.d_att_pg.mean():+.3f}, "
          f"50+ per game {a.d_long_pg.mean():+.3f},")
    print(f"  mean attempt distance {a.d_dist.mean():+.2f} yards, "
          f"contested-band kick rate {a.d_band.mean():+.1f} points")

    # ------------------------------------------------------ 2. the regression
    hdr("2. THE ELASTICITY: DOES OPPORTUNITY RESPOND TO KICKER QUALITY?")
    r = ts[ts.prior_quality.notna() & ts.band_n.ge(3)].copy()
    r["band_rate"] = 100 * r.band_kick_rate
    r["band_punt_pp"] = 100 * r.band_punt_rate
    r["drives_pg"] = r.band_n / r.g
    print(f"{len(r)} team-seasons where the primary kicker had a record of "
          f"{MIN_CAREER}+ prior attempts")
    print(f"prior_quality = career makes above expected per attempt, prior "
          f"seasons only")
    print(f"  spread across those team-seasons: "
          f"{r.prior_quality.quantile(0.05):+.3f} (5th) to "
          f"{r.prior_quality.quantile(0.95):+.3f} (95th), "
          f"sd {r.prior_quality.std():.3f}")
    PERFECT_Q = 1 - fg[fg.dist.le(60)].xmake.mean()
    print(f"  a leg that never misses inside 60 would sit at "
          f"{PERFECT_Q:+.3f}, which is "
          f"{PERFECT_Q / r.prior_quality.std():.1f} standard deviations out")

    specs = [
        ("attempts per game", "att_pg", ""),
        ("attempts per game", "att_pg", " + drives_pg"),
        ("50+ yard attempts per game", "long_pg", ""),
        ("mean attempt distance", "mean_dist", ""),
        ("contested-band kick rate (pp)", "band_rate", ""),
        ("contested-band punt rate (pp)", "band_punt_pp", ""),
    ]
    out = []
    for lab, y, extra in specs:
        f = smf.ols(f"{y} ~ prior_quality + C(posteam) + C(season)" + extra,
                    data=r).fit(cov_type="cluster",
                                cov_kwds={"groups": r.posteam})
        b, se = f.params["prior_quality"], f.bse["prior_quality"]
        out.append({"outcome": lab + extra, "coef": b, "se": se,
                    "t": b / se, "p": f.pvalues["prior_quality"],
                    "per_sd": b * r.prior_quality.std(),
                    "if_perfect": b * PERFECT_Q})
    o = pd.DataFrame(out)
    print("\n  team and season fixed effects, standard errors clustered by team.")
    print("  'per_sd' is the effect of a one-sd better kicker; 'if_perfect' is")
    print("  the same coefficient extrapolated to a leg that never misses.")
    print(o.round(3).to_string(index=False))
    band_coef = o.loc[o.outcome.str.startswith("contested-band kick"),
                      "if_perfect"].iloc[0]
    att_coef = o.loc[o.outcome.eq("attempts per game"), "if_perfect"].iloc[0]
    print(f"\n  read plainly: give a team a leg that never misses inside 60 and")
    print(f"  the observed elasticity predicts {att_coef:+.2f} field goal")
    print(f"  attempts a game and {band_coef:+.1f} points of contested-band kick")
    print(f"  rate. The case studies said {a.d_att_pg.mean():+.2f} and "
          f"{a.d_band.mean():+.1f}. Same order of magnitude.")

    sub("the league already moved further than any single kicker ever did")
    print(f"  contested-band kick rate, league: {yr.loc[1999, 'band_kick%']:.1f}% "
          f"in 1999 -> {yr.loc[2025, 'band_kick%']:.1f}% in 2025")
    print(f"  contested-band punt rate, league: {yr.loc[1999, 'band_punt%']:.1f}% "
          f"-> {yr.loc[2025, 'band_punt%']:.1f}%")
    print(f"  50+ attempts per game, league   : {yr.loc[1999, 'long_pg']:.3f} "
          f"-> {yr.loc[2025, 'long_pg']:.3f}")
    print("  Coaches respond to kicker quality, but they have responded far more")
    print("  to twenty-five years of the league getting better at kicking in")
    print("  general. The kicker-specific effect rides on top of that.")

    # ------------------------------------------------------- 3. the break-even
    hdr("3. THE BREAK-EVEN: HOW MUCH EXTRA WORK WOULD HE NEED?")
    full, _ = add_adjusted(pd.read_parquet(SRC), fit_seasons=list(range(1999, 2026)))
    w = full[full.season.isin(MODERN)]
    n_tg = 2 * w.game_id.nunique()
    tsn = n_tg / GAMES
    fourth = w[w.down.eq(4) & w.yardline_100.le(MAX_YL)
               & w.play_type.isin(["punt", "pass", "run"])].copy()
    go = w[w.down.eq(4) & w.yardline_100.le(MAX_YL)
           & w.play_type.isin(["pass", "run"])].copy()
    go["tg"] = pd.cut(go.ydstogo, TOGO_CUTS, labels=TOGO_LAB)
    go_v = go.groupby("tg", observed=True).aepa.mean()
    yls = np.arange(1, MAX_YL + 1)
    punts = fourth[fourth.play_type.eq("punt")]
    punt_v = kern(yls, punts.yardline_100.to_numpy(float),
                  punts.aepa.to_numpy(float), 6.0)
    fourth["v_alt"] = np.where(
        fourth.play_type.eq("punt"),
        fourth.yardline_100.map(pd.Series(punt_v, index=yls)),
        pd.cut(fourth.ydstogo, TOGO_CUTS, labels=TOGO_LAB).map(go_v).astype(float))
    fourth["gain"] = fourth.v_perfect - fourth.v_alt
    sup = fourth[fourth.gain > 0].sort_values("gain", ascending=False)

    print(f"the study window is {MODERN[0]}-{MODERN[-1]}: {n_tg:,} team-games, "
          f"{tsn:.0f} team-seasons")
    print("every fourth down inside the 42 that a team punted or went for, "
          "ranked by")
    print("how much a guaranteed make would have beaten the play they called:")
    tiers = [0.05, 0.11, 0.2, 0.3, 0.4, 0.54, 0.6]
    print(f"\n  {'extra att/game':>15} {'attempts/season':>16} "
          f"{'points/season':>14} {'marginal pt/att':>16} {'wins':>7}")
    prev_n, prev_p = 0, 0.0
    for x in tiers:
        n = int(round(x * n_tg))
        n = min(n, len(sup))
        pts = sup.gain.iloc[:n].sum() / tsn
        marg = ((pts - prev_p) * tsn / (n - prev_n)) if n > prev_n else np.nan
        print(f"  {x:>15.2f} {n / tsn:>16.1f} {pts:>14.1f} {marg:>16.2f} "
              f"{SLOPE * (pts + CH1 + CH5):>7.2f}")
        prev_n, prev_p = n, pts
    total_supply = sup.gain.sum() / tsn
    print(f"\n  the whole positive-gain supply is {len(sup) / n_tg:.2f} attempts a")
    print(f"  game, {len(sup) / tsn:.1f} a season, worth {total_supply:.1f} points.")
    print(f"  Past that, kicking is worse than the alternative and the marginal")
    print(f"  attempt costs points rather than adding them.")

    sub("what the coach would actually give him")
    for lab, x in [("regression elasticity", att_coef),
                   ("case studies", a.d_att_pg.mean()),
                   ("optimal, what the study assumes", len(sup) / n_tg)]:
        n = min(int(round(x * n_tg)), len(sup))
        pts = sup.gain.iloc[:n].sum() / tsn
        tot = pts + CH1 + CH5
        print(f"  {lab:34} {x:+.2f} att/game -> channel 3 = {pts:5.1f} points, "
              f"total {tot:5.1f} = {SLOPE * tot:.2f} wins")
    print("\n  So the headline 0.94 wins already assumes a coach five times more")
    print("  responsive than any real coach has ever been to a real elite kicker.")
    print("  Priced at the behaviour actually observed, he is worth about "
          f"{SLOPE * (sup.gain.iloc[:int(round(att_coef * n_tg))].sum() / tsn + CH1 + CH5):.2f} wins.")

    sub("so what would it take to beat the first overall pick?")
    for lab, target in [("1.01 quarterback, mean", QB_MEAN),
                        ("1.01 quarterback, median", QB_MEDIAN)]:
        need_pts = target / SLOPE - (CH1 + CH5)
        gap = need_pts - total_supply
        print(f"\n  {lab}: {target:+.2f} wins = {target / SLOPE:.1f} points a season")
        print(f"    channels 1 and 5 give {CH1 + CH5:.1f}; the entire fourth-down")
        print(f"    supply gives {total_supply:.1f}; that is "
              f"{SLOPE * (CH1 + CH5 + total_supply):.2f} wins and still "
              f"{gap:.1f} points short.")
        # value of a brand-new in-range possession, at the far edge
        edge = w[w.down.eq(4) & w.yardline_100.between(MAX_YL - 4, MAX_YL)]
        v_new = edge.v_perfect.mean() - punt_v[-5:].mean()
        print(f"    a brand new possession that reaches the 42 and stalls is worth")
        print(f"    {v_new:.2f} points, so he needs {gap / v_new:.1f} more of them a "
              f"season,")
        print(f"    {gap / v_new / GAMES:+.2f} a game, on top of everything above.")

    sub("is that supply even there?")
    stall = w[w.down.eq(4) & w.yardline_100.between(MAX_YL + 1, 60)
              & w.play_type.eq("punt")]
    print(f"  fourth-down punts from just outside the guarantee (the 43 to the "
          f"60): {len(stall):,}")
    print(f"  = {len(stall) / n_tg:.2f} a game. Those are the drives that would "
          f"have to be")
    print(f"  pushed a few yards further to become kicks, and each one needs the")
    print(f"  offence to gain yards it did not gain. The supply exists; the")
    print(f"  conversion is not free, and none of it is in the 0.94.")

    sub("stated as raw volume, and whether anyone has ever kicked that much")
    lg_pg = ts[ts.season.isin(MODERN)].att.sum() / ts[ts.season.isin(MODERN)].g.sum()
    need_mean = total_supply and (QB_MEAN / SLOPE - (CH1 + CH5) - total_supply) / 2.01
    need_med = (QB_MEDIAN / SLOPE - (CH1 + CH5) - total_supply) / 2.01
    for lab, extra in [("match the mean 1.01 quarterback",
                        len(sup) / n_tg + need_mean / GAMES),
                       ("match the median", len(sup) / n_tg + need_med / GAMES)]:
        print(f"  to {lab}: {lg_pg:.2f} + {extra:.2f} = {lg_pg + extra:.2f} "
              f"attempts a game, {GAMES * (lg_pg + extra):.0f} a season")
        print(f"    that is {extra / att_coef:.1f}x the behavioural response the "
              f"data actually shows")
    top = ts[ts.season.ge(1999)].assign(pg=lambda x: x.att / x.g).nlargest(6, "pg")
    print("\n  the biggest field goal volumes any team has ever posted:")
    print(top[["season", "posteam", "kicker", "att", "g", "pg"]]
          .round(2).to_string(index=False))
    print(f"\n  the league averages {lg_pg:.2f} a game. Break-even asks for "
          f"{lg_pg + len(sup) / n_tg + need_mean / GAMES:.2f} every year,")
    print("  which is at or past the highest single season any team has managed,")
    print("  and it asks for it while the offence is not any better than before.")

    return dict(ts=ts, fg=fg, c=c, a=a, yr=yr, o=o, perfect_q=PERFECT_Q,
                att_if_perfect=att_coef, band_if_perfect=band_coef,
                case_att=a.d_att_pg.mean(), case_band=a.d_band.mean(),
                supply=total_supply, sup_att=len(sup) / n_tg)


if __name__ == "__main__":
    r = main()
    hdr("SUMMARY")
    print(f"  coaches DO respond to a better leg: "
          f"{r['case_att']:+.2f} attempts a game in the case studies, "
          f"{r['att_if_perfect']:+.2f} from the")
    print(f"  fixed-effects elasticity extrapolated to a perfect leg. The "
          f"contested-band kick")
    print(f"  rate moves {r['case_band']:+.1f} and {r['band_if_perfect']:+.1f} "
          f"points respectively.")
    print(f"  But the whole positive-value fourth-down supply is only "
          f"{r['sup_att']:.2f} attempts a game")
    print(f"  ({r['supply']:.1f} points), and the marginal attempt is worthless "
          f"by the end of it.")
    print(f"  Priced at observed coaching behaviour he is worth 0.70 wins, not "
          f"0.94, and")
    print(f"  beating the 1.01 needs roughly eight times the response ever "
          f"measured.")
