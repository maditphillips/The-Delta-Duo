import type { Metadata } from "next";
import RankingsBoard from "@/components/RankingsBoard";

export const metadata: Metadata = {
  title: "Rankings — The Delta Duo",
  description: "The Delta Duo's 2026 redraft rankings: PPR, Half PPR, and Superflex boards with QB/RB/WR/TE views.",
};

export default function RankingsPage() {
  return (
    <div>
      <div className="mb-8 pt-4">
        <h1 className="font-sketch text-3xl sm:text-4xl" style={{ color: "var(--ink)" }}>
          The Rankings Board
        </h1>
        <p className="mt-2 max-w-3xl text-xl" style={{ color: "var(--ink-dim)" }}>
          The 2026 redraft boards — PPR, Half PPR, and Superflex — with every tier, bye, and delta note. Toggle a position to see
          just the QBs, RBs, WRs, or TEs.
        </p>
      </div>
      <RankingsBoard />
    </div>
  );
}
