"""Run every module, then write the headline FINDINGS.txt from their output files.

Every number below is read back out of out_*.csv, so nothing here is typed by hand.
"""
import subprocess, sys
import numpy as np
import pandas as pd
import common as C

MODULES = [("predictiveness.py", "PREDICTIVENESS.txt"),
           ("stability.py", "STABILITY.txt"),
           ("fantasy.py", "FANTASY.txt"),
           ("team.py", "TEAM.txt")]

# the specific questions that started this study
ASKED = [("RB", "carries", "Week 1 carries -> rest-of-season carries/game"),
         ("RB", "rush_share", "Week 1 share of team carries -> rest-of-season share"),
         ("RB", "snap_pct", "Week 1 snap share -> rest-of-season snap share"),
         ("RB", "yards_per_carry", "Week 1 yards per carry -> rest-of-season YPC"),
         ("RB", "targets", "Week 1 targets -> rest-of-season targets/game"),
         ("RB", "fantasy_ppg_ppr", "Week 1 PPR points -> rest-of-season PPR/game"),
         ("WR", "targets", "Week 1 targets -> rest-of-season targets/game"),
         ("WR", "target_share", "Week 1 target share -> rest-of-season target share"),
         ("WR", "snap_pct", "Week 1 snap share -> rest-of-season snap share"),
         ("WR", "air_yards", "Week 1 air yards -> rest-of-season air yards/game"),
         ("WR", "yards_per_target", "Week 1 yards per target -> rest-of-season YPT"),
         ("WR", "fantasy_ppg_ppr", "Week 1 PPR points -> rest-of-season PPR/game"),
         ("TE", "target_share", "Week 1 target share -> rest-of-season target share"),
         ("TE", "fantasy_ppg_ppr", "Week 1 PPR points -> rest-of-season PPR/game"),
         ("QB", "completion_pct", "Week 1 completion % -> rest-of-season completion %"),
         ("QB", "cpoe", "Week 1 CPOE -> rest-of-season CPOE"),
         ("QB", "pass_attempts", "Week 1 attempts -> rest-of-season attempts/game"),
         ("QB", "fantasy_ppg", "Week 1 fantasy points -> rest-of-season points/game")]


def weeks_to_match_prior(pos):
    """First k where the running weeks-1..k average beats last season's full line."""
    c = pd.read_csv(f"out_curve_{pos}.csv")
    rows = []
    for m in [col for col in c.columns
              if not col.startswith("prior_") and col not in ("k", "n", "position")]:
        p = c["prior_" + m].iloc[0] if "prior_" + m in c else np.nan
        if not np.isfinite(p):
            continue
        hit = c.k[c[m] >= p]
        rows.append(dict(metric=m, prior_r=p, w1_r=c[m].iloc[0],
                         best_r=c[m].max(),
                         k=int(hit.iloc[0]) if len(hit) else None))
    return pd.DataFrame(rows)


