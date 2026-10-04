"""How many groups should round 1 (or rounds 1-2) be split into?

Usage: python3 choose_groups.py        # round 1
       python3 choose_groups.py 2      # rounds 1 and 2 pooled

Two views:
  1. Unsupervised (clustering on draft pick alone): elbow, silhouette, gap statistic.
     These only ask whether pick numbers bunch up; they ignore careers.
  2. Supervised (groups that best explain career outcome): for k = 1..4 contiguous pick
     groups, find the cut points that best fit the outcome, then score each k with BIC
     and with cross-validation (cut points re-chosen inside each training fold, so the
     search itself can't overfit the test players).
"""
import sys
import warnings
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.model_selection import KFold

warnings.filterwarnings("ignore")
rng = np.random.default_rng(0)

df = pd.read_csv("rbs.csv")
ROUNDS = int(sys.argv[1]) if len(sys.argv) > 1 else 1
K_MAX = 4 if ROUNDS == 1 else 5
df = df[(df.draft_round <= ROUNDS) & df.rookie_year.between(2000, 2020)].sort_values("draft_pick")
pick = df.draft_pick.to_numpy()
OUT = {"log yr-2+ PPR": np.log1p(df.y2_ppr.to_numpy()),
       "yr-2+ PPR per game": (df.y2_ppr / df.y2_games).to_numpy(),
       "any top-12 season": (df.y2_top12 > 0).astype(float).to_numpy(),
       "any top-24 season": (df.y2_top24 > 0).astype(float).to_numpy()}
MIN_SIZE = 6
print(f"Round 1{'-' + str(ROUNDS) if ROUNDS > 1 else ''} RBs 2000-2020: n = {len(df)}, "
      f"picks {pick.min():.0f}-{pick.max():.0f}\n")

# ---------- 1. unsupervised ----------
X = pick.reshape(-1, 1).astype(float)
print("1. Clustering on draft pick alone")
inertia = {}
for k in range(1, 7):
    km = KMeans(k, n_init=20, random_state=0).fit(X)
    inertia[k] = km.inertia_
    sil = silhouette_score(X, km.labels_) if k > 1 else np.nan
    # gap statistic: compare log(within-SS) to uniform reference data over the same range
    ref = [np.log(KMeans(k, n_init=5, random_state=b).fit(
        rng.uniform(X.min(), X.max(), X.shape)).inertia_) for b in range(50)]
    gap, sk = np.mean(ref) - np.log(km.inertia_), np.std(ref) * np.sqrt(1 + 1 / 50)
    inertia[k] = (km.inertia_, sil, gap, sk, sorted(int(c) for c in np.round(km.cluster_centers_.ravel())))
for k, (w, sil, gap, sk, c) in inertia.items():
    print(f"   k={k}: within-SS {w:8.0f}  silhouette {sil:5.2f}  gap {gap:5.2f} (se {sk:.2f})  centers {c}")
ks = sorted(inertia)
gap_pick = next((k for k in ks[:-1] if inertia[k][2] >= inertia[k + 1][2] - inertia[k + 1][3]), ks[-1])
print(f"   gap-statistic choice (first k with gap(k) >= gap(k+1) - se): k = {gap_pick}")
print("   Picks are spread evenly, so any 'clusters' here are just equal slices.\n")


# ---------- 2. supervised: best contiguous cut points ----------
def seg_cost(y, binary):
    """cost[i, j] = loss of one group holding sorted players i..j-1, fit by its mean."""
    n = len(y)
    c1 = np.concatenate([[0], np.cumsum(y)])
    c2 = np.concatenate([[0], np.cumsum(y ** 2)])
    cost = np.full((n + 1, n + 1), np.inf)
    for i in range(n):
        for j in range(i + MIN_SIZE, n + 1):
            m, s = j - i, c1[j] - c1[i]
            if binary:
                mu = np.clip(s / m, 0.02, 0.98)
                cost[i, j] = -(s * np.log(mu) + (m - s) * np.log(1 - mu))
            else:
                cost[i, j] = (c2[j] - c2[i]) - s * s / m
    return cost


def fit_cuts(p, y, k, binary):
    """Exact best split of players (sorted by pick) into k contiguous groups, by dynamic
    programming. Cuts fall between distinct pick values; each group needs MIN_SIZE players."""
    o = np.argsort(p, kind="stable")
    p, y = p[o], y[o]
    n = len(y)
    cost = seg_cost(y, binary)
    ok = np.r_[True, p[1:] != p[:-1], True]  # may a group start/end at index i?
    D = np.full((k + 1, n + 1), np.inf)
    B = np.zeros((k + 1, n + 1), dtype=int)
    D[0, 0] = 0
    for g in range(1, k + 1):
        for j in range(1, n + 1):
            if not ok[j]:
                continue
            cand = D[g - 1, :j] + cost[:j, j]
            cand[~ok[:j]] = np.inf
            i = int(np.argmin(cand))
            D[g, j], B[g, j] = cand[i], i
    if not np.isfinite(D[k, n]):
        return np.inf, None
    cuts, j = [], n
    for g in range(k, 0, -1):
        i = B[g, j]
        if g > 1:
            cuts.append((p[i - 1] + p[i]) / 2)
        j = i
    return D[k, n], tuple(sorted(cuts))


