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

export type MatchedProduct = {
  id: number;
  code: string;
  name: string;
  description: string;
  product_type: string;
  price_cents: number;
  currency: string;
};

export type ExistingOrder = {
  id: number;
  status: string;
  price_cents: number;
  currency: string;
  fulfilled_document_id?: number | null;
  created_at?: string | null;
};

export type ConciergeMatch = {
  checklist_item_id: number;
  checklist_code: string;
  checklist_name: string;
  products: MatchedProduct[];
  existing_order?: ExistingOrder | null;
};

export type ConciergeOrder = {
  id: number;
  case_id: number;
  checklist_item_id: number;
  product_id: number;
  user_id: number;
  price_cents: number;
  currency: string;
  status: string;
  fulfilled_document_id?: number | null;
  notes?: string | null;
};

export function getAvailableConcierge(
  token: string | null,
  caseId: number,
): Promise<ConciergeMatch[]> {
  return req<ConciergeMatch[]>(`/cases/${caseId}/concierge`, token);
}

export function orderConcierge(
  token: string | null,
  caseId: number,
  checklistItemId: number,
  productId: number,
): Promise<ConciergeOrder> {
  return req<ConciergeOrder>(`/cases/${caseId}/concierge/order`, token, {
    method: "POST",
    body: JSON.stringify({ checklist_item_id: checklistItemId, product_id: productId }),
  });
}

export function getConciergeOrders(
  token: string | null,
  caseId: number,
): Promise<ConciergeOrder[]> {
  return req<ConciergeOrder[]>(`/cases/${caseId}/concierge/orders`, token);
}

