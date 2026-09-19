"""What makes him an outlier - Henry's percentile against every modern RB.

Peer group: every player with 400+ designed carries, 2016-2026 regular season,
which is the era NGS tracking covers and the whole of Henry's career.
Each test is scored as a percentile so the metrics are comparable to each other.
"""
import numpy as np
import pandas as pd

import common

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 40)

g, r = common.load()
reg = r[r.season_type == "REG"].copy()

reg = reg[reg.rusher_player_id.isin(common.rb_ids())]   # RBs only, no QB keepers
vol = reg.groupby("rusher_player_id").size()
peers = vol[vol >= common.MIN_CARRIES].index
p = reg[reg.rusher_player_id.isin(peers)].copy()
name = p.groupby("rusher_player_id").rusher_player_name.last()

print("=" * 96)
print(f"PEER GROUP: {len(peers)} backs with {common.MIN_CARRIES}+ designed "
      f"carries, 2016-2026 regular season")
print("=" * 96)


def rank(series, label, higher_better=True, fmt="{:.3f}"):
    """Print Henry's value, rank and percentile within the peer group."""
    s = series.dropna().sort_values(ascending=not higher_better)
    if common.HENRY not in s.index:
        print(f"{label:<38} n/a")
        return
    v = s.loc[common.HENRY]
    pos = list(s.index).index(common.HENRY) + 1
    pct = 100 * (len(s) - pos) / (len(s) - 1)
    lead = name.get(s.index[0], "?")
    print(f"{label:<38} {fmt.format(v):>8}   rank {pos:>2}/{len(s)}   "
          f"{pct:>5.1f}th pct   (leader: {lead} {fmt.format(s.iloc[0])})")


# --- 1. The favoured effect itself -------------------------------------------
fav = p[p.favored == "Favored"].groupby("rusher_player_id")
dog = p[p.favored == "Underdog"].groupby("rusher_player_id")
enough = (fav.size() >= 150) & (dog.size() >= 150)
gap = (fav.yards_gained.mean() - dog.yards_gained.mean())[enough]
gap_epa = (fav.epa.mean() - dog.epa.mean())[enough]

print(f"\n--- 1. IS THE FAVOURED EFFECT ITSELF UNUSUAL?  "
      f"({enough.sum()} backs with 150+ carries on each side)\n")
rank(fav.yards_gained.mean()[enough], "YPC when favoured", fmt="{:.2f}")
rank(dog.yards_gained.mean()[enough], "YPC when underdog", fmt="{:.2f}")
rank(gap, "favoured MINUS underdog, YPC", fmt="{:+.2f}")
rank(gap_epa, "favoured MINUS underdog, EPA/carry", fmt="{:+.3f}")

# --- 2. Running when everyone knows it is coming ------------------------------
print("\n--- 2. RUNNING WITH A LEAD, WHEN THE BOX IS STACKED AND EVERYONE KNOWS\n")
up9 = p[p.score_differential >= 9].groupby("rusher_player_id")
u9 = up9.yards_gained.mean()[up9.size() >= 100]
rank(u9, "YPC while up 9+ (100+ carries)", fmt="{:.2f}")
rank(up9.explosive_10.mean()[up9.size() >= 100], "10+ yd rate while up 9+")

q4 = p[p.qtr == 4].groupby("rusher_player_id")
rank(q4.yards_gained.mean()[q4.size() >= 100], "YPC in the 4th quarter", fmt="{:.2f}")
q4l = p[(p.qtr == 4) & (p.score_differential >= 1)].groupby("rusher_player_id")
rank(q4l.yards_gained.mean()[q4l.size() >= 75],
     "YPC, 4th quarter while leading", fmt="{:.2f}")

# --- 3. Shape of the distribution: is he a big-play back or a grinder? --------
print("\n--- 3. THE SHAPE OF THE CARRY DISTRIBUTION\n")
gp = p.groupby("rusher_player_id")
rank(gp.yards_gained.mean(), "yards per carry, overall", fmt="{:.2f}")
rank(gp.yards_gained.median(), "MEDIAN yards per carry", fmt="{:.1f}")
rank(gp.explosive_10.mean(), "10+ yard rate")
rank(gp.explosive_15.mean(), "15+ yard rate")
rank(p.assign(b=(p.yards_gained >= 25).astype(float)).groupby("rusher_player_id").b.mean(),
     "25+ yard rate")
rank(p.assign(b=(p.yards_gained >= 40).astype(float)).groupby("rusher_player_id").b.mean(),
     "40+ yard rate")
