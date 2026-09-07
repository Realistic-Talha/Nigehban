"use client";

export function EntityBars({ counts }: { counts: Record<string, number> }) {
  const entries = Object.entries(counts);
  if (entries.length === 0) {
    return (
      <p className="app-card p-6 text-sm text-ink-muted">
        Entity mix appears when trending data is available.
      </p>
    );
  }

  const max = Math.max(...entries.map(([, n]) => n), 1);

  return (
    <div className="app-card p-5 sm:p-6">
      <h3 className="font-display text-xl text-ink">By entity type</h3>
      <ul className="mt-5 space-y-4">
        {entries.map(([type, count]) => (
          <li key={type}>
            <div className="mb-1 flex justify-between text-sm">
              <span className="capitalize text-ink-muted">{type.replace(/_/g, " ")}</span>
              <span className="tabular-nums text-ink">{count}</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-paper-3">
              <div
                className="h-full rounded-full bg-accent/80"
                style={{ width: `${(count / max) * 100}%` }}
              />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
