import { formatApiDetail } from "./errors";

const API = "/backend/v1";

function authHeaders(token: string | null): Record<string, string> {
  const h: Record<string, string> = { "content-type": "application/json" };
  if (token) h.Authorization = `Bearer ${token}`;
  return h;
}

export type CorridorCheckIn = {
  destination_code: string;
  purpose_code: string;
  action_code: string;
  nationality?: string | null;
  residence_country?: string | null;
  force_refresh?: boolean;
};

export type Citation = {
  authority?: string;
  title?: string;
  url: string;
  source_version?: string;
};

export type AdmissionData = {
  visa_required?: boolean | null;
  route?: string | null;
  max_stay_days?: number | null;
  citation?: Citation;
};

export type FilingChannelData = {
  channel?: string | null;
  filer?: string | null;
  mission_name?: string | null;
  mission_url?: string | null;
  directory_url?: string | null;
  citation?: Citation;
};

export type ProcessStep = {
  order: number;
  title: string;
  detail: string;
};

export type ProcessData = {
  steps?: ProcessStep[];
  processing_time_days_min?: number | null;
  processing_time_days_max?: number | null;
  citation?: Citation;
};

export type FeeItem = {
  code?: string;
  amount?: number | null;
  currency?: string;
  citation?: Citation;
};

export type FaqItem = {
  question: string;
  answer: string;
  citation?: Citation;
};

export type CorridorItems = {
  admission?: AdmissionData;
  filing_channel?: FilingChannelData;
  process?: ProcessData;
  fees?: FeeItem[];
  faq?: FaqItem[];
};

export type SourcePage = {
  url: string;
  title?: string;
  retrieved_at?: string;
};

export type CorridorCheckOut = {
  id: number;
  status: "completed" | "queued" | "running" | "failed" | "stale";
  items: CorridorItems;
  source_pages: SourcePage[];
  researched_at?: string | null;
  expires_at?: string | null;
  review_required?: boolean;
  verification_status?: "verified" | "needs_review" | "unverified" | "failed" | string;
  retrieval_status?: "direct_scrape" | "search_snippet_fallback" | "insufficient" | "failed" | string;
  source_domains?: string[];
  error_diagnostics?: string | null;
  failure_reason?: string | null;
};

export async function checkCorridor(
  payload: CorridorCheckIn,
  token?: string | null,
): Promise<CorridorCheckOut> {
  const res = await fetch(`${API}/corridors/check`, {
    method: "POST",
    headers: authHeaders(token || null),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { detail?: unknown } | null;
    throw new Error(formatApiDetail(body?.detail) || `Corridor check failed (${res.status})`);
  }
  return (await res.json()) as CorridorCheckOut;
}

export async function getCorridor(
  corridorId: number,
  token?: string | null,
): Promise<CorridorCheckOut> {
  const res = await fetch(`${API}/corridors/${corridorId}`, {
    method: "GET",
    headers: authHeaders(token || null),
  });
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { detail?: unknown } | null;
    throw new Error(formatApiDetail(body?.detail) || `Get corridor failed (${res.status})`);
  }
  return (await res.json()) as CorridorCheckOut;
}
