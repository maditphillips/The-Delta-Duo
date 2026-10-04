"""Test the data-chosen round-1 split (picks 1-29 vs 30-32; nobody in the sample went 29th).

The cut came from searching every possible 2-group split, so a plain t-test is biased
toward significance. The search-adjusted permutation test repeats the full search on
every shuffled dataset and asks how often the *best* split of pure noise beats ours.
"""
import numpy as np
import pandas as pd
from scipy import stats

rng = np.random.default_rng(0)
N_PERM, MIN_SIZE = 20000, 6

df = pd.read_csv("rbs.csv")
df = df[(df.draft_round == 1) & df.rookie_year.between(2000, 2020)].sort_values("draft_pick")
df["ppg"] = df.y2_ppr / df.y2_games
df["log_ppr"] = np.log1p(df.y2_ppr)
df["top12"] = (df.y2_top12 > 0).astype(float)
df["top24"] = (df.y2_top24 > 0).astype(float)
pick = df.draft_pick.to_numpy()
late = pick >= 30
vals = np.unique(pick)
cuts = [c for c in (vals[:-1] + vals[1:]) / 2 if MIN_SIZE <= (pick < c).sum() <= len(pick) - MIN_SIZE]


def welch_t(Y, mask):
    """Vectorized Welch t (early minus late) for every row of Y."""
    a, b = Y[:, ~mask], Y[:, mask]
    va, vb = a.var(axis=1, ddof=1) / a.shape[1], b.var(axis=1, ddof=1) / b.shape[1]
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.nan_to_num((a.mean(axis=1) - b.mean(axis=1)) / np.sqrt(va + vb))


def tstat(y, mask):
    return stats.ttest_ind(y[~mask], y[mask], equal_var=False).statistic


print(f"Picks 1-29: n = {(~late).sum()}   Picks 30-32: n = {late.sum()}  "
      f"({', '.join(df.loc[late, 'name'])})\n")
rows = []
for col, lab in (("ppg", "PPR per game, yr 2+"), ("log_ppr", "total PPR, yr 2+ (log)"),
                 ("top12", "any top-12 season"), ("top24", "any top-24 season")):
    y = df[col].to_numpy()
    obs = tstat(y, late)
    naive_p = stats.ttest_ind(y[~late], y[late], equal_var=False).pvalue
    # search-adjusted: best |t| over all allowed cuts, on shuffled outcomes
    S = np.array([rng.permutation(y) for _ in range(N_PERM)])  # N_PERM x n, sorted by pick
    best = np.max([np.abs(welch_t(S, pick > c)) for c in cuts], axis=0)
    adj_p = (best >= abs(obs)).mean()
    show = (lambda v: f"{v:.0%}") if col.startswith("top") else \
           (lambda v: f"{np.expm1(v):.0f} (geo mean)") if col == "log_ppr" else (lambda v: f"{v:.1f}")
    rows.append({"outcome": lab, "picks 1-29": show(y[~late].mean()), "picks 30-32": show(y[late].mean()),
                 "naive p": naive_p, "search-adjusted p": adj_p})
print(pd.DataFrame(rows).to_string(index=False, float_format=lambda x: f"{x:.3f}"))

# where would the 30-32 group's PPG rank if pick didn't matter?
y = df.ppg.to_numpy()
print(f"\nPPG medians: picks 1-29 {np.median(y[~late]):.1f}, picks 30-32 {np.median(y[late]):.1f}")
print(f"Without the 30-32 group, picks 1-29 vs pick number: Spearman rho = "
      f"{stats.spearmanr(pick[~late], y[~late])[0]:+.2f} (p = {stats.spearmanr(pick[~late], y[~late])[1]:.2f})")
