"""Separate "his team was favoured" from "his team was ahead".

A favourite leads more often, and leading teams run more against softer boxes,
so the raw split in splits.py is partly just score state. Two ways of pulling
them apart: the two-way table, and direct standardisation - reweighting his
underdog carries so their score-state mix matches his favoured carries, which
answers "what would the underdog games look like if they had been played from
the same scoreboard?"
"""
import numpy as np
import pandas as pd

import common

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 40)

g, r = common.load()
reg = r[(r.season_type == "REG") & r.script.notna()]
h = reg[reg.rusher_player_id == common.HENRY].copy()
lg = reg[reg.rusher_player_id != common.HENRY]

print("=" * 96)
print("SEPARATING 'FAVOURED' FROM 'AHEAD'")
print("=" * 96)

print("\n### Where his carries actually come from (% of carries by score state)\n")
mix = pd.crosstab(h.favored, h.script, normalize="index").mul(100).round(1)
mix["carries"] = h.groupby("favored").size()
print(mix.to_string())

print("\n### Two-way: yards per carry, favoured x score state  (carries in brackets)\n")
piv = h.pivot_table(index="favored", columns="script", values="yards_gained",
                    aggfunc=["mean", "size"], observed=True)
out = pd.DataFrame(index=piv["mean"].index)
for c in piv["mean"].columns:
    out[c] = (piv["mean"][c].round(2).astype(str) + " ("
              + piv["size"][c].fillna(0).astype(int).astype(str) + ")")
print(out.to_string())

print("\n### Two-way: EPA per carry, favoured x score state\n")
print(h.pivot_table(index="favored", columns="script", values="epa",
                    aggfunc="mean", observed=True).round(3).to_string())


def standardise(df, weights, col):
    """Value of `col` if this group's score-state mix matched `weights`."""
    m = df.groupby("script", observed=True)[col].mean()
    w = weights.reindex(m.index).fillna(0)
    return float((m * w).sum() / w.sum())


fav = h[h.favored == "Favored"]
dog = h[h.favored == "Underdog"]
wfav = fav.groupby("script", observed=True).size()

print("\n### Direct standardisation: the gap before and after holding score state constant\n")
rows = []
for col, label in [("yards_gained", "yards per carry"), ("epa", "EPA per carry"),
                   ("success", "success rate"), ("rush_touchdown", "TD per carry"),
                   ("explosive_10", "10+ yard rate")]:
    raw_f, raw_d = fav[col].mean(), dog[col].mean()
    adj_d = standardise(dog, wfav, col)
    rows.append({
        "metric": label,
        "favoured": round(raw_f, 4),
        "underdog (raw)": round(raw_d, 4),
        "underdog (score-state adj.)": round(adj_d, 4),
        "raw gap": round(raw_f - raw_d, 4),
        "gap after control": round(raw_f - adj_d, 4),
        "% of gap that survives": f"{100 * (raw_f - adj_d) / (raw_f - raw_d):.0f}%"
        if abs(raw_f - raw_d) > 1e-9 else "-",
    })
print(pd.DataFrame(rows).to_string(index=False))

print("\n### The same control applied to every other RB, as the baseline\n")
lgf, lgd = lg[lg.favored == "Favored"], lg[lg.favored == "Underdog"]
wlf = lgf.groupby("script", observed=True).size()
rows = []
for col, label in [("yards_gained", "yards per carry"), ("epa", "EPA per carry"),
                   ("explosive_10", "10+ yard rate")]:
    rf, rd = lgf[col].mean(), lgd[col].mean()
    ad = standardise(lgd, wlf, col)
    rows.append({"metric": label, "favoured": round(rf, 4),
                 "underdog (raw)": round(rd, 4),
                 "underdog (adj.)": round(ad, 4),
                 "raw gap": round(rf - rd, 4),
                 "gap after control": round(rf - ad, 4)})
print(pd.DataFrame(rows).to_string(index=False))
print(f"\n(league baseline: {len(lgf):,} favoured carries, {len(lgd):,} underdog, "
      f"all non-Henry designed runs 2016-2026)")

print("\n### Henry vs the field inside each score state (yards per carry)\n")
cmp = pd.DataFrame({
    "Henry": h.groupby("script", observed=True).yards_gained.mean(),
    "league RB": lg.groupby("script", observed=True).yards_gained.mean(),
    "Henry carries": h.groupby("script", observed=True).size(),
})
cmp["edge"] = (cmp.Henry - cmp["league RB"]).round(2)
print(cmp.round(2).to_string())

print("\n### And by live win probability (yards per carry)\n")
cmp2 = pd.DataFrame({
    "Henry": h.groupby("wp_bucket", observed=True).yards_gained.mean(),
    "league RB": lg.groupby("wp_bucket", observed=True).yards_gained.mean(),
    "Henry carries": h.groupby("wp_bucket", observed=True).size(),
})
cmp2["edge"] = (cmp2.Henry - cmp2["league RB"]).round(2)
print(cmp2.round(2).to_string())
