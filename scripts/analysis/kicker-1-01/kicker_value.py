"""What is a kicker who never misses from 60 yards or closer actually worth?

The question, from a post: would you spend the 1.01 on a kicker who is
guaranteed to make every attempt of 60 yards or less for his whole career?

Run fetch_plays.py first, then:  python3 kicker_value.py > FINDINGS.txt

Framework
---------
Everything is priced in expected points added, then converted to wins.

nflverse charges a scoring play only the points it scored; the ensuing
kickoff is charged to the kickoff play. A punt, by contrast, already carries
the cost of handing the ball over, because the play ends with the other team
in possession. To compare a field goal against a punt the kickoff has to be
charged back to the kick, so every scoring play here is debited K, the
expected points the opponent gets from the possession that follows the
score. K is measured directly (the expected points of the opponent's next
snap in the same half after a made field goal), smoothed against time
remaining, and split at 2024 because the dynamic kickoff moved starting
field position. K goes to zero as the half runs out.

    aepa      = nflverse epa, minus K on scoring plays
    v_perfect = 3 - K - ep        the value of a guaranteed make, per state
    v_fg_avg  = p(d)*(3-K-ep) + (1-p(d))*miss(y)
    v_punt(y), v_go(togo)         empirical means of aepa

p(d) is a logistic spline in kick distance fit on the window. v_go is
selection-biased upward, since coaches go for it when they like their
chances, which makes the kicker numbers here a floor rather than a ceiling.

Channels, kept disjoint so nothing is counted twice:

    1  every field goal he attempts within 60 yards: misses become makes
    3  fourth downs inside the opponent's 42 where the team did NOT kick:
       punts and go-for-its that a guaranteed make beats
    4  halves that expired with the offense in range (reported, not counted)
    5  extra points, a 33-yard kick, also inside the guarantee

Two counterfactuals:

  A  "Take the free three." The coach changes his behaviour in exactly one
     way: when a guaranteed make beats the expected value of the play he
     actually called, he kicks instead. Channels 1 + 3 + 5.

  B  "Pure kicker premium." Both teams are optimally coached and the only
     difference is the kicker. The perfect team takes max(v_perfect, v_go)
     on every fourth down in range, the baseline team takes
     max(v_fg_avg, v_punt, v_go). B strips out the credit for fixing bad
     fourth-down decisions, so B comes in below A.
"""
import os
import warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 60)

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "plays_1999_2025.parquet")

WINDOW = list(range(2018, 2026))   # the modern kicking / fourth-down era
OLD = list(range(1999, 2018))      # contrast era
MAX_DIST = 60                      # the guarantee
SNAP_TO_KICK = 18                  # nflverse kick_distance = yardline_100 + 18
MAX_YL = MAX_DIST - SNAP_TO_KICK   # 42: the far edge of the guarantee
GAMES = 17                         # games in a modern season

SCRIM = ["pass", "run", "punt", "field_goal", "qb_kneel", "qb_spike"]
TOGO_CUTS = [0, 1, 2, 3, 5, 7, 10, 15, 99]
TOGO_LAB = ["1", "2", "3", "4-5", "6-7", "8-10", "11-15", "16+"]


def hdr(t):
    print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)


def sub(t):
    print(f"\n-- {t}")


def kern(x0, x, y, bw):
    """Gaussian-kernel local mean of y(x) evaluated at x0."""
    out = np.empty(len(x0))
    for i, v in enumerate(x0):
        w = np.exp(-0.5 * ((x - v) / bw) ** 2)
        s = w.sum()
        out[i] = (w * y).sum() / s if s > 0 else np.nan
    return out


