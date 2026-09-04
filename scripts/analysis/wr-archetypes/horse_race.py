"""Which season-N wide receiver metric actually predicts season N+1?

    python3 horse_race.py > HORSE_RACE.txt

Sample: every WR-season 2009-2024 with 6+ games and 40+ targets - a receiver
with a real role, the only kind anyone is choosing between in a draft room.
The outcome is season N+1: PPR points per game, and whether he finished top-24.
A receiver with no season N+1 line did not play; that is a fantasy outcome, not
missing data, so he stays in with 0 points per game and a censored finish.

Nothing here is scored in sample. Section 2 ranks metrics by leave-one-season-out
cross-validated R2, so a metric only counts as predictive if it helps on seasons
the model has never seen.
"""
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

from panel import build

warnings.filterwarnings("ignore")
pd.set_option("display.width", 220)

FEATURES = {
    # production
    "ppg": "PPR points per game",
    "finish": "positional finish",
    "pace_finish": "health-adjusted finish (per-game pace over a full slate)",
    "prev_ppg": "PPR points per game, season N-1",
    "best_prior_finish": "best finish in any earlier season",
    "prior_top24": "count of earlier top-24 seasons",
    # volume
    "tpg": "targets per game",
    "targets": "total targets",
    "target_share": "target share",
    "air_yards_share": "air yards share",
    "wopr": "WOPR (target + air-yards opportunity)",
    "adot": "average depth of target",
    # weekly shape
    "gini": "weekly-score Gini (spike concentration)",
    "top5_share": "share of season points from the 5 best games",
    "boom_rate": "share of games over 20 PPR",
    "quiet_rate": "share of games at or under 8 PPR",
    "week_cv": "week-to-week coefficient of variation",
    # efficiency
    "ypt": "yards per target",
    "ppr_per_target": "PPR points per target",
    "catch_pct": "catch rate",
    "yac_per_rec": "YAC per reception",
    "racr": "RACR (yards per air yard)",
    "fd_per_target": "first downs per target",
    "epa_per_target": "receiving EPA per target",
    "td_per_target": "touchdowns per target",
    # health and profile
    "games": "games played",
    "missed": "games missed",
    "exp": "years of experience",
    "age": "age",
    "draft_pick": "draft pick",
    # team context
    "mate_finish": "best finish among the other WRs on his team",
    "young_mate_finish": "best finish among his 1st/2nd-year teammates",
    "mate_exp": "experience of that teammate",
    "n_teams": "teams played for this season",
}

# Metrics whose *natural good direction* is downward. Used only to orient the
# reported correlations so "+" always means "predicts a better season N+1".
# NOTE: mate_finish / young_mate_finish are deliberately NOT in here. A low
# number means a strong teammate, which is bad for the receiver in question, so
# their good direction is upward like everything else outside this set.
LOWER_IS_BETTER = {"finish", "pace_finish", "best_prior_finish", "quiet_rate",
                   "missed", "age", "draft_pick", "exp", "week_cv", "gini",
                   "top5_share", "n_teams"}

BLOCKS = {
    "Production": ["ppg", "finish", "pace_finish", "prev_ppg", "best_prior_finish", "prior_top24"],
    "Volume": ["tpg", "targets", "target_share", "air_yards_share", "wopr", "adot"],
    "Weekly shape": ["gini", "top5_share", "boom_rate", "quiet_rate", "week_cv"],
    "Efficiency": ["ypt", "ppr_per_target", "catch_pct", "yac_per_rec", "racr",
                   "fd_per_target", "epa_per_target", "td_per_target"],
    "Health / profile": ["games", "missed", "exp", "age", "draft_pick"],
    "Team context": ["mate_finish", "mate_exp", "young_mate_finish", "n_teams"],
}

NO_PRIOR_FINISH = 200.0   # sentinel rank for "has never had a qualifying season"
UNDRAFTED = 300.0


