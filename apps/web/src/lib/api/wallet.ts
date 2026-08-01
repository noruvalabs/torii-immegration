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
  status: string;
  created_at: string | null;
};

export type DocumentVersion = {
  id: number;
  version: number;
  filename: string;
  content_type: string;
  file_size: number | null;
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
  message: string;
};

async function request<T>(path: string, options: RequestInit): Promise<T> {
  const token = localStorage.getItem("token");
  const res = await fetch(`${API}${path}`, {
    ...options,
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail ?? `Request failed (${res.status})`);
  }

  return res.json() as Promise<T>;
}

export function getDocumentTypes() {
  return request<DocumentTypesResponse>("/document-types", { method: "GET" });
}

export function getWallet() {
  return request<WalletDocument[]>("/", { method: "GET" });
}

export function getWalletSummary() {
  return request<WalletSummary>("/summary", { method: "GET" });
}

export function uploadDocument(
  file: File,
  docType: string,
  name?: string,
  issuedDate?: string,
  expiryDate?: string,
  notes?: string,
) {
  const formData = new URLSearchParams();
  formData.append("doc_type", docType);
  if (name) formData.append("name", name);
  if (issuedDate) formData.append("issued_date", issuedDate);
  if (expiryDate) formData.append("expiry_date", expiryDate);
  if (notes) formData.append("notes", notes);

  const token = localStorage.getItem("token");
  return fetch(`${API}/upload?${formData.toString()}`, {
    method: "POST",
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: file,
  }).then(async (res) => {
    if (!res.ok) {
      const body = (await res.json().catch(() => null)) as { detail?: string } | null;
      throw new Error(body?.detail ?? `Upload failed (${res.status})`);
    }
    return res.json() as Promise<WalletUploadResponse>;
  });
}

export function getDocument(documentId: number) {
  return request<WalletDocument>(`/${documentId}`, { method: "GET" });
}

export function getDocumentVersions(documentId: number) {
  return request<DocumentVersion[]>(`/${documentId}/versions`, { method: "GET" });
}

export function expireDocument(documentId: number) {
  return request<WalletDocument>(`/${documentId}/expire`, { method: "POST" });
}

export function deleteDocument(documentId: number) {
  const token = localStorage.getItem("token");
  return fetch(`${API}/${documentId}`, {
    method: "DELETE",
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  }).then(async (res) => {
    if (!res.ok) {
      const body = (await res.json().catch(() => null)) as { detail?: string } | null;
      throw new Error(body?.detail ?? `Delete failed (${res.status})`);
    }
  });
}
