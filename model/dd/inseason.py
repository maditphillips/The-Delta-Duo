"""The week 2 onward model: what this season has shown, weighted against last.

The week 1 model is a preseason model. Every feature in it is last year plus
whatever the offseason changed, because that is genuinely all anyone knows in
early September. From week 2 the question is different, and so is the data: a
player has games on this roster, in this scheme, with this depth chart in front
of him. Most of the preseason features are superseded by better versions of
themselves.

The decisive difference is not the features though, it is the training set. The
week 1 model sees one week per season, about nine thousand rows once filtered,
and that starvation has already bitten once: a conclusion drawn from it about
which players the buy/sell model could call turned out to be an artifact of
having too few rows. From week 2 there are seventeen weeks a season to learn
from.

Two things this module refuses to do. It never looks at the week it is
predicting, only at weeks strictly before it, which is enforced in `to_date`
by shifting before the expanding mean rather than after. And it carries no
consensus feature: a model that is handed the market's answer learns to repeat
it, and the gap between our board and the market is the entire point.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import ingest
from .config import CACHE

# What a player was given, and what he did with it. The two halves are
# shrunk towards last season at different rates: a role establishes itself
# quickly and efficiency does not, so one week of touches means far more than
# one week of yards per touch.
ROLE = ["targets", "carries", "attempts", "snap_share",
        "target_share", "carry_share", "rz_targets", "rz_carries"]
EFFICIENCY = ["yards_per_target", "yards_per_carry", "yards_per_attempt",
              "td_rate", "catch_rate"]

TEAM = ["team_plays", "team_pass_rate", "team_sec_per_play",
        "team_rz_trips", "team_points"]

# The first season the in-season half of the panel covers. Earlier seasons sit
# in the panel with every sd_ column blank, because build() starts here, and
# they are a quarter of the rows. Training on them taught the model to lean on
# preseason features for a fifth of its evidence, and it cost real accuracy:
# excluding them is worth +0.053 Spearman at running back, +0.033 at receiver.
# Worse, any column that happened to be blank before this season let a booster
# split those rows off and looked like a feature that worked. That is how the
# matchup layer first appeared to help. Nothing should train on the panel
# without going through usable().
FIRST_IN_SEASON = 2019


def _weekly(seasons) -> pd.DataFrame:
    """One row per player-week: the raw counting stats, plus his team's."""
    s = ingest.load("stats_player", seasons)
    s = s[s.season_type.eq("REG")] if "season_type" in s else s
    keep = ["player_id", "player_name", "position", "season", "week", "team",
            "opponent_team", "targets", "receptions", "receiving_yards",
            "receiving_tds", "carries", "rushing_yards", "rushing_tds",
            "attempts", "completions", "passing_yards", "passing_tds",
            # nflverse calls it passing_interceptions. Asking for
            # "interceptions" matched nothing and the keep filter dropped it
            # silently, so the panel carried no interceptions at all. The model
            # never read them, but anything scoring a quarterback off this
            # frame was handing him back two points a pick.
            "passing_interceptions"]
    s = s[[c for c in keep if c in s.columns]].copy()
    for c in s.columns:
        if c not in ("player_id", "player_name", "position", "team",
                     "opponent_team", "season", "week"):
            s[c] = pd.to_numeric(s[c], errors="coerce").fillna(0.0)

    # Snap counts key on Pro Football Reference ids and the weekly stats key on
    # GSIS, and the names cannot bridge them: the stats file writes "T.Brady"
    # where the snap file writes "Tom Brady". The players release carries both
    # ids, and that join lands 99.8% of snap rows.
    snaps = ingest.load("snap_counts", seasons)
    if len(snaps):
        bridge = (ingest.load("players")[["gsis_id", "pfr_id"]]
                  .dropna().drop_duplicates("pfr_id"))
        sn = snaps.merge(bridge, left_on="pfr_player_id", right_on="pfr_id", how="inner")
        sn = sn.groupby(["season", "week", "gsis_id"], as_index=False).agg(
            off_snaps=("offense_snaps", "sum"), off_pct=("offense_pct", "max"))
        s = s.merge(sn.rename(columns={"gsis_id": "player_id"}),
                    on=["season", "week", "player_id"], how="left")
    s["snap_share"] = pd.to_numeric(s.get("off_pct"), errors="coerce")
    if s.snap_share.max() and s.snap_share.max() > 1.5:
        s["snap_share"] = s.snap_share / 100.0

    # Team totals for the same week, so a share can be taken.
    tm = s.groupby(["season", "week", "team"], as_index=False).agg(
        tm_targets=("targets", "sum"), tm_carries=("carries", "sum"),
        tm_pass_att=("attempts", "sum"))
    s = s.merge(tm, on=["season", "week", "team"], how="left")
    s["target_share"] = s.targets / s.tm_targets.replace(0, np.nan)
    s["carry_share"] = s.carries / s.tm_carries.replace(0, np.nan)
    s["yards_per_target"] = s.receiving_yards / s.targets.replace(0, np.nan)
    s["yards_per_carry"] = s.rushing_yards / s.carries.replace(0, np.nan)
    s["yards_per_attempt"] = s.passing_yards / s.attempts.replace(0, np.nan)
    s["catch_rate"] = s.receptions / s.targets.replace(0, np.nan)
    touches = (s.targets + s.carries + s.attempts).replace(0, np.nan)
    s["td_rate"] = (s.receiving_tds + s.rushing_tds + s.passing_tds) / touches
    # Red zone is not in the weekly file; approximated from scoring volume,
    # which is the honest limit of what this source carries.
    s["rz_targets"] = s.receiving_tds
    s["rz_carries"] = s.rushing_tds
    return s


