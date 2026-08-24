import { ReactNode } from "react";

export default function ChalkCard({
  title,
  kicker,
  note,
  source,
  children,
  alt = false,
}: {
  title?: string;
  kicker?: string;
  note?: string;
  source?: string;
  children: ReactNode;
  alt?: boolean;
}) {
  return (
    <section className={`${alt ? "chalk-card-alt" : "chalk-card"} px-5 py-5 sm:px-7 sm:py-6`}>
      <div className="relative">
        {kicker && <div className="chalk-kicker mb-1.5">{kicker}</div>}
        {title && (
          <h2 className="font-sketch mb-5 text-2xl sm:text-[1.7rem]" style={{ color: "var(--ink)" }}>
            {title}
          </h2>
        )}
        {children}
        {note && (
          <p className="mt-4 text-sm leading-snug" style={{ color: "var(--ink-dim)" }}>
            {note}
          </p>
        )}
        <div className="mt-5 flex items-baseline justify-between gap-4 border-t pt-2" style={{ borderColor: "var(--ink-ghost)" }}>
          <span className="chalk-brand">The Delta Duo</span>
          <span className="chalk-source text-right">{source ?? "we don't draft players. we draft deltas."}</span>
        </div>
      </div>
    </section>
  );
}
