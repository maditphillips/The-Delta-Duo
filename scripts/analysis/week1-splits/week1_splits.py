"""Week 1 team and back splits from nflverse play-by-play.

Three tables, printed as markdown:
  1. offense  - shotgun rate (share of scrimmage snaps out of shotgun)
  2. defense  - tackle-for-loss rate (TFL forced per opponent carry)
  3. backs    - first-down rate per carry, running backs with >= 5 carries

Downloads play_by_play_<season>.parquet and the weekly roster (for positions)
into NFLVERSE_TMP and reuses them on later runs.

    python3 week1_splits.py [season] [week]
"""
import os
import subprocess
import sys

import pandas as pd

TMP = os.environ.get("NFLVERSE_TMP", "/tmp/nflverse")
MIN_CARRIES = 5


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
    ros = ros[ros.week == week][["gsis_id", "position", "full_name"]].drop_duplicates("gsis_id")
    return pbp, ros


def markdown(df, headers):
    lines = ["| " + " | ".join(headers) + " |",
             "|" + "|".join("---" for _ in headers) + "|"]
    for row in df.itertuples(index=False):
        lines.append("| " + " | ".join(str(v) for v in row) + " |")
    return "\n".join(lines)


def main(season=2026, week=1):
    pbp, ros = load(season, week)

    # Scrimmage snaps: every pass or rush the offence lined up for, including
    # the ones a penalty wiped out (the formation still happened). Two-point
    # plays are dropped - no down and distance, so no shotgun decision to read.
    snaps = pbp[((pbp["pass"] == 1) | (pbp["rush"] == 1)) & (pbp.two_point_attempt == 0)]

    shotgun = (snaps.groupby("posteam")
               .agg(snaps=("shotgun", "size"), shotgun=("shotgun", "sum")))
    shotgun["rate"] = shotgun.shotgun / shotgun.snaps
    shotgun = shotgun.sort_values("rate", ascending=False).reset_index()
    print(f"\n## Shotgun rate, {season} week {week} (offence)\n")
    print(markdown(pd.DataFrame({
        "Team": shotgun.posteam,
        "Snaps": shotgun.snaps,
        "Shotgun": shotgun.shotgun.astype(int),
        "Rate": (shotgun.rate * 100).round(1).astype(str) + "%",
    }), ["Team", "Snaps", "Shotgun", "Rate"]))

    # nflverse only charges tackled_for_loss on runs - sacks are their own
    # column - so the honest denominator is opponent carries, kneels aside.
    carries = pbp[(pbp.rush_attempt == 1) & (pbp.qb_kneel == 0)]
    tfl = (carries.groupby("defteam")
           .agg(carries_faced=("tackled_for_loss", "size"),
                tfl=("tackled_for_loss", "sum")))
    tfl["rate"] = tfl.tfl / tfl.carries_faced
    tfl = tfl.sort_values("rate", ascending=False).reset_index()
    print(f"\n## Tackle-for-loss rate, {season} week {week} (defence)\n")
    print(markdown(pd.DataFrame({
        "Team": tfl.defteam,
        "Carries faced": tfl.carries_faced,
        "TFL": tfl.tfl.astype(int),
        "Rate": (tfl.rate * 100).round(1).astype(str) + "%",
    }), ["Team", "Carries faced", "TFL", "Rate"]))

    allowed = (carries.groupby("posteam")
               .agg(carries=("tackled_for_loss", "size"),
                    tfl=("tackled_for_loss", "sum")))
    allowed["rate"] = allowed.tfl / allowed.carries
    allowed = allowed.sort_values("rate").reset_index()
    print(f"\n## Tackle-for-loss rate allowed, {season} week {week} (offence)\n")
    print(markdown(pd.DataFrame({
        "Team": allowed.posteam,
        "Carries": allowed.carries,
        "TFL allowed": allowed.tfl.astype(int),
        "Rate": (allowed.rate * 100).round(1).astype(str) + "%",
    }), ["Team", "Carries", "TFL allowed", "Rate"]))

    # first_down_rush is 1 when the carry moved the chains or scored; it leaves
    # out first downs handed over by an offsetting penalty on the same play.
    backs = (carries.groupby(["rusher_player_id", "rusher_player_name", "posteam"])
             .agg(carries=("first_down_rush", "size"),
                  first_downs=("first_down_rush", "sum"),
                  yards=("rushing_yards", "sum"))
             .reset_index()
             .merge(ros, left_on="rusher_player_id", right_on="gsis_id", how="left"))
    backs = backs[(backs.carries >= MIN_CARRIES) & (backs.position.isin(["RB", "FB"]))]
    backs["rate"] = backs.first_downs / backs.carries
    backs = backs.sort_values(["rate", "carries"], ascending=[False, False]).reset_index()
    print(f"\n## First-down rate per carry, {season} week {week} "
          f"(RB/FB, >= {MIN_CARRIES} carries)\n")
    print(markdown(pd.DataFrame({
        "Player": backs.rusher_player_name,
        "Team": backs.posteam,
        "Carries": backs.carries,
        "First downs": backs.first_downs.astype(int),
        "Rate": (backs.rate * 100).round(1).astype(str) + "%",
        "Yards": backs.yards.astype(int),
    }), ["Player", "Team", "Carries", "First downs", "Rate", "Yards"]))


if __name__ == "__main__":
    args = [int(a) for a in sys.argv[1:3]]
    main(*args)
