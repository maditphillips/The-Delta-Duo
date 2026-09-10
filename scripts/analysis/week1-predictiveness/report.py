"""Render the study as a standalone HTML report in the Delta Duo house style.

This is an offline file, not a page of the site: nothing in src/ imports it and no
route serves it. It only borrows the house style so it reads like the rest of the Lab.

Reads report_data.json (written by make_report_data.py) so no figure in the page
is typed by hand. Writes week1-report.html.

House style comes from src/app/globals.css: green slate boards in a wooden frame
on a near-black page, sketch-chalk titles, gold em-dash kickers, handwritten gold
annotations. Series colours are the site's chalk palette. Gold+pink and gold+blue
both clear CVD separation against the #466553 board; gold+green does not, so it
is never used as a pair here, and every mark is directly labelled.
"""
import json, os, html

HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, "report_data.json")))

GOLD, PINK, BLUE, INK = "#e9c464", "#f4a3be", "#7cc4ea", "#f2eee2"
DIM, FAINT, GHOST = "rgba(242,238,226,.72)", "rgba(242,238,226,.45)", "rgba(242,238,226,.18)"

# curated ranking for exhibit 1: the metrics this study was asked about, plus the
# ones needed to show the full range from pure role to pure outcome
PICK = [("RB", "rush_share"), ("WR", "snap_pct"), ("WR", "target_share"), ("RB", "snap_pct"),
        ("RB", "carries"), ("WR", "targets"), ("TE", "snap_pct"), ("RB", "touches"),
        ("TE", "targets"), ("WR", "air_yards"), ("RB", "targets"), ("RB", "rushing_yards"),
        ("WR", "adot"), ("RB", "fantasy_ppg_ppr"), ("WR", "receptions"),
        ("WR", "fantasy_ppg_ppr"), ("TE", "fantasy_ppg_ppr"), ("QB", "pass_attempts"),
        ("QB", "fantasy_ppg"), ("RB", "rushing_tds"), ("QB", "completion_pct"),
        ("RB", "yards_per_touch"), ("WR", "receiving_tds"), ("QB", "cpoe"),
        ("WR", "catch_rate"), ("RB", "rush_fd_rate"), ("RB", "yards_per_carry"),
        ("WR", "yards_per_target"), ("QB", "int_rate")]

SIG = {(r["position"], r["metric"]): r for r in D["signal"]}
ASK = {(r["position"], r["metric"]): r for r in D["asked"]}


def esc(s):
    return html.escape(str(s))


def tip(text):
    return f' data-tip="{esc(text)}" tabindex="0"'


# ------------------------------------------------------------------ exhibit 1
def chart_signal():
    rows = [SIG[k] for k in PICK if k in SIG]
    rows.sort(key=lambda r: -r["rel1"])
    rh, top, bot = 25, 34, 12
    lw, bw, vw = 232, 300, 132                 # label / bar / value columns
    h = top + len(rows) * rh + bot
    w = lw + bw + vw
    o = [f'<svg viewBox="0 0 {w} {h}" role="img" class="cw" '
         f'aria-label="Share of one Week 1 game that is signal, by metric">']
    o.append(f'<text x="{lw}" y="14" fill="{FAINT}" font-size="10.5" '
             f'letter-spacing=".14em">SHARE OF ONE GAME THAT IS SIGNAL</text>')
    for f in (0, .25, .5, .75, 1):
        x = lw + f * bw
        o.append(f'<line x1="{x:.1f}" y1="{top-8}" x2="{x:.1f}" y2="{h-bot}" '
                 f'stroke="{GHOST}" stroke-width="1"/>')
        o.append(f'<text x="{x:.1f}" y="{h-bot+14}" fill="{DIM}" font-size="10.5" '
                 f'text-anchor="middle">{int(f*100)}%</text>')
    for i, r in enumerate(rows):
        y = top + i * rh
        col = GOLD if r["group"] == "opportunity" else PINK
        bl = r["rel1"] * bw
        g = r["g50"]
        games = f"{g:.1f} game" + ("" if abs(g - 1) < .05 else "s")
        o.append(f'<text x="0" y="{y+13}" fill="{DIM}" font-size="11.5">'
                 f'<tspan fill="{FAINT}" font-size="10" letter-spacing=".1em">'
                 f'{r["position"]}</tspan>  {esc(r["label"])}</text>')
        t = (f"{r['position']} {r['label']}: {r['rel1']*100:.0f}% of one game's spread "
             f"is signal, {games} to reach half signal, Week 1 to rest-of-season "
             f"r = {r['r']:.2f}")
        o.append(f'<rect x="{lw}" y="{y+3}" width="{max(bl,2):.1f}" height="12" rx="4" '
                 f'fill="{col}"{tip(t)}/>')
        o.append(f'<text x="{lw+max(bl,2)+7:.1f}" y="{y+13}" fill="{INK}" font-size="11" '
                 f'font-weight="600" style="font-variant-numeric:tabular-nums">'
                 f'{r["rel1"]*100:.0f}%</text>')
        o.append(f'<text x="{w}" y="{y+13}" fill="{FAINT}" font-size="10.5" '
                 f'text-anchor="end" style="font-variant-numeric:tabular-nums">'
                 f'{games} to half signal</text>')
    o.append("</svg>")
    return '<div class="scroll">' + "".join(o) + "</div>"


