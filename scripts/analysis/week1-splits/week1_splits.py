"""Week 1 team and player splits from nflverse play-by-play.

Five tables, printed as markdown and written to tables/ as CSV:
  1. team_shotgun        - shotgun rate by half, neutral script and overall,
                           with the week's score and result
  2. team_tfl_defense    - tackles for loss forced, per opponent carry
  3. team_tfl_offense    - tackles for loss allowed, per carry
  4. rush_first_downs    - first-down rate per carry, RB/FB, >= 5 carries
  5. target_first_downs  - first-down rate per target, RB/WR, >= 5 targets

Downloads play_by_play_<season>.parquet and the weekly roster (for positions)
into NFLVERSE_TMP and reuses them on later runs.

    python3 week1_splits.py [season] [week]
"""
import os
import subprocess
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
TABLES = os.path.join(HERE, "tables")
TMP = os.environ.get("NFLVERSE_TMP", "/tmp/nflverse")
MIN_CARRIES = 5
MIN_TARGETS = 5


def grab(name, url):
    path = os.path.join(TMP, name)
    if not os.path.exists(path):
        os.makedirs(TMP, exist_ok=True)
        rc = subprocess.run(["curl", "-sSL", "--retry", "4", "--retry-delay", "2",
                             "-o", path, url]).returncode
        if rc != 0:
            sys.exit(f"download failed: {url}")
    return path


def load(season, week):
    pbp = pd.read_parquet(grab(
        f"pbp_{season}.parquet",
        "https://github.com/nflverse/nflverse-data/releases/download/"
        f"pbp/play_by_play_{season}.parquet"))
    pbp = pbp[(pbp.week == week) & (pbp.season_type == "REG")].copy()
    if pbp.empty:
        sys.exit(f"no REG week {week} plays in the {season} file yet")

    ros = pd.read_parquet(grab(
        f"roster_weekly_{season}.parquet",
        "https://github.com/nflverse/nflverse-data/releases/download/"
        f"weekly_rosters/roster_weekly_{season}.parquet"))
    ros = ros[ros.week == week][["gsis_id", "position"]].drop_duplicates("gsis_id")
    return pbp, ros


def results(pbp):
    """One row per team: final score, opponent, and W/L/T for the week."""
    games = (pbp.groupby("game_id")
             .agg(home_team=("home_team", "first"), away_team=("away_team", "first"),
                  home_score=("home_score", "first"), away_score=("away_score", "first"))
             .reset_index())
    rows = []
    for g in games.itertuples(index=False):
        for team, opp, pf, pa in ((g.home_team, g.away_team, g.home_score, g.away_score),
                                  (g.away_team, g.home_team, g.away_score, g.home_score)):
            rows.append({"team": team, "opponent": opp, "points": pf, "points_allowed": pa,
                         "result": "W" if pf > pa else "L" if pf < pa else "T"})
    return pd.DataFrame(rows)


def emit(name, title, df):
    """Print df as markdown under a heading and save it to tables/<name>.csv."""
    os.makedirs(TABLES, exist_ok=True)
    df.to_csv(os.path.join(TABLES, f"{name}.csv"), index=False)
    print(f"\n## {title}\n")
    print("| " + " | ".join(df.columns) + " |")
    print("|" + "|".join("---" for _ in df.columns) + "|")
    for row in df.itertuples(index=False):
        print("| " + " | ".join(str(v) for v in row) + " |")


def pct(s):
    return (s * 100).round(1)


