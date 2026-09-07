"use client";

import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import type { TrendingItem } from "@/lib/api/client";

export function TrendTable({ items }: { items: TrendingItem[] }) {
  if (items.length === 0) {
    return <p className="text-sm text-ink-muted">No trending items yet.</p>;
  }

  return (
    <Card className="overflow-x-auto p-0">
      <table className="w-full min-w-[320px] text-left text-sm">
        <thead>
          <tr className="border-b border-border bg-paper-3">
            <th className="p-3 font-medium">Title</th>
            <th className="p-3 font-medium">Type</th>
            <th className="p-3 font-medium">Score</th>
          </tr>
        </thead>
        <tbody>
          {items.map((row) => (
            <tr key={row.id} className="border-b border-border last:border-0">
              <td className="max-w-[200px] truncate p-3">{row.title ?? row.related_entity_id}</td>
              <td className="p-3 capitalize text-ink-muted">{row.entity_type.replace(/_/g, " ")}</td>
              <td className="p-3">
                {row.verdict ? <Badge verdict={row.verdict} /> : <span>{Math.round(row.spread_score)}</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}
