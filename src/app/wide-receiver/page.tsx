import type { Metadata } from "next";
import WrDashboard from "@/components/dashboards/WrDashboard";
import { wrMeta } from "@/data/wr";

export const metadata: Metadata = {
  title: "Wide Receiver — The Delta Duo",
  description: wrMeta.subtitle,
};

export default function WideReceiverPage() {
  return (
    <div>
      <div className="mb-6 pt-2 sm:mb-8 sm:pt-4">
        <h1 className="neon-title text-2xl sm:text-4xl">
          {wrMeta.title}
        </h1>
        <p className="mt-2 max-w-3xl text-base sm:text-xl" style={{ color: "var(--ink-dim)" }}>
          {wrMeta.subtitle}
        </p>
      </div>
      <WrDashboard />
    </div>
  );
}
