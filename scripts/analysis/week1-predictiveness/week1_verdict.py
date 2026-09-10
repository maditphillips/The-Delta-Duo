"""One question: does Week 1 predict how a player performs over the whole year?

The common analyst line -- "look at all these Week 1 stars who were duds" -- is a
claim about a numerator with no denominator. Week 1 stars who bust are real and
easy to name. The question is whether they bust MORE OFTEN than everyone else.
So every tier below reports its own bust rate next to the field's.

Two targets, because "the entire year" and "the rest of the year" are different
questions and the difference matters:

  full season   weeks 1 onward. Week 1 is inside it, so 1/17th of the target is
                the predictor itself. Honest for "how did the year go", but part
                of the correlation is definitional.
  rest of season  weeks 2 onward. No overlap. The clean prediction test.

Ranks are taken each season among every player at that position who played in
Week 1, so a tier means the same thing in 2013 as in 2025.

Written to VERDICT.txt.
"""
import numpy as np
import pandas as pd
from scipy import stats
import common as C

POS = ("QB", "RB", "WR", "TE")
STARTERS = {"QB": 12, "RB": 24, "WR": 36, "TE": 12}     # roughly a 12-team league
TIERS = [(1, 3, "top 3"), (4, 6, "4-6"), (7, 12, "7-12"), (13, 24, "13-24"),
         (25, 36, "25-36"), (37, 60, "37-60"), (61, 999, "61+")]


def panel(pos, weekly):
    p = weekly[weekly.position == pos]
    w1 = p[p.week == 1].groupby(["player_id", "season"]).agg(
        w1_pts=("fantasy_points_ppr", "sum"), w1_half=("fantasy_points_half", "sum"))
    g = p.groupby(["player_id", "season"])
    full = pd.DataFrame(dict(full_pts=g.fantasy_points_ppr.sum(), full_games=g.size()))
    r = p[p.week >= 2].groupby(["player_id", "season"])
    ros = pd.DataFrame(dict(ros_pts=r.fantasy_points_ppr.sum(), ros_games=r.size()))
    d = w1.join(full).join(ros).reset_index()
    d["ros_pts"] = d.ros_pts.fillna(0)
    d["ros_games"] = d.ros_games.fillna(0)
    d["full_ppg"] = d.full_pts / d.full_games
    d["ros_ppg"] = np.where(d.ros_games > 0, d.ros_pts / d.ros_games, 0.0)
    names = p[["player_id", "season", "player_display_name"]].drop_duplicates(
        ["player_id", "season"])
    d = d.merge(names, on=["player_id", "season"], how="left")
    for src, out in (("w1_pts", "w1_rank"), ("full_pts", "full_rank"),
                     ("ros_pts", "ros_rank")):
        d[out] = d.groupby("season")[src].rank(ascending=False, method="min")
    return d


def cc(x, y):
    m = np.isfinite(x) & np.isfinite(y)
    r = float(np.corrcoef(x[m], y[m])[0, 1])
    rho = float(pd.Series(x[m]).rank().corr(pd.Series(y[m]).rank()))
    t = r * np.sqrt(m.sum() - 2) / np.sqrt(1 - r * r)
    return r, rho, r * r, float(2 * stats.t.sf(abs(t), m.sum() - 2)), int(m.sum())