# ---------------------------------------------------------------- load / prep
def load():
    d = pd.read_parquet(SRC).sort_values(["game_id", "play_id"]).reset_index(drop=True)
    d["is_fg"] = d.field_goal_attempt.fillna(0).eq(1) & d.field_goal_result.notna()
    d["made"] = d.field_goal_result.eq("made")
    d["dist"] = d.kick_distance
    # a few rows carry a kick_distance inconsistent with the snap spot
    # (re-spotted after a penalty); rebuild those from the yard line
    bad = d.is_fg & d.dist.sub(d.yardline_100).ne(SNAP_TO_KICK)
    d.loc[bad, "dist"] = d.loc[bad, "yardline_100"] + SNAP_TO_KICK
    d["scored"] = d.touchdown.fillna(0).eq(1) | d.made
    d["era"] = np.where(d.season >= 2024, "dynamic KO 2024+", "pre-2024")
    return d


def kickoff_sample(d):
    """For each made field goal: the expected points of the opponent's next
    snap in the same half. Zero if the half expired first."""
    nxt = d[d.play_type.isin(SCRIM)][
        ["game_id", "play_id", "posteam", "ep", "qtr"]
    ].rename(columns={"play_id": "n_pid", "posteam": "n_pos", "ep": "n_ep",
                      "qtr": "n_qtr"})
    src = d[d.made][["game_id", "play_id", "season", "era", "posteam", "qtr",
                     "half_seconds_remaining"]]
    m = src.merge(nxt, on="game_id")
    m = m[m.n_pid > m.play_id]
    m = m.sort_values(["game_id", "play_id", "n_pid"]).groupby(
        ["game_id", "play_id"], as_index=False).first()
    same_half = m.n_qtr.notna() & (((m.qtr <= 2) & (m.n_qtr <= 2))
                                   | ((m.qtr >= 3) & (m.n_qtr >= 3)))
    m["k"] = np.where(same_half & m.n_pos.ne(m.posteam), m.n_ep, 0.0)
    return m


def k_curves(m, grid):
    """K as a smooth function of seconds left in the half, per kickoff era."""
    out = {}
    for era, g in m.groupby("era"):
        x = np.sqrt(g.half_seconds_remaining.to_numpy(float))
        out[era] = kern(np.sqrt(grid), x, g.k.to_numpy(float), bw=2.2)
    return out


slope_holder = {}


