import { formatApiDetail } from "./errors";

const API = "/backend/v1/jurisdictions";

function authHeaders(token: string | null): Record<string, string> {
  const h: Record<string, string> = { "content-type": "application/json" };
  if (token) h.Authorization = `Bearer ${token}`;
  return h;
}

async function req<T>(path: string, token: string | null, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    cache: "no-store",
    ...init,
    headers: { ...authHeaders(token), ...init?.headers },
  });
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { detail?: unknown } | null;
    throw new Error(formatApiDetail(body?.detail) || `Request failed (${res.status})`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ── Types ──────────────────────────────────────────────────────────────────────

export type Citation = { authority?: string; title?: string; url?: string };

export type AdminJurisdiction = {
  id: number;
  code: string;
  name: string;
  /** A seeded content pack backs this country. Owned by `docs/jurisdictions`, not by ops. */
  is_live: boolean;
  /** Ops' own switch. Survives a reseed, and decides whether applicants see the country. */
  is_enabled: boolean;
};

/** A visa route or an application procedure — the two tables carry the same shape. */
export type Scope = {
  id: number;
  jurisdiction_id: number;
  code: string;
  name: string;
  is_live: boolean;
  is_enabled: boolean;
  research_enabled: boolean;
  description: string;
  /** "pack" (seeded), "discovered" (read off an official page), or "manual" (typed in). */
  source: string;
  citation: Citation;
};

export type ScopeKind = "visa-categories" | "case-actions";

export type DiscoveredScope = {
  code: string;
  name: string;
  description: string;
  citation: Citation;
  outcome: "created" | "enriched" | "unchanged";
};

export type Discovery = {
  jurisdiction_code: string;
  visa_categories: DiscoveredScope[];
  case_actions: DiscoveredScope[];
  source_pages: { url?: string; retrieved_at?: string }[];
  discovered_at: string;
  created: number;
  message: string;
};

export type ScopeCreate = {
  code: string;
  name: string;
  description?: string;
  is_enabled?: boolean;
  research_enabled?: boolean;
};

export type ScopePatch = {
  name?: string;
  description?: string;
  is_enabled?: boolean;
  research_enabled?: boolean;
};

// ── Countries ──────────────────────────────────────────────────────────────────

export function listJurisdictions(token: string | null) {
  return req<AdminJurisdiction[]>("", token);
}

export function createJurisdiction(
  token: string | null,
  data: { code: string; name: string; is_live?: boolean; is_enabled?: boolean },
) {
  return req<AdminJurisdiction>("", token, { method: "POST", body: JSON.stringify(data) });
}

export function updateJurisdiction(
  token: string | null,
  id: number,
  data: { name?: string; is_live?: boolean; is_enabled?: boolean },
) {
  return req<AdminJurisdiction>(`/${id}`, token, { method: "PATCH", body: JSON.stringify(data) });
}

export function deleteJurisdiction(token: string | null, id: number) {
  return req<void>(`/${id}`, token, { method: "DELETE" });
}

/**
 * Read a country's own immigration pages and record the routes it publishes.
 *
 * Slow by nature — it searches, fetches several government pages and runs one extraction
 * pass — and everything it writes arrives switched off, awaiting a decision here.
 */
export function discoverScopes(token: string | null, id: number, originCountry?: string) {
  const qs = originCountry ? `?origin_country=${encodeURIComponent(originCountry)}` : "";
  return req<Discovery>(`/${id}/discover${qs}`, token, { method: "POST" });
}

// ── Routes and procedures ──────────────────────────────────────────────────────

export function listScopes(token: string | null, id: number, kind: ScopeKind) {
  return req<Scope[]>(`/${id}/${kind}`, token);
}

export function createScope(
  token: string | null,
  id: number,
  kind: ScopeKind,
  data: ScopeCreate,
) {
  return req<Scope>(`/${id}/${kind}`, token, { method: "POST", body: JSON.stringify(data) });
}

export function updateScope(
  token: string | null,
  id: number,
  kind: ScopeKind,
  scopeId: number,
  data: ScopePatch,
) {
  return req<Scope>(`/${id}/${kind}/${scopeId}`, token, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function deleteScope(token: string | null, id: number, kind: ScopeKind, scopeId: number) {
  return req<void>(`/${id}/${kind}/${scopeId}`, token, { method: "DELETE" });
}
