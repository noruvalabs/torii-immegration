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

// ── Scope Details & Intake/PDF Editor API ──────────────────────────────────────

const OPS_API = "/backend/v1/admin/ops";

export type IntakeQuestion = {
  key: string;
  section?: string;
  prompt: string;
  prompt_ja?: string;
  type: "string" | "text" | "enum" | "date" | "integer" | "boolean";
  options?: string[];
  min_length?: number;
  max_length?: number;
  min_value?: number;
  max_value?: number;
  required?: boolean;
  citation?: Citation;
};

export type DocumentRequirement = {
  code: string;
  name: string | { en: string; ja?: string };
  is_required?: boolean;
  how_to_obtain?: string | { en: string; ja?: string };
  why_required?: string | { en: string; ja?: string };
  citation?: Citation;
  show_when?: Record<string, unknown>;
};

export type FormTemplateDetail = {
  id?: number;
  code: string;
  version: string;
  official_title: string;
  citation?: Citation;
  field_mappings?: { form_field: string; answer_key: string; required?: boolean }[];
  is_live?: boolean;
  has_pdf?: boolean;
  pdf_filename?: string | null;
  pdf_filesize?: number | null;
  pdf_pages?: number | null;
  pdf_sha256?: string | null;
  pdf_uploaded_at?: string | null;
  detected_fields?: string[];
  download_url?: string | null;
  jurisdiction_code?: string | null;
  jurisdiction_name?: string | null;
  visa_category_code?: string | null;
  visa_category_name?: string | null;
  action_code?: string | null;
  action_name?: string | null;
};

export type EligibilityRule = {
  key: string;
  operator: "in" | "min" | "max" | "equals" | "not_equals";
  value: unknown;
  failure_status?: "at_risk" | "ineligible";
  message?: string;
  citation?: Citation;
};

export type AdminScopeDetails = {
  jurisdiction: { id: number; code: string; name: string };
  visa_category: {
    id: number;
    code: string;
    name: string;
    description?: string;
    is_enabled: boolean;
    is_live: boolean;
    citation?: Citation;
  };
  case_action: {
    id: number;
    code: string;
    name: string;
    description?: string;
    is_enabled: boolean;
  } | null;
  available_actions: {
    id: number;
    code: string;
    name: string;
    description?: string;
    is_enabled: boolean;
  }[];
  intake_questions: IntakeQuestion[];
  document_requirements: DocumentRequirement[];
  form_templates: FormTemplateDetail[];
  eligibility_rules: EligibilityRule[];
};

export type ScopeDetailUpdatePayload = {
  jurisdiction_code: string;
  visa_category_code: string;
  action_code: string;
  category_name?: string;
  category_description?: string;
  is_enabled?: boolean;
  intake_questions?: IntakeQuestion[];
  document_requirements?: DocumentRequirement[];
  form_templates?: FormTemplateDetail[];
  eligibility_rules?: EligibilityRule[];
};

export async function fetchScopeDetails(
  token: string | null,
  jurisdictionCode: string,
  visaCategoryCode: string,
  actionCode?: string,
): Promise<AdminScopeDetails> {
  const qs = new URLSearchParams({
    jurisdiction_code: jurisdictionCode,
    visa_category_code: visaCategoryCode,
  });
  if (actionCode) qs.set("action_code", actionCode);

  const res = await fetch(`${OPS_API}/scope-details?${qs.toString()}`, {
    cache: "no-store",
    headers: authHeaders(token),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(formatApiDetail(body?.detail) || `Failed to fetch scope details (${res.status})`);
  }
  return res.json();
}

export async function updateScopeDetails(
  token: string | null,
  payload: ScopeDetailUpdatePayload,
): Promise<AdminScopeDetails> {
  const res = await fetch(`${OPS_API}/scope-details`, {
    method: "PUT",
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(formatApiDetail(body?.detail) || `Failed to save scope details (${res.status})`);
  }
  return res.json();
}

export async function uploadFormTemplatePdf(
  token: string | null,
  code: string,
  file: File,
  scope?: {
    jurisdiction_code?: string;
    visa_category_code?: string;
    action_code?: string;
  },
): Promise<{
  success: boolean;
  code: string;
  filename: string;
  filesize: number;
  pages: number;
  sha256: string;
  detected_fields: string[];
  download_url: string;
  message: string;
}> {
  const formData = new FormData();
  formData.append("file", file);

  const qs = new URLSearchParams();
  if (scope?.jurisdiction_code) qs.set("jurisdiction_code", scope.jurisdiction_code);
  if (scope?.visa_category_code) qs.set("visa_category_code", scope.visa_category_code);
  if (scope?.action_code) qs.set("action_code", scope.action_code);

  const url = `${OPS_API}/form-templates/${encodeURIComponent(code)}/upload-pdf${qs.toString() ? `?${qs.toString()}` : ""}`;
  const res = await fetch(url, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(formatApiDetail(body?.detail) || `Failed to upload PDF template (${res.status})`);
  }
  return res.json();
}

export async function listAllFormTemplates(
  token: string | null,
): Promise<FormTemplateDetail[]> {
  const res = await fetch(`${OPS_API}/form-templates`, {
    cache: "no-store",
    headers: authHeaders(token),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(formatApiDetail(body?.detail) || `Failed to fetch form templates (${res.status})`);
  }
  return res.json();
}


