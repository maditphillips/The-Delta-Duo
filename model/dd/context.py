"""Game context: what Vegas and the schedule say before kickoff."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import ingest


def team_week(seasons=None) -> pd.DataFrame:
    """One row per team-game with the market's view of it.

    The implied team total is the single strongest weekly signal available for
    free, and it is known days before kickoff, so it is fair game for a week-1
    model in a way that nothing else about the current season is.
    """
    g = ingest.load("schedules")
    if seasons is not None:
        g = g[g["season"].isin(list(seasons))]
    g = g[g["game_type"] == "REG"].copy()

    home = g.assign(team=g["home_team"], opponent=g["away_team"], is_home=1.0,
                    team_spread=-g["spread_line"], rest=g["home_rest"],
                    opp_rest=g["away_rest"], coach=g["home_coach"], opp_coach=g["away_coach"])
    away = g.assign(team=g["away_team"], opponent=g["home_team"], is_home=0.0,
                    team_spread=g["spread_line"], rest=g["away_rest"],
                    opp_rest=g["home_rest"], coach=g["away_coach"], opp_coach=g["home_coach"])
    cols = ["game_id", "season", "week", "gameday", "team", "opponent", "is_home",
            "team_spread", "total_line", "rest", "opp_rest", "roof", "surface",
            "div_game", "temp", "wind"]
    tw = pd.concat([home[cols], away[cols]], ignore_index=True)
    tw["team"] = tw["team"].replace({"OAK": "LV", "SD": "LAC", "STL": "LA", "LAR": "LA"})
    tw["opponent"] = tw["opponent"].replace({"OAK": "LV", "SD": "LAC", "STL": "LA", "LAR": "LA"})

    # team_spread is from this team's perspective: negative means favoured.
    tw["implied_team_total"] = tw["total_line"] / 2 - tw["team_spread"] / 2
    tw["implied_opp_total"] = tw["total_line"] / 2 + tw["team_spread"] / 2
    tw["is_dome"] = tw["roof"].isin(["dome", "closed"]).astype(float)
    tw["is_favourite"] = (tw["team_spread"] < 0).astype(float)
    tw["abs_spread"] = tw["team_spread"].abs()
    return tw
