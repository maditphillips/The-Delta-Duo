"use client";

import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import ChalkCard from "@/components/ChalkCard";
import StatTile from "@/components/StatTile";
import ChalkTooltip from "@/components/charts/ChalkTooltip";
import { CHALK, axisLine, axisTick, gridProps } from "@/components/charts/theme";
import { stadiums, stadiumMeta, type Stadium, type StadiumBand } from "@/data/stadiums";

// Diverging pair, validated against the board surface (#466553):
// gold <-> blue clears CVD separation at dE 18.7 (protan) / 20.8 (normal vision),
// where the site's pink/blue pair only reaches the 6.8 warning band. Near-zero
// venues take neutral chalk ink so the midpoint is not a hue.
const HARD = CHALK.gold;
const EASY = CHALK.blue;
const NEUTRAL = "rgba(242,238,226,0.55)";
const barColor = (d: number) => (d <= -1 ? HARD : d >= 1 ? EASY : NEUTRAL);

const pp = (v: number) => `${v > 0 ? "+" : ""}${v.toFixed(1)} pp`;
const yds = (v: number) => `${v > 0 ? "+" : ""}${v.toFixed(2)} yds`;

type Scope = "all" | "current" | "outdoor";
type SortKey =
  | "visDiff"
  | "name"
  | "visPct"
  | "visN"
  | "gap"
  | "puntOE"
  | "homeLongKickRate"
  | "homeDiff";

const scopeLabel: Record<Scope, string> = {
  all: `All ${stadiumMeta.venues} venues`,
  current: "Current venues only",
  outdoor: "Outdoor only",
};

// Four team codes host two venues each in this span (SF, NYG/NYJ, ATL, MIN),
// so a bare team code would collide on the axis. Disambiguate those with the
// venue's opening season and leave the unique ones alone.
const labelCounts = stadiums.reduce<Record<string, number>>((acc, s) => {
  const k = s.teams.join("/") || s.id;
  acc[k] = (acc[k] ?? 0) + 1;
  return acc;
}, {});
const shortLabel = (s: Stadium) => {
  const k = s.teams.join("/") || s.id;
  return labelCounts[k] > 1 ? `${k} \u2019${String(s.firstSeason).slice(2)}` : k;
};

function fitLine(pts: { x: number; y: number }[]) {
  const n = pts.length;
  const mx = pts.reduce((s, p) => s + p.x, 0) / n;
  const my = pts.reduce((s, p) => s + p.y, 0) / n;
  const num = pts.reduce((s, p) => s + (p.x - mx) * (p.y - my), 0);
  const den = pts.reduce((s, p) => s + (p.x - mx) ** 2, 0);
  const slope = num / den;
  return { slope, intercept: my - slope * mx };
}

