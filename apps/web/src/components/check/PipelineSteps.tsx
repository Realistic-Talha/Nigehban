import { cn } from "@/lib/utils";

export function PipelineSteps({
  steps,
  stepStatus,
}: {
  steps: string[];
  stepStatus: Record<string, string>;
}) {
  return (
    <ol className="flex flex-wrap gap-2" aria-label="Pipeline progress">
      {steps.map((step, i) => {
        const status = stepStatus[step] ?? "pending";
        return (
          <li
            key={step}
            className={cn(
              "inline-flex items-center gap-2 rounded-full border px-3 py-2 text-xs font-medium capitalize",
              status === "complete" && "border-success/30 bg-success/10 text-success",
              status === "running" &&
                "border-accent/40 bg-accent-muted text-accent animate-pulse motion-reduce:animate-none",
              status === "error" && "border-danger/40 bg-danger/10 text-danger",
              status === "pending" && "border-border bg-paper-2 text-ink-subtle",
            )}
          >
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-current/10 text-[10px] opacity-70">
              {i + 1}
            </span>
            {step.replace(/_/g, " ")}
          </li>
        );
      })}
    </ol>
  );
}