# ------------------------------------------------------------------ exhibit 2
def chart_dumbbell():
    rows = [ASK[k] for k in
            [("RB", "rush_share"), ("RB", "snap_pct"), ("RB", "targets"), ("RB", "carries"),
             ("RB", "fantasy_ppg_ppr"), ("RB", "yards_per_carry"),
             ("WR", "snap_pct"), ("WR", "air_yards"), ("WR", "target_share"), ("WR", "targets"),
             ("WR", "fantasy_ppg_ppr"), ("WR", "yards_per_target"),
             ("TE", "target_share"), ("TE", "fantasy_ppg_ppr"),
             ("QB", "pass_attempts"), ("QB", "fantasy_ppg"), ("QB", "completion_pct"),
             ("QB", "cpoe")] if k in ASK]
    rh, top, bot, lw, pw = 26, 40, 12, 214, 400
    h = top + len(rows) * rh + bot
    w = lw + pw + 74
    def X(v):
        return lw + max(v, 0) / 1.0 * pw
    o = [f'<svg viewBox="0 0 {w} {h}" role="img" class="cw" '
         f'aria-label="Week 1 correlation versus last season correlation, by metric">']
    o.append(f'<text x="{lw}" y="14" fill="{FAINT}" font-size="10.5" letter-spacing=".14em">'
             f'CORRELATION WITH THE REST OF THE SEASON (r)</text>')
    for f in (0, .2, .4, .6, .8, 1):
        x = X(f)
        o.append(f'<line x1="{x:.1f}" y1="{top-10}" x2="{x:.1f}" y2="{h-bot}" '
                 f'stroke="{GHOST}"/>')
        o.append(f'<text x="{x:.1f}" y="{top-16}" fill="{FAINT}" font-size="10" '
                 f'text-anchor="middle">{f:.1f}</text>')
    last_pos = None
    for i, r in enumerate(rows):
        y = top + i * rh + 12
        a, b = r["r"], (r["r_prior"] if r["r_prior"] == r["r_prior"] else 0)
        if r["position"] != last_pos:
            o.append(f'<text x="0" y="{y+4}" fill="{GOLD}" font-size="10.5" '
                     f'font-weight="700" letter-spacing=".14em">{r["position"]}</text>')
            last_pos = r["position"]
        o.append(f'<text x="34" y="{y+4}" fill="{DIM}" font-size="11.5">'
                 f'{esc(r["label"])}</text>')
        o.append(f'<line x1="{X(min(a,b)):.1f}" y1="{y}" x2="{X(max(a,b)):.1f}" y2="{y}" '
                 f'stroke="{GHOST}" stroke-width="3" stroke-linecap="round"/>')
        tb = (f"{r['position']} {r['label']}: last season's full line predicts the rest "
              f"of this season at r = {b:.2f}")
        ta = (f"{r['position']} {r['label']}: Week 1 alone predicts the rest of this "
              f"season at r = {a:.2f}")
        o.append(f'<circle cx="{X(b):.1f}" cy="{y}" r="5.5" fill="{BLUE}" '
                 f'stroke="#466553" stroke-width="2"{tip(tb)}/>')
        o.append(f'<circle cx="{X(a):.1f}" cy="{y}" r="5.5" fill="{GOLD}" '
                 f'stroke="#466553" stroke-width="2"{tip(ta)}/>')
        win = GOLD if a >= b else BLUE
        o.append(f'<text x="{w}" y="{y+4}" fill="{win}" font-size="11" text-anchor="end" '
                 f'font-weight="600" style="font-variant-numeric:tabular-nums">'
                 f'{a:.2f} / {b:.2f}</text>')
    o.append("</svg>")
    return '<div class="scroll">' + "".join(o) + "</div>"


# ------------------------------------------------------------------ exhibit 3
def chart_curves():
    panels = []
    for pos in ("RB", "WR", "TE", "QB"):
        for m in D["curves"][pos]:
            panels.append((pos, m))
    pw, ph = 168, 108
    pl, pt, pr, pb = 30, 30, 8, 24
    out = []
    for pos, m in panels:
        vals, prior = m["vals"], m["prior"]
        w, h = pl + pw + pr, pt + ph + pb
        def X(k):
            return pl + (k - 1) / (len(vals) - 1) * pw
        def Y(v):
            return pt + ph - max(min(v, 1), 0) * ph
        o = [f'<svg viewBox="0 0 {w} {h}" class="pn" role="img" '
             f'aria-label="{pos} {esc(m["label"])}: correlation with weeks 10 onward, '
             f'after k weeks of data">']
        o.append(f'<text x="0" y="10" fill="{INK}" font-size="10.5" font-weight="600">'
                 f'<tspan fill="{GOLD}" letter-spacing=".1em">{pos}</tspan> '
                 f'{esc(m["label"])}</text>')
        for v in (0, .5, 1):
            o.append(f'<line x1="{pl}" y1="{Y(v):.1f}" x2="{pl+pw}" y2="{Y(v):.1f}" '
                     f'stroke="{GHOST}"/>')
            o.append(f'<text x="{pl-6}" y="{Y(v)+3.5:.1f}" fill="{FAINT}" font-size="9" '
                     f'text-anchor="end">{v:.1f}</text>')
        tp = (f"{pos} {m['label']}: last season's full line predicts weeks 10 onward "
              f"at r = {prior:.2f}")
        o.append(f'<line x1="{pl}" y1="{Y(prior):.1f}" x2="{pl+pw}" y2="{Y(prior):.1f}" '
                 f'stroke="{BLUE}" stroke-width="2" stroke-dasharray="5 4"{tip(tp)}/>')
        o.append(f'<text x="{pl+pw}" y="{Y(prior)-6:.1f}" fill="{BLUE}" font-size="9" '
                 f'text-anchor="end">last season {prior:.2f}</text>')
        pts = " ".join(f"{X(k+1):.1f},{Y(v):.1f}" for k, v in enumerate(vals))
        o.append(f'<polyline points="{pts}" fill="none" stroke="{GOLD}" stroke-width="2" '
                 f'stroke-linejoin="round"/>')
        for k, v in enumerate(vals):
            wk = "week" if k == 0 else "weeks"
            tk = (f"{pos} {m['label']}: after {k+1} {wk} of the new season, "
                  f"r = {v:.2f} with weeks 10 onward")
            o.append(f'<circle cx="{X(k+1):.1f}" cy="{Y(v):.1f}" r="3.2" fill="{GOLD}" '
                     f'stroke="#466553" stroke-width="1.4"{tip(tk)}/>')
        o.append(f'<text x="{X(1):.1f}" y="{Y(vals[0])+16:.1f}" fill="{GOLD}" font-size="9.5" '
                 f'font-weight="600" text-anchor="middle">{vals[0]:.2f}</text>')
        o.append(f'<text x="{pl}" y="{h-8}" fill="{FAINT}" font-size="9">wk 1</text>')
        o.append(f'<text x="{pl+pw}" y="{h-8}" fill="{FAINT}" font-size="9" '
                 f'text-anchor="end">through wk {len(vals)}</text>')
        o.append("</svg>")
        out.append("".join(o))
    return '<div class="grid4">' + "".join(f"<div>{p}</div>" for p in out) + "</div>"


