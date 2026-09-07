"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type CheckDetail } from "@/lib/api/client";
import { queryKeys } from "@/lib/query-keys";
import { API_BASE } from "@/lib/api/client";

export type CheckKind = "scam" | "fact" | "media";

export interface PipelineEvent {
  agent_name?: string;
  status?: string;
  output_summary?: string;
}

const SCAM_STEPS = ["intake", "detection_kernel", "url_lgbm", "text_scam", "rules_pk", "meta_learner", "narrate", "pipeline"];
const FACT_STEPS = ["intake", "detection_kernel", "fact_nli", "meta_learner", "narrate", "pipeline"];
const MEDIA_STEPS = ["intake", "detection_kernel", "metadata", "forensics_ela", "aigc", "provenance", "meta_learner", "narrate", "pipeline"];

export function getStepsForKind(kind: CheckKind) {
  if (kind === "scam") return SCAM_STEPS;
  if (kind === "fact") return FACT_STEPS;
  return MEDIA_STEPS;
}

export function useCheckSubmit(kind: CheckKind) {
  const [checkId, setCheckId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [stepStatus, setStepStatus] = useState<Record<string, string>>({});

  const submit = useCallback(
    async (payload: { text?: string; file?: File; url?: string; media_type?: "image" | "video"; language?: string }) => {
      setError(null);
      setStepStatus({});
      try {
        let id: string;
        if (kind === "scam") {
          const res = await api.submitScam({ text: payload.text, file: payload.file, language: payload.language });
          id = res.id;
        } else if (kind === "fact") {
          if (!payload.text?.trim()) throw new Error("Text required");
          const res = await api.submitFact({ text: payload.text, url: payload.url, language: payload.language });
          id = res.id;
        } else {
          const res = await api.submitMedia({
            media_type: payload.media_type ?? "image",
            file: payload.file,
            url: payload.url,
          });
          id = res.id;
        }
        setCheckId(id);
        return id;
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Submit failed";
        setError(msg);
        throw e;
      }
    },
    [kind],
  );

  useEffect(() => {
    if (!checkId || typeof EventSource === "undefined") return;
    const es = new EventSource(`${API_BASE}/api/v1/checks/${checkId}/stream`);
    es.onmessage = (msg) => {
      try {
        const data = JSON.parse(msg.data) as PipelineEvent;
        if (data.agent_name && data.status) {
          setStepStatus((prev) => ({ ...prev, [data.agent_name!]: data.status! }));
        }
        // Kernel finishes with pipeline_complete — stop waiting on legacy "judge"
        if (data.agent_name === "pipeline" && data.status === "pipeline_complete") {
          es.close();
        }
      } catch {
        /* ignore */
      }
    };
    es.onerror = () => {
      es.close();
    };
    return () => es.close();
  }, [checkId]);

  const poll = useQuery({
    queryKey: queryKeys.check(checkId ?? ""),
    queryFn: () => api.getCheck(checkId!),
    enabled: !!checkId,
    refetchInterval: (q) => {
      const d = q.state.data as CheckDetail | undefined;
      if (d?.status === "complete" || d?.status === "error") return false;
      return 1500;
    },
  });

  // Backfill step chips from agent_trail when SSE events were missed
  useEffect(() => {
    const trail = poll.data?.agent_trail;
    if (!trail?.length) return;
    setStepStatus((prev) => {
      const next = { ...prev };
      for (const step of trail) {
        if (step.agent_name) next[step.agent_name] = step.status || "complete";
      }
      if (poll.data?.status === "complete" || poll.data?.status === "error") {
        next.pipeline = "pipeline_complete";
      }
      return next;
    });
  }, [poll.data?.agent_trail, poll.data?.status]);

  const reset = useCallback(() => {
    setCheckId(null);
    setError(null);
    setStepStatus({});
  }, []);

  const done = poll.data?.status === "complete" || poll.data?.status === "error";
  // From submit until terminal status (including before first poll) — keep UI in analyzing mode
  const isProcessing = !!checkId && !done;

  return { checkId, submit, error, stepStatus, poll, reset, isProcessing, done };
}
