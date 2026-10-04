"""Are a rookie RB's first three games predictive of his career?

Cohort: RBs who debuted 2000-2020 and played 3+ games as rookies (5+ later seasons
observed through 2025). Outcomes are measured from year 2 on so they never overlap
the games used to predict them. Prints every table; writes report_data.json.
"""
import json
import warnings
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import r2_score, roc_auc_score
from sklearn.model_selection import KFold, StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")
pd.set_option("display.width", 200)
OUT = {}

raw = pd.read_csv("rbs.csv")
df = raw[raw.rookie_year.between(2000, 2020)].copy()
print(f"Cohort: {len(df)} rookie RBs, 2000-2020 debuts, 3+ rookie games\n")

# ---------- derived columns ----------
for d in (df, raw):
    d["pick"] = d.draft_pick.fillna(260)
    d["log_pick"] = np.log(d.pick)
    d["log_y2_ppr"] = np.log1p(d.y2_ppr)
    d["any_top24"] = (d.y2_top24 > 0).astype(int)
    d["any_top12"] = (d.y2_top12 > 0).astype(int)
    # Efficiency on 10-20 carries is mostly noise. For modeling, shrink each rate toward
    # the cohort mean with a prior worth K carries, so a 3-carry 9.0 YPC doesn't dominate.
    for pre, n_col in (("f3", "f3_carries"), ("rk", "rk_carries")):
        for m, K in (("ypc", 30), ("rush_epa_pc", 30), ("rush_sr", 30), ("rush_1d_rate", 30)):
            mu = df[f"{pre}_{m}"].mean()
            n = d[n_col]
            d[f"{pre}_{m}_s"] = (d[f"{pre}_{m}"].fillna(mu) * n + mu * K) / (n + K)

print("Base rates (year 2+):")
print(f"  any top-24 PPR RB season: {df.any_top24.mean():.1%}   any top-12: {df.any_top12.mean():.1%}")
print(f"  median year-2+ PPR points: {df.y2_ppr.median():.0f}   mean: {df.y2_ppr.mean():.0f}\n")
OUT["n"] = len(df)
OUT["base_top24"] = df.any_top24.mean()
OUT["base_top12"] = df.any_top12.mean()

# ---------- A. raw and draft-adjusted correlations ----------
F3 = {
    "f3_carries_pg": "Carries / game", "f3_carry_share": "Carry share", "f3_rec_pg": "Receptions / game",
    "f3_rec_share": "Reception share", "f3_target_share": "Target share", "f3_snap_share": "Snap share",
    "f3_touches_pg": "Touches / game", "f3_ypc": "Yards / carry", "f3_rush_epa_pc": "Rush EPA / carry",
    "f3_rush_sr": "Rush success rate", "f3_rush_1d_rate": "1st downs / carry", "f3_yds_per_tgt": "Yards / target",
    "f3_scrim_ypg": "Scrimmage yds / game", "f3_ppr_pg": "PPR pts / game",
}
KIND = {k: "usage" for k in ["f3_carries_pg", "f3_carry_share", "f3_rec_pg", "f3_rec_share",
                             "f3_target_share", "f3_snap_share", "f3_touches_pg"]}
KIND.update({k: "efficiency" for k in ["f3_ypc", "f3_rush_epa_pc", "f3_rush_sr", "f3_rush_1d_rate",
                                       "f3_yds_per_tgt"]})
KIND.update({"f3_scrim_ypg": "production", "f3_ppr_pg": "production"})


def resid_rank(y, X):
    """Rank-transform, then residualize on draft capital + age (partial Spearman)."""
    yr = stats.rankdata(y)
    Xr = np.column_stack([stats.rankdata(X[:, j]) for j in range(X.shape[1])] + [np.ones(len(y))])
    beta, *_ = np.linalg.lstsq(Xr, yr, rcond=None)
    return yr - Xr @ beta


