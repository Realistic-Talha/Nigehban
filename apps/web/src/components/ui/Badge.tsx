import { cn } from "@/lib/utils";

const verdictStyles: Record<string, string> = {
  true: "bg-success/15 text-success border-success/25",
  false: "bg-danger/15 text-danger border-danger/25",
  misleading: "bg-warning/15 text-warning border-warning/25",
  unverified: "bg-paper-3 text-ink-muted border-border",
  scam: "bg-danger/15 text-danger border-danger/25",
  safe: "bg-success/15 text-success border-success/25",
  needs_caution: "bg-warning/15 text-warning border-warning/25",
  inconclusive: "bg-paper-3 text-ink-muted border-border",
  likely_authentic: "bg-success/15 text-success border-success/25",
  likely_edited: "bg-warning/15 text-warning border-warning/25",
  likely_manipulated: "bg-danger/15 text-danger border-danger/25",
  likely_scam: "bg-danger/15 text-danger border-danger/25",
  likely_safe: "bg-success/15 text-success border-success/25",
};

export function Badge({
  verdict,
  className,
}: {
  verdict: string;
  className?: string;
}) {
  const key = verdict.toLowerCase().replace(/\s+/g, "_");
  return (
    <span
      className={cn(
        "inline-flex min-h-7 items-center rounded-full border px-3 py-0.5 text-[11px] font-semibold capitalize tracking-wide",
        verdictStyles[key] ?? verdictStyles.unverified,
        className,
      )}
    >
      {verdict.replace(/_/g, " ")}
    </span>
  );
}
