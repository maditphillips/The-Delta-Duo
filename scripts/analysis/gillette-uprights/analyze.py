"""Did the Patriots' "yellow uprights" video-board trick actually make
opposing kickers miss at Gillette Stadium?

Run fetch_kicks.py first. Then: python3 analyze.py > FINDINGS.txt

Design
------
Baseline: a logistic model of make probability on a spline in kick distance
plus season fixed effects, FIT ONLY ON KICKS OUTSIDE GILLETTE, so Gillette
kicks are scored against the rest of the league rather than against
themselves. Blocked kicks are dropped from the primary sample because a
block is a line-of-scrimmage failure, not an aiming failure; block rates are
reported separately.

The claim implies a specific fingerprint, not just "visitors kick worse
here". Sections A-K test that fingerprint: lateral (not short) misses, a
consistent left/right bias, an onset tied to the video boards, a
disappearance once the alleged operator left, and an effect on extra points
from the same spot.
"""
import os, re, warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 60)

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kicks_2002_2025.parquet")
GILLETTE = "BOS00"
ERAS = {
    "Full Gillette era 2002-2025": range(2002, 2026),
    "Last decade 2016-2025":       range(2016, 2026),
    "Belichick era 2002-2023":     range(2002, 2024),
    "Post-Belichick 2024-2025":    range(2024, 2026),
}


def hdr(t):
    print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)


def load():
    d = pd.read_parquet(SRC)
    d["gillette"] = d.stadium_id.eq(GILLETTE)
    d["is_home_kick"] = d.posteam.eq(d.home_team)
    return d


def build(d):
    fg = d[d.field_goal_attempt.eq(1) & d.field_goal_result.notna()
           & d.kick_distance.between(15, 75)].copy()
    fg["made"] = fg.field_goal_result.eq("made").astype(int)
    nb = fg[fg.field_goal_result.ne("blocked")].copy()
    model = smf.glm("made ~ bs(kick_distance, df=5) + C(season)",
                    data=nb[~nb.gillette], family=sm.families.Binomial()).fit()
    nb["xmake"] = model.predict(nb)
    return fg, nb, model


def oe(s):
    """(n, actual rate, actual-minus-expected, z) for a set of kicks."""
    if len(s) == 0:
        return 0, np.nan, np.nan, np.nan
    var = (s.xmake * (1 - s.xmake)).sum()
    z = (s.made.sum() - s.xmake.sum()) / np.sqrt(var) if var > 0 else np.nan
    return len(s), s.made.mean(), s.made.mean() - s.xmake.mean(), z


def line(s, label):
    n, act, diff, z = oe(s)
    p = 2 * (1 - stats.norm.cdf(abs(z))) if n else np.nan
    print(f"{label:<44} n={n:>5}  act={act:6.2%}  exp={act-diff:6.2%}  "
          f"diff={diff:+6.2%}  ({s.made.sum()-s.xmake.sum():+6.1f} kicks)  z={z:+5.2f}  p={p:.3f}")


