import type { Metadata } from "next";
import WeeklyBoard from "@/components/WeeklyBoard";

export const metadata: Metadata = {
  title: "Weekly Data vs. Vibe Rankings — The Delta Duo",
  description:
    "Every week, two rankings per position: Wilson's built purely from the data, MC's built purely from the vibes — and the delta between them.",
};

export default function DataVsVibesPage() {
  return (
    <div>
      <div className="mb-6 pt-2 sm:mb-8 sm:pt-4">
        <h1 className="neon-title text-2xl sm:text-4xl">Weekly Data vs. Vibe Rankings</h1>
        <p className="mt-2 max-w-3xl text-base sm:text-xl" style={{ color: "var(--ink-dim)" }}>
          Two rankings, same players, every week. Wilson ranks on the data alone. MC ranks on the vibes alone. The gap between
          them is the delta.
        </p>
      </div>
      <WeeklyBoard />
    </div>
  );
}
