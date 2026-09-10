"""When does a metric start to mean something?

Two views, both aimed at the same question:

1. SIGNAL SHARE / STABILISATION POINT. Treat each player-season as a group and
   split game-to-game variance into between-player (real differences in level)
   and within-player (game noise) with a one-way random-effects decomposition.
   With lambda = var_within / var_between, the reliability of a k-game sample is
   k / (k + lambda). So reliability at k=1 is the share of a single game's spread
   that is actually signal, and lambda is the number of games needed to reach 0.5.

   Caveat worth stating: this holds a player's true level fixed inside a season,
   so a genuine mid-season role change lands in the noise bucket. lambda is
   therefore an upper bound on games-to-stabilise, not a floor.

2. THE CUMULATIVE CURVE. Correlate the average of weeks 1..k against a fixed
   late-season target (weeks 10 onward). The target never changes as k grows, so
   the curve is a clean read on how fast information accumulates -- and it can be
   compared against the flat line of "what last season already told you."

Written to STABILITY.txt.
"""
import numpy as np
import pandas as pd
import common as C

MIN_GAMES_GROUP = 8
TARGET_FIRST_WEEK = 10
MIN_TARGET_GAMES = 5
# a game only counts toward a rate metric if it clears this denominator
GAME_MIN_DEN = {"QB": 15, "RB": 5, "WR": 2, "TE": 2}


def variance_split(df, value, group_cols=("player_id", "season")):
    d = df[[*group_cols, value]].dropna()
    d = d[np.isfinite(d[value])]
    g = d.groupby(list(group_cols))[value]
    n = g.size()
    keep = n[n >= 3].index
    d = d.set_index(list(group_cols)).loc[keep].reset_index()
    g = d.groupby(list(group_cols))[value]
    n, means = g.size(), g.mean()
    G, N = len(n), len(d)
    if G < 30 or N - G < 30:
        return None
    grand = d[value].mean()
    ssw = float(((d[value].values - d.set_index(list(group_cols)).index.map(means).values) ** 2).sum())
    msw = ssw / (N - G)
    ssb = float((n * (means - grand) ** 2).sum())
    msb = ssb / (G - 1)
    n0 = (N - (n ** 2).sum() / N) / (G - 1)
    var_between = (msb - msw) / n0
    if var_between <= 0:
        return None
    lam = msw / var_between
    return dict(groups=G, obs=N, lam=lam, rel1=1 / (1 + lam),
                g50=lam, g70=lam * (0.7 / 0.3))


def game_values(p_pos, pos):
    """Per-game value of every metric, so the variance split has something to chew on."""
    d = p_pos.copy()
    out = d[["player_id", "season", "week"]].copy()
    for name, num in C.VOLUME[pos]:
        out[name] = d[num]
    for name, col in C.SHARE[pos]:
        out[name] = d[col].replace([np.inf, -np.inf], np.nan)
    floor = GAME_MIN_DEN[pos]
    for name, num, den in C.RATE[pos]:
        v = np.where(d[den] >= floor, d[num] / d[den].replace(0, np.nan), np.nan)
        out[name] = v
    return out


