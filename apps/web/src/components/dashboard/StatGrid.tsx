"use client";

import { useLocale } from "@/providers/locale-provider";
import { Card } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import type { DashboardStats } from "@/lib/api/client";

export function StatGrid({ stats, loading }: { stats?: DashboardStats; loading?: boolean }) {
  const { t } = useLocale();
  const items = [
    { label: t("dashboard.claims"), value: stats?.total_claims },
    { label: t("dashboard.scams"), value: stats?.total_scams },
    { label: t("dashboard.media"), value: stats?.total_media_checks },
    { label: t("dashboard.today"), value: stats?.checks_today },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 sm:gap-4">
      {items.map(({ label, value }) => (
        <Card key={label} className="p-4">
          {loading ? (
            <Skeleton className="h-8 w-16" />
          ) : (
            <p className="text-2xl font-semibold tabular-nums text-ink">{value ?? "—"}</p>
          )}
          <p className="mt-1 text-xs text-ink-muted">{label}</p>
        </Card>
      ))}
    </div>
  );
}
