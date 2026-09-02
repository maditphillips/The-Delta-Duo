"""Lateral miss RATE (per attempt), not just the share of misses that are wide.

If the video board pushed opposing kickers sideways, the excess at Gillette
should be specifically lateral: visiting kickers should miss wide more often
per attempt than New England does, and more than the short-miss rate can
explain. Blocked kicks are excluded throughout.
"""
import re, warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, statsmodels.api as sm, statsmodels.formula.api as smf
from scipy import stats
pd.set_option("display.width", 210)

K = pd.read_parquet("kicks_2002_2025.parquet")
K["gillette"] = K.stadium_id.eq("BOS00")
K["is_home_kick"] = K.posteam.eq(K.home_team)
fg = K[K.field_goal_attempt.eq(1) & K.field_goal_result.notna()
       & K.kick_distance.between(15, 75) & K.field_goal_result.ne("blocked")].copy()
fg["made"] = fg.field_goal_result.eq("made").astype(int)

# classify EVERY attempt, not just the misses
tail = fg.desc.str.extract(r"No Good,\s*([^.]*?),\s*(?:Center|Holder)", flags=re.I)[0].fillna("")
fg["coded"] = tail.str.len().gt(0)
fg["wl"] = tail.str.contains("Wide Left", case=False)
fg["wr"] = tail.str.contains("Wide Right", case=False)
fg["anyWide"] = (fg.wl | fg.wr).astype(int)
fg["short"] = tail.str.contains("Short", case=False)
fg["wideOnly"] = ((fg.wl | fg.wr) & ~fg.short).astype(int)
fg["shortAny"] = fg.short.astype(int)
# a coded miss that is neither wide nor short (uprights, crossbar, etc.)
fg["otherMiss"] = (fg.made.eq(0) & fg.coded & ~(fg.wl | fg.wr) & ~fg.short).astype(int)
fg["wl"] = fg.wl.astype(int)
fg["wr"] = fg.wr.astype(int)
# a miss we could not classify — keep it visible rather than silently dropping it
fg["uncoded_miss"] = fg.made.eq(0) & ~fg.coded

def hdr(t): print("\n" + "=" * 84 + f"\n{t}\n" + "=" * 84)

hdr("0. CODING COVERAGE")
m = fg[fg.made.eq(0)]
print(f"misses {len(m):,}, direction coded {m.coded.mean():.1%}")
for lab, s in [("Gillette, visitors", fg[fg.gillette & ~fg.is_home_kick]),
               ("Gillette, Patriots", fg[fg.gillette & fg.is_home_kick])]:
    mm = s[s.made.eq(0)]
    print(f"  {lab:<22} attempts {len(s):>4}  misses {len(mm):>3}  coded {mm.coded.sum():>3} ({mm.coded.mean():.0%})")

GROUPS = [
    ("Gillette — visiting kickers", fg.gillette & ~fg.is_home_kick),
    ("Gillette — Patriots kickers", fg.gillette & fg.is_home_kick),
    ("All other stadiums — visitors", ~fg.gillette & ~fg.is_home_kick),
    ("All other stadiums — home", ~fg.gillette & fg.is_home_kick),
]

hdr("1. LATERAL MISS RATE PER ATTEMPT  (the question asked)")
print(f"  {'group':<32}{'att':>6}{'wide%':>9}{'wide-only%':>12}{'short%':>9}{'miss%':>8}")
res = {}
for lab, mask in GROUPS:
    s = fg[mask]
    res[lab] = s
    print(f"  {lab:<32}{len(s):>6}{s.anyWide.mean():>8.2%}{s.wideOnly.mean():>12.2%}"
          f"{s.shortAny.mean():>9.2%}{(1-s.made.mean()):>8.2%}")

g_v = res["Gillette — visiting kickers"]; g_h = res["Gillette — Patriots kickers"]
def prop_test(a, b, col, la, lb):
    ka, na = a[col].sum(), len(a); kb, nb = b[col].sum(), len(b)
    tab = [[ka, na - ka], [kb, nb - kb]]
    p = stats.fisher_exact(tab)[1]
    print(f"  {la} {a[col].mean():.2%} vs {lb} {b[col].mean():.2%}  "
          f"diff {a[col].mean()-b[col].mean():+.2%}  Fisher p={p:.4f}")

hdr("2. THE HEAD-TO-HEAD THE THEORY PREDICTS")
print("  If the board pushed visitors sideways, their LATERAL rate should exceed New England's")
print("  by more than their overall miss rate does.\n")
for col, lab in [("anyWide", "any wide miss"), ("wideOnly", "wide-only miss"), ("shortAny", "short miss")]:
    print(f"  {lab}:")
    prop_test(g_v, g_h, col, "visitors", "Patriots")
print("\n  overall miss rate:")
gv = g_v.assign(miss=1 - g_v.made); gh = g_h.assign(miss=1 - g_h.made)
prop_test(gv, gh, "miss", "visitors", "Patriots")

hdr("3. DECOMPOSING THE GILLETTE PENALTY: how much of the excess is lateral?")
o_v = res["All other stadiums — visitors"]
for col, lab in [("anyWide", "wide misses"), ("shortAny", "short misses")]:
    exc = (g_v[col].mean() - o_v[col].mean()) * len(g_v)
    print(f"  {lab:<16} Gillette visitors {g_v[col].mean():.2%} vs visitors elsewhere {o_v[col].mean():.2%}"
          f"   excess {exc:+.1f} kicks over {len(g_v)} attempts")
