"""Henry when his team was favoured - volume, efficiency, touchdowns.

Three cuts of the same question, because "favoured" can be read three ways:
binary, by the size of the spread, and as the market's implied win probability.
Regular season only; the playoffs are counted separately at the end.
"""
import pandas as pd

import common

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 40)

g, r = common.load()
reg = r[r.season_type == "REG"]
h = reg[reg.rusher_player_id == common.HENRY].copy()

PCT = ["success", "td_rate", "exp10", "exp15", "stuff"]


def show(title, table, per_game=None):
    t = table.copy()
    for c in PCT:
        if c in t:
            t[c] = (t[c] * 100).round(1)
    for c in ("ypc", "epa"):
        if c in t:
            t[c] = t[c].round(3 if c == "epa" else 2)
    t["att"] = t["att"].astype(int)
    t["yards"] = t["yards"].astype(int)
    if per_game is not None:
        t.insert(0, "games", per_game["games"])
        t.insert(1, "att/g", per_game["att_pg"].round(1))
        t.insert(2, "yds/g", per_game["yds_pg"].round(1))
    print(f"\n### {title}\n")
    print(t.to_string())


def per_game(df, key):
    gm = df.groupby([key, "game_id"], observed=True).agg(
        a=("yards_gained", "size"), y=("yards_gained", "sum"))
    out = gm.groupby(level=0, observed=True).agg(
        games=("a", "size"), att_pg=("a", "mean"), yds_pg=("y", "mean"))
    return out


print("=" * 88)
print("DERRICK HENRY, REGULAR SEASON 2016-2026  (designed runs only)")
print(f"{len(h)} carries, {int(h.yards_gained.sum())} yards, "
      f"{int(h.rush_touchdown.sum())} rushing TD, "
      f"{h.game_id.nunique()} games")
print("=" * 88)

# 1. Binary
show("1. Binary: was his team favoured?",
     h.groupby("favored", observed=True).apply(common.rates, include_groups=False),
     per_game(h, "favored"))

# 2. Spread tiers
show("2. By the size of the line",
     h.groupby("tier", observed=True).apply(common.rates, include_groups=False),
     per_game(h, "tier"))

# 3. Market implied win probability
h["ml_bucket"] = pd.cut(h.team_wp_pre, [0, .35, .5, .65, .8, 1.0],
                        labels=["<35%", "35-50%", "50-65%", "65-80%", ">80%"])
show("3. By pre-game moneyline win probability (de-vigged)",
     h.groupby("ml_bucket", observed=True).apply(common.rates, include_groups=False),
     per_game(h, "ml_bucket"))

# Correlation of the continuous line against per-game output
pg = h.groupby("game_id").agg(
    att=("yards_gained", "size"), yds=("yards_gained", "sum"),
    td=("rush_touchdown", "sum"), epa=("epa", "mean"),
    spread=("team_spread", "first"), wp=("team_wp_pre", "first"))
print("\n### Correlation with the pre-game line, across "
      f"{len(pg)} games\n")
print(pg[["att", "yds", "td", "epa"]].corrwith(pg.spread).round(3)
      .rename("vs spread").to_frame()
      .join(pg[["att", "yds", "td", "epa"]].corrwith(pg.wp).round(3)
            .rename("vs implied win %")).to_string())

# Playoffs, reported on their own
po = r[(r.season_type != "REG") & (r.rusher_player_id == common.HENRY)]
print(f"\n### Playoffs, separately: {len(po)} carries in "
      f"{po.game_id.nunique()} games\n")
show("Playoffs by favoured status",
     po.groupby("favored", observed=True).apply(common.rates, include_groups=False),
     per_game(po, "favored"))
