import { cn } from "@/lib/utils";

export function ConfidenceMeter({
  value,
  className,
}: {
  value: number;
  className?: string;
}) {
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div className={cn("space-y-1", className)}>
      <div className="flex justify-between text-xs text-ink-muted">
        <span>0</span>
        <span>{pct}%</span>
        <span>100</span>
      </div>
      <div
        className="h-2 w-full overflow-hidden rounded-full bg-paper-3"
        role="meter"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className="h-full rounded-full bg-accent transition-[width] duration-normal ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
