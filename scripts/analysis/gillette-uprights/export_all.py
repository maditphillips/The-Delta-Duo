"""Compute the kicking profile for every NFL venue and emit src/data/stadiums.ts.

Every venue is scored against a leave-one-out baseline: the expected-make model
(distance spline + season fixed effects) is refit for each venue with that
venue's own kicks held out, so no stadium is graded against itself.
"""
import json, os, re, warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, statsmodels.api as sm, statsmodels.formula.api as smf
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "..", "src", "data", "stadiums.ts")
MIN_VIS = 150          # minimum visiting-kicker FG attempts for a venue to qualify
FGFORM = "made ~ B1+B2+B3+B4+B5 + C(season)"

K = pd.read_parquet(f"{HERE}/kicks_2002_2025.parquet")
P = pd.read_parquet(f"{HERE}/punts_2002_2025.parquet")
D = pd.read_parquet(f"{HERE}/fourth_2002_2025.parquet")
for df in (K, P, D):
    df["is_home_kick"] = df.posteam.eq(df.home_team)
    df["parity"] = np.where(df.qtr.isin([1, 3]), "A", "B")

fg = K[K.field_goal_attempt.eq(1) & K.field_goal_result.notna()
       & K.kick_distance.between(15, 75)].copy()
fg["made"] = fg.field_goal_result.eq("made").astype(int)
F = fg[fg.field_goal_result.ne("blocked")].copy()

# Fixed spline basis computed ONCE over every kick, so each leave-one-out refit
# shares identical knots and a held-out venue can never fall outside them.
from patsy import dmatrix
_B = dmatrix("bs(kick_distance, df=5) - 1", {"kick_distance": F.kick_distance.values},
             return_type="dataframe")
for i in range(5):
    F[f"B{i+1}"] = _B.iloc[:, i].values

VENUES = [s for s, g in F.groupby("stadium_id") if (~g.is_home_kick).sum() >= MIN_VIS]
print(f"{len(VENUES)} venues clear the {MIN_VIS}-visiting-kick threshold")

# leave-one-out expected-make: one refit per venue
F["xmake"] = np.nan
for sid in VENUES:
    m = smf.glm(FGFORM, data=F[F.stadium_id.ne(sid)], family=sm.families.Binomial()).fit()
    F.loc[F.stadium_id.eq(sid), "xmake"] = m.predict(F[F.stadium_id.eq(sid)])
    print(".", end="", flush=True)
rest = F.xmake.isna()
F.loc[rest, "xmake"] = smf.glm(FGFORM, data=F[~F.stadium_id.isin(VENUES)],
                               family=sm.families.Binomial()).fit().predict(F[rest])
print(" baselines fit")

# punts: gross distance vs field-position/season expectation, leave-one-out by venue
pu = P[P.punt_attempt.eq(1) & P.kick_distance.between(15, 80) & P.punt_blocked.ne(1)
       & P.yardline_100.notna() & P.qtr.le(4)].copy()
_PB = dmatrix("bs(yl, df=4) - 1", {"yl": pu.yardline_100.astype(float).values}, return_type="dataframe")
for i in range(4):
    pu[f"Y{i+1}"] = _PB.iloc[:, i].values
pu["poe"] = np.nan
for sid in VENUES:
    sub = pu.stadium_id.eq(sid)
    if sub.sum() < 50:
        continue
    m = smf.ols("kick_distance ~ Y1+Y2+Y3+Y4+C(season)", data=pu[~sub]).fit()
    pu.loc[sub, "poe"] = pu.loc[sub, "kick_distance"] - m.predict(pu[sub])

ko = P[P.kickoff_attempt.eq(1) & P.season.between(2011, 2023)].copy()
ko["tb"] = ko.touchback.eq(1).astype(int)
kd = ko[ko.kick_distance.between(40, 80)].copy()
kd["koe"] = kd.kick_distance - smf.ols("kick_distance ~ C(season)", data=kd).fit().predict(kd)

D4 = D[D.yardline_100.notna() & D.play_type.notna() & D.qtr.le(4)].copy()
D4["fga"] = D4.field_goal_attempt.eq(1).astype(int)
D4["fgd"] = D4.yardline_100 + 17
LONG = D4[D4.fgd.between(50, 62) & D4.ydstogo.between(1, 10) & D4.wp.between(0.05, 0.95)]
LG_HOME_KICK = LONG[LONG.is_home_kick].fga.mean()

