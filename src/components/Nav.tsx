"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const tabs = [
  { href: "/", label: "The Deltas" },
  { href: "/wide-receiver", label: "Wide Receiver" },
  { href: "/quarterback", label: "Quarterback" },
  { href: "/running-back", label: "Running Back" },
  { href: "/explorer", label: "Player Explorer" },
  { href: "/stadiums", label: "Stadiums" },
  { href: "/rankings", label: "Rankings" },
];

export default function Nav() {
  const pathname = usePathname();
  return (
    <header className="mx-auto max-w-6xl px-4 pt-8 sm:px-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <Link href="/" className="leading-none">
          <span className="font-sketch block text-4xl" style={{ color: "var(--ink)" }}>
            The Delta Duo
          </span>
          <span className="mt-1 block text-xs tracking-[0.28em] uppercase" style={{ color: "var(--accent)" }}>
            fantasy football, measured
          </span>
        </Link>
        <nav className="flex flex-wrap gap-1.5 text-sm">
          {tabs.map((t) => {
            const active = t.href === "/" ? pathname === "/" : pathname.startsWith(t.href);
            return (
              <Link key={t.href} href={t.href} className={`chalk-tab ${active ? "active" : ""}`}>
                {t.label}
              </Link>
            );
          })}
        </nav>
      </div>
      <div className="mt-4 h-px w-full" style={{ background: "var(--ink-ghost)" }} />
    </header>
  );
}
