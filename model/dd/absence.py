"""Where a starter's work goes when he sits.

The in-season model prices every player on his own usage, blended with last
season's. When a starter is ruled out his targets, carries and snaps have to
go somewhere, and nothing in the model says where: the man behind him is
priced as the backup he was last week. Oronde Gadsden played 18% of the snaps
behind David Njoku and Charlie Kolar and was priced at TE41 in the week both
of them were out.

This module measures it from 2019-2025. An ABSENCE is an established player
(two or more games for his team this season, including the team's previous
game) who does not take an offensive snap. For every teammate who does play
that week, the change is his usage that week against his own season to date
before it. The changes are summed by where the teammate sits relative to the
absent man:

  next    the highest-usage teammate at the same position ranked BELOW him
  same    everyone else at his position, including men ranked above him
  new     anyone with no game for the team yet this season
  RB/WR/TE the other positions

and reported as a share of what the absent man had been getting.

What it found, when the absent man was the top of his room:
  RB1 out   next back 45% of carries, 37% of targets; rest of the room 26%/33%
  TE1 out   next tight end 33% of targets and snaps; rest 24%/32%; receivers
            about 28% of his targets
  WR1 out   no single heir: next man 14% of targets, the rest of the room 58%

Backtest, 2021-2025, train on earlier seasons (rates re-measured inside each
fold): adding the measured share to the heirs' usage ("rule") beat the
current model in all 15 position-seasons. Players not touched by an absence
rank exactly as before. The next man up was under-projected by 3.0 points (RB),
1.2 (TE) and 1.1 (WR); the rule cuts that to 0.3, -0.3 and 0.3. Error per
player improves at RB and is slightly worse at TE and WR, where the work is
spread thin and who gets it is harder to call.

Limits: absences are taken from who did not play, where live use has the
injury report; and only a man's first missed game is handled.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import ingest

POS = ("RB", "WR", "TE")
SEASONS = range(2019, 2026)


def usage(seasons=SEASONS) -> pd.DataFrame:
    """Every RB/WR/TE who took an offensive snap, with his targets and carries.

    Built on the snap file rather than the stats file: a blocking tight end
    with no target is missing from the stats but not from the field.
    """
    sn = ingest.load("snap_counts", seasons)
    sn = sn[(sn.game_type == "REG") & sn.position.isin(POS) & (sn.offense_snaps > 0)]
    bridge = (ingest.load("players")[["gsis_id", "pfr_id"]]
              .dropna().drop_duplicates("pfr_id"))
    sn = sn.merge(bridge, left_on="pfr_player_id", right_on="pfr_id", how="left")
    sn["player_id"] = sn.gsis_id.fillna("pfr:" + sn.pfr_player_id)
    sn["snap_share"] = pd.to_numeric(sn.offense_pct, errors="coerce")
    if sn.snap_share.max() > 1.5:
        sn["snap_share"] /= 100.0
    u = sn[["season", "week", "team", "player_id", "player", "position", "snap_share"]]
    st = ingest.load("stats_player", seasons)
    st = st[st.season_type.eq("REG")][["season", "week", "player_id", "targets", "carries"]]
    u = u.merge(st, on=["season", "week", "player_id"], how="left")
    u[["targets", "carries"]] = u[["targets", "carries"]].fillna(0.0)
    return u.drop_duplicates(["season", "week", "team", "player_id"])


def baselines(u: pd.DataFrame) -> pd.DataFrame:
    """Each player's season to date with this team, BEFORE each week."""
    u = u.sort_values(["season", "team", "player_id", "week"]).copy()
    g = u.groupby(["season", "team", "player_id"], sort=False)
    u["games"] = g.cumcount()
    for c in ("targets", "carries", "snap_share"):
        u[f"base_{c}"] = g[c].transform(lambda s: s.shift(1).expanding().mean())
    return u


def absences(u: pd.DataFrame) -> pd.DataFrame:
    """Established men who played the team's previous game and not this one."""
    weeks = (u[["season", "team", "week"]].drop_duplicates()
             .sort_values(["season", "team", "week"]))
    weeks["prev_week"] = weeks.groupby(["season", "team"]).week.shift(1)
    last = u.merge(weeks, on=["season", "team", "week"])
    # A man's state after his game in week w is his baseline for the team's
    # next game, so carry it forward one team-game and see who is missing.
    after = last.assign(
        games_after=last.games + 1,
        pg_targets=(last.base_targets.fillna(0) * last.games + last.targets) / (last.games + 1),
        pg_carries=(last.base_carries.fillna(0) * last.games + last.carries) / (last.games + 1),
        pg_snap=(last.base_snap_share.fillna(0) * last.games + last.snap_share) / (last.games + 1))
    nxt = weeks.rename(columns={"week": "next_week", "prev_week": "week"})
    after = after.merge(nxt, on=["season", "team", "week"])
    after = after[after.games_after >= 2]
    played = u[["season", "team", "week", "player_id"]].assign(here=1)
    a = after.merge(played.rename(columns={"week": "next_week"}),
                    on=["season", "team", "next_week", "player_id"], how="left")
    a = a[a.here.isna()]
    return a.rename(columns={"next_week": "abs_week"})[
        ["season", "team", "abs_week", "player_id", "player", "position",
         "games_after", "pg_targets", "pg_carries", "pg_snap"]]