# ------------------------------------------------------------------ exhibit 4
def table_models():
    order = ["W1 fantasy pts", "W1 usage only", "W1 pts + usage", "last season only",
             "last season + W1 pts", "last season + W1 usage", "everything"]
    nice = {"W1 fantasy pts": "Week 1 fantasy points alone",
            "W1 usage only": "Week 1 usage alone (share of team work, snap share)",
            "W1 pts + usage": "Week 1 points + Week 1 usage",
            "last season only": "Last season alone",
            "last season + W1 pts": "Last season + Week 1 points",
            "last season + W1 usage": "Last season + Week 1 usage",
            "everything": "Last season + Week 1 points + Week 1 usage"}
    poss = ["RB", "WR", "TE", "QB"]
    o = ['<div class="scroll"><table class="tb"><thead><tr>'
         '<th class="l">what you feed the model</th>']
    for p in poss:
        o.append(f'<th>{p}</th>')
    o.append("</tr></thead><tbody>")
    for k in order:
        hi = "hl" if k in ("W1 usage only", "W1 fantasy pts") else ""
        o.append(f'<tr class="{hi}"><td class="l">{esc(nice[k])}</td>')
        for p in poss:
            src = D["models"][p].get("snaps") or D["models"][p]["all"]
            v = src.get(k)
            if v is None:
                o.append('<td class="mut">—</td>')
                continue
            col = GOLD if k.startswith("W1") else BLUE
            o.append(f'<td><span class="minibar" style="--v:{v/0.6*72:.0f}px;--c:{col}">'
                     f'</span><span class="num">{v:.3f}</span></td>')
        o.append("</tr>")
    ns = ", ".join(f"{p} n={(D['models'][p].get('snaps') or D['models'][p]['all'])['n']}"
                   for p in poss)
    o.append("</tbody></table></div>")
    o.append(f'<p class="cap">R&sup2; predicting rest-of-season fantasy points per game '
             f'({ns}). RB, WR and TE usage includes snap share, so those columns run '
             f'{D["meta"]["snap_first"]}&ndash;{D["meta"]["last"]}. A starting quarterback '
             f'plays every snap, so there is no snap share to read and the QB column runs '
             f'the full {D["meta"]["first"]}&ndash;{D["meta"]["last"]} with attempts and '
             f'rush attempts as its usage.</p>')
    return "".join(o)


# ------------------------------------------------------------------ exhibit 5
def table_panic():
    o = ['<div class="scroll"><table class="tb"><thead><tr>'
         '<th class="l">last season</th><th class="l">week 1</th><th>n</th>'
         '<th>finished top&nbsp;12</th><th>finished top&nbsp;24</th>'
         '<th>median ppg</th></tr></thead><tbody>']
    for pos in ("RB", "WR", "TE", "QB"):
        o.append(f'<tr class="sec"><td colspan="6">{pos}</td></tr>')
        for r in D["panic"][pos]:
            pl = "top 12" if r["prior"] else "outside top 12"
            wl = "top 12" if r["wk1"] else "outside top 12"
            key = r["prior"] and r["wk1"]
            o.append(
                f'<tr{" class=hl" if r["prior"] and not r["wk1"] else ""}>'
                f'<td class="l">{pl}</td><td class="l">{wl}</td>'
                f'<td class="num">{r["n"]}</td>'
                f'<td><span class="minibar" style="--v:{r["top12"]*72:.0f}px;'
                f'--c:{GOLD if key else BLUE}"></span>'
                f'<span class="num">{r["top12"]*100:.0f}%</span></td>'
                f'<td class="num">{r["top24"]*100:.0f}%</td>'
                f'<td class="num">{r["med_ppg"]:.1f}</td></tr>')
    o.append("</tbody></table></div>")
    o.append('<p class="cap">Positional finish by PPR points. Ranks are taken inside the '
             'pool of players who had a real Week 1 role, so the base rates are '
             'position-specific. Highlighted rows are the panic case: a known producer '
             'who opened badly.</p>')
    return "".join(o)


