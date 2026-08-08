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
  return res.json() as Promise<T>;
}

// ── Types ──────────────────────────────────────────────────────────────────────

export type Jurisdiction = { id: number; code: string; name: string; is_live: boolean };
export type VisaCategory = { id: number; jurisdiction_id: number; code: string; name: string; is_live: boolean };
export type CaseAction = { id: number; jurisdiction_id: number; code: string; name: string; is_live: boolean };

export type Case = {
  id: number;
  reference: string;
  jurisdiction_id: number;
  visa_category_id: number | null;
  case_action_id: number | null;
  user_id: number | null;
  status: string;
  applicant_email: string | null;
  locale: string;
  host_locale: string;
  submission_reference: string | null;
  intake_answers: Record<string, unknown>;
  intake_step: string | null;
  notes: string | null;
  created_at: string | null;
  updated_at: string | null;
  jurisdiction_code?: string | null;
  visa_category_code?: string | null;
  case_action_code?: string | null;
  scope_label?: string | null;
  next_phase?: string | null;
  next_title?: string | null;
  origin_country?: string | null;
  residence_country?: string | null;
  research_id?: number | null;
};

export type IntakeQuestion = {
  key: string;
  prompt: string;
  type: "boolean" | "string" | "integer" | "enum";
  required?: boolean;
  options?: string[] | null;
  show_when?: { key: string; equals: boolean | string | number } | null;
  min_length?: number | null;
  max_length?: number | null;
  min_value?: number | null;
  max_value?: number | null;
};

export type IntakeState = {
  case_id: number;
  questions: IntakeQuestion[];
  answers: Record<string, unknown>;
  progress: { answered: number; total: number; complete: boolean };
  intake_step: string | null;
};

export type EligibilityResult = {
  result: "pass" | "at_risk" | "fail" | "out_of_scope";
  findings: {
    key: string;
    status: "pass" | "at_risk" | "fail" | "out_of_scope";
    message: string;
    citation: Record<string, unknown>;
  }[];
  disclaimer: string;
};

export type ChecklistItem = {
  id: number;
  case_id: number;
  code: string;
  name: string;
  how_to_obtain: string;
  why_required: string;
  is_required: boolean;
  status: string;
  citation: Record<string, unknown>;
  document_id: number | null;
};

export type Document = {
  id: number;
  case_id: number;
  doc_type: string;
  filename: string;
  storage_key: string;
  extracted_fields: Record<string, unknown>;
  extraction_confidence: number | null;
  confirmed: boolean;
  content_type: string;
};

export type GeneratedForm = {
  id: number;
  case_id: number;
  form_template_id: number;
  form_code: string;
  form_version: string;
  filled_fields: Record<string, unknown>;
  missing_required_fields: string[];
  citation: Record<string, unknown>;
};

export type ReviewResult = {
  flags: { code: string; message: string; fields?: string[] }[];
  checks: { code: string; message: string; passed: boolean }[];
  ready: boolean;
};

export type ResearchStepLog = {
  key: string;
  label: string;
  detail: string;
  at: string;
};

export type CaseGuidance = {
  phase: "intake" | "eligibility" | "checklist" | "forms" | "review" | "packet" | "done" | "blocked" | "research";
  title: string;
  instruction: string;
  cta_label: string;
  blocked_reason: string | null;
  progress: { answered: number; total: number; complete: boolean } | null;
  scope_label: string | null;
  research_status?: string | null;
  research_steps?: ResearchStepLog[];
  deadlines?: CaseDeadlines | null;
};

// Computed filing deadlines for a case, derived from the residence-card expiry
// intake answer (window open, online cut-off, grace period). Nulls mean the value
// is not applicable/known yet for this case's procedure.
export type CaseDeadlines = {
  residence_expiry: string | null;
  procedure: string;
  filing_window_opens: string | null;
  online_cutoff: string | null;
  grace_period_end: string | null;
  my_number_expiry: string | null;
  has_grace_period: boolean;
};

export type Escalation = {
  id: number;
  case_id: number;
  reason: string;
  message: string;
  consent_to_share: boolean;
  status: string;
  outcome: string | null;
};

// ── Jurisdictions ──────────────────────────────────────────────────────────────

export function listJurisdictions(token: string, liveOnly = false) {
  return req<Jurisdiction[]>(`/jurisdictions${liveOnly ? "?live_only=true" : ""}`, token);
}

export function listVisaCategories(token: string, jurisdictionCode: string, liveOnly = true) {
  return req<VisaCategory[]>(
    `/cases/visa-categories?jurisdiction_code=${encodeURIComponent(jurisdictionCode)}&live_only=${liveOnly}`,
    token,
  );
}

export function listCaseActions(token: string, jurisdictionCode: string, liveOnly = true) {
  return req<CaseAction[]>(
    `/cases/case-actions?jurisdiction_code=${encodeURIComponent(jurisdictionCode)}&live_only=${liveOnly}`,
    token,
  );
}

// ── Cases ──────────────────────────────────────────────────────────────────────