def to_date(w: pd.DataFrame) -> pd.DataFrame:
    """This season so far, counted only up to the week before.

    The shift comes before the expanding mean, not after. Reversed, every row
    would carry the week it is trying to predict and the backtest would look
    superb and mean nothing.
    """
    w = w.sort_values(["player_id", "season", "week"]).copy()
    g = w.groupby(["player_id", "season"], sort=False)
    for c in ROLE + EFFICIENCY:
        if c in w.columns:
            w[f"sd_{c}"] = g[c].transform(lambda x: x.shift(1).expanding().mean())
    w["sd_games"] = g.cumcount()
    w["sd_ppg"] = g.fantasy_points.transform(lambda x: x.shift(1).expanding().mean()) \
        if "fantasy_points" in w.columns else np.nan
    return w


def team_to_date(w: pd.DataFrame) -> pd.DataFrame:
    """The offence around him, same rule: strictly before this week."""
    tm = w.groupby(["season", "week", "team"], as_index=False).agg(
        team_plays=("tm_targets", "sum"), team_pass_att=("tm_pass_att", "max"),
        team_rush_att=("tm_carries", "max"),
        team_pass_td=("passing_tds", "sum"), team_rush_td=("rushing_tds", "sum"),
        team_rec_td=("receiving_tds", "sum"))
    tm["team_plays"] = tm.team_pass_att + tm.team_rush_att
    tm["team_pass_rate"] = tm.team_pass_att / tm.team_plays.replace(0, np.nan)
    tm["team_tds"] = tm.team_rush_td + tm.team_rec_td
    tm = tm.sort_values(["team", "season", "week"])
    g = tm.groupby(["team", "season"], sort=False)
    for c in ["team_plays", "team_pass_rate", "team_tds"]:
        tm[f"sd_{c}"] = g[c].transform(lambda x: x.shift(1).expanding().mean())
    tm["sd_team_games"] = g.cumcount()
    keep = ["season", "week", "team", "sd_team_plays", "sd_team_pass_rate",
            "sd_team_tds", "sd_team_games"]
    return tm[keep]


def build(seasons=range(2019, 2027), refresh: bool = False) -> pd.DataFrame:
    """The in-season half of the panel, cached."""
    path = CACHE / "inseason.parquet"
    if path.exists() and not refresh:
        return pd.read_parquet(path)
    w = _weekly(seasons)
    w = to_date(w)
    w = w.merge(team_to_date(w), on=["season", "week", "team"], how="left")
    w.to_parquet(path)
    return w


