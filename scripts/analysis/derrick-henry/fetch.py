"""Pull the nflverse data this study needs and cache it next to this script.

Three sources, all free:
  games.csv        - nflverse/nfldata. Spreads, moneylines, totals, rest, roof.
  NGS rushing      - 2016+ tracking. Expected rush yards, RYOE, box counts.
  play-by-play     - per-carry EPA, success, live win probability, score state.

Play-by-play is downloaded one season at a time, filtered to run plays, then
deleted, so peak disk stays around one season's file instead of eleven.
Everything written here is gitignored.
"""
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
TMP = os.environ.get("NFLVERSE_TMP", "/tmp/nflverse")
REL = "https://github.com/nflverse/nflverse-data/releases/download"
START, END = 2016, 2026

# Enough to rebuild a carry's context without hauling all 372 columns.
PBP_COLS = [
    "game_id", "season", "season_type", "week", "posteam", "defteam",
    "home_team", "away_team", "posteam_type",
    "play_type", "rush_attempt", "qb_scramble", "qb_dropback", "two_point_attempt",
    "down", "ydstogo", "yardline_100", "goal_to_go", "qtr",
    "game_seconds_remaining", "half_seconds_remaining",
    "score_differential", "posteam_score", "defteam_score",
    "wp", "vegas_wp", "epa", "wpa", "yards_gained", "touchdown", "rush_touchdown",
    "first_down_rush", "fumble_lost", "success", "penalty",
    "rusher_player_id", "rusher_player_name", "run_location", "run_gap",
    "shotgun", "no_huddle", "spread_line", "total_line", "result",
]


# All offensive plays (not just runs) + who was on the field for them. The
# down-usage study needs the denominator: snaps his offence ran, by down.
PLAY_COLS = [
    "game_id", "play_id", "season", "season_type", "week", "posteam", "defteam",
    "home_team", "away_team", "play_type", "down", "ydstogo", "yardline_100",
    "goal_to_go", "qtr", "score_differential", "shotgun", "no_huddle",
    "rush_attempt", "pass_attempt", "qb_dropback", "qb_scramble", "sack",
    "two_point_attempt", "penalty", "aborted_play", "epa", "success",
    "yards_gained", "touchdown", "first_down", "special_teams_play",
    "rusher_player_id", "receiver_player_id", "passer_player_id",
    "complete_pass", "interception", "spread_line",
]


def games():
    out = os.path.join(HERE, "games.parquet")
    if os.path.exists(out):
        return pd.read_parquet(out)
    g = pd.read_csv(
        "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv",
        low_memory=False,
    )
    g = g[(g.season >= START) & (g.season <= END)].copy()
    g.to_parquet(out, index=False)
    print(f"games.parquet  {len(g):>6} games {START}-{END}")
    return g


def players():
    out = os.path.join(HERE, "players.parquet")
    if os.path.exists(out):
        return pd.read_parquet(out)
    p = pd.read_parquet(f"{REL}/players/players.parquet")
    keep = [c for c in ["gsis_id", "display_name", "position", "position_group",
                        "rookie_season", "birth_date"] if c in p.columns]
    p = p[keep].dropna(subset=["gsis_id"])
    p.to_parquet(out, index=False)
    print(f"players.parquet  {len(p):>6} players")
    return p


def weekly():
    """stats_player_week: receiving, target share, fantasy points, by game."""
    out = os.path.join(HERE, "weekly.parquet")
    if os.path.exists(out):
        return pd.read_parquet(out)
    frames = []
    for yr in range(START, END + 1):
        w = pd.read_parquet(f"{REL}/stats_player/stats_player_week_{yr}.parquet")
        keep = [c for c in [
            "player_id", "player_display_name", "position", "season", "week",
            "season_type", "game_id", "team", "opponent_team",
            "carries", "rushing_yards", "rushing_tds", "rushing_epa",
            "receptions", "targets", "receiving_yards", "receiving_tds",
            "receiving_air_yards", "receiving_yards_after_catch",
            "receiving_first_downs", "receiving_epa", "target_share",
            "air_yards_share", "wopr", "fantasy_points", "fantasy_points_ppr",
        ] if c in w.columns]
        frames.append(w[keep])
    w = pd.concat(frames, ignore_index=True)
    w.to_parquet(out, index=False)
    print(f"weekly.parquet  {len(w):>6} player-weeks")
    return w


def snaps():
    """Snap counts: the share of his offence he was actually on the field for."""
    out = os.path.join(HERE, "snaps.parquet")
    if os.path.exists(out):
        return pd.read_parquet(out)
    frames = []
    for yr in range(START, END + 1):
        s = pd.read_parquet(f"{REL}/snap_counts/snap_counts_{yr}.parquet")
        frames.append(s[["game_id", "season", "week", "game_type", "player",
                         "position", "team", "offense_snaps", "offense_pct"]])
    s = pd.concat(frames, ignore_index=True)
    s.to_parquet(out, index=False)
    print(f"snaps.parquet  {len(s):>6} player-games")
    return s


