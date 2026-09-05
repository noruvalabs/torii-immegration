"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { useAuth } from "./auth-context";
import {
  fetchCreditBalance,
  consumeCredits,
  topUpCredits,
  unlockCasePacket,
  type CreditPack,
  type CreditTransaction,
} from "./api/credits";

interface CreditsContextValue {
  balance: number;
  loading: boolean;
  packs: CreditPack[];
  transactions: CreditTransaction[];
  isTopUpOpen: boolean;
  setIsTopUpOpen: (open: boolean) => void;
  refreshBalance: () => Promise<void>;
  purchasePack: (packId: "starter" | "standard" | "family", currency?: "usd" | "jpy") => Promise<void>;
  deductCredits: (
    feature: "ocr_extraction" | "ai_query" | "case_unlock" | "pdf_export" | "translation",
    amount: number,
    description: string,
    caseId?: number,
  ) => Promise<boolean>;
  unlockCase: (caseId: number) => Promise<{ success: boolean; already_unlocked: boolean }>;
}

const CreditsContext = createContext<CreditsContextValue | null>(null);

export function CreditsProvider({ children }: { children: React.ReactNode }) {
  const { token, user } = useAuth();
  const [balance, setBalance] = useState<number>(3);
  const [packs, setPacks] = useState<CreditPack[]>([]);
  const [transactions, setTransactions] = useState<CreditTransaction[]>([]);
  const [loading, setLoading] = useState(false);
  const [isTopUpOpen, setIsTopUpOpen] = useState(false);

  const refreshBalance = useCallback(async () => {
    if (!token) return;
    try {
      setLoading(true);
      const data = await fetchCreditBalance(token);
      setBalance(data.credit_balance);
      setPacks(data.packs);
      setTransactions(data.recent_transactions);
    } catch {
      // Fallback
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (token) {
      void refreshBalance();
    }
  }, [token, refreshBalance]);

  const purchasePack = async (packId: "starter" | "standard" | "family", currency: "usd" | "jpy" = "usd") => {
    if (!token) return;
    const res = await topUpCredits(token, packId, currency);
    setBalance(res.credit_balance);
    await refreshBalance();
  };

  const deductCredits = async (
    feature: "ocr_extraction" | "ai_query" | "case_unlock" | "pdf_export" | "translation",
    amount: number,
    description: string,
    caseId?: number,
  ): Promise<boolean> => {
    if (!token) return false;
    try {
      const res = await consumeCredits(token, feature, amount, description, caseId);
      setBalance(res.credit_balance);
      return true;
    } catch {
      setIsTopUpOpen(true);
      return false;
    }
  };

  const unlockCase = async (caseId: number) => {
    if (!token) return { success: false, already_unlocked: false };
    try {
      const res = await unlockCasePacket(token, caseId);
      setBalance(res.credit_balance);
      return { success: res.success, already_unlocked: res.already_unlocked };
    } catch {
      setIsTopUpOpen(true);
      return { success: false, already_unlocked: false };
    }
  };

  return (
    <CreditsContext.Provider
      value={{
        balance,
        loading,
        packs,
        transactions,
        isTopUpOpen,
        setIsTopUpOpen,
        refreshBalance,
        purchasePack,
        deductCredits,
        unlockCase,
      }}
    >
      {children}
    </CreditsContext.Provider>
  );
}

export function useCredits(): CreditsContextValue {
  const ctx = useContext(CreditsContext);
  if (!ctx) {
    throw new Error("useCredits must be used within a CreditsProvider");
  }
  return ctx;
}