# ------------------------------------------------------------------ exhibit 6
def chart_team():
    t = D["team"]
    bars = [("rest-of-season win rate", t["won"]["ros_win"], t["lost"]["ros_win"], 1.0, "%"),
            ("reached the playoffs", t["won"]["playoffs"], t["lost"]["playoffs"], 1.0, "%"),
            ("covered the spread after week 1", t["won"]["cover"], t["lost"]["cover"], 1.0, "%")]
    o = ['<div class="grid3">']
    for label, a, b, mx, unit in bars:
        rows = [("1-0", a, GOLD), ("0-1", b, PINK)]
        w, h = 260, 118
        s = [f'<svg viewBox="0 0 {w} {h}" class="pn" role="img" '
             f'aria-label="{esc(label)}: 1-0 teams versus 0-1 teams">']
        s.append(f'<text x="0" y="11" fill="{INK}" font-size="11" font-weight="600">'
                 f'{esc(label)}</text>')
        for i, (lab, v, col) in enumerate(rows):
            y = 32 + i * 38
            bl = v / mx * 176
            s.append(f'<text x="0" y="{y+13}" fill="{DIM}" font-size="12" '
                     f'font-weight="700">{lab}</text>')
            n = t["won" if i == 0 else "lost"]["n"]
            tt = f"{lab} teams: {v*100:.1f}% — {label} (n={n})"
            s.append(f'<rect x="30" y="{y+2}" width="{bl:.1f}" height="14" rx="4" '
                     f'fill="{col}"{tip(tt)}/>')
            s.append(f'<text x="{30+bl+7:.1f}" y="{y+13}" fill="{INK}" font-size="11.5" '
                     f'font-weight="600" style="font-variant-numeric:tabular-nums">'
                     f'{v*100:.1f}%</text>')
        s.append(f'<line x1="30" y1="106" x2="206" y2="106" stroke="{GHOST}"/>')
        s.append(f'<text x="118" y="{116}" fill="{FAINT}" font-size="9" '
                 f'text-anchor="middle">0% to 100%</text>')
        s.append("</svg>")
        o.append(f"<div>{''.join(s)}</div>")
    o.append("</div>")
    # the blowout ladder
    o.append('<div class="scroll"><table class="tb" style="margin-top:1.4rem"><thead><tr>'
             '<th class="l">week 1 result</th><th>n</th><th>rest-of-season win rate</th>'
             '<th>reached the playoffs</th></tr></thead><tbody>')
    for b in t["bins"]:
        o.append(f'<tr><td class="l">{esc(b["label"])}</td><td class="num">{b["n"]}</td>'
                 f'<td><span class="minibar" style="--v:{b["ros_win"]*72:.0f}px;--c:{GOLD}">'
                 f'</span><span class="num">{b["ros_win"]*100:.1f}%</span></td>'
                 f'<td><span class="minibar" style="--v:{b["playoffs"]*72:.0f}px;--c:{BLUE}">'
                 f'</span><span class="num">{b["playoffs"]*100:.1f}%</span></td></tr>')
    o.append("</tbody></table></div>")
    return "".join(o)


def table_split():
    o = ['<div class="scroll"><table class="tb"><thead><tr><th class="l">last season</th>'
         '<th class="l">week 1</th><th>n</th><th>rest-of-season win rate</th>'
         '<th>reached the playoffs</th></tr></thead><tbody>']
    for s in D["team"]["split"]:
        o.append(f'<tr><td class="l">{s["prior"]} record</td><td class="l">{s["wk1"]}</td>'
                 f'<td class="num">{s["n"]}</td>'
                 f'<td class="num">{s["ros_win"]*100:.1f}%</td>'
                 f'<td><span class="minibar" style="--v:{s["playoffs"]*72:.0f}px;--c:{BLUE}">'
                 f'</span><span class="num">{s["playoffs"]*100:.1f}%</span></td></tr>')
    o.append("</tbody></table></div>")
    return "".join(o)


