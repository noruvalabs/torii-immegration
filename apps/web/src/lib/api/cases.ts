import { formatApiDetail } from "./errors";

const API = "/backend/v1";

function authHeaders(token: string | null): Record<string, string> {
  const h: Record<string, string> = { "content-type": "application/json" };
  if (token) h.Authorization = `Bearer ${token}`;
  return h;
}

const inFlightRequests = new Map<string, Promise<unknown>>();

async function req<T>(path: string, token: string | null, init?: RequestInit): Promise<T> {
  const method = (init?.method || "GET").toUpperCase();
  const isGet = method === "GET";
  const dedupeKey = isGet ? `${token || ""}:${path}` : null;

  if (dedupeKey) {
    const existing = inFlightRequests.get(dedupeKey);
    if (existing) {
      return existing as Promise<T>;
    }
  }

  const execute = async () => {
    try {
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
    } finally {
      if (dedupeKey) {
        inFlightRequests.delete(dedupeKey);
      }
    }
  };

  const promise = execute();
  if (dedupeKey) {
    inFlightRequests.set(dedupeKey, promise);
  }
  return promise;
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
  is_entitled?: boolean;
  is_archived?: boolean;
  packet_snapshot?: Record<string, unknown> | null;
  eligibility_snapshot?: Record<string, unknown> | null;
};

