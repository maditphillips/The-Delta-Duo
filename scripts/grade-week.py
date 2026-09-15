"""Grade week 1: Wilson's board, MC's board, and preseason consensus."""
import csv, json, re, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr

SCRATCH = Path("/tmp/claude-0/-home-user-The-Delta-Duo/8c91f04b-24b4-5638-8c4d-a7fd7c62ef31/scratchpad")
WEEK = Path("data/weekly/2026/week-01")
st = json.load(open(SCRATCH / "st1.json"))
ids = {(r["player"], r["team"]): r["sleeper_id"]
       for r in csv.DictReader(open("data/sleeper-ids.csv"))}
by_name = {}
for (p, t), sid in ids.items():
    by_name.setdefault(p, sid)

# Preseason consensus, straight off the model's own export, as a third voice.
CONS = {}
for pos, f in [("qb", "qb_qb_4pt"), ("rb", "rb_ppr"), ("wr", "wr_ppr"), ("te", "te_ppr")]:
    p = Path(f"/tmp/notes_{f}.csv")
    if p.exists():
        for r in csv.DictReader(p.open()):
            if r.get("consensus_rank"):
                CONS[(pos, r["player_name"])] = float(r["consensus_rank"])

FILES = {("qb", "4pt"): "qb-4pt", ("qb", "6pt"): "qb-6pt",
         ("rb", "ppr"): "rb-ppr", ("rb", "half"): "rb-half",
         ("wr", "ppr"): "wr-ppr", ("wr", "half"): "wr-half",
         ("te", "ppr"): "te-ppr", ("te", "half"): "te-half"}
STARTERS = {"qb": 12, "rb": 24, "wr": 24, "te": 12}


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
    correctly? Chance is 50%."""
    n = len(pred_rank); right = total = 0
    for i in range(n):
        for j in range(i + 1, n):
            if pts[i] == pts[j]:
                continue
            total += 1
            better = i if pts[i] > pts[j] else j
            ahead = i if pred_rank[i] < pred_rank[j] else j
            right += (better == ahead)
    return right / total if total else np.nan


rows = []
for (pos, variant), stem in FILES.items():
    df = pd.DataFrame(list(csv.DictReader(open(WEEK / f"{stem}.csv"))))
    df["sid"] = [ids.get((p, t)) or by_name.get(p) for p, t in zip(df.player, df.team)]
    df["pts"] = [actual(s, variant) for s in df.sid]
    df["cons"] = [CONS.get((pos, p), np.nan) for p in df.player]
    # Ranked inside our own pool: a man we never listed cannot take a top spot.
    df["truth"] = df.pts.rank(ascending=False, method="first")
    k = STARTERS[pos]
    best = df.nlargest(k, "pts").pts.sum()
    for who, col in (("Wilson", "rank_data"), ("MC", "rank_vibes"), ("consensus", "cons")):
        r = pd.to_numeric(df[col], errors="coerce")
        ok = r.notna()
        if ok.sum() < k:
            continue
        d = df[ok].copy(); rr = r[ok]
        got = d.assign(_r=rr).nsmallest(k, "_r").pts.sum()
        rows.append({
            "pos": pos.upper(), "variant": variant, "who": who, "n": int(ok.sum()),
            "pairwise": pairwise(rr.to_numpy(), d.pts.to_numpy()),
            "spots_off": float(np.abs(rr.rank(method="first").to_numpy()
                                      - d.pts.rank(ascending=False, method="first").to_numpy()).mean()),
            "spearman": spearmanr(-rr, d.pts).statistic,
            "pts_got": got, "pts_best": best, "pts_lost": best - got,
        })
pd.DataFrame(rows).to_csv(SCRATCH / "week1_grades.csv", index=False)
print(f"graded {len(rows)} list-voice combinations")