# Each in-season feature and the prior-season feature it is shrunk towards.
# The pairing matters more than the list: a blend is only meaningful between
# two measurements of the same thing.
PAIRS = {
    # role
    "targets": ("sd_targets", "targets_per_game", "role"),
    "carries": ("sd_carries", "carries_per_game", "role"),
    "attempts": ("sd_attempts", "attempts_per_game", "role"),
    "snap_share": ("sd_snap_share", "snap_share_eb", "role"),
    "target_share": ("sd_target_share", "target_share_eb", "role"),
    "carry_share": ("sd_carry_share", "rush_share_eb", "role"),
    # efficiency
    "yards_per_target": ("sd_yards_per_target", "yards_per_target_eb", "eff"),
    "yards_per_carry": ("sd_yards_per_carry", "yards_per_carry_eb", "eff"),
    "yards_per_attempt": ("sd_yards_per_attempt", "ypa_eb", "eff"),
    "catch_rate": ("sd_catch_rate", "catch_rate_eb", "eff"),
}

TEAM_PAIRS = {
    "team_plays": ("sd_team_plays", "team_prev_plays_per_game"),
    "team_pass_rate": ("sd_team_pass_rate", "team_prev_neutral_pass_rate"),
}


def usable(panel: pd.DataFrame) -> pd.DataFrame:
    """The rows that actually carry this-season evidence."""
    return panel[panel.season >= FIRST_IN_SEASON]


def blend(df: pd.DataFrame, k_role: float, k_eff: float,
          k_team: float | None = None) -> pd.DataFrame:
    """Weigh this season against last, by how much of this season there is.

    A straight average would treat one game like sixteen. This is the standard
    shrinkage: n games of evidence against k games of prior, so the in-season
    number takes over gradually and at a rate that differs by what is being
    measured. A role is visible almost immediately, which is a small k; yards
    a carry is mostly noise for a long time, which is a large one. The two k's
    are fitted rather than asserted.
    """
    out = df.copy()
    n = out.get("sd_games", pd.Series(0.0, index=out.index)).fillna(0.0)
    for name, (sd, prior, kind) in PAIRS.items():
        if sd not in out or prior not in out:
            continue
        k = k_role if kind == "role" else k_eff
        cur, old = out[sd], out[prior]
        out[f"b_{name}"] = np.where(
            cur.isna(), old,
            np.where(old.isna(), cur, (n * cur + k * old) / (n + k)))
    kt = k_team if k_team is not None else k_role
    nt = out.get("sd_team_games", pd.Series(0.0, index=out.index)).fillna(0.0)
    for name, (sd, prior) in TEAM_PAIRS.items():
        if sd not in out or prior not in out:
            continue
        cur, old = out[sd], out[prior]
        out[f"b_{name}"] = np.where(
            cur.isna(), old,
            np.where(old.isna(), cur, (nt * cur + kt * old) / (nt + kt)))
    return out


# What the week 2 model looks at. The blended pair for each usage measure,
# this season's sample size so the model knows how much to trust it, the
# matchup, and the team around him. No consensus anywhere.
def feature_list(position: str) -> list[str]:
    blended = [f"b_{k}" for k in PAIRS] + [f"b_{k}" for k in TEAM_PAIRS]
    context = ["sd_games", "sd_team_games", "week",
               "implied_team_total", "team_spread", "total_line", "is_home",
               "is_dome", "rest", "div_game",
               "opp_prev_def_epa_pass", "opp_prev_def_epa_rush",
               "opp_prev_def_success_rate", "opp_prev_def_plays_per_game",
               "depth_rank", "is_rookie", "changed_team", "age", "years_exp"]
    return blended + context


def training_frame(panel: pd.DataFrame, position: str, k_role: float,
                   k_eff: float) -> pd.DataFrame:
    from .features import rankable
    d = rankable(usable(panel), position)
    return blend(d, k_role, k_eff)


