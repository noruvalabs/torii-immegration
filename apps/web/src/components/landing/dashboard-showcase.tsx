"use client";

import { useEffect, useRef, useState } from "react";
import {
  FileText,
  CheckCircle2,
  Clock,
  ShieldCheck,
  Search,
  ArrowUpRight,
  Sparkles,
  Download,
  Layers,
} from "lucide-react";
import { Reveal } from "./reveal";
import { useLang } from "./i18n";
import { dictionary } from "./dictionary";
import { cn } from "@/lib/utils";

type CaseId = "renewal" | "change" | "coe";

interface CaseData {
  id: string;
  category: string;
  badge: string;
  badgeTone: "success" | "primary" | "warning";
  progress: number;
  subtitle: string;
  ruleCitation: string;
  deadlineNotice: string;
  checklist: Array<{
    title: string;
    source: string;
    status: "verified" | "pending";
  }>;
  forms: Array<{
    name: string;
    version: string;
    fields: string;
    format: string;
  }>;
}

const CASES_EN: Record<CaseId, CaseData> = {
  renewal: {
    id: "JP-2026-000047",
    category: "Work Visa (Renewal) · 技術・人文知識・国際業務",
    badge: "Forms Ready",
    badgeTone: "primary",
    progress: 87,
    subtitle: "Company Sponsor: Nikko Systems K.K.",
    ruleCitation: "Official 2026 Japanese Immigration Guidelines (MoJ 16-3)",
    deadlineNotice: "Application deadline: Dec 2, 2026 (No late grace period in Japan)",
    checklist: [
      {
        title: "Passport & Residence Card",
        source: "Originals verified · Valid through Dec 2026",
        status: "verified",
      },
      {
        title: "Certificate of Employment",
        source: "Issued by your employer within 3 months · Verified",
        status: "verified",
      },
      {
        title: "Annual Tax Withholding Slip (源泉徴収票)",
        source: "Standard tax record attached · Verified",
        status: "verified",
      },
      {
        title: "Company Statutory Tax Report",
        source: "Corporate sponsor documents attached · Verified",
        status: "verified",
      },
    ],
    forms: [
      {
        name: "Official Visa Extension Application",
        version: "2026 Government Standard Form",
        fields: "All 38 questions filled out",
        format: "Official PDF",
      },
      {
        name: "Company Sponsor Form",
        version: "Company details & corporate number linked",
        fields: "All company requirements met",
        format: "Official PDF",
      },
      {
        name: "Statement of Reasons (Draft)",
        version: "Explains your job role and qualifications",
        fields: "Pre-filled and ready to sign",
        format: "Word & PDF",
      },
    ],
  },
  change: {
    id: "JP-2026-000048",
    category: "Student to Work Visa · 在留資格変更",
    badge: "Requirements Met",
    badgeTone: "warning",
    progress: 52,
    subtitle: "University Graduate starting a new job in Japan",
    ruleCitation: "Official 2026 Status Change Procedures (MoJ 16-2)",
    deadlineNotice: "Apply before your student visa expires · Continuous legal stay required",
    checklist: [
      {
        title: "University Graduation Certificate",
        source: "Degree certificate verified",
        status: "verified",
      },
      {
        title: "Employment Contract",
        source: "Salary meets legal requirement (¥3.4M/yr)",
        status: "verified",
      },
      {
        title: "Company Registry Record",
        source: "Legal Affairs Bureau official certificate",
        status: "verified",
      },
      {
        title: "Job-to-Degree Alignment Statement",
        source: "Explains how your studies match your job duties",
        status: "pending",
      },
    ],
    forms: [
      {
        name: "Official Status Change Application",
        version: "2026 Government Standard Form",
        fields: "All 4 pages filled out",
        format: "Official PDF",
      },
      {
        name: "Company Sponsor Organization Forms",
        version: "Company representative and seal confirmed",
        fields: "Company sponsor information checked",
        format: "Official PDF",
      },
    ],
  },
  coe: {
    id: "JP-2026-000045",
    category: "New Work Visa (CoE) · 在留資格認定",
    badge: "Ready to Submit",
    badgeTone: "success",
    progress: 100,
    subtitle: "Hiring an engineer from overseas to work in Japan",
    ruleCitation: "Official 2026 Certificate of Eligibility Procedures (MoJ 16-1)",
    deadlineNotice: "Processing time: 30 to 90 days · Valid for 3 months once issued",
    checklist: [
      {
        title: "Passport Copy of Applicant",
        source: "Information page checked and verified",
        status: "verified",
      },
      {
        title: "Resume & University Degree",
        source: "Satisfies required education / experience criteria",
        status: "verified",
      },
      {
        title: "Sponsoring Company Financial Report",
        source: "Latest audited company report attached",
        status: "verified",
      },
      {
        title: "Self-Addressed Return Envelope",
        source: "460 JPY registered delivery stamp attached",
        status: "verified",
      },
    ],
    forms: [
      {
        name: "Official CoE Application Form",
        version: "2026 Government Standard Form",
        fields: "All 38 questions filled out",
        format: "Official PDF",
      },
      {
        name: "Complete Submission Dossier",
        version: "Arranged in Tokyo Immigration inspection order",
        fields: "Ready for counter submission or online filing",
        format: "Submission PDF",
      },
    ],
  },
};

