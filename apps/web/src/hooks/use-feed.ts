"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { queryKeys } from "@/lib/query-keys";

export function useFeed(q?: string, category?: string) {
  return useQuery({
    queryKey: queryKeys.feed(q, category),
    queryFn: () => api.getFeed({ q, category, limit: 30 }),
    refetchInterval: 30_000,
  });
}
