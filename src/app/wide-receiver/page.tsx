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
      <div className="mb-8 pt-4">
        <h1 className="font-sketch text-3xl sm:text-4xl" style={{ color: "var(--ink)" }}>
          {wrMeta.title}
        </h1>
        <p className="mt-2 max-w-3xl text-xl" style={{ color: "var(--ink-dim)" }}>
          {wrMeta.subtitle}
        </p>
      </div>
      <WrDashboard />
    </div>
  );
}
