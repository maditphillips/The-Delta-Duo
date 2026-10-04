"""First-round RBs only: do the first three games tell you anything, and does it differ
between early, middle and late first-round picks?

Same cohort rules and outcomes as analyze.py (2000-2020 debuts, outcomes from year 2 on).
With ~50 players every estimate here is noisy; bootstrap intervals are printed throughout.
"""
import warnings
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import r2_score, roc_auc_score
from sklearn.model_selection import KFold, StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")
pd.set_option("display.width", 200)
rng = np.random.default_rng(0)

raw = pd.read_csv("rbs.csv")
r1all = raw[raw.draft_round == 1].copy()
df = r1all[r1all.rookie_year.between(2000, 2020)].copy()
df["log_pick"] = np.log(df.draft_pick)
df["log_y2_ppr"] = np.log1p(df.y2_ppr)
df["y2_ppr_pg"] = df.y2_ppr / df.y2_games.where(df.y2_games > 0)
df["any_top24"] = (df.y2_top24 > 0).astype(int)
df["any_top12"] = (df.y2_top12 > 0).astype(int)
mu = df.f3_rush_sr.mean()
df["f3_rush_sr_s"] = (df.f3_rush_sr.fillna(mu) * df.f3_carries + mu * 30) / (df.f3_carries + 30)
mu = df.f3_ypc.mean()
df["f3_ypc_s"] = (df.f3_ypc.fillna(mu) * df.f3_carries + mu * 30) / (df.f3_carries + 30)

print(f"First-round RBs, 2000-2020 debuts, 3+ rookie games: n = {len(df)}")
print(f"  any top-24 season (yr 2+): {df.any_top24.mean():.0%}   any top-12: {df.any_top12.mean():.0%}"
      f"   median yr-2+ PPR: {df.y2_ppr.median():.0f}\n")

METRICS = {"f3_carry_share": "Carry share", "f3_carries_pg": "Carries / game",
           "f3_rec_pg": "Receptions / game", "f3_touches_pg": "Touches / game",
           "f3_ppr_pg": "PPR pts / game", "f3_scrim_ypg": "Scrimmage yds / game",
           "f3_ypc": "Yards / carry*", "f3_rush_epa_pc": "Rush EPA / carry*",
           "f3_rush_sr": "Rush success rate*"}
EFF = {"f3_ypc", "f3_rush_epa_pc", "f3_rush_sr"}
OUTCOMES = {"log_y2_ppr": "yr2+ PPR", "y2_ppr_pg": "yr2+ PPR/g", "y2_top12": "# top-12 yrs"}


def boot_rho(x, y, n=2000):
    idx = np.arange(len(x))
    bs = []
    for _ in range(n):
        s = rng.choice(idx, len(idx))
        if np.unique(x[s]).size > 2:
            bs.append(stats.spearmanr(x[s], y[s])[0])
    return np.nanpercentile(bs, [2.5, 97.5])


def corr_table(d, title):
    rows = []
    for col, lab in METRICS.items():
        sub = d.dropna(subset=[col])
        if col in EFF:
            sub = sub[sub.f3_carries >= 10]
        row = {"metric": lab, "n": len(sub)}
        for o, olab in OUTCOMES.items():
            s2 = sub.dropna(subset=[o])
            r, p = stats.spearmanr(s2[col], s2[o])
            row[olab] = r
            if o == "log_y2_ppr":
                lo, hi = boot_rho(s2[col].to_numpy(), s2[o].to_numpy())
                row["95% CI"] = f"[{lo:+.2f}, {hi:+.2f}]"
                row["p"] = p
        rows.append(row)
    t = pd.DataFrame(rows)
    print(title)
    print(t.to_string(index=False, float_format=lambda x: f"{x:+.2f}"))
    print()
    return t


# ---------- 1. all first-rounders ----------
corr_table(df, "1. Spearman rho, first-3 metric vs career (yr 2+), all first-rounders  "
               "(* = 10+ first-3 carries)")
r, p = stats.spearmanr(-df.draft_pick, df.log_y2_ppr)
print(f"   reference: pick number within round 1 vs yr-2+ PPR: rho = {r:+.2f} (p = {p:.2f})\n")

# ---------- 2. out-of-sample: does it beat pick + age? ----------
BASE = ["log_pick", "age"]
SETS = {"Pick + age": BASE,
        "Pick + age + carry share": BASE + ["f3_carry_share"],
        "Pick + age + PPR/g": BASE + ["f3_ppr_pg"],
        "Pick + age + touches/g": BASE + ["f3_touches_pg"],
        "Pick + age + success rate": BASE + ["f3_rush_sr_s"],
        "Pick + age + YPC": BASE + ["f3_ypc_s"],
        "Pick + age + share + PPR/g + SR": BASE + ["f3_carry_share", "f3_ppr_pg", "f3_rush_sr_s"]}
