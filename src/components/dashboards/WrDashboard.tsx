"use client";

import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import ChalkCard from "@/components/ChalkCard";
import ChalkTooltip from "@/components/charts/ChalkTooltip";
import { CHALK, axisLine, axisTick, gridProps } from "@/components/charts/theme";
import * as wr from "@/data/wr";

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

type FunnelOutcome = "everStartable" | "everWr1";
const funnelLabels: Record<FunnelOutcome, string> = {
  everStartable: "Ever startable (top-36)",
  everWr1: "Ever WR1 (top-12)",
};

export default function WrDashboard() {
  const [funnelOutcome, setFunnelOutcome] = useState<FunnelOutcome | "both">("both");

  return (
    <div className="flex flex-col gap-8">
      {/* the two doors */}
      <div className="grid gap-4 lg:grid-cols-2">
        {wr.twoDoors.map((d, i) => (
          <ChalkCard key={d.door} kicker={d.gate} title={d.door} alt>
            <div className="font-display text-5xl font-bold" style={{ color: i === 0 ? CHALK.salmon : CHALK.green }}>
              {d.stat}
            </div>
            <p className="mt-3 leading-snug" style={{ color: "var(--ink-dim)" }}>
              {d.detail}
            </p>
          </ChalkCard>
        ))}
      </div>

      {/* Act One — the funnel */}
      <ChalkCard
        kicker="Act One"
        title="What each draft day buys"
        note="2008–2022 classes, PPR. The Day 2 vs Day 3 startable gap carries p = 4.7e-12 — as certain as statistics gets. And the median-career-targets column previews the whole article: 520 for Round 1, 29 for Day 3. The draft's product is volume."
      >
        <div className="mb-3 flex flex-wrap gap-2">
          <button className={`chalk-btn ${funnelOutcome === "both" ? "selected" : ""}`} onClick={() => setFunnelOutcome("both")}>
            Both tiers
          </button>
          {(Object.keys(funnelLabels) as FunnelOutcome[]).map((o) => (
            <button key={o} className={`chalk-btn ${funnelOutcome === o ? "selected" : ""}`} onClick={() => setFunnelOutcome(o)}>
              {funnelLabels[o]}
            </button>
          ))}
        </div>
        <Legend
          items={[
            ...(funnelOutcome !== "everWr1" ? [{ label: "Ever startable (top-36)", color: CHALK.blue }] : []),
            ...(funnelOutcome !== "everStartable" ? [{ label: "Ever WR1 (top-12)", color: CHALK.salmon }] : []),
          ]}
        />
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={wr.funnel} barCategoryGap="28%" barGap={2}>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="day" tick={axisTick} axisLine={axisLine} tickLine={false} />
            <YAxis tick={axisTick} axisLine={axisLine} tickLine={false} unit="%" domain={[0, 100]} />
            <Tooltip content={<ChalkTooltip format={(v) => pct(v)} />} cursor={{ fill: "rgba(242,238,226,0.06)" }} />
            {funnelOutcome !== "everWr1" && (
              <Bar dataKey="everStartable" name="Ever startable" fill={CHALK.blue} fillOpacity={0.9} radius={[4, 4, 0, 0]}>
                <LabelList dataKey="everStartable" position="top" formatter={(v) => `${v}%`} fill={CHALK.ink} fontSize={14} />
              </Bar>
            )}
            {funnelOutcome !== "everStartable" && (
              <Bar dataKey="everWr1" name="Ever WR1" fill={CHALK.salmon} fillOpacity={0.9} radius={[4, 4, 0, 0]}>
                <LabelList dataKey="everWr1" position="top" formatter={(v) => `${v}%`} fill={CHALK.ink} fontSize={14} />
              </Bar>
            )}
          </BarChart>
        </ResponsiveContainer>
        <div className="scroll-x mt-4">
          <table className="chalk-table">
            <thead>
              <tr>
                <th>Draft day</th>
                <th className="num">n</th>
                <th className="num">Median career targets</th>
              </tr>
            </thead>
            <tbody>
              {wr.funnel.map((r) => (
                <tr key={r.day}>
                  <td>{r.day}</td>
                  <td className="num">{r.n}</td>
                  <td className="num">{r.medianCareerTargets}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ChalkCard>

      {/* ramp + inside round 1 */}
      <div className="grid gap-4 lg:grid-cols-2">
        <ChalkCard kicker="Cliff or ramp?" title="A ramp, not a staircase" alt>
          <p className="leading-snug" style={{ color: "var(--ink-dim)" }}>
            {wr.rampNotCliff.note}
          </p>
          <div className="mt-4 flex flex-wrap gap-6">
            <div>
              <div className="font-display text-4xl font-bold" style={{ color: CHALK.yellow }}>
                {wr.rampNotCliff.day3FloorSplit.rounds45}% vs {wr.rampNotCliff.day3FloorSplit.rounds67}%
              </div>
              <div className="text-sm" style={{ color: "var(--ink-dim)" }}>
                startable rate, rounds 4-5 vs 6-7 (p = {wr.rampNotCliff.day3FloorSplit.p}). Early Day 3 buys a floor — the top-12 rate is
                flat across all of Day 3 (p = {wr.rampNotCliff.day3FloorSplit.top12FlatP}).
              </div>
            </div>
          </div>
        </ChalkCard>
        <ChalkCard kicker="Inside Round 1" title="Capital buys safety, not stardom" alt>
          <div className="flex flex-wrap gap-6">
            <div>
              <div className="font-display text-4xl font-bold" style={{ color: CHALK.green }}>
                {wr.insideRound1.floorEarly}% vs {wr.insideRound1.floorLate}%
              </div>
              <div className="text-sm" style={{ color: "var(--ink-dim)" }}>
                startable rate, top-10 picks vs picks 11-32 — {wr.insideRound1.floorVerdict}
              </div>
            </div>
            <div>
              <div className="font-display text-4xl font-bold" style={{ color: CHALK.salmon }}>
                OR {wr.insideRound1.ceilingOR}
              </div>
              <div className="text-sm" style={{ color: "var(--ink-dim)" }}>
                p = {wr.insideRound1.ceilingP} — {wr.insideRound1.ceilingVerdict} ({wr.insideRound1.ceilingEarlyRate}% vs{" "}
                {wr.insideRound1.ceilingLateRate}%)
              </div>
            </div>
          </div>
          <p className="mt-3 text-sm leading-snug" style={{ color: "var(--ink-dim)" }}>
            {wr.insideRound1.contrast}
          </p>
        </ChalkCard>
      </div>

      {/* Act Two — equality */}
      <ChalkCard
        kicker="Act Two"
        title="Everyone who gets the ball plays the same"
        note={`${wr.equalityHeadline.survivors}. Round 1 produces ${wr.equalityHeadline.round1PprPerTarget} PPR points per target; Round 7 produces ${wr.equalityHeadline.round7PprPerTarget} — three thousandths of a point. ${wr.equalityHeadline.volumeShareOfGap}% of the fantasy gap between draft days is volume: 6.8 targets per game for Round 1 vs 4.6 for Day 3.`}
      >
        <div className="scroll-x">
          <table className="chalk-table">
            <thead>
              <tr>
                <th>Draft day (150+ career targets)</th>
                <th className="num">n</th>
                <th className="num">Yards/target</th>
                <th className="num">Catch %</th>
                <th className="num">YAC/reception</th>
                <th className="num">PPR per target</th>
              </tr>
            </thead>
            <tbody>
              {wr.equalityMetrics.map((r) => (
                <tr key={r.day}>
                  <td>{r.day}</td>
                  <td className="num">{r.n}</td>
                  <td className="num">{r.yardsPerTarget}</td>
                  <td className="num">{r.catchPct}%</td>
                  <td className="num">{r.yacPerRec}</td>
                  <td className="num">{r.pprPerTarget}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-6">
          <h3 className="mb-2 text-xl" style={{ color: "var(--ink)" }}>
            …but the usage is not the same
          </h3>
          <Legend items={[{ label: "% of full games played with zero targets, zero catches, zero points", color: CHALK.salmon }]} />
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={wr.zeroTargetGames} barCategoryGap="35%">
              <CartesianGrid {...gridProps} />
              <XAxis dataKey="day" tick={axisTick} axisLine={axisLine} tickLine={false} />
              <YAxis tick={axisTick} axisLine={axisLine} tickLine={false} unit="%" domain={[0, 20]} />
              <Tooltip content={<ChalkTooltip format={(v) => pct(v)} />} cursor={{ fill: "rgba(242,238,226,0.06)" }} />
              <Bar dataKey="pct" name="Zero-usage games" fill={CHALK.salmon} fillOpacity={0.9} radius={[4, 4, 0, 0]}>
                <LabelList dataKey="pct" position="top" formatter={(v) => `${v}%`} fill={CHALK.ink} fontSize={14} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <p className="mt-1 text-sm" style={{ color: "var(--ink-dim)" }}>
            A Day 3 receiver is 11 times more likely than a Round 1 receiver to play a full game and score nothing at all.
          </p>
        </div>
      </ChalkCard>

      {/* Act Three — the snap gate */}
      <ChalkCard
        kicker="Act Three"
        title="The snap gate"
        note={`No receiver under 25% of team pass snaps has ever reached 80 targets — zero of 484 seasons. Above 85%, it's nearly automatic. And the residual: ${wr.residual.note}`}
      >
        <Legend items={[{ label: "Reached an 80-target season", color: CHALK.yellow }]} />
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={wr.snapGate} barCategoryGap="20%">
            <CartesianGrid {...gridProps} />
            <XAxis
              dataKey="share"
              tick={axisTick}
              axisLine={axisLine}
              tickLine={false}
              label={{ value: "share of team pass snaps", position: "insideBottom", offset: -4, fill: CHALK.inkFaint, fontSize: 13 }}
              height={52}
            />
            <YAxis tick={axisTick} axisLine={axisLine} tickLine={false} unit="%" domain={[0, 100]} />
            <Tooltip
              content={<ChalkTooltip format={(v, name) => (name === "Median targets" || name === "n" ? `${v}` : pct(v))} />}
              cursor={{ fill: "rgba(242,238,226,0.06)" }}
            />
            <Bar dataKey="reached80" name="Reached 80 targets" fill={CHALK.yellow} fillOpacity={0.9} radius={[4, 4, 0, 0]}>
              <LabelList dataKey="reached80" position="top" formatter={(v) => `${v}%`} fill={CHALK.ink} fontSize={14} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <div className="scroll-x mt-3">
          <table className="chalk-table">
            <thead>
              <tr>
                <th>Snap share</th>
                <th className="num">n</th>
                <th className="num">Median targets</th>
              </tr>
            </thead>
            <tbody>
              {wr.snapGate.map((r) => (
                <tr key={r.share}>
                  <td>{r.share}</td>
                  <td className="num">{r.n}</td>
                  <td className="num">{r.medianTargets}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ChalkCard>

      {/* the ladder */}
      <ChalkCard
        kicker="The ladder"
        title="Depth-chart role vs fantasy finish"
        note={wr.alphaConversion.note + " Round 1 alphas became WR1s at 86.4%, Day 3 alphas at 77.8% (p = 0.61)."}
      >
        <Legend
          items={[
            { label: "Ever startable (top-36)", color: CHALK.blue },
            { label: "Ever WR1 (top-12)", color: CHALK.salmon },
          ]}
        />
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={wr.ladder} barCategoryGap="24%" barGap={2}>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="role" tick={{ ...axisTick, fontSize: 12 }} axisLine={axisLine} tickLine={false} interval={0} />
            <YAxis tick={axisTick} axisLine={axisLine} tickLine={false} unit="%" domain={[0, 100]} />
            <Tooltip content={<ChalkTooltip format={(v) => pct(v)} />} cursor={{ fill: "rgba(242,238,226,0.06)" }} />
            <Bar dataKey="everStartable" name="Ever startable" fill={CHALK.blue} fillOpacity={0.9} radius={[4, 4, 0, 0]} />
            <Bar dataKey="everWr1" name="Ever WR1" fill={CHALK.salmon} fillOpacity={0.9} radius={[4, 4, 0, 0]}>
              <LabelList dataKey="everWr1" position="top" formatter={(v) => `${v}%`} fill={CHALK.ink} fontSize={14} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <p className="mt-2 text-sm leading-snug" style={{ color: "var(--ink-dim)" }}>
          Read the bottom rung carefully: of the 63 receivers who peaked in the 80–109 target band — a real NFL job — the 58 drafted
          outside Round 1 produced zero fantasy WR1 seasons. It takes a 110+ target workload to reliably produce even a WR3 season.
        </p>
      </ChalkCard>

      {/* Act Four — pre-draft board */}
      <ChalkCard
        kicker="Act Four"
        title="What the scouts can't sell you"
        note="~220 tests with draft position controlled. College production is real but priced in: by draft night the market has already paid for the college tape, and a big dominator rating buys nothing extra within a round, in any round (interaction p = 0.30–0.81). Two things survive — and neither measures ability."
      >
        <div className="scroll-x">
          <table className="chalk-table">
            <thead>
              <tr>
                <th>Signal family</th>
                <th>Survives pick control?</th>
                <th>Detail</th>
              </tr>
            </thead>
            <tbody>
              {wr.preDraftBoard.map((r) => (
                <tr key={r.family}>
                  <td style={{ color: r.survives ? CHALK.green : "var(--ink)" }}>{r.family}</td>
                  <td style={{ color: r.survives ? CHALK.green : CHALK.salmon }}>{r.survives ? "survives" : "dies"}</td>
                  <td style={{ color: "var(--ink-dim)" }}>{r.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ChalkCard>

      {/* age */}
      <ChalkCard
        kicker="The one scouting-adjacent signal that lives"
        title="Draft age — but only on Day 3"
        note="Within Day 3, age and pick are uncorrelated (r = 0.038), so age is not a proxy for slot. The 24-plus cell is 0-for-22 all time. The sweet spot — early half of Day 3, age 22 or under — hits startable at 20.5%: Day 2 odds at a Day 3 price."
      >
        <Legend
          items={[
            { label: "Ever startable", color: CHALK.yellow },
            { label: "Ever reached 150 career targets", color: CHALK.blue },
          ]}
        />
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={wr.day3Age} barCategoryGap="24%" barGap={2}>
            <CartesianGrid {...gridProps} />
            <XAxis
              dataKey="age"
              tick={axisTick}
              axisLine={axisLine}
              tickLine={false}
              label={{ value: "draft age (Day 3 picks only)", position: "insideBottom", offset: -4, fill: CHALK.inkFaint, fontSize: 13 }}
              height={52}
            />
            <YAxis tick={axisTick} axisLine={axisLine} tickLine={false} unit="%" domain={[0, 45]} />
            <Tooltip content={<ChalkTooltip format={(v) => pct(v)} />} cursor={{ fill: "rgba(242,238,226,0.06)" }} />
            <Bar dataKey="everStartable" name="Ever startable" fill={CHALK.yellow} fillOpacity={0.9} radius={[4, 4, 0, 0]} />
            <Bar dataKey="reached150" name="Reached 150 targets" fill={CHALK.blue} fillOpacity={0.9} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
        <div className="scroll-x mt-4">
          <table className="chalk-table">
            <thead>
              <tr>
                <th>Day 3 cell</th>
                <th className="num">n</th>
                <th className="num">Earned a real role</th>
                <th className="num">Ever startable</th>
              </tr>
            </thead>
            <tbody>
              {wr.day3SweetSpot.map((r) => (
                <tr key={r.bucket}>
                  <td style={{ color: r.sweetSpot ? CHALK.green : "var(--ink)" }}>
                    {r.bucket}
                    {r.sweetSpot ? " ★" : ""}
                  </td>
                  <td className="num">{r.n}</td>
                  <td className="num">{r.realRole}%</td>
                  <td className="num">{r.everStartable}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ChalkCard>

      {/* Act Five — timeline */}
      <ChalkCard
        kicker="Act Five"
        title="The timeline — when the hits arrive"
        note={`55.8% of Round 1 receivers clear the 80-target gate as rookies — the most redraft-relevant number in the study. ${wr.timeline.day2Window} Day 3 rookies essentially do not hit (1.6% top-36). No startable season by end of year two → the odds he ever gets one: 21.4% (R1), 13.3% (D2), 3.2% (D3).`}
      >
        <Legend
          items={[
            { label: "80+ targets as a rookie", color: CHALK.yellow },
            { label: "Top-36 as a rookie", color: CHALK.blue },
            { label: "Top-12 as a rookie", color: CHALK.salmon },
          ]}
        />
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={wr.rookieRates} barCategoryGap="24%" barGap={2}>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="day" tick={axisTick} axisLine={axisLine} tickLine={false} />
            <YAxis tick={axisTick} axisLine={axisLine} tickLine={false} unit="%" domain={[0, 60]} />
            <Tooltip content={<ChalkTooltip format={(v) => pct(v)} />} cursor={{ fill: "rgba(242,238,226,0.06)" }} />
            <Bar dataKey="targets80" name="80+ targets" fill={CHALK.yellow} fillOpacity={0.9} radius={[4, 4, 0, 0]} />
            <Bar dataKey="top36" name="Top-36" fill={CHALK.blue} fillOpacity={0.9} radius={[4, 4, 0, 0]} />
            <Bar dataKey="top12" name="Top-12" fill={CHALK.salmon} fillOpacity={0.9} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </ChalkCard>

      {/* Act Six — how roles change hands */}
      <ChalkCard
        kicker="Act Six"
        title="Roles change hands through departures, not skill"
        note={`${wr.acquisitionRule.declineNote} ${wr.acquisitionRule.compounding} And the QB version points the other way: ${wr.acquisitionRule.qbRule.note}`}
      >
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="chalk-card-alt px-4 py-4">
            <div className="font-display text-4xl font-bold" style={{ color: CHALK.yellow }}>
              12.5% vs 4.9%
            </div>
            <div className="mt-1 text-sm" style={{ color: "var(--ink-dim)" }}>
              first-feed rate when the team&apos;s leading WR departed vs stayed (OR 2.79, p = 0.0011, n = 805 at-risk seasons)
            </div>
          </div>
          <div className="chalk-card-alt px-4 py-4">
            <div className="font-display text-4xl font-bold" style={{ color: CHALK.salmon }}>
              49% → 26%
            </div>
            <div className="mt-1 text-sm" style={{ color: "var(--ink-dim)" }}>
              odds of keeping an established role when the quarterback departs (OR 0.43, p = 0.026)
            </div>
          </div>
          <div className="chalk-card-alt px-4 py-4">
            <div className="font-display text-4xl font-bold" style={{ color: CHALK.blue }}>
              16.1% vs 2.0%
            </div>
            <div className="mt-1 text-sm" style={{ color: "var(--ink-dim)" }}>
              first-feed rate: vacancy + age ≤22, vs no vacancy + age 23+. The signals compound.
            </div>
          </div>
        </div>

        <h3 className="mb-2 mt-6 text-xl" style={{ color: "var(--ink)" }}>
          When the receiver is the one who moves
        </h3>
        <Legend
          items={[
            { label: "Stayed — kept an 80-target role", color: CHALK.blue },
            { label: "Moved teams", color: CHALK.salmon },
          ]}
        />
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={wr.movers} barCategoryGap="26%" barGap={2}>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="band" tick={{ ...axisTick, fontSize: 12 }} axisLine={axisLine} tickLine={false} interval={0} />
            <YAxis tick={axisTick} axisLine={axisLine} tickLine={false} unit="%" domain={[0, 100]} />
            <Tooltip content={<ChalkTooltip format={(v) => pct(v)} />} cursor={{ fill: "rgba(242,238,226,0.06)" }} />
            <Bar dataKey="stayed" name="Stayed" fill={CHALK.blue} fillOpacity={0.9} radius={[4, 4, 0, 0]} />
            <Bar dataKey="moved" name="Moved" fill={CHALK.salmon} fillOpacity={0.9} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
        <p className="mt-2 text-sm leading-snug" style={{ color: "var(--ink-dim)" }}>
          {wr.moversNote}
        </p>
      </ChalkCard>

      {/* Act Seven — era turn */}
      <ChalkCard
        kicker="Act Seven"
        title="The era turn — the middle class collapsed; the lottery ticket didn't"
        note={`Day 3 receivers drafted 2008–2012 became startable at ${wr.eraDetail.day3StartableEarly}%; those drafted 2013–2019 at ${wr.eraDetail.day3StartableLate}% (trend p = ${wr.eraDetail.trendP}, ~${wr.eraDetail.declinePerYear}% decline per draft year). The median Day 3 success story used to peak at ${wr.eraDetail.medianPeakTargetsThen} targets; now ${wr.eraDetail.medianPeakTargetsNow}. ${wr.eraDetail.note}`}
      >
        <Legend
          items={[
            { label: "Late-round share, first 5 years", color: CHALK.blue },
            { label: "Late-round share, last 5 years", color: CHALK.yellow },
          ]}
        />
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={wr.eraTurn} barCategoryGap="28%" barGap={2}>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="tier" tick={axisTick} axisLine={axisLine} tickLine={false} />
            <YAxis tick={axisTick} axisLine={axisLine} tickLine={false} unit="%" domain={[0, 40]} />
            <Tooltip content={<ChalkTooltip format={(v) => pct(v)} />} cursor={{ fill: "rgba(242,238,226,0.06)" }} />
            <Bar dataKey="early" name="First 5 years" fill={CHALK.blue} fillOpacity={0.9} radius={[4, 4, 0, 0]} />
            <Bar dataKey="late" name="Last 5 years" fill={CHALK.yellow} fillOpacity={0.9} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
        <div className="mt-2 flex flex-col gap-1 text-sm" style={{ color: "var(--ink-dim)" }}>
          {wr.eraTurn.map((t) => (
            <div key={t.tier}>
              <strong style={{ color: "var(--ink)" }}>{t.tier}:</strong> {t.verdict} (p = {t.p})
            </div>
          ))}
        </div>
      </ChalkCard>

      {/* who to draft */}
      <ChalkCard kicker="Who to draft" title="The archetypes">
        <div className="grid gap-4 lg:grid-cols-2">
          {wr.archetypes.map((a, i) => (
            <div key={a.name} className="chalk-card-alt px-4 py-4">
              <div className="font-display text-2xl font-bold" style={{ color: [CHALK.green, CHALK.blue, CHALK.yellow, CHALK.salmon][i] }}>
                {a.name}
              </div>
              <p className="mt-2 leading-snug" style={{ color: "var(--ink-dim)" }}>
                {a.detail}
              </p>
            </div>
          ))}
        </div>
      </ChalkCard>

      <ChalkCard
        kicker="2026 application"
        title="The Round 1 class and the Nacua-cell darts"
        note="The base rates say roughly 2–3 of the five Round 1 rookies will be startable this season, and the majority will clear 80 targets as rookies. Every 2026 Round 4 receiver is 23 or older — the sweet-spot cell is empty in the fourth round this year, so the real darts are in Round 5."
      >
        <div className="scroll-x">
          <table className="chalk-table">
            <thead>
              <tr>
                <th>Round 1 rookie</th>
                <th className="num">Pick</th>
                <th>Team</th>
                <th className="num">Age</th>
                <th>Read</th>
              </tr>
            </thead>
            <tbody>
              {wr.class2026.map((r) => (
                <tr key={r.player}>
                  <td>{r.player}</td>
                  <td className="num">{r.pick}</td>
                  <td>{r.team}</td>
                  <td className="num">{r.age}</td>
                  <td style={{ color: "var(--ink-dim)" }}>{r.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <h3 className="mb-2 mt-6 text-xl" style={{ color: "var(--ink)" }}>
          The darts
        </h3>
        <div className="grid gap-3 lg:grid-cols-3">
          {wr.darts2026.map((d) => (
            <div key={d.player} className="chalk-card-alt px-4 py-4">
              <div className="font-display text-2xl font-bold" style={{ color: CHALK.yellow }}>
                {d.player}
              </div>
              <div className="text-sm" style={{ color: "var(--ink-faint)" }}>
                {d.pick} · {d.team} · age {d.age}
              </div>
              <p className="mt-2 text-sm leading-snug" style={{ color: "var(--ink-dim)" }}>
                {d.mechanism}
              </p>
            </div>
          ))}
        </div>
        <p className="chalk-card-alt mt-6 px-5 py-4 text-lg leading-relaxed" style={{ color: "var(--ink)" }}>
          {wr.wrVerdict}
        </p>
      </ChalkCard>
    </div>
  );
}
