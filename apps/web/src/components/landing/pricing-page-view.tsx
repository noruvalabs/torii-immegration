"use client";

import Link from "next/link";
import { ArrowLeft, Check, X, ShieldCheck, HelpCircle, Sparkles } from "lucide-react";
import { Pricing } from "./pricing";
import { useLang } from "./i18n";
import { dictionary } from "./dictionary";
import { Reveal } from "./reveal";

export function PricingPageView() {
  const { lang } = useLang();
  const t = dictionary[lang];

  const comparisonRows = [
    {
      feature: lang === "ja" ? "法定書式への高精度な自動転記" : "Official Statutory Form Auto-Population",
      torii: true,
      scrivener: true,
      manual: false,
    },
    {
      feature: lang === "ja" ? "入管公表基準への直接の根拠明記" : "Direct Sourcing to Official ISA Rules",
      torii: true,
      scrivener: true,
      manual: false,
    },
    {
      feature: lang === "ja" ? "所属機関区分に応じた必要書類判定" : "Employer Category Checklist Calculation",
      torii: true,
      scrivener: true,
      manual: false,
    },
    {
      feature: lang === "ja" ? "事前チェックによる記載矛盾リスク検知" : "Pre-Submission Inconsistency Detection",
      torii: true,
      scrivener: true,
      manual: false,
    },
    {
      feature: lang === "ja" ? "理由書・滞在計画書の生成・編集" : "Statement of Purpose & Cover Letter Drafts",
      torii: true,
      scrivener: true,
      manual: false,
    },
    {
      feature: lang === "ja" ? "何度でも修正・再出力が可能" : "Unlimited Revisions & Re-exports",
      torii: true,
      scrivener: false,
      manual: true,
    },
    {
      feature: lang === "ja" ? "標準的な費用" : "Typical Cost",
      toriiText: lang === "ja" ? "3件無料 / 以降 買い切り" : "3 passes free, then pay-per-case",
      scrivenerText: lang === "ja" ? "¥100,000 〜 ¥300,000" : "¥100,000 – ¥300,000+",
      manualText: lang === "ja" ? "0円（莫大な時間と不備リスク）" : "Free (High error risk & delay)",
    },
  ];

  return (
    <div className="pt-24 pb-20 sm:pt-28 sm:pb-28">
      {/* Top breadcrumb */}
      <div className="mx-auto max-w-6xl px-6 pt-4 sm:px-8">
        <Reveal>
          <div className="flex items-center justify-between border-b border-border/60 pb-5">
            <Link
              href="/"
              className="inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
            >
              <ArrowLeft className="size-4" />
              {lang === "ja" ? "ホームに戻る" : "Back to Home"}
            </Link>

            <span className="rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-semibold text-emerald-600 dark:text-emerald-400">
              {lang === "ja" ? "3件分の無料パスプレゼント中" : "3 Free Starter Passes Included"}
            </span>
          </div>
        </Reveal>
      </div>

      {/* Main Pricing Interactive Section */}
      <Pricing />

      {/* Detailed Feature Comparison Matrix */}
      <div className="mx-auto mt-16 max-w-5xl px-6 sm:mt-24 sm:px-8">
        <div className="text-center">
          <p className="text-xs font-semibold uppercase tracking-wider text-primary">
            {lang === "ja" ? "比較表" : "Comparison"}
          </p>
          <h2 className="mt-2 text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
            {lang === "ja" ? "Toriiと従来の手続き方法の比較" : "How Torii compares to alternatives"}
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-sm text-muted-foreground">
            {lang === "ja"
              ? "高額な士業への丸投げでも、不安な手探りの自力申請でもない、第三の賢い選択肢です。"
              : "A modern alternative between expensive legal retainers and stressful, unguided manual filings."}
          </p>
        </div>

        <div className="mt-10 overflow-hidden rounded-2xl border border-border/70 bg-card shadow-panel">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-border/70 bg-muted/40 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                <tr>
                  <th className="p-4 sm:p-5">{lang === "ja" ? "機能・特徴" : "Feature / Capability"}</th>
                  <th className="bg-primary/5 p-4 text-primary sm:p-5">Torii</th>
                  <th className="p-4 sm:p-5">{lang === "ja" ? "行政書士・弁護士" : "Lawyer / Scrivener"}</th>
                  <th className="p-4 sm:p-5">{lang === "ja" ? "手作業での自力申請" : "Manual Self-Filing"}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {comparisonRows.map((row, idx) => (
                  <tr key={idx} className="transition-colors hover:bg-muted/20">
                    <td className="p-4 font-medium text-foreground sm:p-5">{row.feature}</td>
                    <td className="bg-primary/5 p-4 font-semibold text-primary sm:p-5">
                      {row.toriiText ? (
                        row.toriiText
                      ) : row.torii ? (
                        <Check className="size-5 text-emerald-600 dark:text-emerald-400" />
                      ) : (
                        <X className="size-5 text-muted-foreground/50" />
                      )}
                    </td>
                    <td className="p-4 text-muted-foreground sm:p-5">
                      {row.scrivenerText ? (
                        row.scrivenerText
                      ) : row.scrivener ? (
                        <Check className="size-5 text-emerald-600 dark:text-emerald-400" />
                      ) : (
                        <X className="size-5 text-muted-foreground/50" />
                      )}
                    </td>
                    <td className="p-4 text-muted-foreground sm:p-5">
                      {row.manualText ? (
                        row.manualText
                      ) : row.manual ? (
                        <Check className="size-5 text-emerald-600 dark:text-emerald-400" />
                      ) : (
                        <X className="size-5 text-muted-foreground/50" />
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* 30-Day Guarantee Banner */}
        <div className="mt-12">
          <div className="flex flex-col items-start gap-5 rounded-2xl border border-emerald-500/30 bg-emerald-500/5 p-6 sm:flex-row sm:items-center sm:justify-between sm:p-8">
            <div className="flex items-start gap-4">
              <div className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-emerald-500/15 text-emerald-600 dark:text-emerald-400">
                <ShieldCheck className="size-6" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-foreground">
                  {lang === "ja" ? "未使用クレジット 30日間全額返金保証" : "30-Day Money-Back Guarantee"}
                </h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  {lang === "ja"
                    ? "ご購入から30日以内の未使用申請パスは、理由を問わず100%返金の対象となります。安心してお試しいただけます。"
                    : "Any unused case passes purchased within the last 30 days are eligible for a 100% money-back refund, no questions asked."}
                </p>
              </div>
            </div>
            <Link
              href="/refund"
              className="shrink-0 text-sm font-semibold text-emerald-600 hover:underline dark:text-emerald-400"
            >
              {lang === "ja" ? "返金ポリシーを見る →" : "Read Refund Policy →"}
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
