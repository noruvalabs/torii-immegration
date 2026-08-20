export type CreditPack = {
  id: "starter" | "standard" | "family";
  name: string;
  name_ja: string;
  credits: number;
  price_usd: number;
  price_jpy: number;
  badge: string | null;
  description: string;
  description_ja: string;
};

export type CreditTransaction = {
  id: number;
  amount: number;
  balance_after: number;
  feature: string;
  case_id: number | null;
  description: string;
  created_at: string;
};

export type CreditBalanceResponse = {
  credit_balance: number;
  user_id: number;
  email: string;
  packs: CreditPack[];
  recent_transactions: CreditTransaction[];
};

export async function fetchCreditBalance(token: string): Promise<CreditBalanceResponse> {
  const res = await fetch("/backend/v1/credits/balance", {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to fetch credit balance");
  return res.json();
}

export async function topUpCredits(
  token: string,
  packId: "starter" | "standard" | "family",
  currency: "usd" | "jpy" = "usd",
): Promise<{ success: boolean; credits_added: number; credit_balance: number; message: string }> {
  const res = await fetch("/backend/v1/credits/top-up", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ pack_id: packId, currency }),
  });
  if (!res.ok) throw new Error("Failed to purchase credit pack");
  return res.json();
}

export async function consumeCredits(
  token: string,
  feature: "ocr_extraction" | "ai_query" | "case_unlock" | "pdf_export" | "translation",
  amount: number,
  description: string,
  caseId?: number,
): Promise<{ success: boolean; credits_consumed: number; credit_balance: number }> {
  const res = await fetch("/backend/v1/credits/consume", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ feature, amount, description, case_id: caseId }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData?.detail?.message || "Insufficient credits");
  }
  return res.json();
}

export async function unlockCasePacket(
  token: string,
  caseId: number,
): Promise<{ success: boolean; already_unlocked: boolean; credits_consumed: number; credit_balance: number }> {
  const res = await fetch(`/backend/v1/credits/unlock-case/${caseId}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData?.detail?.message || "Insufficient credits to unlock case");
  }
  return res.json();
}
