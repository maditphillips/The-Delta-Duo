"""Turn the model's week-1 output into the Weekly Data vs. Vibes CSVs.

Each note is composed from the drivers the model actually used -- projected
volume, scoring-position work, and the opponent's measured defence last season
-- so it explains why *this* week moved a player rather than narrating around
him. Notes are shared across scoring formats: the reasoning does not change
between PPR and half-PPR.

    python3 scripts/build-weekly-notes.py && node scripts/build-weekly.mjs
"""
from __future__ import annotations

import csv
import math
from pathlib import Path

import pandas as pd

SRC = Path("/tmp")
OUT = Path("data/weekly/2026/week-01")
FILES = {
    ("qb", "4pt"): "notes_qb_qb_4pt.csv", ("qb", "6pt"): "notes_qb_qb_6pt.csv",
    ("rb", "ppr"): "notes_rb_ppr.csv",    ("rb", "half"): "notes_rb_half_ppr.csv",
    ("wr", "ppr"): "notes_wr_ppr.csv",    ("wr", "half"): "notes_wr_half_ppr.csv",
    ("te", "ppr"): "notes_te_ppr.csv",    ("te", "half"): "notes_te_half_ppr.csv",
}


def upper_first(text: str) -> str:
    """Capitalise the first letter only. `str.capitalize` lower-cases the rest,
    which turns TB into Tb and EPA into epa."""
    return text[:1].upper() + text[1:] if text else text


def ordinal(n) -> str:
    if n is None or (isinstance(n, float) and math.isnan(n)):
        return ""
    n = int(round(n))
    suffix = "th" if 11 <= n % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def num(v, default=None):
    try:
        f = float(v)
        return default if math.isnan(f) else f
    except (TypeError, ValueError):
        return default


def defence_clause(r, side: str) -> str:
    """How the opponent's defence graded last season, in league-relative terms."""
    rk = num(r.get("rk_def_pass" if side == "pass" else "rk_def_rush"))
    if rk is None:
        return ""
    opp, unit = r["opponent"], "pass defence" if side == "pass" else "run defence"
    if rk >= 27:
        return f"{opp} carried one of the league's softest {unit}s last year, {ordinal(33 - rk)}-most EPA allowed"
    if rk >= 20:
        return f"{opp}'s {unit} graded {ordinal(33 - rk)}-worst by EPA last season"
    if rk <= 6:
        return f"{opp} brings a top-{int(rk)} {unit} by EPA allowed"
    if rk <= 12:
        return f"{opp}'s {unit} ranked {ordinal(rk)} in EPA allowed"
    return f"{opp}'s {unit} sat mid-pack last season"


def total_clause(r) -> str:
    """Vegas' view of how many points this offence scores. Rank is over the 32
    teams, 1 = highest implied total on the slate."""
    itt, rk = num(r.get("implied_team_total")), num(r.get("rk_team_total"))
    if itt is None:
        return ""
    if rk is not None and rk <= 6:
        return f"a {itt:.1f}-point implied total, {ordinal(rk)}-highest on the slate"
    if rk is not None and rk >= 27:
        return f"a thin {itt:.1f}-point implied total, {ordinal(33 - rk)}-lowest this week"
    return f"a {itt:.1f}-point implied total"


SLOT = {"qb": "QB", "rb": "RB", "wr": "WR", "te": "TE"}


def plural(n: float, singular: str, plural_form: str | None = None) -> str:
    """1.0 red-zone look, 2.4 red-zone looks, 0.5 goal-line rushes."""
    if 0.5 <= n < 1.5:
        return f"{n:.1f} {singular}"
    return f"{n:.1f} {plural_form or singular + 's'}"


def no_history_clause(r, pos: str) -> str:
    """A player the model has no NFL usage for -- almost always a rookie or
    someone who never saw the field. Quoting '0.0 projected targets' is true but
    useless, so say what he is actually being ranked on."""
    depth = num(r.get("depth_rank"))
    slot = f"{SLOT[pos]}{int(depth)}" if depth and depth <= 6 else "a depth role"
    if num(r.get("is_rookie"), 0) == 1:
        return f"no NFL usage to price yet, so he is ranked off draft capital and a {slot} slot"
    return f"no meaningful usage last season, ranked off a {slot} slot"


