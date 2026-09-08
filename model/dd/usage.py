"""Player usage: the opportunity layer.

The studies in src/data all point the same way -- per-opportunity efficiency is
close to flat among players who earn a role, and volume is what separates
fantasy outcomes. So this module measures opportunity carefully (shares,
snap rate, scoring-position work) and treats efficiency as a lightly-held
secondary term that gets shrunk hard later.

Everything here is season-level and strictly historical. Point-in-time
discipline is enforced by the caller: features for season S use season S-1.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import ingest
from .scheme import PBP_COLS

SKILL = ("QB", "RB", "WR", "TE", "FB")


def _team_fix(s: pd.Series) -> pd.Series:
    return s.replace({"OAK": "LV", "SD": "LAC", "STL": "LA", "LAR": "LA"})


def weekly_stats(seasons) -> pd.DataFrame:
    s = ingest.load("stats_player", seasons)
    s = s[(s["season_type"] == "REG") & (s["position"].isin(SKILL))].copy()
    s["position"] = s["position"].replace({"FB": "RB"})
    s["team"] = _team_fix(s["team"])
    s["opponent_team"] = _team_fix(s["opponent_team"])
    return s


def snap_shares(seasons) -> pd.DataFrame:
    """Season-level snap share. nflverse snap counts are PFR-sourced and keyed
    by pfr_player_id, so they are joined on name+team+season rather than gsis."""
    sn = ingest.load("snap_counts", seasons)
    sn = sn[sn["game_type"] == "REG"].copy()
    sn["team"] = _team_fix(sn["team"])
    sn = sn[sn["position"].isin(SKILL)]
    g = sn.groupby(["season", "team", "player", "position"])
    out = g.agg(snap_games=("offense_snaps", lambda s: int((s > 0).sum())),
                offense_snaps=("offense_snaps", "sum"),
                snap_share=("offense_pct", "mean"),
                snap_share_max=("offense_pct", "max")).reset_index()
    out["player_key"] = out["player"].str.lower().str.replace(r"[^a-z]", "", regex=True)
    return out


def _pbp_opportunity(seasons) -> pd.DataFrame:
    """Scoring-position and passing-down opportunity, straight from play-by-play.

    Snap-level personnel data (which would give true down-split participation,
    the way the RB third-down study measured it) was pulled from nflverse when
    NGS stopped publishing it. Third-down *target rate* is the closest
    observable proxy and is what we use.
    """
    cols = ["season", "posteam", "down", "yardline_100", "pass", "rush", "play_type",
            "receiver_player_id", "rusher_player_id", "passer_player_id", "season_type",
            "special", "aborted_play", "play_deleted", "qb_scramble", "ydstogo", "touchdown"]
    p = ingest.load("pbp", seasons, columns=cols)
    p = p[(p["season_type"] == "REG") & (p["play_deleted"] != 1) & (p["special"] != 1)
          & (p["aborted_play"] != 1) & (p["play_type"].isin(["pass", "run"]))].copy()
    p["posteam"] = _team_fix(p["posteam"])
    p["is_pass"] = p["pass"].fillna(0)
    p["is_rush"] = p["rush"].fillna(0)

    def _share(sub, id_col, name, denom_mask=None):
        num = sub.groupby(["season", "posteam", id_col]).size().rename(name).reset_index()
        num = num.rename(columns={id_col: "player_id"})
        den = sub.groupby(["season", "posteam"]).size().rename(f"team_{name}").reset_index()
        return num.merge(den, on=["season", "posteam"], how="left")

    frames = []
    rz = p[(p["yardline_100"] <= 20) & (p["is_pass"] == 1) & p["receiver_player_id"].notna()]
    frames.append(_share(rz, "receiver_player_id", "rz_targets"))
    gl = p[(p["yardline_100"] <= 5) & (p["is_rush"] == 1) & p["rusher_player_id"].notna()]
    frames.append(_share(gl, "rusher_player_id", "gl_carries"))
    third = p[(p["down"] == 3) & (p["is_pass"] == 1) & p["receiver_player_id"].notna()]
    frames.append(_share(third, "receiver_player_id", "third_down_targets"))
    rzr = p[(p["yardline_100"] <= 20) & (p["is_rush"] == 1) & p["rusher_player_id"].notna()]
    frames.append(_share(rzr, "rusher_player_id", "rz_carries"))
    qbr = p[(p["is_rush"] == 1) & (p["qb_scramble"] != 1) & p["rusher_player_id"].notna()
            & (p["yardline_100"] <= 5)]
    frames.append(_share(qbr, "rusher_player_id", "gl_qb_rushes"))

    out = frames[0]
    for f in frames[1:]:
        out = out.merge(f, on=["season", "posteam", "player_id"], how="outer")
    return out.rename(columns={"posteam": "team"})


def season_usage(seasons) -> pd.DataFrame:
    """One row per player-season: volume, shares, and lightly-held efficiency."""
    w = weekly_stats(seasons)
    num = ["targets", "receptions", "receiving_yards", "receiving_tds", "receiving_air_yards",
           "receiving_yards_after_catch", "carries", "rushing_yards", "rushing_tds",
           "attempts", "completions", "passing_yards", "passing_tds", "passing_interceptions",
           "sacks_suffered", "passing_air_yards", "fantasy_points_ppr"]
    for c in num:
        if c not in w.columns:
            w[c] = 0.0
    w[num] = w[num].fillna(0.0)

    played = w[(w[["targets", "carries", "attempts"]].sum(axis=1) > 0)]
    g = w.groupby(["season", "team", "player_id", "player_display_name", "position"])
    agg = g[num].sum()
    agg["games"] = played.groupby(["season", "team", "player_id", "player_display_name",
                                   "position"]).size()
    agg = agg.reset_index()
    agg["games"] = agg["games"].fillna(0)

    team = w.groupby(["season", "team"])[["targets", "carries", "attempts",
                                          "receiving_air_yards"]].sum()
    team.columns = ["team_targets", "team_carries", "team_attempts", "team_air_yards"]
    team["team_games"] = w.groupby(["season", "team"])["week"].nunique()
    agg = agg.merge(team.reset_index(), on=["season", "team"], how="left")

    agg["target_share"] = agg["targets"] / agg["team_targets"].replace(0, np.nan)
    agg["rush_share"] = agg["carries"] / agg["team_carries"].replace(0, np.nan)
    agg["air_yards_share"] = agg["receiving_air_yards"] / agg["team_air_yards"].replace(0, np.nan)
    agg["wopr"] = 1.5 * agg["target_share"].fillna(0) + 0.7 * agg["air_yards_share"].fillna(0)

    # Efficiency: measured, but downstream it gets shrunk toward role means.
    agg["yards_per_target"] = agg["receiving_yards"] / agg["targets"].replace(0, np.nan)
    agg["catch_rate"] = agg["receptions"] / agg["targets"].replace(0, np.nan)
    agg["adot"] = agg["receiving_air_yards"] / agg["targets"].replace(0, np.nan)
    agg["yac_per_rec"] = agg["receiving_yards_after_catch"] / agg["receptions"].replace(0, np.nan)
    agg["yards_per_carry"] = agg["rushing_yards"] / agg["carries"].replace(0, np.nan)
    agg["rec_td_rate"] = agg["receiving_tds"] / agg["targets"].replace(0, np.nan)
    agg["rush_td_rate"] = agg["rushing_tds"] / agg["carries"].replace(0, np.nan)
    agg["ypa"] = agg["passing_yards"] / agg["attempts"].replace(0, np.nan)
    agg["pass_td_rate"] = agg["passing_tds"] / agg["attempts"].replace(0, np.nan)
    agg["int_rate"] = agg["passing_interceptions"] / agg["attempts"].replace(0, np.nan)
    agg["sack_rate"] = agg["sacks_suffered"] / (agg["attempts"] + agg["sacks_suffered"]).replace(0, np.nan)
    agg["ppg_ppr"] = agg["fantasy_points_ppr"] / agg["games"].replace(0, np.nan)

    # Per-game volume, the thing that actually predicts next year.
    for c in ["targets", "carries", "attempts"]:
        agg[f"{c}_per_game"] = agg[c] / agg["games"].replace(0, np.nan)

    opp = _pbp_opportunity(seasons)
    agg = agg.merge(opp, on=["season", "team", "player_id"], how="left")
    for c, t in [("rz_targets", "team_rz_targets"), ("gl_carries", "team_gl_carries"),
                 ("third_down_targets", "team_third_down_targets"),
                 ("rz_carries", "team_rz_carries"), ("gl_qb_rushes", "team_gl_qb_rushes")]:
        agg[c] = agg[c].fillna(0)
        agg[f"{c.replace('team_','')}_share"] = agg[c] / agg[t].replace(0, np.nan)

    sn = snap_shares(seasons)
    agg["player_key"] = agg["player_display_name"].str.lower().str.replace(r"[^a-z]", "", regex=True)
    agg = agg.merge(sn[["season", "team", "player_key", "snap_share", "snap_share_max",
                        "offense_snaps", "snap_games"]],
                    on=["season", "team", "player_key"], how="left")

    # The WR study's second gate: targets earned per unit of field time.
    agg["targets_per_snap_share"] = agg["target_share"] / agg["snap_share"].replace(0, np.nan)
    return agg


# ---------------------------------------------------------------------------
# Empirical-Bayes shrinkage
# ---------------------------------------------------------------------------

def eb_shrink(values: pd.Series, weights: pd.Series, group: pd.Series | None = None,
              prior_strength: float | None = None) -> pd.Series:
    """Shrink a rate toward its group mean, weighted by sample size.

    Method-of-moments beta-binomial: the prior strength k is chosen so that the
    observed between-player variance matches binomial sampling noise plus true
    spread. A player with 20 targets ends up mostly prior; a player with 150
    ends up mostly himself. This is what keeps a four-game 2025 sample from
    being treated like a seventeen-game one.
    """
    v = pd.to_numeric(values, errors="coerce")
    n = pd.to_numeric(weights, errors="coerce").fillna(0)
    grp = group if group is not None else pd.Series("all", index=v.index)
    out = pd.Series(np.nan, index=v.index, dtype=float)
    for key, idx in grp.groupby(grp).groups.items():
        vv, nn = v.loc[idx], n.loc[idx]
        ok = vv.notna() & (nn > 0)
        if ok.sum() < 5:
            out.loc[idx] = vv
            continue
        mu = np.average(vv[ok], weights=nn[ok])
        obs_var = np.average((vv[ok] - mu) ** 2, weights=nn[ok])
        samp_var = mu * (1 - mu) / np.average(nn[ok]) if 0 < mu < 1 else np.nan
        if prior_strength is not None:
            k = prior_strength
        elif np.isfinite(samp_var) and obs_var > samp_var:
            true_var = obs_var - samp_var
            k = max(mu * (1 - mu) / true_var - 1, 1.0)
        else:
            k = float(np.nanmedian(nn[ok])) if ok.any() else 1.0

        # Guard against the method-of-moments blow-up.
        #
        # When the observed spread barely exceeds the assumed sampling noise,
        # true_var goes to zero and k goes to infinity, which shrinks every
        # player onto the group mean and destroys the feature. That is not
        # hypothetical: for 2025 quarterback rush share, obs_var 0.00374 against
        # samp_var 0.00367 gave k = 1393, so Jalen Hurts at 105 carries kept
        # 6.7% of his own rate and every quarterback came out at ~0.12 -- the
        # position's single biggest differentiator, flattened.
        #
        # The root error is the sampling term: these are shares of *team*
        # volume, but samp_var uses the player's own count as the binomial
        # denominator, which overstates the noise by an order of magnitude.
        # Fixing that properly means reworking the exposure weights, so this
        # caps k instead: no player is shrunk harder than a prior worth three
        # times the group's median sample.
        k_max = 3.0 * float(np.nanmedian(nn[ok])) if ok.any() else np.inf
        k = min(k, max(k_max, 1.0))
        out.loc[idx] = (vv.fillna(mu) * nn + mu * k) / (nn + k)
    return out