def _fast_eval(d: pd.DataFrame, feats: list[str], target: str,
               seasons) -> float:
    """One booster, for searching k and ablating groups.

    This was a ridge fed median-filled NaNs, and it was the wrong instrument.
    Most of the panel has no in-season history at all in any given week, and
    filling those blanks with the median tells the model a man who has not
    played is an average one. The ridge scored 0.62 where the shipped model
    scores 0.84, so every conclusion drawn from it was drawn about a different
    model. A booster that reads a blank as a blank scores what the real thing
    scores, which is the whole point of a search harness.
    """
    from scipy.stats import spearmanr
    from sklearn.ensemble import HistGradientBoostingRegressor
    cols = [c for c in feats if c in d.columns]
    out = []
    for s in seasons:
        tr, te = d[d.season < s], d[d.season == s]
        if len(tr) < 500 or len(te) < 200:
            continue
        m = HistGradientBoostingRegressor(max_depth=4, learning_rate=0.05,
                                          max_iter=300, l2_regularization=1.0,
                                          random_state=0)
        m.fit(tr[cols], tr[target])
        # Scored within each week, because that is how a weekly list is used.
        p = pd.Series(m.predict(te[cols]), index=te.index)
        rho = te.assign(p=p).groupby("week").apply(
            lambda g: spearmanr(g.p, g[target]).statistic if len(g) > 5 else np.nan)
        out.append(rho.mean())
    return float(np.nanmean(out)) if out else np.nan


def search_k(panel: pd.DataFrame, position: str, scoring_col: str,
             seasons, k_roles=(1, 2, 4, 8, 16), k_effs=(4, 8, 16, 32, 64)):
    """How many games of prior each half of the game is worth."""
    from .features import rankable
    base = rankable(usable(panel), position)
    feats = feature_list(position)
    rows = []
    for kr in k_roles:
        for ke in k_effs:
            d = blend(base, kr, ke)
            rows.append({"k_role": kr, "k_eff": ke,
                         "rho": _fast_eval(d, feats, scoring_col, seasons)})
    return pd.DataFrame(rows).sort_values("rho", ascending=False)


# What the k search settled. Role blends after a single game of prior, which
# is to say this season takes over almost at once. Efficiency does not blend
# at all: across every position, ignoring this season's yards a touch scored
# as well as any finite weight, so it stays on last season where the sample is
# large enough to mean something.
K_ROLE, K_EFF = 1.0, np.inf

GROUPS = {
    "in-season role": [f"b_{k}" for k, v in PAIRS.items() if v[2] == "role"] + ["sd_games"],
    "efficiency": [f"b_{k}" for k, v in PAIRS.items() if v[2] == "eff"],
    "team": [f"b_{k}" for k in TEAM_PAIRS] + ["sd_team_games"],
    "vegas": ["implied_team_total", "team_spread", "total_line"],
    "opponent": [c for c in ["opp_prev_def_epa_pass", "opp_prev_def_epa_rush",
                             "opp_prev_def_success_rate", "opp_prev_def_plays_per_game"]],
    "situation": ["is_home", "is_dome", "rest", "div_game", "week"],
    "player": ["depth_rank", "is_rookie", "changed_team", "age", "years_exp"],
}


def ablate(panel: pd.DataFrame, position: str, scoring_col: str, seasons):
    """Drop each group in turn and see what the list loses without it."""
    from .features import rankable
    d = blend(rankable(usable(panel), position), K_ROLE, K_EFF)
    full = feature_list(position)
    base = _fast_eval(d, full, scoring_col, seasons)
    rows = [{"group": "(everything)", "n_feats": len(full), "rho": base, "delta": 0.0}]
    for name, cols in GROUPS.items():
        keep = [c for c in full if c not in cols]
        r = _fast_eval(d, keep, scoring_col, seasons)
        rows.append({"group": f"without {name}", "n_feats": len(keep),
                     "rho": r, "delta": r - base})
    return pd.DataFrame(rows)


# Efficiency and opponent defence are dropped. Both cost nothing in ablation
# at any position, and together they cost nothing either: 23 features score
# what 31 did. Opponent is the more surprising of the two, and it echoes what
# the preseason model found about scheme, that a defence measured last year
# says very little about one week this year.
DROP = set(GROUPS["efficiency"]) | set(GROUPS["opponent"])


