"""Does the favoured effect survive the obvious confounds?

His team's average line jumps from about even in Tennessee to +6 in Baltimore,
so "favoured" and "Ravens, with Lamar Jackson holding the edge defender" are
badly tangled. Three checks: split by era, split by quarterback, and a
within-season check so team quality cannot carry the result.
"""
import numpy as np
import pandas as pd

import common

pd.set_option("display.width", 200)

g, r = common.load()
reg = r[r.season_type == "REG"]
h = reg[reg.rusher_player_id == common.HENRY].copy()
h["era"] = np.where(h.season >= 2024, "Baltimore 2024-26", "Tennessee 2016-23")


def split(df, key):
    t = df[df.favored != "Pick'em"].groupby([key, "favored"], observed=True).apply(
        common.rates, include_groups=False)
    return t[["att", "ypc", "epa", "success", "td_rate", "exp10"]].round(3)


print("=" * 88)
print("ROBUSTNESS: IS 'FAVOURED' JUST STANDING IN FOR 'BALTIMORE'?")
print("=" * 88)

print("\n### 1. By era\n")
t = split(h, "era")
print(t.to_string())
for era in t.index.get_level_values(0).unique():
    sub = t.loc[era]
    if {"Favored", "Underdog"} <= set(sub.index):
        print(f"  {era}: favoured minus underdog = "
              f"{sub.loc['Favored','ypc'] - sub.loc['Underdog','ypc']:+.2f} YPC, "
              f"{sub.loc['Favored','epa'] - sub.loc['Underdog','epa']:+.3f} EPA")

print("\n### 2. Within season: paired favoured-vs-underdog gap, season by season\n")
rows = []
for (season,), d in h.groupby(["season"]):
    f = d[d.favored == "Favored"]
    u = d[d.favored == "Underdog"]
    if len(f) >= 40 and len(u) >= 40:
        rows.append({"season": season, "team": d.posteam.mode().iat[0],
                     "fav att": len(f), "fav YPC": round(f.yards_gained.mean(), 2),
                     "dog att": len(u), "dog YPC": round(u.yards_gained.mean(), 2),
                     "gap": round(f.yards_gained.mean() - u.yards_gained.mean(), 2)})
w = pd.DataFrame(rows)
print(w.to_string(index=False))
pos = (w.gap > 0).sum()
print(f"\n  positive in {pos} of {len(w)} seasons with both samples; "
      f"median gap {w.gap.median():+.2f} YPC, mean {w.gap.mean():+.2f}")

print("\n### 3. Tennessee only, excluding Baltimore entirely\n")
ten = h[h.era == "Tennessee 2016-23"]
print(split(ten, "tier").to_string())

print("\n### 4. Baltimore only\n")
bal = h[h.era == "Baltimore 2024-26"]
print(split(bal, "tier").to_string())

# Does the gap hold when the QB is not Lamar? Approximate by era, which is exact
# here: Henry never played with Jackson outside Baltimore.
print("\n### 5. The same era split for every other RB, as the control\n")
lg = reg[reg.rusher_player_id.isin(common.rb_ids())
         & (reg.rusher_player_id != common.HENRY)].copy()
lg["era"] = np.where(lg.season >= 2024, "2024-26", "2016-23")
t = split(lg, "era")
print(t[["att", "ypc", "epa"]].to_string())
for era in t.index.get_level_values(0).unique():
    sub = t.loc[era]
    print(f"  peer RBs {era}: favoured minus underdog = "
          f"{sub.loc['Favored','ypc'] - sub.loc['Underdog','ypc']:+.2f} YPC")

print("\n### 6. Sample-size reality check on the biggest claim\n")
for lab, mask in [("Fav 7+", h.tier == "Fav 7+"),
                  ("up 9+ and favoured",
                   (h.favored == "Favored") & (h.score_differential >= 9))]:
    d = h[mask]
    n_g = d.game_id.nunique()
    bal_share = (d.season >= 2024).mean()
    # bootstrap the mean so the number carries its own error bar
    boot = [d.yards_gained.sample(len(d), replace=True).mean() for _ in range(2000)]
    lo, hi = np.percentile(boot, [2.5, 97.5])
    print(f"  {lab:<22} {len(d):>4} carries, {n_g:>3} games, "
          f"{100*bal_share:>3.0f}% Baltimore, "
          f"YPC {d.yards_gained.mean():.2f}  95% CI [{lo:.2f}, {hi:.2f}]")
