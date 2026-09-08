"""Assemble the point-in-time feature matrix for a week-1 projection.

The one rule this module enforces: a row for season S may only use information
that existed before week 1 of season S kicked off. That means season S-1 and
earlier for anything on-field, the S depth chart and roster, the S week-1
injury report, and the S week-1 betting market. Nothing else.
"""
from __future__ import annotations

import functools

import numpy as np
import pandas as pd

from . import context, ingest, playcaller as pc, scheme, usage
from .config import CACHE, POSITIONS, SCHEME_FIRST_SEASON, TARGET_SEASON
from .scheme import DEF_DIMS, OFF_DIMS


def _team_fix(s):
    return s.replace({"OAK": "LV", "SD": "LAC", "STL": "LA", "LAR": "LA"})


# ---------------------------------------------------------------------------
# Cached heavy pieces
# ---------------------------------------------------------------------------

@functools.lru_cache(maxsize=1)
def fingerprints() -> tuple:
    off_p, def_p = CACHE / "fp_offense.parquet", CACHE / "fp_defense.parquet"
    if off_p.exists() and def_p.exists():
        return pd.read_parquet(off_p), pd.read_parquet(def_p)
    d = scheme.build(range(SCHEME_FIRST_SEASON, TARGET_SEASON))
    d["offense"].to_parquet(off_p)
    d["defense"].to_parquet(def_p)
    return d["offense"], d["defense"]


@functools.lru_cache(maxsize=1)
def all_usage() -> pd.DataFrame:
    p = CACHE / "usage.parquet"
    if p.exists():
        return pd.read_parquet(p)
    u = usage.season_usage(range(2016, TARGET_SEASON))
    u.to_parquet(p)
    return u


@functools.lru_cache(maxsize=1)
def regime_table() -> pd.DataFrame:
    return pc.regimes(SCHEME_FIRST_SEASON - 1, TARGET_SEASON)


@functools.lru_cache(maxsize=8)
def team_environment(season: int) -> pd.DataFrame:
    """Projected team rates for `season`, from last season plus whether the head
    coach changed. Fitted only on seasons before it."""
    from .team_env import TeamEnvironment
    off, _ = fingerprints()
    reg = regime_table()
    m = TeamEnvironment().fit(off, reg, season)
    return m.project(off, reg, season)


@functools.lru_cache(maxsize=8)
def scheme_projection(season: int, side: str) -> pd.DataFrame:
    """Projected scheme vector for every team in `season`, fitted only on
    seasons strictly before it."""
    off, dfn = fingerprints()
    fp = off if side == "off" else dfn
    dims = OFF_DIMS if side == "off" else DEF_DIMS
    proj, model, rep = pc.project(fp, regime_table(), side, dims, season)
    proj = proj.drop(columns=[c for c in ("season",) if c in proj.columns])
    proj = proj.drop(columns=[c for c in proj.columns if c.endswith("_playcaller")])
    proj = proj.rename(columns={c: f"{side}_proj_{c}" for c in dims})
    keep = ["team", "continuity", "caller_prior_seasons", "confidence"]
    proj = proj.rename(columns={k: f"{side}_{k}" for k in keep if k != "team"})
    return proj


# ---------------------------------------------------------------------------
# Point-in-time roster inputs
# ---------------------------------------------------------------------------

def depth_chart_week1(season: int, as_of: str | None = None) -> pd.DataFrame:
    """Offensive depth chart as it stood going into week 1.

    nflverse changed schema in 2025: pre-2025 rows are weekly with a 1/2/3
    depth_team; 2025+ rows are timestamped ESPN snapshots with an explicit
    within-position rank. Both are normalised to (team, player_id, depth_rank).
    """
    d = pd.read_parquet(ingest.fetch("depth_charts", season))
    if "dt" in d.columns:
        d = d.copy()
        d["dt"] = pd.to_datetime(d["dt"], utc=True)
        cutoff = pd.Timestamp(as_of, tz="UTC") if as_of else d["dt"].max()
        d = d[d["dt"] <= cutoff]
        if d.empty:
            return pd.DataFrame(columns=["season", "team", "player_id", "position", "depth_rank"])
        d = d[d["dt"] == d["dt"].max()]
        d = d[d["pos_abb"].isin(["QB", "RB", "WR", "TE", "FB"])]
        out = d.rename(columns={"gsis_id": "player_id", "pos_abb": "position",
                                "pos_rank": "depth_rank"})[
            ["team", "player_id", "position", "depth_rank"]].copy()
    else:
        d = d[(d["week"] == 1) & (d["game_type"] == "REG") & (d["formation"] == "Offense")]
        d = d[d["position"].isin(["QB", "RB", "WR", "TE", "FB"])].copy()
        d["depth_team"] = pd.to_numeric(d["depth_team"], errors="coerce")
        d = d.sort_values(["club_code", "position", "depth_team"])
        d["depth_rank"] = d.groupby(["club_code", "position"]).cumcount() + 1
        out = d.rename(columns={"club_code": "team", "gsis_id": "player_id"})[
            ["team", "player_id", "position", "depth_rank"]]
    out["position"] = out["position"].replace({"FB": "RB"})
    out["team"] = _team_fix(out["team"])
    out["season"] = season
    return out.dropna(subset=["player_id"]).drop_duplicates(["season", "team", "player_id"])


