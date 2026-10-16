/**
 * MetricsCard.jsx — Reusable Metric Display Card
 * =================================================
 * Shows a single metric value with label and optional delta.
 */

export default function MetricsCard({ label, value, delta, suffix = '', colorize = false }) {
  // Determine color class based on value
  let valueClass = 'metric-card__value';
  if (colorize && typeof value === 'number') {
    if (value > 0) valueClass += ' metric-card__value--up';
    else if (value < 0) valueClass += ' metric-card__value--down';
  }

  // Format the display value
  const displayValue = typeof value === 'number'
    ? `${value.toFixed(2)}${suffix}`
    : value || '—';

  // Format delta
  const deltaDisplay = delta !== undefined && delta !== null
    ? `${delta >= 0 ? '+' : ''}${delta.toFixed(3)}`
    : null;

  return (
    <div className="metric-card fade-in">
      <div className="metric-card__label">{label}</div>
      <div className={valueClass}>{displayValue}</div>
      {deltaDisplay && (
        <div
          className="metric-card__delta"
          style={{ color: delta >= 0 ? 'var(--color-up)' : 'var(--color-down)' }}
        >
          {deltaDisplay}
        </div>
      )}
    </div>
  );
}