rows = []
for col, label in F3.items():
    # efficiency needs some volume to mean anything
    vol = {"f3_yds_per_tgt": ("f3_targets", 4)}.get(col, ("f3_carries", 10))
    sub = df.dropna(subset=[col])
    if KIND[col] == "efficiency":
        sub = sub[sub[vol[0]] >= vol[1]]
    for out in ("log_y2_ppr", "any_top24", "y2_games"):
        r, p = stats.spearmanr(sub[col], sub[out])
        X = sub[["log_pick", "undrafted", "age"]].to_numpy()
        pr, pp = stats.pearsonr(resid_rank(sub[col].to_numpy(), X), resid_rank(sub[out].to_numpy(), X))
        rows.append({"metric": label, "kind": KIND[col], "outcome": out, "n": len(sub),
                     "rho": r, "p": p, "partial_rho": pr, "partial_p": pp})
corr = pd.DataFrame(rows)
print("A. Spearman correlation of first-3-game metric with career outcome (year 2+)")
print("   partial = after removing draft pick, undrafted flag and age")
print("   efficiency metrics: only backs with 10+ carries (4+ targets for yds/target)\n")
piv = corr[corr.outcome == "log_y2_ppr"][["metric", "kind", "n", "rho", "p", "partial_rho", "partial_p"]]
print(piv.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
print()
OUT["corr"] = corr.to_dict("records")

# draft capital alone, for reference
r_draft, _ = stats.spearmanr(-df.pick, df.log_y2_ppr)
print(f"   reference: draft pick vs year-2+ PPR, rho = {r_draft:.3f}\n")
OUT["rho_draft"] = r_draft

# ---------- B. cross-validated incremental value ----------
DRAFT = ["log_pick", "undrafted", "age"]
F3_USAGE = ["f3_carries_pg", "f3_carry_share", "f3_rec_pg", "f3_rec_share"]
F3_EFF = ["f3_ypc_s", "f3_rush_epa_pc_s", "f3_rush_sr_s", "f3_rush_1d_rate_s"]
F3_PROD = ["f3_ppr_pg"]
RK_USAGE = [c.replace("f3_", "rk_") for c in F3_USAGE]
RK_EFF = [c.replace("f3_", "rk_") for c in F3_EFF]
SETS = {
    "Draft capital + age": DRAFT,
    "First 3 games only": F3_USAGE + F3_EFF + F3_PROD,
    "Draft + first-3 usage": DRAFT + F3_USAGE,
    "Draft + first-3 efficiency": DRAFT + F3_EFF,
    "Draft + first 3 games (all)": DRAFT + F3_USAGE + F3_EFF + F3_PROD,
    "Draft + full rookie season": DRAFT + RK_USAGE + RK_EFF + ["rk_ppr_pg", "rk_games"],
    "Draft + full rookie + first 3": DRAFT + RK_USAGE + RK_EFF + ["rk_ppr_pg", "rk_games"]
                                     + F3_USAGE + F3_EFF + F3_PROD,
}
REPS, FOLDS = 20, 10


def cv_reg(cols, y, model=None):
    X = df[cols].to_numpy()
    scores = []
    for rep in range(REPS):
        pred = np.zeros(len(y))
        for tr, te in KFold(FOLDS, shuffle=True, random_state=rep).split(X):
            m = model() if model else make_pipeline(StandardScaler(), LinearRegression())
            m.fit(X[tr], y[tr])
            pred[te] = m.predict(X[te])
        scores.append(r2_score(y, pred))
    return np.array(scores)


def cv_clf(cols, y):
    X = df[cols].to_numpy()
    scores = []
    for rep in range(REPS):
        pred = np.zeros(len(y))
        for tr, te in StratifiedKFold(FOLDS, shuffle=True, random_state=rep).split(X, y):
            m = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000))
            m.fit(X[tr], y[tr])
            pred[te] = m.predict_proba(X[te])[:, 1]
        scores.append(roc_auc_score(y, pred))
    return np.array(scores)


