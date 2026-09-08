"use client";

import { useState } from "react";
import { Sparkles, Check, Loader2, X, Coins, ShieldCheck, Zap } from "lucide-react";
import { toast } from "sonner";
import { useCredits } from "@/lib/credits-context";
import { useI18n } from "@/lib/i18n";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export function TopUpModal() {
  const { isTopUpOpen, setIsTopUpOpen, packs, purchasePack, balance } = useCredits();
  const { lang, t } = useI18n();
  const [selectedPackId, setSelectedPackId] = useState<"starter" | "standard" | "family">("standard");
  const [currency, setCurrency] = useState<"usd" | "jpy">("usd");
  const [purchasing, setPurchasing] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  if (!isTopUpOpen) return null;

  function handlePurchase() {
    toast.error(
      lang === "ja" ? "現在お支払いはご利用いただけません" : "Payment Currently Unavailable",
      {
        description:
          lang === "ja"
            ? "オンライン決済システムは現在メンテナンス中です。しばらく経ってから再度お試しいただくか、サポートまでお問い合わせください。"
            : "Online payment processing is currently unavailable. Please try again later or contact support.",
      },
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-150">
      <div className="relative w-full max-w-2xl rounded-2xl border bg-card p-6 shadow-2xl space-y-6 animate-in zoom-in-95 duration-150">
        {/* Close Button */}
        <button
          type="button"
          onClick={() => setIsTopUpOpen(false)}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-muted-foreground hover:bg-muted transition-colors"
        >
          <X className="size-5" />
        </button>

        {/* Modal Header */}
        <div className="space-y-1.5 text-center sm:text-left">
          <div className="flex items-center gap-2 justify-center sm:justify-start">
            <div className="flex size-9 items-center justify-center rounded-xl bg-amber-500/10 text-amber-500 border border-amber-500/20">
              <Coins className="size-5" />
            </div>
            <h2 className="text-xl font-bold text-foreground">
              {lang === "ja" ? "Torii クレジットの購入" : "Top Up Torii Credits"}
            </h2>
            <Badge tone="default" className="text-xs ml-auto hidden sm:inline-flex">
              {lang === "ja" ? `残高: ${balance} クレジット` : `Current Balance: ${balance} Credits`}
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground">
            {lang === "ja"
              ? "ビザ申請書の公的PDF出力、AI法令検索、書類OCR抽出に必要なクレジットを購入します。"
              : "Credits unlock official Government Dossier Packets, AI Copilot citations, and automated document OCR."}
          </p>
        </div>

        {/* Currency Switcher */}
        <div className="flex items-center justify-between border-b pb-4">
          <span className="text-xs font-semibold text-foreground">
            {lang === "ja" ? "お支払い通貨の選択" : "Select Currency"}
          </span>
          <div className="inline-flex rounded-lg border bg-muted/30 p-0.5 text-xs font-semibold">
            <button
              type="button"
              onClick={() => setCurrency("usd")}
              className={`px-3 py-1 rounded-md transition-all ${
                currency === "usd"
                  ? "bg-background text-foreground shadow-xs font-bold"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              🇺🇸 USD ($)
            </button>
            <button
              type="button"
              onClick={() => setCurrency("jpy")}
              className={`px-3 py-1 rounded-md transition-all ${
                currency === "jpy"
                  ? "bg-background text-foreground shadow-xs font-bold"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              🇯🇵 JPY (¥)
            </button>
          </div>
        </div>

        {/* Success Alert */}
        {successMsg && (
          <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-600 font-semibold flex items-center gap-2">
            <Check className="size-4" />
            <span>{successMsg}</span>
          </div>
        )}

        {/* 3 Pricing Tier Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
          {packs.map((pack) => {
            const isSelected = selectedPackId === pack.id;
            const price =
              currency === "usd"
                ? `$${pack.price_usd.toFixed(2)}`
                : `¥${pack.price_jpy.toLocaleString()}`;

            return (
              <div
                key={pack.id}
                onClick={() => setSelectedPackId(pack.id)}
                className={`relative flex flex-col justify-between rounded-xl border p-4 cursor-pointer transition-all ${
                  isSelected
                    ? "border-primary bg-primary/5 shadow-md ring-2 ring-primary/40"
                    : "border-border bg-card hover:bg-muted/30 hover:border-border/80"
                }`}
              >
                {pack.badge && (
                  <div className="absolute -top-2.5 right-3">
                    <span className="rounded-full bg-primary px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-primary-foreground shadow-xs">
                      {pack.badge}
                    </span>
                  </div>
                )}

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-foreground">
                      {lang === "ja" ? pack.name_ja : pack.name}
                    </span>
                  </div>

                  <div className="flex items-baseline gap-1">
                    <span className="text-2xl font-black text-foreground">{price}</span>
                  </div>

                  <div className="inline-flex items-center gap-1 text-xs font-semibold text-primary bg-primary/10 px-2 py-0.5 rounded-md">
                    <Zap className="size-3" />
                    <span>{pack.credits} Credits</span>
                  </div>

                  <p className="text-[11px] text-muted-foreground leading-snug pt-1">
                    {lang === "ja" ? pack.description_ja : pack.description}
                  </p>
                </div>

                <div className="pt-3 border-t mt-3 flex items-center justify-between text-[11px]">
                  <span className="text-muted-foreground">
                    {lang === "ja" ? "1クレジットあたり" : "Per credit"}
                  </span>
                  <span className="font-semibold text-foreground">
                    {currency === "usd"
                      ? `$${(pack.price_usd / pack.credits).toFixed(2)}`
                      : `¥${Math.round(pack.price_jpy / pack.credits)}`}
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Feature Usage Value Guide */}
        <div className="rounded-xl border bg-muted/20 p-3 text-[11px] space-y-1.5">
          <div className="flex items-center gap-1.5 font-bold text-foreground">
            <ShieldCheck className="size-3.5 text-primary" />
            <span>{lang === "ja" ? "申請パスに含まれるすべての機能（追加料金なし）" : "100% All-Inclusive Per Application Pass"}</span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-muted-foreground">
            <div>📄 <strong>OCR 読み取り</strong>: 無制限</div>
            <div>🤖 <strong>AI 条文・法令相談</strong>: 無制限</div>
            <div>📋 <strong>公的申請書式</strong>: 入力・自動作成</div>
            <div>📦 <strong>大使館・出入国在留庁提出一式</strong>: 永久再出力</div>
          </div>
        </div>

        {/* Modal Action Buttons */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => setIsTopUpOpen(false)}
            disabled={purchasing}
          >
            {lang === "ja" ? "キャンセル" : "Cancel"}
          </Button>

          <Button
            type="button"
            onClick={handlePurchase}
            disabled={purchasing}
            className="min-w-40 h-10 font-bold gap-2 shadow-md"
          >
            {purchasing ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                {lang === "ja" ? "処理中…" : "Processing…"}
              </>
            ) : (
              <>
                <Sparkles className="size-4" />
                {lang === "ja" ? "クレジットを購入する" : "Purchase Credits"}
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
