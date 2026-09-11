"""Buy low, sell high: what a week's miss actually predicts.

A player who misses his projection by ten points has told you something or
nothing, and the box score alone cannot say which. Sam Darnold opened 2026
with 0.5 points against a 17.1 projection and five snaps of fifty: he left the
game, and the miss predicts nothing at all. Christian McCaffrey missed by six
the same night with his targets *above* projection and his carries halved,
which is a different animal entirely.

So the week is split before it is used. Opportunity -- targets, carries, snaps
against what was expected of him -- is one thing; efficiency -- yards a touch,
touchdowns -- is another. The first is known to persist and the second is known
to regress, and the model is fitted to find out by how much rather than told.

Sleeper supplies both halves: its projections carry a full stat line, not just
a points total, and both endpoints reach back to 2022.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

from .config import CACHE

SLEEPER = "https://api.sleeper.app/v1"
STORE = CACHE / "sleeper"
# 2022 is as far back as the projections endpoint carries a full slate.
SEASONS = range(2022, 2027)
WEEKS = range(1, 19)


def _get(kind: str, season: int, week: int) -> dict:
    """One week of one endpoint, cached on disk. Their data for a finished week
    never changes, so it is fetched once and kept."""
    STORE.mkdir(parents=True, exist_ok=True)
    path = STORE / f"{kind}_{season}_{week:02d}.json"
    if path.exists():
        return json.loads(path.read_text())
    url = f"{SLEEPER}/{kind}/nfl/regular/{season}/{week}"
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as fh:
                data = json.load(fh)
            break
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)
    path.write_text(json.dumps(data))
    return data


# What is pulled from each side. Projections carry no snap counts, which is why
# snap share is measured against the player's own season rather than a forecast.
PROJ = ["pts_ppr", "pts_half_ppr", "rec_tgt", "rec", "rec_yd", "rec_td",
        "rush_att", "rush_yd", "rush_td", "pass_att", "pass_yd", "pass_td"]
ACT = PROJ + ["off_snp", "tm_off_snp", "gp", "pass_int", "fum_lost"]


def week_frame(season: int, week: int) -> pd.DataFrame:
    """Actuals and projections for one week, one row per player."""
    st, pr = _get("stats", season, week), _get("projections", season, week)
    rows = []
    for pid, s in st.items():
        if not isinstance(s, dict) or not s.get("gp"):
            continue
        p = pr.get(pid) or {}
        if not isinstance(p, dict) or p.get("pts_ppr") is None:
            continue  # nobody projected him, so there is no miss to measure
        row = {"sleeper_id": pid, "season": season, "week": week}
        row.update({f"a_{k}": float(s.get(k) or 0.0) for k in ACT})
        row.update({f"p_{k}": float(p.get(k) or 0.0) for k in PROJ})
        rows.append(row)
    return pd.DataFrame(rows)


def panel(seasons=SEASONS, weeks=WEEKS, verbose: bool = True) -> pd.DataFrame:
    """Every player-week Sleeper both projected and scored."""
    out = []
    for s in seasons:
        got = 0
        for w in weeks:
            try:
                f = week_frame(s, w)
            except Exception as e:  # a week that does not exist yet
                if verbose:
                    print(f"  {s} wk{w:>2}: {type(e).__name__}")
                continue
            if len(f):
                out.append(f)
                got += len(f)
        if verbose:
            print(f"  {s}: {got} player-weeks")
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def _players() -> pd.DataFrame:
    """Sleeper's roster, for position and name. One document, cached."""
    path = STORE / "players.json"
    if not path.exists():
        with urllib.request.urlopen(f"{SLEEPER}/players/nfl", timeout=180) as fh:
            path.write_text(json.dumps(json.load(fh)))
    d = json.loads(path.read_text())
    return pd.DataFrame([
        {"sleeper_id": k, "player": v.get("full_name"), "position": v.get("position"),
         "team": v.get("team")}
        for k, v in d.items() if v.get("position") in ("QB", "RB", "WR", "TE")
    ])


POSITIONS = ("QB", "RB", "WR", "TE")
# Below this he was not a startable asset going in, and the "miss" is noise
# about a man nobody would trade for either way.
MIN_PROJECTED = 5.0
# Fewer games left than this and the target is one or two outings, which is
# not a rest of season anything.
MIN_REMAINING = 3


