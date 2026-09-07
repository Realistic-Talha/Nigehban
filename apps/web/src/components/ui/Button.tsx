"use client";

import { cn } from "@/lib/utils";

export function Button({
  className,
  variant = "primary",
  state = "default",
  disabled,
  children,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "cta" | "ghost" | "outline" | "danger";
  state?: "default" | "loading" | "error" | "success";
}) {
  const isLoading = state === "loading";
  return (
    <button
      className={cn(
        "inline-flex min-h-12 cursor-pointer items-center justify-center gap-2 rounded-full px-6 py-2.5 text-sm font-semibold transition-all duration-normal ease-out",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-paper",
        "disabled:cursor-not-allowed disabled:opacity-50",
        "hover:-translate-y-0.5 hover:shadow-sm active:scale-[0.98]",
        variant === "primary" && "bg-cta text-on-cta hover:bg-cta-hover",
        variant === "cta" && "bg-cta text-on-cta hover:bg-cta-hover",
        variant === "secondary" && "border border-border bg-paper-2 text-ink hover:bg-paper-3",
        variant === "outline" &&
          "border-[1.5px] border-accent bg-transparent text-accent hover:bg-accent hover:text-on-accent",
        variant === "ghost" && "text-ink-muted hover:bg-paper-3 hover:text-ink",
        variant === "danger" && "bg-danger text-white hover:opacity-90",
        state === "error" && "ring-2 ring-danger",
        state === "success" && "ring-2 ring-success",
        className,
      )}
      disabled={disabled || isLoading}
      data-state={state}
      {...props}
    >
      {isLoading && (
        <span
          className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent"
          aria-hidden
        />
      )}
      {children}
    </button>
  );
}