def sample(df, min_games=6, min_targets=40, min_season=2009, with_next=True):
    """Receivers with a real role, and (by default) a season N+1 to judge them by.

    The usage bar is deliberately low: a receiver whose season collapsed is
    exactly the case archetypes B and C are about, and an 8-game/50-target
    screen quietly deletes them from the sample.

    2009 is a hard floor. nflverse carries no target or air-yards data for
    2003-2008, so every volume and efficiency metric is missing there; 2000-2002
    have it but sit on the far side of that hole. The panel itself still runs
    from 2000, so career history (best prior finish, earlier top-24 seasons) is
    right for players whose careers started before the sample does.
    """
    s = df[(df.season >= min_season) & (df.games >= min_games) & (df.targets >= min_targets)]
    s = (s[s.has_next] if with_next else s).copy()
    for c in FEATURES:
        s[c] = s[c].astype(float).replace([np.inf, -np.inf], np.nan)
    s["no_prior"] = (s.prior_seasons == 0).astype(float)
    s["undrafted"] = s.draft_pick.isna().astype(float)
    s["draft_pick"] = s.draft_pick.fillna(UNDRAFTED)
    s["best_prior_finish"] = s.best_prior_finish.fillna(NO_PRIOR_FINISH)
    s["prev_ppg"] = s.prev_ppg.fillna(0.0)
    s["mate_finish"] = s.mate_finish.fillna(NO_PRIOR_FINISH)
    s["young_mate_finish"] = s.young_mate_finish.fillna(NO_PRIOR_FINISH)
    s["mate_exp"] = s.mate_exp.fillna(s.mate_exp.median())
    for c in FEATURES:
        s[c] = s[c].fillna(s[c].median())
    return s


