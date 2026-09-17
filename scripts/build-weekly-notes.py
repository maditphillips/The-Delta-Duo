"""Turn the model's output for one week into the Weekly Data vs. Vibes CSVs.

Each note is composed from the drivers the model actually used -- projected
volume, scoring-position work, and the opponent's measured defence last season
-- so it explains why *this* week moved a player rather than narrating around
him. Notes are shared across scoring formats: the reasoning does not change
between PPR and half-PPR.

    python3 scripts/build-weekly-notes.py --week 2 && node scripts/build-weekly.mjs

Week 1 and the weeks after it come from two different models and two different
export paths, so the source is an argument rather than a constant. Week 1 was
written to /tmp by `dd.cli predict` with a notes_ prefix and is left alone;
week 2 onward is written by `dd.cli week` into model/outputs/<season>/week-NN.
"""
from __future__ import annotations

import argparse
import os
import sys
import csv
import math
from pathlib import Path

import pandas as pd

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--season", type=int, default=2026)
ap.add_argument("--week", type=int, default=1)
ap.add_argument("--src", default=None, help="where the model's CSVs are")
ap.add_argument("--prefix", default=None, help="filename prefix on those CSVs")
args = ap.parse_args()

SEASON, WEEK = args.season, args.week
# Week 1 kept its original home; everything after it reads the model's own
# output directory, which is committed rather than living in /tmp.
if args.src is not None:
    SRC, PREFIX = Path(args.src), (args.prefix or "")
elif WEEK == 1:
    SRC, PREFIX = Path("/tmp"), "notes_"
else:
    SRC, PREFIX = Path(f"model/outputs/{SEASON}/week-{WEEK:02d}"), ""
OUT = Path(f"data/weekly/{SEASON}/week-{WEEK:02d}")
# Players ruled out after the model last ran. nflverse publishes the official
# report on its own schedule, and a Sunday-morning ruling lands hours after it;
# this file is the manual override so a ruled-out player never ships in a list.
RULED_OUT = Path("data/weekly/ruled-out.csv")
# MC's board and his takes, from tools/mc-rankings.html. He ranks once per
# position, not once per scoring format: consensus differs between PPR and
# half-PPR for two backs and nobody else, and his opinion of a player does not
# change with a league's reception setting.
MC = Path(f"data/weekly/{SEASON}/week-{WEEK:02d}/mc-rankings.csv")
# Hand placements on Wilson's board. The model is not touched; a player is
# lifted out and reinserted, and everyone he passes moves down one. Each row
# carries the reason, because an override with no argument behind it is just
# the vibes list wearing the data list's colours.
MANUAL = Path("data/weekly/manual-ranks.csv")
# Men promoted onto the board from just off it, when someone published is out.
# They are pulled from the model's own deeper pool rather than invented, so a
# promoted player arrives with a real floor, median, ceiling and top-12 odds.
ADDED = Path("data/weekly/added.csv")
# Hand placements on MC's board. His own file is one list per position, because
# a player's rank is his opinion of the player and that does not change with a
# league's reception setting. Membership does though, and occasionally so does
# he: a target hog is worth more in PPR than in half. These rows are keyed by
# scoring format so one can be moved in one list without touching the other.
MC_MANUAL = Path("data/weekly/mc-manual-ranks.csv")
# Keyed by position and scoring format, valued by the model's own stem for
# that list. The prefix and directory are decided above, because they differ
# between week 1 and the weeks after it.
FILES = {
    ("qb", "4pt"): "qb_qb_4pt", ("qb", "6pt"): "qb_qb_6pt",
    ("rb", "ppr"): "rb_ppr",    ("rb", "half"): "rb_half_ppr",
    ("wr", "ppr"): "wr_ppr",    ("wr", "half"): "wr_half_ppr",
    ("te", "ppr"): "te_ppr",    ("te", "half"): "te_half_ppr",
}


def model_csv(stem: str) -> Path:
    return SRC / f"{PREFIX}{stem}.csv"


def pool_csv(stem: str) -> Path:
    return SRC / f"{PREFIX}{stem}_pool.csv"


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


def plural(n: float, singular: str, plural_form: str | None = None) -> str:
    """1.0 red-zone look, 2.4 red-zone looks, 0.5 goal-line rushes."""
    if 0.5 <= n < 1.5:
        return f"{n:.1f} {singular}"
    return f"{n:.1f} {plural_form or singular + 's'}"


