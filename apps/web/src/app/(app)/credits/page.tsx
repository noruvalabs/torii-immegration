"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Coins,
  Sparkles,
  Zap,
  ShieldCheck,
  FileText,
  ScanText,
  Bot,
  Clock,
  Loader2,
  RefreshCw,
  FolderKanban,
  CheckCircle2,
} from "lucide-react";
import { useCredits } from "@/lib/credits-context";
import { useI18n } from "@/lib/i18n";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";

export default function CreditsPage() {
  const { balance, loading, packs, transactions, purchasePack, refreshBalance } = useCredits();
  const { lang } = useI18n();

  const [selectedPackId, setSelectedPackId] = useState<"starter" | "standard" | "family">("standard");
  const [currency, setCurrency] = useState<"usd" | "jpy">("usd");
  const [purchasing, setPurchasing] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  async function handlePurchase(packId: "starter" | "standard" | "family") {
    setPurchasing(true);
    try {
      await purchasePack(packId, currency);
      toast.success(
        lang === "ja"
          ? "クレジットの購入が完了しました！即時反映されました。"
          : "Application Passes successfully added to your balance!",
      );
    } catch {
      toast.error(lang === "ja" ? "購入に失敗しました。" : "Failed to purchase credits.");
    } finally {
      setPurchasing(false);
    }
  }

  async function handleRefresh() {
    setRefreshing(true);
    try {
      await refreshBalance();
      toast.success(lang === "ja" ? "残高を更新しました" : "Credit balance refreshed");
    } finally {
      setRefreshing(false);
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-8 p-4 sm:p-6 lg:p-8 animate-in fade-in duration-200">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b pb-6">
        <div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground font-medium mb-1">
            <Link href="/dashboard" className="hover:text-primary transition-colors">
              {lang === "ja" ? "ダッシュボード" : "Dashboard"}
            </Link>
            <span>/</span>
            <span className="text-foreground">{lang === "ja" ? "クレジット・パス" : "Credits & Passes"}</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground flex items-center gap-2.5">
            <Coins className="size-7 text-amber-500" />
            <span>{lang === "ja" ? "クレジット残高と申請パス" : "Credits & Application Passes"}</span>
          </h1>
          <p className="text-xs sm:text-sm text-muted-foreground mt-1 max-w-2xl">
            {lang === "ja"
              ? "Toriiでは 1クレジット＝1件のビザ申請完全パスです。公的PDF出力、AI法令相談、OCR抽出のすべてが含まれます。"
              : "In Torii, 1 Credit = 1 Full Application Pass. Each pass unlocks the entire official filing kit, government PDF generation, AI copilot, and OCR extraction."}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={refreshing || loading}
            className="h-9 gap-1.5 text-xs font-semibold rounded-md"
          >
            <RefreshCw className={`size-3.5 ${refreshing ? "animate-spin" : ""}`} />
            <span>{lang === "ja" ? "残高更新" : "Refresh"}</span>
          </Button>
          <Link
            href="/cases"
            className="inline-flex items-center justify-center h-9 px-3 gap-1.5 text-xs font-semibold rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-xs"
          >
            <FolderKanban className="size-3.5" />
            <span>{lang === "ja" ? "申請案件一覧" : "My Cases"}</span>
          </Link>
        </div>
      </div>

      {/* Balance Summary Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* Metric 1: Available Passes */}
        <Card className="border-amber-500/30 bg-gradient-to-br from-amber-500/5 via-card to-card shadow-xs relative overflow-hidden rounded-xl">
          <div className="absolute top-0 right-0 p-4 opacity-10">
            <Coins className="size-24 text-amber-500" />
          </div>
          <CardHeader className="pb-2">
            <CardDescription className="text-xs font-semibold text-amber-600 dark:text-amber-400 uppercase tracking-wider">
              {lang === "ja" ? "利用可能残高" : "Available Balance"}
            </CardDescription>
            <CardTitle className="text-3xl sm:text-4xl font-black text-foreground flex items-baseline gap-2">
              <span>{balance}</span>
              <span className="text-sm font-bold text-muted-foreground">
                {lang === "ja" ? "申請パス" : balance === 1 ? "Application Pass" : "Application Passes"}
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <p className="text-xs text-muted-foreground">
              {balance > 0
                ? lang === "ja"
                  ? `現在、最大 ${balance} 件のビザ申請を公的書類まで完全作成・出力できます。`
                  : `You can complete and export up to ${balance} full visa application dossier(s).`
                : lang === "ja"
                ? "残高がありません。下記より申請パスを追加購入できます。"
                : "No active passes. Top up below to unlock dossier exports."}
            </p>
          </CardContent>
        </Card>

        {/* Metric 2: Initial Free Grant */}
        <Card className="border shadow-xs rounded-xl">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardDescription className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                {lang === "ja" ? "新規登録特典" : "Welcome Bonus"}
              </CardDescription>
              <Badge tone="success" className="text-[10px]">
                {lang === "ja" ? "3件分 無料" : "3 Free Cases"}
              </Badge>
            </div>
            <CardTitle className="text-xl font-bold text-foreground flex items-center gap-1.5">
              <Sparkles className="size-4 text-emerald-500" />
              <span>3 Free Passes</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <p className="text-xs text-muted-foreground">
              {lang === "ja"
                ? "新規登録者全員に3パス（3件分の申請完了パス）が付与されています。"
                : "Every registered user receives 3 complimentary passes to complete initial cases for free."}
            </p>
          </CardContent>
        </Card>

        {/* Metric 3: Value Included */}
        <Card className="border shadow-xs rounded-xl">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardDescription className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                {lang === "ja" ? "パスに含まれる機能" : "All-Inclusive Kit"}
              </CardDescription>
              <ShieldCheck className="size-4 text-primary" />
            </div>
            <CardTitle className="text-xl font-bold text-foreground">
              100% Inclusive
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <p className="text-xs text-muted-foreground">
              {lang === "ja"
                ? "OCR自動抽出、AI法令アドバイス、公的PDF申請書出力のすべてに追加料金なし。"
                : "Includes auto-OCR, statutory AI copilot, checklist audit, and official Ministry of Justice PDFs."}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Top Up / Buy Passes Section */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h2 className="text-lg sm:text-xl font-bold text-foreground flex items-center gap-2">
              <Zap className="size-5 text-amber-500" />
              <span>{lang === "ja" ? "申請パスの追加購入（トップアップ）" : "Purchase Application Passes"}</span>
            </h2>
            <p className="text-xs text-muted-foreground">
              {lang === "ja"
                ? "サブスクリプション（月額課金）ではありません。必要な分だけ1回限りの購入です。"
                : "No recurring subscriptions or hidden lock-ins. Pay once, use whenever you need."}
            </p>
          </div>

          {/* Currency Switcher */}
          <div className="flex items-center gap-2 self-start sm:self-auto">
            <span className="text-xs text-muted-foreground font-medium">
              {lang === "ja" ? "通貨:" : "Currency:"}
            </span>
            <div className="inline-flex rounded-lg border bg-muted/40 p-0.5 text-xs font-semibold">
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
        </div>

        {/* 3 Pricing Packages Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {packs.map((pack) => {
            const isSelected = selectedPackId === pack.id;
            const price =
              currency === "usd"
                ? `$${pack.price_usd.toFixed(2)}`
                : `¥${pack.price_jpy.toLocaleString()}`;

            return (
              <div
                key={pack.id}
                onClick={() => setSelectedPackId(pack.id as "starter" | "standard" | "family")}
                className={`relative flex flex-col justify-between rounded-xl border p-5 cursor-pointer transition-all ${
                  isSelected
                    ? "border-primary bg-primary/5 shadow-md ring-2 ring-primary/40"
                    : "border-border bg-card hover:bg-muted/30 hover:border-border/80 shadow-xs"
                }`}
              >
                {pack.badge && (
                  <div className="absolute -top-3 right-4">
                    <span className="rounded-full bg-primary px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-primary-foreground shadow-xs">
                      {pack.badge}
                    </span>
                  </div>
                )}

                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-bold text-foreground">
                      {lang === "ja" ? pack.name_ja : pack.name}
                    </span>
                  </div>

                  <div className="flex items-baseline gap-1.5">
                    <span className="text-3xl font-black text-foreground">{price}</span>
                    <span className="text-xs text-muted-foreground font-medium">
                      / {pack.credits} {pack.credits === 1 ? "Pass" : "Passes"}
                    </span>
                  </div>

                  <div className="inline-flex items-center gap-1 text-xs font-semibold text-primary bg-primary/10 px-2.5 py-1 rounded-md">
                    <Zap className="size-3.5" />
                    <span>{pack.credits} {lang === "ja" ? "件 申請パス" : pack.credits === 1 ? "Application Pass" : "Application Passes"}</span>
                  </div>

                  <p className="text-xs text-muted-foreground leading-relaxed pt-1">
                    {lang === "ja" ? pack.description_ja : pack.description}
                  </p>
                </div>

                <div className="space-y-3 pt-4 border-t mt-4">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">
                      {lang === "ja" ? "1件あたり実質" : "Cost per case"}
                    </span>
                    <span className="font-bold text-foreground">
                      {currency === "usd"
                        ? `$${(pack.price_usd / pack.credits).toFixed(2)}`
                        : `¥${Math.round(pack.price_jpy / pack.credits).toLocaleString()}`}
                    </span>
                  </div>

                  <Button
                    disabled={purchasing}
                    onClick={(e) => {
                      e.stopPropagation();
                      handlePurchase(pack.id as "starter" | "standard" | "family");
                    }}
                    className={`w-full text-xs font-bold h-9 rounded-md ${
                      isSelected ? "bg-primary text-primary-foreground" : "bg-muted text-foreground hover:bg-primary hover:text-primary-foreground"
                    }`}
                  >
                    {purchasing && selectedPackId === pack.id ? (
                      <Loader2 className="size-3.5 animate-spin" />
                    ) : (
                      <span>{lang === "ja" ? `${price} で購入` : `Buy ${price}`}</span>
                    )}
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Feature Breakdown Card */}
      <Card className="border shadow-xs rounded-xl">
        <CardHeader>
          <CardTitle className="text-base font-bold text-foreground flex items-center gap-2">
            <CheckCircle2 className="size-5 text-emerald-500" />
            <span>{lang === "ja" ? "すべての申請パスに含まれる標準機能" : "What is Included with Every Application Pass"}</span>
          </CardTitle>
          <CardDescription className="text-xs">
            {lang === "ja"
              ? "日本の行政書士費用（¥80,000〜¥180,000）と比較して、圧倒的なコストパフォーマンスで公式書類一式を作成できます。"
              : "Compare with traditional Tokyo immigration attorney fees ($550–$1,200). Everything you need to file is included."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="flex flex-col gap-1.5 rounded-lg border bg-muted/10 p-3">
              <div className="flex items-center gap-2 text-xs font-bold text-foreground">
                <FileText className="size-4 text-primary" />
                <span>Official PDF Packets</span>
              </div>
              <p className="text-[11px] text-muted-foreground leading-snug">
                Official MOJ / ISA forms (別記様式) generated with flawless pixel precision.
              </p>
            </div>

            <div className="flex flex-col gap-1.5 rounded-lg border bg-muted/10 p-3">
              <div className="flex items-center gap-2 text-xs font-bold text-foreground">
                <ScanText className="size-4 text-primary" />
                <span>Automated OCR Scan</span>
              </div>
              <p className="text-[11px] text-muted-foreground leading-snug">
                Extract Passport, Residence Card (在留カード), and Tax slips directly into your intake.
              </p>
            </div>

            <div className="flex flex-col gap-1.5 rounded-lg border bg-muted/10 p-3">
              <div className="flex items-center gap-2 text-xs font-bold text-foreground">
                <Bot className="size-4 text-primary" />
                <span>AI Immigration Copilot</span>
              </div>
              <p className="text-[11px] text-muted-foreground leading-snug">
                24/7 statutory guidance, tax compliance checks, and legal question answers.
              </p>
            </div>

            <div className="flex flex-col gap-1.5 rounded-lg border bg-muted/10 p-3">
              <div className="flex items-center gap-2 text-xs font-bold text-foreground">
                <ShieldCheck className="size-4 text-primary" />
                <span>Checklist & Risk Audit</span>
              </div>
              <p className="text-[11px] text-muted-foreground leading-snug">
                Verified compliance audit preventing common visa rejection triggers.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Transaction & Usage Ledger */}
      <Card className="border shadow-xs rounded-xl">
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <div>
            <CardTitle className="text-base font-bold text-foreground flex items-center gap-2">
              <Clock className="size-4 text-primary" />
              <span>{lang === "ja" ? "クレジット利用履歴・取引元帳" : "Credit Transactions & Usage Ledger"}</span>
            </CardTitle>
            <CardDescription className="text-xs">
              {lang === "ja" ? "パスの付与、購入、ケース利用の全履歴" : "Audit trail of all grants, top-ups, and case unlocks"}
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          {transactions.length === 0 ? (
            <div className="py-8 text-center text-xs text-muted-foreground">
              {lang === "ja" ? "取引履歴はまだありません。" : "No credit transactions recorded yet."}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b bg-muted/30 text-muted-foreground font-semibold">
                    <th className="py-2.5 px-3">Date</th>
                    <th className="py-2.5 px-3">Type</th>
                    <th className="py-2.5 px-3">Description</th>
                    <th className="py-2.5 px-3 text-right">Amount</th>
                    <th className="py-2.5 px-3 text-right">Balance After</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {transactions.map((tx) => {
                    const isCredit = tx.amount > 0;
                    return (
                      <tr key={tx.id} className="hover:bg-muted/20 transition-colors">
                        <td className="py-2.5 px-3 text-muted-foreground whitespace-nowrap">
                          {tx.created_at ? new Date(tx.created_at).toLocaleDateString() : "Recent"}
                        </td>
                        <td className="py-2.5 px-3 whitespace-nowrap">
                          <Badge
                            tone={isCredit ? "success" : "default"}
                            className="text-[10px] font-semibold"
                          >
                            {tx.feature.replace(/_/g, " ")}
                          </Badge>
                        </td>
                        <td className="py-2.5 px-3 text-foreground font-medium">
                          {tx.description}
                        </td>
                        <td
                          className={`py-2.5 px-3 text-right font-bold whitespace-nowrap ${
                            isCredit ? "text-emerald-600 dark:text-emerald-400" : "text-foreground"
                          }`}
                        >
                          {isCredit ? `+${tx.amount}` : tx.amount}
                        </td>
                        <td className="py-2.5 px-3 text-right font-semibold text-muted-foreground whitespace-nowrap">
                          {tx.balance_after} Passes
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
