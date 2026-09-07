"use client";

import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import type { TrendingItem } from "@/lib/api/client";

export function TrendCards({ items }: { items: TrendingItem[] }) {
  if (items.length === 0) {
    return (
      <p className="app-card p-8 text-sm text-ink-muted">
        No trending items yet for this window.
      </p>
    );
  }

  return (
    <ul className="space-y-3">
      {items.map((row) => {
        const score = Math.max(0, Math.min(100, row.spread_score ?? 0));
        return (
          <li key={row.id}>
            <Link
              href={`/v/${row.related_entity_id}`}
              className="app-card block p-5 transition hover:-translate-y-0.5 hover:shadow-md"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate font-medium text-ink">
                    {row.title ?? row.related_entity_id}
                  </p>
                  <p className="mt-1 text-xs capitalize text-ink-subtle">
                    {row.entity_type.replace(/_/g, " ")}
                  </p>
                </div>
                {row.verdict && <Badge verdict={row.verdict} />}
              </div>
              <div className="mt-3">
                <div className="mb-1 flex justify-between text-xs text-ink-subtle">
                  <span>Spread</span>
                  <span>{Math.round(score)}</span>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-paper-3">
                  <div
                    className="h-full rounded-full bg-accent transition-[width] duration-normal"
                    style={{ width: `${score}%` }}
                  />
                </div>
              </div>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
