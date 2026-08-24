"use client";

import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import ChalkCard from "@/components/ChalkCard";
import StatTile from "@/components/StatTile";
import ChalkTooltip from "@/components/charts/ChalkTooltip";
import { CHALK, axisLine, axisTick, gridProps } from "@/components/charts/theme";
import * as qb from "@/data/qb";

const pct = (v: number) => `${v.toFixed(1)}%`;

function Legend({ items }: { items: { label: string; color: string }[] }) {
  return (
    <div className="mb-2 flex flex-wrap gap-x-5 gap-y-1 text-base" style={{ color: "var(--ink-dim)" }}>
      {items.map((it) => (
        <span key={it.label} className="flex items-center gap-2">
          <span aria-hidden style={{ background: it.color, width: 12, height: 12, borderRadius: 3, display: "inline-block" }} />
          {it.label}
        </span>
      ))}
    </div>
  );
}

type Outcome = "everStarted" | "everTop24" | "everTop12";
const outcomeLabels: Record<Outcome, string> = {
  everStarted: "Ever started",
  everTop24: "Ever top-24",
  everTop12: "Ever top-12 (QB1)",
};

export default function QbDashboard() {
  const [bucketOutcome, setBucketOutcome] = useState<Outcome>("everTop12");
  const [classSort, setClassSort] = useState<"pick" | "everStarted" | "everTop12">("pick");

  const sortedClass = useMemo(() => {
    const rows = [...qb.class2026];
    if (classSort === "pick") rows.sort((a, b) => a.pick - b.pick);
    else rows.sort((a, b) => b[classSort] - a[classSort]);
    return rows;
  }, [classSort]);

  return (
    <div className="flex flex-col gap-8">
      {/* headline tiles */}
      <div className="grid gap-4 sm:grid-cols-3">
        <StatTile
          value="90.2×"
          label="Round 1 vs Day 3 odds of ever starting"
          sublabel="Draft capital buys access on a scale nothing else approaches"
          color={CHALK.yellow}
        />
        <StatTile
          value="0.028"
          label="FP/game gap, Round 1 vs Day 3"
          sublabel="among QBs with 16+ career starts (15.7 vs 15.6)"
          color={CHALK.blue}
        />
        <StatTile
          value="103%"
          label="of draft position's effect is explained by starter seasons"
          sublabel="capital buys duration, not quality"
          color={CHALK.salmon}
        />
      </div>

      {/* funnel */}
      <ChalkCard
        kicker="Act One"
        title="What a quarterback pick actually buys"
        note="2008–2022 classes, outcomes through 2025. Median Day 3 QB career: one start. Not one season — one game. Every comparison clears Holm correction."
      >
        <Legend
          items={[
            { label: "Ever started", color: CHALK.gold },
            { label: "Ever top-24", color: CHALK.pink },
            { label: "Ever top-12", color: CHALK.white },
          ]}
        />
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={qb.funnel} barCategoryGap="24%" barGap={2}>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="day" tick={axisTick} axisLine={axisLine} tickLine={false} />
            <YAxis tick={axisTick} axisLine={axisLine} tickLine={false} unit="%" domain={[0, 100]} />
            <Tooltip content={<ChalkTooltip format={(v) => pct(v)} />} cursor={{ fill: "rgba(242,238,226,0.06)" }} />
            <Bar dataKey="everStarted" name="Ever started" fill={CHALK.gold} fillOpacity={0.9} radius={[4, 4, 0, 0]} />
            <Bar dataKey="everTop24" name="Ever top-24" fill={CHALK.pink} fillOpacity={0.9} radius={[4, 4, 0, 0]} />
            <Bar dataKey="everTop12" name="Ever top-12" fill={CHALK.white} fillOpacity={0.9} radius={[4, 4, 0, 0]}>
              <LabelList dataKey="everTop12" position="top" formatter={(v) => `${v}%`} fill={CHALK.ink} fontSize={14} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <div className="scroll-x mt-4">
          <table className="chalk-table">
            <thead>
              <tr>
                <th>Draft day</th>
                <th className="num">n</th>
                <th className="num">Median career starts</th>
                <th className="num">Median attempts</th>
                <th className="num">Median starter seasons</th>
              </tr>
            </thead>
            <tbody>
              {qb.funnel.map((r) => (
                <tr key={r.day}>
                  <td>{r.day}</td>
                  <td className="num">{r.n}</td>
                  <td className="num">{r.medianStarts}</td>
                  <td className="num">{r.medianAttempts.toLocaleString()}</td>
                  <td className="num">{r.medianStarterSeasons}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ChalkCard>

      {/* pick buckets */}
      <ChalkCard
        kicker="Cliff or ramp?"
        title="Hit rate by pick bucket"
        note="No magic round exists — a square-root curve fits best and round boundaries add nothing (p = 0.59–0.87). The practical break: picks 1–64 are a different universe from picks 65+. Small buckets (n printed in tooltip) — don't over-read the 6–10 bucket's 100% on n = 8."
      >
        <div className="mb-3 flex flex-wrap gap-2">
          {(Object.keys(outcomeLabels) as Outcome[]).map((o) => (
            <button key={o} className={`chalk-btn ${bucketOutcome === o ? "selected" : ""}`} onClick={() => setBucketOutcome(o)}>
              {outcomeLabels[o]}
            </button>
          ))}
        </div>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={qb.pickBuckets} barCategoryGap="18%">
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="bucket" tick={axisTick} axisLine={axisLine} tickLine={false} />
            <YAxis tick={axisTick} axisLine={axisLine} tickLine={false} unit="%" domain={[0, 100]} />
            <Tooltip
              content={
                <ChalkTooltip
                  format={(v, name) => (name === "n" ? `${v}` : pct(v))}
                />
              }
              cursor={{ fill: "rgba(242,238,226,0.06)" }}
            />
            <Bar dataKey={bucketOutcome} name={outcomeLabels[bucketOutcome]} fill={CHALK.yellow} fillOpacity={0.9} radius={[4, 4, 0, 0]}>
              <LabelList dataKey="n" position="top" formatter={(v) => `n=${v}`} fill={CHALK.inkFaint} fontSize={12} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </ChalkCard>

      {/* the two absolutes + ladder */}
      <div className="grid gap-4 sm:grid-cols-2">
        <StatTile
          value="0 of 104"
          label="QBs without a 10-start season who ever finished top-24"
          sublabel="the gate closes perfectly in both directions"
          color={CHALK.salmon}
        />
        <StatTile
          value="33 of 33"
          label="QBs with 4+ starter seasons who finished top-24"
          sublabel="29 of 33 (87.9%) were ever top-12"
          color={CHALK.green}
        />
      </div>

      <ChalkCard
        kicker="The ladder"
        title="Availability is the gate"
        note="You cannot finish top-12 on 13 starts — zero counterexamples in 14 tries. Half of the 12–14-start QBs were startable in Superflex; none was ever a QB1. (12–14 row: n = 14 — suggestive, not a law.)"
      >
        <Legend
          items={[
            { label: "Ever top-24", color: CHALK.gold },
            { label: "Ever top-12", color: CHALK.pink },
          ]}
        />
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={qb.ladder} barCategoryGap="24%" barGap={2}>
            <CartesianGrid {...gridProps} />
            <XAxis
              dataKey="peakStarts"
              tick={axisTick}
              axisLine={axisLine}
              tickLine={false}
              label={{ value: "peak season starts", position: "insideBottom", offset: -4, fill: CHALK.inkFaint, fontSize: 13 }}
              height={50}
            />
            <YAxis tick={axisTick} axisLine={axisLine} tickLine={false} unit="%" domain={[0, 100]} />
            <Tooltip content={<ChalkTooltip format={(v) => pct(v)} />} cursor={{ fill: "rgba(242,238,226,0.06)" }} />
            <Bar dataKey="everTop24" name="Ever top-24" fill={CHALK.gold} fillOpacity={0.9} radius={[4, 4, 0, 0]} />
            <Bar dataKey="everTop12" name="Ever top-12" fill={CHALK.pink} fillOpacity={0.9} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </ChalkCard>

      {/* equality test */}
      <ChalkCard
        kicker="Act Two"
        title="The equality test — once they hold the job, the draft is over"
        note="0 of 48 comparisons separate Round 1 from Day 3 at the 16-start bar; 0 of 48 at 400 dropbacks. Once a Day 3 QB holds a starting job, his season is at least as likely to finish top-12 as a first-rounder's."
      >
        <div className="scroll-x">
          <table className="chalk-table">
            <thead>
              <tr>
                <th>Metric (16+ career starts)</th>
                <th className="num">Round 1 (n=47)</th>
                <th className="num">Day 3 (n=10)</th>
                <th className="num">p</th>
              </tr>
            </thead>
            <tbody>
              {qb.equalityMetrics.map((r) => (
                <tr key={r.metric}>
                  <td>{r.metric}</td>
                  <td className="num">{r.round1}</td>
                  <td className="num">{r.day3}</td>
                  <td className="num">{r.p}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-5">
          <Legend
            items={[
              { label: "Top-12 rate per starter season", color: CHALK.pink },
              { label: "Top-24 rate per starter season", color: CHALK.gold },
            ]}
          />
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={qb.perSeasonRates} barCategoryGap="26%" barGap={2}>
              <CartesianGrid {...gridProps} />
              <XAxis dataKey="day" tick={axisTick} axisLine={axisLine} tickLine={false} />
              <YAxis tick={axisTick} axisLine={axisLine} tickLine={false} unit="%" domain={[0, 100]} />
              <Tooltip content={<ChalkTooltip format={(v) => pct(v)} />} cursor={{ fill: "rgba(242,238,226,0.06)" }} />
              <Bar dataKey="top24Rate" name="Top-24 rate" fill={CHALK.gold} fillOpacity={0.9} radius={[4, 4, 0, 0]} />
              <Bar dataKey="top12Rate" name="Top-12 rate" fill={CHALK.pink} fillOpacity={0.9} radius={[4, 4, 0, 0]}>
                <LabelList dataKey="top12Rate" position="top" formatter={(v) => `${v}%`} fill={CHALK.ink} fontSize={14} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </ChalkCard>

      {/* rushing */}
      <ChalkCard
        kicker="Act Three"
        title="Rushing is a multiplier, not a substitute"
        note="Split at the medians (10.5 rush yds/game, 0.067 EPA/dropback), n = 504 starter seasons. Rushing lifts every efficiency tier — but no amount of rushing rescues a bad passer (OR 0.126, p = 2.2e-14 for legs-over-arm)."
      >
        <div className="grid gap-3 sm:grid-cols-2">
          {qb.rushing2x2.map((q) => (
            <div key={q.quadrant} className="chalk-inset px-4 py-4">
              <div className="text-lg" style={{ color: "var(--ink)" }}>
                {q.quadrant} <span style={{ color: "var(--ink-faint)" }}>(n={q.n})</span>
              </div>
              <div className="font-display mt-1 text-4xl font-bold" style={{ color: q.top12Rate >= 60 ? CHALK.green : q.top12Rate >= 15 ? CHALK.yellow : CHALK.salmon }}>
                {q.top12Rate}%
              </div>
              <div className="text-sm" style={{ color: "var(--ink-dim)" }}>
                top-12 rate · {q.medianFpg} median FP/G · {q.top24Rate}% top-24
              </div>
            </div>
          ))}
        </div>
      </ChalkCard>

      <ChalkCard
        kicker="The dead zone"
        title="Top-12 rate by rushing yards per game"
        note="U-shaped, not gated: the 10–15 yds/game band is the worst cell in the study (29.8%) — worse than QBs who don't run at all. Either the offense is built around the arm or the legs; in between is the worst place to be."
      >
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={qb.rushGradient} barCategoryGap="18%">
            <CartesianGrid {...gridProps} />
            <XAxis
              dataKey="band"
              tick={axisTick}
              axisLine={axisLine}
              tickLine={false}
              label={{ value: "rushing yards per game", position: "insideBottom", offset: -4, fill: CHALK.inkFaint, fontSize: 13 }}
              height={50}
            />
            <YAxis tick={axisTick} axisLine={axisLine} tickLine={false} unit="%" domain={[0, 100]} />
            <Tooltip content={<ChalkTooltip format={(v, n) => (n === "n" ? `${v}` : pct(v))} />} cursor={{ fill: "rgba(242,238,226,0.06)" }} />
            <Bar dataKey="top12Rate" name="Top-12 rate" fill={CHALK.yellow} fillOpacity={0.9} radius={[4, 4, 0, 0]}>
              <LabelList
                dataKey="deadZone"
                position="top"
                formatter={(v) => (v ? "☠ dead zone" : "")}
                fill={CHALK.salmon}
                fontSize={14}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </ChalkCard>

      <ChalkCard
        kicker="Stickiness"
        title="Forecast the legs, stay humble about the arm"
        note="Year-over-year Spearman correlation, 338 consecutive starter-season pairs. Efficiency has the largest effect on this season's finish and is the least projectable into next season. Rushing is more than twice as stable (0.864 vs 0.413)."
      >
        <Legend
          items={[
            { label: "Rushing inputs", color: CHALK.yellow },
            { label: "Passing / other inputs", color: CHALK.blue },
          ]}
        />
        <ResponsiveContainer width="100%" height={380}>
          <BarChart data={qb.stickiness} layout="vertical" margin={{ left: 60 }}>
            <CartesianGrid {...gridProps} horizontal={false} vertical />
            <XAxis type="number" tick={axisTick} axisLine={axisLine} tickLine={false} domain={[0, 1]} />
            <YAxis type="category" dataKey="input" tick={{ ...axisTick, fontSize: 13 }} axisLine={axisLine} tickLine={false} width={130} />
            <Tooltip content={<ChalkTooltip format={(v) => v.toFixed(3)} />} cursor={{ fill: "rgba(242,238,226,0.06)" }} />
            <Bar dataKey="r" name="Year-over-year r" fillOpacity={0.9} radius={[0, 4, 4, 0]}>
              {qb.stickiness.map((s, i) => (
                <Cell key={i} fill={s.kind === "rushing" ? CHALK.yellow : CHALK.blue} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </ChalkCard>

      {/* pre-draft board */}
      <ChalkCard
        kicker="Act Four"
        title="The pre-draft board — one signal survives"
        note="78 tests, six families, each run raw and with log(pick) controlled. College rushing is the only family that survives — and controlling for pick makes it STRONGER. The market has priced everything a scout can measure, and underpriced the one thing that predicts fantasy QB value."
      >
        <div className="scroll-x">
          <table className="chalk-table">
            <thead>
              <tr>
                <th>Signal family</th>
                <th className="num">Signals tested</th>
                <th className="num">Survivors (pick controlled)</th>
              </tr>
            </thead>
            <tbody>
              {qb.preDraftBoard.map((r) => (
                <tr key={r.family}>
                  <td style={{ color: r.survivors > 0 ? CHALK.green : "var(--ink)" }}>{r.family}</td>
                  <td className="num">{r.tested}</td>
                  <td className="num" style={{ color: r.survivors > 0 ? CHALK.green : CHALK.salmon }}>
                    {r.survivors} of {r.tested}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {qb.causalChain.map((c) => (
            <div key={c.step} className="chalk-inset px-4 py-3">
              <div className="font-display text-3xl font-bold" style={{ color: CHALK.violet }}>
                {c.step}
              </div>
              <div style={{ color: "var(--ink)" }}>{c.claim}</div>
              <div className="mt-1 text-sm" style={{ color: "var(--ink-dim)" }}>
                {c.stat}
              </div>
            </div>
          ))}
        </div>
      </ChalkCard>

      {/* the leash */}
      <ChalkCard
        kicker="Act Five"
        title="The leash — capital buys forgiveness"
        note="After a bottom-tercile season, first-rounders start again 60.3% of the time against 25.0% for Day 3 picks, and the effect survives controlling for performance (p = 0.0004). Play well and everyone keeps their job. Play badly and only the first-rounders do."
      >
        <Legend
          items={[
            { label: "Round 1", color: CHALK.yellow },
            { label: "Day 2", color: CHALK.blue },
            { label: "Day 3", color: CHALK.salmon },
          ]}
        />
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={qb.leashGradient} barCategoryGap="24%" barGap={2}>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="tercile" tick={axisTick} axisLine={axisLine} tickLine={false} />
            <YAxis tick={axisTick} axisLine={axisLine} tickLine={false} unit="%" domain={[0, 100]} />
            <Tooltip content={<ChalkTooltip format={(v) => pct(v)} />} cursor={{ fill: "rgba(242,238,226,0.06)" }} />
            <Bar dataKey="round1" name="Round 1" fill={CHALK.yellow} fillOpacity={0.9} radius={[4, 4, 0, 0]} />
            <Bar dataKey="day2" name="Day 2" fill={CHALK.blue} fillOpacity={0.9} radius={[4, 4, 0, 0]} />
            <Bar dataKey="day3" name="Day 3" fill={CHALK.salmon} fillOpacity={0.9} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
        <div className="scroll-x mt-4">
          <table className="chalk-table">
            <thead>
              <tr>
                <th>Give-up curve: no top-24 through year…</th>
                <th className="num">Round 1</th>
                <th className="num">Day 2</th>
                <th className="num">Day 3</th>
              </tr>
            </thead>
            <tbody>
              {qb.giveUpCurve.map((r) => (
                <tr key={r.throughYear}>
                  <td>Year {r.throughYear}</td>
                  <td className="num">
                    {r.round1}% <span style={{ color: "var(--ink-faint)" }}>(n={r.round1N})</span>
                  </td>
                  <td className="num">
                    {r.day2}% <span style={{ color: "var(--ink-faint)" }}>(n={r.day2N})</span>
                  </td>
                  <td className="num">
                    {r.day3}% <span style={{ color: "var(--ink-faint)" }}>(n={r.day3N})</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ChalkCard>

      {/* era turn */}
      <ChalkCard
        kicker="Act Seven"
        title="The era turn — the modal QB1 flipped"
        note="Quadrant composition of top-12 seasons. Passing volume did not increase (31.6 → 31.7 att/game); passing got safer and more efficient, and rushing more than doubled (8.96 → 17.7 yds/game, ρ = 0.951 — the strongest trend in the study)."
      >
        <Legend
          items={[
            { label: "2008–2016", color: CHALK.blue },
            { label: "2017–2025", color: CHALK.yellow },
          ]}
        />
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={qb.eraShift} barCategoryGap="22%" barGap={2}>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="quadrant" tick={{ ...axisTick, fontSize: 12 }} axisLine={axisLine} tickLine={false} interval={0} />
            <YAxis tick={axisTick} axisLine={axisLine} tickLine={false} unit="%" domain={[0, 60]} />
            <Tooltip content={<ChalkTooltip format={(v) => pct(v)} />} cursor={{ fill: "rgba(242,238,226,0.06)" }} />
            <Bar dataKey="early" name="2008–2016" fill={CHALK.blue} fillOpacity={0.9} radius={[4, 4, 0, 0]} />
            <Bar dataKey="late" name="2017–2025" fill={CHALK.yellow} fillOpacity={0.9} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </ChalkCard>

      {/* 2026 class */}
      <ChalkCard
        kicker="Application"
        title="The 2026 class against the base rates"
        note="Each rookie shown with the historical hit rates of his pick bucket (2008–2022 classes). Mendoza at pick 1 sits in the single strongest cell in the study; Klubnik's dynasty helium runs ahead of a 5.3% base rate."
      >
        <div className="mb-3 flex flex-wrap gap-2">
          <button className={`chalk-btn ${classSort === "pick" ? "selected" : ""}`} onClick={() => setClassSort("pick")}>
            Sort by pick
          </button>
          <button className={`chalk-btn ${classSort === "everStarted" ? "selected" : ""}`} onClick={() => setClassSort("everStarted")}>
            Sort by P(ever starts)
          </button>
          <button className={`chalk-btn ${classSort === "everTop12" ? "selected" : ""}`} onClick={() => setClassSort("everTop12")}>
            Sort by P(ever QB1)
          </button>
        </div>
        <div className="scroll-x">
          <table className="chalk-table">
            <thead>
              <tr>
                <th>Player</th>
                <th className="num">Pick</th>
                <th>Team</th>
                <th>College</th>
                <th className="num">Bucket</th>
                <th className="num">P(ever starts)</th>
                <th className="num">P(ever QB1)</th>
              </tr>
            </thead>
            <tbody>
              {sortedClass.map((r) => (
                <tr key={r.player}>
                  <td>{r.player}</td>
                  <td className="num">
                    {r.round}.{r.pick}
                  </td>
                  <td>{r.team}</td>
                  <td>{r.college}</td>
                  <td className="num">{r.bucket}</td>
                  <td className="num">{r.everStarted}%</td>
                  <td className="num" style={{ color: r.everTop12 >= 40 ? CHALK.green : r.everTop12 >= 10 ? CHALK.yellow : CHALK.salmon }}>
                    {r.everTop12}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ChalkCard>

      {/* rules */}
      <ChalkCard kicker="Who to draft" title="The three rules">
        <div className="grid gap-4 lg:grid-cols-3">
          {qb.qbRules.map((r, i) => (
            <div key={r.rule} className="chalk-inset px-4 py-4">
              <div className="font-display text-2xl font-bold" style={{ color: [CHALK.yellow, CHALK.blue, CHALK.salmon][i] }}>
                Rule {i + 1}: {r.rule}
              </div>
              <p className="mt-2 leading-snug" style={{ color: "var(--ink-dim)" }}>
                {r.detail}
              </p>
            </div>
          ))}
        </div>
        <p className="mt-5 leading-relaxed" style={{ color: "var(--ink)" }}>
          {qb.superflexVerdict}
        </p>
      </ChalkCard>
    </div>
  );
}