def main():
    d = load()
    fg, F, model = build(d)

    hdr("0. SAMPLE")
    g = F[F.gillette]
    print(f"FG attempts 2002-2025: {len(fg):,} (blocked {fg.field_goal_result.eq('blocked').sum():,})")
    print(f"Non-blocked primary sample: {len(F):,}")
    print(f"At Gillette: {len(g):,} kicks in {g.game_id.nunique()} games | "
          f"NE {g.is_home_kick.sum()} | visitors {(~g.is_home_kick).sum()}")
    print(f"Baseline fit on {(~F.gillette).sum():,} non-Gillette kicks")
    v = F[~F.is_home_kick]
    print(f"Distance check - visitors at Gillette avg {v[v.gillette].kick_distance.mean():.1f} yds "
          f"vs {v[~v.gillette].kick_distance.mean():.1f} elsewhere")

    hdr("1. VISITING KICKERS AT GILLETTE (distance + season adjusted)")
    for name, yrs in ERAS.items():
        line(F[F.gillette & ~F.is_home_kick & F.season.isin(yrs)], name)

    hdr("2. NEW ENGLAND'S OWN KICKERS AT GILLETTE (same yardstick)")
    for name, yrs in ERAS.items():
        line(F[F.gillette & F.is_home_kick & F.season.isin(yrs)], name)

    hdr("3. HOME-vs-VISITOR GAP: GILLETTE vs THE REST OF THE NFL")
    for name, yrs in ERAS.items():
        sub = F[F.season.isin(yrs)]
        print(f"\n{name}")
        for lab, part in [("Gillette", sub[sub.gillette]), ("Rest NFL", sub[~sub.gillette])]:
            h, a = part[part.is_home_kick], part[~part.is_home_kick]
            hd, ad = h.made.mean() - h.xmake.mean(), a.made.mean() - a.xmake.mean()
            print(f"  {lab:<9}: home {h.made.mean():.1%} (adj {hd:+.1%})  "
                  f"visitor {a.made.mean():.1%} (adj {ad:+.1%})  gap adj {hd-ad:+.1%}")

    hdr("4. VISITOR PENALTY BY VENUE, 2002-2025 (>=200 visiting-kicker FGs)")
    rows = []
    for _, sub in F.groupby("stadium_id"):
        a = sub[~sub.is_home_kick]
        if len(a) < 200:
            continue
        rows.append(dict(stadium=sub.stadium.mode().iat[0][:28], team=sub.home_team.mode().iat[0],
                         roof=sub.roof.mode().iat[0], n=len(a), act=a.made.mean(),
                         exp=a.xmake.mean(), diff=a.made.mean() - a.xmake.mean(), z=oe(a)[3]))
    tab = pd.DataFrame(rows).sort_values("diff")
    show = tab.copy()
    for c, f in [("act", "{:.1%}"), ("exp", "{:.1%}"), ("diff", "{:+.1%}"), ("z", "{:+.2f}")]:
        show[c] = show[c].map(f.format)
    print(show.to_string(index=False))
    print(f"\nGillette rank: {list(tab.team).index('NE')+1} of {len(tab)} (1 = hardest on visitors)")

    hdr("5. WITHIN-KICKER: same visiting kicker, Gillette vs his own season elsewhere")
    pairs = []
    for (_, szn), sub in F[~F.is_home_kick].groupby(["kicker_player_id", "season"]):
        gi, el = sub[sub.gillette], sub[~sub.gillette]
        if len(gi) == 0 or len(el) < 10:
            continue
        pairs.append(dict(season=szn, w=len(gi),
                          delta=(gi.made - gi.xmake).mean() - (el.made - el.xmake).mean()))
    P = pd.DataFrame(pairs)
    for name, yrs in ERAS.items():
        q = P[P.season.isin(yrs)]
        rep = np.repeat(q.delta.values, q.w.values)
        print(f"{name:<44} {len(q):>4} kicker-seasons, {q.w.sum():>4} kicks | "
              f"Gillette minus own-elsewhere {np.average(q.delta, weights=q.w):+.2%}  "
              f"p={stats.ttest_1samp(rep, 0).pvalue:.3f}")

    hdr("6. PLACEBO: EXTRA POINTS (33-yd era, 2015-2025) - same uprights, same board")
    xp = d[d.extra_point_attempt.eq(1) & d.extra_point_result.isin(["good", "failed"])
           & d.season.ge(2015)].copy()
    xp["made"] = xp.extra_point_result.eq("good").astype(int)
    lg = xp[~xp.gillette].made.mean()
    for lab, s in [("Visiting kickers at Gillette", xp[xp.gillette & ~xp.is_home_kick]),
                   ("Patriots kickers at Gillette", xp[xp.gillette & xp.is_home_kick])]:
        p = stats.binomtest(int(s.made.sum()), len(s), lg).pvalue
        print(f"{lab:<32} n={len(s):>4}  {s.made.mean():.2%}  vs league elsewhere {lg:.2%}  "
              f"diff {s.made.mean()-lg:+.2%}  p={p:.3f}")

    hdr("7. HOW DID THEY MISS?  illusion => lateral error; wind/cold => short")
    miss = F[F.made.eq(0)].copy()
    tail = miss.desc.str.extract(r"No Good,\s*([^.]*?),\s*(?:Center|Holder)", flags=re.I)[0].fillna("")
    miss["wl"] = tail.str.contains("Wide Left", case=False)
    miss["wr"] = tail.str.contains("Wide Right", case=False)
    miss["short"] = tail.str.contains("Short", case=False)
    miss["wide"] = miss.wl | miss.wr
    c = miss[tail.str.len().gt(0)]
    print(f"direction coded for {len(c):,} of {len(miss):,} misses\n")
    for lab, s in [("Gillette - visiting kickers", c[c.gillette & ~c.is_home_kick]),
                   ("Gillette - Patriots kickers", c[c.gillette & c.is_home_kick]),
                   ("Other stadiums - visitors", c[~c.gillette & ~c.is_home_kick]),
                   ("Other stadiums - home", c[~c.gillette & c.is_home_kick])]:
        w = s[s.wide]
        print(f"{lab:<30} n={len(s):>4}  wide-only {(s.wide & ~s.short).mean():6.1%}  "
              f"short-involved {s.short.mean():6.1%}  |  wide misses {w.wl.mean():5.1%}L / {w.wr.mean():5.1%}R")
    gv, ov = c[c.gillette & ~c.is_home_kick], c[~c.gillette & ~c.is_home_kick]
    ct = [[((gv.wide) & ~gv.short).sum(), (~((gv.wide) & ~gv.short)).sum()],
          [((ov.wide) & ~ov.short).sum(), (~((ov.wide) & ~ov.short)).sum()]]
    print(f"\nwide-only share, Gillette visitors vs visitors elsewhere: chi2 p={stats.chi2_contingency(ct)[1]:.3f}")
    w = gv[gv.wide]
    print(f"left/right split of Gillette visitor wide misses: {w.wl.sum()}L / {w.wr.sum()}R  "
          f"(binomial p={stats.binomtest(int(w.wl.sum()), len(w), 0.5).pvalue:.3f})")

    hdr("8. WEATHER CONTROLS")
    W = F.copy()
    W["wind"] = pd.to_numeric(W.wind, errors="coerce")
    W["temp"] = pd.to_numeric(W.temp, errors="coerce")
    W = W.dropna(subset=["wind", "temp"])
    W = W[W.wind.between(0, 40) & W.temp.between(-10, 110)]
    W["visitor"] = (~W.is_home_kick).astype(int)
    W["G"] = W.gillette.astype(int)
    print(f"sample {len(W):,} kicks ({W.G.sum()} at Gillette) | wind {W[W.G==1].wind.mean():.1f} vs "
          f"{W[W.G==0].wind.mean():.1f} mph | temp {W[W.G==1].temp.mean():.0f}F vs {W[W.G==0].temp.mean():.0f}F")
    specs = [("distance + season only", "made ~ bs(kick_distance,df=5)+C(season)+G+G:visitor+visitor"),
             ("+ wind + temp", "made ~ bs(kick_distance,df=5)+C(season)+wind+temp+G+G:visitor+visitor"),
             ("+ wind + temp + week", "made ~ bs(kick_distance,df=5)+C(season)+wind+temp+C(week)+G+G:visitor+visitor"),
             ("per-yard distance FE + wx", "made ~ C(kick_distance)+C(season)+wind+temp+G+G:visitor+visitor")]
    for lab, f in specs:
        r = smf.glm(f, data=W, family=sm.families.Binomial()).fit(
            cov_type="cluster", cov_kwds={"groups": W.game_id})
        b = r.params["G"] + r.params["G:visitor"]
        se = np.sqrt(r.cov_params().loc[["G", "G:visitor"], ["G", "G:visitor"]].values.sum())
        p = 2 * (1 - stats.norm.cdf(abs(b / se)))
        print(f"  {lab:<26} NE-at-home b={r.params['G']:+.3f} (p={r.pvalues['G']:.2f})   "
              f"VISITOR-at-Gillette b={b:+.3f} se={se:.3f} p={p:.3f}")

    hdr("9. TIMING - does the effect track the video boards or Belichick?")
    v = F[F.gillette & ~F.is_home_kick]
    for lo, hi, lab in [(2002, 2009, "2002-09  original scoreboards"),
                        (2010, 2022, "2010-22  HD video boards"),
                        (2023, 2025, "2023-25  new giant board")]:
        n, a, dd, z = oe(v[v.season.between(lo, hi)])
        print(f"  {lab:<32} n={n:>4}  act {a:6.1%}  diff {dd:+6.1%}  z={z:+.2f}")
    ss = v.groupby("season").apply(lambda s: s.made.mean() - s.xmake.mean())
    cnt = v.groupby("season").size()
    print("\n  season by season (pp vs expected, n):")
    print("   " + "  ".join(f"{i}:{x*100:+.0f}({cnt[i]})" for i, x in ss.items()))
    print(f"  seasons below expectation: {(ss < 0).sum()} of {len(ss)}")

    hdr("10. CONDITIONS SPLIT (visiting kickers at Gillette)")
    vv = v.copy()
    vv["t"] = pd.to_numeric(vv.temp, errors="coerce")
    vv["w"] = pd.to_numeric(vv.wind, errors="coerce")
    for lab, s in [("Weeks 1-8", vv[vv.week.le(8)]), ("Weeks 9+ / playoffs", vv[vv.week.gt(8)]),
                   ("Warm (>=50F)", vv[vv.t.ge(50)]), ("Cold (<50F)", vv[vv.t.lt(50)]),
                   ("Calm (<10 mph)", vv[vv.w.lt(10)]), ("Windy (>=10 mph)", vv[vv.w.ge(10)])]:
        n, a, dd, z = oe(s)
        print(f"  {lab:<24} n={n:>3}  act {a:6.1%}  diff {dd:+6.1%}  z={z:+.2f}")

    hdr("11. DISTANCE BUCKETS (visiting kickers)")
    for lo, hi in [(15, 29), (30, 39), (40, 49), (50, 75)]:
        s = v[v.kick_distance.between(lo, hi)]
        e = F[~F.gillette & ~F.is_home_kick & F.kick_distance.between(lo, hi)]
        print(f"  {lo}-{hi} yds: Gillette n={len(s):>3} {s.made.mean():6.1%} "
              f"({s.made.mean()-s.xmake.mean():+.1%} vs exp) | elsewhere {e.made.mean():.1%}")

    hdr("12. FAMILIARITY - do repeat visitors adapt?")
    v2 = v.sort_values(["kicker_player_id", "season", "week"]).copy()
    v2["trip"] = v2.groupby("kicker_player_id")["game_id"].transform(lambda s: pd.factorize(s)[0] + 1)
    for lab, s in [("1st career trip", v2[v2.trip.eq(1)]), ("2nd-3rd trip", v2[v2.trip.between(2, 3)]),
                   ("4th+ trip", v2[v2.trip.ge(4)])]:
        n, a, dd, z = oe(s)
        print(f"  {lab:<20} n={n:>3}  act {a:6.1%}  diff {dd:+6.1%}  z={z:+.2f}")

    hdr("13. BLOCK RATES (excluded from the primary sample)")
    A = fg.assign(blk=fg.field_goal_result.eq("blocked").astype(int))
    for lab, s in [("Visitors at Gillette", A[A.gillette & ~A.is_home_kick]),
                   ("Patriots at Gillette", A[A.gillette & A.is_home_kick]),
                   ("Visitors elsewhere", A[~A.gillette & ~A.is_home_kick])]:
        print(f"  {lab:<24} n={len(s):>5}  blocked {s.blk.mean():.2%}")

    hdr("14. NE'S OWN KICKERS, HOME vs ROAD")
    ne = F[F.posteam.eq("NE")]
    for lab, s in [("NE at Gillette", ne[ne.gillette]), ("NE everywhere else", ne[~ne.gillette])]:
        n, a, dd, _ = oe(s)
        print(f"  {lab:<24} n={n:>4}  act {a:6.2%}  diff {dd:+6.2%}")
    lg2 = F[~F.posteam.eq("NE")]
    print(f"  league home {oe(lg2[lg2.is_home_kick])[2]:+.2%} vs league road {oe(lg2[~lg2.is_home_kick])[2]:+.2%}")

    hdr("15. MULTIPLE COMPARISONS - 29 venues were searched")
    rows = []
    for _, sub in F.groupby("stadium_id"):
        h, a = sub[sub.is_home_kick], sub[~sub.is_home_kick]
        if len(h) < 200 or len(a) < 200:
            continue
        rows.append(dict(team=sub.home_team.mode().iat[0], z_visitor=oe(a)[3],
                         z_gap=(oe(h)[3] - oe(a)[3]) / np.sqrt(2)))
    T = pd.DataFrame(rows)
    k = len(T)
    for col, lab in [("z_visitor", "visiting-kicker penalty"), ("z_gap", "home-minus-visitor gap")]:
        z = T.loc[T.team == "NE", col].iat[0]
        raw = stats.norm.sf(abs(z)) * 2
        rank = int(T[col].rank(ascending=(col == "z_visitor")).loc[T.team == "NE"].iat[0])
        print(f"  {lab:<26} NE z={z:+.2f}  rank {rank}/{k}  raw p={raw:.4f}  "
              f"Bonferroni p={min(1, raw*k):.3f}  "
              f"{'SURVIVES' if raw*k < 0.05 else 'does NOT survive'}")

    hdr("16. VENUE-LEVEL PERMUTATION - does ANY venue look this bad by chance?")
    elig = [s for s, x in F.groupby("stadium_id")
            if len(x[~x.is_home_kick]) >= 200 and len(x[x.is_home_kick]) >= 200]
    E = F[F.stadium_id.isin(elig)]
    games = E.groupby("game_id").agg(season=("season", "first"), stad=("stadium_id", "first"))
    obs = oe(E[E.gillette & ~E.is_home_kick])[3]
    rng = np.random.default_rng(11)
    mins = []
    for _ in range(2000):
        perm = games.groupby("season", group_keys=False).apply(
            lambda s: s.assign(pstad=rng.permutation(s.stad.values)))
        mp = E.game_id.map(perm.pstad)
        away = E[~E.is_home_kick]
        z = away.assign(ps=mp[~E.is_home_kick.values].values).groupby("ps").apply(
            lambda s: oe(s)[3] if len(s) >= 150 else np.nan)
        mins.append(np.nanmin(z))
    mins = np.array(mins)
    print(f"  observed worst-venue z (Gillette) = {obs:.2f}")
    print(f"  null 'worst of {len(elig)}' z: mean {mins.mean():.2f}, 5th pct {np.percentile(mins,5):.2f}")
    print(f"  p(some venue this bad by chance) = {(mins <= obs).mean():.4f}")

    hdr("17. THE RATIO THE POST IMPLIES")
    for lo, hi, lab in [(2002, 2025, "2002-2025"), (2016, 2025, "2016-2025")]:
        gil = F[F.gillette & F.season.between(lo, hi)]
        rest = F[~F.gillette & F.season.between(lo, hi)]
        n_, v_ = gil[gil.is_home_kick], gil[~gil.is_home_kick]
        lh, la = rest[rest.is_home_kick], rest[~rest.is_home_kick]
        print(f"  {lab}: NE {n_.made.mean():.1%} ({n_.made.sum()}/{len(n_)}) vs visitors "
              f"{v_.made.mean():.1%} ({v_.made.sum()}/{len(v_)})  ratio {n_.made.mean()/v_.made.mean():.3f}")
        print(f"  {' '*len(lab)}  league home {lh.made.mean():.1%} vs visitor {la.made.mean():.1%}  "
              f"ratio {lh.made.mean()/la.made.mean():.3f}")

    hdr("18. DID IT WIN GAMES?")
    gil = F[F.gillette]
    gm = gil.groupby("game_id").agg(season=("season", "first"), away=("away_team", "first"),
                                    margin=("result", "first"))
    vm = gil[~gil.is_home_kick].groupby("game_id").agg(att=("made", "size"), made=("made", "sum"),
                                                       xmake=("xmake", "sum"))
    gm = gm.join(vm).fillna(0)
    gm["missed"] = gm.att - gm.made
    excess = gm.xmake.sum() - gm.made.sum()
    flip = gm[(gm.margin > 0) & (gm.missed > 0) & (gm.margin <= 3 * gm.missed)]
    print(f"  NE at Gillette 2002-2025: {(gm.margin>0).sum()}-{(gm.margin<0).sum()} ({(gm.margin>0).mean():.1%})")
    print(f"  excess visitor misses: {excess:.1f} of {int(gm.missed.sum())} total ({excess/gm.missed.sum():.0%})")
    print(f"  NE wins a visitor make would have tied or flipped: {len(flip)}")
    print(f"  upper-bound wins attributable: {len(flip)} x {excess/gm.missed.sum():.2f} = "
          f"{len(flip)*excess/gm.missed.sum():.1f} over 24 seasons "
          f"(~{len(flip)*excess/gm.missed.sum()/24:.2f}/season)")
    print(f"  points-value framing: {excess*3/len(gm):.2f} pts/game -> ~{excess/len(gm)*0.115*8.7:.2f} wins per home season")
    print("\n  the flippable games:")
    print(flip.reset_index()[["game_id", "season", "away", "margin", "att", "missed"]].to_string(index=False))


if __name__ == "__main__":
    main()
