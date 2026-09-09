import Link from "next/link";
import ChalkCard from "@/components/ChalkCard";
import WeeklyDeltas from "@/components/WeeklyDeltas";
import { anchorClaim, crossStudy } from "@/data/crossStudy";
import { CHALK } from "@/components/charts/theme";

const dashboards = [
  {
    href: "/wide-receiver",
    label: "Wide Receiver",
    title: "The Two Doors of Fantasy Relevance",
    blurb: "Getting on the field, and getting the ball. 580 drafted WRs since 2008, both gates measured.",
    color: CHALK.pink,
  },
  {
    href: "/quarterback",
    label: "Quarterback",
    title: "The Quarterback Cliff",
    blurb: "The draft decides who plays. It does not decide who is good. 212 drafted QBs, 2008–2025.",
    color: "var(--accent)",
  },
  {
    href: "/running-back",
    label: "Running Back",
    title: "The Running Back Cliff",
    blurb: "388 drafted RBs — and every down they played — on talent, volume, and third down.",
    color: CHALK.blue,
  },
];

const otherTabs = [
  {
    href: "/data-vs-vibes",
    label: "Weekly Rankings",
    blurb:
      "Every week, two rankings per position: Wilson's built purely from the data, MC's built purely from the vibes — plus the delta between them.",
    color: "var(--accent-2-lt)",
  },
  {
    href: "/start-sit",
    label: "Start / Sit",
    blurb:
      "Two players in, one decision out — plus who wins you the week, who keeps you out of trouble, and why those aren't the same man.",
    color: CHALK.green,
  },
  {
    href: "/rankings",
    label: "Season Rankings",
    blurb:
      "The season-long redraft boards — PPR, Half PPR, and Superflex — every player, tier, bye, and the delta note behind each call.",
    color: "var(--accent)",
  },
  {
    href: "/explorer",
    label: "Player Explorer",
    blurb:
      "Build any category from the studies — draft day, age, target band, moves, vacancies — and get the actual list of players in it.",
    color: "var(--accent-3)",
  },
  {
    href: "/stadiums",
    label: "Stadiums",
    blurb: "Every NFL kicking venue since 2002, and what the buildings themselves do to field goals.",
    color: CHALK.green,
  },
];

export default function Home() {
  return (
    <div className="flex flex-col gap-8 sm:gap-10">
      <div className="pt-6 text-center">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/delta-duo-logo.png" alt="The Delta Duo" className="mx-auto mb-6 w-full max-w-[15rem] object-contain sm:mb-8 sm:max-w-sm" />
        <h1 className="neon-title mx-auto max-w-3xl text-2xl leading-tight sm:text-4xl">
          We don&apos;t draft players. We draft deltas.
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-base leading-relaxed sm:mt-5 sm:text-lg" style={{ color: "var(--ink-dim)" }}>
          A delta is a measurable distance between two values. We find the ones that matter: the gap between where consensus
          has a player and where he actually belongs.
        </p>
        <p className="mx-auto mt-3 max-w-2xl text-sm leading-relaxed" style={{ color: "var(--ink-faint)" }}>
          {anchorClaim}
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="chalk-inset px-5 py-4 sm:px-6 sm:py-5" style={{ borderColor: "rgba(255,47,166,0.4)" }}>
          <div className="font-retro text-2xl" style={{ color: "var(--accent-2)" }}>
            Wilson
          </div>
          <div className="chalk-kicker mt-1" style={{ color: "var(--accent-2)" }}>
            the data
          </div>
          <p className="mt-2 text-sm leading-snug" style={{ color: "var(--ink-dim)" }}>
            Data scientist. Makes every call with the numbers… the studies, the models, the base rates. Looks into data
            you&apos;ve never even thought of.
          </p>
        </div>
        <div className="chalk-inset px-5 py-4 sm:px-6 sm:py-5" style={{ borderColor: "rgba(69,227,255,0.35)" }}>
          <div className="font-retro text-2xl" style={{ color: "var(--accent-3)" }}>
            MC
          </div>
          <div className="chalk-kicker mt-1" style={{ color: "var(--accent-3)" }}>
            the vibes
          </div>
          <p className="mt-2 text-sm leading-snug" style={{ color: "var(--ink-dim)" }}>
            Makes every call with the vibes — the film feel, the locker-room reads, the gut. Some things the numbers
            can&apos;t see yet.
          </p>
        </div>
      </div>

      <div>
        <h2 className="neon-title mb-1 text-2xl sm:text-3xl">The Dashboards</h2>
        <p className="mb-5 max-w-3xl text-sm" style={{ color: "var(--ink-dim)" }}>
          One tab per position. Each is a live dashboard carrying every current finding from that position&apos;s study —
          the tables, the charts, and the base rates, all interactive. When a study is updated, the dashboard updates
          with it.
        </p>
        <div className="grid gap-5 lg:grid-cols-3">
          {dashboards.map((p) => (
            <Link key={p.href} href={p.href} className="group">
              <div className="chalk-card h-full px-6 py-6 transition-transform group-hover:-translate-y-1">
                <div className="chalk-kicker relative">{p.label} · dashboard</div>
                <div className="font-sketch relative mt-2 text-2xl leading-tight" style={{ color: p.color }}>
                  {p.title}
                </div>
                <p className="relative mt-3 text-sm leading-snug" style={{ color: "var(--ink-dim)" }}>
                  {p.blurb}
                </p>
                <div className="chalk-annotation relative mt-4" style={{ color: "var(--accent)" }}>
                  Open the board →
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>

      <div>
        <h2 className="neon-title mb-1 text-2xl sm:text-3xl">Everything Else</h2>
        <p className="mb-5 max-w-3xl text-sm" style={{ color: "var(--ink-dim)" }}>
          Where the studies turn into calls you can actually draft on.
        </p>
        <div className="grid gap-4 sm:grid-cols-2">
          {otherTabs.map((t) => (
            <Link key={t.href} href={t.href} className="group">
              <div className="chalk-inset h-full px-5 py-4 transition-colors group-hover:border-[color:var(--ink-faint)]">
                <div className="font-retro text-xl" style={{ color: t.color }}>
                  {t.label}
                </div>
                <p className="mt-2 text-sm leading-snug" style={{ color: "var(--ink-dim)" }}>
                  {t.blurb}
                </p>
              </div>
            </Link>
          ))}
        </div>
      </div>

      <WeeklyDeltas />

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
