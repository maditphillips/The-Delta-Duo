import type { Metadata } from "next";
import RankingsBoard from "@/components/RankingsBoard";

export const metadata: Metadata = {
  title: "Rankings — The Delta Duo",
  description: "The Delta Duo's player rankings: overall, quarterback, running back, and wide receiver boards.",
};

export default function RankingsPage() {
  return (
    <div>
      <div className="mb-8 pt-4">
        <h1 className="font-display text-4xl font-bold sm:text-5xl" style={{ color: "var(--ink)" }}>
          The Rankings Board
        </h1>
        <p className="mt-2 max-w-3xl text-xl" style={{ color: "var(--ink-dim)" }}>
          Positional and overall boards, straight from the lab. Updated by CSV upload — no redeploy needed.
        </p>
      </div>
      <RankingsBoard />
    </div>
  );
}
