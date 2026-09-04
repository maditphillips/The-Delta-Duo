"""Season-level wide receiver panel with next-season outcomes.

Importable: `from panel import build; df = build()`. Run directly to print a
summary and write wr_panel.csv (gitignored) for eyeballing.

One row per WR-season 2000-2025. Everything a fantasy manager could have known
on the morning after season N sits on the same row as what happened in season
N+1, so no feature ever peeks forward.

Caveat worth knowing before using this: nflverse carries no target or air-yards
data for 2003-2008, so every volume and efficiency column is empty in those
seasons. Points, receptions, yards, touchdowns and therefore finishes are fine
throughout, which is why the panel still starts in 2000 - career history for a
player who debuted in 2005 is correct even though his 2005 target count is not.
The analysis sample in horse_race.py starts at 2009 for that reason.
"""
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SPIKE = 20.0   # PPR points that make a game a "spike"
DUD = 8.0      # PPR points at or below which a game is a "quiet" one


def _load():
    wk = pd.read_parquet(f"{HERE}/wr_weeks.parquet")
    tg = pd.read_parquet(f"{HERE}/team_games.parquet")
    pl = pd.read_parquet(f"{HERE}/players.parquet")
    return wk, tg, pl


def _weekly_shape(g):
    """Spike/quiet structure of one player-season's weekly scores."""
    pts = np.sort(g.fantasy_points_ppr.to_numpy(dtype=float))[::-1]
    total = pts.sum()
    n = len(pts)
    # Gini of the weekly scores: 0 = every week identical, 1 = one week is the
    # whole season. Unlike a "top 5 games" share it does not drift with games
    # played, so it is safe to pool 8-game and 17-game seasons in a regression.
    asc = pts[::-1]
    gini = ((2 * np.arange(1, n + 1) - n - 1) * asc).sum() / (n * total) if total > 0 else np.nan
    return pd.Series({
        "gini": gini,
        "games": n,
        "ppr": total,
        "top5_pts": pts[:5].sum(),
        "top5_share": pts[:5].sum() / total if total > 0 else np.nan,
        "spike_games": int((pts >= SPIKE).sum()),
        "quiet_games": int((pts <= DUD).sum()),
        "week_sd": pts.std(ddof=1) if n > 1 else np.nan,
        "median_week": float(np.median(pts)),
    })


