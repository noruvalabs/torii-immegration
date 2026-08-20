"use client";

import { Coins, Plus } from "lucide-react";
import { useCredits } from "@/lib/credits-context";
import { useI18n } from "@/lib/i18n";
import { cn } from "@/lib/utils";

export function CreditBalanceBadge({ className }: { className?: string }) {
  const { balance, setIsTopUpOpen } = useCredits();
  const { lang } = useI18n();

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
