"""Shared expected-points machinery for the kicker-1.01 study.

The one adjustment every script here needs: nflverse charges a scoring play
only the points it scored and charges the ensuing kickoff to the kickoff
play, while a punt already carries the cost of handing the ball over. To
compare a field goal against a punt, the kickoff has to be charged back to
the kick.

    K(t, era) = expected points the opponent gets from the possession that
                follows a score, as a smooth function of seconds left in the
                half, split at the 2024 dynamic kickoff.

    aepa      = nflverse epa, minus K on scoring plays
    v_perfect = 3 - K - ep, the value of a guaranteed make from that state

K is measured directly: for every made field goal, the expected points of the
opponent's next snap in the same half, or zero if the half expired first.
"""
import numpy as np
import pandas as pd

SNAP_TO_KICK = 18       # nflverse kick_distance = yardline_100 + 18
SCRIM = ["pass", "run", "punt", "field_goal", "qb_kneel", "qb_spike"]
KO_ERA_SPLIT = 2024     # the dynamic kickoff moved starting field position


def kern(x0, x, y, bw):
    """Gaussian-kernel local mean of y(x) evaluated at the points x0."""
    out = np.empty(len(x0))
    for i, v in enumerate(x0):
        w = np.exp(-0.5 * ((x - v) / bw) ** 2)
        s = w.sum()
        out[i] = (w * y).sum() / s if s > 0 else np.nan
    return out


def tag_kicks(d):
    """Add is_fg / made / dist / scored / era. Safe to call twice."""
    d["is_fg"] = d.field_goal_attempt.fillna(0).eq(1) & d.field_goal_result.notna()
    d["made"] = d.field_goal_result.eq("made")
    d["dist"] = d.kick_distance
    # a few rows carry a kick_distance inconsistent with the snap spot
    # (re-spotted after a penalty); rebuild those from the yard line
    bad = d.is_fg & d.dist.sub(d.yardline_100).ne(SNAP_TO_KICK)
    d.loc[bad, "dist"] = d.loc[bad, "yardline_100"] + SNAP_TO_KICK
    d["scored"] = d.touchdown.fillna(0).eq(1) | d.made
    d["era"] = np.where(d.season >= KO_ERA_SPLIT, "dynamic KO 2024+", "pre-2024")
    return d


def kickoff_sample(d):
    """One row per made field goal: K, the expected points of the opponent's
    next snap in the same half (zero if the half expired first)."""
    nxt = d[d.play_type.isin(SCRIM)][
        ["game_id", "play_id", "posteam", "ep", "qtr"]
    ].rename(columns={"play_id": "n_pid", "posteam": "n_pos", "ep": "n_ep",
                      "qtr": "n_qtr"})
    src = d[d.made][["game_id", "play_id", "season", "era", "posteam", "qtr",
                     "half_seconds_remaining"]]
    m = src.merge(nxt, on="game_id")
    m = m[m.n_pid > m.play_id]
    m = m.sort_values(["game_id", "play_id", "n_pid"]).groupby(
        ["game_id", "play_id"], as_index=False).first()
    same_half = m.n_qtr.notna() & (((m.qtr <= 2) & (m.n_qtr <= 2))
                                   | ((m.qtr >= 3) & (m.n_qtr >= 3)))
    m["k"] = np.where(same_half & m.n_pos.ne(m.posteam), m.n_ep, 0.0)
    return m


def add_adjusted(d, fit_seasons=None):
    """Attach k_eff, aepa and v_perfect to a full play-by-play frame."""
    d = tag_kicks(d.sort_values(["game_id", "play_id"]).reset_index(drop=True))
    ks = kickoff_sample(d)
    fit = ks if fit_seasons is None else ks[ks.season.isin(fit_seasons)]
    grid = np.arange(0, 1901, 5.0)
    k_eff = np.zeros(len(d))
    for era, g in fit.groupby("era"):
        vals = kern(np.sqrt(grid), np.sqrt(g.half_seconds_remaining.to_numpy(float)),
                    g.k.to_numpy(float), bw=2.2)
        sel = (d.era == era).to_numpy()
        k_eff[sel] = np.interp(d.half_seconds_remaining.fillna(0)
                               .to_numpy(float)[sel], grid, vals)
    d["k_eff"] = k_eff
    d["aepa"] = d.epa - np.where(d.scored, d.k_eff, 0.0)
    d["v_perfect"] = 3.0 - d.k_eff - d.ep
    return d, ks