def role_clause(r, pos: str) -> str:
    et, ec = num(r.get("expected_targets"), 0), num(r.get("expected_carries"), 0)
    gl, rz = num(r.get("expected_gl_carries"), 0), num(r.get("expected_rz_targets"), 0)
    ts, ss = num(r.get("target_share_eb")), num(r.get("snap_share_eb"))
    depth = num(r.get("depth_rank"), 9)

    if pos == "qb":
        att, pyd = num(r.get("expected_pass_att"), 0), num(r.get("expected_pass_yards"), 0)
        bits = []
        if att >= 5:
            bits.append(f"{att:.0f} projected attempts for {pyd:.0f} yards")
        elif att > 0:
            bits.append("a thin projected workload")
        else:
            return no_history_clause(r, pos)
        if ec >= 4:
            bits.append(f"plus {ec:.1f} carries of his own")
        elif ec >= 2:
            bits.append(f"a little rushing on top ({ec:.1f} carries)")
        if gl >= 0.3:
            bits.append(plural(gl, "goal-line rush", "goal-line rushes"))
        return ", ".join(bits)

    if pos == "rb":
        if ec < 1 and et < 1:
            return no_history_clause(r, pos)
        bits = [f"{ec:.1f} projected carries"]
        if gl >= 0.5:
            bits.append(f"{gl:.1f} of them at the goal line")
        if et >= 3:
            bits.append(f"plus {et:.1f} targets out of the backfield")
        return ", ".join(bits)

    if et < 1:
        return no_history_clause(r, pos)
    bits = [f"{et:.1f} projected targets"]
    if ts is not None and ts >= 0.18:
        article = "an" if f"{ts:.0%}".startswith(("8", "11", "18")) else "a"
        bits.append(f"{article} {ts:.0%} target share")
    if rz >= 0.6:
        bits.append(plural(rz, "red-zone look"))
    if ss is not None and ss >= 0.8:
        bits.append(f"{ss:.0%} of the snaps")
    elif depth and depth >= 3 and (ss is None or ss < 0.6):
        bits.append("a rotational snap count")
    return ", ".join(bits)


def modifier_clause(r, skip_rookie: bool = False) -> str:
    out = []
    if num(r.get("is_out"), 0) == 1:
        return "RULED OUT — take him off your board."
    if num(r.get("is_questionable"), 0) == 1:
        prac = str(r.get("practice_status") or "").lower()
        how = ("did not practise" if "did not" in prac else
               "practised in a limited role" if "limited" in prac else
               "took a full practice" if "full" in prac else "status unclear")
        out.append(f"Questionable — {how}; drop him if he's downgraded.")
    if num(r.get("is_rookie"), 0) == 1 and not skip_rookie:
        out.append("Rookie, so the role is projected from draft capital and the depth chart, not observed.")
    elif num(r.get("changed_team"), 0) == 1:
        out.append("New team — his share is carried over, not measured here.")
    if num(r.get("hc_change"), 0) == 1:
        out.append("New head coach, so last season's team tendencies are discounted.")
    return " ".join(out)


def build_note(r, pos: str) -> str:
    side = "rush" if pos == "rb" else "pass"
    role, matchup, total = role_clause(r, pos), defence_clause(r, side), total_clause(r)
    lead = upper_first(role)
    if total:
        lead += f", on {total}"
    lead += "."
    second = f"{upper_first(matchup)}." if matchup else ""
    # The no-usage clause already says he is priced off draft capital, so the
    # rookie sentence would only repeat it.
    mod = modifier_clause(r, skip_rookie="usage" in role.lower())
    return " ".join(x for x in (lead, second, mod) if x).replace("  ", " ")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for (pos, variant), fname in FILES.items():
        df = pd.read_csv(SRC / fname)
        # Consensus is re-ranked inside our published list, so both columns
        # order the same players and the delta is a like-for-like comparison.
        df["_c"] = df["consensus_rank"].fillna(9999)
        df = df.sort_values(["_c", "rank_data"]).reset_index(drop=True)
        df["rank_vibes"] = range(1, len(df) + 1)
        df = df.sort_values("rank_data")
        rows = []
        for _, r in df.iterrows():
            rows.append({
                "rank_data": int(r["rank_data"]),
                "rank_vibes": int(r["rank_vibes"]),
                "player": r["player_name"],
                "team": r["team"],
                "note_data": build_note(r, pos),
                "note_vibes": "",
            })
        path = OUT / f"{pos}-{variant}.csv"
        with path.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["rank_data", "rank_vibes", "player",
                                               "team", "note_data", "note_vibes"])
            w.writeheader()
            w.writerows(rows)
        print(f"  {path}  ({len(rows)} players)")
    for stale in ("qb.csv", "rb.csv"):
        p = OUT / stale
        if p.exists():
            p.unlink()
            print(f"  removed sample {p}")


if __name__ == "__main__":
    main()