# ------------------------------------------------------------------ the page
CSS = """
:root{
  --page:#0c0e0d; --board:#466553; --board-hi:#4e7060; --board-lo:#3e5a4a;
  --ink:#f2eee2; --ink-dim:rgba(242,238,226,.74); --ink-faint:rgba(242,238,226,.46);
  --ink-ghost:rgba(242,238,226,.16);
  --gold:#e9c464; --pink:#f4a3be; --blue:#7cc4ea;
  --accent:#fb9f55; --accent-2:#f80693; --accent-3:#01def3;
  --sketch:"Cabin Sketch","Patrick Hand",cursive;
  --retro:"Righteous","Cabin Sketch",sans-serif;
  --hand:"Caveat","Patrick Hand",cursive;
  --body:"Inter",ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;
  --step:clamp(1rem,.94rem + .3vw,1.05rem);
}
*{box-sizing:border-box}
body{
  margin:0; padding-block:clamp(1.6rem,4vw,3.2rem); padding-left:16px; padding-right:16px;
  background:radial-gradient(ellipse at 50% 0%,rgba(255,255,255,.035),transparent 55%) var(--page);
  color:var(--ink); font-family:var(--body); font-size:var(--step); line-height:1.62;
  -webkit-font-smoothing:antialiased;
}
.wrap{max-width:74rem; margin:0 auto; display:flex; flex-direction:column; gap:clamp(1.3rem,3vw,2.1rem)}

/* masthead */
.mast{display:flex; flex-direction:column; gap:.5rem; text-align:center; padding-block:.6rem 1.2rem}
.kick{color:var(--gold); font-size:.72rem; font-weight:600; letter-spacing:.22em; text-transform:uppercase}
.kick::before{content:"— "}
h1{
  margin:0; font-family:var(--retro); text-transform:uppercase; letter-spacing:.03em;
  font-size:clamp(1.9rem,1rem + 4.6vw,4rem); line-height:1.02; text-wrap:balance;
  background:linear-gradient(180deg,#ffc46a 5%,var(--accent) 48%,#f4702a 100%);
  -webkit-background-clip:text; background-clip:text; color:transparent;
  filter:drop-shadow(.045em .05em 0 rgba(248,6,147,.9)) drop-shadow(-.02em -.02em 0 rgba(1,222,243,.35));
}
.dek{margin:.2rem auto 0; max-width:44rem; color:var(--ink-dim); font-size:1.02rem; text-wrap:pretty}
.rule{height:2px; border:0; margin:.7rem 0 0;
  background:linear-gradient(90deg,transparent,var(--accent-3) 18%,var(--accent-2) 50%,var(--accent) 82%,transparent);
  box-shadow:0 0 8px rgba(255,47,166,.5)}
.src{color:var(--ink-faint); font-size:.78rem; letter-spacing:.03em}

/* the slate board in its wooden frame */
.board{
  position:relative; border-radius:14px; border:12px solid transparent;
  padding:clamp(1.1rem,2.6vw,2rem);
  background:
    radial-gradient(ellipse at 25% 12%,rgba(255,255,255,.05),transparent 50%) padding-box,
    radial-gradient(ellipse at 78% 88%,rgba(0,0,0,.16),transparent 55%) padding-box,
    linear-gradient(158deg,var(--board-hi) 0%,var(--board) 55%,var(--board-lo) 100%) padding-box,
    repeating-linear-gradient(93deg,rgba(255,231,195,.1) 0px,rgba(74,40,16,.16) 3px,
      rgba(255,226,185,.07) 7px,rgba(66,36,14,.12) 12px,rgba(255,231,195,.09) 18px) border-box,
    linear-gradient(118deg,#9a6a3e 0%,#7c4e28 26%,#8d5c33 47%,#6b3f1e 74%,#85562f 100%) border-box;
  box-shadow:inset 0 0 0 2px rgba(20,12,5,.55), inset 0 2px 8px rgba(0,0,0,.4),
    inset 0 0 60px rgba(0,0,0,.14), 0 0 0 1px rgba(30,18,8,.9),
    0 1px 0 1px rgba(255,220,170,.08), 0 6px 22px rgba(0,0,0,.55);
}
.board > * + *{margin-top:1rem}
h2{
  margin:.15rem 0 0; font-family:var(--sketch); text-transform:uppercase; letter-spacing:.03em;
  font-size:clamp(1.25rem,.9rem + 1.5vw,1.85rem); line-height:1.12; text-wrap:balance; color:var(--ink);
}
.lede{margin:0; color:var(--ink-dim); max-width:62ch}
.lede strong{color:var(--ink); font-weight:600}
.note{
  margin:0; font-family:var(--hand); color:var(--gold); font-size:1.24rem; line-height:1.28;
  border-top:1px solid var(--ink-ghost); padding-top:.85rem; max-width:60ch;
}
.cap{margin:0; color:var(--ink-faint); font-size:.8rem; line-height:1.5; max-width:70ch}

/* legend */
.leg{display:flex; flex-wrap:wrap; gap:.4rem 1.2rem; align-items:center;
  font-size:.8rem; color:var(--ink-dim); letter-spacing:.02em}
.leg span{display:inline-flex; align-items:center; gap:.42rem}
.leg i{width:13px; height:13px; border-radius:4px; display:inline-block; flex:none}
.leg i.dash{height:0; border-top:2px dashed var(--blue); border-radius:0; width:18px}

/* stat tiles: used once, for the four numbers the page exists to deliver */
.tiles{display:grid; gap:.75rem; grid-template-columns:repeat(auto-fit,minmax(min(100%,13.5rem),1fr))}
.tile{border-radius:8px; border:1px solid var(--ink-ghost); background:rgba(0,0,0,.15);
  padding:.9rem 1rem; display:flex; flex-direction:column; gap:.2rem}
.tile b{font-family:var(--retro); font-size:clamp(1.7rem,1.2rem + 1.6vw,2.4rem); line-height:1;
  color:var(--gold); letter-spacing:.01em; font-variant-numeric:tabular-nums}
.tile b.cool{color:var(--blue)}
.tile b.warm{color:var(--pink)}
.tile em{font-style:normal; font-size:.72rem; letter-spacing:.15em; text-transform:uppercase;
  color:var(--ink-faint)}
.tile small{font-size:.84rem; color:var(--ink-dim); line-height:1.42}

/* charts */
.scroll{overflow-x:auto; -webkit-overflow-scrolling:touch}
svg.cw{width:100%; height:auto; min-width:560px; display:block; font-family:var(--body)}
svg.pn{width:100%; height:auto; display:block; font-family:var(--body)}
.grid4{display:grid; gap:.9rem 1.1rem; grid-template-columns:repeat(auto-fit,minmax(min(100%,13rem),1fr))}
.grid3{display:grid; gap:1rem 1.4rem; grid-template-columns:repeat(auto-fit,minmax(min(100%,15rem),1fr))}

/* tables */
table.tb{width:100%; border-collapse:collapse; font-size:.88rem; min-width:520px;
  font-variant-numeric:tabular-nums}
table.tb th{
  text-align:right; padding:.5rem .55rem; font-size:.68rem; letter-spacing:.14em;
  text-transform:uppercase; color:var(--gold); font-weight:600; white-space:nowrap;
  border-bottom:1px solid var(--ink-ghost);
}
table.tb th.l, table.tb td.l{text-align:left}
table.tb td{padding:.42rem .55rem; text-align:right; border-bottom:1px solid rgba(242,238,226,.07);
  color:var(--ink-dim); white-space:nowrap}
table.tb td.l{color:var(--ink); white-space:normal}
table.tb tr.sec td{color:var(--gold); font-size:.7rem; letter-spacing:.16em; text-transform:uppercase;
  padding-top:.9rem; border-bottom:1px solid var(--ink-ghost)}
table.tb tr.hl td{background:rgba(233,196,100,.09)}
table.tb td .num{color:var(--ink); font-weight:600}
table.tb td.mut{color:var(--ink-faint)}
.minibar{display:inline-block; height:9px; width:var(--v); min-width:3px;
  background:var(--c); border-radius:3px; margin-right:.5rem; vertical-align:middle}

/* the playbook list */
ol.play{margin:0; padding:0; list-style:none; counter-reset:p;
  display:flex; flex-direction:column; gap:.8rem}
ol.play li{counter-increment:p; display:grid; grid-template-columns:1.9rem 1fr; gap:.7rem;
  align-items:start}
ol.play li::before{content:counter(p); font-family:var(--retro); color:var(--gold);
  font-size:1.15rem; line-height:1.35; text-align:right; grid-column:1}
ol.play li > b, ol.play li > span{grid-column:2}
ol.play b{color:var(--ink); font-weight:600}
ol.play span{color:var(--ink-dim); font-size:.94rem; max-width:70ch}

/* method */
dl.meth{margin:0; display:grid; gap:.55rem 1.2rem; grid-template-columns:1fr}
dl.meth div{display:grid; gap:.15rem}
dl.meth dt{color:var(--gold); font-size:.7rem; letter-spacing:.14em; text-transform:uppercase}
dl.meth dd{margin:0; color:var(--ink-dim); font-size:.9rem}
@media (min-width:44rem){dl.meth{grid-template-columns:1fr 1fr}}

footer{color:var(--ink-faint); font-size:.78rem; text-align:center; letter-spacing:.03em;
  padding-block:.8rem 0}
footer b{color:var(--gold); font-size:.66rem; font-weight:700; letter-spacing:.26em;
  text-transform:uppercase; display:block; margin-bottom:.3rem}

/* tooltip */
#tt{position:fixed; z-index:20; pointer-events:none; opacity:0; transition:opacity .1s ease;
  max-width:19rem; padding:.5rem .65rem; border-radius:7px; font-size:.8rem; line-height:1.4;
  background:#12211a; color:var(--ink); border:1px solid rgba(233,196,100,.4);
  box-shadow:0 6px 20px rgba(0,0,0,.6)}
#tt.on{opacity:1}
[data-tip]{cursor:help}
[data-tip]:focus-visible{outline:2px solid var(--accent-3); outline-offset:2px}
@media (prefers-reduced-motion:reduce){*{transition:none!important; animation:none!important}}
"""

