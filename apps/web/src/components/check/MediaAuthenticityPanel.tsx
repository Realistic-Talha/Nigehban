"use client";

import { useMemo, useState } from "react";
import { API_BASE, type AuthenticityReport } from "@/lib/api/client";
import { Card } from "@/components/ui/Card";

const OVERLAY_LABELS: Record<string, string> = {
  ela: "ELA image",
  residual_noise: "Residual noise maps",
  edge_anomaly: "Edge anomaly heat map",
  cfa: "CFA pattern analysis",
};

const DEFAULT_OVERLAY_GUIDES: Record<string, string> = {
  ela: "Bright / warm patches = different JPEG compression history (possible paste/edit). Uniform mid tones are normal.",
  residual_noise: "Warm islands = noise statistics that don't match neighbors (splice / heavy retouch).",
  edge_anomaly: "Warm = edge sharpness inconsistent with local context (not merely all edges).",
  cfa: "Warm structure = Bayer/demosaic period-2 energy. Flat/dark can mean over-smoothing or non-camera pipeline.",
};

const AXIS_META: Record<string, { label: string; hint: string; invert?: boolean }> = {
  p_ai: { label: "AI generation", hint: "Higher = more likely synthetic AI (not mere editing)" },
  p_edit: {
    label: "Edit / composite",
    hint: "Higher = post-capture edit (Lightroom etc.) or forensic edit traces",
  },
  s_cam: {
    label: "Camera authenticity",
    hint: "Higher = stronger hardware EXIF prior (editors do not erase this)",
    invert: true,
  },
};

function mediaSrc(checkId: string, artifact?: string, bust?: string | number) {
  const params = new URLSearchParams();
  if (artifact) params.set("artifact", artifact);
  if (bust != null) params.set("v", String(bust));
  const q = params.toString();
  return `${API_BASE}/api/v1/media/${checkId}${q ? `?${q}` : ""}`;
}

function pct(v: number | null | undefined) {
  if (v == null || Number.isNaN(Number(v))) return "—";
  return `${(Number(v) * 100).toFixed(0)}%`;
}

function AxisMeter({
  id,
  value,
}: {
  id: string;
  value: number | undefined;
}) {
  const meta = AXIS_META[id] || { label: id, hint: "" };
  const v = Math.max(0, Math.min(1, Number(value ?? 0)));
  const severity = meta.invert ? 1 - v : v;
  const tone =
    severity >= 0.7 ? "bg-danger" : severity >= 0.45 ? "bg-amber-600" : "bg-emerald-700";
  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline justify-between gap-2">
        <p className="text-sm font-medium text-ink">{meta.label}</p>
        <p className="font-display text-lg text-ink">{pct(v)}</p>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-paper-3">
        <div className={`h-full rounded-full ${tone}`} style={{ width: `${v * 100}%` }} />
      </div>
      <p className="text-xs text-ink-muted">{meta.hint}</p>
    </div>
  );
}

