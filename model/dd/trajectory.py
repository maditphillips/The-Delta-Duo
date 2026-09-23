"""Buy low, sell high on the whole season so far, not the last week.

rebound.py reads one week: how far he missed his projection and why. That
cannot tell a man who had two good games from a man who had one bad game and
one huge one, and those are opposite trades. Here a row is a player THROUGH
week N: every game he has played this season, as one shape.

What is measured, week 1 through N:
  shape        how much of his season is one game, how often he beat his line
  opportunity  targets, carries, attempts and snaps a game, and whether the
               latest week is a step up from the ones before it
  efficiency   yards a touch and touchdowns against what was projected, which
               are the parts that come back to earth
  price        what Sleeper has him down for NEXT week, which has already seen
               weeks 1 through N

The target is his points a game over the rest of the season against that next
price. N and games played are features, so one model covers every week and
learns its own discount for a short sample.

What the backtest found (leave one season out, 2022-2025):

  * Against Sleeper's raw price, the calls were mostly "fade the expensive
    ones, buy the cheap ones". Sleeper overprices its stars and underprices
    bench players who keep getting snaps. That is a bias in the price, not a
    trade, so every call is judged against other men AT HIS PRICE (PRICE).
  * On that footing the season model and the single-week model tied (0.17
    Spearman within position and price band). Their average beat either at
    every stage of the season, so the call is the average.
  * The season model is the better calibrated of the two on week-1/week-2
    patterns. Two big weeks: the single-week model expected them to hold
    their price and they fell 1.2 points a game short of it.
  * Nearly everyone regresses toward his price. After two weeks, 97% of hot
    men went on to score less than they had, and 92% of cold men more. The
    calls pick who moves further than his peers.

Hit rates against peers at the same price: sells 62% after two weeks, 74%
weeks 3-5, 75% weeks 6-9, 59% after. Buys 55%, 66%, 50%, then 45%, which is
worse than a coin flip, so buys from week 10 on should not be trusted.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from . import rebound as rb

MIN_REMAINING = rb.MIN_REMAINING
MIN_PROJECTED = rb.MIN_PROJECTED


def _opp(p, side):
    return p[f"{side}_rec_tgt"] + p[f"{side}_rush_att"] + p[f"{side}_pass_att"]


def _yds(p, side):
    return p[f"{side}_rec_yd"] + p[f"{side}_rush_yd"] + p[f"{side}_pass_yd"]


def _tds(p, side):
    return p[f"{side}_rec_td"] + p[f"{side}_rush_td"] + p[f"{side}_pass_td"]


def prices(seasons, last_week: dict[int, int]) -> pd.DataFrame:
    """Sleeper's projection for every player-week, played or not.

    The panel only keeps weeks a man played, and next week has not been played
    by anyone. last_week caps each season at the latest week anyone could need,
    so a live season does not fetch sixteen weeks of forecasts nobody uses.
    """
    rows = []
    for s in seasons:
        for w in range(1, min(last_week.get(s, 18), 18) + 1):
            pr = rb._get("projections", s, w)
            for pid, v in pr.items():
                if isinstance(v, dict) and v.get("pts_ppr") is not None:
                    rows.append((pid, s, w, float(v["pts_ppr"])))
    return pd.DataFrame(rows, columns=["sleeper_id", "season", "week", "price"])


SHRUNK = ["ytd_resid", "d_tds_pg", "d_tgt_pg", "d_car_pg", "d_att_pg",
          "beat_frac", "best_share", "snap_trend", "ypo_ytd"]


def features(p: pd.DataFrame) -> pd.DataFrame:
    """One row per player through week N, with what followed."""
    p = p.merge(rb._players(), on="sleeper_id", how="left")
    p = p[p.position.isin(rb.POSITIONS) & (p.p_pts_ppr >= MIN_PROJECTED)].copy()
    p = p.sort_values(["sleeper_id", "season", "week"]).reset_index(drop=True)

    p["resid"] = p.a_pts_ppr - p.p_pts_ppr
    p["opp_a"], p["opp_p"] = _opp(p, "a"), _opp(p, "p")
    p["yds_a"], p["td_a"], p["td_p"] = _yds(p, "a"), _tds(p, "a"), _tds(p, "p")
    p["snap_share"] = np.where(p.a_tm_off_snp > 0, p.a_off_snp / p.a_tm_off_snp, np.nan)
    p["beat"] = (p.resid > 0).astype(float)

    g = p.groupby(["sleeper_id", "season"], sort=False)
    cs = lambda c: g[c].cumsum()
    p["games"] = g.cumcount() + 1
    n = p.games
    pts = cs("a_pts_ppr")

    # Where the season stands, and where the market thought it would.
    p["ytd_ppg"] = pts / n
    p["ytd_proj"] = cs("p_pts_ppr") / n
    p["ytd_resid"] = p.ytd_ppg - p.ytd_proj
    p["last_resid"] = p.resid
    p["missed"] = p.week - n

    # Shape. One game carrying the season looks nothing like two good ones.
    best = g.a_pts_ppr.cummax()
    p["best_share"] = np.where(n > 1, (best / pts.clip(lower=1.0)).clip(0, 1), np.nan)
    p["ppg_ex_best"] = np.where(n > 1, (pts - best) / (n - 1).clip(lower=1), np.nan)
    p["beat_frac"] = cs("beat") / n
    p["pts_sd"] = (g.a_pts_ppr.expanding().std().reset_index(level=[0, 1], drop=True)
                   .sort_index())

    # Opportunity, to date and trending. The trend is the newest week against
    # his own weeks before it, which is where a new role first shows.
    for a, pcol, name in (("a_rec_tgt", "p_rec_tgt", "tgt"),
                          ("a_rush_att", "p_rush_att", "car"),
                          ("a_pass_att", "p_pass_att", "att")):
        ca = cs(a)
        p[f"{name}_pg"] = ca / n
        p[f"d_{name}_pg"] = (ca - cs(pcol)) / n
        p[f"{name}_trend"] = np.where(n > 1, p[a] - (ca - p[a]) / (n - 1).clip(lower=1), np.nan)
    p["opp_ratio"] = cs("opp_a") / cs("opp_p").clip(lower=0.5)
    snaps = p.snap_share.fillna(0)
    has = p.snap_share.notna().astype(float)
    sc, hc = g.snap_share.transform(lambda s: s.fillna(0).cumsum()), g.snap_share.transform(lambda s: s.notna().cumsum())
    p["snap_ytd"] = sc / hc.replace(0, np.nan)
    prev = (sc - snaps) / (hc - has).replace(0, np.nan)
    p["snap_trend"] = p.snap_share - prev

    # Efficiency, the half that regresses.
    p["ypo_ytd"] = cs("yds_a") / cs("opp_a").clip(lower=1)
    p["d_tds_ytd"] = cs("td_a") - cs("td_p")
    p["d_tds_pg"] = p.d_tds_ytd / n
    p["td_rate"] = cs("td_a") / cs("opp_a").clip(lower=1)
    p["first_price"] = g.p_pts_ppr.transform("first")

    # The week just played, as rebound.py reads it. The season shape alone
    # scored no better than the single week did; the two together do.
    p["d_targets"] = p.a_rec_tgt - p.p_rec_tgt
    p["d_carries"] = p.a_rush_att - p.p_rush_att
    p["d_pass_att"] = p.a_pass_att - p.p_pass_att
    p["d_tds"] = p.td_a - p.td_p
    p["d_yards"] = p.yds_a - _yds(p, "p")
    p["yds_per_opp"] = p.yds_a / p.opp_a.clip(lower=1)
    p["prior_ppg"] = np.where(n > 1, (pts - p.a_pts_ppr) / (n - 1).clip(lower=1), np.nan)

    # How far to trust a rate depends on how many games are behind it, and a
    # ridge cannot learn that on its own. Each rate also enters scaled by
    # games / (games + 3): a quarter weight after one game, 0.8 after twelve.
    p["shrink"] = n / (n + 3)
    for c in SHRUNK:
        p[f"{c}_x"] = p[c] * p.shrink

    # Last season, for anyone who played in it.
    last = (p.groupby(["sleeper_id", "season"]).a_pts_ppr.mean()
            .rename("last_season_ppg").reset_index())
    last["season"] += 1
    p = p.merge(last, on=["sleeper_id", "season"], how="left")

    # Rest of season: games played after week N, as in rebound.py.
    rev = p.iloc[::-1]
    rg = rev.groupby(["sleeper_id", "season"], sort=False).a_pts_ppr
    p["ros_ppg"] = (rg.cumsum().shift(1) / rg.cumcount().replace(0, np.nan)).iloc[::-1]
    p["ros_games"] = rg.cumcount().iloc[::-1]
    # shift(1) inside a reversed group leaks across groups at the boundary;
    # a player's last game has nothing after it.
    p.loc[p.ros_games == 0, "ros_ppg"] = np.nan

    # The price: next week's projection, or the week after if he is on a bye.
    last_week = p.groupby("season").week.max().add(2).to_dict()
    pr = prices(sorted(p.season.unique()), last_week)
    for k in (1, 2):
        nxt = pr.rename(columns={"price": f"price_{k}"}).assign(week=lambda d: d.week - k)
        p = p.merge(nxt, on=["sleeper_id", "season", "week"], how="left")
    p["level"] = p.price_1.fillna(p.price_2)
    p["market_move"] = p.level - p.first_price
    p["target"] = p.ros_ppg - p.level
    return p


SEASON = ["week", "games", "missed", "level", "market_move", "last_season_ppg",
          "ytd_ppg", "ytd_proj", "ytd_resid", "last_resid",
          "best_share", "ppg_ex_best", "beat_frac", "pts_sd",
          "tgt_pg", "car_pg", "att_pg", "d_tgt_pg", "d_car_pg", "d_att_pg",
          "tgt_trend", "car_trend", "att_trend", "opp_ratio",
          "snap_ytd", "snap_trend", "ypo_ytd", "d_tds_ytd", "d_tds_pg", "td_rate"]
LAST_WEEK = ["d_targets", "d_carries", "d_pass_att", "d_tds", "d_yards",
             "yds_per_opp", "snap_share", "prior_ppg"]
FEATURES = SEASON + LAST_WEEK + ["shrink"] + [f"{c}_x" for c in SHRUNK]
# Price alone. Sleeper overprices its stars and underprices the bench players
# who keep getting snaps, so against the raw price every call is "fade the
# expensive ones". What a trade needs is the part left over: better or worse
# than other men at his price.
PRICE = ["week", "level"]


def _frame(df, cols):
    X = df[cols].copy()
    for pos in rb.POSITIONS[1:]:
        X[f"is_{pos}"] = (df.position == pos).astype(float)
    return X


def usable(f):
    return f[(f.ros_games >= MIN_REMAINING) & f.target.notna() & f.level.notna()].copy()


class Model:
    """Ridge or booster on a named column set, filled from training only."""

    def __init__(self, kind="ridge", cols=FEATURES):
        self.kind, self.cols = kind, cols

    def fit(self, tr):
        X = _frame(tr, self.cols)
        if self.kind == "ridge":
            from sklearn.linear_model import RidgeCV
            from sklearn.pipeline import make_pipeline
            from sklearn.preprocessing import StandardScaler
            self.fill_ = X.median(numeric_only=True)
            self.m = make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-2, 4, 25)))
            self.m.fit(X.fillna(self.fill_).to_numpy(), tr.target.to_numpy())
        else:
            from sklearn.ensemble import HistGradientBoostingRegressor
            self.m = HistGradientBoostingRegressor(
                max_depth=3, learning_rate=0.04, max_iter=400, min_samples_leaf=80,
                l2_regularization=1.0, random_state=0)
            self.m.fit(X.to_numpy(), tr.target.to_numpy())
        return self

    def predict(self, df):
        X = _frame(df, self.cols)
        if self.kind == "ridge":
            X = X.fillna(self.fill_)
        return self.m.predict(X.to_numpy())


# The single-week model has to be scored against the same price. It predicts
# rest of season against THIS week's projection; add that back and take off
# next week's and it answers the same question as everything else here.
def _rebound_preds(panel_df, tr_seasons, te):
    rf = rb.features(panel_df)
    m = rb.fit(rb.usable(rf[rf.season.isin(tr_seasons)]))
    x = rf.merge(te[["sleeper_id", "season", "week", "level"]]
                 .rename(columns={"level": "next_price"}),
                 on=["sleeper_id", "season", "week"], how="inner")
    x["pred"] = m.predict(rb._matrix(x, m.fill_)) + x.p_pts_ppr - x.next_price
    return te[["sleeper_id", "season", "week"]].merge(
        x[["sleeper_id", "season", "week", "pred"]], how="left").pred.to_numpy()


def _blend(tr, te, panel_df, tr_seasons):
    """Both models and the price-only line, fitted on tr, scored on te.

    The season model and the single-week model tie on their own, and their
    average beats either at every stage of the season, so the call is the
    average. Each is put on the other's scale first; the single-week model
    spreads its predictions wider, and a plain mean would let it outvote.
    """
    ms, mp = Model("ridge", FEATURES).fit(tr), Model("ridge", PRICE).fit(tr)
    out = te[["sleeper_id", "season", "week"]].copy()
    out["m_season"] = ms.predict(te)
    out["m_week"] = _rebound_preds(panel_df, tr_seasons, te)
    out["m_price"] = mp.predict(te)
    ref = tr[["sleeper_id", "season", "week"]].copy()
    ref["s"], ref["p"] = ms.predict(tr), mp.predict(tr)
    ref["w"] = _rebound_preds(panel_df, tr_seasons, tr)
    sd_s, sd_w = (ref.s - ref.p).std(), (ref.w - ref.p).std()
    a_s = out.m_season - out.m_price
    a_w = (out.m_week - out.m_price).fillna(a_s)
    out["vs_peers"] = (a_s / sd_s + a_w / sd_w) / 2 * sd_s
    out["pred_change"] = out.m_price + out.vs_peers
    return out


def backtest(panel_df, f=None, seasons=range(2022, 2026)):
    """Leave one season out, every call scored against what followed."""
    if f is None:
        f = features(panel_df)
    d = usable(f[f.season.isin(seasons)])
    out = []
    for s in seasons:
        tr, te = d[d.season != s], d[d.season == s].copy()
        b = _blend(tr, te, panel_df, [x for x in seasons if x != s])
        te = te.merge(b, on=["sleeper_id", "season", "week"])
        te["b_season"] = te.ytd_ppg - te.level
        out.append(te)
    bt = pd.concat(out, ignore_index=True)
    bt["verdict"] = verdicts(bt)
    return bt


# Running hot or cold: his scoring so far against his projections so far, in
# standard deviations of a single week's miss at his position, scaled by games
# played. A quarterback's week swings further than a tight end's, and one
# yardstick for all four made every hot or cold call a quarterback. Measured
# on 2022-2025: QB 7.4, RB 6.2, WR 6.3, TE 5.0. One sd for a receiver over
# two games is a 4.4-point-a-game gap; over eight, 2.2.
WEEK_SD = {"QB": 7.37, "RB": 6.15, "WR": 6.25, "TE": 5.01}
HOT = 1.0
# How far from other men at his price before it is a call, in points a game.
TAU = 0.75


def form(df):
    return df.ytd_resid * np.sqrt(df.games) / df.position.map(WEEK_SD)


def verdicts(df):
    """Hot and expected back more than his peers: sell. Cold and expected to
    recover more than his peers: buy. Everyone else holds.

    Two labels the design started with are gone because the backtest could
    not tell them from a coin flip. BREAKOUT (hot, not a sell) beat its peers
    49% of the time after two weeks and those men still fell from 20.2 points
    a game to 11.5; calling that a breakout is the wrong word for a 43% drop.
    FADE (cold, not a buy) was right 56% of the time and those men went from
    6.2 to 11.9, which is the opposite of what the word says.
    """
    z = form(df)
    sell = (z >= HOT) & (df.vs_peers <= -TAU)
    buy = (z <= -HOT) & (df.vs_peers >= TAU)
    return np.select([sell, buy], ["SELL HIGH", "BUY LOW"], "HOLD")


PHASES = [0, 2, 5, 9, 15]


def report(bt):
    """Hit rates by stage of the season.

    A sell is right if he then trailed other men at his price, a buy if he
    beat them. Also: how often a hot man fell below what he had been scoring
    and a cold man rose above it, which is what a trade partner is paying for.
    """
    bt = bt.assign(peer=bt.target - bt.m_price,
                   phase=pd.cut(bt.week, PHASES,
                                labels=["wk1-2", "wk3-5", "wk6-9", "wk10-15"]))
    rows = []
    for (ph, v), g in bt.groupby(["phase", "verdict"], observed=True):
        if v == "HOLD":
            continue
        sell = v == "SELL HIGH"
        rows.append({"phase": ph, "verdict": v, "calls": len(g),
                     "vs_peers": ((g.peer < 0) if sell else (g.peer >= 0)).mean(),
                     "vs_his_scoring": ((g.ros_ppg < g.ytd_ppg) if sell
                                        else (g.ros_ppg > g.ytd_ppg)).mean(),
                     "ppg_so_far": g.ytd_ppg.mean(), "ppg_after": g.ros_ppg.mean(),
                     "price": g.level.mean()})
    return pd.DataFrame(rows)


def _why(r, weeks) -> str:
    """The season in one line: the weeks, the shape, and what drove it."""
    bits = []
    if len(weeks):
        pts = ", ".join(f"{x:.1f}" for x in weeks.a_pts_ppr)
        proj = ", ".join(f"{x:.1f}" for x in weeks.p_pts_ppr)
        wk = (f"Week {int(weeks.week.iloc[0])}" if len(weeks) == 1
              else f"Weeks {int(weeks.week.iloc[0])}-{int(weeks.week.iloc[-1])}")
        bits.append(f"{wk}: {pts} against {proj} projected")
    if r.games > 1 and r.best_share >= 0.65 and r.ytd_ppg > 0:
        bits.append(f"one game is {r.best_share:.0%} of his points")
    if abs(r.d_tds_ytd) >= 1.0:
        tds = r.d_tds_ytd + (weeks.td_p.sum() if len(weeks) else 0)
        word = "touchdown" if round(tds) == 1 else "touchdowns"
        bits.append(f"{tds:.0f} {word} against {tds - r.d_tds_ytd:.1f} projected")
    for name, pg, d in (("targets", r.tgt_pg, r.d_tgt_pg), ("carries", r.car_pg, r.d_car_pg)):
        if abs(d) >= 1.5 and max(pg, pg - d) >= 3:
            bits.append(f"{pg:.1f} {name} a game against {pg - d:.1f} projected")
    if r.games > 1 and pd.notna(r.snap_trend) and abs(r.snap_trend) >= 0.12:
        before = r.snap_share - r.snap_trend
        bits.append(f"snaps {before:.0%} to {r.snap_share:.0%}")
    return ". ".join(b[0].upper() + b[1:] for b in bits[:4]) + "." if bits else ""


def predict(season: int, week: int, panel_df=None, f=None) -> pd.DataFrame:
    """Call every player through the week just played, on every season before."""
    if panel_df is None:
        panel_df = rb.panel(verbose=False)
    if f is None:
        f = features(panel_df)
    train_seasons = sorted(x for x in f.season.unique() if x < season)
    tr = usable(f[f.season.isin(train_seasons)])
    live = f[(f.season == season) & (f.week == week) & f.level.notna()].copy()
    live = live.merge(_blend(tr, live, panel_df, train_seasons),
                      on=["sleeper_id", "season", "week"])
    live["form"] = form(live)
    live["verdict"] = verdicts(live)
    live["left_early"] = ((live.snap_share < rb.EXIT_SNAP_SHARE)
                          & (live.p_pts_ppr >= rb.EXIT_LEVEL) & (live.resid < 0))
    hurt = live.injury_status.isin(rb.SIDELINED) | live.left_early
    live.loc[hurt, "verdict"] = "INJURED"
    wk = f[(f.season == season) & (f.week <= week)]
    live["why"] = [_why(r, wk[wk.sleeper_id == r.sleeper_id]) for r in live.itertuples()]
    live["ros_proj"] = live.level + live.pred_change
    live["cuts"] = json.dumps({"hot_sd": HOT, "tau": TAU, "week_sd": WEEK_SD})
    cols = ["season", "week", "sleeper_id", "player", "position", "team",
            "a_pts_ppr", "p_pts_ppr", "resid", "pred_change", "verdict", "why",
            "snap_share", "level", "d_targets", "d_carries", "d_tds",
            "injury_status", "injury_part", "left_early", "cuts",
            "games", "ytd_ppg", "ytd_proj", "ytd_resid", "form", "vs_peers", "ros_proj"]
    return live[cols].sort_values("vs_peers")