def measure(u=None, strict=False) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Where the work went, by the absent man's position and role.

    Only team-weeks with one absence at the absent man's position are used,
    so each change inside his room can be pinned on one man. strict=True also
    requires nobody missing at the other two positions, which keeps the
    cross-position numbers clean and costs over half the sample.
    """
    if u is None:
        u = baselines(usage())
    a = absences(u)
    by = ["season", "team", "abs_week"] + ([] if strict else ["position"])
    a = a[a.groupby(by).player_id.transform("size") == 1]
    # Rank him among his position room by snap share to date: 1 is the starter.
    rows = []
    for x in a.itertuples():
        wk = u[(u.season == x.season) & (u.team == x.team) & (u.week == x.abs_week)]
        room = wk[(wk.position == x.position) & (wk.games > 0)]
        below = room[room.base_snap_share < x.pg_snap].sort_values("base_snap_share", ascending=False)
        nxt = below.player_id.iloc[0] if len(below) else None
        above = (room.base_snap_share >= x.pg_snap).sum()
        for y in wk.itertuples():
            if y.games == 0:
                grp = "new"
            elif y.position == x.position:
                grp = "next" if y.player_id == nxt else "same"
            else:
                grp = y.position
            rows.append({"season": x.season, "team": x.team, "week": x.abs_week,
                         "absent": x.player, "abs_pos": x.position, "abs_rank": above + 1,
                         "v_targets": x.pg_targets, "v_carries": x.pg_carries, "v_snap": x.pg_snap,
                         "group": grp, "mate": y.player,
                         "d_targets": y.targets - (y.base_targets if y.games else 0),
                         "d_carries": y.carries - (y.base_carries if y.games else 0),
                         "d_snap": y.snap_share - (y.base_snap_share if y.games else 0)})
    d = pd.DataFrame(rows)
    return a, d


# ---------------------------------------------------------------------------
# Stage 2: does pricing it help the model?

STATS = {"t": ("base_targets", "pg_targets", "targets"),
         "c": ("base_carries", "pg_carries", "carries"),
         "s": ("base_snap_share", "pg_snap", "snap_share")}
INH = [f"inh_{g}_{k}" for g in ("next", "same") for k in STATS]


def allocations(u: pd.DataFrame, a: pd.DataFrame) -> pd.DataFrame:
    """Each absent man's per-game work, laid on the teammates in his room.

    The next man up gets all of it in the inh_next columns; everyone else at
    the position splits it by his own share of the room in inh_same. These
    are raw amounts: how much of it each man actually inherits is either
    measured (rule) or learned by the model (learned).
    """
    out = []
    for x in a.itertuples():
        room = u[(u.season == x.season) & (u.team == x.team) & (u.week == x.abs_week)
                 & (u.position == x.position) & (u.games > 0)]
        if room.empty:
            continue
        below = room[room.base_snap_share < x.pg_snap].sort_values("base_snap_share", ascending=False)
        nxt = below.player_id.iloc[0] if len(below) else None
        rank = int((room.base_snap_share >= x.pg_snap).sum()) + 1
        rest = room[room.player_id != nxt]
        for y in room.itertuples():
            r = {"season": x.season, "week": x.abs_week, "team": x.team,
                 "player_id": y.player_id, "abs_rank": rank, "abs_pos": x.position}
            for k, (base, vac, _) in STATS.items():
                v = getattr(x, vac)
                if y.player_id == nxt:
                    r[f"inh_next_{k}"], r[f"inh_same_{k}"] = v, 0.0
                else:
                    tot = rest[base].sum()
                    r[f"inh_next_{k}"] = 0.0
                    r[f"inh_same_{k}"] = v * (getattr(y, base) / tot if tot > 0 else 0.0)
            out.append(r)
    al = pd.DataFrame(out)
    if al.empty:
        return al
    keep = ["season", "week", "team", "player_id"]
    s = al.groupby(keep)[INH].sum()
    s["abs_top"] = al.groupby(keep).abs_rank.min()
    return s.reset_index()


def rates(d: pd.DataFrame) -> dict:
    """Measured share of the vacated work taken by next / same, by the absent
    man's position and whether he was the starter, from a measure() detail."""
    key = ["season", "team", "week"]
    out = {}
    d = d.assign(starter=d.abs_rank == 1)
    for (pos, st), dd in d.groupby(["abs_pos", "starter"]):
        for k, (vcol, dcol) in {"t": ("v_targets", "d_targets"), "c": ("v_carries", "d_carries"),
                                "s": ("v_snap", "d_snap")}.items():
            per = dd.groupby(key + ["group"])[dcol].sum().unstack("group").fillna(0)
            vv = dd.groupby(key)[vcol].first().sum()
            for grp in ("next", "same"):
                val = per[grp].sum() / vv if grp in per and vv > 0 else 0.0
                out[(pos, st, grp, k)] = float(np.clip(val, 0.0, 1.0))
    return out


