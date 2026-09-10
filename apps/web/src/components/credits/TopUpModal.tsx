"use client";

import { useEffect, useState } from "react";
import { Sparkles, Check, Loader2, X, Coins, ShieldCheck, Zap, AlertCircle } from "lucide-react";
import { toast } from "sonner";
import { useCredits } from "@/lib/credits-context";
import { useAuth } from "@/lib/auth-context";
import { useI18n } from "@/lib/i18n";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { fetchPaymentConfig, createCheckoutSession, type PaymentConfigResponse } from "@/lib/api/payments";
import { openPaddleCheckout } from "@/lib/paddle";

export function TopUpModal() {
  const { isTopUpOpen, setIsTopUpOpen, packs, refreshBalance, balance } = useCredits();
  const { token } = useAuth();
  const { lang } = useI18n();
  const [selectedPackId, setSelectedPackId] = useState<"starter" | "standard" | "family">("standard");
  const [currency, setCurrency] = useState<"usd" | "jpy">("usd");
  const [purchasing, setPurchasing] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [paymentConfig, setPaymentConfig] = useState<PaymentConfigResponse | null>(null);
  const [loadingConfig, setLoadingConfig] = useState(false);

  useEffect(() => {
    if (!isTopUpOpen) return;
    let mounted = true;
    setLoadingConfig(true);
    fetchPaymentConfig(token ?? undefined)
      .then((cfg) => {
        if (mounted) setPaymentConfig(cfg);
      })
      .catch(() => {
        if (mounted) {
          setPaymentConfig({
            payments_enabled: true,
            provider: "paddle",
            environment: "sandbox",
            client_token: "",
            default_checkout_url: "",
          });
        }
      })
      .finally(() => {
        if (mounted) setLoadingConfig(false);
      });

    return () => {
      mounted = false;
    };
  }, [isTopUpOpen, token]);

  if (!isTopUpOpen) return null;

  const paymentsDisabled = paymentConfig !== null && !paymentConfig.payments_enabled;

  async function handlePurchase() {
    if (paymentsDisabled) {
      toast.error(
        lang === "ja" ? "現在お支払いはご利用いただけません" : "Payments Temporarily Disabled",
        {
          description:
            lang === "ja"
              ? "管理者によりオンライン決済が一時的に無効化されています。しばらく経ってから再度お試しください。"
              : "Online payments are currently paused by the administrator for maintenance. Please try again later.",
        },
      );
      return;
    }

    if (!token) {
      toast.error(
        lang === "ja" ? "ログインが必要です" : "Authentication Required",
        {
          description:
            lang === "ja"
              ? "クレジットを購入するにはログインしてください。"
              : "Please sign in to your account to purchase credit passes.",
        },
      );
      return;
    }

    setPurchasing(true);
    setSuccessMsg(null);

    try {
      const checkout = await createCheckoutSession(token, selectedPackId, currency);

      if (checkout.provider_session_id) {
        const clientToken = paymentConfig?.client_token || process.env.NEXT_PUBLIC_PADDLE_CLIENT_TOKEN;
        const env = paymentConfig?.environment || process.env.NEXT_PUBLIC_PADDLE_ENV || "sandbox";

        if (clientToken) {
          const { completed } = await openPaddleCheckout(checkout.provider_session_id, clientToken, env);
          if (completed) {
            await refreshBalance();
            setSuccessMsg(
              lang === "ja"
                ? "お支払いが完了しました！クレジットが付与されました。"
                : "Payment completed successfully! Credits added to your account.",
            );
            toast.success(
              lang === "ja" ? "決済完了" : "Payment Succeeded",
              {
                description:
                  lang === "ja"
                    ? `${checkout.credits} 件分の申請パスが追加されました。`
                    : `${checkout.credits} Application Pass(es) credited.`,
              },
            );
          }
        } else if (checkout.checkout_url) {
          window.location.href = checkout.checkout_url;
        }
      } else if (checkout.checkout_url) {
        window.location.href = checkout.checkout_url;
      }
    } catch (err) {
      toast.error(
        lang === "ja" ? "決済エラー" : "Checkout Failed",
        {
          description: err instanceof Error ? err.message : "Failed to initiate checkout.",
        },
      );
    } finally {
      setPurchasing(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-150">
      <div className="relative w-full max-w-2xl rounded-2xl border bg-card p-6 shadow-2xl space-y-6 animate-in zoom-in-95 duration-150 max-h-[90vh] overflow-y-auto">
        {/* Close Button */}
        <button
          type="button"
          onClick={() => setIsTopUpOpen(false)}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-muted-foreground hover:bg-muted transition-colors cursor-pointer"
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

        {/* Payments Disabled Notice */}
        {paymentsDisabled && (
          <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-xs space-y-1 animate-in fade-in">
            <div className="flex items-center gap-2 font-bold text-amber-700 dark:text-amber-400">
              <AlertCircle className="size-4 shrink-0" />
              <span>
                {lang === "ja"
                  ? "オンライン決済は現在メンテナンス中です"
                  : "Online Payments Temporarily Disabled"}
              </span>
            </div>
            <p className="text-muted-foreground leading-relaxed pl-6">
              {lang === "ja"
                ? "管理者によりオンライン決済およびクレジットの新規購入が一時停止されています。既存の残高および保有クレジットは引き続き通常通りご利用いただけます。"
                : "Credit purchases are currently paused by the system administrator for scheduled maintenance. You can continue using all features with your existing balance."}
            </p>
          </div>
        )}

        {/* Currency Switcher */}
        <div className="flex items-center justify-between border-b pb-4">
          <span className="text-xs font-semibold text-foreground">
            {lang === "ja" ? "お支払い通貨の選択" : "Select Currency"}
          </span>
          <div className="inline-flex rounded-lg border bg-muted/30 p-0.5 text-xs font-semibold">
            <button
              type="button"
              onClick={() => setCurrency("usd")}
              className={`px-3 py-1 rounded-md transition-all cursor-pointer ${
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
              className={`px-3 py-1 rounded-md transition-all cursor-pointer ${
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
            <Check className="size-4 shrink-0" />
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
            <span>
              {lang === "ja"
                ? "申請パスに含まれるすべての機能（追加料金なし）"
                : "100% All-Inclusive Per Application Pass"}
            </span>
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
            disabled={purchasing || loadingConfig || paymentsDisabled}
            className="min-w-44 h-10 font-bold gap-2 shadow-md"
          >
            {purchasing ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                {lang === "ja" ? "決済画面を準備中…" : "Opening Checkout…"}
              </>
            ) : paymentsDisabled ? (
              <>
                <AlertCircle className="size-4" />
                {lang === "ja" ? "現在購入停止中" : "Purchases Disabled"}
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
