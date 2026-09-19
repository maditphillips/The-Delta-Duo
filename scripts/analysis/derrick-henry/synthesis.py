"""The bridge: when his team is favoured, defences commit harder to stopping him.

NGS is weekly, so each player-week is joined to that week's game and its line.
The question is whether the two halves of the study are the same finding: he is
handed worse rushing situations than his peers, and the situations get worse
still when his team is favoured, and he beats them anyway.
RYOE and expected yards exist from 2018 on; box counts from 2016.
"""
import numpy as np
import pandas as pd

import common

pd.set_option("display.width", 220)

g, r = common.load()
n = pd.read_parquet(f"{common.HERE}/ngs_rushing.parquet")
n = n[(n.season_type == "REG") & (n.rush_attempts > 0)
      & n.player_gsis_id.isin(common.rb_ids())].copy()

# Attach the line to each player-week via that team's game.
gm = g[g.game_type == "REG"].copy()
long = pd.concat([
    gm.assign(team=gm.home_team, sp=gm.spread_line),
    gm.assign(team=gm.away_team, sp=-gm.spread_line),
])[["season", "week", "team", "sp"]]
n = n.merge(long, left_on=["season", "week", "team_abbr"],
            right_on=["season", "week", "team"], how="left")
n = n[n.sp.notna()]
n["favored"] = np.where(n.sp > 0, "Favored", np.where(n.sp < 0, "Underdog", "Pick'em"))

h = n[n.player_gsis_id == common.HENRY]
peer = n[n.player_gsis_id != common.HENRY]


def block(df, label):
    rows = {}
    for tag, d in df.groupby("favored"):
        if tag == "Pick'em" or d.rush_attempts.sum() < 50:
            continue
        rows[tag] = {
            "att": int(d.rush_attempts.sum()),
            "% vs 8+ box": round(common.wavg(d.percent_attempts_gte_eight_defenders,
                                             d.rush_attempts), 1),
            "expected YPC": round(common.wavg(
                d.expected_rush_yards / d.rush_attempts.clip(lower=1),
                d.rush_attempts), 2),
            "actual YPC": round(d.rush_yards.sum() / d.rush_attempts.sum(), 2),
            "RYOE/att": round(common.wavg(d.rush_yards_over_expected_per_att,
                                          d.rush_attempts), 2),
        }
    t = pd.DataFrame(rows).T
    print(f"\n### {label}\n")
    print(t.to_string())
    return t


print("=" * 88)
print("THE BRIDGE: DOES THE DEFENCE COMMIT HARDER WHEN HIS TEAM IS FAVOURED?")
print("=" * 88)
ht = block(h, "Derrick Henry")
pt = block(peer, "Every other RB, same weeks")

if {"Favored", "Underdog"} <= set(ht.index) and {"Favored", "Underdog"} <= set(pt.index):
    print("\n### Favoured minus underdog, side by side\n")
    d = pd.DataFrame({
        "Henry": ht.loc["Favored"] - ht.loc["Underdog"],
        "peer RBs": pt.loc["Favored"] - pt.loc["Underdog"],
    }).drop(index="att").round(2)
    print(d.to_string())

# Does the box-count effect show up on the ground, in the play-by-play?
reg = r[(r.season_type == "REG") & r.rusher_player_id.isin(common.rb_ids())]
hh = reg[reg.rusher_player_id == common.HENRY]
print("\n### The same split, from play-by-play (all designed runs)\n")
t = hh.groupby("favored", observed=True).apply(common.rates, include_groups=False)
print(t.drop(index="Pick'em", errors="ignore").round(3).to_string())

# How much of Henry's career is spent as the favourite at all?
print("\n### How often was he the favourite?\n")
gmh = hh.groupby("game_id").team_spread.first()
print(f"  favoured in {int((gmh > 0).sum())} of {len(gmh)} games "
      f"({100 * (gmh > 0).mean():.0f}%), average line {gmh.mean():+.1f}")
by_team = hh.groupby([hh.season, "posteam"]).team_spread.mean().round(1)
print("\n  average line by season (his team's side):")
print(by_team.to_string())
