import Link from "next/link";
import ChalkCard from "@/components/ChalkCard";
import { anchorClaim, crossStudy } from "@/data/crossStudy";
import { CHALK } from "@/components/charts/theme";

const positions = [
  {
    href: "/wide-receiver",
    label: "Wide Receiver",
    title: "The Two Doors of Fantasy Relevance",
    blurb: "Getting on the field, and getting the ball. What 580 drafted WRs since 2008 reveal about both gates.",
    color: CHALK.pink,
  },
  {
    href: "/quarterback",
    label: "Quarterback",
    title: "The Quarterback Cliff",
    blurb: "The draft decides who plays. It does not decide who is good. 212 drafted QBs, 2008–2025.",
    color: CHALK.gold,
  },
  {
    href: "/running-back",
    label: "Running Back",
    title: "The Running Back Cliff",
    blurb: "What 388 drafted RBs — and every down they played — reveal about talent, volume, and third down.",
    color: CHALK.blue,
  },
];

export default function Home() {
  return (
    <div className="flex flex-col gap-10">
      <div className="pt-6 text-center">
        <h1 className="font-sketch mx-auto max-w-3xl text-4xl leading-tight sm:text-5xl" style={{ color: "var(--ink)" }}>
          The draft decides who plays.
          <br />
          <span style={{ color: CHALK.gold }}>It does not decide who is good.</span>
        </h1>
        <p className="mx-auto mt-5 max-w-2xl text-xl leading-relaxed" style={{ color: "var(--ink-dim)" }}>
          {anchorClaim}
        </p>
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        {positions.map((p) => (
          <Link key={p.href} href={p.href} className="group">
            <div className="chalk-card h-full px-6 py-6 transition-transform group-hover:-translate-y-1">
              <div className="chalk-kicker relative">{p.label}</div>
              <div className="font-sketch relative mt-2 text-2xl leading-tight" style={{ color: p.color }}>
                {p.title}
              </div>
              <p className="relative mt-3 text-sm leading-snug" style={{ color: "var(--ink-dim)" }}>
                {p.blurb}
              </p>
              <div className="chalk-annotation relative mt-4">Open the board →</div>
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
