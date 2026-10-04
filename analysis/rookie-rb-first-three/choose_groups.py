"""How many groups should round 1 be split into?

Two views:
  1. Unsupervised (clustering on draft pick alone): elbow, silhouette, gap statistic.
     These only ask whether pick numbers bunch up; they ignore careers.
  2. Supervised (groups that best explain career outcome): for k = 1..4 contiguous pick
     groups, find the cut points that best fit the outcome, then score each k with BIC
     and with cross-validation (cut points re-chosen inside each training fold, so the
     search itself can't overfit the test players).
"""
import itertools
import warnings
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.model_selection import KFold

warnings.filterwarnings("ignore")
rng = np.random.default_rng(0)

df = pd.read_csv("rbs.csv")
df = df[(df.draft_round == 1) & df.rookie_year.between(2000, 2020)].sort_values("draft_pick")
pick = df.draft_pick.to_numpy()
OUT = {"log yr-2+ PPR": np.log1p(df.y2_ppr.to_numpy()),
       "yr-2+ PPR per game": (df.y2_ppr / df.y2_games).to_numpy(),
       "any top-12 season": (df.y2_top12 > 0).astype(float).to_numpy(),
       "any top-24 season": (df.y2_top24 > 0).astype(float).to_numpy()}
MIN_SIZE = 6
print(f"First-round RBs 2000-2020: n = {len(df)}\n")

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
print("   Picks are spread evenly 1-32, so any 'clusters' here are just equal slices.\n")


# ---------- 2. supervised: best contiguous cut points ----------
def fit_cuts(p, y, k, binary):
    """Exhaustive search for k contiguous pick groups minimizing SSE / log-loss.
    Cuts fall between distinct pick values; each group needs MIN_SIZE players."""
    vals = np.unique(p)
    cands = (vals[:-1] + vals[1:]) / 2
    best = (np.inf, None)
    for cuts in itertools.combinations(cands, k - 1):
        edges = [-np.inf, *cuts, np.inf]
        g = np.digitize(p, edges[1:-1])
        sizes = np.bincount(g, minlength=k)
        if sizes.min() < MIN_SIZE:
            continue
        means = np.array([y[g == j].mean() for j in range(k)])
        loss = loss_fn(y, means[g], binary)
        if loss < best[0]:
            best = (loss, cuts)
    return best


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
for oname, y in OUT.items():
    binary = oname.startswith("any ")
    n = len(y)
    for k in range(1, 5):
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
