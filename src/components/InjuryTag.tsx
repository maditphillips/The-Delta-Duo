/** Sleeper's designation as a small badge next to a name: "Q" for
 *  Questionable, the full text on hover and for screen readers. Display only:
 *  the ranking is not adjusted for it. */
export default function InjuryTag({ injury }: { injury?: string | null }) {
  if (!injury) return null;
  const status = injury.split(" (")[0];
  const short = status === "Questionable" ? "Q" : status === "Doubtful" ? "D" : status.slice(0, 1).toUpperCase();
  return (
    <span
      title={injury}
      aria-label={injury}
      style={{
        display: "inline-block",
        marginLeft: 6,
        padding: "0 5px",
        borderRadius: 4,
        fontSize: "0.72em",
        fontWeight: 700,
        lineHeight: 1.5,
        verticalAlign: "middle",
        color: "var(--accent-gold)",
        border: "1px solid var(--accent-gold)",
      }}
    >
      {short}
    </span>
  );
}