def main():
    if "--skip-run" not in sys.argv:
        for mod, out in MODULES:
            print(f"running {mod} -> {out}", flush=True)
            with open(out, "w") as fh:
                subprocess.run([sys.executable, mod], stdout=fh, check=True)

    pred = pd.read_csv("out_predictiveness.csv")
    stab = pd.read_csv("out_stability.csv")
    team = pd.read_csv("out_team.csv")
    lines = []
    P = lines.append

    P("=" * 100)
    P("HOW PREDICTIVE IS NFL WEEK 1?   headline findings")
    P(f"nflverse, regular seasons {C.FIRST_SEASON}-{C.LAST_SEASON}"
      f" (snap share {C.SNAP_FIRST}+). Detail in PREDICTIVENESS.txt,")
    P("STABILITY.txt, FANTASY.txt, TEAM.txt.")
    P("=" * 100)

    P("")
    P("1. THE ONE-LINE ANSWER")
    v = pred[pred.kind.isin(("volume", "share", "role"))].r.mean()
    e = pred[pred.kind == "rate"].r.mean()
    P(f"   Averaged over every position and metric, a Week 1 opportunity number carries"
      f" r={v:.2f}")
    P(f"   to the rest of the season. A Week 1 efficiency number carries r={e:.2f}.")
    P(f"   Week 1 tells you about ROLE. It tells you almost nothing about SKILL.")

    P("")
    P("2. THE QUESTIONS THAT STARTED THIS, ANSWERED DIRECTLY")
    P(f"   {'':<58}{'r':>7}{'R2':>7}{'signal':>9}{'g->0.5':>8}")
    P("   " + "-" * 87)
    for pos, m, label in ASKED:
        pr = pred[(pred.position == pos) & (pred.metric == m)]
        st = stab[(stab.position == pos) & (stab.metric == m)]
        if not len(pr):
            continue
        r, r2 = float(pr.r.iloc[0]), float(pr.r2.iloc[0])
        sig = f"{float(st.rel1.iloc[0])*100:>8.0f}%" if len(st) else f"{'--':>9}"
        g50 = f"{float(st.g50.iloc[0]):>8.1f}" if len(st) else f"{'--':>8}"
        P(f"   {pos} {label:<55}{r:>7.3f}{r2:>7.3f}{sig}{g50}")
    P("   r  = correlation of the Week 1 value with the rest of the season")
    P("   signal = share of a single game's spread in that metric that is real, not noise")
    P("   g->0.5 = games of data needed before the metric is half signal")

    P("")
    P("3. IS WEEK 1 SPECIAL, OR IS IT JUST ONE GAME?")
    P("   Running the identical test on weeks 2-9 instead of Week 1:")
    for pos in ("QB", "RB", "WR", "TE"):
        s = pred[pred.position == pos]
        P(f"     {pos}: mean r from Week 1 = {s.r.mean():.3f}, "
          f"mean r from a mid-season week = {s.r_midweek.mean():.3f}"
          f"  (edge to Week 1: {s.w1_edge.mean():+.3f})")
    P(f"   Across all {len(pred)} position-metric pairs the average edge is "
      f"{pred.w1_edge.mean():+.3f}.")
    P("   Week 1 is not a special window into a new season. It is one game, priced as one")
    P("   game. Roster churn and new schemes do not make it more informative than Week 6.")

    P("")
    P("4. HOW LONG BEFORE THE NEW SEASON BEATS THE OLD ONE?")
    P("   Weeks of the current season needed before the running average predicts the back")
    P("   half better than last season's full line does (target = weeks 10 onward):")
    for pos in ("QB", "RB", "WR", "TE"):
        w = weeks_to_match_prior(pos)
        dead = w[w[["prior_r", "best_r"]].max(axis=1) < 0.20]
        w = w[w[["prior_r", "best_r"]].max(axis=1) >= 0.20]
        fast, med = w[w.k == 1], w[(w.k >= 2) & (w.k <= 4)]
        slow = w[(w.k.isna()) | (w.k >= 5)]
        P(f"     {pos}")
        P(f"       Week 1 alone already beats it:  "
          + (", ".join(f"{r.metric} ({r.w1_r:.2f} vs {r.prior_r:.2f})"
                       for _, r in fast.iterrows()) if len(fast) else "none"))
        if len(med):
            P(f"       takes 2-4 weeks:  "
              + ", ".join(f"{r.metric} (k={int(r.k)})" for _, r in med.iterrows()))
        P(f"       last season still wins after 4 weeks:  "
          + (", ".join(f"{r.metric} ({r.w1_r:.2f} vs {r.prior_r:.2f})"
                       for _, r in slow.iterrows()) if len(slow) else "none"))
        if len(dead):
            P(f"       no usable signal from either source:  "
              + ", ".join(dead.metric))

    P("")
    P("5. FANTASY: THE USAGE UNDER THE BOX SCORE BEATS THE BOX SCORE")
    P("   Best single Week 1 predictor of rest-of-season fantasy points per game:")
    for pos in ("QB", "RB", "WR", "TE"):
        r = pd.read_csv(f"out_ranks_{pos}.csv")
        tgt = "ros_fantasy_ppg_ppr" if pos != "QB" else "ros_fantasy_ppg"
        cands = [c for c in r.columns
                 if c.startswith("w1_") and not c.startswith("w1_den_")
                 and not c.endswith(("_bucket", "_rank"))
                 and c not in ("w1_games", "w1_pts")   # constant, and a duplicate of ppg
                 and pd.api.types.is_numeric_dtype(r[c])]
        best = []
        for c in cands:
            d = r[np.isfinite(r[[c, tgt]]).all(axis=1)]
            if len(d) < 200:
                continue
            best.append((abs(np.corrcoef(d[c], d[tgt])[0, 1]), c))
        best.sort(reverse=True)
        P(f"     {pos}: " + ",  ".join(f"{c.replace('w1_','')} r={v:.3f}" for v, c in best[:4]))

    P("")
    P("6. TEAM LEVEL")
    won, lost = team[team.w1_win == 1], team[team.w1_win == 0]
    P(f"   1-0 teams: {won.ros_win.mean()*100:.1f}% win rate the rest of the way, "
      f"{won.playoffs.mean()*100:.0f}% reach the playoffs")
    P(f"   0-1 teams: {lost.ros_win.mean()*100:.1f}% win rate the rest of the way, "
      f"{lost.playoffs.mean()*100:.0f}% reach the playoffs")
    d = team[np.isfinite(team[["w1_margin", "ros_margin"]]).all(axis=1)]
    P(f"   r(Week 1 point margin, rest-of-season margin per game) = "
      f"{np.corrcoef(d.w1_margin, d.ros_margin)[0,1]:.3f}  "
      f"(R2 = {np.corrcoef(d.w1_margin, d.ros_margin)[0,1]**2:.3f})")
    P(f"   The Week 1 win itself is worth about "
      f"{(won.ros_win.mean()-lost.ros_win.mean())*16:.1f} extra wins over the "
      f"remaining schedule --")
    P(f"   most of the 1-0 / 0-1 playoff gap is the game already in the bank, not a")
    P(f"   revealed change in team strength.")

    text = "\n".join(lines) + "\n"
    open("FINDINGS.txt", "w").write(text)
    print(text)


if __name__ == "__main__":
    main()