miss = F[F.made.eq(0)].copy()
tail = miss.desc.str.extract(r"No Good,\s*([^.]*?),\s*(?:Center|Holder)", flags=re.I)[0].fillna("")
miss["wide"] = tail.str.contains("Wide", case=False)
miss["short"] = tail.str.contains("Short", case=False)
miss = miss[tail.str.len().gt(0)]

def finite(x):
    """None for anything that is not a real number, so NaN can never reach the
    generated TypeScript (json.dumps would otherwise emit a bare `NaN`)."""
    if x is None:
        return None
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    return None if not np.isfinite(f) else f


def rnd(x, places=1):
    f = finite(x)
    return None if f is None else round(f, places)


def stats_for(s):
    if len(s) == 0:
        return None
    v = (s.xmake * (1 - s.xmake)).sum()
    return dict(n=int(len(s)), act=float(s.made.mean()), exp=float(s.xmake.mean()),
                diff=float(s.made.mean() - s.xmake.mean()),
                z=float((s.made.sum() - s.xmake.sum()) / np.sqrt(v)) if v > 0 else 0.0)

rows = []
for sid in VENUES:
    g = F[F.stadium_id.eq(sid)]
    vis, home = g[~g.is_home_kick], g[g.is_home_kick]
    v, h = stats_for(vis), stats_for(home)
    vv = (vis.xmake * (1 - vis.xmake)).sum() / len(vis) ** 2
    hv = (home.xmake * (1 - home.xmake)).sum() / len(home) ** 2
    hosts = g.drop_duplicates("game_id").home_team.value_counts()
    residents = sorted(hosts[hosts >= 20].index)
    seasons = sorted(g.season.unique())

    band = {}
    for lo, hi, key in [(15, 29, "u30"), (30, 39, "d30"), (40, 49, "d40"), (50, 75, "d50")]:
        b = stats_for(vis[vis.kick_distance.between(lo, hi)])
        band[key] = None if not b or b["n"] < 10 else {"diff": rnd(b["diff"] * 100), "n": b["n"]}

    wsub = vis.copy(); wsub["w"] = pd.to_numeric(wsub.wind, errors="coerce")
    windy = stats_for(wsub[wsub.w.ge(15)])

    pv = pu[pu.stadium_id.eq(sid) & pu.poe.notna()]
    kv = kd[kd.stadium_id.eq(sid)]
    tv = ko[ko.stadium_id.eq(sid)]
    lv = LONG[LONG.stadium_id.eq(sid) & LONG.is_home_kick]
    mv = miss[miss.stadium_id.eq(sid) & ~miss.is_home_kick]

    pa = stats_for(vis[vis.parity.eq("A")]); pb = stats_for(vis[vis.parity.eq("B")])
    byseason = [{"season": int(y), "n": int((vis.season == y).sum()),
                 "diff": rnd((vis[vis.season == y].made - vis[vis.season == y].xmake).mean() * 100)}
                for y in sorted(vis.season.unique()) if (vis.season == y).sum() >= 5]

    rows.append(dict(
        id=sid,
        name=g.stadium.mode().iat[0],
        teams=residents,
        roof=g.roof.mode().iat[0] if g.roof.notna().any() else "unknown",
        surface=g.surface.mode().iat[0] if g.surface.notna().any() else "unknown",
        firstSeason=int(seasons[0]), lastSeason=int(seasons[-1]),
        games=int(g.game_id.nunique()),
        visN=v["n"], visPct=rnd(v["act"] * 100), visExp=rnd(v["exp"] * 100),
        visDiff=rnd(v["diff"] * 100), visZ=rnd(v["z"], 2),
        homeN=h["n"], homePct=rnd(h["act"] * 100), homeDiff=rnd(h["diff"] * 100),
        gap=rnd((h["diff"] - v["diff"]) * 100),
        gapZ=rnd((h["diff"] - v["diff"]) / np.sqrt(vv + hv), 2),
        bands=band,
        windyDiff=None if not windy or windy["n"] < 25 else rnd(windy["diff"] * 100),
        windyN=0 if not windy else windy["n"],
        puntOE=None if len(pv) < 200 else rnd(pv.poe.mean(), 2),
        puntN=int(len(pv)),
        koDistOE=None if len(kv) < 200 else rnd(kv.koe.mean(), 2),
        touchback=None if len(tv) < 200 else rnd(tv.tb.mean() * 100),
        homeLongKickRate=None if len(lv) < 40 else rnd(lv.fga.mean() * 100),
        homeLongKickN=int(len(lv)),
        wideOnly=None if len(mv) < 25 else rnd(((mv.wide) & ~mv.short).mean() * 100),
        missN=int(len(mv)),
        dirSplit=None if not pa or not pb or min(pa["n"], pb["n"]) < 40
                 else rnd((pb["diff"] - pa["diff"]) * 100),
        bySeason=byseason,
    ))

