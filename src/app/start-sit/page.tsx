import type { Metadata } from "next";
import StartSit from "@/components/StartSit";

export const metadata: Metadata = {
  title: "Start / Sit · The Delta Duo",
  description:
    "Two players in, one decision out. Wilson's projection and MC's rank on the same scale, plus the ceiling, the floor and the odds of a startable week.",
};

export default function StartSitPage() {
  return (
    <div>
      <div className="mb-6 pt-2 sm:mb-8 sm:pt-4">
        <h1 className="neon-title text-2xl sm:text-4xl">Start / Sit</h1>
        <p className="mt-2 max-w-3xl text-base sm:text-xl" style={{ color: "var(--ink-dim)" }}>
          Pick two. We&apos;ll tell you who&apos;s better, and since that isn&apos;t always the
          same question, who wins you the week and who keeps you out of trouble.
        </p>
      </div>
      <StartSit />
    </div>
  );
}
