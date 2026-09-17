"""Grade week 1: Wilson's board, MC's board, and preseason consensus.

Two scopes are graded. The full list is every player a voice ranked, which
answers "is the board any good". The startable scope is the top of each
position, which answers the question anyone actually has on a Sunday: the
back of a 80-deep receiver list is not a lineup decision.
"""
import csv, json, os, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr

SCRATCH = Path("/tmp/claude-0/-home-user-The-Delta-Duo/8c91f04b-24b4-5638-8c4d-a7fd7c62ef31/scratchpad")
WEEK = Path("data/weekly/2026/week-01")
OUT = Path("data/grades/2026")
st = json.load(open(SCRATCH / "st1.json"))
ids = {(r["player"], r["team"]): r["sleeper_id"]
       for r in csv.DictReader(open("data/sleeper-ids.csv"))}
by_name = {}
for (p, t), sid in ids.items():
    by_name.setdefault(p, sid)

# Two consensus voices, because they are not the same thing and only one of
# them is a fair opponent.
#
# The preseason board is FantasyPros' draft cheat sheet, last scraped nine days
# before kickoff. It is not trying to answer who scores most in week 1: it does
# not know the injuries, the depth charts or the matchups. Grading our weekly
# lists against it flattered us, and it was the only consensus this file had.
#
# The weekly board is what FantasyPros published for week 1 itself, scraped
# after the preseason and before the games. That is the like-for-like
# comparison and it is the one that counts.
#
# The two disagree more than their shared name suggests: Spearman 0.79 to 0.87
# between them, a median move of 9 spots at quarterback and 32 at receiver.
CONS, WCONS = {}, {}
NAME = {}
for pos, f in [("qb", "qb_qb_4pt"), ("rb", "rb_ppr"), ("wr", "wr_ppr"), ("te", "te_ppr")]:
    src = Path(f"/tmp/notes_{f}.csv")
    if not src.exists():
        continue
    for r in csv.DictReader(src.open()):
        if r.get("consensus_rank"):
            CONS[(pos, r["player_name"])] = float(r["consensus_rank"])
        if r.get("player_id"):
            NAME[r["player_id"]] = (pos, r["player_name"])

# The model lives on the rankings branch, not this one, so its path is given
# rather than assumed. Without it the weekly consensus is simply absent and the
# other three voices grade as before.
sys.path.insert(0, os.environ.get("DD_MODEL", "model"))
try:
    from dd import benchmark
    wk = benchmark.weekly_consensus(2026, 1)
    for _, x in wk.iterrows():
        hit = NAME.get(x.player_id)
        if hit and hit[0] == x.position.lower():
            WCONS[hit] = float(x.consensus_rank)
    print(f"  weekly consensus as scraped {wk.scraped.max()}: {len(WCONS)} matched")
except Exception as exc:
    print(f"  ! no weekly consensus ({exc})")

FILES = {("qb", "4pt"): "qb-4pt", ("qb", "6pt"): "qb-6pt",
         ("rb", "ppr"): "rb-ppr", ("rb", "half"): "rb-half",
         ("wr", "ppr"): "wr-ppr", ("wr", "half"): "wr-half",
         ("te", "ppr"): "te-ppr", ("te", "half"): "te-half"}
STARTERS = {"qb": 12, "rb": 24, "wr": 24, "te": 12}
# The startable scope: roughly one starter per team at quarterback and tight
# end, three deep at the positions a lineup starts two or three of.
TOPN = {"qb": 16, "rb": 36, "wr": 36, "te": 24}
VOICES = [("Wilson", "rank_data"), ("MC", "rank_vibes"),
          ("preseason consensus", "cons"), ("weekly consensus", "wcons")]
# The mirror carries PPR pages only, and one quarterback page at four points a
# passing touchdown. There is no half-PPR or six-point consensus to compare
# against at any date, so those lists get no consensus row rather than a PPR
# ranking wearing a half-PPR label.
CONS_VARIANT = {"qb": "4pt", "rb": "ppr", "wr": "ppr", "te": "ppr"}


def actual(sid, variant):
    """The week's real score, in the scoring the model was fitted to.

    Sleeper's own totals are close but not identical to ours: they dock one
    point for an interception and model/dd/config.py docks two. Everything
    else matches, so the correction is a single term, and it only moves
    quarterbacks. Grading a model fitted to minus two against a truth paying
    minus one would quietly punish it for the interceptions it was built to
    fear.
    """
    s = st.get(sid) or {}
    if not isinstance(s, dict):
        return 0.0
    ints = float(s.get("pass_int") or 0.0)
    base = float(s.get("pts_half_ppr" if variant == "half" else "pts_ppr") or 0.0)
    pts = base - ints                          # their -1 becomes our -2
    if variant == "6pt":                       # their 4 per passing TD becomes 6
        pts += 2 * float(s.get("pass_td") or 0.0)
    return pts