def cumulative_curve(p_pos, pos, metrics, kmax=9):
    gate_min = C.W1_GATE[pos][1]
    tgt = C.aggregate(p_pos[p_pos.week >= TARGET_FIRST_WEEK], pos).add_prefix("t_")
    tgt = tgt[tgt.t_games >= MIN_TARGET_GAMES]
    w1 = C.aggregate(p_pos[p_pos.week == 1], pos)
    eligible = w1[w1[C._gate_name(pos)] >= gate_min].index
    tgt = tgt.loc[tgt.index.intersection(eligible)]

    prior = C.aggregate(p_pos, pos).add_prefix("p_").reset_index()
    prior["season"] = prior.season + 1
    prior = prior.set_index(["player_id", "season"])

    rows = []
    for k in range(1, kmax + 1):
        cum = C.aggregate(p_pos[p_pos.week <= k], pos).add_prefix("c_")
        d = tgt.join(cum, how="inner").join(prior, how="left")
        rec = dict(k=k, n=len(d))
        for m, kind in metrics:
            a, b = d["c_" + m], d["t_" + m]
            ok = a.notna() & b.notna() & np.isfinite(a) & np.isfinite(b)
            if kind in ("rate", "role"):
                ok &= d["t_den_" + m].fillna(0) >= C.RATE_MIN_DEN[pos]
            rec[m] = float(np.corrcoef(a[ok], b[ok])[0, 1]) if ok.sum() >= 40 else np.nan
            if k == 1:
                pa = d["p_" + m]
                ok2 = pa.notna() & b.notna() & np.isfinite(pa) & np.isfinite(b)
                if kind in ("rate", "role"):
                    ok2 &= d["t_den_" + m].fillna(0) >= C.RATE_MIN_DEN[pos]
                    ok2 &= d["p_den_" + m].fillna(0) >= C.RATE_MIN_DEN[pos]
                rec["prior_" + m] = (float(np.corrcoef(pa[ok2], b[ok2])[0, 1])
                                     if ok2.sum() >= 40 else np.nan)
        rows.append(rec)
    return pd.DataFrame(rows)


def main():
    weekly = C._derived(C.load_weekly())
    print("=" * 100)
    print("HOW FAST DOES A METRIC BECOME REAL?")
    print("=" * 100)

    keep = []
    for pos in ("QB", "RB", "WR", "TE"):
        p_pos = weekly[weekly.position == pos]
        metrics = C.metric_list(pos)
        # snap share only exists from 2013, so its variance split uses that window
        gv_all = game_values(p_pos, pos)
        gv_all = gv_all.merge(
            p_pos.groupby(["player_id", "season"]).size().rename("gp"),
            left_on=["player_id", "season"], right_index=True, how="left")
        gv = gv_all[gv_all.gp >= MIN_GAMES_GROUP]

        print(f"\n\n{'#'*100}\n## {pos}  signal share of one game, and games needed to stabilise"
              f"\n{'#'*100}")
        print(f"\n{'metric':<20}{'type':<8}{'plyr-szn':>9}{'games':>7}"
              f"{'signal share':>14}{'lambda':>8}{'g->0.5':>8}{'g->0.7':>8}")
        print("-" * 82)
        res = []
        for m, kind in metrics:
            sub = gv if m != "snap_pct" else gv[gv.season >= C.SNAP_FIRST]
            v = variance_split(sub, m)
            if v:
                res.append(dict(position=pos, metric=m, kind=kind, **v))
        for r in sorted(res, key=lambda r: (r["kind"], -r["rel1"])):
            print(f"{r['metric']:<20}{r['kind']:<8}{r['groups']:>9}{r['obs']:>7}"
                  f"{r['rel1']*100:>13.1f}%{r['lam']:>8.1f}{r['g50']:>8.1f}{r['g70']:>8.1f}")
        keep += res

        cur = cumulative_curve(p_pos, pos, metrics)
        show = [m for m, k in metrics]
        print(f"\n  cumulative weeks 1..k vs a fixed target of weeks {TARGET_FIRST_WEEK}+ "
              f"(r; last column is last season's full line on the same players)")
        print(f"    {'metric':<20}" + "".join(f"{('k='+str(k)):>7}" for k in cur.k)
              + f"{'| prior':>9}")
        for m in show:
            if cur[m].notna().sum() == 0:
                continue
            print(f"    {m:<20}" + "".join(f"{C.fmt(v, 2):>7}" for v in cur[m])
                  + f"{C.fmt(cur['prior_' + m].iloc[0], 2):>9}")
        print(f"    {'(n)':<20}" + "".join(f"{n:>7}" for n in cur.n))
        cur.assign(position=pos).to_csv(f"out_curve_{pos}.csv", index=False)

    pd.DataFrame(keep).to_csv("out_stability.csv", index=False)


if __name__ == "__main__":
    main()