def loss_fn(y, yhat, binary):
    if binary:
        yh = np.clip(yhat, 0.02, 0.98)
        return -np.sum(y * np.log(yh) + (1 - y) * np.log(1 - yh))
    return np.sum((y - yhat) ** 2)


def predict(p_tr, y_tr, cuts, p_te):
    edges = list(cuts)
    g_tr, g_te = np.digitize(p_tr, edges), np.digitize(p_te, edges)
    means = np.array([y_tr[g_tr == j].mean() for j in range(len(edges) + 1)])
    return means[g_te]


rows = []
pick_all = pick
for oname, y in OUT.items():
    binary = oname.startswith("any ")
    # PPG is undefined for backs who never played after year 1; leave them out of that one
    keep = ~np.isnan(y)
    if (~keep).any():
        print(f"   ({oname}: {(~keep).sum()} backs with no games after year 1 left out)")
    pick, y = pick_all[keep], y[keep]
    n = len(y)
    for k in range(1, K_MAX + 1):
        loss, cuts = fit_cuts(pick, y, k, binary)
        n_par = k + (k - 1)  # group means + cut points
        if binary:
            bic = 2 * loss + n_par * np.log(n)
        else:
            bic = n * np.log(loss / n) + n_par * np.log(n)
        cv = []
        for rep in range(20):
            tot = 0.0
            for tr, te in KFold(5, shuffle=True, random_state=rep).split(pick):
                _, c = fit_cuts(pick[tr], y[tr], k, binary)
                if c is None:
                    tot = np.nan
                    break
                tot += loss_fn(y[te], predict(pick[tr], y[tr], c, pick[te]), binary)
            cv.append(tot / n)
        cv = np.array(cv)
        rows.append({"outcome": oname, "k": k, "best cuts (pick)": "none" if k == 1 else
                     ", ".join(f"{c:.1f}" for c in cuts), "BIC": bic, "CV loss": np.nanmean(cv),
                     "CV se": np.nanstd(cv)})

    # smooth alternative: straight line in log(pick), same CV folds
    lp = np.log(pick)
    cv = []
    for rep in range(20):
        tot = 0.0
        for tr, te in KFold(5, shuffle=True, random_state=rep).split(pick):
            b = np.polyfit(lp[tr], y[tr], 1)
            tot += loss_fn(y[te], np.polyval(b, lp[te]), binary)
        cv.append(tot / n)
    b = np.polyfit(lp, y, 1)
    full = loss_fn(y, np.polyval(b, lp), binary)
    bic = 2 * full + 2 * np.log(n) if binary else n * np.log(full / n) + 2 * np.log(n)
    rows.append({"outcome": oname, "k": "line", "best cuts (pick)": "log(pick), no groups",
                 "BIC": bic, "CV loss": np.mean(cv), "CV se": np.std(cv)})

pick = pick_all
res = pd.DataFrame(rows)
print("2. Groups chosen to explain career outcome (lower BIC / CV loss = better)")
print("   CV loss: squared error per player (PPR) or log-loss per player (top-12/24);")
print("   cut points re-optimized inside every training fold, 20x repeated 5-fold\n")
for oname in OUT:
    t = res[res.outcome == oname].drop(columns="outcome")
    best_bic = t.loc[t.BIC.idxmin(), "k"]
    best_cv = t.loc[t["CV loss"].idxmin(), "k"]
    print(f"   {oname}   (best BIC: k={best_bic}, best CV: k={best_cv})")
    print(t.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print()

# ---------- 3. rounds 1-2: where do picks 30-32 belong? ----------
if ROUNDS >= 2:
    df["ppg"] = df.y2_ppr / df.y2_games
    df["band"] = pd.cut(df.draft_pick, [0, 29, 32, 48, 64],
                        labels=["Picks 1-29", "Picks 30-32", "Picks 33-48", "Picks 49-64"])
    print("3. Picks 30-32 next to their neighbors")
    print(df.groupby("band", observed=True).agg(
        n=("ppg", "size"), ppg_mean=("ppg", "mean"), ppg_median=("ppg", "median"),
        total_ppr_median=("y2_ppr", "median"), top12=("y2_top12", lambda v: (v > 0).mean()),
        top24=("y2_top24", lambda v: (v > 0).mean()))
        .to_string(float_format=lambda x: f"{x:.2f}"))
    print()
    from scipy import stats
    a = df[df.band == "Picks 30-32"]
    for other in ("Picks 1-29", "Picks 33-48"):
        b = df[df.band == other]
        print(f"   30-32 vs {other}:  PPG p = {stats.ttest_ind(a.ppg.dropna(), b.ppg.dropna(), equal_var=False).pvalue:.2f}"
              f",  log total PPR p = {stats.ttest_ind(np.log1p(a.y2_ppr), np.log1p(b.y2_ppr), equal_var=False).pvalue:.2f}"
              f",  top-12 Fisher p = {stats.fisher_exact([[(a.y2_top12 > 0).sum(), (a.y2_top12 == 0).sum()], [(b.y2_top12 > 0).sum(), (b.y2_top12 == 0).sum()]])[1]:.2f}")
