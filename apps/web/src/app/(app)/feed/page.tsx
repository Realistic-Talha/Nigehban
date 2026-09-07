"use client";

import { useEffect, useState } from "react";
import { useLocale } from "@/providers/locale-provider";
import { useFeed } from "@/hooks/use-feed";
import { Input } from "@/components/ui/Input";
import { FeedRow } from "@/components/feed/FeedRow";
import { Skeleton } from "@/components/ui/Skeleton";

const CATEGORIES = ["all", "politics", "health", "finance", "disaster", "celebrity", "other"];

export default function FeedPage() {
  const { t } = useLocale();
  const [q, setQ] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [category, setCategory] = useState("all");

  useEffect(() => {
    const id = setTimeout(() => setDebouncedQ(q), 300);
    return () => clearTimeout(id);
  }, [q]);

  const { data, isLoading } = useFeed(
    debouncedQ || undefined,
    category === "all" ? undefined : category,
  );

  return (
    <div className="page-shell max-w-3xl space-y-8">
      <div>
        <p className="page-eyebrow">Live</p>
        <h1 className="page-title mt-2">{t("feed.title")}</h1>
      </div>

      <Input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder={t("feed.search")}
        aria-label="Search feed"
      />

      <div className="flex flex-wrap gap-2">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            type="button"
            onClick={() => setCategory(cat)}
            className={`min-h-10 rounded-full border px-4 text-[13px] font-medium capitalize transition ${
              category === cat
                ? "border-ink bg-ink text-paper"
                : "border-border bg-white text-ink-muted hover:text-ink"
            }`}
          >
            {cat === "all" ? t("feed.all") : cat}
          </button>
        ))}
      </div>

      <div className="space-y-3">
        {isLoading &&
          Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-[28px]" />
          ))}
        {data?.map((item) => (
          <FeedRow key={item.id} item={item} />
        ))}
        {!isLoading && data?.length === 0 && (
          <p className="app-card p-6 text-sm text-ink-muted">
            No claims yet. Seed data or run a fact check.
          </p>
        )}
      </div>
    </div>
  );
}
