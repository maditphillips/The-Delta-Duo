"use client";

import { useMemo, useState } from "react";
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
import * as rb from "@/data/rb";

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

const downKeys = ["first", "second", "thirdShort", "thirdLong", "fourth"] as const;
const downLabels: Record<(typeof downKeys)[number], string> = {
  first: "1st",
  second: "2nd",
  thirdShort: "3rd & short",
  thirdLong: "3rd & long",
  fourth: "4th",
};

type SeasonSortKey = "thirdShare" | "ppg" | "season" | "earlyShare";

export default function RbDashboard() {
  const [gateKey, setGateKey] = useState<keyof typeof rb.gateTables>("thirdAll");
  const [matrixOutcome, setMatrixOutcome] = useState<"rb1" | "top24">("rb1");
  const [seasonSort, setSeasonSort] = useState<SeasonSortKey>("thirdShare");

  const gate = rb.gateTables[gateKey];

  const seasons = useMemo(() => {
    const rows = [...rb.namedRb1Seasons];
    if (seasonSort === "thirdShare") rows.sort((a, b) => a.thirdShare - b.thirdShare);
    if (seasonSort === "earlyShare") rows.sort((a, b) => b.earlyShare - a.earlyShare);
    if (seasonSort === "ppg") rows.sort((a, b) => b.ppg - a.ppg);
    if (seasonSort === "season") rows.sort((a, b) => b.season - a.season);
    return rows;
  }, [seasonSort]);

  const valueIndexRows = useMemo(
    () =>
      downKeys.map((k) => {
        const row: Record<string, number | string> = { down: downLabels[k] };
        for (const p of rb.valueIndexByPosition) row[p.position] = p[k];
        return row;
      }),
    []
  );

  return (
    <div className="flex flex-col gap-8">
      <div className="grid gap-4 sm:grid-cols-3">
        <StatTile
          value="0.642"
          label="RB value index on third-and-long"
          sublabel="the only position in football below 1.0 — WRs sit at 1.476"
          color={CHALK.salmon}
        />
        <StatTile value="~87%" label="of every tier-to-tier PPG gap is built on 1st and 2nd down" color={CHALK.yellow} />
        <StatTile
          value="2.67"
          label="carries — what one target is worth"
          sublabel="targets pay 2.67× carries (R² = 0.83)"
          color={CHALK.blue}
        />
      </div>

      <ChalkCard
        kicker="The Cliff — Act One"
        title="Cumulative hit rate by draft round"
        note={rb.twoCliffsNote}
      >
        <Legend
          items={[
            { label: "RB3 (top-36)", color: CHALK.gold },
            { label: "RB2 (top-24)", color: CHALK.pink },
            { label: "RB1 (top-12)", color: CHALK.white },
          ]}
        />
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={rb.hitRateByRound} barCategoryGap="18%" barGap={2}>
            <CartesianGrid {...gridProps} />
            <XAxis
              dataKey="round"
              tick={axisTick}
              axisLine={axisLine}
              tickLine={false}
              label={{ value: "draft round", position: "insideBottom", offset: -4, fill: CHALK.inkFaint, fontSize: 13 }}
              height={50}
            />
            <YAxis tick={axisTick} axisLine={axisLine} tickLine={false} unit="%" domain={[0, 100]} />
            <Tooltip content={<ChalkTooltip format={(v) => pct(v)} />} cursor={{ fill: "rgba(242,238,226,0.06)" }} />
            <Bar dataKey="rb3" name="RB3 (top-36)" fill={CHALK.gold} fillOpacity={0.9} radius={[4, 4, 0, 0]} />
            <Bar dataKey="rb2" name="RB2 (top-24)" fill={CHALK.pink} fillOpacity={0.9} radius={[4, 4, 0, 0]} />
            <Bar dataKey="rb1" name="RB1 (top-12)" fill={CHALK.white} fillOpacity={0.9} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </ChalkCard>

      <ChalkCard
        kicker="The Cliff — Act Two"
        title="The equality: once a back gets the ball, the round stops mattering"
        note={rb.perTouchNote + " The median first-rounder logs 1,065 career touches; the median Day 3 back, 74."}
      >
        <div className="scroll-x">
          <table className="chalk-table">
            <thead>
              <tr>
                <th>Among RBs with 50+ carries</th>
                <th className="num">Round 1 (n=31)</th>
                <th className="num">Day 2 (n=84)</th>
                <th className="num">Day 3 (n=140)</th>
              </tr>
            </thead>
            <tbody>
              {rb.perTouchEquality.map((r) => (
                <tr key={r.metric}>
                  <td>{r.metric}</td>
                  <td className="num">{r.round1}</td>
                  <td className="num">{r.day2}</td>
                  <td className="num" style={{ color: r.metric === "Touches per game" ? CHALK.salmon : "var(--ink)" }}>
                    {r.day3}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="scroll-x mt-5">
          <table className="chalk-table">
            <thead>
              <tr>
                <th>Opportunity funnel</th>
                <th className="num">Round 1</th>
                <th className="num">Day 2</th>
                <th className="num">Day 3</th>
              </tr>
            </thead>
            <tbody>
              {rb.opportunityFunnel.map((r) => (
                <tr key={r.milestone}>
                  <td>{r.milestone}</td>
                  <td className="num">{r.round1}%</td>
                  <td className="num">{r.day2}%</td>
                  <td className="num">{r.day3}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ChalkCard>

      <ChalkCard
        kicker="The Cliff — Acts Three & Four"
        title="The one skill gap is receiving — and the one late signal is college receiving"
        note={rb.passPresence.note}
      >
        <div className="scroll-x">
          <table className="chalk-table">
            <thead>
              <tr>
                <th>Among RBs with 20+ targets</th>
                <th className="num">Round 1</th>
                <th className="num">Day 2</th>
                <th className="num">Day 3</th>
                <th className="num">p</th>
              </tr>
            </thead>
            <tbody>
              {rb.receivingGap.map((r) => (
                <tr key={r.metric}>
                  <td>{r.metric}</td>
                  <td className="num">{r.round1}</td>
                  <td className="num">{r.day2}</td>
                  <td className="num">{r.day3}</td>
                  <td className="num">{r.p}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-6">
          <Legend
            items={[
              { label: "College pass-catcher (top ⅓ by college receiving yards)", color: CHALK.yellow },
              { label: "Everyone else", color: CHALK.blue },
            ]}
          />
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={rb.collegeSignal} barCategoryGap="24%" barGap={2}>
              <CartesianGrid {...gridProps} />
              <XAxis dataKey="outcome" tick={{ ...axisTick, fontSize: 12 }} axisLine={axisLine} tickLine={false} interval={0} />
              <YAxis tick={axisTick} axisLine={axisLine} tickLine={false} unit="%" domain={[0, 80]} />
              <Tooltip content={<ChalkTooltip format={(v) => pct(v)} />} cursor={{ fill: "rgba(242,238,226,0.06)" }} />
              <Bar dataKey="passCatcher" name="College pass-catcher" fill={CHALK.yellow} fillOpacity={0.9} radius={[4, 4, 0, 0]} />
              <Bar dataKey="everyoneElse" name="Everyone else" fill={CHALK.blue} fillOpacity={0.9} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
          <p className="mt-1 text-sm leading-snug" style={{ color: "var(--ink-dim)" }}>
            College pass-catchers hit RB1 at 32.4% vs 9.7% — more than triple the rate. Backs who hit top-36 were on the field for 41.1%
            of team pass plays; backs who missed, 9.7%.
          </p>
        </div>
      </ChalkCard>

      <ChalkCard
        kicker="The companion study — Section 1"
        title="What a snap is worth, by down"
        note="All RB snaps 2016–2025, full PPR. Third-and-long has the highest target rate and the lowest touch rate of any down — that combination is the whole story. Third-and-short is statistically indistinguishable from an early down (p = 0.25)."
      >
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={rb.pointsPerSnap} barCategoryGap="24%">
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="bucket" tick={{ ...axisTick, fontSize: 13 }} axisLine={axisLine} tickLine={false} interval={0} />
            <YAxis tick={axisTick} axisLine={axisLine} tickLine={false} domain={[0, 0.4]} />
            <Tooltip
              content={
                <ChalkTooltip
                  format={(v, name) => (name === "Points per snap" ? v.toFixed(3) : pct(v))}
                />
              }
              cursor={{ fill: "rgba(242,238,226,0.06)" }}
            />
            <Bar dataKey="ptsPerSnap" name="Points per snap" fill={CHALK.yellow} fillOpacity={0.9} radius={[4, 4, 0, 0]}>
              <LabelList dataKey="ptsPerSnap" position="top" formatter={(v) => Number(v).toFixed(3)} fill={CHALK.ink} fontSize={14} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <div className="scroll-x mt-4">
          <table className="chalk-table">
            <thead>
              <tr>
                <th>Down</th>
                <th className="num">Snaps</th>
                <th className="num">Touch rate</th>
                <th className="num">Target rate</th>
              </tr>
            </thead>
            <tbody>
              {rb.pointsPerSnap.map((r) => (
                <tr key={r.bucket}>
                  <td>{r.bucket}</td>
                  <td className="num">{r.snaps.toLocaleString()}</td>
                  <td className="num">{r.touchRate}%</td>
                  <td className="num">{r.targetRate}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ChalkCard>

      <ChalkCard
        kicker="Section 5 — the strongest table in the study"
        title="Value index by position and down"
        note="Value index = share of points ÷ share of snaps. Third-and-long is the most valuable down in football for every position except running back, where it is the least valuable. RB is also the only position that beats its fair share on first down."
      >
        <Legend
          items={[
            { label: "QB", color: CHALK.gold },
            { label: "WR", color: CHALK.pink },
            { label: "TE", color: CHALK.white },
            { label: "RB", color: CHALK.blue },
          ]}
        />
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={valueIndexRows} barCategoryGap="20%" barGap={1}>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="down" tick={axisTick} axisLine={axisLine} tickLine={false} />
            <YAxis tick={axisTick} axisLine={axisLine} tickLine={false} domain={[0, 1.8]} />
            <Tooltip content={<ChalkTooltip format={(v) => v.toFixed(3)} />} cursor={{ fill: "rgba(242,238,226,0.06)" }} />
            <Bar dataKey="QB" fill={CHALK.gold} fillOpacity={0.9} radius={[4, 4, 0, 0]} />
            <Bar dataKey="WR" fill={CHALK.pink} fillOpacity={0.9} radius={[4, 4, 0, 0]} />
            <Bar dataKey="TE" fill={CHALK.white} fillOpacity={0.9} radius={[4, 4, 0, 0]} />
            <Bar dataKey="RB" fill={CHALK.blue} fillOpacity={0.9} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </ChalkCard>

      <ChalkCard
        kicker="Section 2"
        title="The gate tables — usage share vs outcome"
        note={gate.note ?? "RB1 = top-12, RB2 = top-24, RB3 = top-36, all cumulative. Pick a down type to see how snap share there translates to fantasy outcomes."}
      >
        <div className="mb-3 flex flex-wrap gap-2">
          {(Object.keys(rb.gateTables) as (keyof typeof rb.gateTables)[]).map((k) => (
            <button key={k} className={`chalk-btn ${gateKey === k ? "selected" : ""}`} onClick={() => setGateKey(k)}>
              {rb.gateTables[k].label}
            </button>
          ))}
        </div>
        <Legend
          items={[
            { label: "RB3 rate (top-36)", color: CHALK.gold },
            { label: "RB2 rate (top-24)", color: CHALK.pink },
            { label: "RB1 rate (top-12)", color: CHALK.white },
          ]}
        />
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={gate.rows} barCategoryGap="20%" barGap={2}>
            <CartesianGrid {...gridProps} />
            <XAxis
              dataKey="share"
              tick={axisTick}
              axisLine={axisLine}
              tickLine={false}
              label={{ value: "share of team snaps in this bucket", position: "insideBottom", offset: -4, fill: CHALK.inkFaint, fontSize: 13 }}
              height={52}
            />
            <YAxis tick={axisTick} axisLine={axisLine} tickLine={false} unit="%" domain={[0, 100]} />
            <Tooltip
              content={
                <ChalkTooltip
                  format={(v, name) => (name === "Median PPG" ? v.toFixed(1) : name === "n" ? `${v}` : pct(v))}
                />
              }
              cursor={{ fill: "rgba(242,238,226,0.06)" }}
            />
            <Bar dataKey="rb3" name="RB3 rate" fill={CHALK.gold} fillOpacity={0.9} radius={[4, 4, 0, 0]} />
            <Bar dataKey="rb2" name="RB2 rate" fill={CHALK.pink} fillOpacity={0.9} radius={[4, 4, 0, 0]} />
            <Bar dataKey="rb1" name="RB1 rate" fill={CHALK.white} fillOpacity={0.9} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
        <div className="scroll-x mt-3">
          <table className="chalk-table">
            <thead>
              <tr>
                <th>Share</th>
                <th className="num">n</th>
                <th className="num">Median PPG</th>
              </tr>
            </thead>
            <tbody>
              {gate.rows.map((r) => (
                <tr key={r.share}>
                  <td>{r.share}</td>
                  <td className="num">{r.n}</td>
                  <td className="num">{r.medianPpg}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ChalkCard>

      <ChalkCard
        kicker="Section 4"
        title="Where each tier's points come from"
        note="Elite seasons are the LEAST third-down dependent, not the most. RB1s draw 13.1% of points from third down; backs who never hit draw 17.9%. Roughly 87% of every tier-to-tier jump is built on first and second down."
      >
        <Legend
          items={[
            { label: "Early downs (1st/2nd)", color: CHALK.yellow },
            { label: "Third & long", color: CHALK.blue },
            { label: "Third & short", color: CHALK.violet },
          ]}
        />
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={rb.tierPpg} barCategoryGap="26%">
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="tier" tick={axisTick} axisLine={axisLine} tickLine={false} />
            <YAxis tick={axisTick} axisLine={axisLine} tickLine={false} label={{ value: "PPG", angle: -90, position: "insideLeft", fill: CHALK.inkFaint }} />
            <Tooltip content={<ChalkTooltip format={(v) => v.toFixed(2)} />} cursor={{ fill: "rgba(242,238,226,0.06)" }} />
            <Bar dataKey="early" name="Early-down PPG" stackId="a" fill={CHALK.yellow} fillOpacity={0.9} stroke="var(--board)" strokeWidth={2} />
            <Bar dataKey="thirdLong" name="3rd & long PPG" stackId="a" fill={CHALK.blue} fillOpacity={0.9} stroke="var(--board)" strokeWidth={2} />
            <Bar dataKey="thirdShort" name="3rd & short PPG" stackId="a" fill={CHALK.violet} fillOpacity={0.9} stroke="var(--board)" strokeWidth={2} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </ChalkCard>

      <ChalkCard
        kicker="Section 6"
        title="Third-and-long is a passing down — almost entirely"
        note="On third-and-long, 78.8% of RB points come through the air, and rushing there has a value index of 0.234 — carries are nearly worthless. When a back IS involved on third down, the touch is worth ~35% more than an early-down touch."
      >
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={rb.airShare} barCategoryGap="24%">
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="down" tick={axisTick} axisLine={axisLine} tickLine={false} />
            <YAxis tick={axisTick} axisLine={axisLine} tickLine={false} unit="%" domain={[0, 100]} />
            <Tooltip content={<ChalkTooltip format={(v) => pct(v)} />} cursor={{ fill: "rgba(242,238,226,0.06)" }} />
            <Bar dataKey="pctReceiving" name="% of RB points from receiving" fill={CHALK.gold} fillOpacity={0.9} radius={[4, 4, 0, 0]}>
              <LabelList dataKey="pctReceiving" position="top" formatter={(v) => `${Number(v).toFixed(0)}%`} fill={CHALK.ink} fontSize={14} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </ChalkCard>

      <ChalkCard
        kicker="Section 8"
        title="Can a back be elite without third-down snaps? Yes."
        note="40.5% of RB1 seasons and 52.5% of top-24 seasons came with the back on the field for under half his team's third downs. Only 9.9% and 24.0% managed that on early downs. Early-down deployment is 3–4.5× more powerful per unit of snap share."
      >
        <Legend
          items={[
            { label: "% of RB1 seasons below threshold — third down", color: CHALK.yellow },
            { label: "same threshold on early downs", color: CHALK.salmon },
          ]}
        />
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={rb.existenceProof} barCategoryGap="24%" barGap={2}>
            <CartesianGrid {...gridProps} />
            <XAxis
              dataKey="threshold"
              tick={axisTick}
              axisLine={axisLine}
              tickLine={false}
              label={{ value: "team snap share threshold", position: "insideBottom", offset: -4, fill: CHALK.inkFaint, fontSize: 13 }}
              height={52}
            />
            <YAxis tick={axisTick} axisLine={axisLine} tickLine={false} unit="%" domain={[0, 60]} />
            <Tooltip content={<ChalkTooltip format={(v) => pct(v)} />} cursor={{ fill: "rgba(242,238,226,0.06)" }} />
            <Bar dataKey="rb1Third" name="Third down" fill={CHALK.yellow} fillOpacity={0.9} radius={[4, 4, 0, 0]} />
            <Bar dataKey="rb1Early" name="Early down" fill={CHALK.salmon} fillOpacity={0.9} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>

        <div className="mt-6">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <span style={{ color: "var(--ink-dim)" }}>Hit-rate matrix:</span>
            <button className={`chalk-btn ${matrixOutcome === "rb1" ? "selected" : ""}`} onClick={() => setMatrixOutcome("rb1")}>
              RB1 (top-12)
            </button>
            <button className={`chalk-btn ${matrixOutcome === "top24" ? "selected" : ""}`} onClick={() => setMatrixOutcome("top24")}>
              Top-24
            </button>
          </div>
          <div className="scroll-x">
            <table className="chalk-table">
              <thead>
                <tr>
                  <th>Early share ↓ / Third share →</th>
                  {rb.hitMatrix.cols.map((c) => (
                    <th key={c} className="num">
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rb.hitMatrix.rows.map((rowLabel, i) => (
                  <tr key={rowLabel}>
                    <td>{rowLabel}</td>
                    {rb.hitMatrix[matrixOutcome][i].map((v, j) => (
                      <td key={j} className="num" title={`n=${rb.hitMatrix.counts[i][j]} · median ${rb.hitMatrix.medianPpg[i][j]} PPG`}>
                        <span style={{ color: v >= 60 ? CHALK.green : v >= 25 ? CHALK.yellow : "var(--ink-dim)" }}>{v.toFixed(1)}%</span>{" "}
                        <span style={{ color: "var(--ink-faint)", fontSize: "0.85em" }}>n={rb.hitMatrix.counts[i][j]}</span>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-sm leading-snug" style={{ color: "var(--ink-dim)" }}>
            Three regimes: with a 65%+ early-down role, third down is irrelevant. In a 50–65% role it genuinely helps (17.9% → 46.3%).
            Below 35%, nothing helps — 576 player-seasons and essentially zero RB1s. Every back with 65%+ early share and under 30% third
            share finished top-24 (17 for 17 — small cell).
          </p>
        </div>
      </ChalkCard>

      <ChalkCard
        kicker="Section 8.7"
        title="The proof by name — RB1 seasons with the lowest third-down share"
        note="Derrick Henry appears six times. 2021 Henry is the single best example in the study: fifth-lowest third-down share among 242 top-24 seasons and the highest PPG of any of them (24.16, listed in the top-24 table)."
      >
        <div className="mb-3 flex flex-wrap gap-2">
          {(
            [
              ["thirdShare", "Sort by 3rd-down share"],
              ["ppg", "Sort by PPG"],
              ["earlyShare", "Sort by early share"],
              ["season", "Sort by season"],
            ] as [SeasonSortKey, string][]
          ).map(([k, label]) => (
            <button key={k} className={`chalk-btn ${seasonSort === k ? "selected" : ""}`} onClick={() => setSeasonSort(k)}>
              {label}
            </button>
          ))}
        </div>
        <div className="scroll-x" style={{ maxHeight: 420, overflowY: "auto" }}>
          <table className="chalk-table">
            <thead>
              <tr>
                <th>Season</th>
                <th>Player</th>
                <th>Team</th>
                <th className="num">Early share</th>
                <th className="num">3rd share</th>
                <th className="num">PPG</th>
              </tr>
            </thead>
            <tbody>
              {seasons.map((r) => (
                <tr key={`${r.season}-${r.player}`}>
                  <td>{r.season}</td>
                  <td>{r.player}</td>
                  <td>{r.team}</td>
                  <td className="num">{(r.earlyShare * 100).toFixed(1)}%</td>
                  <td className="num" style={{ color: r.thirdShare < 0.2 ? CHALK.yellow : "var(--ink)" }}>
                    {(r.thirdShare * 100).toFixed(1)}%
                  </td>
                  <td className="num">{r.ppg.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ChalkCard>

      <ChalkCard
        kicker="Section 9"
        title="Role archetypes — and why the third-down specialist is a dead end"
        note="Zero of 66 third-down-specialist seasons finished as an RB1. Zero of 42 became three-down backs the following season. Third-down work predicts slightly LESS early-down work next year (−0.085, p = 0.01)."
      >
        <div className="scroll-x">
          <table className="chalk-table">
            <thead>
              <tr>
                <th>Role</th>
                <th className="num">n</th>
                <th className="num">Median PPG</th>
                <th className="num">RB3</th>
                <th className="num">RB2</th>
                <th className="num">RB1</th>
                <th className="num">Promoted to 3-down next yr</th>
              </tr>
            </thead>
            <tbody>
              {rb.archetypes.map((r) => {
                const promo = rb.promotion.find((p) => p.role === r.role);
                return (
                  <tr key={r.role}>
                    <td>{r.role}</td>
                    <td className="num">{r.n}</td>
                    <td className="num">{r.medianPpg}</td>
                    <td className="num">{r.rb3}%</td>
                    <td className="num">{r.rb2}%</td>
                    <td className="num" style={{ color: r.rb1 === 0 ? CHALK.salmon : "var(--ink)" }}>
                      {r.rb1}%
                    </td>
                    <td className="num" style={{ color: promo && promo.becameThreeDown === 0 ? CHALK.salmon : "var(--ink)" }}>
                      {promo ? `${promo.becameThreeDown}%` : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <h3 className="mt-6 text-xl" style={{ color: "var(--ink)" }}>
          True third-down specialists, 2025
        </h3>
        <div className="scroll-x mt-2">
          <table className="chalk-table">
            <thead>
              <tr>
                <th>Player</th>
                <th>Team</th>
                <th className="num">Early share</th>
                <th className="num">3rd share</th>
                <th className="num">PPG</th>
              </tr>
            </thead>
            <tbody>
              {rb.specialists2025.map((r) => (
                <tr key={r.player}>
                  <td>{r.player}</td>
                  <td>{r.team}</td>
                  <td className="num">{(r.earlyShare * 100).toFixed(1)}%</td>
                  <td className="num">{(r.thirdShare * 100).toFixed(1)}%</td>
                  <td className="num">{r.ppg}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ChalkCard>

      <ChalkCard kicker="Section 10" title="The claims, in one place">
        <ul className="flex list-none flex-col gap-3">
          {rb.rbClaims.map((c, i) => (
            <li key={i} className="flex gap-3 leading-snug">
              <span className="font-display text-2xl font-bold" style={{ color: CHALK.yellow, minWidth: "2rem" }}>
                {i + 1}.
              </span>
              <span style={{ color: "var(--ink-dim)" }}>{c}</span>
            </li>
          ))}
        </ul>
        <p className="chalk-inset mt-6 px-5 py-4 text-lg leading-relaxed" style={{ color: "var(--ink)" }}>
          {rb.rbSummaryLine}
        </p>
      </ChalkCard>
    </div>
  );
}
