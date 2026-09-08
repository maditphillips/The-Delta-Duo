"""Which columns each position model is allowed to see."""
from __future__ import annotations

MARKET = ["implied_team_total", "implied_opp_total", "team_spread", "abs_spread",
          "total_line", "is_home", "is_dome", "is_favourite", "rest", "div_game"]

SCHEME_PROJ = ["off_proj_plays_per_game", "off_proj_sec_per_play", "off_proj_proe",
               "off_proj_neutral_pass_rate", "off_proj_early_down_pass_rate",
               "off_proj_adot", "off_proj_deep_rate", "off_proj_short_rate",
               "off_proj_rb_target_share", "off_proj_te_target_share",
               "off_proj_wr_target_share", "off_proj_rz_pass_rate", "off_proj_gl_rush_rate",
               "off_proj_qb_designed_run_rate", "off_proj_no_huddle_rate",
               "off_proj_shotgun_rate", "off_proj_pa_rate", "off_proj_motion_rate"]

SCHEME_PREV = ["team_prev_plays_per_game", "team_prev_proe", "team_prev_neutral_pass_rate",
               "team_prev_rb_target_share", "team_prev_te_target_share",
               "team_prev_wr_target_share", "team_prev_rz_pass_rate",
               "team_prev_gl_rush_rate", "team_prev_sec_per_play"]

REGIME = ["off_continuity", "hc_continuity", "off_caller_prior_seasons"]

CHURN = ["vacated_target_share", "vacated_rush_share", "vacated_rz_target_share",
         "vacated_gl_carry_share", "vacated_air_yards_share"]

PLAYER = ["depth_rank", "changed_team", "is_rookie", "no_prior_season", "log_draft_pick",
          "years_exp", "age", "is_questionable"]

USAGE_RECEIVING = ["target_share_eb", "air_yards_share_eb", "wopr", "rz_targets_share_eb",
                   "third_down_targets_share_eb", "targets_per_snap_share",
                   "targets_per_game", "snap_share_eb", "snap_share"]
USAGE_RUSHING = ["rush_share_eb", "gl_carries_share_eb", "rz_carries_share_eb",
                 "carries_per_game", "snap_share_eb", "snap_share"]
USAGE_PASSING = ["attempts_per_game", "gl_qb_rushes_share_eb", "carries_per_game"]

EFF_RECEIVING = ["yards_per_target_eb", "catch_rate_eb", "adot_eb", "yac_per_rec_eb",
                 "rec_td_rate_eb"]
EFF_RUSHING = ["yards_per_carry_eb", "rush_td_rate_eb"]
EFF_PASSING = ["ypa_eb", "pass_td_rate_eb", "int_rate_eb", "sack_rate_eb"]

HISTORY = ["ppg_ppr", "games", "ppg_ppr_y2", "target_share_y2", "rush_share_y2",
           "snap_share_y2", "targets_per_game_y2", "carries_per_game_y2"]

OPPONENT = ["opp_prev_def_epa_pass", "opp_prev_def_epa_rush", "opp_prev_def_pass_funnel",
            "opp_prev_def_success_rate", "opp_prev_def_sack_rate",
            "opp_prev_def_ypa_allowed", "opp_prev_def_ypc_allowed",
            "opp_prev_def_rz_td_rate", "opp_def_continuity",
            "opp_def_proj_def_epa_pass", "opp_def_proj_def_epa_rush",
            "opp_def_proj_def_pass_funnel"]

OPPORTUNITY = ["proj_team_plays", "proj_team_pass_att", "proj_team_rush_att",
               "expected_targets", "expected_carries", "expected_rz_targets",
               "expected_gl_carries", "expected_rec_yards", "expected_rush_yards",
               "expected_receptions", "expected_rec_td", "expected_rush_td",
               "naive_points_ppr"]
OPPORTUNITY_QB = ["proj_team_plays", "proj_team_pass_att", "expected_pass_att",
                  "expected_pass_yards", "expected_pass_td", "expected_carries",
                  "expected_gl_carries", "expected_rush_yards", "naive_points_ppr"]

# The reduced team-environment block: last season's measured offence, discounted
# by a head-coach change. Ten columns instead of twenty-seven, and every input
# is either measured or verified -- no play-caller curation required.
TEAM_ENV = ["env_plays_per_game", "env_neutral_pass_rate", "env_proe",
            "env_sec_per_play", "env_rb_target_share", "env_te_target_share",
            "env_wr_target_share", "env_rz_pass_rate", "env_gl_rush_rate",
            "hc_change", "opp_hc_change"]
USE_TEAM_ENV_COLUMNS = True

BASE = MARKET + SCHEME_PROJ + SCHEME_PREV + REGIME + CHURN + PLAYER + HISTORY + OPPONENT

# ---------------------------------------------------------------------------
# Whether the raw scheme columns are fed to the player models
# ---------------------------------------------------------------------------
# Decided by ablation (outputs/ablation/), seed-averaged over three seed
# families, 28 position-seasons:
#
#   dropping the play-caller layer alone  ->  -0.006 Spearman, 95% CI
#                                             [-0.021, +0.008], p = 0.38 (null)
#   dropping every scheme column          ->  +0.026 Spearman, 95% CI
#                                             [+0.012, +0.041], p = 0.001
#
# Twenty-seven mostly-collinear team columns on a thousand-row problem dilute
# the features that carry the signal, so they stay out. Note this removes the
# scheme *columns* only: the carryover projection still reaches the model
# through expected volume in dataset.py, because projected team plays and pass
# rate are what turn a player's share into expected targets and carries. The
# claim is "raw scheme columns do not earn a slot", not "scheme is irrelevant".
USE_SCHEME_COLUMNS = False

_SCHEME_BLOCK = SCHEME_PROJ + SCHEME_PREV + REGIME
if not USE_SCHEME_COLUMNS:
    BASE = [c for c in BASE if c not in set(_SCHEME_BLOCK)]
if USE_TEAM_ENV_COLUMNS:
    BASE = BASE + TEAM_ENV

FEATURES = {
    "QB": BASE + OPPORTUNITY_QB + USAGE_PASSING + EFF_PASSING + ["gl_qb_rushes_share", "rush_share_eb"],
    "RB": BASE + OPPORTUNITY + USAGE_RUSHING + USAGE_RECEIVING + EFF_RUSHING + EFF_RECEIVING,
    "WR": BASE + OPPORTUNITY + USAGE_RECEIVING + EFF_RECEIVING,
    "TE": BASE + OPPORTUNITY + USAGE_RECEIVING + EFF_RECEIVING,
}

# Who is even rankable in week 1. Anyone else is noise in training and clutter
# in the output.
def rankable(df, position: str):
    d = df[(df["position"] == position) & (df["is_out"] != 1)]
    if position == "QB":
        m = (d["depth_rank"] <= 2) | (d["attempts_per_game"].fillna(0) >= 8)
    elif position == "RB":
        m = (d["depth_rank"] <= 5) | (d["carries_per_game"].fillna(0) >= 3) \
            | (d["targets_per_game"].fillna(0) >= 2)
    elif position == "WR":
        m = (d["depth_rank"] <= 6) | (d["targets_per_game"].fillna(0) >= 2)
    else:
        m = (d["depth_rank"] <= 4) | (d["targets_per_game"].fillna(0) >= 1.5)
    return d[m].copy()
