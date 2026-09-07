"use client";

import { useLocale } from "@/providers/locale-provider";
import { cn } from "@/lib/utils";

export function LocaleToggle({ className }: { className?: string }) {
  const { locale, setLocale } = useLocale();
  return (
    <button
      type="button"
      onClick={() => setLocale(locale === "en" ? "ur" : "en")}
      className={cn(
        "inline-flex h-10 min-w-10 cursor-pointer items-center justify-center rounded-full border border-border bg-paper px-3 text-[13px] font-semibold text-ink-muted transition-colors hover:border-ink/20 hover:text-ink",
        className,
      )}
      aria-label="Toggle language"
    >
      {locale === "en" ? "اردو" : "EN"}
    </button>
  );
}
