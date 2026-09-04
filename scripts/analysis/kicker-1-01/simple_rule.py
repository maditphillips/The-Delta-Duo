"""One simple rule: if going for it converts less than X% of the time, kick.

The earlier scripts decided each fourth down by comparing expected points,
which is right but hard to hold in your head. This one uses a rule you could
write on a wristband:

    inside the opponent's 42, if the league converts this yards-to-go less
    than X% of the time, the perfect kicker kicks it. Regardless of how long
    the field goal is.

Run fetch_plays.py first, then:  python3 simple_rule.py > RULE.txt

Because conversion rates fall as yards-to-go rises, any threshold X is the
same thing as "kick on fourth and N or longer", so the rule is reported that
way. Everything is priced on the same adjusted-EPA footing as
kicker_value.py (see epa_common.py), and the gains are signed: if the rule
tells him to kick somewhere it should not, the total pays for it.
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

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "plays_1999_2025.parquet")

WINDOW = list(range(2018, 2026))
MAX_DIST = 60
MAX_YL = MAX_DIST - SNAP_TO_KICK        # 42
GAMES = 17
GO = ["pass", "run"]

# carried over from FINDINGS.txt so the totals line up with the other scripts
SLOPE = 0.02796      # win% per point of margin per game, 2018-2025, R^2 0.81
CH1 = 17.79          # channel 1: the kicks he already takes
CH5 = 2.15           # channel 5: extra points
QB_MEAN, QB_MEDIAN = 1.28, 1.59
OBSERVED_RESPONSE = 0.11   # extra attempts/game real coaches give an elite leg


def hdr(t):
    print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)


def sub(t):
    print(f"\n-- {t}")


def rates(d, down, zone=None):
    p = d[d.down.eq(down) & d.play_type.isin(GO)]
    if zone is not None:
        p = p[p.yardline_100.le(zone)]
    p = p.assign(conv=p[f"{'third' if down == 3 else 'fourth'}_down_converted"]
                 .fillna(0).eq(1).astype(int),
                 tg=p.ydstogo.clip(upper=11))
    return p.groupby("tg").conv.agg(["size", "mean"])


def main():
    d, _ = add_adjusted(pd.read_parquet(SRC), fit_seasons=WINDOW)
    w = d[d.season.isin(WINDOW)].copy()
    n_tg = 2 * w.game_id.nunique()
    tsn = n_tg / GAMES

    hdr("1. HOW OFTEN DOES GOING FOR IT ACTUALLY WORK?")
    print(f"{WINDOW[0]}-{WINDOW[-1]} regular and post season, every fourth-down "
          f"run or pass.")
    print("Third down at the same distance is shown alongside, because fourth-down")
    print("rates are flattered by selection - coaches go for it when they like the")
    print("look. The truth for a team that HAD to go every time sits between them.")
    tab = pd.DataFrame({
        "4th_n": rates(w, 4)["size"], "4th_conv%": 100 * rates(w, 4)["mean"],
        "4th_n_in42": rates(w, 4, MAX_YL)["size"],
        "4th_conv%_in42": 100 * rates(w, 4, MAX_YL)["mean"],
        "3rd_n": rates(w, 3)["size"], "3rd_conv%": 100 * rates(w, 3)["mean"],
    })
    tab.index = [f"4th & {int(i)}" + ("+" if i == 11 else "") for i in tab.index]
    tab.index.name = "to go"
    print("\n" + tab.round(1).to_string())
    conv = (rates(w, 4, MAX_YL)["mean"] * 100).to_dict()

    # ---------------------------------------- what one kick is worth, per spot
    hdr("2. WHAT ONE GUARANTEED KICK IS WORTH, BY YARDS TO GO")
    print("Every fourth down inside the 42 that was NOT already a field goal,")
    print("split by what the team actually did. 'gain' is the points a guaranteed")
    print("make would have added over that choice. This is the raw material; the")
    print("rule sweep in section 3 is just cumulative sums of these rows.")
    fourth = w[w.down.eq(4) & w.yardline_100.le(MAX_YL)
               & w.play_type.isin(["field_goal", "punt"] + GO)].copy()
    nokick = fourth[~fourth.play_type.eq("field_goal")].copy()
    nokick["was"] = np.where(nokick.play_type.eq("punt"), "punt", "went for it")

    yls = np.arange(1, MAX_YL + 1)
    punts = nokick[nokick.play_type.eq("punt")]
    punt_v = kern(yls, punts.yardline_100.to_numpy(float),
                  punts.aepa.to_numpy(float), 6.0)
    go = nokick[nokick.play_type.isin(GO)]
    go_v = go.groupby(go.ydstogo.clip(upper=11)).aepa.mean()

    nokick["v_alt"] = np.where(
        nokick.play_type.eq("punt"),
        nokick.yardline_100.map(pd.Series(punt_v, index=yls)),
        nokick.ydstogo.clip(upper=11).map(go_v).astype(float))
    nokick["gain"] = nokick.v_perfect - nokick.v_alt

    per = nokick.groupby([nokick.ydstogo.clip(upper=11), "was"]).agg(
        n=("gain", "size"), gain=("gain", "mean")).unstack()
    per.columns = [f"{b}_{a}" for a, b in per.columns]
    per["conv%"] = pd.Series(conv)
    per["went_per_gm"] = per["went for it_n"] / n_tg
    per["punt_per_gm"] = per["punt_n"] / n_tg
    per.index = [f"4th & {int(i)}" + ("+" if i == 11 else "") for i in per.index]
    per.index.name = "to go"
    print("\n" + per[["conv%", "went for it_n", "went_per_gm", "went for it_gain",
                      "punt_n", "punt_per_gm", "punt_gain"]].round(2).to_string())
    print("\n  Two things read straight off this table.")
    print("  1. Replacing a PUNT with a guaranteed 3 wins at every distance, by")
    print(f"     about 2 points a go. Worst single case in "
          f"{nokick.was.eq('punt').sum():,} punts: "
          f"{nokick[nokick.was.eq('punt')].gain.min():+.2f}. It is never close:")
    print("     punting from the 39-42 is worth about -0.42 points, a guaranteed")
    print("     3 from there is worth about +1.73.")
    print("  2. Replacing a GO-FOR-IT flips sign at 4th & 5. Short yardage is")
    print("     where a touchdown is still live and 3 is a step down; long")
    print("     yardage is where the kick is free money.")
    xo = per["went for it_gain"]
    print(f"     4th & 1: {xo.iloc[0]:+.2f}   4th & 4: {xo.iloc[3]:+.2f}   "
          f"4th & 5: {xo.iloc[4]:+.2f}   4th & 8: {xo.iloc[7]:+.2f}")

    sub("so where are the losing kicks, if you kick on every fourth down?")
    bad = nokick[nokick.gain < 0]
    print(f"  {len(bad):,} of the {len(nokick):,} non-kick fourth downs lose points "
          f"({100 * len(bad) / len(nokick):.0f}%)")
    print(f"  punts among them: {bad.was.eq('punt').sum()}. Every single one is a "
          f"go-for-it.")
    bb = bad.assign(yl=pd.cut(bad.yardline_100, [0, 10, 20, 32, 42]))
    print("\n  " + pd.crosstab(bb.yl, bb.ydstogo.clip(upper=11).astype(int),
                               margins=True).to_string().replace("\n", "\n  "))
    print(f"\n  {100 * bad.yardline_100.le(10).mean():.0f}% of them are inside the")
    print(f"  opponent's 10, and {100 * bad.ydstogo.le(2).mean():.0f}% are 4th & 1 "
          f"or 4th & 2. That is the whole story of the")
    print("  losses: 4th and goal-ish from the 5, where 65% of the time you get a")
    print("  first down worth nearly seven, and the rule takes three instead.")

    # ------------------------------------------------------------- the rule
    hdr("3. THE RULE SWEPT: KICK WHENEVER IT IS FOURTH AND N OR LONGER")
    print("Lower N means MORE kicking. N=1 kicks on every fourth down inside the")
    print("42; N=11 kicks only on fourth and 11 or longer. Each row is the")
    print("cumulative sum of section 2 from N downward.")

    # the same rule with an ordinary NFL leg, to separate the guarantee itself
    # from simply being more willing to kick. Make probability comes from a
    # logistic spline in kick distance; the value of a make is the play's own
    # v_perfect, so the state (down, distance, clock) is respected.
    fgs = w[w.is_fg & w.dist.le(MAX_DIST)]
    pmod = smf.glm("made ~ bs(dist, df=5)",
                   data=fgs.assign(made=fgs.made.astype(int)),
                   family=sm.families.Binomial()).fit()
    miss_v = pd.Series(kern(yls, fgs[~fgs.made].yardline_100.to_numpy(float),
                            fgs[~fgs.made].aepa.to_numpy(float), 6.0), index=yls)
    p = pmod.predict(pd.DataFrame(
        {"dist": nokick.yardline_100 + SNAP_TO_KICK})).to_numpy()
    nokick["gain_avg"] = (p * nokick.v_perfect
                          + (1 - p) * nokick.yardline_100.map(miss_v)
                          - nokick.v_alt)

    kicked_pg = len(fgs) / n_tg
    rows = []
    for n in range(1, 12):
        sel = nokick[nokick.ydstogo.ge(n)]
        pts = sel.gain.sum() / tsn
        pts_avg = sel.gain_avg.sum() / tsn
        tot = CH1 + pts + CH5
        rows.append({
            "kick if togo >=": n, "conv% at N": conv.get(min(n, 11), np.nan),
            "extra_att/gm": len(sel) / n_tg,
            "total_att/gm": kicked_pg + len(sel) / n_tg,
            "bad_kicks%": 100 * sel.gain.lt(0).mean() if len(sel) else np.nan,
            "ch3_pts": pts, "total_pts": tot, "wins": SLOPE * tot,
            "wins_avg_leg": SLOPE * (CH1 + pts_avg + CH5),
        })
    r = pd.DataFrame(rows)
    print("  'conv% at N' is the fourth-down conversion rate at exactly N to go,")
    print("  inside the 42: the threshold the rule is implicitly using.")
    print("  'bad_kicks%' is the share of the extra kicks where kicking was worse")
    print("  than the play the team actually called - the rule's own mistakes,")
    print("  and they are charged against the total.")
    print("  'wins_avg_leg' is the same rule run with an ordinary NFL kicker, so")
    print("  the gap between the last two columns is the guarantee itself.")
    print("\n" + r.round(2).to_string(index=False))

    sub("read it plainly")
    for n in [3, 5, 7]:
        row = r[r["kick if togo >="].eq(n)].iloc[0]
        print(f"  kick on 4th & {n} or longer (a {row['conv% at N']:.0f}% "
              f"conversion or worse):")
        print(f"    {row['extra_att/gm']:.2f} extra attempts a game "
              f"({row['extra_att/gm'] * GAMES:.0f} a season), "
              f"{row['total_att/gm']:.2f} total")
        print(f"    {row['ch3_pts']:.1f} points a season from the new kicks, "
              f"{row['total_pts']:.1f} all in")
        print(f"    {row['wins']:.2f} wins - against "
              f"{row['wins_avg_leg']:.2f} for the same rule with a normal leg")

    sub("under the best rule (4th & 4 or longer), where does the value sit?")
    pick = nokick[nokick.ydstogo.ge(4)].copy()
    pick["band"] = pd.cut(pick.yardline_100, [0, 15, 25, 32, 38, 42],
                          labels=["inside 15", "16-25", "26-32", "33-38", "39-42"])
    br = pick.groupby("band", observed=True).apply(lambda x: pd.Series({
        "kick_len": (x.yardline_100 + SNAP_TO_KICK).mean(),
        "extra_kicks": len(x),
        "per_game": len(x) / n_tg,
        "was_punt%": 100 * x.play_type.eq("punt").mean(),
        "pts/kick": x.gain.mean(),
        "pts/season": x.gain.sum() / tsn,
        "bad%": 100 * x.gain.lt(0).mean()}), include_groups=False)
    print(br.round(2).to_string())
    print(f"\n  the money is between the 33 and the 42 - a 51 to 60 yard kick.")
    print(f"  That band alone is {br.loc[['33-38', '39-42'], 'pts/season'].sum():.1f} "
          f"of the {pick.gain.sum() / tsn:.1f} points, on "
          f"{br.loc[['33-38', '39-42'], 'per_game'].sum():.2f} attempts a game,")
    print(f"  and {br.loc[['33-38', '39-42'], 'was_punt%'].mean():.0f}% of those "
          f"snaps were punts. Inside the 25 the rule actively costs points:")
    print(f"  a guaranteed 3 is worth less than a shot at 7 when you are already")
    print(f"  expected to score.")

    sub("the cost of keeping it simple")
    print(f"  best simple rule (4th & 4+)        : {r.wins.max():.2f} wins")
    print(f"  deciding every fourth down on expected points: 0.94 wins")
    print(f"  the gap is the {100 * pick.gain.lt(0).mean():.0f}% of rule-driven "
          f"kicks that were")
    print(f"  the wrong call - mostly short fields where a touchdown was live.")

    sub("one extra clause fixes most of that: don't kick from inside the 25")
    for lo in [1, 20, 25, 30, 33]:
        sel = nokick[nokick.ydstogo.ge(4) & nokick.yardline_100.ge(lo)]
        pts = sel.gain.sum() / tsn
        tot = CH1 + pts + CH5
        lab = "any yard line" if lo == 1 else f"outside the {lo}"
        print(f"  4th & 4+, {lab:16}: {len(sel) / n_tg:.2f} extra att/game, "
              f"{pts:5.1f} pts, {SLOPE * tot:.2f} wins "
              f"({100 * sel.gain.lt(0).mean():.0f}% bad kicks)")

    # ------------------------------------------------------- 4. the verdict
    hdr("4. WHERE THAT LEAVES THE 1.01")
    best = r.loc[r.wins.idxmax()]
    print(f"  the rule that maximises his value is 4th & "
          f"{best['kick if togo >=']:.0f} or longer: {best['wins']:.2f} wins")
    print(f"  the first overall pick has returned {QB_MEAN:+.2f} wins a season "
          f"on average, {QB_MEDIAN:+.2f} median")
    for lab, target in [("mean", QB_MEAN), ("median", QB_MEDIAN)]:
        need = target / SLOPE - (CH1 + CH5)
        print(f"\n  to match the {lab}: {target / SLOPE:.0f} points a season, so "
              f"{need:.1f} from new kicks")
        ok = r[r.ch3_pts >= need]
        if len(ok):
            print(f"    reachable at 4th & "
                  f"{ok.iloc[0]['kick if togo >=']:.0f}+")
        else:
            print(f"    no rule gets there. The most any threshold produces is "
                  f"{r.ch3_pts.max():.1f} points,")
            print(f"    at 4th & "
                  f"{r.loc[r.ch3_pts.idxmax(), 'kick if togo >=']:.0f}+, and "
                  f"pushing further makes it worse, not better.")
    print(f"\n  and every row above assumes the coach follows the rule every time.")
    print(f"  Real coaches handed an elite leg add {OBSERVED_RESPONSE:+.2f} attempts")
    print(f"  a game (OPPORTUNITY.txt). At that much extra kicking he is worth "
          f"about")
    small = r.iloc[(r["extra_att/gm"] - OBSERVED_RESPONSE).abs().argsort()].iloc[0]
    print(f"  {small['wins']:.2f} wins, the 4th & "
          f"{small['kick if togo >=']:.0f}+ row.")

    return r, tab


if __name__ == "__main__":
    main()