def roster_week1(season: int) -> pd.DataFrame:
    r = pd.read_parquet(ingest.fetch("rosters", season))
    r = r[r["week"] == 1] if "week" in r.columns else r
    r = r[r["position"].isin(["QB", "RB", "WR", "TE", "FB"])].copy()
    r["position"] = r["position"].replace({"FB": "RB"})
    r["team"] = _team_fix(r["team"])
    r["season"] = season
    r["age"] = (pd.Timestamp(f"{season}-09-01") - pd.to_datetime(r["birth_date"], errors="coerce")
                ).dt.days / 365.25
    keep = ["season", "team", "gsis_id", "full_name", "position", "status", "years_exp",
            "age", "entry_year", "draft_number", "draft_club"]
    keep = [c for c in keep if c in r.columns]
    out = r[keep].rename(columns={"gsis_id": "player_id", "full_name": "player_name"})
    out["years_exp"] = pd.to_numeric(out.get("years_exp"), errors="coerce")
    out["draft_number"] = pd.to_numeric(out.get("draft_number"), errors="coerce")
    return out.dropna(subset=["player_id"]).drop_duplicates(["season", "player_id"])


def injuries_week1(season: int) -> pd.DataFrame:
    try:
        inj = pd.read_parquet(ingest.fetch("injuries", season))
    except Exception:
        return pd.DataFrame(columns=["season", "player_id", "report_status"])
    if inj.empty:
        return pd.DataFrame(columns=["season", "player_id", "report_status"])
    inj = inj[(inj["week"] == 1) & (inj["season"] == season)]
    col = "gsis_id" if "gsis_id" in inj.columns else "player_id"
    out = inj[[col, "report_status"]].rename(columns={col: "player_id"})
    out["season"] = season
    return out.dropna(subset=["player_id"]).drop_duplicates(["season", "player_id"])


# ---------------------------------------------------------------------------
# Team-level offseason churn
# ---------------------------------------------------------------------------

def vacated_opportunity(season: int, roster: pd.DataFrame, prev_usage: pd.DataFrame) -> pd.DataFrame:
    """Share of last season's targets / carries / scoring-position work whose
    owner is no longer on the roster. This is the number that actually moves a
    depth chart, and it is fully observable before week 1."""
    here = roster[["team", "player_id"]].assign(on_roster=1)
    prev = prev_usage.merge(here, on=["team", "player_id"], how="left")
    prev["on_roster"] = prev["on_roster"].fillna(0)
    gone = prev[prev["on_roster"] == 0]
    cols = {"target_share": "vacated_target_share", "rush_share": "vacated_rush_share",
            "rz_targets_share": "vacated_rz_target_share",
            "gl_carries_share": "vacated_gl_carry_share",
            "air_yards_share": "vacated_air_yards_share"}
    out = gone.groupby("team")[list(cols)].sum().rename(columns=cols).reset_index()
    out["season"] = season
    return out


# ---------------------------------------------------------------------------
# Row assembly
# ---------------------------------------------------------------------------

SHARE_COLS = ["target_share", "rush_share", "air_yards_share", "wopr", "snap_share",
              "rz_targets_share", "gl_carries_share", "third_down_targets_share",
              "rz_carries_share", "targets_per_snap_share", "gl_qb_rushes_share"]
RATE_COLS = ["yards_per_target", "catch_rate", "adot", "yac_per_rec", "yards_per_carry",
             "rec_td_rate", "rush_td_rate", "ypa", "pass_td_rate", "int_rate", "sack_rate"]
VOL_COLS = ["targets_per_game", "carries_per_game", "attempts_per_game", "ppg_ppr", "games"]


