"""Usage by down: when was he on the field, and when did he get the ball?

Two different questions that get conflated. Presence is participation data -
was he one of the eleven. Usage is what happened once he was there. A back can
look like a two-down player because he sits on third down, or because he stays
in to block; only the first shows up in presence.

Participation runs 2016-2025, so 2026 is out of this file entirely.
"""
import numpy as np
import pandas as pd

import common

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 40)

pl = pd.read_parquet(f"{common.HERE}/plays.parquet")
pr = pd.read_parquet(f"{common.HERE}/rb_presence.parquet")

pl = pl[(pl.season_type == "REG") & (pl.season <= 2025) & pl.down.notna()].copy()
pl["down"] = pl.down.astype(int)

# One row per (play, peer RB on the field for it).
snaps = pr.merge(pl, on=["game_id", "play_id"], how="inner")
snaps = snaps[snaps.possession_team == snaps.posteam]
snaps["is_carry"] = (snaps.rusher_player_id == snaps.pid).astype(int)
snaps["is_target"] = (snaps.receiver_player_id == snaps.pid).astype(int)
snaps["touch"] = snaps[["is_carry", "is_target"]].max(axis=1)

h = snaps[snaps.pid == common.HENRY]
peer = snaps[snaps.pid != common.HENRY]

print("=" * 100)
print("USAGE BY DOWN  (participation data, 2016-2025 regular season)")
print("=" * 100)

# Coverage check before any conclusion rests on it.
cov = pl.groupby("season").size()
seen = snaps.groupby("season").game_id.nunique()
print(f"\n  participation covers {snaps.game_id.nunique()} games; "
      f"Henry appears in {h.game_id.nunique()} of them "
      f"({int(h.is_carry.sum())} carries, {int(h.is_target.sum())} targets "
      f"on charted plays)")

# --- 1. Presence: share of his own offence's snaps, by down -------------------
team_snaps = pl.groupby(["game_id", "posteam", "down"]).size().rename("team_plays")
hg = h.groupby(["game_id", "posteam", "down"]).size().rename("on_field")
pres = pd.concat([team_snaps, hg], axis=1).dropna(subset=["on_field"])
by_down = pres.groupby(level=2).agg(on_field=("on_field", "sum"),
                                    team_plays=("team_plays", "sum"))
by_down["presence %"] = (100 * by_down.on_field / by_down.team_plays).round(1)

pg = peer.groupby(["game_id", "posteam", "pid", "down"]).size().rename("on_field")
ppres = pg.reset_index().merge(team_snaps.reset_index(),
                               on=["game_id", "posteam", "down"])
pk = ppres.groupby("down").agg(on=("on_field", "sum"), tp=("team_plays", "sum"))
# Peer rate is per-back, so divide by the number of backs contributing.
nb = ppres.groupby("down").pid.nunique()
by_down["peer avg presence %"] = (100 * pk.on / pk.tp).round(1)

print("\n### 1. PRESENCE — was he one of the eleven?\n")
print(by_down.rename_axis("down").to_string())
print("\n  (peer figure is every other 400+ carry back pooled, so it reads as "
      "'an average peer back's share', not a single player's)")

print("\n### Henry's presence by down, against each of the other top-12 backs\n")
top = peer.groupby("pid").size().nlargest(11).index
rows = []
for pid in [common.HENRY, *top]:
    d = snaps[snaps.pid == pid]
    t = d.groupby("down").size()
    tot = t.sum()
    nmm = d.pid.iloc[0]
    rows.append({"player": nmm, **{f"D{k} %": round(100 * t.get(k, 0) / tot, 1)
                                   for k in (1, 2, 3, 4)}, "snaps": int(tot)})
nmap = pd.read_parquet(f"{common.HERE}/players.parquet").set_index("gsis_id").display_name
t = pd.DataFrame(rows)
t["player"] = t.player.map(nmap).fillna(t.player)
print("  share of each back's own snaps that came on each down:")
print(t.to_string(index=False))

# --- 2. Usage given presence --------------------------------------------------
print("\n### 2. USAGE — once on the field, did he get the ball?\n")
u = h.groupby("down").agg(snaps=("touch", "size"), carries=("is_carry", "sum"),
                          targets=("is_target", "sum"), touches=("touch", "sum"))
u["carry % of snaps"] = (100 * u.carries / u.snaps).round(1)
u["target % of snaps"] = (100 * u.targets / u.snaps).round(1)
u["touch % of snaps"] = (100 * u.touches / u.snaps).round(1)
pu = peer.groupby("down").agg(s=("touch", "size"), t=("touch", "sum"))
u["peer touch % of snaps"] = (100 * pu.t / pu.s).round(1)
print(u.to_string())