def build():
    wk, tg, pl = _load()
    wk = wk.copy()
    wk["fantasy_points_ppr"] = wk.fantasy_points_ppr.fillna(0.0)

    shape = wk.groupby(["season", "player_id"], sort=False).apply(
        _weekly_shape, include_groups=False
    ).reset_index()

    sums = wk.groupby(["season", "player_id"], sort=False).agg(
        player=("player_display_name", "last"),
        team=("team", "last"),
        n_teams=("team", "nunique"),
        targets=("targets", "sum"),
        receptions=("receptions", "sum"),
        rec_yards=("receiving_yards", "sum"),
        rec_tds=("receiving_tds", "sum"),
        air_yards=("receiving_air_yards", "sum"),
        yac=("receiving_yards_after_catch", "sum"),
        first_downs=("receiving_first_downs", "sum"),
        rec_epa=("receiving_epa", "sum"),
        carries=("carries", "sum"),
        rush_yards=("rushing_yards", "sum"),
        target_share=("target_share", "mean"),
        air_yards_share=("air_yards_share", "mean"),
        wopr=("wopr", "mean"),
    ).reset_index()

    df = shape.merge(sums, on=["season", "player_id"])

    # Games the player's team actually played, so absence is measured properly.
    team_games = tg.groupby(["season", "team"]).week.nunique().rename("team_games").reset_index()
    df = df.merge(team_games, on=["season", "team"], how="left")
    df["team_games"] = df.team_games.fillna(df.season.map(lambda s: 17 if s >= 2021 else 16))
    df["missed"] = (df.team_games - df.games).clip(lower=0)

    # --- rate stats -------------------------------------------------------
    df["ppg"] = df.ppr / df.games
    df["tpg"] = df.targets / df.games
    df["ypt"] = df.rec_yards / df.targets.replace(0, np.nan)
    df["catch_pct"] = df.receptions / df.targets.replace(0, np.nan)
    df["ppr_per_target"] = df.ppr / df.targets.replace(0, np.nan)
    df["yac_per_rec"] = df.yac / df.receptions.replace(0, np.nan)
    df["racr"] = df.rec_yards / df.air_yards.replace(0, np.nan)
    df["fd_per_target"] = df.first_downs / df.targets.replace(0, np.nan)
    df["epa_per_target"] = df.rec_epa / df.targets.replace(0, np.nan)
    df["td_per_target"] = df.rec_tds / df.targets.replace(0, np.nan)
    df["adot"] = df.air_yards / df.targets.replace(0, np.nan)
    df["boom_rate"] = df.spike_games / df.games
    df["quiet_rate"] = df.quiet_games / df.games
    df["week_cv"] = df.week_sd / df.ppg.replace(0, np.nan)

    # --- finishes ---------------------------------------------------------
    df["finish"] = df.groupby("season").ppr.rank(ascending=False, method="min")
    # What the season would have ranked at the same per-game pace over a full
    # slate: the "had he not been hurt" counterfactual, ranked inside its year.
    # Every receiver in the season is projected the same way, so the pool stays
    # the same size as the real one; under 4 games there is no rate worth
    # extrapolating, so those keep their actual points.
    df["pace_points"] = np.where(df.games >= 4, df.ppg * df.team_games, df.ppr)
    df["pace_finish"] = df.groupby("season").pace_points.rank(ascending=False, method="min")

    df = df.sort_values(["player_id", "season"]).reset_index(drop=True)

    # --- career history to date (strictly prior seasons) ------------------
    g = df.groupby("player_id", sort=False)
    df["prior_seasons"] = g.cumcount()
    df["best_prior_finish"] = g.finish.transform(lambda s: s.shift().cummin())
    df["prev_finish"] = g.finish.shift()
    df["prev_ppg"] = g.ppg.shift()
    df["prev_games"] = g.games.shift()
    df["prev_targets"] = g.targets.shift()
    df["prior_top12"] = g.finish.transform(lambda s: (s.shift() <= 12).cumsum())
    df["prior_top24"] = g.finish.transform(lambda s: (s.shift() <= 24).cumsum())
    df["prior_ppr"] = g.ppr.transform(lambda s: s.shift().cumsum())

    # --- age, experience, draft slot --------------------------------------
    pl = pl.rename(columns={"gsis_id": "player_id"})
    df = df.merge(
        pl[["player_id", "birth_date", "draft_number", "rookie_year", "entry_year",
            "first_roster_season", "draft_round", "draft_pick"]],
        on="player_id", how="left",
    )
    rookie = df.rookie_year.fillna(df.entry_year).fillna(df.first_roster_season)
    # Last resort: the first season the player shows up in this panel.
    rookie = rookie.fillna(df.groupby("player_id").season.transform("min"))
    df["rookie_year"] = rookie
    df["exp"] = df.season - df.rookie_year + 1
    df.loc[(df.exp < 1) | (df.exp > 22), "exp"] = np.nan
    bd = pd.to_datetime(df.birth_date, errors="coerce")
    df["age"] = (pd.to_datetime(df.season.astype(str) + "-09-01") - bd).dt.days / 365.25
    df["draft_pick"] = df.draft_pick.fillna(df.draft_number)

    # --- teammate context --------------------------------------------------
    # Two things about the room he plays in: the best of the other receivers on
    # his team, and separately the best of the YOUNG ones - a first- or
    # second-year teammate coming off a strong finish is the specific worry.
    tm = df[["season", "team", "player_id", "finish", "exp", "targets"]].copy()
    rows = []
    for (yr, _), grp in tm.groupby(["season", "team"], sort=False):
        grp = grp.sort_values("finish")
        for pid in grp.player_id:
            others = grp[grp.player_id != pid]
            young = others[others.exp <= 2]
            rows.append((
                yr, pid,
                others.finish.iloc[0] if len(others) else np.nan,
                others.exp.iloc[0] if len(others) else np.nan,
                others.targets.iloc[0] if len(others) else np.nan,
                young.finish.iloc[0] if len(young) else np.nan,
            ))
    tmate = pd.DataFrame(rows, columns=["season", "player_id", "mate_finish", "mate_exp",
                                        "mate_targets", "young_mate_finish"])
    df = df.merge(tmate, on=["season", "player_id"], how="left")
    df["mate_is_younger"] = (df.mate_exp < df.exp).astype(float)
    df["mate_threat"] = (df.young_mate_finish <= 36).astype(float)

    # --- next-season outcomes ---------------------------------------------
    nxt = df[["player_id", "season", "finish", "ppg", "ppr", "games", "targets",
              "pace_finish", "team"]].copy()
    nxt["season"] = nxt.season - 1
    nxt = nxt.rename(columns={
        "finish": "next_finish", "ppg": "next_ppg", "ppr": "next_ppr",
        "games": "next_games", "targets": "next_targets",
        "pace_finish": "next_pace_finish", "team": "next_team",
    })
    df = df.merge(nxt, on=["player_id", "season"], how="left")

    last_season = int(df.season.max())
    df["has_next"] = df.season < last_season
    # A receiver with no season N+1 line did not play: that is a fantasy
    # outcome, not missing data. Censor at the bottom of the pool.
    pool = df.groupby("season").player_id.nunique().median()
    df["next_finish_c"] = df.next_finish.where(
        df.next_finish.notna(), float(pool) + 1
    ).where(df.has_next)
    df["next_ppg_c"] = df.next_ppg.fillna(0.0).where(df.has_next)
    df["next_top12"] = (df.next_finish_c <= 12).astype(float).where(df.has_next)
    df["next_top24"] = (df.next_finish_c <= 24).astype(float).where(df.has_next)
    df["next_top36"] = (df.next_finish_c <= 36).astype(float).where(df.has_next)
    df["next_moved"] = (df.next_team != df.team).astype(float).where(df.next_team.notna())

    return df


if __name__ == "__main__":
    d = build()
    d.to_csv(f"{HERE}/wr_panel.csv", index=False)
    print(f"{len(d):,} WR-seasons, {d.player_id.nunique():,} receivers, "
          f"{d.season.min()}-{d.season.max()}")
    fed = d[(d.games >= 8) & (d.targets >= 50)]
    print(f"{len(fed):,} seasons with 8+ games and 50+ targets")
    print(d.groupby("season").size().describe()[["min", "50%", "max"]])
    print(d[d.finish <= 12].groupby("season").ppr.min().tail(6))