def _collapse_stints(u: pd.DataFrame) -> pd.DataFrame:
    """One row per player-season.

    A player traded mid-season has a row per team, and joining on player_id
    alone then duplicates him in the output -- Jakobi Meyers appeared twice in
    the same WR list before this. Counting stats are summed across stints;
    shares and rates, which are team-relative, are averaged weighted by games;
    the team recorded is the stint he played most.
    """
    if u.empty:
        return u
    u = u.sort_values(["player_id", "games"])
    counting = ["targets", "receptions", "receiving_yards", "receiving_tds",
                "receiving_air_yards", "receiving_yards_after_catch", "carries",
                "rushing_yards", "rushing_tds", "attempts", "completions",
                "passing_yards", "passing_tds", "passing_interceptions",
                "sacks_suffered", "passing_air_yards", "fantasy_points_ppr", "games",
                "rz_targets", "gl_carries", "third_down_targets", "rz_carries",
                "gl_qb_rushes", "offense_snaps"]
    counting = [c for c in counting if c in u.columns]
    keys = ["player_id"]
    grouped = u.groupby(keys, sort=False)
    out = grouped[counting].sum()

    weight_cols = [c for c in u.columns
                   if c not in counting + keys + ["season", "team", "player_key"]
                   and pd.api.types.is_numeric_dtype(u[c])]
    w = u["games"].clip(lower=0.5)
    for c in weight_cols:
        num = (u[c].fillna(0) * w).groupby(u["player_id"]).sum()
        den = (u[c].notna() * w).groupby(u["player_id"]).sum().replace(0, np.nan)
        out[c] = num / den
    last = grouped.tail(1).set_index("player_id")
    for c in ["team", "position", "player_display_name", "season"]:
        if c in last.columns:
            out[c] = last[c]
    out["n_stints"] = grouped.size()
    return out.reset_index()


def _prior_usage(season: int) -> pd.DataFrame:
    """Player usage from S-1 and S-2, with S-1 shares empirically shrunk."""
    u = all_usage()
    p1 = _collapse_stints(u[u["season"] == season - 1].copy())
    p2 = _collapse_stints(u[u["season"] == season - 2].copy())

    for c in SHARE_COLS:
        if c in ("targets_per_snap_share",):
            continue
        weight = p1["targets"] if "target" in c else p1["carries"]
        weight = weight.where(weight > 0, p1[["targets", "carries"]].sum(axis=1))
        p1[f"{c}_eb"] = usage.eb_shrink(p1[c], weight, p1["position"])
    for c in RATE_COLS:
        weight = p1["targets"] if c in ("yards_per_target", "catch_rate", "adot", "rec_td_rate") \
            else p1["carries"] if c in ("yards_per_carry", "rush_td_rate") else p1["attempts"]
        p1[f"{c}_eb"] = usage.eb_shrink(p1[c], weight, p1["position"], prior_strength=None)

    keep1 = ["player_id", "team", "position", "player_display_name"] + SHARE_COLS + RATE_COLS + VOL_COLS \
        + [f"{c}_eb" for c in SHARE_COLS if c != "targets_per_snap_share"] \
        + [f"{c}_eb" for c in RATE_COLS]
    p1 = p1[[c for c in keep1 if c in p1.columns]].rename(columns={"team": "prev_team"})
    p2 = p2[["player_id"] + SHARE_COLS + VOL_COLS].add_suffix("_y2").rename(
        columns={"player_id_y2": "player_id"})
    return p1.merge(p2, on="player_id", how="left")