print("\n### 3. DISTRIBUTION — where his touches actually come from\n")
tot_t = u.touches.sum()
dist = pd.DataFrame({
    "carries": u.carries, "targets": u.targets, "touches": u.touches,
    "% of his touches": (100 * u.touches / tot_t).round(1),
})
pt = peer.groupby("down").touch.sum()
dist["peer % of touches"] = (100 * pt / pt.sum()).round(1)
print(dist.to_string())

# --- 3. The third-down story --------------------------------------------------
print("\n### 4. THIRD DOWN, split by how far there is to go\n")
h3 = h[h.down == 3].copy()
p3 = peer[peer.down == 3].copy()
bins = [0, 1.5, 3.5, 6.5, 99]
lab = ["3rd & 1", "3rd & 2-3", "3rd & 4-6", "3rd & 7+"]
h3["dist"] = pd.cut(h3.ydstogo, bins, labels=lab)
p3["dist"] = pd.cut(p3.ydstogo, bins, labels=lab)
t3 = pd.DataFrame({
    "Henry snaps": h3.groupby("dist", observed=True).size(),
    "Henry carries": h3.groupby("dist", observed=True).is_carry.sum(),
    "Henry targets": h3.groupby("dist", observed=True).is_target.sum(),
})
t3["Henry touch %"] = (100 * (t3["Henry carries"] + t3["Henry targets"])
                       / t3["Henry snaps"]).round(1)
t3["peer touch %"] = (100 * p3.groupby("dist", observed=True).touch.sum()
                      / p3.groupby("dist", observed=True).size()).round(1)
print(t3.to_string())

# What does his offence do on the third downs he IS out there for?
print("\n### 5. On third downs he was on the field for, what was called?\n")
call = h3.play_type.value_counts(normalize=True).mul(100).round(1)
pcall = p3.play_type.value_counts(normalize=True).mul(100).round(1)
print(pd.DataFrame({"Henry on field %": call, "peer RB on field %": pcall}).to_string())

# --- 4. Efficiency by down ----------------------------------------------------
print("\n### 6. What he did with the carries, by down\n")
hc = h[h.is_carry == 1]
pc = peer[peer.is_carry == 1]
e = pd.DataFrame({
    "att": hc.groupby("down").size(),
    "YPC": hc.groupby("down").yards_gained.mean().round(2),
    "EPA": hc.groupby("down").epa.mean().round(3),
    "success": (100 * hc.groupby("down").success.mean()).round(1),
    "peer YPC": pc.groupby("down").yards_gained.mean().round(2),
    "peer EPA": pc.groupby("down").epa.mean().round(3),
    "peer success": (100 * pc.groupby("down").success.mean()).round(1),
})
print(e.to_string())

print("\n### 7. Third- and fourth-down conversions when he carried\n")
for d in (3, 4):
    c = hc[hc.down == d]
    pcd = pc[pc.down == d]
    if len(c) == 0:
        continue
    print(f"  down {d}: {len(c)} carries, "
          f"{100 * c.first_down.mean():.1f}% moved the chains "
          f"(peer backs {100 * pcd.first_down.mean():.1f}%)")
    sh = c[c.ydstogo <= 2]
    psh = pcd[pcd.ydstogo <= 2]
    if len(sh):
        print(f"          with 2 or fewer to go: {len(sh)} carries, "
              f"{100 * sh.first_down.mean():.1f}% "
              f"(peer backs {100 * psh.first_down.mean():.1f}%)")

print("\n### 8. Presence by down, season by season\n")
hs = h.groupby(["season", "down"]).size().rename("on_field").reset_index()
ts = pl.groupby(["season", "down"]).size().rename("tp").reset_index()
hteam = h.groupby("season").posteam.agg(lambda s: s.mode().iat[0])
tsa = pl[pl.posteam.isin(hteam.values)].copy()
tsa["own"] = tsa.season.map(hteam)
tsa = tsa[tsa.posteam == tsa.own].groupby(["season", "down"]).size().rename("tp").reset_index()
m = hs.merge(tsa, on=["season", "down"])
m["presence %"] = (100 * m.on_field / m.tp).round(1)
print(m.pivot(index="season", columns="down", values="presence %")
      .rename(columns={1: "D1 %", 2: "D2 %", 3: "D3 %", 4: "D4 %"}).to_string())
