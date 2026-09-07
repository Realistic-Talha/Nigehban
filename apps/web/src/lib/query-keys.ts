export const queryKeys = {
  check: (id: string) => ["check", id] as const,
  feed: (q?: string, category?: string) => ["feed", q, category] as const,
  dashboardStats: ["dashboard", "stats"] as const,
  trending: (window: string) => ["dashboard", "trending", window] as const,
};
