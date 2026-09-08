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


SLOT = {"qb": "QB", "rb": "RB", "wr": "WR", "te": "TE"}


def matchup_phrase(r, pos: str) -> str:
    """Vegas' view of the offence, then the defence it runs into. Leads with
    whichever is the sharper fact -- a league-extreme total, or an extreme
    defence -- because that is the reason the week moved him."""
    itt, rk = num(r.get("implied_team_total")), num(r.get("rk_team_total"))
    side = "rush" if pos == "rb" else "pass"
    unit = "run defense" if side == "rush" else "pass defense"
    drk = num(r.get("rk_def_pass" if side == "pass" else "rk_def_rush"))

    if itt is None:
        total = ""
    elif rk == 1:
        total = f"Highest implied total ({itt:.1f})"
    elif rk is not None and rk <= 6:
        total = f"{ordinal(rk)}-highest implied total ({itt:.1f})"
    elif rk is not None and rk >= 28:
        total = f"{ordinal(33 - rk)}-lowest implied total ({itt:.1f})"
    else:
        total = f"{itt:.1f}-point implied total"

    if drk is None:
        defense = ""
    elif drk >= 21:
        defense = f"{ordinal(33 - drk)}-worst {unit} by EPA last year"
    elif drk <= 5:
        defense = f"a top-{int(drk)} {unit} by EPA last year"
    elif drk <= 12:
        defense = f"the {ordinal(drk)}-best {unit} by EPA last year"
    else:
        defense = f"a mid-pack {unit} last year"

    if total and defense:
        return f"{total} against {defense}."
    return f"{total or upper_first(defense)}."


def blurb(r, pos: str) -> str:
    """One short clause on why the role supports that projection."""
    et, ec = num(r.get("expected_targets"), 0), num(r.get("expected_carries"), 0)
    gl, rz = num(r.get("expected_gl_carries"), 0), num(r.get("expected_rz_targets"), 0)
    ts, ss = num(r.get("target_share_eb")), num(r.get("snap_share_eb"))
    att = num(r.get("expected_pass_att"), 0)
    depth = num(r.get("depth_rank"), 9)
    rookie = num(r.get("is_rookie"), 0) == 1

    if pos == "qb":
        if att < 5:
            return "No starting workload priced in."
        if ec >= 5:
            return "Rushing floor carries the projection."
        if att >= 31:
            return "Situation and skillset point to a high pass volume."
        if att >= 28:
            return "Steady attempt volume, no rushing floor."
        return "Modest attempt projection."

    if pos == "rb":
        if ec < 1 and et < 1:
            return ("No NFL usage; priced on draft capital and the depth chart." if rookie
                    else "No real usage last year.")
        if ec >= 14 and gl >= 0.8:
            return "Bell-cow carries with the goal-line work."
        if ec >= 14:
            return "Bell-cow carries, little goal-line equity."
        if et >= 4:
            return "Value sits in the passing-down role."
        if ec >= 8:
            return "Committee lead with real volume."
        return "Backup volume."

    if et < 1:
        return ("No NFL usage; priced on draft capital and the depth chart." if rookie
                else "No real usage last year.")
    if ts is not None and ts >= 0.25:
        return "Alpha target share." if rz < 1 else "Alpha target share with red-zone work."
    if ts is not None and ts >= 0.18:
        return "Clear starter's target share." if rz < 1 else "Starter's share plus red-zone looks."
    if ss is not None and ss < 0.6 and depth >= 3:
        return "Rotational snaps cap the ceiling."
    return "Secondary role in the passing game."


def flags(r) -> str:
    """Only what changes a start/sit call, in as few words as possible."""
    out = []
    if num(r.get("is_out"), 0) == 1:
        return "RULED OUT."
    if num(r.get("is_questionable"), 0) == 1:
        prac = str(r.get("practice_status") or "").lower()
        how = ("DNP" if "did not" in prac else "limited" if "limited" in prac
               else "full" if "full" in prac else "no practice detail")
        out.append(f"Questionable ({how}).")
    if num(r.get("hc_change"), 0) == 1:
        out.append("New HC.")
    if num(r.get("changed_team"), 0) == 1:
        out.append("New team.")
    return " ".join(out)


def build_note(r, pos: str) -> str:
    return " ".join(x for x in (matchup_phrase(r, pos), blurb(r, pos), flags(r)) if x)


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
                "opponent": r.get("opponent", ""),
                "is_home": int(num(r.get("is_home"), 0)),
                "proj": round(float(r["proj"]), 1),
                "note_data": build_note(r, pos),
                "note_vibes": "",
            })
        path = OUT / f"{pos}-{variant}.csv"
        with path.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["rank_data", "rank_vibes", "player", "team",
                                               "opponent", "is_home", "proj",
                                               "note_data", "note_vibes"])
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
