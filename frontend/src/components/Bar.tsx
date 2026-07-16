/** A labeled resource bar (HP / MP / Stamina / EXP) with an ASCII-style fill. */
export function Bar({
  label,
  value,
  max,
  className,
}: {
  label: string;
  value: number;
  max: number;
  className: string;
}) {
  const pct = max > 0 ? Math.max(0, Math.min(100, (value / max) * 100)) : 0;
  return (
    <div className="bar-row">
      <span className="bar-label">{label}</span>
      <span className={`bar ${className}`}>
        <span className="bar-fill" style={{ width: `${pct}%` }} />
      </span>
      <span className="bar-value">
        {value} / {max}
      </span>
    </div>
  );
}
