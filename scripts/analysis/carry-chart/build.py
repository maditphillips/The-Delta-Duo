#!/usr/bin/env python3
"""Run-direction chart plus drive strip for one back in one game.

Built from free nflverse data only (play-by-play and game snap counts). The
lines are a schematic: the lane each run crossed the line of scrimmage in and
how far it went are real, the curve between them is drawn, not tracked.

    python3 scripts/analysis/carry-chart/build.py \
        --game 2026_08_ATL_TB --player-id 00-0039361 --name "Bucky Irving"
    node scripts/analysis/carry-chart/render.mjs <out.html> <out.png>
"""
from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "model"))
from dd import ingest  # noqa: E402

# --- look -------------------------------------------------------------------
BG, PANEL, GRID = "#0f1014", "#16181d", "#2a2d35"
INK, INK2, INK3 = "#f0efec", "#c3c2b7", "#8b8a84"
LOSS, SHORT, GOOD = "#d03b3b", "#fab219", "#0ca30c"  # status steps, dark surface
OTHER_BACK, TWO_MIN, LOS = "#3987e5", "#199e70", "#3987e5"
W, PAD = 1600, 96

LANES = [("left", "end"), ("left", "tackle"), ("left", "guard"), ("middle", None),
         ("right", "guard"), ("right", "tackle"), ("right", "end")]
LANE_NAMES = ["L end", "L tackle", "L guard", "Middle", "R guard", "R tackle", "R end"]
RESULTS = {"Field goal": "FG", "Touchdown": "TD", "Punt": "PUNT", "Turnover": "TURNOVER",
           "Turnover on downs": "DOWNS", "End of half": "END", "Missed field goal": "MISSED FG",
           "Safety": "SAFETY", "Opp touchdown": "OPP TD"}


def outcome(yards: float) -> str:
    return LOSS if yards < 0 else SHORT if yards < 5 else GOOD


def short_name(full: str) -> str:
    first, last = full.split(" ", 1)
    return f"{first[0]}.{last}"


def pct(n: float, d: float) -> int:
    return round(100 * n / d) if d else 0


def esc(s) -> str:
    return html.escape(str(s))


# --- data -------------------------------------------------------------------
def load(game: str, player_id: str, name: str):
    season = int(game[:4])
    pbp = ingest.load("pbp", [season])
    g = pbp[pbp.game_id == game].sort_values("play_id")
    team = g.loc[g.rusher_player_id == player_id, "posteam"].iloc[0]
    plays = g[(g.posteam == team) & g.play_type.isin(["run", "pass", "qb_kneel"])].copy()

    snaps = ingest.load("snap_counts", [season])
    snaps = snaps[(snaps.game_id == game) & (snaps.team == team)]
    me = snaps[snaps.player == name].iloc[0]
    backs = {short_name(p) for p in snaps[snaps.position.isin(["RB", "FB"])].player} - {short_name(name)}

    plays["carry"] = (plays.rusher_player_id == player_id) & (plays.rush_attempt == 1)
    plays["target"] = plays.receiver_player_id == player_id
    plays["touch"] = plays.carry | plays.target
    plays["other_back"] = (plays.rusher_player_name.isin(backs) | plays.receiver_player_name.isin(backs)) & ~plays.touch
    plays["two_min"] = plays.half_seconds_remaining <= 120
    plays["n"] = plays.carry.cumsum().where(plays.carry)
    return g, plays, team, me


def situations(plays: pd.DataFrame, snaps_played: int):
    """Snap share by situation, as a range.

    Play-level participation is not public in-season. He was certainly on the
    field for his touches; his remaining snaps could have fallen anywhere.
    """
    spare = snaps_played - int(plays.touch.sum())
    rows = []
    buckets = [(f"{d}{s} down", plays.down == d) for d, s in ((1, "st"), (2, "nd"), (3, "rd"), (4, "th"))]
    buckets.append(("Under 2:00, either half", plays.two_min))
    for label, mask in buckets:
        total, known = int(mask.sum()), int((mask & plays.touch).sum())
        if not total:
            continue
        hi = known + min(spare, total - known)
        rows.append((label, total, known, pct(known, total), pct(hi, total)))
    return rows, spare


