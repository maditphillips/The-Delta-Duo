import Link from "next/link";
import ChalkCard from "@/components/ChalkCard";
import { anchorClaim, crossStudy } from "@/data/crossStudy";
import { CHALK } from "@/components/charts/theme";

const positions = [
  {
    href: "/wide-receiver",
    label: "Wide Receiver",
    title: "The Two Doors of Fantasy Relevance",
    blurb: "Getting on the field, and getting the ball. What every drafted WR since 2008 reveals about both gates.",
    color: CHALK.blue,
  },
  {
    href: "/quarterback",
    label: "Quarterback",
    title: "The Quarterback Cliff",
    blurb: "The draft decides who plays. It does not decide who is good. 212 drafted QBs, 2008–2025.",
    color: CHALK.yellow,
  },
  {
    href: "/running-back",
    label: "Running Back",
    title: "The Running Back Cliff",
    blurb: "What 388 drafted RBs — and every down they played — reveal about talent, volume, and third down.",
    color: CHALK.salmon,
  },
];

export default function Home() {
  return (
    <div className="flex flex-col gap-10">
      <div className="pt-6 text-center">
        <h1 className="font-display mx-auto max-w-3xl text-5xl font-bold leading-tight sm:text-6xl" style={{ color: "var(--ink)" }}>
          The draft decides who plays.
          <br />
          <span style={{ color: CHALK.yellow }}>It does not decide who is good.</span>
        </h1>
        <p className="mx-auto mt-5 max-w-2xl text-xl leading-relaxed" style={{ color: "var(--ink-dim)" }}>
          {anchorClaim}
        </p>
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        {positions.map((p) => (
          <Link key={p.href} href={p.href} className="group">
            <div className="chalk-card h-full px-6 py-6 transition-transform group-hover:-translate-y-1">
              <div className="text-sm uppercase tracking-widest" style={{ color: "var(--ink-faint)" }}>
                {p.label}
              </div>
              <div className="font-display mt-2 text-3xl font-bold leading-tight" style={{ color: p.color }}>
                {p.title}
              </div>
              <p className="mt-3 leading-snug" style={{ color: "var(--ink-dim)" }}>
                {p.blurb}
              </p>
              <div className="mt-4 text-lg" style={{ color: "var(--ink)" }}>
                Open the board →
              </div>
            </div>
          </Link>
        ))}
      </div>

      <ChalkCard
        kicker="The connective tissue"
        title="One question, three positions"
        note="Cross-study callbacks: where the three studies agree, disagree, and why. ~1,350 drafted players across RB, WR, and QB."
      >
        <div className="scroll-x">
          <table className="chalk-table">
            <thead>
              <tr>
                <th>Finding</th>
                <th>RB</th>
                <th>WR</th>
                <th>QB</th>
              </tr>
            </thead>
            <tbody>
              {crossStudy.map((r) => (
                <tr key={r.finding}>
                  <td style={{ color: "var(--ink)" }}>{r.finding}</td>
                  <td style={{ color: "var(--ink-dim)" }}>{r.rb}</td>
                  <td style={{ color: "var(--ink-dim)" }}>{r.wr}</td>
                  <td style={{ color: "var(--ink-dim)" }}>{r.qb}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ChalkCard>
    </div>
  );
}