def ngs():
    out = os.path.join(HERE, "ngs_rushing.parquet")
    if os.path.exists(out):
        return pd.read_parquet(out)
    n = pd.read_parquet(f"{REL}/nextgen_stats/ngs_rushing.parquet")
    n = n[(n.season >= START) & (n.season <= END)].copy()
    n.to_parquet(out, index=False)
    print(f"ngs_rushing.parquet  {len(n):>6} player-weeks")
    return n


def pbp():
    out = os.path.join(HERE, "runs.parquet")
    if os.path.exists(out):
        return pd.read_parquet(out)
    os.makedirs(TMP, exist_ok=True)
    frames = []
    for yr in range(START, END + 1):
        local = os.path.join(TMP, f"pbp_{yr}.parquet")
        url = f"{REL}/pbp/play_by_play_{yr}.parquet"
        if os.system(f'curl -sL -o "{local}" "{url}"') != 0:
            sys.exit(f"download failed: {url}")
        have = pd.read_parquet(local, columns=None).columns
        df = pd.read_parquet(local, columns=[c for c in PBP_COLS if c in have])
        # Designed runs only: no scrambles, no kneels, no two-point plays.
        df = df[(df.rush_attempt == 1) & (df.qb_scramble != 1)
                & (df.play_type == "run") & (df.two_point_attempt != 1)]
        frames.append(df)
        os.remove(local)
        print(f"  {yr}  {len(df):>6} designed runs")
    r = pd.concat(frames, ignore_index=True)
    r.to_parquet(out, index=False)
    print(f"runs.parquet  {len(r):>7} designed runs {START}-{END}")
    return r


def plays():
    """Every non-special-teams offensive play, for snap denominators by down."""
    out = os.path.join(HERE, "plays.parquet")
    if os.path.exists(out):
        return pd.read_parquet(out)
    os.makedirs(TMP, exist_ok=True)
    frames = []
    for yr in range(START, END + 1):
        local = os.path.join(TMP, f"pbp_{yr}.parquet")
        url = f"{REL}/pbp/play_by_play_{yr}.parquet"
        if os.system(f'curl -sL -o "{local}" "{url}"') != 0:
            sys.exit(f"download failed: {url}")
        have = pd.read_parquet(local, columns=None).columns
        df = pd.read_parquet(local, columns=[c for c in PLAY_COLS if c in have])
        df = df[(df.play_type.isin(["run", "pass"]))
                & (df.special_teams_play != 1) & (df.aborted_play != 1)]
        frames.append(df)
        os.remove(local)
        print(f"  {yr}  {len(df):>6} offensive plays")
    p = pd.concat(frames, ignore_index=True)
    p.to_parquet(out, index=False)
    print(f"plays.parquet  {len(p):>7} offensive plays")
    return p


def presence(peer_ids):
    """Which peer RBs were on the field for each play.

    offense_players is a 22-ish id list per play, so the lists are exploded and
    immediately narrowed to the backs this study compares; keeping them whole
    would be several GB for no gain. Participation stops after 2025.
    """
    out = os.path.join(HERE, "rb_presence.parquet")
    if os.path.exists(out):
        return pd.read_parquet(out)
    frames = []
    for yr in range(START, min(END, 2025) + 1):
        url = f"{REL}/pbp_participation/pbp_participation_{yr}.parquet"
        d = pd.read_parquet(url, columns=["nflverse_game_id", "play_id",
                                          "possession_team", "offense_players",
                                          "defenders_in_box", "offense_personnel"])
        d = d[d.offense_players.notna() & (d.offense_players != "")]
        ex = d.assign(pid=d.offense_players.str.split(";")).explode("pid")
        ex = ex[ex.pid.isin(peer_ids)]
        frames.append(ex[["nflverse_game_id", "play_id", "possession_team",
                          "pid", "defenders_in_box", "offense_personnel"]]
                      .rename(columns={"nflverse_game_id": "game_id"}))
        print(f"  {yr}  {len(frames[-1]):>6} peer-RB snaps")
    r = pd.concat(frames, ignore_index=True)
    r.to_parquet(out, index=False)
    print(f"rb_presence.parquet  {len(r):>7} peer-RB snaps 2016-2025")
    return r


if __name__ == "__main__":
    games(); players(); weekly(); snaps(); ngs()
    runs = pbp()
    plays()
    vol = runs[runs.season_type == "REG"].groupby("rusher_player_id").size()
    presence(set(vol[vol >= 400].index))
