"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/Card";
import { SubmitPanel } from "@/components/check/SubmitPanel";
import { PipelineSteps } from "@/components/check/PipelineSteps";
import { getStepsForKind, useCheckSubmit } from "@/hooks/use-check-submit";
import { VerdictPanel } from "@/components/check/VerdictPanel";
import { Button } from "@/components/ui/Button";
import { useLocale } from "@/providers/locale-provider";

const EXAMPLES = [
  "SBP approved your loan. Send OTP to release funds.",
  "Work from home — earn 80,000 PKR. Pay registration fee first.",
  "Your SIM will be blocked in 24 hours. Verify via this link.",
];

export default function ScamCheckPage() {
  const { t, locale } = useLocale();
  const { submit, stepStatus, poll, reset, isProcessing, error, checkId, done } = useCheckSubmit("scam");
  const [showResult, setShowResult] = useState(false);

  useEffect(() => {
    if (done) setShowResult(true);
  }, [done]);

  const handleSubmit = async (data: { text?: string; file?: File }) => {
    setShowResult(false);
    await submit({ ...data, language: locale });
  };

  return (
    <div className="page-shell max-w-2xl space-y-8">
      <div>
        <p className="page-eyebrow">Scam</p>
        <h1 className="page-title mt-2">{t("home.scamTitle")}</h1>
        <p className="mt-2 text-[15px] text-ink-muted">{t("home.scamDesc")}</p>
      </div>

      {!showResult ? (
        <>
          <Card className="app-card !bg-white p-5 sm:p-7">
            <SubmitPanel mode="both" onSubmit={handleSubmit} isProcessing={isProcessing} />
          </Card>
          <div className="space-y-3">
            <p className="page-eyebrow">{t("check.examples")}</p>
            <div className="flex flex-wrap gap-2">
              {EXAMPLES.map((ex) => (
                <button
                  key={ex}
                  type="button"
                  className="min-h-11 rounded-full border border-border bg-white px-4 py-2 text-left text-xs text-ink-muted transition hover:border-accent hover:text-ink"
                  onClick={() => handleSubmit({ text: ex })}
                >
                  {ex.slice(0, 48)}…
                </button>
              ))}
            </div>
          </div>
        </>
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
          <PipelineSteps steps={getStepsForKind("scam")} stepStatus={stepStatus} />
        </div>
      )}
      {error && <p className="text-sm text-danger">{error}</p>}
    </div>
  );
}
