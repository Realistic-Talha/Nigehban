"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api/client";
import { queryKeys } from "@/lib/query-keys";
import { VerdictPanel } from "@/components/check/VerdictPanel";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { Button } from "@/components/ui/Button";
import { useLocale } from "@/providers/locale-provider";
import { formatDate } from "@/lib/utils";

export default function VerdictPage() {
  const { id } = useParams<{ id: string }>();
  const { locale } = useLocale();
  const { data, isLoading, error } = useQuery({
    queryKey: queryKeys.check(id),
    queryFn: () => api.getCheck(id),
    refetchInterval: (q) => (q.state.data?.status === "processing" ? 2000 : false),
  });

  if (isLoading) {
    return (
      <div className="page-shell max-w-2xl space-y-4">
        <Skeleton className="h-10 w-48 rounded-full" />
        <Skeleton className="h-48 rounded-[28px]" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="page-shell max-w-2xl space-y-4">
        <p className="text-danger">Check not found.</p>
        <Link href="/">
          <Button variant="secondary">Home</Button>
        </Link>
      </div>
    );
  }

  if (data.status === "processing") {
    return (
      <div className="page-shell max-w-2xl space-y-4">
        <Badge verdict="unverified" />
        <p className="text-ink-muted">Analysis in progress…</p>
        <Skeleton className="h-32 rounded-[28px]" />
      </div>
    );
  }

  return (
    <div className="page-shell max-w-2xl space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="page-eyebrow">{data.type.replace(/_/g, " ")}</span>
        {data.created_at && (
          <span className="text-xs text-ink-subtle">{formatDate(data.created_at, locale)}</span>
        )}
      </div>

      <VerdictPanel data={data} checkId={id} />

      {data.agent_trail.length > 0 && (
        <section className="app-card space-y-4 p-6 sm:p-7">
          <h2 className="font-display text-2xl">Agent trail</h2>
          <ol className="space-y-4 border-s-2 border-border ps-5">
            {data.agent_trail.map((step, i) => (
              <li key={i} className="text-sm">
                <span className="font-semibold capitalize text-ink">
                  {step.agent_name.replace(/_/g, " ")}
                </span>
                {step.output_summary && (
                  <p className="mt-1 text-ink-muted">{step.output_summary}</p>
                )}
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}
