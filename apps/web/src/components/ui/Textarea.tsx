import { cn } from "@/lib/utils";

export function Textarea({ className, ...props }: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        "min-h-[160px] w-full resize-y rounded-[24px] border border-border bg-paper px-4 py-4 text-base text-ink sm:min-h-[200px]",
        "placeholder:text-ink-subtle transition-colors duration-fast",
        "hover:border-border-strong focus-visible:border-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/25",
        "disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    />
  );
}