def main(season=2026, week=1):
    pbp, ros = load(season, week)
    tag = f"{season} week {week}"

    # Scrimmage snaps: every pass or rush the offence lined up for, including
    # the ones a penalty wiped out (the formation still happened). Two-point
    # plays are dropped - no down and distance, so no shotgun decision to read.
    snaps = pbp[((pbp["pass"] == 1) | (pbp["rush"] == 1)) & (pbp.two_point_attempt == 0)]

    # Neutral script: one score either way, and not inside the two-minute
    # warning of either half, where the clock dictates the formation. This is
    # the closest thing here to a scheme read; overtime is dropped.
    neutral = snaps[(snaps.score_differential.abs() <= 7)
                    & (snaps.half_seconds_remaining > 120)
                    & (snaps.game_half != "Overtime")]

    def rate(df, label):
        g = df.groupby("posteam").agg(**{f"{label}_snaps": ("shotgun", "size"),
                                         f"{label}_rate": ("shotgun", "mean")})
        g[f"{label}_rate"] = pct(g[f"{label}_rate"])
        return g

    sg = (rate(snaps, "all")
          .join(rate(snaps[snaps.game_half == "Half1"], "h1"))
          .join(rate(snaps[snaps.game_half == "Half2"], "h2"))
          .join(rate(neutral, "neutral")))
    sg["h2_minus_h1"] = (sg.h2_rate - sg.h1_rate).round(1)
    sg = (sg.reset_index().rename(columns={"posteam": "team"})
            .merge(results(pbp), on="team", how="left"))
    emit("team_shotgun", f"Shotgun rate by half, {tag} (offence)",
         sg.sort_values("neutral_rate", ascending=False)
           .astype({"points": int, "points_allowed": int})
           [["team", "h1_snaps", "h1_rate", "h2_snaps", "h2_rate", "h2_minus_h1",
             "neutral_snaps", "neutral_rate", "all_snaps", "all_rate",
             "points", "points_allowed", "result", "opponent"]])

    # nflverse only charges tackled_for_loss on runs - sacks are their own
    # column - so the honest denominator is opponent carries, kneels aside.
    carries = pbp[(pbp.rush_attempt == 1) & (pbp.qb_kneel == 0)]
    d = (carries.groupby("defteam")
         .agg(carries_faced=("tackled_for_loss", "size"), tfl=("tackled_for_loss", "sum")))
    d["tfl_rate"] = pct(d.tfl / d.carries_faced)
    emit("team_tfl_defense", f"Tackle-for-loss rate, {tag} (defence)",
         d.sort_values("tfl_rate", ascending=False).reset_index()
          .astype({"tfl": int}).rename(columns={"defteam": "team"}))

    o = (carries.groupby("posteam")
         .agg(carries=("tackled_for_loss", "size"), tfl_allowed=("tackled_for_loss", "sum")))
    o["tfl_rate_allowed"] = pct(o.tfl_allowed / o.carries)
    emit("team_tfl_offense", f"Tackle-for-loss rate allowed, {tag} (offence)",
         o.sort_values("tfl_rate_allowed").reset_index()
          .astype({"tfl_allowed": int}).rename(columns={"posteam": "team"}))

    # first_down_rush / first_down_pass are 1 when the play moved the chains or
    # scored; first downs handed over by penalty on the play are not counted.
    rush = (carries.groupby(["rusher_player_id", "rusher_player_name", "posteam"])
            .agg(carries=("first_down_rush", "size"),
                 first_downs=("first_down_rush", "sum"),
                 yards=("rushing_yards", "sum"))
            .reset_index()
            .merge(ros, left_on="rusher_player_id", right_on="gsis_id", how="left"))
    rush = rush[(rush.carries >= MIN_CARRIES) & (rush.position.isin(["RB", "FB"]))].copy()
    rush["first_down_rate"] = pct(rush.first_downs / rush.carries)
    emit("rush_first_downs",
         f"First-down rate per carry, {tag} (RB/FB, >= {MIN_CARRIES} carries)",
         rush.sort_values(["first_down_rate", "carries"], ascending=[False, False])
             .astype({"first_downs": int, "yards": int})
             [["rusher_player_name", "posteam", "position", "carries",
               "first_downs", "first_down_rate", "yards"]]
             .rename(columns={"rusher_player_name": "player", "posteam": "team"}))

    # A target is a pass attempt with a charged receiver, so throwaways and
    # sacks are out; every incompletion counts against the rate.
    targets = pbp[(pbp.pass_attempt == 1) & (pbp.two_point_attempt == 0)
                  & (pbp.receiver_player_id.notna())]
    rec = (targets.groupby(["receiver_player_id", "receiver_player_name", "posteam"])
           .agg(targets=("first_down_pass", "size"),
                catches=("complete_pass", "sum"),
                first_downs=("first_down_pass", "sum"),
                yards=("receiving_yards", "sum"))
           .reset_index()
           .merge(ros, left_on="receiver_player_id", right_on="gsis_id", how="left"))
    rec = rec[(rec.targets >= MIN_TARGETS) & (rec.position.isin(["RB", "WR"]))].copy()
    rec["first_down_rate"] = pct(rec.first_downs / rec.targets)
    emit("target_first_downs",
         f"First-down rate per target, {tag} (RB/WR, >= {MIN_TARGETS} targets)",
         rec.sort_values(["first_down_rate", "targets"], ascending=[False, False])
            .astype({"catches": int, "first_downs": int, "yards": int})
            [["receiver_player_name", "posteam", "position", "targets", "catches",
              "first_downs", "first_down_rate", "yards"]]
            .rename(columns={"receiver_player_name": "player", "posteam": "team"}))


if __name__ == "__main__":
    main(*[int(a) for a in sys.argv[1:3]])
