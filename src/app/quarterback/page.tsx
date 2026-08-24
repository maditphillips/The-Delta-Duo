import type { Metadata } from "next";
import QbDashboard from "@/components/dashboards/QbDashboard";
import { qbMeta } from "@/data/qb";

export const metadata: Metadata = {
  title: "Quarterback — The Delta Duo",
  description: qbMeta.subtitle,
};

export default function QuarterbackPage() {
  return (
    <div>
      <div className="mb-8 pt-4">
        <h1 className="font-sketch text-3xl sm:text-4xl" style={{ color: "var(--ink)" }}>
          {qbMeta.title}
        </h1>
        <p className="mt-2 max-w-3xl text-xl" style={{ color: "var(--ink-dim)" }}>
          {qbMeta.subtitle}
        </p>
        <p className="mt-2 max-w-3xl text-sm" style={{ color: "var(--ink-faint)" }}>
          {qbMeta.population}
        </p>
      </div>
      <QbDashboard />
    </div>
  );
}
