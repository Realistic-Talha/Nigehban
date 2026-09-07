"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/Card";
import { SubmitPanel } from "@/components/check/SubmitPanel";
import { PipelineSteps } from "@/components/check/PipelineSteps";
import { getStepsForKind, useCheckSubmit } from "@/hooks/use-check-submit";
import { VerdictPanel } from "@/components/check/VerdictPanel";
import { Button } from "@/components/ui/Button";
import { useLocale } from "@/providers/locale-provider";

export default function FactCheckPage() {
  const { t, locale } = useLocale();
  const { submit, stepStatus, poll, reset, isProcessing, error, checkId, done } = useCheckSubmit("fact");
  const [showResult, setShowResult] = useState(false);

  useEffect(() => {
    if (done) setShowResult(true);
  }, [done]);

  const handleSubmit = async (data: { text?: string; url?: string }) => {
    setShowResult(false);
    await submit({ text: data.text, url: data.url, language: locale });
  };

  return (
    <div className="page-shell max-w-2xl space-y-8">
      <div>
        <p className="page-eyebrow">Fact</p>
        <h1 className="page-title mt-2">{t("home.factTitle")}</h1>
        <p className="mt-2 text-[15px] text-ink-muted">{t("home.factDesc")}</p>
      </div>

      {!showResult ? (
        <Card className="app-card !bg-white p-5 sm:p-7">
          <SubmitPanel mode="text" acceptUrl onSubmit={handleSubmit} isProcessing={isProcessing} />
        </Card>
      ) : poll.data && checkId ? (
        <>
          <VerdictPanel data={poll.data} checkId={checkId} />
          <Button
            variant="secondary"
            onClick={() => {
              reset();
              setShowResult(false);
            }}
          >
            {t("check.again")}
          </Button>
        </>
      ) : null}

      {isProcessing && (
        <div className="space-y-3">
          <p className="text-sm font-medium text-ink-muted">{t("check.processing")}</p>
          <PipelineSteps steps={getStepsForKind("fact")} stepStatus={stepStatus} />
        </div>
      )}
      {error && <p className="text-sm text-danger">{error}</p>}
    </div>
  );
}