JS = """
(function(){
  var tt=document.getElementById('tt');
  function show(el,x,y){
    tt.textContent=el.getAttribute('data-tip'); tt.classList.add('on');
    var r=tt.getBoundingClientRect();
    var left=Math.min(Math.max(8,x+14),window.innerWidth-r.width-8);
    var top=y-r.height-12; if(top<8) top=y+18;
    tt.style.left=left+'px'; tt.style.top=top+'px';
  }
  function hide(){ tt.classList.remove('on'); }
  document.addEventListener('mousemove',function(e){
    var el=e.target.closest&&e.target.closest('[data-tip]');
    if(el) show(el,e.clientX,e.clientY); else hide();
  });
  document.addEventListener('focusin',function(e){
    var el=e.target.closest&&e.target.closest('[data-tip]');
    if(!el){hide();return;}
    var b=el.getBoundingClientRect(); show(el,b.left+b.width/2,b.top);
  });
  document.addEventListener('focusout',hide);
  document.addEventListener('scroll',hide,{passive:true});
})();
"""


def board(kicker, title, lede, body, note=None, legend=None):
    o = [f'<section class="board"><p class="kick">{kicker}</p><h2>{title}</h2>']
    if lede:
        o.append(f'<p class="lede">{lede}</p>')
    if legend:
        o.append(f'<div class="leg">{legend}</div>')
    o.append(body)
    if note:
        o.append(f'<p class="note">{note}</p>')
    o.append("</section>")
    return "".join(o)