def no_history_clause(r, pos: str) -> str:
    """Someone the model has no NFL usage for. Quoting "0.0 targets" is true but
    useless, so say what he is actually being ranked on."""
    depth = num(r.get("depth_rank"))
    slot = f"{SLOT[pos]}{int(depth)}" if depth and depth <= 6 else "a depth role"
    if num(r.get("is_rookie"), 0) == 1:
        return f"No NFL usage to price yet, so he is ranked off draft capital and a {slot} slot"
    return f"No meaningful usage last season, ranked off a {slot} slot"


# This season's defence, ranked over the weeks strictly before this one. The
# model does not read any of this: the opponent group was dropped in ablation
# because a defence measured last year says almost nothing about one week this
# year, and the matchup layer built on this season's measure scored identically
# when every player was joined to a defence chosen at random. So the clause is
# context for a reader, not a driver of the number beside it.
#
# Last season and this are both quoted because neither is worth trusting alone.
# Week 1 agreed with last season at rho 0.002 against the pass and 0.106
# against the run, which is to say not at all: Houston were 6th against the
# pass last year and 27th in week 1, Denver 5th against the run and 32nd. One
# of those is a small sample and the other is a stale one, and a reader who
# sees both knows exactly what he is looking at.
DEF_TO_DATE = {}


def defense_to_date() -> dict:
    """Rank the 32 defences on what they have given up this season so far."""
    sys.path.insert(0, os.environ.get("DD_MODEL", "model"))
    try:
        from dd import defense
    except Exception as exc:
        print(f"  ! no in-season defence ({exc}); last season only")
        return {}
    d = defense.build()
    d = d[(d.season == SEASON) & (d.week < WEEK)]
    if d.empty:
        return {}
    g = d.groupby("team").agg(pass_epa=("def_epa_pass", "mean"),
                              rush_epa=("def_epa_rush", "mean"),
                              games=("week", "nunique"))
    g["rk_pass"] = g.pass_epa.rank(method="first")
    g["rk_rush"] = g.rush_epa.rank(method="first")
    print(f"  in-season defence: {len(g)} teams over {int(g.games.max())} week(s)")
    return {t: (int(x.rk_pass), int(x.rk_rush), int(x.games))
            for t, x in g.iterrows()}


def rank_words(rk: float, unit: str, when: str) -> str:
    """The same ladder for either season, so the two halves read alike."""
    if rk is None:
        return ""
    if rk == 32:
        return f"the worst {unit} in the league by EPA {when}"
    if rk >= 21:
        return f"{ordinal(33 - int(rk))}-worst {unit} by EPA {when}"
    if rk == 1:
        return f"the best {unit} in the league by EPA {when}"
    if rk <= 5:
        return f"a top-{int(rk)} {unit} by EPA {when}"
    if rk <= 12:
        return f"the {ordinal(int(rk))}-best {unit} by EPA {when}"
    return f"a mid-pack {unit} {when}"


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

    defense = rank_words(drk, unit, "last year")

    # What that same defence has given up this season. One plain ranking, with
    # the sample it rests on stated, so a reader can weigh one game himself.
    now = DEF_TO_DATE.get(r.get("opponent"))
    since = ""
    if now:
        rk_now = now[0] if side == "pass" else now[1]
        games = now[2]
        span = ("in week 1" if games == 1 and WEEK == 2
                else f"through {games} game{'s' * (games != 1)}")
        since = f" They rank {ordinal(rk_now)} of 32 against the {side} {span}."

    head = (f"{total} against {defense}." if total and defense
            else f"{total or upper_first(defense)}.")
    return head + since


# The volume a note quotes has two possible sources and they are not the same
# number. expected_* is built from last season's shares times a projected team
# volume, which is what week 1 had and all it could have had. From week 2 the
# model ranks on b_*, this season blended into last, and quoting the preseason
# figure next to an in-season ranking made the notes describe a board nobody
# was looking at. It read worst on the men with no last season at all: Jadarian
# Price carried ten times in week 1 and his note said he had no NFL usage to
# price, because his preseason share was zero and always would be.
VOLUME = {"targets": "expected_targets", "carries": "expected_carries",
          "attempts": "expected_pass_att", "snap_share": "snap_share_eb",
          "target_share": "target_share_eb", "carry_share": "rush_share_eb"}


def vol(r, name: str, default=None):
    """This season blended into last where the model has it, last season where
    it does not."""
    v = num(r.get(f"b_{name}"))
    return v if v is not None else num(r.get(VOLUME[name]), default)


