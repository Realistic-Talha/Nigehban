"use client";

import { useLocale } from "@/providers/locale-provider";
import { Skeleton } from "@/components/ui/Skeleton";
import type { DashboardStats } from "@/lib/api/client";

export function MetricRibbon({
  stats,
  loading,
}: {
  stats?: DashboardStats;
  loading?: boolean;
}) {
  const { t } = useLocale();
  const items = [
    { label: t("dashboard.claims"), value: stats?.total_claims },
    { label: t("dashboard.scams"), value: stats?.total_scams },
    { label: t("dashboard.media"), value: stats?.total_media_checks },
    { label: t("dashboard.today"), value: stats?.checks_today },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 lg:gap-4">
      {items.map(({ label, value }) => (
        <div key={label} className="app-card p-5 sm:p-6">
          {loading ? (
            <Skeleton className="h-10 w-20 rounded-xl" />
          ) : (
            <p className="font-display text-4xl tracking-tight tabular-nums text-ink sm:text-5xl">
              {value ?? "—"}
            </p>
          )}
          <p className="mt-2 text-[13px] text-ink-muted">{label}</p>
        </div>
      ))}
    </div>
  );
}
