"use client";

import Link from "next/link";
import { ArrowRight, ShieldCheck, FileCheck, Lock, Building2, Globe2, Sparkles } from "lucide-react";
import { useLang } from "./i18n";
import { Reveal } from "./reveal";
import { ToriiLogo } from "@/components/brand/ToriiLogo";

export function SiteFooter() {
  const { lang } = useLang();
  const isJa = lang === "ja";

  const popularVisas = [
    { href: "/visa/japan", label: isJa ? "日本ビザ (Japan)" : "Japan Tourist & Visit Visa", flag: "🇯🇵" },
    { href: "/visa/india", label: isJa ? "インドビザ (India)" : "India Medical & Tourist Visa", flag: "🇮🇳" },
    { href: "/visa/saudi-arabia", label: isJa ? "サウジアラビア (Saudi Arabia)" : "Saudi Arabia eVisa & Umrah", flag: "🇸🇦" },
    { href: "/visa/united-states", label: isJa ? "アメリカ (USA)" : "United States B1/B2 DS-160", flag: "🇺🇸" },
    { href: "/visa/canada", label: isJa ? "カナダ (Canada)" : "Canada Visitor TRV", flag: "🇨🇦" },
    { href: "/visa/france", label: isJa ? "フランス・シェンゲン" : "France & Schengen Visa", flag: "🇫🇷" },
    { href: "/#destinations", label: isJa ? "すべての国を見る →" : "View All Supported Visas →" },
  ];

  const serviceLinks = [
    { href: "/#how-it-works", label: isJa ? "オンライン申請代行" : "Online Portal Filing Concierge" },
    { href: "/#how-it-works", label: isJa ? "公式書類・申請書作成" : "Official Embassy Form Preparation" },
    { href: "/#coverage", label: isJa ? "適格性チェック" : "Eligibility Pre-Check" },
    { href: "/pricing", label: isJa ? "料金プラン" : "Transparent Pricing & Fees" },
    { href: "/about", label: isJa ? "会社概要・ビジョン" : "About Torii & Mission" },
  ];

  const resourceLinks = [
    { href: "/blog", label: isJa ? "ビザ申請ガイド" : "Visa Guides & Country Insights" },
    { href: "/#faq", label: isJa ? "よくある質問" : "Frequently Asked Questions" },
    { href: "/cases", label: isJa ? "申請ステータス追跡" : "Track Application Status" },
    { href: "/help", label: isJa ? "カスタマーサポート" : "Help & Concierge Support" },
  ];

  const legalLinks = [
    { href: "/privacy", label: isJa ? "プライバシーポリシー" : "Privacy Policy" },
    { href: "/terms", label: isJa ? "利用規約" : "Terms of Service" },
    { href: "/refund", label: isJa ? "返金ポリシー" : "Refund & Cancellation Policy" },
    { href: "/cookies", label: isJa ? "クッキーポリシー" : "Cookie Preferences" },
  ];

  return (
    <footer className="relative overflow-hidden rounded-t-[2.5rem] sm:rounded-t-[3.5rem] border-t border-white/10 bg-[#080B14] text-white pt-16 pb-12 sm:pt-20 sm:pb-14">
      {/* Ambient Glow Blobs */}
      <div
        aria-hidden
        className="pointer-events-none absolute -top-32 left-1/4 size-96 rounded-full bg-primary/20 blur-[140px]"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute top-1/2 -right-20 size-96 rounded-full bg-indigo-500/15 blur-[140px]"
      />

      <div className="relative mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 space-y-14">
        {/* Top Grid: Brand & CTA on left, 4 Nav Columns on right */}
        <div className="grid gap-12 lg:grid-cols-12 lg:gap-8 items-start">
          {/* Left Column: Brand, Mission, Primary CTA */}
          <div className="lg:col-span-5 space-y-6">
            <Reveal>
              <Link href="/" className="inline-flex items-center gap-3 group">
                <ToriiLogo size={36} />
                <span className="text-2xl font-extrabold tracking-tight text-white group-hover:text-primary transition-colors">
                  Torii
                </span>
              </Link>

              <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white leading-tight mt-4">
                {isJa
                  ? "ビザ申請の複雑なオンライン作業を、すべてワンストップで。"
                  : "Visa applications & concierge filing, simplified."}
              </h2>

              <p className="text-sm text-white/70 max-w-md leading-relaxed">
                {isJa
                  ? "複雑な政府ポータルや決済エラーに悩む必要はありません。Toriiに一度情報を入力するだけで、公式書類作成からポータル申請・政府手数料納付まで代行します。"
                  : "Skip the frustrating government portals and payment roadblocks. Provide your details once — Torii formats official embassy forms, submits on official portals, and pays statutory visa fees on your behalf."}
              </p>

              <div className="pt-2 flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
                <Link
                  href="/scope"
                  className="group inline-flex h-12 items-center justify-center gap-2 rounded-xl bg-primary px-6 text-sm font-bold text-primary-foreground shadow-lg shadow-primary/25 hover:bg-primary/90 transition-all active:scale-[0.98]"
                >
                  <span>{isJa ? "ビザ申請を始める" : "Start Visa Application"}</span>
                  <ArrowRight className="size-4 transition-transform duration-300 group-hover:translate-x-1" />
                </Link>

                <Link
                  href="/login"
                  className="inline-flex h-12 items-center justify-center rounded-xl border border-white/15 bg-white/5 hover:bg-white/10 px-5 text-xs font-semibold text-white/90 backdrop-blur-sm transition-colors"
                >
                  <span>{isJa ? "ログイン" : "Sign in"}</span>
                </Link>
              </div>

              {/* Trust Micro-Badges */}
              <div className="pt-2 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-white/60">
                <span className="flex items-center gap-1.5">
                  <Sparkles className="size-3.5 text-emerald-400" />
                  <span>3-Min Digital Intake</span>
                </span>
                <span className="text-white/20">·</span>
                <span className="flex items-center gap-1.5">
                  <Lock className="size-3.5 text-purple-400" />
                  <span>256-Bit Data Privacy</span>
                </span>
                <span className="text-white/20">·</span>
                <span className="flex items-center gap-1.5">
                  <ShieldCheck className="size-3.5 text-blue-400" />
                  <span>100% Dossier Compliance</span>
                </span>
              </div>
            </Reveal>
          </div>

          {/* Right Columns: Nav Groups (7 cols) */}
          <div className="lg:col-span-7">
            <Reveal delay={100} className="grid grid-cols-2 sm:grid-cols-4 gap-8">
              {/* Column 1: Popular Visas */}
              <div className="space-y-4">
                <p className="text-xs font-bold uppercase tracking-wider text-white/90">
                  {isJa ? "対応ビザ" : "Popular Visas"}
                </p>
                <ul className="space-y-2.5 text-xs">
                  {popularVisas.map((item) => (
                    <li key={item.href + item.label}>
                      <Link
                        href={item.href}
                        className="text-white/65 hover:text-white transition-colors flex items-center gap-1.5 leading-snug"
                      >
                        {item.flag && <span className="text-sm">{item.flag}</span>}
                        <span>{item.label}</span>
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Column 2: Services */}
              <div className="space-y-4">
                <p className="text-xs font-bold uppercase tracking-wider text-white/90">
                  {isJa ? "サービス" : "Services"}
                </p>
                <ul className="space-y-2.5 text-xs">
                  {serviceLinks.map((item) => (
                    <li key={item.href + item.label}>
                      <Link
                        href={item.href}
                        className="text-white/65 hover:text-white transition-colors block leading-snug"
                      >
                        {item.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Column 3: Resources */}
              <div className="space-y-4">
                <p className="text-xs font-bold uppercase tracking-wider text-white/90">
                  {isJa ? "リソース" : "Resources"}
                </p>
                <ul className="space-y-2.5 text-xs">
                  {resourceLinks.map((item) => (
                    <li key={item.href + item.label}>
                      <Link
                        href={item.href}
                        className="text-white/65 hover:text-white transition-colors block leading-snug"
                      >
                        {item.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Column 4: Legal & Security */}
              <div className="space-y-4">
                <p className="text-xs font-bold uppercase tracking-wider text-white/90">
                  {isJa ? "規約・法務" : "Legal"}
                </p>
                <ul className="space-y-2.5 text-xs">
                  {legalLinks.map((item) => (
                    <li key={item.href + item.label}>
                      <Link
                        href={item.href}
                        className="text-white/65 hover:text-white transition-colors block leading-snug"
                      >
                        {item.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            </Reveal>
          </div>
        </div>

        {/* Middle Banner: Consular Compliance Standards */}
        <div className="border-t border-white/10 pt-8 space-y-4">
          <div className="flex items-center gap-2">
            <ShieldCheck className="size-4 text-emerald-400" />
            <p className="text-xs font-bold uppercase tracking-wider text-white/80">
              {isJa ? "公的基準・コンプライアンス準拠" : "Consular Compliance & Verification Standards"}
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs text-white/70">
            <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 p-3 backdrop-blur-xs">
              <Building2 className="size-4 text-primary shrink-0" />
              <span>Official MOFA &amp; Consular Guidelines</span>
            </div>

            <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 p-3 backdrop-blur-xs">
              <FileCheck className="size-4 text-emerald-400 shrink-0" />
              <span>VFS Global &amp; IVAC Submission Standards</span>
            </div>

            <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 p-3 backdrop-blur-xs">
              <Globe2 className="size-4 text-blue-400 shrink-0" />
              <span>Direct Government Portal Registration</span>
            </div>

            <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 p-3 backdrop-blur-xs">
              <Lock className="size-4 text-purple-400 shrink-0" />
              <span>AES-256 Encrypted Profile Vault</span>
            </div>
          </div>
        </div>

        {/* Bottom Strip: Copyright & Disclaimers */}
        <div className="border-t border-white/10 pt-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-white/50">
          <p>© {new Date().getFullYear()} Torii. Guided visa preparation &amp; concierge platform.</p>

          <p className="text-center sm:text-right text-[11px] max-w-md leading-relaxed text-white/40">
            Torii is an independent visa concierge service and is not an embassy or legal representative. We assist travelers in preparing compliant embassy dossiers and completing official portal filings.
          </p>
        </div>
      </div>
    </footer>
  );
}