def build_rows(season: int, as_of: str | None = None) -> pd.DataFrame:
    """One row per (player, week 1 of `season`) with features only."""
    roster = roster_week1(season)
    depth = depth_chart_week1(season, as_of=as_of)
    prior = _prior_usage(season)
    u_prev = all_usage()
    u_prev = u_prev[u_prev["season"] == season - 1]

    df = roster.merge(depth[["team", "player_id", "depth_rank"]], on=["team", "player_id"],
                      how="outer")
    df["season"] = season
    prior = prior.drop_duplicates("player_id")
    df = df.merge(prior, on="player_id", how="left", suffixes=("", "_prev"))
    df["position"] = df["position"].fillna(df["position_prev"]) if "position_prev" in df else df["position"]
    df = df.dropna(subset=["position", "team"])
    df = df.drop_duplicates(["season", "player_id", "team"])
    df = df[df["position"].isin(POSITIONS)]

    df["changed_team"] = (df["prev_team"].notna() & (df["prev_team"] != df["team"])).astype(float)
    df["is_rookie"] = (df["years_exp"].fillna(0) == 0).astype(float)
    df["no_prior_season"] = df["target_share"].isna() & df["carries_per_game"].isna() \
        & df["attempts_per_game"].isna()
    df["no_prior_season"] = df["no_prior_season"].astype(float)
    df["draft_pick"] = df["draft_number"].fillna(300)
    df["log_draft_pick"] = np.log(df["draft_pick"])
    df["depth_rank"] = df["depth_rank"].fillna(9)

    # Team environment: projected scheme, last year's raw team rates, churn.
    off_proj = scheme_projection(season, "off")
    def_proj = scheme_projection(season, "def")
    df = df.merge(off_proj, on="team", how="left")
    df = df.merge(team_environment(season), on="team", how="left")

    off_fp, def_fp = fingerprints()
    lag_off = off_fp[off_fp["season"] == season - 1].drop(columns=["season"]).add_prefix("team_prev_")
    df = df.merge(lag_off.rename(columns={"team_prev_team": "team"}), on="team", how="left")

    vac = vacated_opportunity(season, roster, u_prev)
    df = df.merge(vac.drop(columns=["season"]), on="team", how="left")

    reg = regime_table()
    reg_s = reg[reg["season"] == season][["team", "off_continuity", "def_continuity",
                                          "hc_continuity", "off_confidence"]]
    df = df.merge(reg_s, on="team", how="left", suffixes=("", "_reg"))

    # Opponent and market.
    tw = context.team_week([season])
    tw = tw[tw["week"] == 1]
    df = df.merge(tw[["team", "opponent", "is_home", "team_spread", "total_line",
                      "implied_team_total", "implied_opp_total", "abs_spread",
                      "is_dome", "is_favourite", "rest", "div_game", "game_id"]],
                  on="team", how="left")
    dp = def_proj.rename(columns={"team": "opponent"})
    dp = dp.rename(columns={c: f"opp_{c}" for c in dp.columns if c != "opponent"})
    df = df.merge(dp, on="opponent", how="left")
    lag_def = def_fp[def_fp["season"] == season - 1].drop(columns=["season"]).add_prefix("opp_prev_")
    df = df.merge(lag_def.rename(columns={"opp_prev_team": "opponent"}), on="opponent", how="left")

    opp_hc = regime_table()
    opp_hc = opp_hc[opp_hc["season"] == season][["team", "hc_continuity"]].rename(
        columns={"team": "opponent", "hc_continuity": "opp_hc_continuity"})
    df = df.merge(opp_hc, on="opponent", how="left")
    df["opp_hc_change"] = (df["opp_hc_continuity"] == 0).astype(float)

    inj = injuries_week1(season)
    df = df.merge(inj[["player_id", "report_status"]], on="player_id", how="left")
    df["is_out"] = df["report_status"].isin(["Out", "Doubtful"]).astype(float)
    df["is_questionable"] = (df["report_status"] == "Questionable").astype(float)

    df["player_name"] = df["player_name"].fillna(df.get("player_display_name"))
    df = _expected_opportunity(df, season)
    return df


# ---------------------------------------------------------------------------
# The opportunity stage, made explicit
# ---------------------------------------------------------------------------

def _raw_scale(season: int, side: str, dims) -> pd.DataFrame:
    """League mean and sd of each dimension in the season before the one we are
    projecting. Scheme projections live in z-space; this puts them back into
    plays, pass rates and target shares so they can be multiplied by a player's
    share."""
    off, dfn = fingerprints()
    fp = (off if side == "off" else dfn)
    prev = fp[fp["season"] == season - 1]
    return pd.DataFrame({"mean": prev[list(dims)].mean(), "sd": prev[list(dims)].std()})


