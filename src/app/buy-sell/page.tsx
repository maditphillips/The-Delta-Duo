import type { Metadata } from "next";
import BuySell from "@/components/BuySell";

export const metadata: Metadata = {
  title: "Buy Low / Sell High · The Delta Duo",
  description:
    "Which of last week's outliers meant something. Every miss split into the work a player was given and what he did with it, then judged against four seasons of what followed.",
};

export default function BuySellPage() {
  return (
    <div>
      <div className="mb-6 pt-2 sm:mb-8 sm:pt-4">
        <h1 className="neon-title text-2xl sm:text-4xl">Buy Low / Sell High</h1>
        <p className="mt-2 max-w-3xl text-base sm:text-xl" style={{ color: "var(--ink-dim)" }}>
          A huge week and a terrible one both tell you something or nothing. This splits
          each one into the work a player was given and what he did with it, then asks
          four seasons of history which way it usually goes.
        </p>
      </div>
      <BuySell />
    </div>
  );
}