# The matchup layer in dd/defense.py is built, measured and not used. What a
# defence has given up so far, opponent-adjusted and shrunk towards last
# season, adds nothing at any position: between -0.002 and +0.003 Spearman,
# and negative at three of the four. The test that settles it is the
# permutation one. Join every player to a real defence from the same week
# chosen at random instead of the one he actually faced, and the model scores
# exactly what it scores with the right defence. There is no matchup signal
# being used because at one to a few games of evidence there is none to use.
# It stays behind a flag rather than being deleted, because the measurement is
# worth keeping and the answer may change with a better opponent adjustment.
def features_final(position: str, matchup: bool = False) -> list[str]:
    f = [c for c in feature_list(position) if c not in DROP]
    if matchup:
        from .defense import MATCHUP
        f = f + [c for c in MATCHUP if c not in f]
    return f


def backtest(panel: pd.DataFrame, seasons=range(2022, 2026), verbose: bool = True):
    """The real model against the two things anyone actually does in-season:
    rank by what a man has averaged so far, or by what he averaged last year."""
    from scipy.stats import spearmanr
    from .features import rankable
    from .model import PositionModel
    panel = usable(panel)
    rows = []
    for pos, col in [("QB", "actual_qb_4pt"), ("RB", "actual_ppr"),
                     ("WR", "actual_ppr"), ("TE", "actual_ppr")]:
        d = blend(rankable(panel, pos), K_ROLE, K_EFF).sort_values(
            ["player_id", "season", "week"])
        g = d.groupby(["player_id", "season"], sort=False)[col]
        d["sd_ppg"] = g.transform(lambda x: x.shift(1).expanding().mean())
        feats = features_final(pos)
        for s in seasons:
            tr, te = d[d.season < s], d[d.season == s]
            if len(tr) < 500 or len(te) < 200:
                continue
            m = PositionModel(pos, "ppr", features=feats)
            m.fit(tr.assign(**{f"actual_{m.scoring}": tr[col]}))
            te = te.copy()
            te["pred"] = m.predict(te)["proj"].to_numpy()
            for name, series in (("model", te.pred),
                                 ("season to date ppg", te.sd_ppg),
                                 ("last season ppg", te.get("ppg_ppr"))):
                if series is None:
                    continue
                # spearmanr returns NaN if either input carries one, and the
                # prior-season column is empty for a fifth of rows, so the
                # comparison has to drop them rather than inherit the NaN.
                t = te.assign(p=series).dropna(subset=["p", col])
                rho = t.groupby("week").apply(
                    lambda x: spearmanr(x.p, x[col]).statistic if len(x) > 5 else np.nan)
                rows.append({"position": pos, "season": s, "source": name,
                             "rho": rho.mean()})
    r = pd.DataFrame(rows)
    if verbose:
        print(r.pivot_table(index="position", columns="source", values="rho").round(4).to_string())
    return r