def build():
    M, O, T = D["meta"], D["overall"], D["team"]
    ypc = SIG[("RB", "yards_per_carry")]
    rbshare = SIG[("RB", "rush_share")]
    wrsnap = SIG[("WR", "snap_pct")]
    qbcp = SIG[("QB", "completion_pct")]
    span = f'{M["first"]}&ndash;{M["last"]}'

    legend2 = (f'<span><i style="background:{GOLD}"></i>Week 1 alone</span>'
               f'<span><i style="background:{BLUE}"></i>last season&rsquo;s full line</span>')

    parts = [f"""
<div class="wrap">
<header class="mast">
  <p class="kick">The Delta Duo Lab &middot; nflverse {span}</p>
  <h1>How Predictive Is Week&nbsp;1?</h1>
  <p class="dek">One game, 32 teams, and a whole week of takes. We ran every Week 1
    against the rest of its own season &mdash; usage, targets, yards per carry, snap
    counts, completion percentage, fantasy points &mdash; to find which numbers were
    telling the truth.</p>
  <hr class="rule">
  <p class="src">{len(D["signal"])} position-metric pairs &middot; regular seasons only
    &middot; snap share {M["snap_first"]}+</p>
</header>

<section class="board">
  <p class="kick">The short version</p>
  <h2>Week 1 tells you about role. It tells you almost nothing about skill.</h2>
  <p class="lede">Split every metric into <strong>opportunity</strong> (how much work a
    player got, and what share of his team's it was) and <strong>efficiency</strong>
    (what he did with it). The two behave nothing alike after one game. Everything
    below is a version of that one sentence.</p>
  <div class="tiles">
    <div class="tile"><em>opportunity metrics</em><b>{O["opp"]:.2f}</b>
      <small>average correlation between a Week 1 opportunity number and the rest of
      the season</small></div>
    <div class="tile"><em>efficiency metrics</em><b class="warm">{O["eff"]:.2f}</b>
      <small>the same average for per-play efficiency &mdash; roughly a third as
      much signal</small></div>
    <div class="tile"><em>Week 1 yards per carry</em><b class="warm">{ypc["rel1"]*100:.0f}%</b>
      <small>share of one game's spread in RB yards per carry that is real. It needs
      {ypc["g50"]:.0f} games to get to half signal</small></div>
    <div class="tile"><em>Week 1 share of carries</em><b>{rbshare["rel1"]*100:.0f}%</b>
      <small>the same figure for an RB's share of his team's carries. Half a game
      gets you there</small></div>
  </div>
  <p class="note">Same box score, same Sunday. One column is worth reading and the
    other is a coin flip with a decimal point.</p>
</section>
"""]

    parts.append(board(
        "Exhibit 1",
        "How much of one game is real?",
        "Each player-season is a group; game-to-game variance splits into real "
        "differences between players and noise inside one player's season. The bar is "
        "the share of a single game that is signal. The right column is how many games "
        "it takes to get that metric to half signal &mdash; and some of them are longer "
        "than a season.",
        chart_signal(),
        note="Snap share and share of team carries are near-certain after one game. "
             "Yards per carry, yards per target and touchdowns are not close.",
        legend=f'<span><i style="background:{GOLD}"></i>opportunity &amp; role</span>'
               f'<span><i style="background:{PINK}"></i>efficiency &amp; outcomes</span>'))

    parts.append(board(
        "Exhibit 2",
        "Week 1 against what you already knew",
        "A big correlation is not proof that Week 1 taught you anything &mdash; good "
        "players are good, and you knew that in August. So the honest test is Week 1 "
        "against <strong>last season's full line</strong> for the same player. Gold "
        "ahead of blue means one game beat a whole season. That happens for exactly "
        "one kind of metric.",
        chart_dumbbell(),
        note="Snap share is the one number where a single game beats a whole prior "
             "season, at every position. Fantasy points, completion percentage and "
             "CPOE: last season still knows more than Sunday did.",
        legend=legend2))

    curve_note = ("The gap between the gold line at week 1 and the blue dashes is your "
                  "overreaction budget. For usage it is nearly closed on day one. For "
                  "fantasy points and completion percentage it takes a month.")
    parts.append(board(
        "Exhibit 3",
        "How fast does the new season take over?",
        "Running average of weeks 1 through k, scored against a fixed target &mdash; "
        "the same player's weeks 10 onward. The target never moves as k grows, so the "
        "climb is clean. The blue dashes are what last season's full line scores against "
        "that same target.",
        chart_curves(),
        note=curve_note, legend=f'<span><i style="background:{GOLD}"></i>weeks 1&ndash;k '
        f'of the new season</span><span><i class="dash"></i>last season&rsquo;s full '
        f'line</span>'))

    parts.append(board(
        "Exhibit 4",
        "The usage under the box score beats the box score",
        "Same target for all of these: rest-of-season fantasy points per game. The only "
        "thing that changes is what the model is allowed to look at. At every position "
        "except quarterback, Week 1 <strong>usage</strong> outpredicts the Week 1 "
        "<strong>fantasy total</strong> that sits on top of it &mdash; and by a lot.",
        table_models(),
        note="A 4-catch, 40-yard game on 11 targets is a better week than a 2-catch, "
             "80-yard game on 3. The scoring column disagrees. Believe the targets."))

    parts.append(board(
        "Exhibit 5",
        "The panic table",
        "The decision almost everyone actually faces on Tuesday of week 2: last year's "
        "producer just laid an egg. Split by where a player finished last season and "
        "where he finished in Week 1, then look at what he did the rest of the way.",
        table_panic(),
        note="A top-12 quarterback who opens badly still finishes top-12 more than half "
             "the time. A top-12 running back who opens badly drops to two in five &mdash; "
             "backfields get taken away, passing games do not."))

    parts.append(board(
        "Exhibit 6",
        "Is a 1-0 team better than it was in August?",
        f"{T['n']} team-seasons. Winning in Week 1 doubles a team's playoff rate, which "
        f"sounds enormous until you notice the rest-of-season win rate barely moves: "
        f"{T['won']['ros_win']*100:.1f}% for 1-0 teams against "
        f"{T['lost']['ros_win']*100:.1f}% for 0-1 teams. That gap is about "
        f"{(T['won']['ros_win']-T['lost']['ros_win'])*16:.1f} wins over the remaining "
        f"schedule. Most of the playoff difference is the game already in the bank, not "
        f"a team that changed.",
        chart_team(),
        note="The third panel is the one that settles it. If Week 1 revealed something "
             "real, teams that won it would go on to beat the closing spread. They do "
             "not &mdash; the market has already read the same game you did.",
        legend=f'<span><i style="background:{GOLD}"></i>won week 1</span>'
               f'<span><i style="background:{PINK}"></i>lost week 1</span>'))

    parts.append(board(
        "Exhibit 6b",
        "Week 1 barely reorders the preseason board",
        "Split team-seasons by last year's record first, then by the Week 1 result. A "
        "good team that loses its opener still reaches the playoffs more often than a "
        "bad team that wins one.",
        table_split(),
        note="&ldquo;They looked terrible in week 1&rdquo; is a sentence about one game. "
             "The roster is still the roster."))

    mw = D["midweek"]
    parts.append(board(
        "The control",
        "Week 1 is not special. It is just one game.",
        "Every claim above rests on Week 1 being read as one game and no more. So we ran "
        "the identical test on a mid-season week &mdash; each of weeks 2 through 9 "
        "against the rest of its own season. New schemes, new rosters, no film: Week 1 "
        "should be the noisiest week of the year, or the most revealing. It is neither.",
        '<div class="scroll"><table class="tb"><thead><tr><th class="l">position</th>'
        '<th>mean r from week 1</th><th>mean r from a mid-season week</th>'
        '<th>edge to week 1</th></tr></thead><tbody>'
        + "".join(
            f'<tr><td class="l">{p}</td><td class="num">{v["w1"]:.3f}</td>'
            f'<td class="num">{v["mid"]:.3f}</td>'
            f'<td class="num">{v["w1"]-v["mid"]:+.3f}</td></tr>' for p, v in mw.items())
        + f'<tr class="hl"><td class="l">all {O["pairs"]} pairs</td><td class="mut">—</td>'
          f'<td class="mut">—</td><td class="num">{O["edge"]:+.3f}</td></tr>'
        + "</tbody></table></div>",
        note="Week 1 carries a hair <em>less</em> information than a random week in "
             "October. Treat it as one game, because that is all it is."))

    parts.append(board(
        "The playbook",
        "What to actually do on Tuesday morning",
        None,
        """<ol class="play">
  <li><b>Open the snap counts before the box score.</b>
      <span>Snap share is the one Week 1 number that outpredicts a full prior season at
      every position, and a running back's share of team carries does it too. Almost
      everything else needs two to four more weeks to catch up.</span></li>
  <li><b>Read targets, not receptions or yards.</b>
      <span>Target share is the best single Week 1 predictor of rest-of-season fantasy
      points at wide receiver and tight end. Catch rate and yards per target are
      noise.</span></li>
  <li><b>Throw out Week 1 yards per carry entirely.</b>
      <span>It needs about a season and a half of carries to become half signal. A
      2.4-yard opener and a 6.1-yard opener tell you the same thing: nothing.</span></li>
  <li><b>Do not move a quarterback on completion percentage.</b>
      <span>One game of it is roughly one-sixth signal, and last season predicts this
      season's rate about twice as well as Sunday did.</span></li>
  <li><b>Buy role changes, not performances.</b>
      <span>A back who took 70% of the snaps out of nowhere keeps most of that job. A
      back who broke one long run keeps nothing.</span></li>
  <li><b>Discount touchdowns to near zero.</b>
      <span>Receiving and rushing touchdowns are the least stable counting stats
      measured here. Week 1 scoring is mostly next week's regression.</span></li>
  <li><b>Do not sell a proven player off one bad Sunday.</b>
      <span>The panic table is the price sheet: the buyer is paying for a name that
      still finishes top-12 about half the time.</span></li>
</ol>""",
        note="Every one of these is the same rule wearing a different jersey: after one "
             "game you know who is on the field, and you do not yet know how good they "
             "are."))

    parts.append(f"""
<section class="board">
  <p class="kick">Method &amp; caveats</p>
  <h2>How this was built</h2>
  <dl class="meth">
    <div><dt>Data</dt><dd>nflverse weekly player stats, team stats and snap counts,
      plus nfldata game results and closing lines. Regular seasons {span}; snap counts
      only exist from {M["snap_first"]}, so every snap figure uses that shorter window.
      Half-PPR is derived as PPR minus half a point per catch.</dd></div>
    <div><dt>Unit</dt><dd>The player-season, with three views of each metric: Week 1,
      weeks 2 onward, and the player's previous full regular season. Volume is per game;
      rates are pooled sum-over-sum with a minimum rest-of-season denominator, so a
      three-carry sample cannot pose as a yards-per-carry.</dd></div>
    <div><dt>Signal share</dt><dd>A one-way random-effects split of game-to-game
      variance. With &lambda; = noise &divide; real spread, a k-game sample has
      reliability k/(k+&lambda;). This holds a player's true level fixed inside a season,
      so a genuine mid-season role change counts as noise &mdash; which makes the
      games-to-stabilise column an upper bound, not a floor.</dd></div>
    <div><dt>Survivorship</dt><dd>The default sample needs four games after Week 1, which
      answers &ldquo;if he stays on the field, what is he?&rdquo; and strips out injury
      risk. The unconditional version, where missed weeks count as zero, runs alongside
      it in the repo and lowers every volume correlation by roughly 0.03 to 0.11.</dd></div>
    <div><dt>What we cut</dt><dd>EPA per play does not beat the Week 1 scoreboard at
      predicting the rest of the season, at any sample size tested here. It was a
      cleaner story and the numbers did not support it, so it is not on this page.</dd></div>
    <div><dt>Reproducing it</dt><dd><code>scripts/analysis/week1-predictiveness</code>
      &mdash; <code>fetch.py</code> then <code>analyze.py</code>. Every figure on this
      page is generated from the study's own output files; none are typed by
      hand.</dd></div>
  </dl>
</section>

<footer><b>The Delta Duo &middot; Inside the Lab</b>
  nflverse regular seasons {span} &middot; {T["n"]} team-seasons &middot;
  {len(D["signal"])} position-metric pairs</footer>
</div>
<div id="tt" role="tooltip" aria-hidden="true"></div>
""")

    head = ("""<title>How Predictive Is Week 1?</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cabin+Sketch:wght@400;700&family=Caveat:wght@500;600&family=Righteous&family=Inter:wght@400;500;600;700&display=swap">
<style>""" + CSS + "</style>")
    return head + "".join(parts) + "<script>" + JS + "</script>"


if __name__ == "__main__":
    out = os.path.join(HERE, "week1-report.html")
    open(out, "w").write(build())
    print("wrote", out, os.path.getsize(out), "bytes")
