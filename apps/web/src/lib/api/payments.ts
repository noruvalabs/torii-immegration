const API = "/backend/v1/payments";

export type Payment = {
  id: number;
  case_id: number;
  transaction_id: string;
  visa_fee: number;
  service_fee: number;
  total_amount: number;
  currency: string;
  status: string;
  payment_method: string | null;
  paid_at: string | null;
  created_at: string | null;
};

export type PaymentFees = {
  destination_code: string;
  currency: string;
  fees: {
    tourist: { visa_fee: number; service_fee: number; total: number };
    student: { visa_fee: number; service_fee: number; total: number };
    work: { visa_fee: number; service_fee: number; total: number };
  };
};

export type PaymentList = {
  payments: Payment[];
  total: number;
};

async function request<T>(path: string, options: RequestInit): Promise<T> {
  const token = localStorage.getItem("token");
  const res = await fetch(`${API}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
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

export function createPayment(caseId: number, destinationCode: string, visaType: string) {
  return request<Payment>("/", {
    method: "POST",
    body: JSON.stringify({
      case_id: caseId,
      destination_code: destinationCode,
      visa_type: visaType,
    }),
  });
}

export function getPayments() {
  return request<PaymentList>("/", { method: "GET" });
}

export function getCasePayment(caseId: number) {
  return request<Payment>(`/case/${caseId}`, { method: "GET" });
}

export function processPayment(paymentId: number, paymentMethod: string = "card") {
  return request<Payment>(`/${paymentId}/process`, {
    method: "POST",
    body: JSON.stringify({ payment_method: paymentMethod }),
  });
}

export function refundPayment(paymentId: number) {
  return request<Payment>(`/${paymentId}/refund`, { method: "POST" });
}

export function getVisaFees(destinationCode: string) {
  return request<PaymentFees>(`/fees/${destinationCode}`, { method: "GET" });
}