y_ppr = df.log_y2_ppr.to_numpy()
y_t24 = df.any_top24.to_numpy()
y_t12 = df.any_top12.to_numpy()
res = []
base = {}
for name, cols in SETS.items():
    r2 = cv_reg(cols, y_ppr)
    a24 = cv_clf(cols, y_t24)
    a12 = cv_clf(cols, y_t12)
    if name == "Draft capital + age":
        base = {"r2": r2, "a24": a24, "a12": a12}
    res.append({"model": name, "k": len(cols),
                "cv_r2": r2.mean(), "d_r2": (r2 - base["r2"]).mean(),
                "d_r2_lo": np.percentile(r2 - base["r2"], 5),
                "auc_top24": a24.mean(), "d_auc24": (a24 - base["a24"]).mean(),
                "auc_top12": a12.mean(), "d_auc12": (a12 - base["a12"]).mean()})
res = pd.DataFrame(res)
print(f"B. Out-of-sample fit, {REPS}x repeated {FOLDS}-fold CV (linear / logistic)")
print("   cv_r2: log(1 + year-2+ PPR points);  auc: had any top-24 / top-12 season in year 2+")
print("   d_*: gain over draft capital alone (same folds)\n")
print(res.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
OUT["models"] = res.to_dict("records")

gb = cv_reg(DRAFT + F3_USAGE + F3_EFF + F3_PROD, y_ppr,
            lambda: HistGradientBoostingRegressor(max_depth=3, learning_rate=0.05, max_iter=200,
                                                  min_samples_leaf=20))
print(f"\n   gradient boosting, draft + first 3: cv_r2 = {gb.mean():.3f} (nonlinearity check)\n")
OUT["gbm_r2"] = gb.mean()

# full-sample coefficients for the combined model (standardized)
cols = DRAFT + F3_USAGE + F3_EFF + F3_PROD
X = StandardScaler().fit_transform(df[cols])
import statsmodels.api as sm
ols = sm.OLS(y_ppr, sm.add_constant(X)).fit()
coef = pd.DataFrame({"feature": cols, "std_coef": ols.params[1:], "p": ols.pvalues[1:]})
print("   standardized OLS coefficients, draft + first 3 (correlated inputs; read with care)")
print(coef.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
print()

# ---------- C. stability: does the same metric hold up for the rest of the career? ----------
STAB = [("carries_pg", "Carries / game", None), ("carry_share", "Carry share", None),
        ("rec_pg", "Receptions / game", None), ("target_share", "Target share", None),
        ("ypc", "Yards / carry", 10), ("rush_epa_pc", "Rush EPA / carry", 10),
        ("rush_sr", "Rush success rate", 10), ("ppr_pg", "PPR pts / game", None)]
srows = []
for m, label, minc in STAB:
    sub = df.dropna(subset=[f"f3_{m}", f"after_{m}"])
    sub = sub[sub.after_carries >= 50]
    if minc:
        sub = sub[sub.f3_carries >= minc]
    r, _ = stats.pearsonr(sub[f"f3_{m}"], sub[f"after_{m}"])
    rr, _ = stats.pearsonr(sub[f"rk_{m}"], sub[f"after_{m}"]) if m != "rec_pg" or True else (np.nan, 0)
    srows.append({"metric": label, "n": len(sub), "r_first3_vs_rest": r, "r_rookieyr_vs_rest": rr})
stab = pd.DataFrame(srows)
print("C. Stability: first-3-game value vs the same metric over the rest of the career")
print("   (backs with 50+ later carries; efficiency needs 10+ first-3 carries)")
print("   r_rookieyr_vs_rest uses the full rookie season for comparison (it overlaps the outcome")
print("   window only in the first 3 games, so treat it as an upper bound)\n")
print(stab.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
print()
OUT["stability"] = stab.to_dict("records")

# ---------- D. practical tables: hit rate by tier ----------
df["tier"] = pd.cut(df.pick, [0, 32, 96, 259, 261], labels=["Rd 1", "Rd 2-3", "Rd 4-7", "UDFA"])
df["share_bin"] = pd.cut(df.f3_carry_share, [-0.01, 0.15, 0.35, 1.01],
                         labels=["<15%", "15-35%", "35%+"])
tab = df.groupby(["tier", "share_bin"], observed=True).agg(
    n=("any_top24", "size"), hit_top24=("any_top24", "mean"),
    med_y2_ppr=("y2_ppr", "median")).reset_index()
print("D. Hit rate (any top-24 season, year 2+) by draft tier x first-3 carry share\n")
print(tab.to_string(index=False, float_format=lambda x: f"{x:.2f}"))
print()
OUT["tier_share"] = tab.astype({"tier": str, "share_bin": str}).to_dict("records")

vol = df[df.f3_carries >= 15].copy()
vol["eff"] = np.where(vol.f3_rush_sr >= vol.f3_rush_sr.median(), "high SR", "low SR")
vol["dc"] = np.where(vol.pick <= 96, "Rd 1-3", "Rd 4+/UDFA")
tab2 = vol.groupby(["dc", "eff"]).agg(n=("any_top24", "size"), hit_top24=("any_top24", "mean"),
                                      med_y2_ppr=("y2_ppr", "median")).reset_index()
print(f"   Among backs with 15+ first-3 carries, split at median success rate ({vol.f3_rush_sr.median():.3f})\n")
print(tab2.to_string(index=False, float_format=lambda x: f"{x:.2f}"))
print()
OUT["tier_eff"] = tab2.to_dict("records")
OUT["sr_median"] = vol.f3_rush_sr.median()

# ---------- E. fit on full cohort, score 2021-2026 rookies ----------
fcols = DRAFT + F3_USAGE + F3_EFF + F3_PROD
clf = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000)).fit(df[fcols], y_t24)
clf0 = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000)).fit(df[DRAFT], y_t24)
new = raw[raw.rookie_year >= 2021].copy()
new["p_top24"] = clf.predict_proba(new[fcols])[:, 1]
new["p_top24_draft_only"] = clf0.predict_proba(new[DRAFT])[:, 1]
new["delta"] = new.p_top24 - new.p_top24_draft_only
show = new[new.rookie_year == 2026].sort_values("p_top24", ascending=False)
print("E. 2026 rookies: chance of a top-24 season in year 2+ (model fit on 2000-2020)\n")
print(show[["name", "team", "draft_pick", "f3_carries_pg", "f3_carry_share", "f3_rec_pg", "f3_ypc",
            "f3_rush_sr", "f3_ppr_pg", "p_top24_draft_only", "p_top24", "delta"]]
      .to_string(index=False, float_format=lambda x: f"{x:.2f}"))
OUT["rookies_2026"] = show[["name", "team", "draft_pick", "f3_carries_pg", "f3_carry_share", "f3_rec_pg",
                            "f3_ypc", "f3_rush_sr", "f3_ppr_pg", "p_top24_draft_only", "p_top24",
                            "delta"]].to_dict("records")

# 2021-2022 rookies have 3+ later seasons: did the model call them?
chk = new[new.rookie_year.between(2021, 2022)]
if chk.any_top24.nunique() > 1:
    print(f"\n   holdout check, 2021-22 rookies (n={len(chk)}): AUC draft-only "
          f"{roc_auc_score(chk.any_top24, chk.p_top24_draft_only):.3f}, "
          f"draft + first 3 {roc_auc_score(chk.any_top24, chk.p_top24):.3f}")
    OUT["holdout"] = {"n": len(chk),
                      "auc_draft": roc_auc_score(chk.any_top24, chk.p_top24_draft_only),
                      "auc_f3": roc_auc_score(chk.any_top24, chk.p_top24)}

json.dump(OUT, open("report_data.json", "w"), indent=1, default=float)
