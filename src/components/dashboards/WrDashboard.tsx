"use client";

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
import StatTile from "@/components/StatTile";
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

export default function WrDashboard() {
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

      <ChalkCard
        kicker="The headline"
        title="Draft capital opens doors — it doesn't run routes"
        note="Round 1 receivers reach the startable tier (top-36) at 70.2% and the elite tier (top-12) at 45.6%; Day 3 receivers at 9.3% and 3.2%. But per-opportunity quality is flat: 0 of 15 metrics separate Round 1 from Day 3 once receivers clear the audition bar."
      >
        <Legend
          items={[
            { label: "Startable (ever top-36)", color: CHALK.blue },
            { label: "Elite (ever top-12)", color: CHALK.salmon },
          ]}
        />
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={wr.roundOutcomes} barCategoryGap="30%" barGap={2}>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="day" tick={axisTick} axisLine={axisLine} tickLine={false} />
            <YAxis tick={axisTick} axisLine={axisLine} tickLine={false} unit="%" domain={[0, 100]} />
            <Tooltip content={<ChalkTooltip format={(v) => pct(v)} />} cursor={{ fill: "rgba(242,238,226,0.06)" }} />
            <Bar dataKey="startable" name="Startable (top-36)" fill={CHALK.blue} fillOpacity={0.9} radius={[4, 4, 0, 0]}>
              <LabelList dataKey="startable" position="top" formatter={(v) => `${v}%`} fill={CHALK.ink} fontSize={14} />
            </Bar>
            <Bar dataKey="elite" name="Elite (top-12)" fill={CHALK.salmon} fillOpacity={0.9} radius={[4, 4, 0, 0]}>
              <LabelList dataKey="elite" position="top" formatter={(v) => `${v}%`} fill={CHALK.ink} fontSize={14} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </ChalkCard>

      <div className="grid gap-4 sm:grid-cols-3">
        <StatTile
          value="86.4% vs 77.8%"
          label="WR1 conversion once alpha volume is earned, R1 vs late"
          sublabel="p = 0.61 — volume converts at the same rate for everyone"
          color={CHALK.blue}
        />
        <StatTile
          value="15.7% vs 3.9%"
          label="startable rate, rounds 4-5 vs 6-7"
          sublabel="early Day 3 buys a real floor (p = 0.0008) — the Nacua cell"
          color={CHALK.yellow}
        />
        <StatTile
          value="1.476"
          label="WR value index on third-and-long"
          sublabel="the most valuable down in football for a receiver"
          color={CHALK.violet}
        />
      </div>

      <ChalkCard
        kicker="Inside Round 1"
        title="Capital buys safety, not stardom"
        note={wr.insideRound1.contrast}
      >
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="chalk-card-alt px-4 py-4">
            <div className="text-lg" style={{ color: "var(--ink)" }}>
              The floor — ever startable
            </div>
            <div className="font-display mt-1 text-4xl font-bold" style={{ color: CHALK.green }}>
              {wr.insideRound1.floorEarly}% vs {wr.insideRound1.floorLate}%
            </div>
            <div className="mt-1 text-sm" style={{ color: "var(--ink-dim)" }}>
              early first-rounders vs late first-rounders — {wr.insideRound1.floorVerdict}
            </div>
          </div>
          <div className="chalk-card-alt px-4 py-4">
            <div className="text-lg" style={{ color: "var(--ink)" }}>
              The ceiling — elite conversion
            </div>
            <div className="font-display mt-1 text-4xl font-bold" style={{ color: CHALK.salmon }}>
              OR {wr.insideRound1.ceilingOR}
            </div>
            <div className="mt-1 text-sm" style={{ color: "var(--ink-dim)" }}>
              p = {wr.insideRound1.ceilingP} — {wr.insideRound1.ceilingVerdict}
            </div>
          </div>
        </div>
      </ChalkCard>

      <ChalkCard
        kicker="Roles & moves"
        title="The role travels for alphas — and only for alphas"
      >
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="chalk-card-alt px-4 py-4">
            <div className="font-display text-4xl font-bold" style={{ color: CHALK.yellow }}>
              58.7% → 32.4%
            </div>
            <p className="mt-2 text-sm leading-snug" style={{ color: "var(--ink-dim)" }}>
              {wr.movers.note}
            </p>
          </div>
          <div className="chalk-card-alt px-4 py-4">
            <div className="font-display text-4xl font-bold" style={{ color: CHALK.blue }}>
              OR 2.79
            </div>
            <p className="mt-2 text-sm leading-snug" style={{ color: "var(--ink-dim)" }}>
              {wr.vacancy.note}
            </p>
          </div>
        </div>
      </ChalkCard>

      <ChalkCard
        kicker="The era turn"
        title="The middle class collapsed; the lottery ticket didn't"
      >
        <Legend
          items={[
            { label: "First nine years", color: CHALK.blue },
            { label: "Last nine years", color: CHALK.yellow },
          ]}
        />
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={wr.eraTrends} barCategoryGap="30%" barGap={2}>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="finding" tick={{ ...axisTick, fontSize: 13 }} axisLine={axisLine} tickLine={false} interval={0} />
            <YAxis tick={axisTick} axisLine={axisLine} tickLine={false} unit="%" domain={[0, 40]} />
            <Tooltip content={<ChalkTooltip format={(v) => pct(v)} />} cursor={{ fill: "rgba(242,238,226,0.06)" }} />
            <Bar dataKey="early" name="First nine years" fill={CHALK.blue} fillOpacity={0.9} radius={[4, 4, 0, 0]} />
            <Bar dataKey="late" name="Last nine years" fill={CHALK.yellow} fillOpacity={0.9} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
        <div className="mt-3 flex flex-col gap-1 text-sm" style={{ color: "var(--ink-dim)" }}>
          {wr.eraTrends.map((t) => (
            <div key={t.finding}>
              <strong style={{ color: "var(--ink)" }}>{t.finding}:</strong> {t.verdict}
            </div>
          ))}
        </div>
      </ChalkCard>

      <ChalkCard kicker="Series findings" title="What the WR study established">
        <div className="scroll-x">
          <table className="chalk-table">
            <thead>
              <tr>
                <th>Finding</th>
                <th>Answer</th>
              </tr>
            </thead>
            <tbody>
              {wr.wrSeriesFindings.map((r) => (
                <tr key={r.finding}>
                  <td style={{ whiteSpace: "nowrap" }}>{r.finding}</td>
                  <td style={{ color: "var(--ink-dim)" }}>{r.answer}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ChalkCard>

      <div className="chalk-card-alt px-5 py-4 text-sm leading-snug" style={{ color: "var(--ink-dim)" }}>
        ✏️ {wr.wrMeta.pendingNote}
      </div>
    </div>
  );
}
