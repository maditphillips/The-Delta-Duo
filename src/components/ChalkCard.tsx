import { ReactNode } from "react";

export default function ChalkCard({
  title,
  kicker,
  kickerRight,
  note,
  source,
  children,
  alt = false,
}: {
  title?: string;
  kicker?: string;
  /** A second kicker pinned to the right of the first, for a card that has to
   *  say what it is showing as well as what it is answering. */
  kickerRight?: string;
  note?: string;
  source?: string;
  children: ReactNode;
  alt?: boolean;
}) {
  return (
    <section className={`${alt ? "chalk-card-alt" : "chalk-card"} px-3 py-4 sm:px-7 sm:py-6`}>
      <div className="relative">
        {(kicker || kickerRight) && (
          <div className="mb-1.5 flex items-baseline justify-between gap-3">
            <span className="chalk-kicker">{kicker}</span>
            {kickerRight && <span className="chalk-kicker">{kickerRight}</span>}
          </div>
        )}
        {title && (
          <h2 className="font-sketch mb-4 text-xl sm:mb-5 sm:text-[1.7rem]" style={{ color: "var(--ink)" }}>
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