const CASES_JA: Record<CaseId, CaseData> = {
  renewal: {
    id: "JP-2026-000047",
    category: "就労ビザ (技術・人文知識・国際業務) · 在留期間更新",
    badge: "申請書式 作成完了",
    badgeTone: "primary",
    progress: 87,
    subtitle: "所属機関：カテゴリー3（日光システムズ株式会社 法人番号 5010001029384）",
    ruleCitation: "出入国在留管理庁 在留期間更新許可のガイドライン (2026年4月改定基準)",
    deadlineNotice: "申請受付期間：2026年9月3日〜12月2日 · 在留期限：2026年12月2日（猶予期間なし）",
    checklist: [
      {
        title: "旅券及び在留カード (原本提示)",
        source: "出入国在留管理庁 法定提示基準照合済 · 2026年12月まで有効",
        status: "verified",
      },
      {
        title: "在職証明書",
        source: "発行後3ヶ月以内 · 日光システムズ株式会社 人事発行確認済",
        status: "verified",
      },
      {
        title: "前年分の給与所得の源泉徴収票",
        source: "国税庁法定調書基準 · 照合・添付完了",
        status: "verified",
      },
      {
        title: "前年分の法定調書合計表の控え",
        source: "税務署受付印確認済 · カテゴリー3立証書類",
        status: "verified",
      },
    ],
    forms: [
      {
        name: "在留期間更新許可申請書 (技術・人文知識・国際業務)",
        version: "法務省 2026.1 正規法定様式 (手続き 16-3)",
        fields: "全38項目 自動マッピング済",
        format: "正規PDF",
      },
      {
        name: "所属機関等作成用 1〜2 (カテゴリー3組織概要書)",
        version: "法人番号 5010001029384 照合済",
        fields: "会社規模・法定要件チェック済",
        format: "正規PDF",
      },
      {
        name: "理由書 (業務内容詳細説明書)",
        version: "法定在留期間更新 理由書ドラフト",
        fields: "職務内容と専攻の整合性を記載済",
        format: "Word (.DOCX) & PDF",
      },
    ],
  },
  change: {
    id: "JP-2026-000048",
    category: "在留資格変更許可申請 (留学 → 就労・技人国)",
    badge: "適格性審査 通過",
    badgeTone: "warning",
    progress: 52,
    subtitle: "大学卒業からITスペシャリストへの移行（カテゴリー3企業採用）",
    ruleCitation: "出入国管理及び難民認定法 第20条 · 在留資格の変更 (手続き 16-2)",
    deadlineNotice: "留学在留期限前の申請が必要 · 継続的適法滞在要件適合",
    checklist: [
      {
        title: "大学卒業証明書 / 学位記",
        source: "日本の認可大学 学士号取得確認済",
        status: "verified",
      },
      {
        title: "労働条件通知書 / 雇用契約書",
        source: "法定報酬基準（年収340万円）を充足 · 照合済",
        status: "verified",
      },
      {
        title: "登記事項証明書 (履歴事項全部証明書)",
        source: "法務局発行（3ヶ月以内）原本確認済",
        status: "verified",
      },
      {
        title: "専攻科目と職務内容の関連性説明書",
        source: "情報科学専攻とソフトウェア開発業務の整合立証",
        status: "pending",
      },
    ],
    forms: [
      {
        name: "在留資格変更許可申請書 (技術・人文知識・国際業務)",
        version: "法務省 2026.1 正規法定様式 (手続き 16-2)",
        fields: "全4ページ 自動入力済",
        format: "正規PDF",
      },
      {
        name: "所属機関等作成用 1〜4 (所属機関情報)",
        version: "カテゴリー3 準拠仕様書式",
        fields: "代表者印・企業データ確認済",
        format: "正規PDF",
      },
    ],
  },
  coe: {
    id: "JP-2026-000045",
    category: "在留資格認定証明書交付申請 (CoE · 新規呼び寄せ)",
    badge: "窓口提出準備 完了",
    badgeTone: "success",
    progress: 100,
    subtitle: "海外エンジニアの直接採用 · カテゴリー2上場企業スポンサー",
    ruleCitation: "出入国管理及び難民認定法 第7条第1項第2号 · 認定証明書交付手続 (手続き 16-1)",
    deadlineNotice: "標準処理期間：30日〜90日 · 交付後3ヶ月以内に領事館査証発給と入国が必要",
    checklist: [
      {
        title: "申請人旅券の身分事項ページ写し",
        source: "海外査証発給基準照合済 · 有効期限確認済",
        status: "verified",
      },
      {
        title: "履歴書及び学歴証明書",
        source: "法定資格要件（情報科学学士号・実務要件）充足",
        status: "verified",
      },
      {
        title: "所属機関の直近年度決算書写し",
        source: "カテゴリー2上場企業財務諸表 · 確認済",
        status: "verified",
      },
      {
        title: "返信用封筒 (460円切手貼付)",
        source: "簡易書留対応 · 宛先明記完了",
        status: "verified",
      },
    ],
    forms: [
      {
        name: "在留資格認定証明書交付申請書 (CoE申請書)",
        version: "法務省 2026.1 正規法定様式 (手続き 16-1)",
        fields: "全38法定項目 作成完了",
        format: "正規PDF",
      },
      {
        name: "提出用書類一式パッケージ (Packet)",
        version: "東京出入国在留管理局 審査順序準拠",
        fields: "法定提出順序にバインド済",
        format: "提出用PDF",
      },
    ],
  },
};

