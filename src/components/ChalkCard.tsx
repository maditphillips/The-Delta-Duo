import { ReactNode } from "react";

export default function ChalkCard({
  title,
  kicker,
  note,
  children,
  alt = false,
}: {
  title?: string;
  kicker?: string;
  note?: string;
  children: ReactNode;
  alt?: boolean;
}) {
  return (
    <section className={`${alt ? "chalk-card-alt" : "chalk-card"} px-5 py-5 sm:px-7 sm:py-6`}>
      {kicker && (
        <div className="mb-1 text-sm uppercase tracking-widest" style={{ color: "var(--ink-faint)" }}>
          {kicker}
        </div>
      )}
      {title && (
        <h2 className="chalk-underline mb-5 inline-block text-2xl sm:text-3xl" style={{ color: "var(--ink)" }}>
          {title}
        </h2>
      )}
      {children}
      {note && (
        <p className="mt-4 text-sm leading-snug" style={{ color: "var(--ink-dim)" }}>
          {note}
        </p>
      )}
    </section>
  );
}