def a_share(v: float, what: str) -> str:
    """"an 84% carry share", "a 46% carry share". Spoken, not spelled: it is
    the digit that decides, so 8, 11 and 18 take "an" and 80 does not."""
    pct = f"{v:.0%}"
    return f"{'an' if pct.startswith(('8', '11', '18')) else 'a'} {pct} {what}"


SUFFIXES = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv", "v"}


def surname(r) -> str:
    """What to call him in a sentence: the last real word of his name."""
    parts = [w for w in str(r.get("player_name") or "").split()
             if w.lower().strip(".") not in SUFFIXES]
    return parts[-1] if parts else "he"


def played(r, pos: str) -> str:
    """What he has actually done this season, kept apart from what is projected.

    Every number in blurb() is a forecast for the coming week, including the
    ones that look like history: b_carries is this season blended into last,
    which is the model's expectation and not a count of anything. Read next to
    a rank it was impossible to tell which was which, so the measured half is
    now said separately and labelled.

    The sd_ columns are expanding means over the weeks strictly before this
    one, so after a single game they are that game and can be quoted as counts.
    From the second game they are averages and have to be called averages.
    """
    n = num(r.get("sd_games"), 0)
    if not n:
        return ""
    ca, ta, at = (num(r.get("sd_carries")), num(r.get("sd_targets")),
                  num(r.get("sd_attempts")))
    cs, ts, ss = (num(r.get("sd_carry_share")), num(r.get("sd_target_share")),
                  num(r.get("sd_snap_share")))
    one = n < 2
    fmt = (lambda v, w: f"{v:.0f} {w}") if one else (lambda v, w: f"{v:.1f} {w} a game")
    bits = []
    if pos == "qb":
        if at:
            bits.append(fmt(at, "attempt" if one and at == 1 else "attempts"))
        if ca:
            bits.append(fmt(ca, "carry" if one and ca == 1 else "carries"))
    elif pos == "rb":
        if ca:
            bits.append(fmt(ca, "carry" if one and ca == 1 else "carries"))
        if cs is not None:
            bits.append(a_share(cs, "carry share"))
        if ta:
            bits.append(fmt(ta, "target" if one and ta == 1 else "targets"))
    else:
        if ta:
            bits.append(fmt(ta, "target" if one and ta == 1 else "targets"))
        if ts is not None:
            bits.append(a_share(ts, "target share"))
    if ss is not None:
        bits.append(f"{ss:.0%} of the snaps")
    if not bits:
        return ""
    # A man with nothing before this season has a blend with nothing to blend:
    # b_ falls back to sd_ exactly, so the projection IS the history and saying
    # both is saying one thing twice. Jadarian Price read "projected 10.0
    # carries" and then "last week he had 10 carries", which is not a second
    # fact. Say why they match instead.
    # Whether the blend had anything to blend, asked of the prior itself rather
    # than inferred from the two halves matching. Jonathan Taylor averaged
    # exactly 19.0 carries a game last season and ran exactly 19 times in week
    # 1, so his blend returned 19.0 and an equality test called him a man with
    # no NFL history. He is the opposite of that.
    key = {"qb": "attempts", "rb": "carries"}.get(pos, "targets")
    if one and num(r.get(f"{key}_per_game")) is None:
        # The two halves are the same numbers, because the blend has nothing to
        # blend. Repeating them is not a second fact, so the space goes to why
        # one game is enough to move him: the k search put the weight on a
        # single game of role at every position, which is the whole reason his
        # rank jumped at all.
        game = "week 1" if WEEK == 2 else "his one game"
        return (f"Usage in {game} is actually fairly predictive. With only one"
                f" game on the books, {surname(r)}'s projection leans on his"
                f" exact usage {'last week' if WEEK == 2 else 'in it'}. This"
                " will change as he gets more games under his belt.")
    body = ", ".join(bits[:-1]) + (f" and {bits[-1]}" if len(bits) > 1 else bits[-1])
    if one:
        lead = "Last week he had" if WEEK == 2 else "In his one game this season he had"
    else:
        lead = f"Across {n:.0f} games he has averaged"
    return f"{lead} {body}."