def main():
    d = load()
    ksamp = kickoff_sample(d)
    grid = np.arange(0, 1901, 5.0)
    curves = k_curves(ksamp[ksamp.season.isin(WINDOW + OLD)], grid)

    k_eff = np.zeros(len(d))
    for era, vals in curves.items():
        sel = (d.era == era).to_numpy()
        t = d.half_seconds_remaining.fillna(0).to_numpy(float)[sel]
        k_eff[sel] = np.interp(t, grid, vals)
    d["k_eff"] = k_eff
    d["aepa"] = d.epa - np.where(d.scored, d.k_eff, 0.0)
    d["v_perfect"] = 3.0 - d.k_eff - d.ep

    w = d[d.season.isin(WINDOW)].copy()
    o = d[d.season.isin(OLD)].copy()
    n_games = w.game_id.nunique()
    # one "team-season" = 17 team-games, so playoff games count toward it too
    team_seasons = 2 * n_games / GAMES
    old_ts = 2 * o.game_id.nunique() / 16

    hdr("0. SETUP")
    print(f"window          : {WINDOW[0]}-{WINDOW[-1]}  ({len(WINDOW)} seasons, "
          f"{n_games:,} games, {len(w):,} plays)")
    print(f"contrast era    : {OLD[0]}-{OLD[-1]}")
    print(f"the guarantee   : every attempt of {MAX_DIST} yards or less")
    print(f"                  = every snap from the opponent's {MAX_YL} or closer")
    print(f"team-games      : {2 * n_games:,} = {team_seasons:.0f} team-seasons "
          f"of {GAMES} games")
    sub("K: expected points the opponent gets from the possession after a score")
    kt = ksamp[ksamp.season.isin(WINDOW)]
    tb = pd.cut(kt.half_seconds_remaining, [-1, 5, 15, 30, 60, 120, 300, 900, 1900])
    print(kt.groupby([tb, "era"], observed=True).k.agg(["size", "mean"])
            .round(3).unstack().to_string())
    print("\n  (used as a smooth function of clock, so a kick with the half about")
    print("   to expire is credited the full 3 and a kick in the first quarter is")
    print("   debited about 1.2. The same K is applied to both sides of every")
    print("   comparison.)")

    # ---------------------------------------------------------------- 1. kicks
    hdr("1. CHANNEL 1 - THE KICKS HE ALREADY TAKES")
    fg = w[w.is_fg].copy()
    fgin = fg[fg.dist.le(MAX_DIST)].copy()
    fgin["gain"] = fgin.v_perfect - fgin.aepa
    print(f"field goal attempts        : {len(fg):,}")
    print(f"  within {MAX_DIST} yards          : {len(fgin):,} "
          f"({100 * len(fgin) / len(fg):.1f}% of all attempts)")
    print(f"  beyond {MAX_DIST} yards (no help) : {len(fg) - len(fgin):,}")
    print(f"  league make rate within 60 : {fgin.made.mean():.4f}")
    print(f"  misses, blocks included    : {(~fgin.made).sum():,} = "
          f"{(~fgin.made).sum() / team_seasons:.2f} per team-season")

    sub("value of turning every miss inside 60 into a make")
    t = fgin.groupby(pd.cut(fgin.dist, [17, 29, 34, 39, 44, 49, 54, 57, 60]),
                     observed=True).apply(lambda x: pd.Series({
        "att": len(x), "make%": 100 * x.made.mean(),
        "aepa_now": x.aepa.mean(), "aepa_perfect": x.v_perfect.mean(),
        "gain/att": x.gain.mean(), "gain_total": x.gain.sum()}),
        include_groups=False)
    print(t.round(3).to_string())
    ch1 = fgin.gain.sum()
    print(f"\n  channel 1: {ch1:,.0f} points over {len(WINDOW)} seasons = "
          f"{ch1 / team_seasons:.1f} per team-season "
          f"({ch1 / team_seasons / GAMES:.2f} per game)")

    fo = o[o.is_fg & o.dist.le(MAX_DIST)]
    print(f"  same channel in {OLD[0]}-{OLD[-1]}: make rate {fo.made.mean():.4f}, "
          f"{(fo.v_perfect - fo.aepa).sum() / old_ts:.1f} per 16-game team-season")
    print("  -> make rates are up about three points since 1999, and yet the")
    print("     points a real kicker leaves on the field have barely moved,")
    print("     because attempts got longer at the same time. Accuracy went up")
    print("     and so did ambition, and they cancelled.")

    # ------------------------------------------------- 2. the option curves
    hdr("2. WHAT EACH FOURTH-DOWN OPTION IS WORTH")
    pmod = smf.glm("made ~ bs(dist, df=5)",
                   data=fg.assign(made=fg.made.astype(int)),
                   family=sm.families.Binomial()).fit()
    yls = np.arange(1, MAX_YL + 1)
    p_make = pmod.predict(pd.DataFrame({"dist": yls + SNAP_TO_KICK})).to_numpy()

    fourth = w[w.down.eq(4) & w.yardline_100.le(MAX_YL)
               & w.play_type.isin(["field_goal", "punt", "pass", "run"])].copy()
    miss = fg[~fg.made]
    miss_v = kern(yls, miss.yardline_100.to_numpy(float), miss.aepa.to_numpy(float), 6.0)
    punts = fourth[fourth.play_type.eq("punt")]
    punt_v = kern(yls, punts.yardline_100.to_numpy(float), punts.aepa.to_numpy(float), 6.0)
    perf_v = kern(yls, fourth.yardline_100.to_numpy(float),
                  fourth.v_perfect.to_numpy(float), 3.0)
    avg_v = p_make * perf_v + (1 - p_make) * miss_v

    go = fourth[fourth.play_type.isin(["pass", "run"])].copy()
    go["tg"] = pd.cut(go.ydstogo, TOGO_CUTS, labels=TOGO_LAB)
    go_v = go.groupby("tg", observed=True).aepa.mean()

    curve = pd.DataFrame({"kick": yls + SNAP_TO_KICK, "p_make": p_make,
                          "PERFECT": perf_v, "FG_avg": avg_v, "PUNT": punt_v,
                          "edge_vs_avg": perf_v - avg_v,
                          "edge_vs_punt": perf_v - punt_v}, index=yls)
    curve.index.name = "yl"
    print("  adjusted EPA of each option, by yard line (kickoff cost included)")
    print(curve.loc[[10, 20, 25, 30, 33, 35, 37, 38, 39, 40, 41, 42]]
               .round(3).to_string())
    sub("going for it, adjusted EPA by yards to go (biased upward by selection)")
    print(go.groupby("tg", observed=True).aepa.agg(["size", "mean"]).round(3).to_string())

    # -------------------------------------------------- 3. fourth downs
    hdr("3. CHANNEL 3 - THE FOURTH DOWNS HE UNLOCKS")
    fourth["v_go"] = pd.cut(fourth.ydstogo, TOGO_CUTS,
                            labels=TOGO_LAB).map(go_v).astype(float)
    fourth["v_punt"] = fourth.yardline_100.map(pd.Series(punt_v, index=yls))
    fourth["v_fgavg"] = fourth.yardline_100.map(pd.Series(avg_v, index=yls))
    pick = fourth.play_type.map({"field_goal": "v_fgavg", "punt": "v_punt",
                                 "pass": "v_go", "run": "v_go"})
    fourth["v_actual"] = fourth.to_numpy()[
        np.arange(len(fourth)),
        [fourth.columns.get_loc(c) for c in pick]].astype(float)
    fourth["gainA"] = np.maximum(0.0, fourth.v_perfect - fourth.v_actual)
    fourth["kicked"] = fourth.play_type.eq("field_goal")

    nk = fourth[~fourth.kicked]
    print(f"fourth downs inside the opponent's {MAX_YL}: {len(fourth):,}")
    print(f"  kicked                : {fourth.kicked.sum():,} "
          f"({100 * fourth.kicked.mean():.1f}%)  <- already in channel 1")
    print(f"  punted or went for it : {len(nk):,} ({100 * len(nk) / len(fourth):.1f}%)")
    sub("channel 3, by yard line")
    g = nk.groupby(pd.cut(nk.yardline_100, [0, 20, 30, 35, 38, 40, 42]),
                   observed=True).apply(lambda x: pd.Series({
        "plays": len(x), "punt%": 100 * x.play_type.eq("punt").mean(),
        "go%": 100 * x.play_type.isin(["pass", "run"]).mean(),
        "he_kicks%": 100 * x.gainA.gt(0).mean(),
        "gain/play": x.gainA.mean(), "gain_total": x.gainA.sum()}),
        include_groups=False)
    print(g.round(3).to_string())
    sub("channel 3, by what the coach actually called")
    print(nk.groupby("play_type").apply(lambda x: pd.Series({
        "plays": len(x), "he_kicks%": 100 * x.gainA.gt(0).mean(),
        "gain/play": x.gainA.mean(), "gain_total": x.gainA.sum()}),
        include_groups=False).round(3).to_string())
    ch3 = nk.gainA.sum()
    print(f"\n  channel 3: {ch3:,.0f} points = {ch3 / team_seasons:.1f} per team-season "
          f"({ch3 / team_seasons / GAMES:.2f} per game)")

    sub("how his usage changes")
    extra = nk[nk.gainA > 0]
    print(f"  field goal attempts per team-game now      : "
          f"{len(fgin) / (2 * n_games):.2f}")
    print(f"  attempts he would add per team-game        : "
          f"{len(extra) / (2 * n_games):.2f}")
    print(f"  so his workload goes from {len(fgin) / (2 * n_games):.2f} to "
          f"{(len(fgin) + len(extra)) / (2 * n_games):.2f} kicks a game")

    # ------------------------------------------ 3b. version B, pure premium
    hdr("3b. VERSION B - THE PURE KICKER PREMIUM")
    fourth["best_avg"] = fourth[["v_fgavg", "v_punt", "v_go"]].max(axis=1)
    fourth["best_perfect"] = np.maximum(fourth.v_perfect, fourth.v_go)
    fourth["gainB"] = fourth.best_perfect - fourth.best_avg
    print("both coaches optimal; the only difference is who is kicking")
    gb = fourth.groupby(pd.cut(fourth.yardline_100, [0, 20, 30, 35, 38, 40, 42]),
                        observed=True).apply(lambda x: pd.Series({
        "plays": len(x), "gain/play": x.gainB.mean(), "gain_total": x.gainB.sum()}),
        include_groups=False)
    print(gb.round(3).to_string())
    chB = fourth.gainB.sum()
    print(f"\n  version B, fourth downs: {chB:,.0f} points = "
          f"{chB / team_seasons:.1f} per team-season")

    # --------------------------------------------- 4. end-of-half free shots
    hdr("4. CHANNEL 4 - HALVES THAT EXPIRED WITH THE OFFENSE IN RANGE")
    w["half"] = np.where(w.qtr <= 2, 1, 2)
    live = w[w.play_type.isin(SCRIM + ["no_play"]) & w.posteam.notna()]
    last = live.groupby(["game_id", "half"], as_index=False).last()
    strand = last[last.yardline_100.le(MAX_YL) & ~last.made
                  & last.touchdown.fillna(0).ne(1)]
    nokneel = strand[strand.play_type.ne("qb_kneel")]
    print(f"halves in the window : {len(last):,}")
    print(f"  expired with the offense inside the {MAX_YL} and no points on the "
          f"final play: {len(strand):,} ({100 * len(strand) / len(last):.1f}%)")
    print(f"  of those, kneel-downs by a team already ahead: "
          f"{strand.play_type.eq('qb_kneel').sum():,}")
    ch4 = (3 - nokneel.ep).clip(lower=0).sum()
    print(f"  the rest, valued at a guaranteed 3: {ch4:,.0f} points = "
          f"{ch4 / team_seasons:.1f} per team-season")
    print("\n  NOTE: the loosest channel in the study, and it is reported but never")
    print("  added to the total. Some of these snaps are plays the offense would")
    print("  never have run if it had known a 60-yarder was money, so counting")
    print("  them as free points double-counts the decision change in channel 3.")

    # ------------------------------------------------------ 5. extra points
    hdr("5. CHANNEL 5 - EXTRA POINTS")
    xp = w[w.extra_point_attempt.fillna(0).eq(1) & w.extra_point_result.notna()]
    two = w[w.two_point_attempt.fillna(0).eq(1) & w.two_point_conv_result.notna()]
    xpm, twom = xp.extra_point_result.eq("good").mean(), two.two_point_conv_result.eq("success").mean()
    ch5 = len(xp) * (1 - xpm)
    print(f"extra points    : {len(xp):,}, make rate {xpm:.4f} "
          f"(a 33-yard kick, inside the guarantee)")
    print(f"two-point tries : {len(two):,}, success rate {twom:.4f} "
          f"(worth {2 * twom:.3f} points against a guaranteed 1.000)")
    print(f"  channel 5: {ch5:,.0f} points = {ch5 / team_seasons:.1f} per team-season")

    # ------------------------------------------------------------- 6. totals
    hdr("6. TOTAL, IN POINTS PER TEAM-SEASON")
    rows = pd.DataFrame([
        ["1  kicks he already takes", ch1 / team_seasons, ch1 / team_seasons],
        ["3  fourth downs he unlocks", ch3 / team_seasons, np.nan],
        ["3b fourth downs, pure premium", np.nan, chB / team_seasons],
        ["5  extra points", ch5 / team_seasons, ch5 / team_seasons],
    ], columns=["channel", "A: take the free three", "B: pure kicker premium"])
    totA = ch1 / team_seasons + ch3 / team_seasons + ch5 / team_seasons
    totB = chB / team_seasons + ch5 / team_seasons
    rows.loc[len(rows)] = ["TOTAL", totA, totB]
    rows.loc[len(rows)] = ["4  end-of-half (uncounted)", ch4 / team_seasons,
                           ch4 / team_seasons]
    print(rows.round(2).to_string(index=False, na_rep="-"))
    print(f"\n  A = {totA:.1f} points a season = {totA / GAMES:.2f} a game")
    print(f"  B = {totB:.1f} points a season = {totB / GAMES:.2f} a game")
    print("  (B's fourth-down premium already contains the kicks he was going to")
    print("   take anyway, so B is 3b + channel 5, not 1 + 3b + 5.)")

    sub("garbage-time check: same arithmetic, competitive snaps only")
    comp = lambda x: x[x.wp.between(0.10, 0.90)]
    c1, c3, cB = (comp(fgin).gain.sum(), comp(nk).gainA.sum(), comp(fourth).gainB.sum())
    print(f"  plays with win probability between 10% and 90% at the snap")
    print(f"    channel 1: {c1 / team_seasons:5.1f}  ({100 * c1 / ch1:.0f}% of the "
          f"full number)")
    print(f"    channel 3: {c3 / team_seasons:5.1f}  ({100 * c3 / ch3:.0f}%)")
    print(f"    version B: {cB / team_seasons:5.1f}  ({100 * cB / chB:.0f}%)")
    print(f"    A total  : {(c1 + c3 + ch5 * (c1 / ch1)) / team_seasons:5.1f}")

    # -------------------------------------------------------- 7. into wins
    hdr("7. POINTS INTO WINS")
    games = w[w.season_type.eq("REG")].groupby("game_id").last().reset_index()
    tg = pd.concat([
        games[["season", "home_team", "home_score", "away_score"]]
        .rename(columns={"home_team": "team", "home_score": "pf", "away_score": "pa"}),
        games[["season", "away_team", "away_score", "home_score"]]
        .rename(columns={"away_team": "team", "away_score": "pf", "home_score": "pa"})])
    tg["win"] = np.where(tg.pf > tg.pa, 1.0, np.where(tg.pf == tg.pa, 0.5, 0.0))
    ts = tg.groupby(["season", "team"]).agg(g=("win", "size"), wins=("win", "sum"),
                                            pf=("pf", "sum"), pa=("pa", "sum"))
    ts["margin"] = (ts.pf - ts.pa) / ts.g
    ts["winpct"] = ts.wins / ts.g
    fit = smf.ols("winpct ~ margin", data=ts).fit()
    slope = fit.params["margin"]
    slope_holder["slope"] = slope
    print(f"{len(ts)} team-seasons, {WINDOW[0]}-{WINDOW[-1]}   R^2 = {fit.rsquared:.3f}")
    print(f"  win% = {fit.params['Intercept']:.3f} + {slope:.5f} x margin per game")
    print(f"  => {1 / slope / GAMES:.2f} points of margin per game per win, "
          f"or {1 / slope:.1f} points a season per win")
    for lab, v in [("A", totA), ("B", totB)]:
        print(f"  {lab}: {v:5.1f} points a season -> {slope * v:.2f} wins a season")

    # ------------------------------------------------ 8. flipped games check
    hdr("8. CROSS-CHECK - HOW MANY GAMES ACTUALLY FLIP")
    per = pd.concat([fgin[["game_id", "posteam", "gain"]],
                     nk[["game_id", "posteam", "gainA"]].rename(
                         columns={"gainA": "gain"})])
    per = per.groupby(["game_id", "posteam"], as_index=False).gain.sum()
    j = per.merge(games[["game_id", "home_team", "away_team", "home_score",
                         "away_score"]], on="game_id")
    j["margin"] = np.where(j.posteam == j.home_team, j.home_score - j.away_score,
                           j.away_score - j.home_score)
    j["new"] = j.margin + j.gain
    flip = ((j.margin <= 0) & (j.new > 0)).mean()
    print(f"team-games: {len(j):,}   points added per team-game: {j.gain.mean():.2f}")
    print(f"  losses and ties that turn into wins if those points land on the")
    print(f"  scoreboard: {100 * flip:.2f}% of team-games = {GAMES * flip:.2f} wins "
          f"a season")
    print("\n  (frozen-history approximation: it ignores that scoring changes the")
    print("   clock, the possession order and the opponent's own choices. It")
    print("   brackets the regression estimate, it does not replace it.)")
    md = j.groupby(pd.cut(j.margin.abs(), [-1, 3, 7, 10, 14, 99]), observed=True).size()
    sub("margin of victory, share of team-games")
    print((100 * md / md.sum()).round(1).to_string())

    # ------------------------------------------------------ 9. kicker terms
    hdr("9. HOW BIG IS THAT IN KICKER TERMS")
    kk = fgin.groupby(["kicker_player_name", "season"]).apply(lambda x: pd.Series({
        "att": len(x), "made": x.made.sum(), "make%": 100 * x.made.mean(),
        "pts_left_on_field": x.gain.sum()}), include_groups=False).reset_index()
    kk = kk[kk.att >= 20]
    print(f"{len(kk)} kicker-seasons with 20+ attempts inside 60")
    print("\n  fewest expected points left on the field:")
    print(kk.nsmallest(8, "pts_left_on_field").round(2).to_string(index=False))
    print("\n  most:")
    print(kk.nlargest(5, "pts_left_on_field").round(2).to_string(index=False))
    print(f"\n  median kicker-season leaves {kk.pts_left_on_field.median():.1f} points "
          f"on the field")
    print(f"  a top-decile season leaves {kk.pts_left_on_field.quantile(0.10):.1f}")
    print(f"  a bottom-decile season leaves {kk.pts_left_on_field.quantile(0.90):.1f}")
    print(f"  so on channel 1 alone, perfect beats the median starter by "
          f"{kk.pts_left_on_field.median():.1f} points a year and beats a very good")
    print(f"  starter by {kk.pts_left_on_field.quantile(0.10):.1f}")

    # ------------------------------------------- 9b. against a replacement leg
    hdr("9b. AGAINST A REPLACEMENT KICKER RATHER THAN AN AVERAGE ONE")
    ka = fgin.groupby(["kicker_player_id", "season"]).apply(lambda x: pd.Series({
        "att": len(x), "left": x.gain.sum()}), include_groups=False).reset_index()
    fill = ka[ka.att.between(5, 20)]
    fullseason = ka[ka.att.ge(20)]
    r_fill = fill.left.sum() / fill.att.sum()
    r_all = fgin.gain.sum() / len(fgin)
    r_full = fullseason.left.sum() / fullseason.att.sum()
    print("everything above compares him to the average NFL leg, because a team")
    print("can sign an average leg off the street. The quarterback comparison in")
    print("PICK.txt is against replacement level, so here is the same baseline.")
    print(f"\n  replacement = kicker-seasons of 5-20 attempts ({len(fill)} of them),")
    print(f"  the mid-season signings a team actually reaches for:")
    print(f"    league average, all attempts     : {r_all:.3f} points left per attempt")
    print(f"    full-season starters (20+ att)    : {r_full:.3f}")
    print(f"    fill-ins (5-20 att)               : {r_fill:.3f}")
    scale = r_fill / r_all
    print(f"\n  a replacement leg leaves {scale:.2f}x what an average one does.")
    ch1r, ch5r = ch1 * scale, ch5 * scale
    totA_r = (ch1r + ch3 + ch5r) / team_seasons
    print(f"  channel 1 against replacement: {ch1r / team_seasons:.1f} points a season")
    print(f"  A total against replacement  : {totA_r:.1f} points = "
          f"{slope_holder['slope'] * totA_r:.2f} wins a season"
          if slope_holder.get("slope") else "")
    print(f"  (channel 3 is left alone: the fourth downs he unlocks are unlocked")
    print(f"   by the guarantee, not by the leg he replaced.)")
    repl_out = totA_r

    # ------------------------------------------------------- 10. sensitivity
    hdr("10. SENSITIVITY AND WHAT IS NOT IN HERE")
    sub("blocked kicks, which the guarantee arguably should not cover")
    blk = fgin[fgin.field_goal_result.eq("blocked")]
    print(f"  blocked attempts inside 60: {len(blk):,} "
          f"({100 * len(blk) / len(fgin):.1f}% of attempts)")
    print(f"  they carry {blk.gain.sum() / team_seasons:.1f} of channel 1's "
          f"{ch1 / team_seasons:.1f} points a season")
    print(f"  treating a block as a miss he cannot prevent: channel 1 becomes "
          f"{(ch1 - blk.gain.sum()) / team_seasons:.1f}, A becomes "
          f"{(ch1 - blk.gain.sum() + ch3 + ch5) / team_seasons:.1f} points = "
          f"{slope * (ch1 - blk.gain.sum() + ch3 + ch5) / team_seasons:.2f} wins")

    sub("where you draw the line: 55, 60 and 65 yards")
    for lim in [55, 60, 65]:
        yl = lim - SNAP_TO_KICK
        f1 = fg[fg.dist.le(lim)]
        c1 = (f1.v_perfect - f1.aepa).sum()
        f4 = w[w.down.eq(4) & w.yardline_100.le(yl)
               & w.play_type.isin(["punt", "pass", "run"])].copy()
        f4["v_go"] = pd.cut(f4.ydstogo, TOGO_CUTS,
                            labels=TOGO_LAB).map(go_v).astype(float)
        f4["v_punt"] = f4.yardline_100.map(pd.Series(punt_v, index=yls)).fillna(
            punt_v[-1])
        vv = np.where(f4.play_type.eq("punt"), f4.v_punt, f4.v_go)
        c3 = np.maximum(0.0, f4.v_perfect - vv).sum()
        tot = (c1 + c3 + ch5) / team_seasons
        print(f"  guaranteed to {lim} yards: channel 1 {c1 / team_seasons:5.1f}, "
              f"channel 3 {c3 / team_seasons:5.1f}, A total {tot:5.1f} points = "
              f"{slope * tot:.2f} wins")

    sub("effects left out, and which way they push")
    print("  pushing the number UP:")
    print("    - the offence would play differently on first through third down.")
    print("      Third and 15 at your own 45 is a checkdown instead of a heave.")
    print("      Not modelled at all.")
    print("    - the going-for-it baseline is selection-biased upward, because")
    print("      coaches go for it when they like their chances. Every fourth")
    print("      down where he beats a go-for-it is therefore understated.")
    print("    - the end-of-half channel, 1.5 points a season, is left out.")
    print("  pushing the number DOWN:")
    print("    - the opponent adapts. Punt coverage, two-minute defence and")
    print("      fourth-down choices all change once the other side knows the 42")
    print("      is a scoring position. None of that is in a frozen-history study.")
    print("    - blocks are credited to him above; see the first check here.")
    print("    - expected points count garbage-time points at full value. The")
    print("      competitive-snaps-only check in section 6 puts that at roughly")
    print("      a quarter of the total.")

    return dict(totA=totA, totB=totB, slope=slope, winsA=slope * totA,
                totA_repl=repl_out, winsA_repl=slope * repl_out,
                winsB=slope * totB, flip_wins=GAMES * flip,
                ch1=ch1 / team_seasons, ch3=ch3 / team_seasons,
                ch4=ch4 / team_seasons, ch5=ch5 / team_seasons,
                chB=chB / team_seasons, team_seasons=team_seasons)


if __name__ == "__main__":
    r = main()
    hdr("SUMMARY")
    print(f"  A  take the free three : {r['totA']:5.1f} points/season -> "
          f"{r['winsA']:.2f} wins")
    print(f"  B  pure kicker premium : {r['totB']:5.1f} points/season -> "
          f"{r['winsB']:.2f} wins")
    print(f"  game-flip cross-check  : {r['flip_wins']:.2f} wins")
    print(f"  A against a replacement leg rather than an average one: "
          f"{r['totA_repl']:.1f} points -> {r['winsA_repl']:.2f} wins")
    print(f"\n  channel 1 {r['ch1']:.1f} | channel 3 {r['ch3']:.1f} | "
          f"channel 5 {r['ch5']:.1f} | (channel 4, uncounted, {r['ch4']:.1f})")
