"""The age curve: running backs are supposed to be finished by 28.

Age is computed at each game, not per season, so a back born in January is not
credited with the same age as one born in December. Every comparison is against
the same peer pool used elsewhere - RB/FB, 400+ designed carries, 2016-2026.
"""
import numpy as np
import pandas as pd

import common

pd.set_option("display.width", 210)
pd.set_option("display.max_columns", 40)

g, r = common.load()
pl = pd.read_parquet(f"{common.HERE}/players.parquet")
dob = pd.to_datetime(pl.set_index("gsis_id").birth_date, errors="coerce")

reg = r[(r.season_type == "REG") & r.rusher_player_id.isin(common.rb_ids())].copy()
kick = g.set_index("game_id").gameday
reg["gameday"] = pd.to_datetime(reg.game_id.map(kick), errors="coerce")
reg["dob"] = reg.rusher_player_id.map(dob)
reg["age"] = (reg.gameday - reg.dob).dt.days / 365.25
reg = reg[reg.age.notna()]
reg["age_season"] = np.floor(reg.age).astype(int)

vol = reg.groupby("rusher_player_id").size()
peers = vol[vol >= common.MIN_CARRIES].index
p = reg[reg.rusher_player_id.isin(peers)].copy()
nm = p.groupby("rusher_player_id").rusher_player_name.last()

h = p[p.rusher_player_id == common.HENRY]
oth = p[p.rusher_player_id != common.HENRY]

print("=" * 100)
print("THE AGE CURVE")
print(f"Henry born {dob[common.HENRY].date()}; "
      f"age {(pd.Timestamp('2026-09-19') - dob[common.HENRY]).days / 365.25:.1f} today")
print("=" * 100)

print("\n### Henry season by season, with his age on opening day\n")
t = h.groupby("season").agg(
    age=("age", "min"), team=("posteam", lambda s: s.mode().iat[0]),
    g=("game_id", "nunique"), att=("yards_gained", "size"),
    yds=("yards_gained", "sum"), td=("rush_touchdown", "sum"),
    ypc=("yards_gained", "mean"), epa=("epa", "mean"))
t["yds/g"] = (t.yds / t.g).round(1)
t["age"] = t.age.round(1)
print(t.round(3).to_string())

print("\n### The league's RB age curve vs his  (designed runs, peer pool)\n")
band = [21, 23, 25, 26, 27, 28, 29, 30, 31, 40]
lab = ["21-22", "23-24", "25", "26", "27", "28", "29", "30", "31+"]
oth_c = pd.cut(oth.age, band, labels=lab, right=False)
h_c = pd.cut(h.age, band, labels=lab, right=False)
cmp = pd.DataFrame({
    "peer YPC": oth.groupby(oth_c, observed=True).yards_gained.mean(),
    "peer carries": oth.groupby(oth_c, observed=True).size(),
    "peer backs": oth.groupby(oth_c, observed=True).rusher_player_id.nunique(),
    "Henry YPC": h.groupby(h_c, observed=True).yards_gained.mean(),
    "Henry carries": h.groupby(h_c, observed=True).size(),
})
cmp["edge"] = (cmp["Henry YPC"] - cmp["peer YPC"]).round(2)
print(cmp.round(2).to_string())

print("\n### How much of the position even survives to each age\n")
surv = oth.groupby(oth_c, observed=True).rusher_player_id.nunique()
print((100 * surv / surv.iloc[0]).round(0).astype(int).to_string(
    header=False, name=False), "\n  (% of the 21-22 cohort still taking carries)")

# --- Age 29+ seasons across the whole era -------------------------------------
print("\n### Every 200+ carry season at age 29 or older, 2016-2026\n")
ssn = p.groupby(["rusher_player_id", "season"]).agg(
    age=("age", "min"), att=("yards_gained", "size"),
    yds=("yards_gained", "sum"), td=("rush_touchdown", "sum"),
    ypc=("yards_gained", "mean"), epa=("epa", "mean"))
old = ssn[(ssn.age >= 29) & (ssn.att >= 200)].copy()
old["player"] = [nm.get(i, i) for i, _ in old.index]
old = old.reset_index(drop=True).sort_values("yds", ascending=False)
old["age"] = old.age.round(1)
print(old[["player", "age", "att", "yds", "td", "ypc", "epa"]]
      .head(18).round(3).to_string(index=False))
print(f"\n  {len(old)} such seasons in 11 years, by "
      f"{old.player.nunique()} different backs. "
      f"Henry has {int((old.player == 'D.Henry').sum())} of them.")

# --- Does HIS curve bend? -----------------------------------------------------
print("\n### Henry before and after 29\n")
pre, post = h[h.age < 29], h[h.age >= 29]
rows = []
for lab2, d in [("age 22-28", pre), ("age 29+", post)]:
    rows.append({"": lab2, "games": d.game_id.nunique(), "att": len(d),
                 "att/g": round(len(d) / d.game_id.nunique(), 1),
                 "YPC": round(d.yards_gained.mean(), 2),
                 "EPA": round(d.epa.mean(), 3),
                 "success": round(d.success.mean(), 3),
                 "10+": round(d.explosive_10.mean(), 3),
                 "TD/carry": round(d.rush_touchdown.mean(), 3)})
print(pd.DataFrame(rows).to_string(index=False))

print("\n### Same split for every peer who reached 29 with 150+ carries either side\n")
rows = []
for pid, d in p.groupby("rusher_player_id"):
    a, b = d[d.age < 29], d[d.age >= 29]
    if len(a) >= 150 and len(b) >= 150:
        rows.append({"player": nm.get(pid, pid), "pre att": len(a),
                     "pre YPC": round(a.yards_gained.mean(), 2),
                     "post att": len(b),
                     "post YPC": round(b.yards_gained.mean(), 2),
                     "delta": round(b.yards_gained.mean() - a.yards_gained.mean(), 2)})
d29 = pd.DataFrame(rows).sort_values("delta", ascending=False)
print(d29.to_string(index=False))
print(f"\n  median delta {d29.delta.median():+.2f} YPC; "
      f"{(d29.delta > 0).sum()} of {len(d29)} improved. "
      f"Henry {d29.loc[d29.player == 'D.Henry', 'delta'].iat[0]:+.2f}.")
