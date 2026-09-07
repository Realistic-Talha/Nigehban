import { cn } from "@/lib/utils";

export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-[20px] bg-paper-3 motion-reduce:animate-none",
        className,
      )}
      aria-hidden
    />
  );
}
