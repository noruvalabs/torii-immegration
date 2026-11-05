import { formatApiDetail } from "./errors";

const API = "/backend/v1";

function authHeaders(token: string | null): Record<string, string> {
  const h: Record<string, string> = { "content-type": "application/json" };
  if (token) h.Authorization = `Bearer ${token}`;
  return h;
}

async function req<T>(path: string, token: string | null, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: { ...authHeaders(token), ...init?.headers },
  });
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { detail?: unknown } | null;
    throw new Error(formatApiDetail(body?.detail) || `Request failed (${res.status})`);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export type JobStep = {
  step: string;
  label: string;
  detail: string;
  timestamp: string;
};

export type PortalJob = {
  id: number;
  case_id: number;
  jurisdiction_code: string;
  portal_name: string;
  portal_url: string;
  status: string;
  attempt_count: number;
  portal_reference?: string | null;
  receipt_url?: string | null;
  screenshot_url?: string | null;
  error_message?: string | null;
  steps_log: JobStep[];
  proxy_used?: string | null;
  captcha_solved: boolean;
  dispatched_at?: string | null;
  completed_at?: string | null;
};

export function dispatchPortalBot(token: string | null, caseId: number): Promise<PortalJob> {
  return req<PortalJob>(`/cases/${caseId}/portal-bot/dispatch`, token, {
    method: "POST",
  });
}

export function getLatestPortalJob(token: string | null, caseId: number): Promise<PortalJob | null> {
  return req<PortalJob | null>(`/cases/${caseId}/portal-bot/latest`, token);
}

export function getAdminPortalJobs(token: string | null, limit = 50): Promise<PortalJob[]> {
  return req<PortalJob[]>(`/admin/portal-bot/jobs?limit=${limit}`, token);
}

export function submitPortalOtp(
  token: string | null,
  caseId: number,
  otpCode: string
): Promise<PortalJob> {
  return req<PortalJob>(`/cases/${caseId}/portal-bot/otp`, token, {
    method: "POST",
    body: JSON.stringify({ otp_code: otpCode }),
  });
}


