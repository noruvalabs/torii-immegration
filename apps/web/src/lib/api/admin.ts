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
    const body = await res.json().catch(() => null) as { detail?: string } | null;
    throw new Error(body?.detail ?? `Request failed (${res.status})`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ── Types ──────────────────────────────────────────────────────────────────

export type AdminUser = {
  id: number;
  email: string;
  username: string | null;
  role: string;
  is_active: boolean;
  email_verified: boolean;
};

export type AdminCase = {
  id: number;
  reference: string | null;
  status: string;
  locale: string | null;
  user_id: number;
  created_at: string | null;
  updated_at: string | null;
  applicant_email: string | null;
};

// ── Users ──────────────────────────────────────────────────────────────────

export function adminListUsers(token: string, opts?: { role?: string; offset?: number; limit?: number }) {
  const params = new URLSearchParams();
  if (opts?.role) params.set("role", opts.role);
  if (opts?.offset) params.set("offset", String(opts.offset));
  if (opts?.limit) params.set("limit", String(opts.limit));
  const qs = params.toString();
  return req<AdminUser[]>(`/admin/users${qs ? `?${qs}` : ""}`, token);
}

export function adminCountUsers(token: string) {
  return req<Record<string, number>>("/admin/users/count", token);
}

// ── Cases ──────────────────────────────────────────────────────────────────

export function adminListCases(token: string, opts?: { status?: string; offset?: number; limit?: number }) {
  const params = new URLSearchParams();
  if (opts?.status) params.set("status", opts.status);
  if (opts?.offset) params.set("offset", String(opts.offset));
  if (opts?.limit) params.set("limit", String(opts.limit));
  const qs = params.toString();
  return req<AdminCase[]>(`/admin/cases${qs ? `?${qs}` : ""}`, token);
}

export function adminCountCases(token: string) {
  return req<Record<string, number>>("/admin/cases/count", token);
}

export function adminGetCase(token: string, caseId: number) {
  return req<AdminCase>(`/admin/cases/${caseId}`, token);
}
