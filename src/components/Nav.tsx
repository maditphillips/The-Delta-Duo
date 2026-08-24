"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const tabs = [
  { href: "/", label: "The Lab" },
  { href: "/wide-receiver", label: "Wide Receiver" },
  { href: "/quarterback", label: "Quarterback" },
  { href: "/running-back", label: "Running Back" },
  { href: "/rankings", label: "Rankings" },
];

export default function Nav() {
  const pathname = usePathname();
  return (
    <header className="mx-auto max-w-6xl px-4 pt-8 sm:px-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <Link href="/" className="leading-none">
          <span className="font-display block text-5xl font-bold" style={{ color: "var(--ink)" }}>
            The Delta Duo
          </span>
          <span className="mt-1 block text-sm tracking-wide" style={{ color: "var(--ink-dim)" }}>
            fantasy football, measured
          </span>
        </Link>
        <nav className="flex flex-wrap gap-2 text-lg">
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
      <div
        className="mt-4 h-0.5 w-full"
        style={{
          background: "var(--ink-faint)",
          borderRadius: "50% 40% 60% 45% / 60% 50% 45% 55%",
        }}
      />
    </header>
  );
}