def features(p: pd.DataFrame) -> pd.DataFrame:
    """One row per player-week: how the week broke, and what followed.

    The target is his points a game over the rest of the season measured
    against the level he carried into this week, which is what Sleeper had him
    down for. Zero therefore means the week changed nothing, and that is
    exactly the first thing worth beating.
    """
    p = p.merge(_players(), on="sleeper_id", how="left")
    p = p[p.position.isin(POSITIONS) & (p.p_pts_ppr >= MIN_PROJECTED)].copy()

    p["resid"] = p.a_pts_ppr - p.p_pts_ppr
    p["snap_share"] = np.where(p.a_tm_off_snp > 0, p.a_off_snp / p.a_tm_off_snp, np.nan)
    # Opportunity: what he was actually given, against what was forecast.
    p["d_targets"] = p.a_rec_tgt - p.p_rec_tgt
    p["d_carries"] = p.a_rush_att - p.p_rush_att
    p["d_pass_att"] = p.a_pass_att - p.p_pass_att
    p["opp_ratio"] = ((p.a_rec_tgt + p.a_rush_att + p.a_pass_att)
                      / (p.p_rec_tgt + p.p_rush_att + p.p_pass_att).clip(lower=0.5))
    # Efficiency: what he did with it. Touchdowns sit on their own because they
    # are the loudest and the least repeatable thing in a box score.
    p["d_yards"] = ((p.a_rec_yd + p.a_rush_yd + p.a_pass_yd)
                    - (p.p_rec_yd + p.p_rush_yd + p.p_pass_yd))
    p["d_tds"] = ((p.a_rec_td + p.a_rush_td + p.a_pass_td)
                  - (p.p_rec_td + p.p_rush_td + p.p_pass_td))
    p["yds_per_opp"] = ((p.a_rec_yd + p.a_rush_yd + p.a_pass_yd)
                        / (p.a_rec_tgt + p.a_rush_att + p.a_pass_att).clip(lower=1))
    p["level"] = p.p_pts_ppr

    p = p.sort_values(["sleeper_id", "season", "week"])
    g = p.groupby(["sleeper_id", "season"], sort=False)
    # Rest of season: his points a game in the games he actually played after
    # this one. Availability is a separate risk from performance and mixing the
    # two would have the model predicting injuries it cannot see.
    rev = p.iloc[::-1]
    rg = rev.groupby(["sleeper_id", "season"], sort=False).a_pts_ppr
    p["ros_ppg"] = (rg.cumsum().shift(1) / rg.cumcount().replace(0, np.nan)).iloc[::-1]
    p["ros_games"] = rg.cumcount().iloc[::-1]
    p["target"] = p.ros_ppg - p.level
    p["prior_ppg"] = g.a_pts_ppr.transform(lambda s: s.shift(1).expanding().mean())
    return p


FEATURES = ["resid", "d_targets", "d_carries", "d_pass_att", "opp_ratio",
            "d_yards", "d_tds", "yds_per_opp", "snap_share", "level",
            "prior_ppg", "week"]


def _frame(df: pd.DataFrame) -> pd.DataFrame:
    X = df[FEATURES].copy()
    for pos in POSITIONS[1:]:          # QB is the reference level
        X[f"is_{pos}"] = (df.position == pos).astype(float)
    return X


def _matrix(df: pd.DataFrame, fill: pd.Series | None = None) -> np.ndarray:
    """Gaps are filled from the training seasons, never from the week in hand.

    In week one nobody has prior form, so prior_ppg and the role features are
    empty for the entire slate and a median taken from the slate itself is
    simply NaN again. Filling from training also keeps one week's rows from
    informing each other, which is its own small leak the rest of the season.
    """
    X = _frame(df)
    return X.fillna(fill if fill is not None else X.median(numeric_only=True)).to_numpy()


def usable(f: pd.DataFrame) -> pd.DataFrame:
    return f[(f.ros_games >= MIN_REMAINING) & f.target.notna()].copy()


def fit(train: pd.DataFrame):
    """Ridge on standardised features. The relationship here is a question of
    how much each half of a week carries forward, which is a set of slopes, and
    a booster on nine thousand rows mostly finds noise in it."""
    from sklearn.linear_model import RidgeCV
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    m = make_pipeline(StandardScaler(),
                      RidgeCV(alphas=np.logspace(-2, 4, 25)))
    fill = _frame(train).median(numeric_only=True)
    m.fit(_matrix(train, fill), train.target.to_numpy())
    m.fill_ = fill
    return m