export function DashboardShowcase() {
  const { lang } = useLang();
  const t = dictionary[lang];
  const [selectedCase, setSelectedCase] = useState<CaseId>("renewal");
  const [activeTab, setActiveTab] = useState<"checklist" | "forms">("checklist");

  // Parallax & 3D tilt state
  const sectionRef = useRef<HTMLDivElement>(null);
  const [scrollYProgress, setScrollYProgress] = useState(0.5);
  const [mouseTilt, setMouseTilt] = useState({ x: 0, y: 0 });

  useEffect(() => {
    let ticking = false;

    const handleScroll = () => {
      if (!ticking) {
        window.requestAnimationFrame(() => {
          if (sectionRef.current) {
            const rect = sectionRef.current.getBoundingClientRect();
            const windowHeight = window.innerHeight;
            const progress = Math.max(
              0,
              Math.min(1, (windowHeight - rect.top) / (windowHeight + rect.height)),
            );
            setScrollYProgress(progress);
          }
          ticking = false;
        });
        ticking = true;
      }
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width - 0.5;
    const y = (e.clientY - rect.top) / rect.height - 0.5;
    setMouseTilt({ x: x * 4, y: y * -4 });
  };

  const handleMouseLeave = () => {
    setMouseTilt({ x: 0, y: 0 });
  };

  const casesMap = lang === "ja" ? CASES_JA : CASES_EN;
  const activeData = casesMap[selectedCase];

  // Parallax translation calculations
  const dashboardTranslateY = (scrollYProgress - 0.5) * -25;
  const dashboardRotateX = (0.5 - scrollYProgress) * 4 + mouseTilt.y;
  const dashboardRotateY = mouseTilt.x;

  const chip1Y = (scrollYProgress - 0.5) * -65;
  const chip2Y = (scrollYProgress - 0.5) * 55;
  const chip3Y = (scrollYProgress - 0.5) * -40;

  return (
    <section
      ref={sectionRef}
      id="dashboard-showcase"
      className="relative overflow-hidden border-t border-border/70 bg-gradient-to-b from-background via-muted/20 to-background py-20 lg:py-28"
    >
      {/* Background ambient light mesh */}
      <div
        aria-hidden
        className="pointer-events-none absolute -top-40 left-1/2 -translate-x-1/2 size-[650px] rounded-full bg-primary/8 blur-[120px]"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute bottom-0 left-1/4 size-[450px] rounded-full bg-blue-500/5 blur-[100px]"
      />

      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <Reveal className="mx-auto max-w-3xl text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-3.5 py-1 text-xs font-medium text-primary backdrop-blur-sm">
            <span className="size-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span>{t.dashboardShowcase.eyebrow}</span>
          </div>
          <h2 className="mt-4 text-3xl font-bold tracking-tight text-foreground sm:text-4xl lg:text-5xl">
            {t.dashboardShowcase.title}
          </h2>
          <p className="mt-4 text-base leading-relaxed text-muted-foreground sm:text-lg">
            {t.dashboardShowcase.subtitle}
          </p>
        </Reveal>

        {/* Parallax Interactive Container */}
        <div
          className="relative mt-14 lg:mt-16"
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
          style={{ perspective: "1400px" }}
        >
          {/* FLOATING BADGE 1 (Top-Right: Statutory Compliance) */}
          <div
            className="pointer-events-none absolute -top-6 right-4 z-20 hidden lg:flex items-center gap-3 rounded-md border border-emerald-500/30 bg-background/95 px-3.5 py-2.5 shadow-sm backdrop-blur-md transition-transform duration-100 ease-out"
            style={{
              transform: `translateY(${chip1Y}px)`,
              willChange: "transform",
            }}
          >
            <div className="flex size-7 items-center justify-center rounded-md bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
              <ShieldCheck className="size-4" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-semibold text-foreground">
                  {lang === "ja" ? "法令基準適合: 100%" : "Rules Match: 100% ✓"}
                </span>
                <span className="size-1.5 rounded-full bg-emerald-500 animate-pulse" />
              </div>
              <p className="text-[10px] text-muted-foreground">
                {lang === "ja" ? "出入国在留管理庁の最新基準と照合" : "Checked against 2026 immigration rules"}
              </p>
            </div>
          </div>

          {/* FLOATING BADGE 2 (Bottom-Left: Zero Discrepancy Risk) */}
          <div
            className="pointer-events-none absolute -bottom-6 left-4 z-20 hidden lg:flex items-center gap-3 rounded-md border border-primary/30 bg-background/95 px-3.5 py-2.5 shadow-sm backdrop-blur-md transition-transform duration-100 ease-out"
            style={{
              transform: `translateY(${chip2Y}px)`,
              willChange: "transform",
            }}
          >
            <div className="flex size-7 items-center justify-center rounded-md bg-primary/10 text-primary">
              <CheckCircle2 className="size-4" />
            </div>
            <div>
              <div className="text-xs font-semibold text-foreground">
                {lang === "ja" ? "書類ミス 0件" : "0 Paperwork Mistakes"}
              </div>
              <p className="text-[10px] text-muted-foreground">
                {lang === "ja" ? "氏名・日付・報酬額の整合性を確認済" : "Names, dates & numbers matched across all files"}
              </p>
            </div>
          </div>

          {/* FLOATING BADGE 3 (Right Mid: Official MoJ Form Engine) */}
          <div
            className="pointer-events-none absolute top-1/2 -right-4 z-20 hidden xl:flex items-center gap-2 rounded-md border border-border/80 bg-background/95 px-3 py-2 shadow-sm backdrop-blur-md transition-transform duration-100 ease-out"
            style={{
              transform: `translateY(${chip3Y}px)`,
              willChange: "transform",
            }}
          >
            <Sparkles className="size-3.5 text-primary" />
            <span className="text-xs font-medium text-foreground">
              {lang === "ja" ? "法務省正規様式 作成完了" : "Official Government Forms Ready"}
            </span>
          </div>

          {/* MAIN DASHBOARD MOCKUP WINDOW */}
          <div
            className="overflow-hidden rounded-lg border border-border/80 bg-card shadow-sm transition-transform duration-150 ease-out"
            style={{
              transform: `translateY(${dashboardTranslateY}px) rotateX(${dashboardRotateX}deg) rotateY(${dashboardRotateY}deg)`,
              transformStyle: "preserve-3d",
              willChange: "transform",
            }}
          >
            {/* Window Chrome Header */}
            <div className="flex items-center justify-between border-b border-border/80 bg-muted/40 px-4 py-3 sm:px-6">
              <div className="flex items-center gap-2">
                <span className="size-2.5 rounded-full bg-red-400/80" />
                <span className="size-2.5 rounded-full bg-amber-400/80" />
                <span className="size-2.5 rounded-full bg-emerald-400/80" />
                <div className="ml-3 hidden sm:flex items-center gap-1.5 rounded border border-border/80 bg-background px-2.5 py-0.5 text-xs text-muted-foreground font-mono">
                  <Search className="size-3" />
                  <span>app.torii.visa/cases/{activeData.id}</span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <span className="inline-flex items-center gap-1 rounded bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-600 dark:text-emerald-400">
                  <span className="size-1.5 rounded-full bg-emerald-500" />
                  Live Sync
                </span>
                <span className="hidden sm:inline-block rounded border border-border bg-background px-2 py-0.5 text-[10px] font-mono text-muted-foreground">
                  MOJ-JP 2026.1
                </span>
              </div>
            </div>

            {/* Dashboard Workspace Grid */}
            <div className="grid lg:grid-cols-[290px_1fr]">
              {/* Left Case Selector Sidebar */}
              <div className="border-b lg:border-b-0 lg:border-r border-border/80 bg-muted/15 p-4 sm:p-5">
                <div className="flex items-center justify-between pb-3 border-b border-border/60">
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    {lang === "ja" ? "実際の管理案件 (3件)" : "Real Platform Cases (3)"}
                  </span>
                  <Layers className="size-3.5 text-muted-foreground" />
                </div>

                <div className="mt-3 space-y-2">
                  {(["renewal", "change", "coe"] as CaseId[]).map((cid) => {
                    const c = casesMap[cid];
                    const isSelected = selectedCase === cid;
                    return (
                      <button
                        key={cid}
                        type="button"
                        onClick={() => setSelectedCase(cid)}
                        className={cn(
                          "w-full text-left rounded-md p-3 transition-all duration-150 border cursor-pointer",
                          isSelected
                            ? "bg-background border-primary/40 shadow-sm text-foreground ring-1 ring-primary/20"
                            : "border-transparent hover:bg-muted/60 text-muted-foreground hover:text-foreground",
                        )}
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-[11px] font-mono font-semibold text-foreground">
                            {c.id}
                          </span>
                          <span
                            className={cn(
                              "text-[10px] font-medium px-2 py-0.5 rounded",
                              c.badgeTone === "success" && "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
                              c.badgeTone === "primary" && "bg-primary/10 text-primary",
                              c.badgeTone === "warning" && "bg-amber-500/10 text-amber-600 dark:text-amber-400",
                            )}
                          >
                            {c.badge}
                          </span>
                        </div>
                        <div className="mt-1.5 text-xs font-medium text-foreground line-clamp-1">
                          {c.category}
                        </div>
                        {/* Mini progress bar */}
                        <div className="mt-2.5 flex items-center gap-2">
                          <div className="h-1.5 flex-1 rounded-full bg-muted overflow-hidden">
                            <div
                              className="h-full bg-primary rounded-full transition-all duration-500"
                              style={{ width: `${c.progress}%` }}
                            />
                          </div>
                          <span className="text-[10px] font-mono text-muted-foreground">
                            {c.progress}%
                          </span>
                        </div>
                      </button>
                    );
                  })}
                </div>

                {/* Statutory Guideline Citation Note */}
                <div className="mt-5 rounded-md border border-border/80 bg-background/70 p-3 text-[11px] text-muted-foreground">
                  <div className="flex items-center gap-1.5 font-medium text-foreground">
                    <ShieldCheck className="size-3.5 text-primary" />
                    <span>{lang === "ja" ? "根拠法令・ガイドライン" : "Statutory Authority"}</span>
                  </div>
                  <p className="mt-1 leading-snug line-clamp-2">
                    {activeData.ruleCitation}
                  </p>
                </div>
              </div>

              {/* Right Workspace Main Pane */}
              <div className="p-5 sm:p-6 lg:p-7 space-y-5">
                {/* Case Top Status Header */}
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between pb-4 border-b border-border/80">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-primary">
                        {activeData.id}
                      </span>
                      <span className="text-muted-foreground">/</span>
                      <span className="text-xs text-muted-foreground font-medium">
                        {lang === "ja" ? "日本 法務省・出入国在留管理庁 管轄" : "Japan ISA / MOJ Jurisdiction"}
                      </span>
                    </div>
                    <h3 className="mt-1 text-lg sm:text-xl font-bold tracking-tight text-foreground">
                      {activeData.category}
                    </h3>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {activeData.subtitle}
                    </p>
                  </div>

                  {/* Tab switcher: Checklist vs Generated Forms */}
                  <div className="inline-flex rounded-md border border-border p-1 bg-muted/40 text-xs self-start sm:self-auto">
                    <button
                      type="button"
                      onClick={() => setActiveTab("checklist")}
                      className={cn(
                        "rounded px-3 py-1 font-medium transition-all cursor-pointer",
                        activeTab === "checklist"
                          ? "bg-background text-foreground shadow-sm"
                          : "text-muted-foreground hover:text-foreground",
                      )}
                    >
                      {lang === "ja" ? `必要書類チェック (${activeData.checklist.length})` : `Checklist (${activeData.checklist.length})`}
                    </button>
                    <button
                      type="button"
                      onClick={() => setActiveTab("forms")}
                      className={cn(
                        "rounded px-3 py-1 font-medium transition-all cursor-pointer",
                        activeTab === "forms"
                          ? "bg-background text-foreground shadow-sm"
                          : "text-muted-foreground hover:text-foreground",
                      )}
                    >
                      {lang === "ja" ? `自動作成書式 (${activeData.forms.length})` : `Statutory Forms (${activeData.forms.length})`}
                    </button>
                  </div>
                </div>

                {/* Real Statutory Deadline Alert Strip */}
                <div className="flex items-center gap-2 rounded-md border border-amber-500/30 bg-amber-500/5 px-3 py-2 text-xs text-amber-800 dark:text-amber-300">
                  <Clock className="size-3.5 shrink-0 text-amber-600 dark:text-amber-400" />
                  <span>{activeData.deadlineNotice}</span>
                </div>

                {/* Tab Content: Checklist vs Forms */}
                {activeTab === "checklist" ? (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between text-xs text-muted-foreground font-medium px-0.5">
                      <span>{lang === "ja" ? "法定提出書類一覧" : "REQUIRED STATUTORY DOCUMENTS"}</span>
                      <span>{lang === "ja" ? "適合ステータス" : "STATUS"}</span>
                    </div>

                    <div className="grid gap-2.5">
                      {activeData.checklist.map((item, i) => (
                        <div
                          key={i}
                          className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 rounded-md border border-border/80 bg-background/60 p-3 transition-colors hover:bg-muted/30"
                        >
                          <div className="flex items-start gap-3">
                            {item.status === "verified" ? (
                              <CheckCircle2 className="size-4 shrink-0 text-emerald-600 dark:text-emerald-400 mt-0.5" />
                            ) : (
                              <Clock className="size-4 shrink-0 text-amber-500 mt-0.5" />
                            )}
                            <div>
                              <div className="text-xs font-semibold text-foreground">
                                {item.title}
                              </div>
                              <div className="text-[11px] text-muted-foreground">
                                {item.source}
                              </div>
                            </div>
                          </div>

                          <div className="self-end sm:self-auto">
                            {item.status === "verified" ? (
                              <span className="inline-flex items-center gap-1 rounded bg-emerald-500/10 px-2 py-0.5 text-[11px] font-semibold text-emerald-600 dark:text-emerald-400">
                                {lang === "ja" ? "適合照合済 ✓" : "Verified ✓"}
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 rounded bg-amber-500/10 px-2 py-0.5 text-[11px] font-semibold text-amber-600 dark:text-amber-400">
                                {lang === "ja" ? "作成進行中" : "In Progress"}
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between text-xs text-muted-foreground font-medium px-0.5">
                      <span>{lang === "ja" ? "自動生成された法務省・入管公式書式" : "AUTO-FILLED STATUTORY PACKETS"}</span>
                      <span>{lang === "ja" ? "出力形式" : "FORMAT"}</span>
                    </div>

                    <div className="grid gap-2.5">
                      {activeData.forms.map((form, i) => (
                        <div
                          key={i}
                          className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-md border border-border/80 bg-background/60 p-3 transition-colors hover:border-primary/40"
                        >
                          <div className="flex items-start gap-3">
                            <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
                              <FileText className="size-4" />
                            </div>
                            <div>
                              <div className="text-xs font-semibold text-foreground">
                                {form.name}
                              </div>
                              <div className="flex items-center gap-2 mt-0.5 text-[11px] text-muted-foreground">
                                <span>{form.version}</span>
                                <span>·</span>
                                <span className="text-emerald-600 dark:text-emerald-400 font-medium">
                                  {form.fields}
                                </span>
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center gap-2 self-end sm:self-auto">
                            <span className="rounded border border-border bg-muted/40 px-2 py-0.5 text-[10px] font-mono text-muted-foreground">
                              {form.format}
                            </span>
                            <span className="inline-flex items-center gap-1 rounded bg-primary text-primary-foreground px-2.5 py-1 text-xs font-medium shadow-sm">
                              <Download className="size-3" />
                              {lang === "ja" ? "即時出力" : "Ready"}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Bottom Verification Banner */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-md border border-primary/20 bg-primary/5 p-3 text-xs">
                  <div className="flex items-center gap-2 text-foreground font-medium">
                    <Sparkles className="size-4 text-primary shrink-0" />
                    <span>
                      {activeData.progress === 100
                        ? (lang === "ja"
                            ? "東京出入国在留管理局 提出仕様に準拠した書類一式が完成しています。"
                            : "Case packet is pre-collated and ready for Tokyo Immigration Bureau submission.")
                        : (lang === "ja"
                            ? "入力データは法務省標準様式PDFに直接マッピングされ、記載漏れは自動検出されます。"
                            : "Intake answers are directly mapped to standard Japanese Ministry PDF forms without guesswork.")}
                    </span>
                  </div>
                  <a
                    href="#pricing"
                    className="inline-flex items-center gap-1 font-medium text-primary hover:underline shrink-0"
                  >
                    <span>{lang === "ja" ? "料金とプランを見る" : "View pricing & tiers"}</span>
                    <ArrowUpRight className="size-3.5" />
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
