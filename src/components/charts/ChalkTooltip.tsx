"use client";

import type { TooltipContentProps } from "recharts";

type Formatter = (value: number, name: string) => string;

export default function ChalkTooltip({
  active,
  payload,
  label,
  format,
}: Partial<TooltipContentProps<number, string>> & { format?: Formatter }) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div
      className="rounded-xl px-3 py-2 text-base"
      style={{
        background: "#1c2f27",
        border: "2px solid var(--ink-faint)",
        color: "var(--ink)",
        fontFamily: "var(--font-chalk)",
        maxWidth: 280,
      }}
    >
      {label != null && (
        <div className="mb-1" style={{ color: "var(--ink-dim)" }}>
          {String(label)}
        </div>
      )}
      {payload.map((p, i) => (
        <div key={i} className="flex items-center gap-2">
          <span
            aria-hidden
            style={{ background: p.color ?? "var(--ink)", width: 10, height: 10, borderRadius: 3, display: "inline-block" }}
          />
          <span>
            {p.name}:{" "}
            <strong>
              {format ? format(Number(p.value), String(p.name)) : `${Number(p.value).toLocaleString()}`}
            </strong>
          </span>
        </div>
      ))}
    </div>
  );
}