def backtest(f: pd.DataFrame, verbose: bool = True) -> pd.DataFrame:
    """Train on the seasons before, predict the next. Scored against the two
    things anyone actually does with a big week: ignore it, or believe it."""
    from scipy.stats import spearmanr
    d = usable(f[f.season < 2026])
    rows = []
    for season in sorted(d.season.unique())[1:]:
        tr, te = d[d.season < season], d[d.season == season]
        m = fit(tr)
        pred = m.predict(_matrix(te, m.fill_))
        y = te.target.to_numpy()
        for name, p in (("model", pred),
                        ("week meant nothing", np.zeros(len(te))),
                        ("week is the new level", te.resid.to_numpy())):
            rows.append({"season": season, "source": name, "n": len(te),
                         "mae": np.abs(p - y).mean(),
                         "rmse": float(np.sqrt(((p - y) ** 2).mean())),
                         "spearman": spearmanr(p, y).statistic})
    r = pd.DataFrame(rows)
    if verbose:
        print(r.groupby("source")[["mae", "rmse", "spearman"]].mean().round(3).to_string())
    return r


# How big a miss has to be before it is worth a second look. Taken from the
# historical spread rather than from the week in hand, so a Thursday night with
# four games on it is judged by the same yardstick as a full Sunday.
FLAG_PCT = 0.15


def calibrate(train: pd.DataFrame, model) -> dict:
    """Where to cut, learned from history instead of guessed."""
    lo, hi = train.resid.quantile(FLAG_PCT), train.resid.quantile(1 - FLAG_PCT)
    pred = model.predict(_matrix(train, model.fill_))
    t = train.assign(pred=pred)
    sell = t[t.resid >= hi]
    buy = t[(t.resid <= lo) & (t.level >= 15)]
    return {"resid_lo": float(lo), "resid_hi": float(hi),
            "sell_cut": float(sell.pred.median()),
            "buy_cut": float(buy.pred.median())}


def _why(r) -> str:
    """The week in one line: what he was given, and what he did with it."""
    bits = []
    opp = [(r.a_rec_tgt, r.p_rec_tgt, "targets"),
           (r.a_rush_att, r.p_rush_att, "carries"),
           (r.a_pass_att, r.p_pass_att, "attempts")]
    for a, p, name in opp:
        if max(a, p) >= 3 and abs(a - p) >= 1:
            bits.append(f"{a:.0f} {name} against {p:.1f} expected")
        elif max(a, p) >= 3:
            bits.append(f"{a:.0f} {name}, about what was expected")
    if pd.notna(r.snap_share):
        bits.append(f"{r.snap_share:.0%} of the snaps")
    td_a = r.a_rec_td + r.a_rush_td + r.a_pass_td
    td_p = r.p_rec_td + r.p_rush_td + r.p_pass_td
    if abs(td_a - td_p) >= 0.6:
        bits.append(f"{td_a:.0f} touchdowns against {td_p:.1f} expected")
    return ". ".join(bits[:4]) + "." if bits else ""


VERDICTS = ("SELL HIGH", "BUY LOW", "HOLD", "NO CALL")


def predict(season: int, week: int, f: pd.DataFrame | None = None) -> pd.DataFrame:
    """Call the week just played, using every season before it."""
    if f is None:
        f = features(panel(verbose=False))
    train = usable(f[f.season < season])
    model = fit(train)
    cuts = calibrate(train, model)

    live = f[(f.season == season) & (f.week == week)].copy()
    live["pred_change"] = model.predict(_matrix(live, model.fill_))

    sell = (live.resid >= cuts["resid_hi"]) & (live.pred_change <= cuts["sell_cut"])
    # Below a 15-point projection the backtest cannot call a rebound, so it
    # does not pretend to. Saying nothing is the honest answer there.
    buyable = (live.resid <= cuts["resid_lo"]) & (live.level >= 15)
    buy = buyable & (live.pred_change >= cuts["buy_cut"])
    live["verdict"] = np.select(
        [sell, buy, buyable | (live.resid >= cuts["resid_hi"]),
         live.resid <= cuts["resid_lo"]],
        ["SELL HIGH", "BUY LOW", "HOLD", "NO CALL"],
        default="HOLD")
    live["why"] = live.apply(_why, axis=1)
    live["cuts"] = json.dumps(cuts)
    cols = ["season", "week", "sleeper_id", "player", "position", "team",
            "a_pts_ppr", "p_pts_ppr", "resid", "pred_change", "verdict", "why",
            "snap_share", "level", "d_targets", "d_carries", "d_tds", "cuts"]
    return live[cols].sort_values("resid")