export default function StadiumDashboard() {
  const [scope, setScope] = useState<Scope>("all");
  const [sort, setSort] = useState<SortKey>("visDiff");
  const [selectedId, setSelectedId] = useState<string>("BOS00");

  const scoped = useMemo(() => {
    if (scope === "current") return stadiums.filter((s) => s.lastSeason >= 2025);
    if (scope === "outdoor") return stadiums.filter((s) => s.roof === "outdoors");
    return stadiums;
  }, [scope]);

  const ladder = useMemo(
    () => [...scoped].sort((a, b) => a.visDiff - b.visDiff).map((s) => ({ ...s, short: shortLabel(s) })),
    [scoped]
  );

  const table = useMemo(() => {
    const rows = [...scoped];
    const num = (s: Stadium, k: SortKey) => {
      const v = s[k as keyof Stadium];
      return typeof v === "number" ? v : Number.NEGATIVE_INFINITY;
    };
    if (sort === "name") rows.sort((a, b) => a.name.localeCompare(b.name));
    else if (sort === "visDiff") rows.sort((a, b) => a.visDiff - b.visDiff);
    else rows.sort((a, b) => num(b, sort) - num(a, sort));
    return rows;
  }, [scoped, sort]);

  const scatter = useMemo(
    () =>
      scoped
        .filter((s) => s.homeLongKickRate !== null)
        .map((s) => ({ x: s.visDiff, y: s.homeLongKickRate as number, name: s.name, short: shortLabel(s), team: s.teams.join("/") })),
    [scoped]
  );

  const trend = useMemo(() => {
    if (scatter.length < 3) return null;
    const { slope, intercept } = fitLine(scatter);
    const xs = scatter.map((p) => p.x);
    const x1 = Math.min(...xs);
    const x2 = Math.max(...xs);
    return [
      { x: x1, y: slope * x1 + intercept },
      { x: x2, y: slope * x2 + intercept },
    ] as [{ x: number; y: number }, { x: number; y: number }];
  }, [scatter]);

  const selected = stadiums.find((s) => s.id === selectedId) ?? stadiums[0];
  const hardest = stadiums[0];
  const ordinary = stadiums.filter((s) => Math.abs(s.visDiff) <= 1).length;

  const bandRows = [
    { label: "Inside 30", v: selected.bands.u30 },
    { label: "30–39", v: selected.bands.d30 },
    { label: "40–49", v: selected.bands.d40 },
    { label: "50+", v: selected.bands.d50 },
  ].filter((r) => r.v !== null) as { label: string; v: StadiumBand }[];

  return (
    <div className="flex flex-col gap-8">
      <div className="grid gap-4 sm:grid-cols-3">
        <StatTile
          value={pp(hardest.visDiff)}
          label={`${hardest.name} — hardest venue in the NFL`}
          sublabel={`visiting kickers made ${hardest.visPct}% against ${hardest.visExp}% expected, over ${hardest.visN} attempts`}
          color={HARD}
        />
        <StatTile
          value={`${ordinary} of ${stadiumMeta.venues}`}
          label="venues land within a point of league expectation"
          sublabel="most stadiums have no kicking personality at all — the reputations belong to a handful"
          color={CHALK.white}
        />
        <StatTile
          value="r = +0.64"
          label="venue difficulty vs how often the home team tries a 50-yarder"
          sublabel="teams price the building into their own fourth-down math (p < 0.0001)"
          color={EASY}
        />
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span style={{ color: "var(--ink-dim)" }}>Show:</span>
        {(Object.keys(scopeLabel) as Scope[]).map((k) => (
          <button key={k} className={`chalk-btn ${scope === k ? "selected" : ""}`} onClick={() => setScope(k)}>
            {scopeLabel[k]}
          </button>
        ))}
      </div>

      <ChalkCard
        kicker="every venue, 2002–2025"
        title="The Kicking Ladder"
        note={`Actual minus expected field goal percentage for VISITING kickers, so no venue is graded on its home team's kicker. Expectation comes from a distance-and-season model refit for each venue with that venue's own kicks held out. Bars left of zero are harder than the league, right of zero easier; venues within a point of expectation are drawn in neutral chalk. ${scoped.length} venues shown.`}
        source="nflverse play-by-play · blocked kicks excluded"
      >
        <div className="mb-2 flex flex-wrap gap-x-5 gap-y-1 text-base" style={{ color: "var(--ink-dim)" }}>
          {[
            { label: "Harder than expected", color: HARD },
            { label: "Within 1 pp", color: NEUTRAL },
            { label: "Easier than expected", color: EASY },
          ].map((it) => (
            <span key={it.label} className="flex items-center gap-2">
              <span
                aria-hidden
                style={{ background: it.color, width: 12, height: 12, borderRadius: 3, display: "inline-block" }}
              />
              {it.label}
            </span>
          ))}
        </div>
        <ResponsiveContainer width="100%" height={Math.max(320, ladder.length * 23)}>
          <BarChart data={ladder} layout="vertical" margin={{ top: 4, right: 16, bottom: 4, left: 4 }} barCategoryGap={2}>
            <CartesianGrid {...gridProps} horizontal={false} vertical />
            <XAxis
              type="number"
              tick={axisTick}
              axisLine={axisLine}
              tickLine={false}
              domain={[-8, 6]}
              tickFormatter={(v: number) => `${v > 0 ? "+" : ""}${v}`}
              unit=" pp"
            />
            <YAxis
              type="category"
              dataKey="short"
              axisLine={axisLine}
              tickLine={false}
              width={132}
              interval={0}
              tick={((props: { x?: number | string; y?: number | string; payload?: { value?: unknown } }) => {
                // The value rides in the axis gutter rather than on the bar:
                // Recharts anchors bar labels to the zero baseline, which puts
                // them on the wrong end of a diverging bar.
                const label = String(props.payload?.value ?? "");
                const d = ladder.find((v) => v.short === label);
                const x = Number(props.x ?? 0);
                const y = Number(props.y ?? 0);
                return (
                  <g>
                    <text x={x - 52} y={y} textAnchor="end" dominantBaseline="central" fill={CHALK.inkDim} fontSize={12.5} fontFamily="Inter, ui-sans-serif, system-ui, sans-serif">
                      {label}
                    </text>
                    {d && (
                      <text x={x - 6} y={y} textAnchor="end" dominantBaseline="central" fill={barColor(d.visDiff)} fontSize={12} fontFamily="Inter, ui-sans-serif, system-ui, sans-serif" style={{ fontVariantNumeric: "tabular-nums" }}>
                        {d.visDiff > 0 ? "+" : ""}{d.visDiff.toFixed(1)}
                      </text>
                    )}
                  </g>
                );
              }) as never}
            />
            <ReferenceLine x={0} stroke={CHALK.inkFaint} strokeWidth={2} />
            <Tooltip
              cursor={{ fill: "rgba(242,238,226,0.06)" }}
              content={
                <ChalkTooltip
                  format={(v) => pp(v)}
                />
              }
            />
            <Bar dataKey="visDiff" name="vs expectation" radius={[4, 4, 4, 4]} minPointSize={2} isAnimationActive={false}>
              {ladder.map((d) => (
                <Cell key={d.id} fill={barColor(d.visDiff)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </ChalkCard>

      <ChalkCard
        kicker="the market is efficient"
        title="Teams Price the Building In"
        note={`Each dot is a venue. Across the ${scatter.length} venues shown, the harder a stadium is on visiting kickers, the less often its own home team attempts a 50-yard field goal on fourth down — r = +0.64, p < 0.0001. New England sits at the far end of both axes: the hardest venue in the league, and a home team that attempted ${hardest.homeLongKickRate}% of its long chances against a league home rate of ${stadiumMeta.leagueLongKickRate}%.`}
        source="4th down, 50–62 yd attempt available, win probability 5–95%"
      >
        <ResponsiveContainer width="100%" height={380}>
          <ScatterChart margin={{ top: 12, right: 20, bottom: 30, left: 4 }}>
            <CartesianGrid {...gridProps} vertical />
            <XAxis
              type="number"
              dataKey="x"
              name="venue difficulty"
              tick={axisTick}
              axisLine={axisLine}
              tickLine={false}
              domain={[-8, 6]}
              tickFormatter={(v: number) => `${v > 0 ? "+" : ""}${v}`}
              label={{
                value: "visiting-kicker FG% vs expected (pp)  →  easier",
                position: "insideBottom",
                offset: -18,
                fill: CHALK.inkDim,
                fontSize: 12.5,
              }}
            />
            <YAxis
              type="number"
              dataKey="y"
              name="home 50+ attempt rate"
              tick={axisTick}
              axisLine={axisLine}
              tickLine={false}
              unit="%"
              width={48}
            />
            <ReferenceLine y={stadiumMeta.leagueLongKickRate} stroke={CHALK.inkGhost} strokeDasharray="4 6" />
            <ReferenceLine x={0} stroke={CHALK.inkGhost} strokeDasharray="4 6" />
            {trend && (
              <ReferenceLine
                segment={trend}
                stroke={CHALK.inkFaint}
                strokeWidth={2}
                strokeDasharray="6 5"
                ifOverflow="extendDomain"
              />
            )}
            <Tooltip
              cursor={{ stroke: CHALK.inkGhost }}
              content={
                <ChalkTooltip
                  format={(v, name) => (name === "home 50+ attempt rate" ? `${v.toFixed(1)}%` : pp(v))}
                />
              }
            />
            <Scatter data={scatter} name="venue" isAnimationActive={false}>
              {scatter.map((d) => (
                <Cell key={d.name} fill={barColor(d.x)} stroke="var(--board)" strokeWidth={2} r={6} />
              ))}
              <LabelList
                dataKey="short"
                content={(props: { x?: number | string; y?: number | string; index?: number }) => {
                  const i = props.index ?? -1;
                  const d = scatter[i];
                  // label only the venues that anchor the story
                  if (!d || !["NE", "CHI", "DEN", "GB"].includes(d.team)) return null;
                  return (
                    <text
                      x={Number(props.x ?? 0) + 10}
                      y={Number(props.y ?? 0) - 8}
                      fill={CHALK.inkDim}
                      fontSize={12}
                      fontFamily="Inter, ui-sans-serif, system-ui, sans-serif"
                    >
                      {d.team}
                    </text>
                  );
                }}
              />
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </ChalkCard>

      <ChalkCard
        kicker={`${selected.firstSeason}–${selected.lastSeason} · ${selected.games} games`}
        title={selected.name}
        note={`Pick any venue in the table below to load its profile here. Punt distance and kickoff carry are aerodynamic probes — nobody is aiming at uprights — so they test whether a venue is genuinely hard on ball flight rather than merely unlucky.`}
        source={`${selected.teams.join(" / ") || "neutral site"} · ${selected.roof} · ${selected.surface}`}
        alt
      >
        <div className="grid gap-5 sm:grid-cols-2">
          <div>
            <div className="chalk-kicker mb-2">Field goals</div>
            <table className="chalk-table">
              <tbody>
                <tr>
                  <td>Visiting kickers</td>
                  <td className="num">{selected.visPct.toFixed(1)}%</td>
                  <td className="num" style={{ color: barColor(selected.visDiff) }}>
                    {pp(selected.visDiff)}
                  </td>
                </tr>
                <tr>
                  <td>Home kickers</td>
                  <td className="num">{selected.homePct.toFixed(1)}%</td>
                  <td className="num" style={{ color: barColor(selected.homeDiff) }}>
                    {pp(selected.homeDiff)}
                  </td>
                </tr>
                <tr>
                  <td>Home minus visitor</td>
                  <td className="num">—</td>
                  <td className="num">{pp(selected.gap)}</td>
                </tr>
                <tr>
                  <td>Rank on visiting kickers</td>
                  <td className="num">—</td>
                  <td className="num">
                    {selected.visRank} of {stadiumMeta.venues}
                  </td>
                </tr>
              </tbody>
            </table>

            {bandRows.length > 0 && (
              <>
                <div className="chalk-kicker mt-5 mb-2">Visiting kickers by distance</div>
                <table className="chalk-table">
                  <tbody>
                    {bandRows.map((r) => (
                      <tr key={r.label}>
                        <td>{r.label} yds</td>
                        <td className="num" style={{ color: "var(--ink-faint)" }}>
                          n={r.v.n}
                        </td>
                        <td className="num" style={{ color: barColor(r.v.diff) }}>
                          {pp(r.v.diff)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            )}
          </div>

          <div>
            <div className="chalk-kicker mb-2">Ball flight &amp; behaviour</div>
            <table className="chalk-table">
              <tbody>
                <tr>
                  <td>Gross punt distance</td>
                  <td className="num">{selected.puntOE === null ? "—" : yds(selected.puntOE)}</td>
                </tr>
                <tr>
                  <td>Kickoff carry</td>
                  <td className="num">{selected.koDistOE === null ? "—" : yds(selected.koDistOE)}</td>
                </tr>
                <tr>
                  <td>Touchback rate</td>
                  <td className="num">{selected.touchback === null ? "—" : `${selected.touchback.toFixed(1)}%`}</td>
                </tr>
                <tr>
                  <td>Visiting kickers in 15+ mph wind</td>
                  <td className="num">{selected.windyDiff === null ? "—" : pp(selected.windyDiff)}</td>
                </tr>
                <tr>
                  <td>Misses that were wide, not short</td>
                  <td className="num">{selected.wideOnly === null ? "—" : `${selected.wideOnly.toFixed(1)}%`}</td>
                </tr>
                <tr>
                  <td>Home team&apos;s 50+ attempt rate</td>
                  <td className="num">
                    {selected.homeLongKickRate === null ? "—" : `${selected.homeLongKickRate.toFixed(1)}%`}
                  </td>
                </tr>
                <tr>
                  <td>Direction-of-play split</td>
                  <td className="num">{selected.dirSplit === null ? "—" : pp(selected.dirSplit)}</td>
                </tr>
              </tbody>
            </table>
            <p className="mt-3 text-sm leading-snug" style={{ color: "var(--ink-dim)" }}>
              Punt and kickoff figures are yards above or below what the same kick is worth elsewhere. The
              direction-of-play split compares visiting kickers in Q2+Q4 against Q1+Q3 — teams swap ends each quarter,
              so a large split points at one end of the stadium being worse than the other.
            </p>
          </div>
        </div>
      </ChalkCard>

      <ChalkCard
        kicker="the table view"
        title="Every Venue, Every Measure"
        note={`Sorted by ${sort === "name" ? "name" : "the selected column"}. Click any row to load that venue above. Positive means easier than the rest of the league.`}
        source={`${stadiumMeta.totalFG.toLocaleString()} field goals and ${stadiumMeta.totalPunts.toLocaleString()} punts, ${stadiumMeta.seasons}`}
      >
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <span style={{ color: "var(--ink-dim)" }}>Sort by:</span>
          {(
            [
              ["visDiff", "Hardest first"],
              ["visPct", "Raw visitor FG%"],
              ["gap", "Home advantage"],
              ["puntOE", "Punt distance"],
              ["homeLongKickRate", "Home 50+ rate"],
              ["visN", "Sample size"],
              ["name", "Name"],
            ] as [SortKey, string][]
          ).map(([k, label]) => (
            <button key={k} className={`chalk-btn ${sort === k ? "selected" : ""}`} onClick={() => setSort(k)}>
              {label}
            </button>
          ))}
        </div>
        <div className="scroll-x">
          <table className="chalk-table">
            <thead>
              <tr>
                <th>Venue</th>
                <th>Team</th>
                <th>Roof</th>
                <th className="num">Seasons</th>
                <th className="num">Vis. att</th>
                <th className="num">Vis. FG%</th>
                <th className="num">vs exp</th>
                <th className="num">Home vs exp</th>
                <th className="num">Gap</th>
                <th className="num">Punt</th>
                <th className="num">Home 50+</th>
              </tr>
            </thead>
            <tbody>
              {table.map((s) => (
                <tr
                  key={s.id}
                  onClick={() => setSelectedId(s.id)}
                  style={{
                    cursor: "pointer",
                    background: s.id === selectedId ? "rgba(242,238,226,0.07)" : undefined,
                  }}
                >
                  <td>{s.name}</td>
                  <td>{s.teams.join("/") || "—"}</td>
                  <td>{s.roof}</td>
                  <td className="num">
                    {s.firstSeason}–{s.lastSeason}
                  </td>
                  <td className="num">{s.visN}</td>
                  <td className="num">{s.visPct.toFixed(1)}%</td>
                  <td className="num" style={{ color: barColor(s.visDiff) }}>
                    {pp(s.visDiff)}
                  </td>
                  <td className="num">{pp(s.homeDiff)}</td>
                  <td className="num">{pp(s.gap)}</td>
                  <td className="num">{s.puntOE === null ? "—" : yds(s.puntOE)}</td>
                  <td className="num">{s.homeLongKickRate === null ? "—" : `${s.homeLongKickRate.toFixed(1)}%`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ChalkCard>

      <ChalkCard kicker="read this before you quote it" title="What the numbers can and cannot say" alt>
        <div className="flex flex-col gap-3 text-base leading-snug" style={{ color: "var(--ink-dim)" }}>
          <p>
            <strong style={{ color: "var(--ink)" }}>Venues differ; home-field kicking edges mostly do not.</strong>{" "}
            Across {stadiumMeta.venues} venues the spread of visiting-kicker penalties is larger than chance allows (p ={" "}
            {stadiumMeta.visChi2P}), so some stadiums really are harder than others. But the spread of{" "}
            <em>home-minus-visitor</em> gaps is not (p = {stadiumMeta.gapChi2P}, mean {pp(stadiumMeta.meanGap)}, sd{" "}
            {stadiumMeta.sdGap.toFixed(1)} pp). Difficulty is real. Asymmetry is mostly noise.
          </p>
          <p>
            <strong style={{ color: "var(--ink)" }}>Someone has to finish last.</strong> With{" "}
            {stadiumMeta.venues} venues in the pool, one of them will look extreme by luck alone. Only{" "}
            {hardest.name} survives correction for having searched all of them.
          </p>
          <p>
            <strong style={{ color: "var(--ink)" }}>Sample sizes are small.</strong> A venue gets roughly 20 visiting
            field goal attempts a season. Even the biggest sample here is {Math.max(...stadiums.map((s) => s.visN))}{" "}
            kicks across two decades, and the distance-band and direction splits divide that further. Treat single
            cells as suggestive, not settled.
          </p>
          <p>
            <strong style={{ color: "var(--ink)" }}>Blocked kicks are excluded.</strong> A block is a
            line-of-scrimmage failure rather than an aiming one, so it says nothing about the venue.
          </p>
        </div>
      </ChalkCard>
    </div>
  );
}