tot_exc = ((1 - g_v.made.mean()) - (1 - o_v.made.mean())) * len(g_v)
print(f"  {'total misses':<16} Gillette visitors {1-g_v.made.mean():.2%} vs elsewhere {1-o_v.made.mean():.2%}"
      f"   excess {tot_exc:+.1f} kicks")

hdr("4. DISTANCE-ADJUSTED LATERAL MISS RATE")
print("  P(wide miss) modelled on a distance spline + season, fit on NON-Gillette kicks.")
tr = fg[~fg.gillette]
for col, lab in [("anyWide", "any wide"), ("wideOnly", "wide only"), ("shortAny", "short")]:
    # cast to int first: patsy treats a boolean endog as categorical and the
    # GLM then models P(False), which silently inverts the whole comparison
    mdl = smf.glm(f"{col} ~ bs(kick_distance, df=5) + C(season)",
                  data=tr.assign(**{col: tr[col].astype(int)}),
                  family=sm.families.Binomial()).fit()
    fg[f"x_{col}"] = mdl.predict(fg)
    print(f"\n  {lab}:")
    for glab, gs in [("visitors at Gillette", g_v), ("Patriots at Gillette", g_h)]:
        s = fg.loc[gs.index]
        act, exp = s[col].mean(), s[f"x_{col}"].mean()
        var = (s[f"x_{col}"] * (1 - s[f"x_{col}"])).sum()
        z = (s[col].sum() - s[f"x_{col}"].sum()) / np.sqrt(var)
        print(f"    {glab:<24} n={len(s):>4}  act {act:6.2%}  exp {exp:6.2%}  "
              f"diff {act-exp:+6.2%}  z={z:+5.2f}  p={2*(1-stats.norm.cdf(abs(z))):.3f}")

hdr("5. LEFT vs RIGHT PER ATTEMPT  (an offset board should bias one way)")
for lab, mask in GROUPS:
    s = fg[mask]
    l, r = s.wl.sum(), s.wr.sum()
    p = stats.binomtest(int(l), int(l + r), 0.5).pvalue if (l + r) > 0 else np.nan
    print(f"  {lab:<32} left {s.wl.mean():.2%}  right {s.wr.mean():.2%}   "
          f"({int(l)}L/{int(r)}R, binomial p={p:.3f})")

hdr("6. RATIO TEST: is the Gillette excess disproportionately lateral?")
print("  wide misses as a share of ALL misses (composition), with a proportion test\n")
for lab, mask in GROUPS:
    s = fg[mask]; mm = s[s.made.eq(0) & s.coded]
    print(f"  {lab:<32} {mm.anyWide.mean():.1%} of misses were wide   (n={len(mm)})")
mv = g_v[g_v.made.eq(0) & g_v.coded]; mh = g_h[g_h.made.eq(0) & g_h.coded]
mo = o_v[o_v.made.eq(0) & o_v.coded]
print()
prop_test(mv, mh, "anyWide", "Gillette visitors", "Gillette Patriots")
prop_test(mv, mo, "anyWide", "Gillette visitors", "visitors elsewhere")


hdr("7. WHAT THE OTHER MISSES WERE")
for lab, mask in GROUPS:
    s2 = fg[mask]
    print(f"  {lab:<32} att {len(s2):>5}  wide {s2.anyWide.mean():.2%}  short {s2.shortAny.mean():.2%}  "
          f"other coded {s2.otherMiss.mean():.2%}  uncoded {s2.uncoded_miss.mean():.2%}")
print("\n  a sample of the 'other' descriptions at Gillette:")
oth = fg[fg.gillette & fg.otherMiss.eq(1)]
seen = set()
for d in oth.desc:
    t = re.search(r"No Good,\s*([^.]*?),\s*(?:Center|Holder)", d, re.I)
    if t and t.group(1) not in seen:
        seen.add(t.group(1))
print("   ", sorted(seen)[:8])

hdr("8. IS THE EXCESS *DISPROPORTIONATELY* LATERAL?")
print("  Each rate at Gillette as a multiple of the same rate for visitors elsewhere.")
print("  If the board worked, the wide multiple should exceed the overall multiple.\n")
for col, lab in [("anyWide", "wide misses"), ("shortAny", "short misses"), ("otherMiss", "other misses")]:
    r = g_v[col].mean() / o_v[col].mean() if o_v[col].mean() > 0 else float("nan")
    print(f"    {lab:<16} {g_v[col].mean():6.2%} / {o_v[col].mean():6.2%} = {r:.2f}x")
r_all = (1 - g_v.made.mean()) / (1 - o_v.made.mean())
print(f"    {'ALL misses':<16} {1-g_v.made.mean():6.2%} / {1-o_v.made.mean():6.2%} = {r_all:.2f}x")

hdr("9. POWER: what lateral gap could 363 vs 431 kicks actually detect?")
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize
pw = NormalIndPower()
base = g_h.anyWide.mean()
for target in [0.03, 0.04, 0.05, 0.06, 0.08]:
    es = proportion_effectsize(base + target, base)
    power = pw.power(effect_size=es, nobs1=len(g_v), ratio=len(g_h) / len(g_v), alpha=0.05)
    print(f"    a +{target:.0%} lateral gap over the Patriots' {base:.1%} -> power {power:.0%}")
print(f"\n  observed gap +{g_v.anyWide.mean()-base:.2%}; at this sample size only a gap")
print("  roughly twice that size would reliably clear p<0.05.")