def _expected_opportunity(df: pd.DataFrame, season: int) -> pd.DataFrame:
    """Turn scheme projections plus player shares into expected volume.

    This is the whole thesis of the model in four lines: a player's fantasy
    week is his share of his team's work, times how much work his team is
    projected to have. Handing the learner the product directly -- rather than
    hoping it discovers the interaction from a thousand rows -- is the
    difference between a volume model and a pile of correlated features.
    """
    scale = _raw_scale(season, "off", OFF_DIMS)

    def raw(dim, default):
        """Projected team rate in real units.

        Prefers the reduced head-coach-aware projection (last season's measured
        rate, discounted when the head coach changed). Falls back to the
        z-scored carryover projection only if the reduced one is missing.
        """
        env = df.get(f"env_{dim}")
        if env is not None and env.notna().any():
            return env.fillna(env.mean() if np.isfinite(env.mean()) else default)
        z = df.get(f"off_proj_{dim}")
        if z is None:
            return pd.Series(default, index=df.index)
        m, sd = scale.loc[dim, "mean"], scale.loc[dim, "sd"]
        return (z * sd + m).fillna(m)

    plays = raw("plays_per_game", 62.0).clip(50, 75)
    pass_rate = raw("neutral_pass_rate", 0.58).clip(0.40, 0.75)

    # Game script: favourites throw less and run more, underdogs the reverse.
    # One point of spread is worth roughly a third of a percent of pass rate.
    script = (df["team_spread"].fillna(0) * 0.0035).clip(-0.06, 0.06)
    pass_rate = (pass_rate + script).clip(0.38, 0.78)

    df["proj_team_plays"] = plays
    df["proj_team_pass_att"] = plays * pass_rate
    df["proj_team_rush_att"] = plays * (1 - pass_rate)
    # Scoring-position volume scales with the implied team total.
    itt = df["implied_team_total"].fillna(22.0)
    df["proj_team_rz_plays"] = 3.2 * (itt / 22.0)
    df["proj_team_gl_plays"] = 1.35 * (itt / 22.0)

    df["expected_targets"] = df["target_share_eb"].fillna(0) * df["proj_team_pass_att"]
    df["expected_carries"] = df["rush_share_eb"].fillna(0) * df["proj_team_rush_att"]
    df["expected_rz_targets"] = df["rz_targets_share_eb"].fillna(0) * df["proj_team_rz_plays"]
    df["expected_gl_carries"] = df["gl_carries_share_eb"].fillna(0) * df["proj_team_gl_plays"]
    df["expected_pass_att"] = df["attempts_per_game"].fillna(0) * (plays / 62.0)

    df["expected_rec_yards"] = df["expected_targets"] * df["yards_per_target_eb"].fillna(7.6)
    df["expected_rush_yards"] = df["expected_carries"] * df["yards_per_carry_eb"].fillna(4.2)
    df["expected_receptions"] = df["expected_targets"] * df["catch_rate_eb"].fillna(0.65)
    df["expected_pass_yards"] = df["expected_pass_att"] * df["ypa_eb"].fillna(7.0)

    # Touchdown equity comes from scoring-position opportunity, never from last
    # season's touchdown count, which is the noisiest number in fantasy.
    df["expected_rec_td"] = df["expected_rz_targets"] * 0.20 + df["expected_targets"] * 0.015
    df["expected_rush_td"] = df["expected_gl_carries"] * 0.42 + df["expected_carries"] * 0.008
    df["expected_pass_td"] = df["expected_pass_att"] * 0.048 * (itt / 22.0)

    df["naive_points_ppr"] = (
        df["expected_rec_yards"] * 0.1 + df["expected_receptions"] + df["expected_rec_td"] * 6
        + df["expected_rush_yards"] * 0.1 + df["expected_rush_td"] * 6
        + df["expected_pass_yards"] * 0.04 + df["expected_pass_td"] * 4)
    return df


def attach_targets(rows: pd.DataFrame, scoring_names) -> pd.DataFrame:
    """Join the actual week-1 outcome for supervised training/backtesting."""
    from .scoring import fantasy_points
    seasons = sorted(rows["season"].unique())
    s = ingest.load("stats_player", seasons)
    if s.empty or "season_type" not in s.columns:
        # The season has not kicked off yet: no outcomes to attach.
        for n in scoring_names:
            rows[f"actual_{n}"] = np.nan
        rows["played_week1"] = np.nan
        return rows
    s = s[(s["season_type"] == "REG") & (s["week"] == 1)].copy()
    for name in scoring_names:
        s[f"actual_{name}"] = fantasy_points(s, name)
    cols = ["season", "player_id"] + [f"actual_{n}" for n in scoring_names]
    out = rows.merge(s[cols], on=["season", "player_id"], how="left")
    for n in scoring_names:
        # A rostered player who did not record a stat line scored zero, and a
        # ranking model should be punished for ranking him highly.
        out[f"actual_{n}"] = out[f"actual_{n}"].fillna(0.0)
    out["played_week1"] = out["player_id"].isin(set(s["player_id"])).astype(float)
    return out