def auc(score, label):
    """P(a random top-24 season scores above a random non-top-24 one)."""
    ok = score.notna() & label.notna()
    x, y = score[ok].to_numpy(), label[ok].astype(bool).to_numpy()
    if y.sum() == 0 or (~y).sum() == 0:
        return np.nan
    r = stats.rankdata(x)
    n1, n0 = y.sum(), (~y).sum()
    return (r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def loso_r2(s, cols, y="next_ppg_c"):
    """Leave-one-season-out R2. Standardisation and fit use training seasons only."""
    yv = s[y].to_numpy(dtype=float)
    X = s[cols].to_numpy(dtype=float) if cols else np.zeros((len(s), 0))
    seasons = s.season.to_numpy()
    pred = np.full(len(s), np.nan)
    for yr in np.unique(seasons):
        tr, te = seasons != yr, seasons == yr
        mu, sd = X[tr].mean(0), X[tr].std(0)
        sd = np.where(sd == 0, 1.0, sd)
        Xtr = np.c_[np.ones(tr.sum()), (X[tr] - mu) / sd]
        Xte = np.c_[np.ones(te.sum()), (X[te] - mu) / sd]
        beta, *_ = np.linalg.lstsq(Xtr, yv[tr], rcond=None)
        pred[te] = Xte @ beta
    ss_res = ((yv - pred) ** 2).sum()
    ss_tot = ((yv - yv.mean()) ** 2).sum()
    return 1 - ss_res / ss_tot, pred


def forward_select(s, cands, min_gain=0.002, max_k=10, report=None):
    """Greedily add whichever metric most improves leave-one-season-out R2."""
    chosen, best = [], 0.0
    while len(chosen) < max_k:
        r2, c = max((loso_r2(s, chosen + [c])[0], c) for c in cands if c not in chosen)
        if r2 - best < min_gain:
            if report:
                report(None, c, r2, r2 - best)
            break
        chosen.append(c)
        if report:
            report(len(chosen), c, r2, r2 - best)
        best = r2
    return chosen, best


def rule(title, char="="):
    print("\n" + char * 78)
    print(title)
    print(char * 78)


def main():
    df = build()
    s = sample(df)
    cands = [c for c in FEATURES if c in s.columns]

    rule("THE SAMPLE")
    print(f"WR-seasons, {int(s.season.min())}-{int(s.season.max())}, 6+ games and 40+ targets: {len(s):,}")
    print(f"Distinct receivers: {s.player_id.nunique():,}")
    print(f"{s.next_finish.isna().sum():,} of them ({100 * s.next_finish.isna().mean():.1f}%) "
          f"never played another qualifying WR season and are censored at the bottom.")
    print(f"Median season N+1 finish: WR{s.next_finish_c.median():.0f}   "
          f"top-24 rate: {100 * s.next_top24.mean():.1f}%   "
          f"top-12 rate: {100 * s.next_top12.mean():.1f}%")

    # ---------------------------------------------------------------- 1 -----
    rule("1. ONE METRIC AT A TIME")
    print("Spearman rho against season N+1 finish, oriented so + always means")
    print("'the good direction of this metric predicts a better season N+1'.")
    print("AUC = P(a top-24 season out-ranks a non-top-24 one) on this metric alone.")
    print("cv R2 = leave-one-season-out R2 on next-year points per game, this")
    print("metric and nothing else.\n")
    rows = []
    for f in cands:
        v = s[f]
        rho, p = stats.spearmanr(v, s.next_finish_c)
        flip = 1.0 if f in LOWER_IS_BETTER else -1.0
        r2, _ = loso_r2(s, [f])
        rows.append((f, FEATURES[f], flip * rho, auc(flip * -v, s.next_top24), r2, p))
    out = pd.DataFrame(rows, columns=["metric", "meaning", "signal", "auc", "cv_r2", "p"])
    out = out.sort_values("cv_r2", ascending=False)
    print(out.to_string(index=False, formatters={
        "signal": "{:+.3f}".format, "auc": "{:.3f}".format,
        "cv_r2": "{:.4f}".format, "p": "{:.1e}".format}))

    # ---------------------------------------------------------------- 2 -----
    rule("2. THE HORSE RACE: forward selection, out of sample")
    print("Greedily add the metric that most improves leave-one-season-out R2.")
    print("A metric enters only if it earns its place on seasons the model has")
    print("never seen, which is the only definition of predictive power that")
    print("survives 33 correlated candidates.\n")
    print(f"{'step':>4}  {'metric':<18} {'cv R2':>8} {'gain':>8}  meaning")

    def report(step, metric, r2, gain):
        if step is None:
            print(f"\n  stopped: the best remaining metric ({metric}) adds only {gain:+.4f}")
        else:
            print(f"{step:>4}  {metric:<18} {r2:>8.4f} {gain:>+8.4f}  {FEATURES[metric]}")

    chosen, best = forward_select(s, cands, report=report)
    r2_all, pred_all = loso_r2(s, cands)
    print(f"\n  all {len(cands)} metrics together: cv R2 = {r2_all:.4f}")
    print(f"  the {len(chosen)} selected:            cv R2 = {best:.4f}")
    _, pred_sel = loso_r2(s, chosen)
    rho_sel = stats.spearmanr(pred_sel, s.next_finish_c).statistic
    a_sel = auc(pd.Series(pred_sel, index=s.index), s.next_top24)
    print(f"  selected model vs actual season N+1 finish: Spearman rho = {rho_sel:.3f}, "
          f"AUC(top-24) = {a_sel:.3f}")

    # ---------------------------------------------------------------- 3 -----
    rule("3. WHAT EACH FAMILY OF METRICS IS WORTH")
    print("Leave-one-season-out R2 for each block on its own, and the R2 lost")
    print(f"when that block is dropped from the model that holds all {len(cands)}.\n")
    brows = []
    for name, cols in BLOCKS.items():
        cols = [c for c in cols if c in cands]
        alone, _ = loso_r2(s, cols)
        rest = [c for c in cands if c not in cols]
        without, _ = loso_r2(s, rest)
        brows.append((name, len(cols), alone, r2_all - without))
    bd = pd.DataFrame(brows, columns=["block", "k", "alone_cv_r2", "adds_on_top"])
    print(bd.sort_values("adds_on_top", ascending=False).to_string(
        index=False, formatters={"alone_cv_r2": "{:.4f}".format, "adds_on_top": "{:+.4f}".format}))

    # ---------------------------------------------------------------- 4 -----
    rule("4. THE THREE QUESTIONS THE ARCHETYPES TURN ON")

    print("\n(a) Spike concentration - archetype A, the five-week wonder.")
    print("    Holding season-N points per game, targets per game and games played")
    print("    fixed, does a season built out of a few huge weeks predict a worse")
    print("    next year?  Coefficient is next-season ppg per sd, season FE, HC3.")
    print("    The second block repeats it on near-full seasons only, where a")
    print("    'top 5 games' share means the same thing for everyone.\n")
    for label, sub in [("the whole sample", s), ("14+ games only", s[s.games >= 14])]:
        print(f"    {label}  (n = {len(sub):,})")
        for shape in ["gini", "top5_share", "boom_rate", "quiet_rate", "week_cv"]:
            cols = ["ppg", "tpg", "games", shape]
            zz = pd.DataFrame({k: (sub[k] - sub[k].mean()) / sub[k].std(ddof=0) for k in cols})
            XX = pd.concat([zz, pd.get_dummies(sub.season, prefix="yr", drop_first=True).astype(float)], axis=1)
            f2 = sm.OLS(sub.next_ppg_c.to_numpy(float), sm.add_constant(XX)).fit(cov_type="HC3")
            print(f"      {shape:<12} {f2.params[shape]:+.3f} ppg/sd   t = {f2.tvalues[shape]:+.2f}"
                  f"   p = {f2.pvalues[shape]:.3f}")
        print()

    print("\n(b) Health adjustment - archetype C, the injured efficient one.")
    print("    Which rank tells you more about next year: what he actually")
    print("    finished, or what his per-game pace says he would have finished?\n")
    for cols in ([["finish"], ["pace_finish"], ["ppg"], ["finish", "pace_finish"],
                  ["ppg", "finish"], ["ppg", "pace_finish"],
                  ["finish", "pace_finish", "missed"], ["ppg", "pace_finish", "missed"]]):
        r2c, _ = loso_r2(s, cols)
        print(f"    {' + '.join(cols):<34} cv R2 = {r2c:.4f}")

    print("\n(c) Does an earlier big season survive a bad one? - archetype B.")
    print("    Receivers coming off a season N finish outside the top 30:\n")
    bad = s[(s.finish > 30) & (s.prior_seasons >= 1)]
    for label, sel in [("an earlier top-12 season", bad.prior_top12 > 0),
                       ("an earlier top-24 but no top-12", (bad.prior_top12 == 0) & (bad.prior_top24 > 0)),
                       ("no earlier top-24 season", bad.prior_top24 == 0)]:
        g = bad[sel]
        print(f"    {label:<34} n = {len(g):>4}   median next WR{g.next_finish_c.median():>5.0f}"
              f"   top-24 {100 * g.next_top24.mean():>5.1f}%   top-12 {100 * g.next_top12.mean():>5.1f}%")

    print("\n(d) The young teammate - archetype C's complication.")
    print("    Among receivers who finished top-30, what does a 1st/2nd-year")
    print("    teammate finishing ahead of a given line do to their next season?\n")
    good = s[s.finish <= 30]
    ym = good.young_mate_finish
    for cut in (24, 36, 60):
        hit, miss = good[ym <= cut], good[~(ym <= cut)]
        u = stats.mannwhitneyu(hit.next_ppg_c, miss.next_ppg_c)
        print(f"    young teammate inside WR{cut:<3}  n = {len(hit):>4}  median next "
              f"WR{hit.next_finish_c.median():>5.0f}  top-24 {100 * hit.next_top24.mean():>5.1f}%"
              f"  next ppg {hit.next_ppg_c.mean():>5.2f}")
        print(f"    no such teammate           n = {len(miss):>4}  median next "
              f"WR{miss.next_finish_c.median():>5.0f}  top-24 {100 * miss.next_top24.mean():>5.1f}%"
              f"  next ppg {miss.next_ppg_c.mean():>5.2f}    Mann-Whitney p = {u.pvalue:.3f}\n")

    print("\n(e) Efficiency without volume.")
    print("    Among receivers at the same targets per game, does elite efficiency")
    print("    predict a better next season?  Terciles of PPR per target, within")
    print("    quartiles of targets per game.\n")
    q = pd.qcut(s.tpg, 4, labels=["tpg Q1", "tpg Q2", "tpg Q3", "tpg Q4"])
    t = s.groupby(q, observed=True).apply(
        lambda g: g.assign(eff=pd.qcut(g.ppr_per_target, 3, labels=["low", "mid", "high"]))
        .groupby("eff", observed=True).next_ppg_c.mean(), include_groups=False)
    print(t.to_string(float_format="{:.2f}".format))


if __name__ == "__main__":
    main()