def apply_rule(df: pd.DataFrame, r: dict) -> pd.DataFrame:
    """Add the measured share of the vacated work to the blended usage."""
    df = df.copy()
    st = df.abs_top.fillna(9) == 1
    for k, b in (("t", "b_targets"), ("c", "b_carries"), ("s", "b_snap_share")):
        add = np.zeros(len(df))
        for grp in ("next", "same"):
            rate = np.where(st, df.position.map(lambda p: r.get((p, True, grp, k), 0.0)),
                            df.position.map(lambda p: r.get((p, False, grp, k), 0.0)))
            add += rate * df[f"inh_{grp}_{k}"].fillna(0).to_numpy()
        old = df[b].copy()
        # Only the rows that inherit anything. Filling every blank with zero
        # would tell the model that a man with no usage history has none.
        hit = add > 0
        df.loc[hit, b] = old[hit].fillna(0) + add[hit]
        if k == "s":
            df[b] = df[b].clip(upper=1.0)
        share = {"t": "b_target_share", "c": "b_carry_share"}.get(k)
        if share and share in df:
            scale = np.where(old.fillna(0) > 0, df[b] / old.replace(0, np.nan), np.nan)
            df[share] = np.where(np.isfinite(scale), df[share] * scale, df[share])
    return df


def backtest(seasons=range(2021, 2026), verbose=True):
    """Current model, rule, learned: scored on every row and on the rows a
    teammate's absence touched."""
    from scipy.stats import spearmanr
    from . import inseason as ins
    from .features import rankable
    from .model import PositionModel
    u = pd.read_parquet(ins.CACHE / "absence_usage.parquet") if (ins.CACHE / "absence_usage.parquet").exists() \
        else baselines(usage())
    a = absences(u)
    al = allocations(u, a)
    _, det = measure(u)
    panel = ins.usable(pd.read_parquet(ins.CACHE / "inseason_panel.parquet"))
    panel = panel[panel.season >= min(SEASONS)]
    rows, calls = [], []
    for pos in POS:
        col = "actual_ppr"
        d = ins.blend(rankable(panel, pos), ins.K_ROLE, ins.K_EFF)
        d = d.merge(al, on=["season", "week", "team", "player_id"], how="left")
        d["hit"] = d[INH].fillna(0).sum(axis=1) > 0
        d[INH] = d[INH].fillna(0.0)
        feats = ins.features_final(pos)
        for s in seasons:
            tr, te = d[d.season < s], d[d.season == s].copy()
            r = rates(det[det.season < s])
            variants = {"current": (tr, te, feats),
                        "rule": (apply_rule(tr, r), apply_rule(te, r), feats),
                        "learned": (tr, te, feats + INH)}
            for name, (a_tr, a_te, f) in variants.items():
                m = PositionModel(pos, "ppr", features=f)
                m.fit(a_tr[a_tr[col].notna()])
                te[f"p_{name}"] = m.predict(a_te)["proj"].to_numpy()
            for name in variants:
                t = te.dropna(subset=[col])
                rho = t.groupby("week").apply(
                    lambda x: spearmanr(x[f"p_{name}"], x[col]).statistic if len(x) > 5 else np.nan).mean()
                h = t[t.hit & (t.played == 1)]
                nx = h[h.inh_next_s > 0]
                rho_rest = t[~t.hit].groupby("week").apply(
                    lambda x: spearmanr(x[f"p_{name}"], x[col]).statistic if len(x) > 5 else np.nan).mean()
                rows.append({"pos": pos, "season": s, "variant": name, "rho_all": rho,
                             "rho_unaffected": rho_rest,
                             "next_n": len(nx), "next_bias": (nx[col] - nx[f"p_{name}"]).mean(),
                             "next_mae": (nx[col] - nx[f"p_{name}"]).abs().mean(),
                             "hit_n": len(h), "hit_bias": (h[col] - h[f"p_{name}"]).mean(),
                             "hit_mae": (h[col] - h[f"p_{name}"]).abs().mean()})
            calls.append(te[te.hit])
    r = pd.DataFrame(rows)
    if verbose:
        print(r.groupby(["pos", "variant"])[["rho_all", "rho_unaffected", "hit_n", "hit_bias", "hit_mae",
                                             "next_n", "next_bias", "next_mae"]].mean().round(4).to_string())
    return r, pd.concat(calls, ignore_index=True)
