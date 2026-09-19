"""Touchdowns: where they come from, and what the spread does to the supply.

A rushing TD is two things multiplied - how often you are handed the ball near
the goal line, and what you do with it there. Being favoured moves the first.
The question is whether it also moves the second.
"""
import numpy as np
import pandas as pd

import common

pd.set_option("display.width", 200)

g, r = common.load()
reg = r[(r.season_type == "REG") & r.rusher_player_id.isin(common.rb_ids())]
h = reg[reg.rusher_player_id == common.HENRY].copy()
lg = reg[reg.rusher_player_id != common.HENRY]

print("=" * 88)
print("TOUCHDOWNS")
print("=" * 88)

h["zone"] = pd.cut(h.yardline_100, [0, 2, 5, 10, 20, 100],
                   labels=["inside 2", "3-5", "6-10", "11-20", "outside 20"])
lgz = lg.assign(zone=pd.cut(lg.yardline_100, [0, 2, 5, 10, 20, 100],
                            labels=["inside 2", "3-5", "6-10", "11-20", "outside 20"]))

print("\n### Conversion by field zone, Henry vs the field\n")
t = pd.DataFrame({
    "Henry att": h.groupby("zone", observed=True).size(),
    "Henry TD%": h.groupby("zone", observed=True).rush_touchdown.mean().mul(100).round(1),
    "peer TD%": lgz.groupby("zone", observed=True).rush_touchdown.mean().mul(100).round(1),
})
t["edge"] = (t["Henry TD%"] - t["peer TD%"]).round(1)
print(t.to_string())

print("\n### Goal-line supply and conversion, favoured vs underdog\n")
rows = []
for tag, d in h[h.favored != "Pick'em"].groupby("favored", observed=True):
    rz = d[d.yardline_100 <= 20]
    gl = d[d.yardline_100 <= 5]
    ngames = d.game_id.nunique()
    rows.append({
        "": tag, "games": ngames,
        "RZ carries/g": round(len(rz) / ngames, 2),
        "RZ TD%": round(100 * rz.rush_touchdown.mean(), 1),
        "inside-5 carries/g": round(len(gl) / ngames, 2),
        "inside-5 TD%": round(100 * gl.rush_touchdown.mean(), 1),
        "TD/game": round(d.rush_touchdown.sum() / ngames, 2),
        "TD outside 20 /g": round(d[d.yardline_100 > 20].rush_touchdown.sum() / ngames, 3),
    })
print(pd.DataFrame(rows).to_string(index=False))

print("\n### Decomposition: where the extra TD/game when favoured comes from\n")
f = h[h.favored == "Favored"]; u = h[h.favored == "Underdog"]
fg, ug = f.game_id.nunique(), u.game_id.nunique()
gl_f, gl_u = f[f.yardline_100 <= 5], u[u.yardline_100 <= 5]
sup_f, sup_u = len(gl_f) / fg, len(gl_u) / ug
cv_f, cv_u = gl_f.rush_touchdown.mean(), gl_u.rush_touchdown.mean()
print(f"  inside-5 carries per game   {sup_u:.2f} -> {sup_f:.2f}  ({sup_f-sup_u:+.2f})")
print(f"  inside-5 conversion rate    {cv_u:.1%} -> {cv_f:.1%}  ({cv_f-cv_u:+.1%})")
print(f"  effect of extra supply alone      {(sup_f-sup_u)*cv_u:+.3f} TD/game")
print(f"  effect of better conversion alone {(cv_f-cv_u)*sup_u:+.3f} TD/game")
long_f = f[f.yardline_100 > 20].rush_touchdown.sum() / fg
long_u = u[u.yardline_100 > 20].rush_touchdown.sum() / ug
print(f"  effect of long TDs (outside 20)   {long_f-long_u:+.3f} TD/game")

print("\n### Career TD share by distance, Henry vs the field\n")
hh = h[h.rush_touchdown == 1]
ll = lg[lg.rush_touchdown == 1]
print(pd.DataFrame({
    "Henry TDs": hh.groupby(pd.cut(hh.yardline_100, [0, 2, 5, 10, 20, 100]),
                            observed=True).size(),
    "Henry %": hh.groupby(pd.cut(hh.yardline_100, [0, 2, 5, 10, 20, 100]),
                          observed=True).size().pipe(lambda s: (100*s/s.sum()).round(1)),
    "peer %": ll.groupby(pd.cut(ll.yardline_100, [0, 2, 5, 10, 20, 100]),
                         observed=True).size().pipe(lambda s: (100*s/s.sum()).round(1)),
}).to_string())

print(f"\n  Henry rushing TDs from outside 20: {int((hh.yardline_100>20).sum())} "
      f"of {len(hh)} ({100*(hh.yardline_100>20).mean():.0f}%), "
      f"peers {100*(ll.yardline_100>20).mean():.0f}%")

# Where he ranks on long TDs, since that is the unusual half.
peers = reg.groupby("rusher_player_id").size()
peers = peers[peers >= common.MIN_CARRIES].index
p = reg[reg.rusher_player_id.isin(peers)]
long_td = p[p.yardline_100 > 20].groupby("rusher_player_id").rush_touchdown.sum()
att = p.groupby("rusher_player_id").size()
rate = (long_td / att).sort_values(ascending=False)
nm = p.groupby("rusher_player_id").rusher_player_name.last()
print(f"\n### Long (20+ yard out) rushing TDs per carry, top 10 of {len(rate)}\n")
top = rate.head(10).to_frame("per carry")
top["TDs"] = long_td.reindex(top.index).astype(int)
top.index = [nm.get(i, i) for i in top.index]
print(top.round(4).to_string())
