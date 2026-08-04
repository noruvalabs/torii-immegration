const AI_API = "/assistant";

export type DocumentType = "passport" | "residence_card" | "employment_contract" | "proof_of_funds" | "travel_itinerary";

export type ExtractedValue = {
  value: string;
  confidence: number;
};

export type OCRResult = {
  fields: Record<string, ExtractedValue>;
  needs_recapture: boolean;
};

export function extractDocumentFields(
  docType: DocumentType,
  filename: string,
  hintText?: string,
): Promise<OCRResult> {
  const token = localStorage.getItem("token");
  return fetch(`${AI_API}/ocr/extract`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      doc_type: docType,
      filename,
      hint_text: hintText || null,
    }),
  }).then(async (res) => {
    if (!res.ok) {
      const body = (await res.json().catch(() => null)) as { detail?: string } | null;
      throw new Error(body?.detail ?? `OCR extraction failed (${res.status})`);
    }
    return res.json() as Promise<OCRResult>;
  });
}

export function extractFromFile(
  file: File,
  docType: DocumentType,
): Promise<OCRResult> {
  const token = localStorage.getItem("token");
  const formData = new FormData();
  formData.append("file", file);
  formData.append("doc_type", docType);

  return fetch(`${AI_API}/ocr/extract-file`, {
    method: "POST",
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: formData,
  }).then(async (res) => {
    if (!res.ok) {
      const body = (await res.json().catch(() => null)) as { detail?: string } | null;
      throw new Error(body?.detail ?? `OCR extraction failed (${res.status})`);
    }
    return res.json() as Promise<OCRResult>;
  });
}