# --- field ------------------------------------------------------------------
def field(carries: pd.DataFrame) -> tuple[str, int]:
    fw, top, yd = W - 2 * PAD, 40, 12.6
    max_y = max(50, int(carries.yards_gained.max()) + 4)
    h = int(top + (max_y + 9) * yd + 96)
    cx, lane_w, side = W / 2, 124, fw / 2 - 20
    y = lambda yards: top + (max_y - yards) * yd  # noqa: E731
    out = [f'<svg width="{W}" height="{h}" viewBox="0 0 {W} {h}">',
           f'<rect x="{PAD}" y="{top}" width="{fw}" height="{(max_y + 9) * yd}" rx="10" fill="{PANEL}"/>']

    for mark in range(10, max_y, 10):
        out.append(f'<line x1="{PAD}" x2="{W - PAD}" y1="{y(mark)}" y2="{y(mark)}" stroke="{GRID}"/>')
        for x, anchor in ((PAD + 14, "start"), (W - PAD - 14, "end")):
            out.append(f'<text x="{x}" y="{y(mark) - 8}" text-anchor="{anchor}" class="tick">+{mark}</text>')
    out.append(f'<line x1="{PAD}" x2="{W - PAD}" y1="{y(0)}" y2="{y(0)}" stroke="{LOS}" stroke-width="3"/>')
    out.append(f'<text x="{PAD + 14}" y="{y(0) - 10}" class="tick" fill="{INK2}">LINE OF SCRIMMAGE</text>')

    lane_of = {k: i for i, k in enumerate(LANES)}
    carries = carries.copy()
    carries["lane"] = [lane_of.get((loc, gap if loc != "middle" else None), 3) if isinstance(loc, str) else 3
                       for loc, gap in zip(carries.run_location, carries.run_gap.where(carries.run_gap.notna(), None))]
    labels, ends = [], []
    for lane, grp in carries.groupby("lane"):
        lx = cx + (lane - 3) * lane_w
        total = int(grp.yards_gained.sum())
        out.append(f'<text x="{lx}" y="{y(-9) + 34}" text-anchor="middle" class="lane">{LANE_NAMES[lane].upper()}</text>')
        out.append(f'<text x="{lx}" y="{y(-9) + 62}" text-anchor="middle" class="lanev">{len(grp)} for {total}</text>')
        for i, (_, r) in enumerate(grp.iterrows()):
            fan = (i - (len(grp) - 1) / 2) * min(11, 84 / max(len(grp), 1))
            px, yards, col = lx + fan, float(r.yards_gained), outcome(float(r.yards_gained))
            sx, sy = cx + (lane - 3) * 6, y(-4.5 if r.shotgun else -7)
            drift = (lane - 3) * min(yards, 20) * 1.1 if yards > 0 else 0
            ex, ey = px + drift, y(yards)
            if r.out_of_bounds == 1:
                ex = cx - side if lane < 3 else cx + side
            if yards <= 0:  # never crossed the line: one bend, stopping short
                d = f"M{sx:.1f},{sy:.1f} C{sx:.1f},{(sy + ey) / 2:.1f} {ex:.1f},{ey + 40:.1f} {ex:.1f},{ey:.1f}"
            else:
                reach = max(10, min(120, (y(0) - ey) * 0.55))
                d = (f"M{sx:.1f},{sy:.1f} C{sx:.1f},{sy - 24:.1f} {px:.1f},{y(0) + 34:.1f} {px:.1f},{y(0):.1f} "
                     f"C{px:.1f},{y(0) - reach:.1f} {ex - (ex - px) * 0.25:.1f},{ey + reach:.1f} {ex:.1f},{ey:.1f}")
            dash = "" if isinstance(r.run_location, str) else ' stroke-dasharray="7 6"'
            out.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="3.5" stroke-linecap="round" opacity=".9"{dash}/>')
            ends.append((ex, ey, col, r))
            tags = []
            if r.rush_touchdown == 1:
                tags.append("TD")
            if r.fumble_lost == 1:
                tags.append("fumble lost")
            if tags or yards >= 10 or yards < 0:
                tail = f" · {', '.join(tags)}" if tags else ""
                labels.append((ex, ey, f"#{int(r.n)} · {int(yards):+d}{tail}", lane))
    for ex, ey, col, r in ends:
        ring = INK if (r.rush_touchdown == 1 or r.fumble_lost == 1) else PANEL
        out.append(f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="7" fill="{col}" stroke="{ring}" stroke-width="2.5"/>')
    placed = []
    for ex, ey, text, lane in sorted(labels, key=lambda l: l[1]):
        below = text.split(" · ")[1].startswith("-")
        ty = ey + 30 if below else ey - 16
        while any(abs(ty - py) < 26 and abs(ex - pxx) < 150 for pxx, py in placed):
            ty += 26 if below else -26
        placed.append((ex, ty))
        anchor = "start" if ex < PAD + 120 else "end" if ex > W - PAD - 120 else "middle"
        out.append(f'<text x="{ex:.1f}" y="{ty:.1f}" text-anchor="{anchor}" class="call">{esc(text)}</text>')
    out.append("</svg>")
    return "\n".join(out), h


# --- drive strip ------------------------------------------------------------
def strip(plays: pd.DataFrame) -> str:
    rows = []
    for _, d in plays.groupby("fixed_drive", sort=True):
        first = d.iloc[0]
        marks, in_two = [], False
        for _, r in d.iterrows():
            if r.two_min and not in_two:
                marks.append('<span class="two"><i>2-MIN</i>')
                in_two = True
            cls = ["m"]
            if r.down >= 3:
                cls.append("late")
            if r.yardline_100 <= 10:
                cls.append("ten")
            label, sub, style = "", "", ""
            if r.touch:
                col = outcome(float(r.yards_gained))
                ink = "#16181d" if col == SHORT else "#fff"
                if r.carry:
                    label, style = str(int(r.n)), f"background:{col};color:{ink};border-color:{col}"
                else:
                    label, style = "T", f"border-color:{col};color:{col}"
                sub = f"{int(r.yards_gained):+d}" if r.yards_gained else "0"
            elif r.other_back:
                cls.append("ob")
            else:
                cls.append("dot")
            marks.append(f'<span class="cell"><span class="{" ".join(cls)}" style="{style}">{label}</span>'
                         f'<span class="sub">{sub}</span></span>')
        if in_two:
            marks.append("</span>")
        result = RESULTS.get(first.fixed_drive_result, str(first.fixed_drive_result).upper())
        touches = int(d.touch.sum())
        rows.append(f'<div class="drive"><div class="when">{int(first.qtr)}Q {first.time}</div>'
                    f'<div class="marks">{"".join(marks)}<span class="res">{esc(result)}</span></div>'
                    f'<div class="cnt{" zero" if not touches else ""}">{touches}</div></div>')
    return "\n".join(rows)


# --- page -------------------------------------------------------------------
CSS = f"""
*{{box-sizing:border-box;margin:0}}
body{{width:{W}px;background:{BG};color:{INK};font-family:Inter,'DejaVu Sans',sans-serif;padding:88px {PAD}px 72px}}
h1{{font:800 76px/1 'Inter Display',Inter,sans-serif;letter-spacing:-1.5px}}
.kick{{margin-top:18px;font:600 25px Inter;letter-spacing:3px;color:{INK3};text-transform:uppercase}}
h2{{font:700 30px Inter;margin:64px 0 6px}}
.note{{font:400 21px/1.45 Inter;color:{INK3};max-width:1300px}}
.tiles{{display:flex;gap:20px;margin-top:44px}}
.tile{{flex:1;background:{PANEL};border-radius:10px;padding:24px 26px}}
.tile b{{display:block;font:800 54px/1 'Inter Display',Inter;font-variant-numeric:tabular-nums}}
.tile span{{display:block;margin-top:10px;font:500 20px Inter;color:{INK2}}}
.sit{{display:flex;gap:20px;margin-top:24px}}
.sit .tile b{{font-size:42px}}
.sit .tile em{{display:block;margin-top:6px;font:400 18px Inter;color:{INK3};font-style:normal}}
.legend{{display:flex;flex-wrap:wrap;gap:12px 34px;margin:22px 0 4px;font:500 22px Inter;color:{INK2};align-items:center}}
.legend span{{display:inline-flex;align-items:center;gap:10px}}
.sw{{width:24px;height:24px;border-radius:5px;display:inline-block;border:3px solid transparent}}
.fieldwrap{{margin:0 -{PAD}px}}
svg text{{font-family:Inter,sans-serif}}
.tick{{font-size:19px;font-weight:600;fill:{INK3};letter-spacing:1px}}
.lane{{font-size:17px;font-weight:700;fill:{INK3};letter-spacing:1.5px}}
.lanev{{font-size:22px;font-weight:700;fill:{INK}}}
.call{{font-size:20px;font-weight:700;fill:{INK};paint-order:stroke;stroke:{PANEL};stroke-width:6px}}
.drive{{display:flex;align-items:center;border-bottom:1px solid {GRID};padding:18px 0 10px;min-height:96px}}
.when{{width:176px;font:700 27px Inter;font-variant-numeric:tabular-nums}}
.marks{{flex:1;display:flex;flex-wrap:wrap;align-items:flex-start;gap:8px 6px}}
.cell{{display:inline-flex;flex-direction:column;align-items:center;width:46px}}
.m{{width:44px;height:44px;border-radius:6px;border:3px solid {INK3};display:flex;align-items:center;justify-content:center;font:800 19px Inter}}
.m.late{{border-radius:50%}}
.m.ten{{outline:3px solid {INK};outline-offset:3px}}
.m.ob{{border-color:{OTHER_BACK};background:{OTHER_BACK}33}}
.m.dot{{width:14px;height:14px;border:0;border-radius:50%;background:{INK3};opacity:.55;margin:15px 0}}
.m.dot.late{{opacity:.9}}
.sub{{height:22px;margin-top:4px;font:600 16px Inter;color:{INK2};font-variant-numeric:tabular-nums}}
.two{{display:inline-flex;gap:6px;position:relative;padding:6px 6px 0;margin:-9px 0 0;border:3px solid {TWO_MIN};border-radius:10px;background:{TWO_MIN}22}}
.two i{{position:absolute;top:-24px;right:4px;font:800 15px Inter;font-style:normal;letter-spacing:2px;color:{TWO_MIN}}}
.res{{align-self:center;margin:0 0 22px 14px;font:700 19px Inter;letter-spacing:2.5px;color:{INK3}}}
.cnt{{width:60px;text-align:right;font:800 30px Inter;font-variant-numeric:tabular-nums}}
.cnt.zero{{color:{INK3};opacity:.5}}
.foot{{margin-top:44px;font:400 20px/1.5 Inter;color:{INK3}}}
.foot b{{color:{INK};font-weight:700}}
"""


def page(name, g, plays, team, me) -> str:
    carries = plays[plays.carry]
    sit, spare = situations(plays, int(me.offense_snaps))
    info = g.iloc[0]
    opp = info.away_team if team == info.home_team else info.home_team
    where = "vs" if team == info.home_team else "at"
    yards, tds = int(carries.yards_gained.sum()), int(carries.rush_touchdown.sum())
    team_snaps = round(me.offense_snaps / me.offense_pct) if me.offense_pct else len(plays)
    field_svg, _ = field(carries)

    tiles = [(f"{pct(me.offense_snaps, team_snaps)}%", f"Snap share · {int(me.offense_snaps)} of {team_snaps} snaps"),
             (str(len(carries)), "Carries"), (str(yards), "Rushing yards"),
             (f"{yards / len(carries):.1f}", "Yards per carry"), (str(tds), "Touchdowns" if tds != 1 else "Touchdown")]
    tiles_html = "".join(f'<div class="tile"><b>{v}</b><span>{esc(l)}</span></div>' for v, l in tiles)
    sit_html = "".join(
        f'<div class="tile"><b>{lo}%{"" if lo == hi else f"–{hi}%"}</b><span>{esc(label)}</span>'
        f'<em>touched {known} of {total} plays</em></div>' for label, total, known, lo, hi in sit)
    unlocated = int(carries.run_location.isna().sum())

    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{esc(name)} carry chart</title>
<style>{CSS}</style></head><body>
<h1>{esc(name)}, run by run</h1>
<div class="kick">Week {int(info.week)} · {team} {where} {opp} · {pd.Timestamp(info.game_date):%b %-d, %Y}</div>
<div class="tiles">{tiles_html}</div>

<h2>Snap share by situation</h2>
<p class="note">Play-by-play snap data is not public during the season, so each figure is a range. The low end
counts only plays where he touched the ball. The high end adds his {spare} snaps without a touch, which could have
come in any situation.</p>
<div class="sit">{sit_html}</div>

<h2>Where he ran</h2>
<div class="legend"><span><i class="sw" style="background:{LOSS}"></i>Loss</span>
<span><i class="sw" style="background:{SHORT}"></i>0–4 yards</span>
<span><i class="sw" style="background:{GOOD}"></i>5+ yards</span>
<span>#n = carry number, matched in the drive strip below</span></div>
<div class="fieldwrap">{field_svg}</div>
<p class="note">Each line enters the lane the run was charted in and ends at the yards gained. The curve between
is drawn, not tracked. Under each lane: carries for yards.{f" {unlocated} carries had no charted lane (dashed, shown in the middle)." if unlocated else ""}</p>

<h2>Drive by drive</h2>
<div class="legend"><span><i class="sw" style="background:{GOOD}"></i>{esc(name.split()[-1])} carry, numbered</span>
<span><i class="sw" style="border-color:{OTHER_BACK};background:{OTHER_BACK}33"></i>Other back's touch</span>
<span><i class="sw" style="width:14px;height:14px;border-radius:50%;background:{INK3};border:0"></i>Other play</span>
<span><i class="sw" style="border-color:{INK3};border-radius:50%"></i>3rd or 4th down</span>
<span><i class="sw" style="border-color:{INK3};outline:2px solid {INK};outline-offset:2px"></i>Inside the 10</span>
<span><i class="sw" style="border-color:{TWO_MIN};background:{TWO_MIN}22"></i>Under 2:00</span>
<span>Right column: his touches</span></div>
{strip(plays)}
<div class="foot"><b>Data: nflverse</b> play-by-play and snap counts. Yards under each square.</div>
</body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", required=True)
    ap.add_argument("--player-id", required=True)
    ap.add_argument("--name", required=True, help="full name as in nflverse snap counts")
    ap.add_argument("--out", type=Path, required=True, help="HTML file to write")
    a = ap.parse_args()
    g, plays, team, me = load(a.game, a.player_id, a.name)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(page(a.name, g, plays, team, me))
    sit, spare = situations(plays, int(me.offense_snaps))
    print(f"{a.name}: {int(plays.carry.sum())} carries, {int(me.offense_snaps)} snaps, {spare} snaps without a touch")
    for row in sit:
        print("  ", row)


if __name__ == "__main__":
    main()
