"use client";

import { Coins, Plus } from "lucide-react";
import { useCredits } from "@/lib/credits-context";
import { useI18n } from "@/lib/i18n";
import { cn } from "@/lib/utils";

export function CreditBalanceBadge({
  className,
  compact = false,
}: {
  className?: string;
  compact?: boolean;
}) {
  const { balance, setIsTopUpOpen } = useCredits();
  const { lang } = useI18n();

  if (compact) {
    return (
      <button
        type="button"
        onClick={() => setIsTopUpOpen(true)}
        title={
          lang === "ja"
            ? `クレジット: ${balance} パス (チャージ)`
            : `Balance: ${balance} ${balance === 1 ? "Pass" : "Passes"} (Top up)`
        }
        className={cn(
          "group relative inline-flex size-9 items-center justify-center rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400 hover:bg-amber-500/20 transition-all shadow-xs",
          className,
        )}
      >
        <Coins className="size-4 text-amber-500 transition-transform group-hover:scale-110" />
        <span className="absolute -top-1 -right-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-amber-500 px-1 text-[9px] font-black text-white shadow-xs">
          {balance}
        </span>
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={() => setIsTopUpOpen(true)}
      title={lang === "ja" ? "クレジットを購入・チャージ" : "Top up credits"}
      className={cn(
        "group inline-flex items-center gap-1.5 rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-1 text-xs font-bold text-amber-600 dark:text-amber-400 hover:bg-amber-500/20 transition-all shadow-xs",
        className,
      )}
    >
      <Coins className="size-3.5 text-amber-500 transition-transform group-hover:scale-110" />
      <span>{balance}</span>
      <span className="text-[10px] font-medium opacity-80">
        {lang === "ja" ? "パス" : balance === 1 ? "Pass" : "Passes"}
      </span>
      <span className="flex size-3.5 items-center justify-center rounded-full bg-amber-500 text-background text-[9px] font-black group-hover:rotate-90 transition-transform ml-0.5">
        <Plus className="size-2.5 text-white" />
      </span>
    </button>
  );
}