export type IntakeQuestion = {
  key: string;
  prompt: string;
  type: "boolean" | "string" | "integer" | "enum" | "date";
  required?: boolean;
  options?: string[] | null;
  /** The official form's own wording per option, where the choice mirrors a tick-box group. */
  option_labels?: Record<string, string> | null;
  /** Revealed by another answer: `equals` for one value, `one_of` for any of several. */
  show_when?: {
    key: string;
    equals?: boolean | string | number | null;
    one_of?: string[] | null;
  } | null;
  min_length?: number | null;
  max_length?: number | null;
  min_value?: number | null;
  max_value?: number | null;
  section?: string | null;
  /** Why the question is asked — set where the answer fills a specific official-form box. */
  hint?: string | null;
  citation?: Record<string, unknown> | null;
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
  /** The form's own name, from the pack or the research behind it. */
  official_title?: string | null;
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

export function archiveCase(token: string, caseId: number) {
  return req<Case>(`/cases/${caseId}/archive`, token, { method: "POST" });
}

export function unarchiveCase(token: string, caseId: number) {
  return req<Case>(`/cases/${caseId}/unarchive`, token, { method: "POST" });
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

export function patchCase(
  token: string,
  caseId: number,
  payload: {
    intake_answers?: Record<string, unknown>;
    intake_step?: string;
    notes?: string;
    submission_reference?: string | null;
  },
) {
  return req<Case>(`/cases/${caseId}`, token, {
    method: "PATCH",
    body: JSON.stringify(payload),
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

// ── Official government forms ──────────────────────────────────────────────────
// The exact ministry-published sheet for this application type, not a rendering of it.

export type OfficialForm = {
  code: string;
  title_en: string;
  title_ja: string;
  series: string;
  procedure: string;
  authority: string;
  source_page_url: string;
  pdf_url: string | null;
  pages: number;
  citation: { authority: string; title: string; url: string };
  note: string | null;
  missing_answer_keys?: string[];
  required_missing_keys?: string[];
  optional_missing_keys?: string[];
  total_items?: number;
};

export type OfficialFormsResponse = {
  jurisdiction: string | null;
  visa_category?: string | null;
  action?: string | null;
  scope_label: string | null;
  forms: OfficialForm[];
};

export function getOfficialForms(token: string, caseId: number) {
  return req<OfficialFormsResponse>(`/cases/${caseId}/official-forms`, token);
}

// ── Filing mode ────────────────────────────────────────────────────────────────
// Some countries publish a form to fill in and hand over (Japan); others are filed
// entirely on a government website (the UK), where the deliverable is an answer pack.

export type PortalField = {
  field: string;
  label: string;
  answer_key: string;
  value: string | null;
  required: boolean;
  answered: boolean;
};

export type PortalSection = { key: string; title: string; fields: PortalField[] };

export type PortalPack = {
  jurisdiction: string;
  scope_label: string;
  apply_url: string | null;
  sections: PortalSection[];
  citations: { authority?: string; title?: string; url?: string }[];
  answered_count: number;
  outstanding_count: number;
  outstanding: string[];
};

export type FilingInfo = {
  case_id: number;
  jurisdiction: string | null;
  scope_label: string | null;
  filing_mode: "official_form_pdf" | "online_portal" | "hybrid";
  apply_url: string | null;
  portal_pack?: PortalPack;
};

export function getFiling(token: string, caseId: number) {
  return req<FilingInfo>(`/cases/${caseId}/filing`, token);
}

export type OfficialFormDownload = {
  filename: string;
  media_type: string;
  data_base64: string;
  size_bytes: number;
  form?: Record<string, unknown>;
};

export function downloadOfficialForm(token: string, caseId: number, formCode: string) {
  return req<OfficialFormDownload>(
    `/cases/${caseId}/export/official-form/${encodeURIComponent(formCode)}?format=base64`,
    token,
    { headers: { Accept: "application/json" } },
  );
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

// ── Document export ────────────────────────────────────────────────────────────

export type ExportFormat = "pdf" | "docx";

export type ExportDocumentInput = {
  title: string;
  content: string;
  filename_stem?: string;
};

export type ExportedFile = {
  filename: string;
  media_type: string;
  data_base64: string;
  size_bytes: number;
};

/**
 * Render the drafts the applicant has on screen as real files.
 *
 * The text is sent back to the server because it is theirs: template, AI draft, or
 * either of those after they edited it in the textarea. `separate` returns a zip with
 * one file per document instead of a single file holding all of them.
 */
export function exportCaseDocuments(
  token: string,
  caseId: number,
  data: { documents: ExportDocumentInput[]; format: ExportFormat; separate?: boolean },
) {
  return req<ExportedFile>(`/cases/${caseId}/export/documents?format=base64`, token, {
    method: "POST",
    headers: { Accept: "application/json" },
    body: JSON.stringify(data),
  });
}

// ── Journey ────────────────────────────────────────────────────────────────────

export type JourneyStage = {
  key: string;
  order: number;
  title: string;
  detail: string;
  owner: "torii" | "you" | "authority" | "third_party";
  status: "done" | "current" | "todo";
  phase: string | null;
  done_count: number | null;
  total_count: number | null;
  authority: string | null;
  official_citation_url: string | null;
  portal_url: string | null;
  notes: string[];
};

export type JourneyExternalTask = {
  code: string;
  category: string;
  categories: string[];
  title: string;
  arranged_with: string;
  lead_time: string;
  guidance: string;
  how_to_obtain: string;
  why_required: string;
  is_required: boolean;
  status: string;
  checklist_item_id: number | null;
  official_citation_url: string | null;
  options: { label: string; url: string | null }[];
};

export type CaseJourney = {
  reference: string;
  scope_label: string;
  phase: string;
  filing_mode: string;
  apply_url: string | null;
  submitted: boolean;
  stages: JourneyStage[];
  external_tasks: JourneyExternalTask[];
  checklist_progress: { done: number; total: number };
  external_progress: { done: number; total: number };
  office: string | null;
  filed_by: string | null;
  fee_note: string | null;
  notes: string[];
};

export function getCaseJourney(token: string, caseId: number) {
  return req<CaseJourney>(`/cases/${caseId}/journey`, token);
}

// ── Action plan ────────────────────────────────────────────────────────────────

export type PlanAction = {
  title: string;
  detail: string;
  lead_time?: string | null;
};

export type CasePlan = {
  headline: string;
  ready_to_file: boolean;
  time_to_ready: string | null;
  start_now: PlanAction[];
  then: PlanAction[];
  risks: PlanAction[];
  questions: string[];
  disclaimer: string;
  model_used: string;
  generated_at: string;
};

/** The plan already built for this case, or `null` if it has not been built yet. */
export function getCasePlan(token: string, caseId: number) {
  return req<{ plan: CasePlan | null }>(`/cases/${caseId}/plan`, token);
}

/**
 * Build the plan once and keep it on the case.
 *
 * The API prepares the case — the outstanding items and their lead times, the cited
 * filing route, the answers that say something — before the model sees it, and stores
 * the result. The browser never talks to the AI service directly: when that service is
 * slow or down the applicant used to get a proxy 500 instead of a plan.
 */
export function buildCasePlan(token: string, caseId: number) {
  return req<{ plan: CasePlan }>(`/cases/${caseId}/plan`, token, { method: "POST" });
}

// ── Submission ─────────────────────────────────────────────────────────────────

/**
 * Record that the applicant filed the application themselves.
 *
 * Not the same call as `submitCase`, which asks Torii to file electronically — that is
 * refused by every jurisdiction whose authority does not accept third-party electronic
 * submission, Japan included. Someone reporting a trip to the counter was being told
 * "E-file is unavailable for this jurisdiction", which answers a question they did not ask.
 */
export function recordCaseFiled(token: string, caseId: number) {
  return req<{ status: string; filed_at: string; submission_reference: string | null }>(
    `/cases/${caseId}/filed`,
    token,
    { method: "POST" },
  );
}

/** Electronic filing by Torii, where the jurisdiction accepts it. Most do not. */
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
