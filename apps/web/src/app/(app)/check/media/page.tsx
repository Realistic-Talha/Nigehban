"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/Card";
import { SubmitPanel } from "@/components/check/SubmitPanel";
import { PipelineSteps } from "@/components/check/PipelineSteps";
import { getStepsForKind, useCheckSubmit } from "@/hooks/use-check-submit";
import { VerdictPanel } from "@/components/check/VerdictPanel";
import { MediaAuthenticityPanel } from "@/components/check/MediaAuthenticityPanel";
import { Button } from "@/components/ui/Button";
import { useLocale } from "@/providers/locale-provider";

export default function MediaCheckPage() {
  const { t } = useLocale();
  const { submit, stepStatus, poll, reset, isProcessing, error, checkId, done } = useCheckSubmit("media");
  const [showResult, setShowResult] = useState(false);

  useEffect(() => {
    if (done) setShowResult(true);
  }, [done]);

  const handleSubmit = async (data: { file?: File; url?: string }) => {
    setShowResult(false);
    const media_type = data.file?.type.startsWith("video/") ? "video" : "image";
    await submit({ file: data.file, url: data.url, media_type });
  };

  return (
    <div className={`page-shell space-y-8 ${showResult ? "max-w-5xl" : "max-w-3xl"}`}>
      <div>
        <p className="page-eyebrow">Media</p>
        <h1 className="page-title mt-2">{t("home.mediaTitle")}</h1>
        <p className="mt-2 text-[15px] text-ink-muted">{t("home.mediaDesc")}</p>
      </div>

      {!showResult ? (
        <Card className="app-card !bg-white p-5 sm:p-7">
          <SubmitPanel mode="both" acceptUrl onSubmit={handleSubmit} isProcessing={isProcessing} />
        </Card>
      ) : poll.data && checkId ? (
        <>
          {poll.data.authenticity_report ? (
            <MediaAuthenticityPanel checkId={checkId} report={poll.data.authenticity_report} />
          ) : null}
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
          <PipelineSteps steps={getStepsForKind("media")} stepStatus={stepStatus} />
        </div>
      )}
      {error && <p className="text-sm text-danger">{error}</p>}
    </div>
  );
}
