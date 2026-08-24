export default function StatTile({
  value,
  label,
  sublabel,
  color = "var(--chalk-gold)",
}: {
  value: string;
  label: string;
  sublabel?: string;
  color?: string;
}) {
  return (
    <div className="chalk-card-alt flex flex-col items-center px-4 py-5 text-center">
      <div className="font-sketch relative text-4xl leading-none sm:text-5xl" style={{ color }}>
        {value}
      </div>
      <div className="relative mt-2 text-base leading-tight" style={{ color: "var(--ink)" }}>
        {label}
      </div>
      {sublabel && (
        <div className="relative mt-1 text-sm leading-snug" style={{ color: "var(--ink-dim)" }}>
          {sublabel}
        </div>
      )}
    </div>
  );
}
