"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { useLocale } from "@/providers/locale-provider";
import { Badge } from "@/components/ui/Badge";
import { formatDate } from "@/lib/utils";
import type { FeedItem } from "@/lib/api/client";

export function FeedRow({ item }: { item: FeedItem }) {
  const { locale } = useLocale();
  const reduce = useReducedMotion();

  return (
    <motion.div whileHover={reduce ? undefined : { y: -4 }} transition={{ duration: 0.25 }}>
      <Link href={`/v/${item.id}`} className="app-card block p-5 transition hover:shadow-md">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <h3 className="min-w-0 flex-1 font-display text-xl text-ink">{item.title}</h3>
          {item.verdict && <Badge verdict={item.verdict} />}
        </div>
        <p className="mt-2 line-clamp-2 text-sm text-ink-muted">{item.explanation_en}</p>
        <p className="mt-3 text-xs text-ink-subtle">{formatDate(item.created_at, locale)}</p>
      </Link>
    </motion.div>
  );
}