def main():
    weekly = C._derived(C.load_weekly())
    print("=" * 98)
    print("DOES WEEK 1 PREDICT THE WHOLE SEASON?")
    print(f"nflverse regular seasons {C.FIRST_SEASON}-{C.LAST_SEASON}, PPR")
    print("=" * 98)

    print("\n\n## 1. THE CORRELATION, PLAINLY")
    print("   Week 1 fantasy points against two targets. 'full season' contains Week 1,")
    print("   so 1/17th of it is the predictor itself; 'rest of season' does not.")
    print(f"\n   {'':<6}{'full-season points/game':>34}{'rest-of-season points/game':>34}")
    print(f"   {'pos':<6}{'n':>7}{'r':>7}{'rho':>7}{'R2':>7}{'p':>9}"
          f"{'r':>9}{'rho':>7}{'R2':>7}{'p':>9}")
    print("   " + "-" * 79)
    keep = {}
    for pos in POS:
        d = panel(pos, weekly)
        d = d[d.full_games >= 1]
        keep[pos] = d
        a = cc(d.w1_pts.values, d.full_ppg.values)
        b = cc(d.w1_pts.values, d.ros_ppg.values)
        fp = lambda v: "  <1e-16" if v < 1e-16 else f"{v:>9.2g}"
        print(f"   {pos:<6}{a[4]:>7}{a[0]:>7.3f}{a[1]:>7.3f}{a[2]:>7.3f}{fp(a[3])}"
              f"{b[0]:>9.3f}{b[1]:>7.3f}{b[2]:>7.3f}{fp(b[3])}")

    print("\n\n## 2. WEEK 1 FINISH -> FULL-SEASON FINISH")
    print("   The 'bust' column is the share of that tier who finished outside a")
    print("   startable full-season rank (QB/TE outside 12, RB outside 24, WR outside 36).")
    for pos in POS:
        d = keep[pos]
        cut = STARTERS[pos]
        base_start = float((d.full_rank <= cut).mean())
        base_bust = 1 - base_start
        print(f"\n   {pos}   ({len(d)} player-seasons, ~{len(d)/d.season.nunique():.0f} "
              f"per season; startable = top {cut})")
        print(f"   {'week 1 finish':<16}{'n':>6}{'full-season ppg':>18}"
              f"{'median full rank':>19}{'startable':>12}{'bust':>8}")
        print("   " + "-" * 79)
        for lo, hi, lab in TIERS:
            b = d[(d.w1_rank >= lo) & (d.w1_rank <= hi)]
            if len(b) < 20:
                continue
            print(f"   {lab:<16}{len(b):>6}{b.full_ppg.mean():>18.2f}"
                  f"{b.full_rank.median():>19.0f}"
                  f"{(b.full_rank <= cut).mean()*100:>11.0f}%"
                  f"{(b.full_rank > cut).mean()*100:>7.0f}%")
        print(f"   {'FIELD AVERAGE':<16}{len(d):>6}{d.full_ppg.mean():>18.2f}"
              f"{d.full_rank.median():>19.0f}{base_start*100:>11.0f}%{base_bust*100:>7.0f}%")

    print("\n\n## 3. THE ANALYST'S CLAIM, TESTED DIRECTLY")
    print("   'Week 1 stars turn into duds.' They do -- but compared with whom?")
    print(f"\n   {'pos':<6}{'week 1 top 12':>28}{'everyone else':>22}{'ratio':>8}")
    print(f"   {'':<6}{'n':>7}{'bust rate':>11}{'per szn':>10}"
          f"{'n':>8}{'bust rate':>14}")
    print("   " + "-" * 64)
    for pos in POS:
        d = keep[pos]
        cut = STARTERS[pos]
        hot = d[d.w1_rank <= 12]
        rest = d[d.w1_rank > 12]
        hb = float((hot.full_rank > cut).mean())
        rb = float((rest.full_rank > cut).mean())
        per = float((hot.full_rank > cut).sum()) / d.season.nunique()
        print(f"   {pos:<6}{len(hot):>7}{hb*100:>10.0f}%{per:>10.1f}"
              f"{len(rest):>8}{rb*100:>13.0f}%{hb/rb:>8.2f}")
    print("\n   'per szn' is how many nameable Week 1 top-12 busts a season produces at")
    print("   that position -- the raw material for the take. The ratio is what the take")
    print("   leaves out: below 1.00 means a Week 1 star busts LESS often than the field.")

    print("\n\n## 4. HOW MUCH OF THE SEASON DOES ONE GAME MOVE THE ESTIMATE?")
    print("   Season points per game predicted from Week 1 points alone (OLS).")
    print(f"   {'pos':<6}{'intercept':>11}{'slope':>9}{'resid sd':>10}"
          f"{'a 25-pt week 1 projects':>26}{'a 3-pt week 1 projects':>25}")
    print("   " + "-" * 87)
    for pos in POS:
        d = keep[pos]
        sl, ic, r, p, se = stats.linregress(d.w1_pts, d.full_ppg)
        rsd = float((d.full_ppg - (ic + sl * d.w1_pts)).std(ddof=2))
        print(f"   {pos:<6}{ic:>11.2f}{sl:>9.3f}{rsd:>10.2f}"
              f"{ic+sl*25:>21.1f} ppg{ic+sl*3:>20.1f} ppg")

    print("\n\n## 5. THE NAMEABLE CASES, SO THE TAKE HAS ITS DUE")
    for pos in ("RB", "WR"):
        d = keep[pos]
        cut = STARTERS[pos]
        busts = d[(d.w1_rank <= 5) & (d.full_rank > cut)].sort_values("w1_pts",
                                                                     ascending=False)
        hits = d[(d.w1_rank <= 5) & (d.full_rank <= 12)]
        tot = d[d.w1_rank <= 5]
        print(f"\n   {pos}: of {len(tot)} top-5 Week 1 finishes, {len(busts)} busted "
              f"({len(busts)/len(tot)*100:.0f}%) and {len(hits)} finished top-12 "
              f"({len(hits)/len(tot)*100:.0f}%)")
        print("     busts: " + ", ".join(
            f"{r.player_display_name} {int(r.season)} ({r.w1_pts:.0f} pts wk1, "
            f"finished {int(r.full_rank)})" for _, r in busts.head(6).iterrows()))
    pd.concat([d.assign(position=p) for p, d in keep.items()]).to_csv(
        "out_verdict.csv", index=False)


if __name__ == "__main__":
    main()