def pairwise(pred_rank, pts):
    """Of every pair whose real scores differed, how many did the list order
    correctly? Chance is 50%. Returned as the fraction it is, so that pairs
    from several positions can be added up rather than averaged."""
    n = len(pred_rank); right = total = 0
    for i in range(n):
        for j in range(i + 1, n):
            if pts[i] == pts[j]:
                continue
            total += 1
            better = i if pts[i] > pts[j] else j
            ahead = i if pred_rank[i] < pred_rank[j] else j
            right += (better == ahead)
    return right, total


def grade(rank, pts, k):
    """One voice on one set of players. Truth is ranked inside the same set,
    so spots off asks how badly the order was wrong, not how deep the set is."""
    right, total = pairwise(rank.to_numpy(), pts.to_numpy())
    truth = pts.rank(ascending=False, method="first").to_numpy()
    mine = rank.rank(method="first").to_numpy()
    got = pts.iloc[np.argsort(rank.to_numpy())[:k]].sum()
    best = pts.nlargest(k).sum()
    return {"n": len(rank), "pairwise": right / total if total else np.nan,
            "pw_right": right, "pw_total": total,
            "spots_off": float(np.abs(mine - truth).mean()),
            "spearman": spearmanr(-rank, pts).statistic,
            "pts_got": got, "pts_best": best, "pts_lost": best - got}


rows = []
for (pos, variant), stem in FILES.items():
    df = pd.DataFrame(list(csv.DictReader(open(WEEK / f"{stem}.csv"))))
    df["sid"] = [ids.get((p, t)) or by_name.get(p) for p, t in zip(df.player, df.team)]
    df["pts"] = [actual(s, variant) for s in df.sid]
    df["cons"] = [CONS.get((pos, p), np.nan) for p in df.player]
    df["wcons"] = [WCONS.get((pos, p), np.nan) for p in df.player]
    for who, col in VOICES:
        if col in ("cons", "wcons") and variant != CONS_VARIANT[pos]:
            continue
        r = pd.to_numeric(df[col], errors="coerce")
        ok = r.notna()
        if ok.sum() < STARTERS[pos]:
            continue
        d = df[ok].reset_index(drop=True); rr = r[ok].reset_index(drop=True)
        base = {"pos": pos.upper(), "variant": variant, "who": who}
        rows.append({**base, "scope": "full", **grade(rr, d.pts, STARTERS[pos])})
        # The startable scope. Each voice is graded on the players it chose to
        # put up there, which is the selection as well as the ordering.
        top = rr.nsmallest(TOPN[pos]).index
        rows.append({**base, "scope": f"top{TOPN[pos]}",
                     **grade(rr[top].reset_index(drop=True),
                             d.pts[top].reset_index(drop=True),
                             min(STARTERS[pos], len(top)))})

g = pd.DataFrame(rows)

# All four positions at once. Pairs are only ever compared inside a position,
# so the combined figure is the pairs added up, not the rates averaged. The
# eight lists are four league settings, and each is pooled on its own.
QBV, SKV = ["4pt", "6pt"], ["ppr", "half"]
alls = []
for qv in QBV:
    for sv in SKV:
        pick = g[((g.pos == "QB") & (g.variant == qv)) | ((g.pos != "QB") & (g.variant == sv))]
        for scope in pick.scope.unique():
            for who in pick.who.unique():
                s = pick[(pick.scope == scope) & (pick.who == who)]
                if len(s) < 4:            # a voice missing a position is not comparable
                    continue
                n = s.n.sum()
                alls.append({
                    "pos": "ALL", "variant": f"{qv}+{sv}", "who": who, "scope": scope,
                    "n": int(n), "pairwise": s.pw_right.sum() / s.pw_total.sum(),
                    "pw_right": int(s.pw_right.sum()), "pw_total": int(s.pw_total.sum()),
                    "spots_off": float((s.spots_off * s.n).sum() / n),
                    "spearman": float((s.spearman * s.n).sum() / n),
                    "pts_got": s.pts_got.sum(), "pts_best": s.pts_best.sum(),
                    "pts_lost": s.pts_lost.sum()})
g = pd.concat([g, pd.DataFrame(alls)], ignore_index=True)
OUT.mkdir(parents=True, exist_ok=True)
g.to_csv(OUT / "week-01.csv", index=False)
g.to_csv(SCRATCH / "week1_grades.csv", index=False)
print(f"graded {len(g)} rows")
