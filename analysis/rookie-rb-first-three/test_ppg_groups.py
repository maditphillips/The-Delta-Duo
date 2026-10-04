"""Is the drop in year-2+ PPR per game across round-1 pick groups (1-10, 11-24, 25-32)
statistically significant, or noise?

Tests: one-way ANOVA (and Welch's version), Kruskal-Wallis (rank-based), a trend test
for an ordered decline, pairwise comparisons with Holm correction, and permutation
versions of each so nothing leans on normality. Bootstrap intervals for the gaps.
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.oneway import anova_oneway

rng = np.random.default_rng(0)
N_PERM = 20000

df = pd.read_csv("rbs.csv")
df = df[(df.draft_round == 1) & df.rookie_year.between(2000, 2020)].copy()
df["ppg"] = df.y2_ppr / df.y2_games
df["grp"] = pd.cut(df.draft_pick, [0, 10, 24, 32], labels=["1-10", "11-24", "25-32"])
df["rank_order"] = df.grp.cat.codes  # 0, 1, 2
G = list(df.grp.cat.categories)
groups = [df.loc[df.grp == g, "ppg"].to_numpy() for g in G]
y, code = df.ppg.to_numpy(), df.rank_order.to_numpy()

print("Year-2+ PPR per game, first-round RBs 2000-2020\n")
print(df.groupby("grp", observed=True).ppg.agg(n="size", mean="mean", median="median", sd="std")
      .to_string(float_format=lambda x: f"{x:.1f}"))
print()


def perm_p(stat_fn, observed, two_sided=False):
    sims = np.empty(N_PERM)
    for i in range(N_PERM):
        sims[i] = stat_fn(rng.permutation(y))
    if two_sided:
        return (np.abs(sims) >= abs(observed)).mean()
    return (sims >= observed).mean()


def f_stat(v):
    return stats.f_oneway(*[v[code == k] for k in range(3)]).statistic


def h_stat(v):
    return stats.kruskal(*[v[code == k] for k in range(3)]).statistic


def trend_stat(v):
    # slope of PPG on group order (0, 1, 2): negative = declines later in the round
    return np.polyfit(code, v, 1)[0]


rows = []
f = stats.f_oneway(*groups)
rows.append(("One-way ANOVA: any difference among the 3 groups", f.pvalue,
             perm_p(f_stat, f.statistic)))
w = anova_oneway(groups, use_var="unequal")
rows.append(("Welch ANOVA (unequal spread)", w.pvalue, np.nan))
k = stats.kruskal(*groups)
rows.append(("Kruskal-Wallis (ranks; robust to outliers)", k.pvalue, perm_p(h_stat, k.statistic)))
t = smf.ols("ppg ~ rank_order", df).fit()
slope = t.params["rank_order"]
rows.append((f"Trend: steady decline across groups ({slope:+.1f} PPG per group step)",
             t.pvalues["rank_order"] / 2 if slope < 0 else 1 - t.pvalues["rank_order"] / 2,
             (np.array([trend_stat(rng.permutation(y)) for _ in range(N_PERM)]) <= slope).mean()))
rho, p_rho = stats.spearmanr(df.draft_pick, df.ppg)
rows.append((f"Trend on raw pick number, Spearman rho {rho:+.2f} (two-sided)", p_rho, np.nan))

print("Tests (one-sided for the trend rows: is there a decline?)")
print(pd.DataFrame(rows, columns=["test", "p", "permutation p"])
      .to_string(index=False, float_format=lambda x: f"{x:.3f}"))
print()

# pairwise, Holm-corrected
pairs, praw, pperm, diffs, cis = [], [], [], [], []
for a, b in [(0, 1), (1, 2), (0, 2)]:
    xa, xb = groups[a], groups[b]
    d = xa.mean() - xb.mean()
    pr = stats.ttest_ind(xa, xb, equal_var=False).pvalue
    pooled = np.concatenate([xa, xb])
    sims = np.empty(N_PERM)
    for i in range(N_PERM):
        s = rng.permutation(pooled)
        sims[i] = s[:len(xa)].mean() - s[len(xa):].mean()
    pp = (np.abs(sims) >= abs(d)).mean()
    boot = [rng.choice(xa, len(xa)).mean() - rng.choice(xb, len(xb)).mean() for _ in range(N_PERM)]
    pairs.append(f"{G[a]} vs {G[b]}")
    praw.append(pr)
    pperm.append(pp)
    diffs.append(d)
    cis.append(np.percentile(boot, [2.5, 97.5]))
holm = multipletests(praw, method="holm")[1]
holm_perm = multipletests(pperm, method="holm")[1]
out = pd.DataFrame({"comparison": pairs, "gap (PPG)": diffs,
                    "95% CI": [f"[{lo:+.1f}, {hi:+.1f}]" for lo, hi in cis],
                    "Welch t p": praw, "Holm p": holm, "perm p": pperm, "Holm perm p": holm_perm})
print("Pairwise (two-sided). Holm adjusts for making 3 comparisons.")
print(out.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
print()

# effect size and power: how big a gap could this sample reliably detect?
eta2 = sm.stats.anova_lm(smf.ols("ppg ~ C(grp)", df).fit()).pipe(
    lambda a: a.loc["C(grp)", "sum_sq"] / a.sum_sq.sum())
sd = df.ppg.std()
n1, n3 = len(groups[0]), len(groups[2])
mde = (1.96 + 0.84) * sd * np.sqrt(1 / n1 + 1 / n3)
print(f"Share of PPG variation explained by group (eta^2): {eta2:.1%}")
print(f"Spread of PPG between players (sd): {sd:.1f}")
print(f"Smallest 1-10 vs 25-32 gap this sample detects 80% of the time (5% level): ~{mde:.1f} PPG")
