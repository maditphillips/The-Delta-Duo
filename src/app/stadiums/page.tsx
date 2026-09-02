import type { Metadata } from "next";
import StadiumDashboard from "@/components/dashboards/StadiumDashboard";
import { stadiumMeta } from "@/data/stadiums";

export const metadata: Metadata = {
  title: "Stadiums — The Delta Duo",
  description:
    "Every NFL kicking venue since 2002, scored against a leave-one-out expectation: which stadiums are genuinely hard on visiting kickers, which reputations don't survive the data, and how teams price the building into their own fourth-down math.",
};

export default function StadiumsPage() {
  return (
    <div>
      <div className="mb-8 pt-4">
        <h1 className="font-sketch text-3xl sm:text-4xl" style={{ color: "var(--ink)" }}>
          The Kicking Ladder
        </h1>
        <p className="mt-2 max-w-3xl text-xl" style={{ color: "var(--ink-dim)" }}>
          Which stadiums are actually hard to kick in — and which ones just have the reputation.
        </p>
        <p className="mt-2 max-w-3xl text-sm" style={{ color: "var(--ink-faint)" }}>
          {stadiumMeta.totalFG.toLocaleString()} field goals and {stadiumMeta.totalPunts.toLocaleString()} punts from
          nflverse play-by-play, {stadiumMeta.seasons}, across {stadiumMeta.venues} venues. Every kick is scored against
          a distance-and-season model refit for each venue with that venue&apos;s own kicks held out, so no stadium is
          graded against itself.
        </p>
      </div>
      <StadiumDashboard />
    </div>
  );
}