df = pd.DataFrame(rows).sort_values("visDiff")
for col, key in [("visDiff", "visRank"), ("gap", "gapRank")]:
    df[key] = df[col].rank(ascending=(col == "visDiff"), method="min").astype(int)
rows = df.to_dict("records")

lg = F[~F.stadium_id.isin(VENUES) | True]
league = dict(
    venues=len(rows), seasons="2002-2025",
    totalFG=int(len(F)), totalPunts=int(len(pu)),
    leagueHome=rnd(F[F.is_home_kick].made.mean() * 100),
    leagueVisitor=rnd(F[~F.is_home_kick].made.mean() * 100),
    leagueLongKickRate=rnd(LG_HOME_KICK * 100),
    meanGap=rnd(df.gap.mean()), sdGap=rnd(df.gap.std()),
    gapChi2P=rnd(stats.chi2.sf((df.gapZ ** 2).sum(), len(df)), 3),
    visChi2P=rnd(stats.chi2.sf((df.visZ ** 2).sum(), len(df)), 4),
)

def scrub(o, path=""):
    """Recursively replace non-finite numbers with None, reporting each one so a
    silent NaN can never reach the generated TypeScript."""
    if isinstance(o, dict):
        return {k: scrub(v, f"{path}.{k}") for k, v in o.items()}
    if isinstance(o, list):
        return [scrub(v, f"{path}[{i}]") for i, v in enumerate(o)]
    if isinstance(o, float) and not np.isfinite(o):
        print(f"  scrubbed non-finite at {path}")
        return None
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        f = float(o)
        if not np.isfinite(f):
            print(f"  scrubbed non-finite at {path}")
            return None
        return f
    return o


def ts(o): return json.dumps(scrub(o), indent=2, allow_nan=False)
with open(OUT, "w") as f:
    f.write(f'''// NFL kicking venues — generated by scripts/analysis/gillette-uprights/export_all.py
// Do not edit by hand; rerun the script to refresh.
//
// Every field goal 2002-2025 from nflverse play-by-play. Each venue is scored
// against a LEAVE-ONE-OUT baseline: the expected-make model (natural spline in
// kick distance + season fixed effects) is refit for each venue with that
// venue's own kicks held out, so no stadium is graded against itself. Blocked
// kicks are excluded (a block is a line-of-scrimmage failure, not an aiming
// one). Venues need {MIN_VIS}+ visiting-kicker attempts to qualify.

export type StadiumBand = {{ diff: number; n: number }};

export type StadiumBands = {{ u30: StadiumBand | null; d30: StadiumBand | null; d40: StadiumBand | null; d50: StadiumBand | null }};

export type StadiumSeason = {{ season: number; n: number; diff: number }};

export type Stadium = {{
  id: string;
  name: string;
  teams: string[];
  roof: string;
  surface: string;
  firstSeason: number;
  lastSeason: number;
  games: number;
  /** visiting-kicker FG attempts */
  visN: number;
  visPct: number;
  visExp: number;
  /** actual minus expected, percentage points */
  visDiff: number;
  visZ: number;
  visRank: number;
  homeN: number;
  homePct: number;
  homeDiff: number;
  /** home minus visitor, both distance-adjusted */
  gap: number;
  gapZ: number;
  gapRank: number;
  bands: StadiumBands;
  windyDiff: number | null;
  windyN: number;
  /** gross punt distance vs expectation, yards */
  puntOE: number | null;
  puntN: number;
  koDistOE: number | null;
  touchback: number | null;
  /** share of 4th-down 50+ yd chances the home team kicked */
  homeLongKickRate: number | null;
  homeLongKickN: number;
  wideOnly: number | null;
  missN: number;
  /** Q2+Q4 minus Q1+Q3 for visiting kickers — a direction-of-play proxy */
  dirSplit: number | null;
  bySeason: StadiumSeason[];
}};

export const stadiumMeta = {ts(league)} as const;

export const stadiums: Stadium[] = {ts(rows)};
''')
print("wrote", os.path.normpath(OUT), f"({len(rows)} venues)")