export function listCases(token: string) {
  return req<Case[]>("/cases", token);
}

export function getCase(token: string, caseId: number) {
  return req<Case>(`/cases/${caseId}`, token);
}

export function deleteCase(token: string, caseId: number) {
  return req<void>(`/cases/${caseId}`, token, { method: "DELETE" });
}

export function scopeCase(token: string, data: {
  jurisdiction_code: string;
  visa_category_code: string;
  action_code: string;
  locale?: string;
  origin_country?: string;
  residence_country?: string;
}) {
  return req<Case>("/cases/scope", token, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function requestResearch(token: string, caseId: number) {
  return req<{ status: string; message: string }>(`/cases/${caseId}/research`, token, { method: "POST" });
}

// ── Intake ─────────────────────────────────────────────────────────────────────

export function getCaseGuidance(token: string, caseId: number) {
  return req<CaseGuidance>(`/cases/${caseId}/guidance`, token);
}

export function getIntake(token: string, caseId: number) {
  return req<IntakeState>(`/cases/${caseId}/intake`, token);
}

export function answerIntake(token: string, caseId: number, key: string, value: unknown) {
  return req<IntakeState>(`/cases/${caseId}/intake/answer`, token, {
    method: "PUT",
    body: JSON.stringify({ key, value }),
  });
}

// ── Eligibility ────────────────────────────────────────────────────────────────

export function evaluateEligibility(token: string, caseId: number) {
  return req<EligibilityResult>(`/cases/${caseId}/eligibility/evaluate`, token, { method: "POST" });
}

export function getEligibility(token: string, caseId: number) {
  return req<EligibilityResult>(`/cases/${caseId}/eligibility`, token);
}

// ── Checklist ──────────────────────────────────────────────────────────────────

export function refreshChecklist(token: string, caseId: number) {
  return req<ChecklistItem[]>(`/cases/${caseId}/checklist/refresh`, token, { method: "POST" });
}

export function getChecklist(token: string, caseId: number) {
  return req<ChecklistItem[]>(`/cases/${caseId}/checklist`, token);
}

export function patchChecklistItem(token: string, caseId: number, itemId: number, status: string) {
  return req<ChecklistItem>(`/cases/${caseId}/checklist/${itemId}`, token, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

// ── Documents ──────────────────────────────────────────────────────────────────

export function getDocuments(token: string, caseId: number) {
  return req<Document[]>(`/cases/${caseId}/documents`, token);
}

export function registerDocument(token: string, caseId: number, data: {
  doc_type: string;
  filename: string;
  storage_key: string;
  extracted_fields?: Record<string, unknown>;
  extraction_confidence?: number;
  content_type?: string;
}) {
  return req<Document>(`/cases/${caseId}/documents`, token, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function confirmDocument(token: string, caseId: number, docId: number) {
  return req<Document>(`/cases/${caseId}/documents/${docId}/confirm`, token, { method: "POST" });
}

// ── Forms ──────────────────────────────────────────────────────────────────────

export function generateForms(token: string, caseId: number) {
  return req<GeneratedForm[]>(`/cases/${caseId}/forms/generate`, token, { method: "POST" });
}

export function getForms(token: string, caseId: number) {
  return req<GeneratedForm[]>(`/cases/${caseId}/forms`, token);
}

// ── Review ─────────────────────────────────────────────────────────────────────

export function reviewCase(token: string, caseId: number) {
  return req<ReviewResult>(`/cases/${caseId}/review`, token, { method: "POST" });
}

export function acknowledgeReview(token: string, caseId: number) {
  return req<{ review_flags_acknowledged: boolean }>(`/cases/${caseId}/review/acknowledge`, token, { method: "POST" });
}

// ── Packet ─────────────────────────────────────────────────────────────────────

export function buildPacket(token: string, caseId: number) {
  return req<Record<string, unknown>>(`/cases/${caseId}/packet`, token, { method: "POST" });
}

export function getPacket(token: string, caseId: number) {
  return req<Record<string, unknown>>(`/cases/${caseId}/packet`, token);
}

// ── Submission ─────────────────────────────────────────────────────────────────

export function submitCase(token: string, caseId: number) {
  return req<{ submission_reference: string }>(`/cases/${caseId}/submit`, token, { method: "POST" });
}

// ── Escalations ────────────────────────────────────────────────────────────────

export function createEscalation(token: string, caseId: number, data: {
  reason: string;
  message: string;
  consent_to_share?: boolean;
}) {
  return req<Escalation>(`/cases/${caseId}/escalations`, token, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function getEscalations(token: string, caseId: number) {
  return req<Escalation[]>(`/cases/${caseId}/escalations`, token);
}

// ── Locale ─────────────────────────────────────────────────────────────────────

export function patchLocale(token: string, caseId: number, locale: string, hostLocale?: string) {
  return req<{ locale: string; host_locale: string }>(`/cases/${caseId}/locale`, token, {
    method: "PATCH",
    body: JSON.stringify({ locale, host_locale: hostLocale }),
  });
}

// ── Admin Cases ──────────────────────────────────────────────────────────────

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