y = df.log_y2_ppr.to_numpy()
yc = df.any_top12.to_numpy()
rows = []
base_r2 = base_auc = None
for name, cols in SETS.items():
    X = df[cols].to_numpy()
    r2s, aucs = [], []
    for rep in range(50):
        pr = np.zeros(len(y))
        for tr, te in KFold(5, shuffle=True, random_state=rep).split(X):
            pr[te] = make_pipeline(StandardScaler(), LinearRegression()).fit(X[tr], y[tr]).predict(X[te])
        r2s.append(r2_score(y, pr))
        pc = np.zeros(len(y))
        for tr, te in StratifiedKFold(5, shuffle=True, random_state=rep).split(X, yc):
            m = make_pipeline(StandardScaler(), LogisticRegression(C=0.5, max_iter=2000))
            pc[te] = m.fit(X[tr], yc[tr]).predict_proba(X[te])[:, 1]
        aucs.append(roc_auc_score(yc, pc))
    r2s, aucs = np.array(r2s), np.array(aucs)
    if base_r2 is None:
        base_r2, base_auc = r2s, aucs
    rows.append({"model": name, "cv_r2": r2s.mean(), "d_r2": (r2s - base_r2).mean(),
                 "share_of_reps_better": (r2s > base_r2).mean() if name != "Pick + age" else np.nan,
                 "auc_top12": aucs.mean(), "d_auc": (aucs - base_auc).mean()})
print("2. Out-of-sample (50x repeated 5-fold CV). Outcome: log yr-2+ PPR; AUC: any top-12 season")
print(pd.DataFrame(rows).to_string(index=False, float_format=lambda x: f"{x:+.3f}"))
print()

# ---------- 3. groups within round 1 ----------
GROUPINGS = {
    "two groups": pd.cut(df.draft_pick, [0, 16, 32], labels=["Picks 1-16", "Picks 17-32"]),
    "three groups": pd.cut(df.draft_pick, [0, 10, 24, 32],
                           labels=["Picks 1-10", "Picks 11-24", "Picks 25-32"]),
}
for gname, g in GROUPINGS.items():
    df["grp"] = g
    print(f"3{'a' if gname == 'two groups' else 'b'}. Round 1 split into {gname}")
    summ = df.groupby("grp", observed=True).agg(
        n=("name", "size"), top24=("any_top24", "mean"), top12=("any_top12", "mean"),
        med_y2_ppr=("y2_ppr", "median"), f3_carry_share=("f3_carry_share", "median"),
        f3_ppr_pg=("f3_ppr_pg", "median"))
    print(summ.to_string(float_format=lambda x: f"{x:.2f}"))
    print()
    for lev in df.grp.cat.categories:
        corr_table(df[df.grp == lev], f"   {lev}: Spearman rho with career")

    # high vs low early usage within each group (split at the group's own median)
    out = []
    for lev in df.grp.cat.categories:
        s = df[df.grp == lev]
        for col, lab in (("f3_carry_share", "carry share"), ("f3_ppr_pg", "PPR/g")):
            hi = s[col] >= s[col].median()
            for flag, part in ((True, s[hi]), (False, s[~hi])):
                out.append({"group": lev, "split on": lab, "half": "high" if flag else "low",
                            "n": len(part), "median_f3": part[col].median(),
                            "top24": part.any_top24.mean(), "top12": part.any_top12.mean(),
                            "med_y2_ppr": part.y2_ppr.median(),
                            "busts (<300 yr2+ PPR)": (part.y2_ppr < 300).mean()})
    print(f"   High vs low half of first-3 usage, within each group ({gname})")
    print(pd.DataFrame(out).to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    print()

    # does the first-3 slope differ by group? (interaction test, plus permutation p)
    for col in ("f3_carry_share", "f3_ppr_pg"):
        d = df[["log_y2_ppr", col, "grp", "age"]].rename(columns={col: "x"})
        d["x"] = (d.x - d.x.mean()) / d.x.std()
        full = smf.ols("log_y2_ppr ~ x * C(grp) + age", d).fit()
        red = smf.ols("log_y2_ppr ~ x + C(grp) + age", d).fit()
        f_obs = full.compare_f_test(red)[0]
        perm = []
        for _ in range(2000):
            dp = d.copy()
            dp["x"] = dp.groupby("grp", observed=True).x.transform(lambda v: rng.permutation(v.values))
            # permute x within group, keeping group effects; refit both
            f2 = smf.ols("log_y2_ppr ~ x * C(grp) + age", dp).fit()
            r2 = smf.ols("log_y2_ppr ~ x + C(grp) + age", dp).fit()
            perm.append(f2.compare_f_test(r2)[0])
        slopes = {lev: smf.ols("log_y2_ppr ~ x + age", d[d.grp == lev]).fit().params["x"]
                  for lev in df.grp.cat.categories}
        print(f"   slope of log yr-2+ PPR on {col} (per 1 SD), by group: "
              + ", ".join(f"{k} {v:+.2f}" for k, v in slopes.items()))
        print(f"     do slopes differ? F-test p = {full.compare_f_test(red)[1]:.2f}, "
              f"permutation p = {(np.array(perm) >= f_obs).mean():.2f}")
    print()

# ---------- 4. who drives it: list ----------
df["grp"] = GROUPINGS["three groups"]
print("4. Every first-round RB, sorted by pick")
print(df.sort_values("draft_pick")[["name", "rookie_year", "draft_pick", "grp", "f3_carry_share",
                                    "f3_ppr_pg", "f3_rush_sr", "y2_ppr", "y2_top12", "y2_top24"]]
      .to_string(index=False, float_format=lambda x: f"{x:.2f}"))
print()
recent = r1all[r1all.rookie_year >= 2021].sort_values(["rookie_year", "draft_pick"])
print("   2021+ first-rounders (careers incomplete; not used above)")
print(recent[["name", "rookie_year", "draft_pick", "f3_carry_share", "f3_ppr_pg", "f3_rush_sr",
              "y2_ppr", "y2_top12", "y2_top24"]].to_string(index=False, float_format=lambda x: f"{x:.2f}"))
