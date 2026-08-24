import type { Metadata } from "next";
import ExplorerBoard from "@/components/ExplorerBoard";

export const metadata: Metadata = {
  title: "Player Explorer — The Delta Duo",
  description:
    "Stack the studies' filters — draft day, age, target bands, moves, vacancies — and get the actual list of player-seasons behind every category.",
};

export default function ExplorerPage() {
  return (
    <div>
      <div className="mb-8 pt-4">
        <h1 className="font-sketch text-3xl sm:text-4xl" style={{ color: "var(--ink)" }}>
          Player Explorer
        </h1>
        <p className="mt-2 max-w-3xl text-xl" style={{ color: "var(--ink-dim)" }}>
          Every category in the studies, as a list of names. Stack filters and see exactly who falls in the bucket.
        </p>
        <p className="mt-2 max-w-3xl text-sm" style={{ color: "var(--ink-faint)" }}>
          Built from nflverse data (draft picks + seasonal stats, 2008–2025, regular season, PPR). Lists may differ at the
          margins from the published study panels, which use finer roster reconstruction.
        </p>
      </div>
      <ExplorerBoard />
    </div>
  );
}