function MetaTable({ title, data }: { title: string; data: Record<string, unknown> | undefined }) {
  const entries = Object.entries(data || {}).filter(([, v]) => v != null && v !== "" && typeof v !== "object");
  const nested = Object.entries(data || {}).filter(([, v]) => v && typeof v === "object");
  if (entries.length === 0 && nested.length === 0) {
    return (
      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wide text-ink-muted">{title}</h4>
        <p className="mt-1 text-sm text-ink-muted">Not present</p>
      </div>
    );
  }
  return (
    <div>
      <h4 className="text-xs font-semibold uppercase tracking-wide text-ink-muted">{title}</h4>
      <dl className="mt-2 space-y-1.5 text-sm">
        {entries.map(([k, v]) => (
          <div key={k} className="flex justify-between gap-4 border-b border-paper-3 pb-1">
            <dt className="text-ink-muted">{k.replace(/_/g, " ")}</dt>
            <dd className="text-right font-medium text-ink">{String(v)}</dd>
          </div>
        ))}
        {nested.map(([k, v]) => (
          <div key={k} className="border-b border-paper-3 pb-1">
            <dt className="text-ink-muted">{k.replace(/_/g, " ")}</dt>
            <dd className="mt-0.5 text-xs text-ink">{JSON.stringify(v)}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function interpretForensic(key: string, v: number | null | undefined) {
  if (v == null) return "n/a";
  if (v < 0.35) return "consistent with natural capture";
  if (v < 0.55) return "mild elevation — not decisive alone";
  return "elevated — review overlay map";
}

export function MediaAuthenticityPanel({
  checkId,
  report,
}: {
  checkId: string;
  report: AuthenticityReport;
}) {
  const overlayKeys = useMemo(() => Object.keys(report.overlays || {}), [report.overlays]);
  const [active, setActive] = useState<string>(overlayKeys[0] || "ela");
  const decision = report.decision;
  const axes = decision?.axes || {};
  const analytics = report.analytics || {};
  const aigc = (analytics.aigc_components || {}) as Record<string, unknown>;
  const forensic = (analytics.forensic_components || {}) as Record<string, unknown>;
  const agreement = decision?.agreement;
  const confNum = report.confidence;

  return (
    <Card className="app-card space-y-8 !bg-white p-5 shadow-md sm:p-7">
      {/* Hero */}
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <p className="page-eyebrow">Result</p>
          {agreement === "conflict" ? (
            <span className="rounded-full border border-amber-700/40 bg-amber-50 px-2.5 py-0.5 text-xs font-semibold text-amber-900">
              Axis conflict — abstained
            </span>
          ) : null}
          {report.domain_shift_warning ? (
            <span className="rounded-full border border-border bg-paper px-2.5 py-0.5 text-xs text-ink-muted">
              Possible social recompression
            </span>
          ) : null}
        </div>
        <div className="mt-3 grid gap-3 sm:grid-cols-4">
          <div>
            <p className="text-xs uppercase tracking-wide text-ink-muted">Classification</p>
            <p className="mt-1 font-display text-2xl text-ink">{report.result}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-ink-muted">Confidence band</p>
            <p className="mt-1 font-display text-2xl text-ink">{report.confidence_band}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-ink-muted">Calibrated score</p>
            <p className="mt-1 font-display text-2xl text-ink">
              {confNum != null ? `${Math.round(confNum)}%` : "—"}
            </p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-ink-muted">Authenticity</p>
            <p className="mt-1 font-display text-2xl text-ink">{report.authenticity}</p>
          </div>
        </div>
      </div>

      {report.conclusion ? (
        <div>
          <h3 className="mb-2 font-display text-xl text-ink">Conclusion</h3>
          <p className="text-sm leading-relaxed text-ink-muted">{report.conclusion}</p>
        </div>
      ) : null}

      {/* Side-by-side original + overlay */}
      <div>
        <h3 className="mb-2 font-display text-xl text-ink">Forensic analysis overlay</h3>
        <p className="mb-3 text-sm text-ink-muted">
          Heat is blended onto the original so you can see <em>where</em> compression, noise, edge,
          or CFA structure looks inconsistent. Warm = higher anomaly; cool/dark = settled or low signal.
        </p>
        {overlayKeys.length > 0 ? (
          <div className="mb-3 flex flex-wrap gap-2">
            {overlayKeys.map((k) => (
              <button
                key={k}
                type="button"
                onClick={() => setActive(k)}
                className={`rounded-full border px-3 py-1 text-xs font-semibold transition ${
                  active === k
                    ? "border-ink bg-ink text-white"
                    : "border-border bg-paper text-ink-muted hover:border-ink/40"
                }`}
              >
                {OVERLAY_LABELS[k] || k}
              </button>
            ))}
          </div>
        ) : null}
        <div className="mb-3 flex items-center gap-3 text-xs text-ink-muted">
          <span className="font-semibold text-ink">Legend</span>
          <span className="inline-flex h-2 w-28 overflow-hidden rounded-full">
            <span className="flex-1 bg-slate-700" />
            <span className="flex-1 bg-cyan-600" />
            <span className="flex-1 bg-amber-500" />
            <span className="flex-1 bg-red-600" />
          </span>
          <span>low → high anomaly</span>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <div className="overflow-hidden rounded-lg border border-border bg-paper-2">
            <p className="border-b border-border px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-ink-muted">
              Original
            </p>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={mediaSrc(checkId, undefined, report.confidence ?? 0)}
              alt="Original upload"
              className="mx-auto max-h-[360px] w-full object-contain"
            />
          </div>
          <div className="overflow-hidden rounded-lg border border-border bg-paper-2">
            <p className="border-b border-border px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-ink-muted">
              {OVERLAY_LABELS[active] || active || "Overlay"}
            </p>
            {overlayKeys.length > 0 ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={mediaSrc(checkId, active, report.confidence ?? 0)}
                alt={OVERLAY_LABELS[active] || active}
                className="mx-auto max-h-[360px] w-full object-contain"
              />
            ) : (
              <p className="p-6 text-sm text-ink-muted">No overlay maps available</p>
            )}
          </div>
        </div>
        {(report.overlay_guides?.[active] || DEFAULT_OVERLAY_GUIDES[active]) && (
          <p className="mt-3 text-sm leading-relaxed text-ink-muted">
            <span className="font-semibold text-ink">How to read: </span>
            {report.overlay_guides?.[active] || DEFAULT_OVERLAY_GUIDES[active]}
          </p>
        )}
        {report.overlay_params?.ela_quality != null && active === "ela" ? (
          <p className="mt-1 text-xs text-ink-muted">
            ELA re-JPEG quality={String(report.overlay_params.ela_quality)}, amplify=
            {String(report.overlay_params.ela_amplify)} (FotoForensics-style).
          </p>
        ) : null}
      </div>

      {/* Three-axis analytics */}
      <div>
        <h3 className="mb-2 font-display text-xl text-ink">Three-axis analytics</h3>
        <p className="mb-4 text-sm text-ink-muted">
          Verdicts lock from agreement across axes — not from a single model score.
        </p>
        <div className="grid gap-5 sm:grid-cols-3">
          <AxisMeter id="p_ai" value={axes.p_ai} />
          <AxisMeter id="p_edit" value={axes.p_edit} />
          <AxisMeter id="s_cam" value={axes.s_cam} />
        </div>
      </div>

      {/* Decision path */}
      {decision ? (
        <div>
          <h3 className="mb-2 font-display text-xl text-ink">Decision path</h3>
          <p className="text-sm font-medium text-ink">
            {decision.rule_label || decision.rule_id || "Fusion rule"}
          </p>
          {decision.why?.length ? (
            <ul className="mt-2 list-disc space-y-1 ps-5 text-sm text-ink-muted">
              {decision.why.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          ) : null}
          {decision.confidence_breakdown?.length ? (
            <div className="mt-4">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-muted">
                Confidence breakdown
              </p>
              <ul className="space-y-1 text-sm">
                {decision.confidence_breakdown.map((row, i) => (
                  <li
                    key={`${row.step}-${i}`}
                    className="flex justify-between gap-4 border-b border-paper-3 pb-1 text-ink-muted"
                  >
                    <span>{row.step.replace(/_/g, " ")}</span>
                    <span className="font-medium text-ink">
                      {row.value != null
                        ? `${row.value}`
                        : row.delta != null
                          ? `${row.delta > 0 ? "+" : ""}${row.delta}`
                          : "—"}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}

      {/* AIGC components */}
      <div>
        <h3 className="mb-2 font-display text-xl text-ink">AIGC component breakdown</h3>
        <ul className="grid gap-2 text-sm text-ink-muted sm:grid-cols-2">
          {[
            ["Zero-shot CLIP", aigc.zeroshot],
            ["UnivFD", aigc.univfd],
            ["Fused model (pre-watermark)", aigc.fused_model],
            ["P_ai (after soft watermark)", aigc.p_ai ?? aigc.p_after_wm],
          ].map(([label, val]) => (
            <li key={String(label)} className="flex justify-between border-b border-paper-3 pb-1">
              <span>{label}</span>
              <span className="font-medium text-ink">
                {val == null ? "—" : pct(Number(val))}
              </span>
            </li>
          ))}
        </ul>
        {aigc.watermark && typeof aigc.watermark === "object" ? (
          <p className="mt-2 text-xs text-ink-muted">
            Watermark:{" "}
            {Boolean((aigc.watermark as { hit?: boolean }).hit)
              ? `hit (score=${Number((aigc.watermark as { score?: number }).score ?? 0).toFixed(2)}) — soft boost only`
              : "not detected"}
          </p>
        ) : null}
      </div>

      {/* Classical forensics */}
      <div>
        <h3 className="mb-2 font-display text-xl text-ink">Classical forensics</h3>
        <ul className="space-y-2 text-sm">
          {(
            [
              ["ela", "ELA", forensic.ela ?? report.forensic_scores?.ela],
              ["residual_noise", "Residual noise", forensic.residual_noise ?? report.forensic_scores?.residual_noise],
              ["edge_anomaly", "Edge anomaly", forensic.edge_anomaly ?? report.forensic_scores?.edge_anomaly],
              ["cfa", "CFA", forensic.cfa ?? report.forensic_scores?.cfa],
            ] as Array<[string, string, unknown]>
          ).map(([key, label, val]) => (
            <li key={key} className="flex flex-wrap items-baseline justify-between gap-2 border-b border-paper-3 pb-2">
              <span className="font-medium text-ink">{label}</span>
              <span className="text-ink-muted">
                {pct(val as number)} — {interpretForensic(key, val as number)}
              </span>
            </li>
          ))}
        </ul>
      </div>

      {report.tools?.length ? (
        <div>
          <h3 className="mb-2 text-sm font-semibold text-ink">Tools used</h3>
          <ul className="flex flex-wrap gap-2">
            {report.tools.map((t) => (
              <li key={t} className="rounded-full border border-border bg-paper px-3 py-1 text-xs text-ink-muted">
                {t}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div>
        <h3 className="mb-3 font-display text-xl text-ink">Image metadata</h3>
        <div className="grid gap-5 sm:grid-cols-2">
          <MetaTable title="EXIF" data={report.metadata?.exif as Record<string, unknown>} />
          <MetaTable title="IPTC" data={report.metadata?.iptc as Record<string, unknown>} />
          <MetaTable title="ICC Profile" data={report.metadata?.icc as Record<string, unknown>} />
          <MetaTable title="C2PA" data={report.metadata?.c2pa as Record<string, unknown>} />
          <MetaTable title="Other" data={report.metadata?.other as Record<string, unknown>} />
        </div>
      </div>

      {(analytics.reliability_notes?.length || report.domain_shift_warning) && (
        <div>
          <h3 className="mb-2 font-display text-xl text-ink">Reliability & limits</h3>
          <ul className="list-disc space-y-1 ps-5 text-sm text-ink-muted">
            {(analytics.reliability_notes || []).map((n) => (
              <li key={n}>{n}</li>
            ))}
            {report.domain_shift_warning ? (
              <li>Social-media recompression may strip EXIF and weaken classical forensics.</li>
            ) : null}
          </ul>
        </div>
      )}
    </Card>
  );
}
