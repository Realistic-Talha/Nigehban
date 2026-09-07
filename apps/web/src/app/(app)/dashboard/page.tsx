"use client";

import { useState } from "react";
import Link from "next/link";
import { useLocale } from "@/providers/locale-provider";
import { useDashboardStats, useTrending } from "@/hooks/use-dashboard";
import { useFeed } from "@/hooks/use-feed";
import { PulseHeader } from "@/components/dashboard/PulseHeader";
import { MetricRibbon } from "@/components/dashboard/MetricRibbon";
import { TrendCards } from "@/components/dashboard/TrendCards";
import { EntityBars } from "@/components/dashboard/EntityBars";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";

type Window = "24h" | "7d" | "30d";

export default function DashboardPage() {
  const { t } = useLocale();
  const [window, setWindow] = useState<Window>("24h");
  const stats = useDashboardStats();
  const trending = useTrending(window);
  const feed = useFeed();

  const entityCounts =
    trending.data?.reduce(
      (acc, item) => {
        acc[item.entity_type] = (acc[item.entity_type] ?? 0) + 1;
        return acc;
      },
      {} as Record<string, number>,
    ) ?? {};

  return (
    <div className="page-shell space-y-10">
      <PulseHeader window={window} onWindowChange={setWindow} />
      <MetricRibbon stats={stats.data} loading={stats.isLoading} />

      <div className="grid gap-8 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        <section className="space-y-4">
          <h2 className="font-display text-2xl">{t("dashboard.trending")}</h2>
          {trending.isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-28 w-full rounded-[28px]" />
              ))}
            </div>
          ) : (
            <TrendCards items={trending.data ?? []} />
          )}
        </section>
        <EntityBars counts={entityCounts} />
      </div>

      <section className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <h2 className="font-display text-2xl">{t("home.recent")}</h2>
          <Link href="/feed" className="text-sm font-semibold text-accent hover:underline">
            Open feed
          </Link>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {feed.isLoading &&
            Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-24 rounded-[28px]" />
            ))}
          {feed.data?.slice(0, 6).map((item) => (
            <Link
              key={item.id}
              href={`/v/${item.id}`}
              className="app-card p-5 transition hover:shadow-md"
            >
              <div className="flex items-start justify-between gap-2">
                <p className="line-clamp-2 text-sm font-medium">{item.title}</p>
                {item.verdict && <Badge verdict={item.verdict} />}
              </div>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