def blurb(r, pos: str) -> str:
    """The volume behind the projection, in the model's own numbers.

    Never asserts the absence of something the model cannot see -- an earlier
    version told readers Josh Allen had "no rushing floor", which was a
    threshold artefact rather than a finding.
    """
    et, ec = vol(r, "targets", 0), vol(r, "carries", 0)
    gl, rz = num(r.get("expected_gl_carries"), 0), num(r.get("expected_rz_targets"), 0)
    ts, ss = vol(r, "target_share"), vol(r, "snap_share")
    cs = vol(r, "carry_share")
    att = vol(r, "attempts", 0)
    pyd = num(r.get("expected_pass_yards"), 0)
    # There is no in-season passing-yards figure to blend, because yards a
    # throw is an efficiency measure and the model deliberately leaves those on
    # last season. Holding the implied yards per attempt and moving the volume
    # keeps the two halves of the sentence talking about the same quarterback.
    pre_att = num(r.get("expected_pass_att"), 0)
    if pre_att and att:
        pyd = pyd * att / pre_att
    depth = num(r.get("depth_rank"), 9)
    rookie = num(r.get("is_rookie"), 0) == 1

    if pos == "qb":
        if att < 5:
            return no_history_clause(r, pos)
        bits = [f"Projected {att:.0f} attempts for {pyd:.0f} yards"]
        if ec >= 4:
            bits.append(f"plus {ec:.1f} carries of his own")
        elif ec >= 2:
            bits.append(f"{ec:.1f} carries of his own")
        if gl >= 0.3:
            bits.append(plural(gl, "goal-line rush", "goal-line rushes"))
        return ", ".join(bits) + "."

    if pos == "rb":
        if ec < 1 and et < 1:
            return no_history_clause(r, pos) + "."
        bits = [f"Projected {ec:.1f} carries"]
        # "of them" has to follow the carries it refers to, so the share comes
        # after the goal-line clause rather than between the two.
        if gl >= 0.5:
            bits.append(f"{gl:.1f} of them at the goal line")
        # A count says what he got; a share says whether he is the back. Ten
        # carries is a committee in Arizona and most of the backfield in
        # Seattle, and the note should be able to tell them apart.
        if cs is not None:
            bits.append(a_share(cs, "carry share"))
        if et >= 2:
            bits.append(f"{et:.1f} targets out of the backfield")
        if ss is not None:
            bits.append(f"{ss:.0%} of the snaps")
        return ", ".join(bits) + "."

    if et < 1:
        return no_history_clause(r, pos) + "."
    bits = [f"Projected {et:.1f} targets"]
    if ts is not None:
        bits.append(a_share(ts, "target share"))
    if rz >= 0.6:
        bits.append(plural(rz, "red-zone look"))
    if ss is not None:
        bits.append(f"{ss:.0%} of the snaps")
    elif depth and depth >= 3:
        bits.append("a rotational snap count")
    return ", ".join(bits) + "."


def outlook(r) -> str:
    """The spread the quantile models give him, and his shot at a top-12 week.

    The median is here because it, not the projection, is what drives the
    top-12 number, and without it the two look like they contradict each other.
    Derrick Henry projects below Saquon Barkley and still shows the better shot
    at a top-12 week: Henry's median week is 16 and Barkley's is 15, so Henry
    clears the bar more often, while Barkley's higher projection rests on a
    ceiling four points taller. Top-12 is a threshold -- points past it do not
    count twice."""
    lo, mid, hi = (num(r.get("floor_q20")), num(r.get("median_q50")),
                   num(r.get("ceiling_q90")))
    proj, p12 = num(r.get("proj")), num(r.get("p_top12"))
    bits = []
    if lo is not None and hi is not None:
        span = f"Range {lo:.0f}-{hi:.0f}"
        if mid is not None:
            span += f" around a median of {mid:.0f}"
        bits.append(span)
    if p12 is not None:
        bits.append(f"{p12:.0%} shot at a top-12 week")
    text = (", ".join(bits) + ".") if bits else ""
    # Which way the range leans, and only when it leans far enough to change
    # how you would use him.
    #
    # The measure is where the median sits between floor and ceiling, not how
    # wide the range is -- width alone says the wrong thing. Derrick Henry
    # spans 7.7 to 20.4 and Saquon Barkley 9.6 to 22.8, so Barkley's range is
    # the wider one, yet Henry is the safer start: his median sits 67% of the
    # way up his band against Barkley's 40%. Henry has more weeks near his top
    # than his bottom; Barkley's projection is carried by his best ones. The
    # Tilt is bunched -- its quartiles run 0.27 to 0.40 across all four
    # positions -- so an absolute cut-off would either fire on a quarter of the
    # board or on nobody. The clause is ranked within its own list instead and
    # goes to the top and bottom tenth, which is rare enough to mean something.
    tilt = r.get("_tilt")
    if tilt is not None and not pd.isna(tilt):
        if tilt >= 0.9:
            text += (" Safer than his projection reads: more of his weeks land"
                     " near the top of that range than the bottom.")
        elif tilt <= 0.1:
            text += (" Ceiling-dependent: his median sits at the low end of that"
                     " range, so the projection leans on his best weeks.")
    return text


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
    return " ".join(x for x in (matchup_phrase(r, pos), blurb(r, pos), played(r, pos),
                                outlook(r), flags(r)) if x)