def target_rows(season: int, week: int) -> pd.DataFrame:
    """The board to be predicted, with this season's weeks so far attached.

    dataset.build_rows deliberately withholds weeks 1..W-1 of the current
    season, because the preseason model poses every week as the week-1 problem.
    This model is the opposite: those weeks are the whole point, so they are
    joined back on here.
    """
    from . import dataset
    rows = dataset.build_rows(season, week=week)
    ins = build()
    sd = [c for c in ins.columns if c.startswith("sd_")]
    prior = ins[(ins.season == season) & (ins.week < week)]
    if prior.empty:
        raise SystemExit(f"no {season} weeks before {week} to learn from")
    # Averaged over the weeks played, not lifted off the last row.
    #
    # to_date gives every row the state *before* it, which is what a training
    # row needs and exactly wrong here: the week 1 row carries "before week 1",
    # which is nothing at all. Predicting week 2 needs the state after week 1,
    # so the same means are taken again at the boundary.
    raw = [c.removeprefix("sd_") for c in sd
           if c.removeprefix("sd_") in prior.columns]
    latest = prior.groupby("player_id")[raw].mean()
    latest.columns = [f"sd_{c}" for c in latest.columns]
    latest["sd_games"] = prior.groupby("player_id").week.count()
    # The offence around him, rebuilt at the boundary for the same reason the
    # player's own role is. The panel carries sd_team_plays as the state BEFORE
    # each week, so lifting it off the week-1 row returns nothing, and every
    # team fell back to last season: b_team_plays and b_team_pass_rate were
    # null on all 920 rows and carried no in-season information at all.
    # Rebuilt from the per-week team totals, which the panel does carry.
    tmw = prior.groupby(["team", "week"], as_index=False).agg(
        pass_att=("tm_pass_att", "max"), rush_att=("tm_carries", "max"))
    tmw["plays"] = tmw.pass_att + tmw.rush_att
    tmw["pass_rate"] = tmw.pass_att / tmw.plays.replace(0, np.nan)
    tm = tmw.groupby("team", as_index=False).agg(
        sd_team_plays=("plays", "mean"), sd_team_pass_rate=("pass_rate", "mean"),
        sd_team_games=("week", "nunique")).set_index("team")
    rows = rows.merge(latest.reset_index(), on="player_id", how="left")
    return rows.merge(tm.reset_index(), on="team", how="left")


# Men who missed last week and are back this one.
#
# The hurdle multiplies E[points if he plays] by P(he plays), and the
# classifier has learned that a blank in-season row means he does not play.
# It is nearly perfect about it: every back who missed week 1 came out between
# 0.0000 and 0.0008, against a mean of 0.82 for everyone who played. That is
# right for a man still injured and badly wrong for one who is back, and the
# model has no way to tell them apart because the injury feed it would need is
# empty this season. TreVeyon Henderson was worth 10.66 points if he played
# and shipped at 0.007.
#
# Naming a player here asserts that he plays, and the published row becomes
# his conditional one: the projection, the tails and the top-12 odds all stop
# being multiplied by a probability we know to be wrong.
RETURNING = Path(__file__).resolve().parent.parent / "data" / "returning.csv"


def returning(season: int, week: int, position: str) -> set[str]:
    if not RETURNING.exists():
        return set()
    r = pd.read_csv(RETURNING)
    r = r[(r.season == season) & (r.week == week)
          & (r.position.str.upper() == position.upper())]
    return set(r.player)


def predict_week(season: int, week: int, panel: pd.DataFrame | None = None,
                 train_seasons=None) -> dict:
    """Wilson's board for one in-season week, one list per position and format."""
    from .config import LIST_DEPTH, LISTS, POSITIONS
    from .features import rankable
    from .model import PositionModel, rank_frame
    if panel is None:
        panel = pd.read_parquet(CACHE / "inseason_panel.parquet")
    panel = usable(panel) if train_seasons is None \
        else panel[panel.season.isin(list(train_seasons))]
    rows = target_rows(season, week)
    out = {}
    for pos in POSITIONS:
        feats = features_final(pos)
        tr_all = blend(rankable(panel, pos), K_ROLE, K_EFF)
        te = blend(rankable(rows, pos), K_ROLE, K_EFF)
        for scoring in LISTS[pos]:
            col = f"actual_{scoring}"
            tr = tr_all[tr_all[col].notna()].copy()
            m = PositionModel(pos, scoring, features=feats)
            m.fit(tr)
            preds = m.predict(te)
            back = returning(season, week, pos)
            if back:
                hit = te.player_name.isin(back).to_numpy()
                if hit.any():
                    preds = preds.copy()
                    preds.loc[hit, "p_play"] = 1.0
                    preds.loc[hit, "proj"] = preds.loc[hit, "cond_points"]
                    for q in range(10, 100, 10):
                        preds.loc[hit, f"q{q}"] = preds.loc[hit, f"cq{q}"]
                    print(f"  {pos} {scoring}: assuming "
                          + ", ".join(te.player_name[hit]) + " plays")
            ranked = rank_frame(te, preds, LIST_DEPTH[pos] * 3)
            ranked["learner"] = m.chosen_
            out[(pos, scoring)] = ranked
    return out
