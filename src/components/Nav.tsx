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
  { href: "/data-vs-vibes", label: "Data vs. Vibes" },
  { href: "/rankings", label: "Rankings" },
];

export default function Nav() {
  const pathname = usePathname();
  return (
    <header className="mx-auto max-w-6xl px-4 pt-6 sm:px-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <Link href="/" className="flex items-center gap-3">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/delta-duo-badge.png" alt="" aria-hidden className="h-14 w-auto object-contain" />
          <span className="leading-none">
            <span className="neon-title block text-3xl">The Delta Duo</span>
            <span className="mt-1.5 block text-[0.65rem] tracking-[0.28em] uppercase" style={{ color: "var(--accent-3)" }}>
              Wilson does the data · MC does the vibes
            </span>
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
      <div className="neon-divider mt-4" />
    </header>
  );
}