# Sleeper's tags, and which of them mean he is not playing. Questionable is
# not among them on purpose: a hundred and twenty players carry it in a normal
# week and most of them start. Those are printed for a human to rule on
# instead, which is what data/weekly/ruled-out.csv is for.
SLEEPER = "https://api.sleeper.app/v1"
SLEEPER_CACHE = Path("/tmp/sleeper-players.json")
SLEEPER_MAX_AGE = 6 * 3600
NOT_PLAYING = {"Out", "IR", "PUP", "Doubtful", "NA", "DNR", "Sus"}
INJURIES = pd.DataFrame(columns=["player", "team", "pos", "status", "part"])


def sleeper_status() -> pd.DataFrame:
    """Every skill player carrying an injury tag right now.

    nflverse publishes the official report, and for this season it is all but
    empty: eleven rows for the whole of 2026, none past week 1, so is_out and
    is_questionable are dead columns and a man on IR shipped in the rankings
    with no flag on him at all. Sleeper's roster carries the same field, keeps
    it current to the hour, and had Ja'Kobi Lane as Doubtful with a wrist when
    ours had nothing.
    """
    import json
    import time
    import urllib.request
    stale = (not SLEEPER_CACHE.exists()
             or time.time() - SLEEPER_CACHE.stat().st_mtime > SLEEPER_MAX_AGE)
    if stale:
        try:
            with urllib.request.urlopen(f"{SLEEPER}/players/nfl", timeout=180) as fh:
                SLEEPER_CACHE.write_text(json.dumps(json.load(fh)))
        except Exception as exc:
            if not SLEEPER_CACHE.exists():
                print(f"  ! could not reach Sleeper ({exc}); no injury pass")
                return pd.DataFrame(columns=["player", "team", "pos", "status", "part"])
            print(f"  ! Sleeper unreachable ({exc}); using the cached copy")
    d = json.loads(SLEEPER_CACHE.read_text())
    rows = [{"player": v.get("full_name"), "team": v.get("team"),
             "pos": (v.get("position") or "").lower(),
             "status": v.get("injury_status"),
             "part": v.get("injury_body_part") or ""}
            for v in d.values()
            if v.get("position") in ("QB", "RB", "WR", "TE") and v.get("injury_status")]
    return pd.DataFrame(rows)


def ruled_out(pos: str) -> pd.DataFrame:
    """This week's scratches for one position: the hand-written ones, plus
    anyone Sleeper has tagged with a status that means he is not playing."""
    cols = ["player", "team", "pos", "reason"]
    hand = pd.DataFrame(columns=cols)
    if RULED_OUT.exists():
        r = pd.read_csv(RULED_OUT)
        hand = r[(r.season == SEASON) & (r.week == WEEK)
                 & (r.pos.str.lower() == pos)][cols]
    inj = INJURIES[(INJURIES.pos == pos) & INJURIES.status.isin(NOT_PLAYING)]
    if inj.empty:
        return hand
    auto = inj.assign(reason=lambda d: d.status + " on Sleeper"
                      + d.part.where(d.part.eq(""), " (" + d.part + ")"))[cols]
    return pd.concat([hand, auto[~auto.player.isin(hand.player)]], ignore_index=True)


def scratch(df: pd.DataFrame, pos: str) -> pd.DataFrame:
    """Drop the scratches, close the gap in the ranks, and tell whoever is left
    in that backfield or receiver room that the touches are up for grabs.

    The vacated work is deliberately *not* redistributed: the model priced the
    survivors with the scratch still on the field, so quietly promoting them
    would invent volume nobody has measured. Saying so is the honest version."""
    out = ruled_out(pos)
    if out.empty:
        return df
    gone = df[df.player_name.isin(out.player)]
    if gone.empty:
        return df
    df = df[~df.player_name.isin(out.player)].copy()
    df["_vacated"] = ""
    for _, g in gone.iterrows():
        mates = df.team == g["team"]
        df.loc[mates, "_vacated"] += (
            f"{g['player_name']} is out; his work is not yet priced in here. ")
    df["rank_data"] = df["proj"].rank(ascending=False, method="first").astype(int)
    return df.sort_values("rank_data").reset_index(drop=True)


