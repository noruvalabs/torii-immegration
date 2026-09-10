export type PaymentConfigResponse = {
  payments_enabled: boolean;
  provider: string;
  environment: string;
  client_token: string;
  default_checkout_url: string;
};

export type CheckoutResponse = {
  checkout_id: string;
  provider: string;
  provider_session_id: string | null;
  checkout_url: string | null;
  amount: number;
  currency: string;
  credits: number;
  pack_id: string;
};

export type CheckoutStatusResponse = {
  checkout_id: string;
  status: string;
  credits: number;
  amount: number;
  currency: string;
  completed_at: string | null;
};

export type AdminPaymentSettingsResponse = {
  payments_enabled: boolean;
  provider: string;
  environment: string;
  client_token_configured: boolean;
  api_key_configured: boolean;
  webhook_secret_configured: boolean;
  default_checkout_url: string;
};

export async function fetchPaymentConfig(token?: string): Promise<PaymentConfigResponse> {
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch("/backend/v1/payments/config", { headers });
  if (!res.ok) {
    // Fallback if backend is momentarily unreachable
    return {
      payments_enabled: true,
      provider: "paddle",
      environment: "sandbox",
      client_token: "",
      default_checkout_url: "",
    };
  }
  return res.json();
}

export async function createCheckoutSession(
  token: string,
  packId: "starter" | "standard" | "family",
  currency: "usd" | "jpy" = "usd",
): Promise<CheckoutResponse> {
  const res = await fetch("/backend/v1/payments/checkout", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ pack_id: packId, currency }),
  });

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data?.detail || "Checkout session failed to initialize");
  }

  return res.json();
}

export async function getCheckoutStatus(
  token: string,
  checkoutId: string,
): Promise<CheckoutStatusResponse> {
  const res = await fetch(`/backend/v1/payments/checkout/${checkoutId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) {
    throw new Error("Failed to check checkout status");
  }

  return res.json();
}

export async function adminGetPaymentSettings(token: string): Promise<AdminPaymentSettingsResponse> {
  const res = await fetch("/backend/v1/admin/settings/payment", {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data?.detail || "Failed to fetch admin payment settings");
  }

  return res.json();
}

export async function adminUpdatePaymentSettings(
  token: string,
  paymentsEnabled: boolean,
): Promise<AdminPaymentSettingsResponse> {
  const res = await fetch("/backend/v1/admin/settings/payment", {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ payments_enabled: paymentsEnabled }),
  });

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data?.detail || "Failed to update payment settings");
  }

  return res.json();
}
