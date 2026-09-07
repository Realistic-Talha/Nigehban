"use client";

import { useLocale } from "@/providers/locale-provider";
import { cn } from "@/lib/utils";

type Window = "24h" | "7d" | "30d";

export function PulseHeader({
  window,
  onWindowChange,
}: {
  window: Window;
  onWindowChange: (w: Window) => void;
}) {
  const { t } = useLocale();
  const options: [Window, string][] = [
    ["24h", t("dashboard.window24h")],
    ["7d", t("dashboard.window7d")],
    ["30d", t("dashboard.window30d")],
  ];

  return (
    <div className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p className="page-eyebrow">Dashboard</p>
        <h1 className="page-title mt-2">Public pulse</h1>
      </div>
      <div className="inline-flex rounded-full border border-border bg-white p-1">
        {options.map(([w, label]) => (
          <button
            key={w}
            type="button"
            onClick={() => onWindowChange(w)}
            className={cn(
              "min-h-10 rounded-full px-4 text-[13px] font-semibold transition-colors",
              window === w ? "bg-ink text-paper" : "text-ink-muted hover:text-ink",
            )}
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}