def league_ranks(frames: list[pd.DataFrame]) -> tuple[dict, dict, dict]:
    """Rank the 32 offences and the 32 defences, once, across the whole slate.

    These have to be league-wide. Ranking inside one position's list would
    measure a team against whoever else happens to be ranked at that position,
    which is how a team total once came out as the "-747rd-lowest" in football.
    Deduplicating by team first is the other half of it: rank the player rows
    and a team with six ranked receivers is counted six times."""
    all_rows = pd.concat(frames, ignore_index=True)

    off = all_rows.drop_duplicates("team").dropna(subset=["implied_team_total"])
    # 1 is the highest implied total.
    total = dict(zip(off.team, off.implied_team_total.rank(ascending=False,
                                                           method="min").astype(int)))
    ranks = []
    for col in ("opp_prev_def_epa_pass", "opp_prev_def_epa_rush"):
        if col not in all_rows.columns:
            ranks.append({})
            continue
        d = all_rows.drop_duplicates("opponent").dropna(subset=[col])
        # EPA allowed, so 1 is the fewest given up and the best defence.
        ranks.append(dict(zip(d.opponent,
                              d[col].rank(ascending=True, method="min").astype(int))))
    return total, ranks[0], ranks[1]


def promote(df: pd.DataFrame, pos: str, fname: str) -> pd.DataFrame:
    """Splice in anyone named in added.csv, taken from the model's pool."""
    if not ADDED.exists():
        return df
    a = pd.read_csv(ADDED)
    a = a[(a.season == SEASON) & (a.week == WEEK) & (a.position.str.lower() == pos)]
    want = [p for p in a.player if p not in set(df.player_name)]
    if not want:
        return df
    pool_path = pool_csv(fname)
    if not pool_path.exists():
        print(f"    {pos}: no pool file, cannot promote {want}")
        return df
    pool = pd.read_csv(pool_path)
    add = pool[pool.player_name.isin(want)]
    missing = set(want) - set(add.player_name)
    if missing:
        print(f"    {pos}: not in the pool either: {sorted(missing)}")
    if add.empty:
        return df
    print(f"    {pos}: promoted from the pool: "
          + ", ".join(f"{r.player_name} (model had him {int(r.rank_data)})"
                      for r in add.itertuples()))
    return pd.concat([df, add], ignore_index=True).sort_values("proj", ascending=False)


def override(df: pd.DataFrame, pos: str, variant: str) -> pd.DataFrame:
    """Move a player to a hand-picked slot and close the list up behind him."""
    if not MANUAL.exists():
        return df
    m = pd.read_csv(MANUAL)
    m = m[(m.season == SEASON) & (m.week == WEEK)
          & (m.position.str.lower() == pos) & (m.variant.str.lower() == variant)]
    if m.empty:
        return df
    df = df.sort_values("rank_data").reset_index(drop=True)
    for _, row in m.iterrows():
        hit = df.index[df.player_name == row.player]
        if not len(hit):
            print(f"    {pos}-{variant}: override skipped, not on the list: {row.player}")
            continue
        moved = df.loc[hit[0]].copy()
        if pd.notna(row.get("proj")):
            # The projection moves with him. Leave it and the start/sit tool,
            # which ranks on points rather than on the board, keeps answering
            # with the number the override was meant to replace.
            moved["proj"] = float(row["proj"])
        rest = df.drop(hit[0]).reset_index(drop=True)
        to = min(max(int(row["rank"]), 1), len(rest) + 1) - 1
        df = pd.concat([rest.iloc[:to], moved.to_frame().T, rest.iloc[to:]],
                       ignore_index=True)
        print(f"    {pos}-{variant}: {row.player} moved to {int(row['rank'])}"
              + (f", projection set to {float(row['proj']):.1f}"
                 if pd.notna(row.get("proj")) else ""))
    df["rank_data"] = range(1, len(df) + 1)

    # Price every man who moved for the slot he landed in.
    #
    # A hand placement moves the rank and leaves the projection where the model
    # put it, which is how Sam LaPorta came to sit tenth on 7.35 with T.J.
    # Hockenson eleventh on 7.60. The board reads as broken and the start/sit
    # tool, which ranks on points rather than on the board, goes on preferring
    # the man underneath. Each mover takes the midpoint of his new neighbours,
    # in rank order so a mover placed next to another sees the corrected value.
    # An explicit projection in the file wins over this.
    priced = set(m.loc[m.proj.notna(), "player"]) if "proj" in m else set()
    df = df.reset_index(drop=True)
    for name in m.sort_values("rank").player:
        if name in priced:
            continue
        at = df.index[df.player_name == name]
        if not len(at):
            continue
        i = at[0]
        above = df.proj.iloc[i - 1] if i > 0 else df.proj.max() * 1.02
        below = df.proj.iloc[i + 1] if i + 1 < len(df) else df.proj.min() * 0.98
        df.loc[i, "proj"] = round((float(above) + float(below)) / 2, 3)
    return df


