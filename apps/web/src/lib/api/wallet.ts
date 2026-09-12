import { formatApiDetail } from "./errors";

const API = "/backend/v1/wallet";

export type DocumentType = {
  code: string;
  name: string;
  category: string;
};

export type WalletDocument = {
  id: number;
  doc_type: string;
  name: string;
  version: number;
  filename: string;
  content_type: string;
  file_size: number | null;
  issued_date: string | null;
  expiry_date: string | null;
  extracted_fields?: Record<string, { value: string; confidence: number } | string> | null;
  extraction_confidence?: number | null;
  status: string;
  created_at: string | null;
};

export type DocumentVersion = {
  id: number;
  version: number;
  filename: string;
  content_type: string;
  file_size: number | null;
  extracted_fields?: Record<string, { value: string; confidence: number } | string> | null;
  extraction_confidence?: number | null;
  notes: string | null;
  created_at: string | null;
};

export type WalletSummary = {
  total_documents: number;
  documents_by_category: Record<string, WalletDocument[]>;
  expiring_soon: Array<{
    id: number;
    doc_type: string;
    name: string;
    expiry_date: string | null;
  }>;
};

export type DocumentTypesResponse = {
  document_types: DocumentType[];
};

export type WalletUploadResponse = {
  id: number;
  doc_type: string;
  name: string;
  version: number;
  filename: string;
  storage_key: string;
  extracted_fields?: Record<string, { value: string; confidence: number } | string> | null;
  extraction_confidence?: number | null;
  message: string;
};

function resolveToken(token?: string | null): string | null {
  if (token) return token;
  if (typeof window !== "undefined") {
    return (
      localStorage.getItem("torii_token") ||
      localStorage.getItem("token")
    );
  }
  return null;
}

async function request<T>(path: string, options: RequestInit, token?: string | null): Promise<T> {
  const authToken = resolveToken(token);
  const res = await fetch(`${API}${path}`, {
    ...options,
    headers: {
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
      ...options.headers,
    },
  });

  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { detail?: unknown } | null;
    const errorMsg = body?.detail ? formatApiDetail(body.detail) : `Request failed (${res.status})`;
    throw new Error(errorMsg);
  }

  return res.json() as Promise<T>;
}

export function getDocumentTypes(token?: string | null) {
  return request<DocumentTypesResponse>("/document-types", { method: "GET" }, token);
}

export async function getWallet(token?: string | null) {
  return request<WalletDocument[]>("", { method: "GET" }, token);
}

export function getWalletSummary(token?: string | null) {
  return request<WalletSummary>("/summary", { method: "GET" }, token);
}

export function uploadDocument(
  token: string | null | undefined,
  file: File,
  docType: string,
  name?: string,
  issuedDate?: string,
  expiryDate?: string,
  notes?: string,
) {
  const formData = new FormData();
  formData.append("file", file);

  const queryParams = new URLSearchParams();
  queryParams.append("doc_type", docType);
  if (name) queryParams.append("name", name);
  if (issuedDate) queryParams.append("issued_date", issuedDate);
  if (expiryDate) queryParams.append("expiry_date", expiryDate);
  if (notes) queryParams.append("notes", notes);

  const authToken = resolveToken(token);
  return fetch(`${API}/upload?${queryParams.toString()}`, {
    method: "POST",
    headers: {
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
    },
    body: formData,
  }).then(async (res) => {
    if (!res.ok) {
      const body = (await res.json().catch(() => null)) as { detail?: unknown } | null;
      const errorMsg = body?.detail ? formatApiDetail(body.detail) : `Upload failed (${res.status})`;
      throw new Error(errorMsg);
    }
    return res.json() as Promise<WalletUploadResponse>;
  });
}

export function getDocument(documentId: number, token?: string | null) {
  return request<WalletDocument>(`/${documentId}`, { method: "GET" }, token);
}

export function getDocumentVersions(documentId: number, token?: string | null) {
  return request<DocumentVersion[]>(`/${documentId}/versions`, { method: "GET" }, token);
}

export function expireDocument(documentId: number, token?: string | null) {
  return request<WalletDocument>(`/${documentId}/expire`, { method: "POST" }, token);
}

export function deleteDocument(documentId: number, token?: string | null) {
  const authToken = resolveToken(token);
  return fetch(`${API}/${documentId}`, {
    method: "DELETE",
    headers: {
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
    },
  }).then(async (res) => {
    if (!res.ok) {
      const body = (await res.json().catch(() => null)) as { detail?: unknown } | null;
      throw new Error(formatApiDetail(body?.detail) || `Delete failed (${res.status})`);
    }
  });
}

export function patchWalletDocument(
  documentId: number,
  data: { name?: string; issued_date?: string; expiry_date?: string; notes?: string },
  token?: string | null
) {
  return request<WalletDocument>(`/${documentId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  }, token);
}

export function applyDocumentToCase(
  documentId: number,
  caseId: number,
  token?: string | null
) {
  return request<{
    success: boolean;
    message: string;
    intake_answers: Record<string, any>;
    fields_applied: string[];
  }>(`/${documentId}/apply-to-case/${caseId}`, { method: "POST" }, token);
}

export function applyDocumentToProfile(
  documentId: number,
  token?: string | null
) {
  return request<{
    success: boolean;
    message: string;
    user: Record<string, any>;
  }>(`/${documentId}/apply-to-profile`, { method: "POST" }, token);
}

export function reextractDocument(
  documentId: number,
  token?: string | null
) {
  return request<WalletDocument>(`/${documentId}/re-extract`, { method: "POST" }, token);
}

export function seedDummyDocuments(token?: string | null) {
  return request<{
    success: boolean;
    message: string;
    documents: Array<{ id: number; doc_type: string; name: string; filename: string }>;
  }>("/seed-dummy-documents", { method: "POST" }, token);
}

export function getDocumentFileUrl(documentId: number, token?: string | null): string {
  const authToken = resolveToken(token);
  const query = authToken ? `?token=${encodeURIComponent(authToken)}` : "";
  return `${API}/${documentId}/file${query}`;
}

export function getDocumentViewUrl(documentId: number, token?: string | null): string {
  const authToken = resolveToken(token);
  const query = authToken ? `?token=${encodeURIComponent(authToken)}` : "";
  return `${API}/${documentId}/view${query}`;
}



