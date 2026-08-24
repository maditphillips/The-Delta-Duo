export default function StatTile({
  value,
  label,
  sublabel,
  color = "var(--chalk-yellow)",
}: {
  value: string;
  label: string;
  sublabel?: string;
  color?: string;
}) {
  return (
    <div className="chalk-card-alt flex flex-col items-center px-4 py-5 text-center">
      <div className="font-display text-5xl font-bold leading-none sm:text-6xl" style={{ color }}>
        {value}
      </div>
      <div className="mt-2 text-lg leading-tight" style={{ color: "var(--ink)" }}>
        {label}
      </div>
      {sublabel && (
        <div className="mt-1 text-sm leading-snug" style={{ color: "var(--ink-dim)" }}>
          {sublabel}
        </div>
      )}
    </div>
  );
}