def mc_override(df: pd.DataFrame, pos: str, variant: str) -> pd.DataFrame:
    """Move a player on MC's side alone, in one scoring format alone."""
    if not MC_MANUAL.exists():
        return df
    m = pd.read_csv(MC_MANUAL)
    m = m[(m.season == SEASON) & (m.week == WEEK)
          & (m.position.str.lower() == pos) & (m.variant.str.lower() == variant)]
    if m.empty:
        return df
    df = df.sort_values("rank_vibes").reset_index(drop=True)
    for _, row in m.iterrows():
        hit = df.index[df.player_name == row.player]
        if not len(hit):
            print(f"    {pos}-{variant}: MC override skipped, not on the list: {row.player}")
            continue
        moved = df.loc[hit[0]]
        rest = df.drop(hit[0]).reset_index(drop=True)
        to = min(max(int(row["rank"]), 1), len(rest) + 1) - 1
        df = pd.concat([rest.iloc[:to], moved.to_frame().T, rest.iloc[to:]],
                       ignore_index=True)
        print(f"    {pos}-{variant}: MC has {row.player} at {int(row['rank'])}")
    df["rank_vibes"] = range(1, len(df) + 1)
    return df


def main() -> None:
    global INJURIES
    OUT.mkdir(parents=True, exist_ok=True)
    global DEF_TO_DATE
    DEF_TO_DATE = defense_to_date()
    INJURIES = sleeper_status()
    hard = INJURIES[INJURIES.status.isin(NOT_PLAYING)]
    soft = INJURIES[~INJURIES.status.isin(NOT_PLAYING)]
    print(f"  injuries: {len(hard)} not playing, {len(soft)} questionable or worse "
          f"but expected to play")
    mc = pd.read_csv(MC) if MC.exists() else None
    loaded = {k: scratch(promote(pd.read_csv(model_csv(v)), k[0], v), k[0])
              for k, v in FILES.items()}
    rk_total, rk_pass, rk_rush = league_ranks(list(loaded.values()))
    for (pos, variant), fname in FILES.items():
        df = loaded[(pos, variant)].copy()
        df["rk_team_total"] = df.team.map(rk_total)
        df["rk_def_pass"] = df.opponent.map(rk_pass)
        df["rk_def_rush"] = df.opponent.map(rk_rush)
        df = override(df, pos, variant)
        band = df["ceiling_q90"] - df["floor_q20"]
        df["_tilt"] = ((df["median_q50"] - df["floor_q20"]) / band.where(band > 0)
                       ).rank(pct=True)
        if mc is not None:
            g = mc[mc.position.str.lower() == pos]
            df["rank_vibes"] = df.player_name.map(dict(zip(g.player, g["rank"])))
            df["note_vibes"] = df.player_name.map(dict(zip(g.player, g.note))).fillna("")
            # A player can make one scoring format's depth cut and not the
            # other -- half-PPR reaches a few names PPR does not -- so MC's
            # board, built from one list per position, can come up short by a
            # man or two at the very bottom. Publish only what he ranked
            # rather than inventing an opinion for him or ranking him against
            # a list he is not on. tools/mc-rankings.html now seeds from every
            # variant, so this should stay empty.
            unranked = df.rank_vibes.isna()
            if unranked.any():
                print(f"    {pos}-{variant}: not on MC's board, dropped: "
                      + ", ".join(df.loc[unranked, "player_name"]))
                df = df[~unranked]
            # Both columns close up behind anyone dropped. Leave them as they
            # were and a published list of 58 men counts to 59, skipping a
            # number, which reads as a missing player rather than a shorter
            # list. MC's order is preserved, only compacted.
            df["rank_data"] = df.rank_data.rank(method="first").astype(int)
            df["rank_vibes"] = df.rank_vibes.rank(method="first").astype(int)
            df = mc_override(df, pos, variant)
        else:
            # No board from MC yet, so consensus stands in. It is re-ranked
            # inside our published list so both columns order the same players
            # and the delta stays a like-for-like comparison.
            df["_c"] = df["consensus_rank"].fillna(9999)
            df = df.sort_values(["_c", "rank_data"]).reset_index(drop=True)
            df["rank_vibes"] = range(1, len(df) + 1)
            df["note_vibes"] = ""
        df = df.sort_values("rank_data")
        # What MC's number is worth in points.
        #
        # MC ranks; he does not project. Showing him Wilson's projection for
        # the same player is what made his own board read as nonsense, with
        # his RB7 carrying fewer points than his RB9. The honest conversion is
        # the one the start/sit tool already uses: his RB7 is worth whatever
        # Wilson's RB7 is worth. It borrows Wilson's scale and keeps MC's
        # order, which is the only thing MC actually claims.
        scale = sorted(df["proj"].dropna(), reverse=True)
        df["proj_vibes"] = [
            round(scale[min(int(v), len(scale)) - 1], 3) if scale else None
            for v in df["rank_vibes"]
        ]
        rows = []
        for _, r in df.iterrows():
            rows.append({
                "rank_data": int(r["rank_data"]),
                "rank_vibes": int(r["rank_vibes"]),
                "player": r["player_name"],
                "team": r["team"],
                "opponent": r.get("opponent", ""),
                "is_home": int(num(r.get("is_home"), 0)),
                # Published to three places and shown to one.
                #
                # Rounding here is destructive: two backs whose floors are
                # 7.694 and 7.698 both became 7.7, and the start/sit tool, with
                # nothing left to sort on, named whichever had been picked
                # first. It called the wrong man the safer floor. The extra
                # places cost nothing and let the tool break a tie the cards
                # cannot show.
                "proj": round(float(r["proj"]), 3),
                "proj_vibes": r.get("proj_vibes"),
                # The shape of his week, for the start/sit tool: what he does
                # when it goes badly, on a normal Sunday, and when it goes right.
                "floor": round(num(r.get("floor_q20"), 0.0), 3),
                "median": round(num(r.get("median_q50"), 0.0), 3),
                "ceiling": round(num(r.get("ceiling_q90"), 0.0), 3),
                "p_top12": round(num(r.get("p_top12"), 0.0), 4),
                "note_data": (str(r.get("_vacated") or "").strip()
                              + (" " if str(r.get("_vacated") or "").strip() else "")
                              + build_note(r, pos)).strip(),
                "note_vibes": r.get("note_vibes") or "",
            })
        path = OUT / f"{pos}-{variant}.csv"
        with path.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["rank_data", "rank_vibes", "player", "team",
                                               "opponent", "is_home", "proj", "proj_vibes",
                                               "floor", "median", "ceiling", "p_top12",
                                               "note_data", "note_vibes"])
            w.writeheader()
            w.writerows(rows)
        print(f"  {path}  ({len(rows)} players)")
    # Everyone still on a board who is carrying a tag we did not act on. These
    # are the calls only a human can make: Zay Flowers is Questionable with a
    # hamstring and might play sixty snaps or none, and no status code says
    # which. Add a row to data/weekly/ruled-out.csv to take one off.
    shipped = set()
    for df in loaded.values():
        shipped |= set(df.player_name)
    left = INJURIES[INJURIES.player.isin(shipped) & ~INJURIES.status.isin(NOT_PLAYING)]
    if len(left):
        print(f"  still on the board, carrying a tag ({len(left)}), your call:")
        for _, x in left.sort_values(["pos", "player"]).iterrows():
            part = f", {x.part}" if x.part else ""
            print(f"    {x.player} ({x.team}, {x.pos.upper()}) {x.status}{part}")
    (OUT / "LABEL.txt").write_text(f"Week {WEEK}\n")
    if not MC.exists():
        print(f"  no {MC} yet, so consensus fills the vibes column")
    for stale in ("qb.csv", "rb.csv"):
        p = OUT / stale
        if p.exists():
            p.unlink()
            print(f"  removed sample {p}")


if __name__ == "__main__":
    main()
