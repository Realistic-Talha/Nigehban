export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

export type CheckStatus = "processing" | "complete" | "error";
export type CheckType = "claim" | "scam_report" | "media_check";

export interface AgentTrailStep {
  agent_name: string;
  status: string;
  output_summary?: string;
  timestamp?: string;
}

export interface AuthenticityDecision {
  rule_id?: string;
  rule_label?: string;
  agreement?: "aligned" | "partial" | "conflict" | string;
  axes?: { p_ai?: number; p_edit?: number; s_cam?: number };
  axis_labels?: Record<string, string>;
  confidence_breakdown?: Array<{ step: string; value?: number; delta?: number }>;
  why?: string[];
  watermark_hit?: boolean;
  aigc_ready?: boolean;
}

export interface AuthenticityReport {
  result: string;
  confidence_band: string;
  confidence?: number | null;
  authenticity: string;
  conclusion?: string | null;
  media_url?: string | null;
  overlays?: Record<string, string>;
  overlay_guides?: Record<string, string>;
  overlay_params?: Record<string, unknown>;
  tools?: string[];
  decision?: AuthenticityDecision | null;
  analytics?: {
    aigc_components?: Record<string, unknown>;
    forensic_components?: Record<string, unknown>;
    metadata_integrity?: Record<string, unknown>;
    reliability_notes?: string[];
  } | null;
  domain_shift_warning?: boolean | null;
  metadata?: {
    exif?: Record<string, unknown>;
    iptc?: Record<string, unknown>;
    icc?: Record<string, unknown>;
    c2pa?: Record<string, unknown>;
    other?: Record<string, unknown>;
  };
  forensic_scores?: Record<string, number | null | undefined>;
}

export interface CheckDetail {
  id: string;
  type: CheckType;
  status: CheckStatus;
  verdict: string;
  confidence: number | null;
  explanation_en?: string | null;
  explanation_ur?: string | null;
  sources?: unknown[] | null;
  red_flags?: string[] | null;
  engines?: Array<{
    id: string;
    p: number;
    available?: boolean;
    abstain?: boolean;
    note?: string | null;
    evidence?: Array<{ type: string; value: string; signal: string }>;
    features?: Record<string, unknown>;
  }> | null;
  abstain?: boolean | null;
  agent_trail: AgentTrailStep[];
  created_at?: string | null;
  media_url?: string | null;
  domain_shift_warning?: boolean | null;
  authenticity_report?: AuthenticityReport | null;
}

export interface FeedItem {
  id: string;
  title: string;
  verdict: string | null;
  confidence: number | null;
  explanation_en?: string | null;
  category?: string | null;
  source_count?: number;
  created_at: string;
}

export interface DashboardStats {
  total_claims: number;
  total_scams: number;
  total_media_checks: number;
  checks_today: number;
}

export interface TrendingItem {
  id: string;
  related_entity_id: string;
  entity_type: string;
  report_volume: number;
  spread_score: number;
  captured_at: string;
  title?: string | null;
  verdict?: string | null;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  submitScam: (data: { text?: string; file?: File; language?: string }) => {
    const fd = new FormData();
    if (data.text) fd.append("text", data.text);
    if (data.file) fd.append("file", data.file);
    if (data.language) fd.append("language", data.language);
    return request<{ id: string; status: string }>("/api/v1/scamcheck/submit", {
      method: "POST",
      body: fd,
    });
  },

  submitFact: (data: { text: string; url?: string; language?: string }) =>
    request<{ id: string; status: string }>("/api/v1/factcheck/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),

  submitMedia: (data: {
    media_type: "image" | "video";
    file?: File;
    url?: string;
  }) => {
    const fd = new FormData();
    fd.append("media_type", data.media_type);
    if (data.file) fd.append("file", data.file);
    if (data.url) fd.append("url", data.url);
    return request<{ id: string; status: string }>("/api/v1/mediacheck/submit", {
      method: "POST",
      body: fd,
    });
  },

  getCheck: (id: string) => request<CheckDetail>(`/api/v1/checks/${id}`),

  getFeed: (params?: { q?: string; category?: string; limit?: number; cursor?: string }) => {
    const sp = new URLSearchParams();
    if (params?.q) sp.set("q", params.q);
    if (params?.category) sp.set("category", params.category);
    if (params?.limit) sp.set("limit", String(params.limit));
    if (params?.cursor) sp.set("cursor", params.cursor);
    const qs = sp.toString();
    return request<FeedItem[]>(`/api/v1/factcheck/feed${qs ? `?${qs}` : ""}`);
  },

  getDashboardStats: () => request<DashboardStats>("/api/v1/dashboard/stats"),

  getTrending: (window: "24h" | "7d" | "30d" = "24h") =>
    request<TrendingItem[]>(`/api/v1/dashboard/trending?window=${window}`),

  submitReport: (data: {
    text: string;
    scam_type?: string;
    sender_identifier?: string;
    description?: string;
  }) =>
    request<{ id: string; status: string }>("/api/v1/reports", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
};