rank(gp.stuffed.mean(), "stuffed rate (<=0 yds)", higher_better=False)
rank(gp.success.mean(), "success rate")
rank(gp.rush_touchdown.mean(), "TD per carry")

# --- 4. Volume and durability -------------------------------------------------
print("\n--- 4. VOLUME AND DURABILITY\n")
rank(gp.size().astype(float), "total designed carries", fmt="{:.0f}")
pgc = p.groupby(["rusher_player_id", "game_id"]).size()
rank(pgc.groupby(level=0).mean(), "carries per game", fmt="{:.1f}")
rank(pgc.groupby(level=0).apply(lambda s: (s >= 25).mean()), "share of games with 25+ carries")
rank(p.groupby("rusher_player_id").season.nunique().astype(float),
     "seasons with a carry", fmt="{:.0f}")
rank(gp.fumble_lost.mean(), "fumbles lost per carry", higher_better=False, fmt="{:.4f}")

# --- 5. Does he wear defences down within a game? -----------------------------
print("\n--- 5. DOES HE GET BETTER AS THE GAME GOES ON?\n")
p = p.sort_values(["game_id", "rusher_player_id"])
p["carry_no"] = p.groupby(["game_id", "rusher_player_id"]).cumcount() + 1
p["carry_bucket"] = pd.cut(p.carry_no, [0, 5, 10, 15, 20, 99],
                           labels=["1-5", "6-10", "11-15", "16-20", "21+"])
h = p[p.rusher_player_id == common.HENRY]
oth = p[p.rusher_player_id != common.HENRY]
curve = pd.DataFrame({
    "Henry YPC": h.groupby("carry_bucket", observed=True).yards_gained.mean(),
    "Henry carries": h.groupby("carry_bucket", observed=True).size(),
    "peer YPC": oth.groupby("carry_bucket", observed=True).yards_gained.mean(),
    "peer carries": oth.groupby("carry_bucket", observed=True).size(),
})
curve["edge"] = curve["Henry YPC"] - curve["peer YPC"]
print(curve.round(2).to_string())

late = p[p.carry_no >= 16].groupby("rusher_player_id")
early = p[p.carry_no <= 5].groupby("rusher_player_id")
ok = (late.size() >= 100) & (early.size() >= 200)
print()
rank(late.yards_gained.mean()[ok], "YPC on carry 16+ of a game", fmt="{:.2f}")
rank((late.yards_gained.mean() - early.yards_gained.mean())[ok],
     "carry 16+ MINUS carries 1-5, YPC", fmt="{:+.2f}")

# --- 6. Next Gen Stats: was the box loaded, and did it matter? ----------------
print("\n--- 6. NEXT GEN STATS TRACKING (2016-2026)\n")
n = pd.read_parquet(f"{common.HERE}/ngs_rushing.parquet")
n = n[(n.season_type == "REG") & (n.week > 0) & (n.rush_attempts > 0)]
n = n[n.player_gsis_id.isin(common.rb_ids())]
w = n.groupby("player_gsis_id").apply(
    lambda d: pd.Series({
        "att": d.rush_attempts.sum(),
        "ryoe_att": common.wavg(d.rush_yards_over_expected_per_att, d.rush_attempts),
        "ryoe_wks": d.rush_yards_over_expected_per_att.notna().sum(),
        "exp_ypc": common.wavg(d.expected_rush_yards / d.rush_attempts.clip(lower=1),
                               d.rush_attempts),
        "box8": common.wavg(d.percent_attempts_gte_eight_defenders, d.rush_attempts),
        "eff": common.wavg(d.efficiency, d.rush_attempts),
        "ttlos": common.wavg(d.avg_time_to_los, d.rush_attempts),
    }), include_groups=False)
w = w[w.att >= common.MIN_CARRIES]
name = pd.concat([name, n.groupby("player_gsis_id").player_display_name.last()])
name = name[~name.index.duplicated(keep="last")]
print(f"({len(w)} backs qualify on NGS volume)\n")
rank(w.ryoe_att, "rush yards OVER EXPECTED per carry", fmt="{:+.2f}")
rank(w.exp_ypc, "EXPECTED yards per carry (blocking/box)", fmt="{:.2f}")
rank(w.box8, "% of carries vs 8+ in the box", fmt="{:.1f}")
rank(w.eff, "NGS efficiency (distance travelled)", higher_better=False, fmt="{:.2f}")
rank(w.ttlos, "avg time to line of scrimmage (s)", higher_better=False, fmt="{:.2f}")
