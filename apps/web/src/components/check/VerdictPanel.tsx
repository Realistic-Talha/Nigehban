"use client";

import { Share2 } from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { ConfidenceMeter } from "@/components/ui/ConfidenceMeter";
import { Button } from "@/components/ui/Button";
import { useLocale } from "@/providers/locale-provider";
import type { CheckDetail } from "@/lib/api/client";

export function VerdictPanel({ data, checkId }: { data: CheckDetail; checkId: string }) {
  const { locale, t } = useLocale();
  const explanation =
    locale === "ur" ? data.explanation_ur ?? data.explanation_en : data.explanation_en;
  const mediaAnalytics = Boolean(data.authenticity_report);

  const share = async () => {
    const url = `${window.location.origin}/v/${checkId}`;
    if (navigator.share) {
      await navigator.share({ title: "Nigehban verdict", url, text: data.verdict });
    } else {
      await navigator.clipboard.writeText(url);
    }
  };

  return (
    <Card className="app-card space-y-5 !bg-white p-5 shadow-md sm:p-7">
      {!mediaAnalytics ? (
        <>
          <div className="flex flex-wrap items-center gap-3">
            <Badge verdict={data.verdict} />
            {data.confidence != null && (
              <span className="text-sm text-ink-muted">
                {t("check.confidence")}: {Math.round(data.confidence)}%
              </span>
            )}
          </div>
          {data.confidence != null && <ConfidenceMeter value={data.confidence} />}
          {data.abstain ? (
            <p className="text-sm text-ink-muted">
              Engines abstained or evidence was thin — treat this as provisional.
            </p>
          ) : null}
        </>
      ) : (
        <div>
          <p className="page-eyebrow">Narration</p>
          <h3 className="mt-1 font-display text-xl text-ink">Bilingual explanation</h3>
          <p className="mt-1 text-sm text-ink-muted">
            Locked by three-axis fusion — this text cannot change the verdict or confidence.
          </p>
        </div>
      )}

      {explanation && (
        <div>
          {!mediaAnalytics ? (
            <h3 className="mb-2 font-display text-xl text-ink">{t("check.explanation")}</h3>
          ) : null}
          <p className="text-sm leading-relaxed text-ink-muted">{explanation}</p>
        </div>
      )}

      {data.engines && data.engines.length > 0 && !mediaAnalytics && (
        <div>
          <h3 className="mb-2 text-sm font-semibold">Detection engines</h3>
          <ul className="space-y-2 text-sm text-ink-muted">
            {data.engines.map((e) => (
              <li
                key={e.id}
                className="flex flex-wrap items-baseline justify-between gap-2 border-b border-paper-3 pb-2"
              >
                <span className="font-medium text-ink">{e.id}</span>
                <span>
                  {e.available === false ? "offline" : `p=${(e.p * 100).toFixed(0)}%`}
                  {e.note ? ` — ${e.note}` : ""}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {data.engines && data.engines.length > 0 && mediaAnalytics && (
        <details className="rounded-lg border border-border bg-paper px-4 py-3">
          <summary className="cursor-pointer text-sm font-semibold text-ink">
            Technical engine dump
          </summary>
          <ul className="mt-3 space-y-2 text-sm text-ink-muted">
            {data.engines.map((e) => (
              <li
                key={e.id}
                className="flex flex-wrap items-baseline justify-between gap-2 border-b border-paper-3 pb-2"
              >
                <span className="font-medium text-ink">{e.id}</span>
                <span>
                  {e.available === false ? "offline" : `p=${(e.p * 100).toFixed(0)}%`}
                  {e.note ? ` — ${e.note}` : ""}
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-ink-muted">
            Raw engine probabilities are inputs to fusion — not the locked confidence score.
          </p>
        </details>
      )}

      {data.red_flags && data.red_flags.length > 0 && (
        <ul className="list-disc space-y-1 ps-5 text-sm text-danger">
          {data.red_flags.map((f, i) => (
            <li key={i}>{typeof f === "string" ? f : JSON.stringify(f)}</li>
          ))}
        </ul>
      )}

      {data.sources && Array.isArray(data.sources) && data.sources.length > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-semibold">{t("check.sources")}</h3>
          <ul className="space-y-1 text-sm">
            {(data.sources as { url?: string; title?: string }[]).map((s, i) => (
              <li key={i}>
                {s.url ? (
                  <a href={s.url} className="text-accent hover:underline" target="_blank" rel="noreferrer">
                    {s.title ?? s.url}
                  </a>
                ) : (
                  JSON.stringify(s)
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex flex-wrap gap-2 pt-2">
        <Button type="button" variant="cta" onClick={share}>
          <Share2 className="h-4 w-4" /> {t("check.share")}
        </Button>
        <Link
          href={`/v/${checkId}`}
          className="inline-flex min-h-12 items-center rounded-full px-4 text-sm font-medium text-ink-muted hover:bg-paper-3 hover:text-ink"
        >
          {t("check.verdict")}
        </Link>
      </div>
    </Card>
  );
}
