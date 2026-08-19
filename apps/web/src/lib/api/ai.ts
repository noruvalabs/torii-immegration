const AI_API = "/assistant/ai";

export type DraftDocumentPayload = {
  doc_type: string;
  jurisdiction_code?: string;
  scope_label?: string;
  case_reference?: string;
  intake_answers?: Record<string, unknown>;
  checklist?: Record<string, unknown>[];
  custom_instructions?: string;
  locale?: string;
};

export type DraftDocumentResult = {
  doc_type: string;
  title: string;
  content: string;
  model_used: string;
  generated_at: string;
};

export async function draftDocument(payload: DraftDocumentPayload): Promise<DraftDocumentResult> {
  const token = typeof window !== "undefined" ? localStorage.getItem("torii_token") : null;
  const res = await fetch(`${AI_API}/agentic/draft-document`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      doc_type: payload.doc_type,
      jurisdiction_code: payload.jurisdiction_code || "JP",
      scope_label: payload.scope_label || "Visa Application",
      case_reference: payload.case_reference || "CASE-1",
      intake_answers: payload.intake_answers || {},
      checklist: payload.checklist || [],
      custom_instructions: payload.custom_instructions || null,
      locale: payload.locale || "en",
    }),
  });

  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail ?? `AI document drafting failed (${res.status})`);
  }
  return res.json() as Promise<DraftDocumentResult>;
}
