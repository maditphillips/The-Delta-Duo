import type { Metadata } from "next";
import RbDashboard from "@/components/dashboards/RbDashboard";
import { rbMeta } from "@/data/rb";

export const metadata: Metadata = {
  title: "Running Back — The Delta Duo",
  description: rbMeta.subtitle,
};

export default function RunningBackPage() {
  return (
    <div>
      <div className="mb-8 pt-4">
        <h1 className="font-sketch text-3xl sm:text-4xl" style={{ color: "var(--ink)" }}>
          {rbMeta.title}
        </h1>
        <p className="mt-2 max-w-3xl text-xl" style={{ color: "var(--ink-dim)" }}>
          {rbMeta.subtitle}
        </p>
        <p className="mt-2 max-w-3xl text-sm" style={{ color: "var(--ink-faint)" }}>
          {rbMeta.population}
        </p>
      </div>
      <RbDashboard />
    </div>
  );
}
