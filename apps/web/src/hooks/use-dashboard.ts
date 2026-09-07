"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { queryKeys } from "@/lib/query-keys";

export function useDashboardStats() {
  return useQuery({
    queryKey: queryKeys.dashboardStats,
    queryFn: api.getDashboardStats,
    refetchInterval: 60_000,
  });
}

export function useTrending(window: "24h" | "7d" | "30d") {
  return useQuery({
    queryKey: queryKeys.trending(window),
    queryFn: () => api.getTrending(window),
    refetchInterval: 60_000,
  });
}
