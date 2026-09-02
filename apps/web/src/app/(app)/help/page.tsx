"use client";

import { useState } from "react";
import Link from "next/link";
import {
  HelpCircle,
  Compass,
  FileSpreadsheet,
  CheckCircle2,
  FolderCheck,
  FileCheck2,
  Send,
  Sparkles,
  Bot,
  Coins,
  ShieldCheck,
  ChevronRight,
  ArrowRight,
  Clock,
  Building2,
  AlertTriangle,
  Lightbulb,
  ExternalLink,
  BookOpen,
  ScanText,
  Printer,
  Globe2,
} from "lucide-react";
import { useI18n } from "@/lib/i18n";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function HelpAndGuidePage() {
  const { lang } = useI18n();
  const [activeTab, setActiveTab] = useState<"steps" | "features" | "faq">("steps");

  const workflowSteps = [
    {
      step: 1,
      id: "scope",
      title: "Scope & Visa Category Discovery",
      title_ja: "1. 診断・ビザ種別の自動特定",
      shortDesc: "Determine your exact visa type and filing route in under 2 minutes.",
      shortDesc_ja: "2分間の診断で最適な在留資格と申請区分（更新・変更・認定）を自動判定します。",
      icon: Compass,
      color: "from-blue-500/20 to-blue-500/5 text-blue-600 dark:text-blue-400 border-blue-500/30",
      badge: "100% Free",
      details: [
        "Identifies whether you need an Extension (更新), Change of Status (変更), or Certificate of Eligibility (COE認定).",
        "Calculates points for Highly Skilled Professional (高度専門職) routes.",
        "Detects potential eligibility bottlenecks early (e.g. salary requirements, degree accreditation).",
      ],
      details_ja: [
        "在留期間更新、在留資格変更、COE交付申請のどれが必要かを即時に特定。",
        "高度専門職ポイント（学歴・職歴・年収）を自動計算。",
        "年収下限（300万円〜）や大学学位要件などの適格性を事前チェック。",
      ],
      tip: "You can run free scoping unlimited times before creating a formal case.",
      tip_ja: "正式なケースを作成する前に、何度でも無料で診断を実行できます。",
    },
    {
      step: 2,
      id: "intake",
      title: "Interactive Applicant Intake",
      title_ja: "2. 基本情報のインタラクティブ入力",
      shortDesc: "Fill in personal, passport, educational, and employer details.",
      shortDesc_ja: "申請者本人、パスポート、学歴・職歴、雇用先企業の情報をフォームに入力します。",
      icon: FileSpreadsheet,
      color: "from-indigo-500/20 to-indigo-500/5 text-indigo-600 dark:text-indigo-400 border-indigo-500/30",
      badge: "Save & Resume",
      details: [
        "Smart dynamic inputs adapt based on your specific visa category (Engineer vs Spouse vs Student).",
        "Real-time validation checks for valid dates, Japanese postal codes, and passport format.",
        "Automatic auto-save prevents lost work if you need to step away.",
      ],
      details_ja: [
        "ビザの種類（技術・人文知識・国際業務、配偶者、留学など）に応じて最適な質問項目を自動提示。",
        "パスポート有効期限、日本の郵便番号、フリガナなどをリアルタイムで入力検証。",
        "途中保存機能により、いつでも中断・再開が可能です。",
      ],
      tip: "Use your Passport and Residence Card for exact character-by-character spelling.",
      tip_ja: "パスポートおよび在留カードの表記と完全一致するように入力してください。",
    },
    {
      step: 3,
      id: "eligibility",
      title: "Statutory Eligibility Audit",
      title_ja: "3. 法令要件・適格性判定",
      shortDesc: "Automated compliance evaluation against Japanese MOJ criteria.",
      shortDesc_ja: "出入国在留管理庁（入管）の審査基準に基づき、法令適合性を自動評価します。",
      icon: ShieldCheck,
      color: "from-emerald-500/20 to-emerald-500/5 text-emerald-600 dark:text-emerald-400 border-emerald-500/30",
      badge: "AI Compliance Check",
      details: [
        "Verifies statutory salary threshold (minimum requirement standard of ¥3,000,000/year for skilled work).",
        "Evaluates major-to-job relevance (field of study matching employment duties).",
        "Audits past immigration violations or residency lapse flags.",
      ],
      details_ja: [
        "日本人の同等報酬要件（年収基準）を満たしているかを検証。",
        "大学での専攻分野と日本での従事業務の関連性を照合・評価。",
        "過去の在留履歴や税務申告状況のリスクを分析。",
      ],
      tip: "The AI Copilot will alert you with citations if any rule needs legal justification.",
      tip_ja: "補足説明や理由書が必要な場合は、AIアシスタントが法的根拠付きで助言します。",
    },
    {
      step: 4,
      id: "checklist",
      title: "Required Documents & Vault",
      title_ja: "4. 必要書類リストと書類保管庫",
      shortDesc: "Personalized checklist based on your employer's tax category (Category 1–4).",
      shortDesc_ja: "企業のカテゴリー区分（カテゴリー1〜4）に応じた必要書類リストを自動生成します。",
      icon: FolderCheck,
      color: "from-amber-500/20 to-amber-500/5 text-amber-600 dark:text-amber-400 border-amber-500/30",
      badge: "Auto-OCR Included",
      details: [
        "Upload tax certificates (住民税の課税・納税証明書), withholding slips (源泉徴収票), and contracts.",
        "Automated OCR scans your Residence Card and Passport photo to prefill form fields instantly.",
        "Tracks status: Missing, Uploaded, Verified, or Employer-Provided.",
      ],
      details_ja: [
        "住民税の課税・納税証明書、源泉徴収票、雇用契約書などの保管と管理。",
        "在留カード・パスポートのOCRスキャンにより、氏名や番号を自動抽出。",
        "書類ごとの準備状況（未収集・確認済・会社手配）をリアルタイム管理。",
      ],
      tip: "Tax certificates must cover the most recent fiscal year and be issued within 3 months.",
      tip_ja: "公的証明書（納税証明書等）は発行後3ヶ月以内の最新原本が必要です。",
    },
    {
      step: 5,
      id: "forms",
      title: "Official MOJ PDF Form Generation",
      title_ja: "5. 公的申請書（別記様式）の自動作成",
      shortDesc: "Pixel-perfect official Japanese Immigration Bureau forms.",
      shortDesc_ja: "入管公式フォーマット（別記様式）に準拠した申請書をミリ単位の精度で自動生成します。",
      icon: FileCheck2,
      color: "from-cyan-500/20 to-cyan-500/5 text-cyan-600 dark:text-cyan-400 border-cyan-500/30",
      badge: "Official Layout",
      details: [
        "Renders Applicant Pages (申請人等作成用) and Organization Pages (所属機関等作成用).",
        "Detects missing required fields with 1-click inline editors (dates, selects, booleans).",
        "Generates clean Japanese Kanji/Katakana typography without formatting errors.",
      ],
      details_ja: [
        "「申請人等作成用」および「所属機関等作成用」のすべての様式を完全網羅。",
        "未入力項目を自動検出し、カード型エディタで即座に修正・補完が可能。",
        "文字化けやレイアウト崩れのない、高精度な日本語PDFを出力。",
      ],
      tip: "Double-check your company's Corporate Number (法人番号) on the organization page.",
      tip_ja: "所属機関等作成用ページの「13桁の法人番号」が正しいかご確認ください。",
    },
    {
      step: 6,
      id: "packet",
      title: "Complete Dossier Kit & Submission",
      title_ja: "6. 提出キットの完成と入管への申請",
      shortDesc: "Download full filing dossier with cover letter, submission guide, and barcodes.",
      shortDesc_ja: "提出用表紙、添付書類目録、提出手順書を含む完全な提出パケットをダウンロードします。",
      icon: Send,
      color: "from-purple-500/20 to-purple-500/5 text-purple-600 dark:text-purple-400 border-purple-500/30",
      badge: "1 Application Pass",
      details: [
        "Complete all-in-one PDF packet with barcode headers, applicant statement, and document index.",
        "Step-by-step instructions for Online e-Filing (在留申請オンラインシステム) or in-person bureau filing (Shinagawa, Tachikawa, Yokohama, etc.).",
        "Revenue stamp (収入印紙) guidance and post-submission monitoring reminder tracking.",
      ],
      details_ja: [
        "バーコード付き表紙、申請理由書、提出書類一覧を一体化した提出用パケット一式。",
        "「在留申請オンラインシステム」による電子申請、または各入管窓口での対面提出手順を明記。",
        "手数料納付（収入印紙）や審査期間中の進捗管理リマインダーを完備。",
      ],
      tip: "Every new user receives 3 Free Application Passes, unlocking up to 3 complete filing dossiers.",
      tip_ja: "新規登録特典として3パスが付与されており、最大3件の完全パケットを無料で出力できます。",
    },
  ];

  const features = [
    {
      title: "AI Immigration Copilot",
      title_ja: "AI 入管アシスタント",
      desc: "Instant answers to complex legal questions, salary rules, side-job permissions, and tax compliance citations.",
      desc_ja: "年収基準、副業許可（資格外活動）、税金滞納リスクなど、入管法・省令に準拠した回答を24時間提供します。",
      icon: Bot,
    },
    {
      title: "Automated Document OCR",
      title_ja: "スマート書類OCR",
      desc: "Upload photos of your Residence Card, Passport, or Tax slips. Torii extracts names, dates, and numbers automatically.",
      desc_ja: "在留カードやパスポートの写真をアップロードするだけで、氏名・在留期限・番号を自動抽出して入力します。",
      icon: ScanText,
    },
    {
      title: "Category 1–4 Company Profiler",
      title_ja: "所属機関カテゴリー自動判定",
      desc: "Identifies whether your employer is listed (Cat 1), medium enterprise (Cat 2), or standard (Cat 3/4) to prune redundant docs.",
      desc_ja: "上場企業（Cat 1）から中小企業（Cat 3）まで区分を特定し、提出不要な書類を自動で省きます。",
      icon: Building2,
    },
    {
      title: "Official Bureau Print Ready",
      title_ja: "入管窓口提出・公的規格",
      desc: "All generated PDFs strictly follow Japanese Ministry of Justice formatting guidelines (A4 standard, exact margins).",
      desc_ja: "出入国在留管理庁の公式レイアウト規格に100%合致したA4サイズ印刷対応PDFです。",
      icon: Printer,
    },
  ];

  const faqs = [
    {
      q: "How much does Torii cost?",
      q_ja: "利用料金はいくらですか？",
      a: "Every new user gets 3 Free Application Passes on signup! A pass unlocks 1 complete visa application with official PDFs, unlimited AI assistance, and OCR. Additional passes cost $19 for 1 pass, $39 for 3 passes, or $59 for 5 passes.",
      a_ja: "新規登録者全員に「3件分の無料申請パス」が付与されます。1パスで1件のビザ申請（公的PDF、AI相談、OCR抽出）を完全作成できます。追加パスは 1件$19 (¥2,800)、3件$39 (¥5,800)、5件$59 (¥8,900) です。",
    },
    {
      q: "When can I submit my visa renewal application?",
      q_ja: "在留期間の更新はいつから申請できますか？",
      a: "In Japan, you can submit your renewal application starting 3 months before your current visa expiration date. We recommend preparing your case in Torii 30 to 45 days before expiry.",
      a_ja: "日本の在留期間更新は、在留期限の「3ヶ月前」から申請可能です。期限の30〜45日前にはToriiで書類作成を開始することをおすすめします。",
    },
    {
      q: "Can I file online without going to the Shinagawa immigration office?",
      q_ja: "品川の入国管理局に行かずにオンラインで申請できますか？",
      a: "Yes! If you have an Individual Number Card (My Number Card) and an IC card reader (or NFC smartphone), you can file directly via the MOJ Online Application System. Torii guides you through both online and in-person filing methods.",
      a_ja: "はい！マイナンバーカードとICカードリーダー（または対応スマートフォン）があれば、「在留申請オンラインシステム」から窓口に行かずに提出できます。Toriiはオンライン提出・窓口提出の双方に対応しています。",
    },
    {
      q: "What if my company hasn't given me their tax documents yet?",
      q_ja: "会社側の書類（決算書や法定調書合計表）がまだ揃っていません。",
      a: "You can start your applicant intake right away! Torii allows you to complete and verify all applicant-side forms first, and add company documents whenever your HR or administration department provides them.",
      a_ja: "ご安心ください。申請人側の基本情報やパスポート情報はいつでも先に入力・作成できます。会社書類が届き次第、書類保管庫に追加して最終パケットを出力できます。",
    },
    {
      q: "Is Torii a replacement for an immigration lawyer (行政書士)?",
      q_ja: "Toriiは行政書士の代わりになりますか？",
      a: "Torii is an automated self-service software platform designed for standard, straightforward visa extensions, status changes, and COE filings. If you have complex legal issues, past criminal charges, or serious tax arrears, Torii's AI Copilot will advise you when to consult a licensed immigration attorney.",
      a_ja: "Toriiは一般的な就労・配偶者・家族滞在・留学などの申請書類をセルフサービスで正確に作成するための自動化ツールです。不法滞在歴や重度の税金滞納など複雑な事情がある場合は、弁護士・行政書士へのご相談を推奨するアラートを表示します。",
    },
  ];

  return (
    <div className="mx-auto max-w-5xl space-y-8 p-4 sm:p-6 lg:p-8 animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b pb-6">
        <div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground font-medium mb-1">
            <Link href="/dashboard" className="hover:text-primary transition-colors">
              {lang === "ja" ? "ダッシュボード" : "Dashboard"}
            </Link>
            <span>/</span>
            <span className="text-foreground">{lang === "ja" ? "ご利用ガイド" : "Help & Guide"}</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground flex items-center gap-2.5">
            <BookOpen className="size-7 text-primary" />
            <span>{lang === "ja" ? "Torii 利用ガイド & 申請の流れ" : "How Torii Works: Complete Case Guide"}</span>
          </h1>
          <p className="text-xs sm:text-sm text-muted-foreground mt-1 max-w-2xl">
            {lang === "ja"
              ? "ビザ診断から公的申請書の作成、出入国在留管理局への提出まで、全ステップを分かりやすく解説します。"
              : "A complete step-by-step walkthrough from initial eligibility scoping to official government dossier submission."}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            href="/scope"
            className="inline-flex items-center justify-center h-9 px-3 gap-1.5 text-xs font-semibold rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-xs"
          >
            <Compass className="size-3.5" />
            <span>{lang === "ja" ? "今すぐ無料診断" : "Start Free Scoping"}</span>
          </Link>
          <Link
            href="/credits"
            className="inline-flex items-center justify-center h-9 px-3 gap-1.5 text-xs font-semibold rounded-md border border-input bg-background hover:bg-accent hover:text-accent-foreground transition-colors shadow-xs"
          >
            <Coins className="size-3.5 text-amber-500" />
            <span>{lang === "ja" ? "クレジット確認" : "Credits"}</span>
          </Link>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-2 border-b pb-2">
        <button
          type="button"
          onClick={() => setActiveTab("steps")}
          className={`inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
            activeTab === "steps"
              ? "bg-primary text-primary-foreground shadow-xs"
              : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
          }`}
        >
          <FolderCheck className="size-3.5" />
          <span>{lang === "ja" ? "申請の6ステップ" : "The 6 Case Steps"}</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("features")}
          className={`inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
            activeTab === "features"
              ? "bg-primary text-primary-foreground shadow-xs"
              : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
          }`}
        >
          <Sparkles className="size-3.5" />
          <span>{lang === "ja" ? "主要機能と特徴" : "Key Features"}</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("faq")}
          className={`inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
            activeTab === "faq"
              ? "bg-primary text-primary-foreground shadow-xs"
              : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
          }`}
        >
          <HelpCircle className="size-3.5" />
          <span>{lang === "ja" ? "よくある質問 (FAQ)" : "FAQ & Rules"}</span>
        </button>
      </div>

      {/* Tab 1: Workflow Steps */}
      {activeTab === "steps" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 gap-4">
            {workflowSteps.map((s) => {
              const Icon = s.icon;
              return (
                <div
                  key={s.id}
                  className="rounded-xl border bg-card p-5 sm:p-6 shadow-xs hover:border-primary/40 transition-all space-y-4"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="flex items-center gap-3.5">
                      <div className={`flex size-11 shrink-0 items-center justify-center rounded-xl border bg-gradient-to-br ${s.color}`}>
                        <Icon className="size-5.5" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-black text-primary uppercase tracking-wider">
                            Step {s.step}
                          </span>
                          <Badge tone="default" className="text-[10px]">
                            {s.badge}
                          </Badge>
                        </div>
                        <h3 className="text-base sm:text-lg font-bold text-foreground">
                          {lang === "ja" ? s.title_ja : s.title}
                        </h3>
                      </div>
                    </div>

                    <p className="text-xs text-muted-foreground sm:text-right max-w-sm">
                      {lang === "ja" ? s.shortDesc_ja : s.shortDesc}
                    </p>
                  </div>

                  {/* Bullet points */}
                  <div className="rounded-lg bg-muted/20 border p-3.5 text-xs space-y-2">
                    <div className="font-semibold text-foreground flex items-center gap-1.5">
                      <CheckCircle2 className="size-3.5 text-emerald-500" />
                      <span>{lang === "ja" ? "このステップで行うこと:" : "What happens in this step:"}</span>
                    </div>
                    <ul className="space-y-1.5 text-muted-foreground pl-5 list-disc">
                      {(lang === "ja" ? s.details_ja : s.details).map((detail, idx) => (
                        <li key={idx} className="leading-relaxed">
                          {detail}
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Pro Tip */}
                  <div className="flex items-center gap-2 text-[11px] text-amber-700 dark:text-amber-300 bg-amber-500/10 border border-amber-500/20 px-3 py-2 rounded-lg">
                    <Lightbulb className="size-3.5 shrink-0 text-amber-500" />
                    <span>
                      <strong>Pro Tip:</strong> {lang === "ja" ? s.tip_ja : s.tip}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Bottom Action CTA */}
          <div className="rounded-2xl border bg-gradient-to-r from-primary/10 via-primary/5 to-card p-6 sm:p-8 text-center space-y-3">
            <h3 className="text-lg sm:text-xl font-bold text-foreground">
              {lang === "ja" ? "準備はできましたか？今すぐ申請を作成しましょう" : "Ready to Prepare Your Application?"}
            </h3>
            <p className="text-xs text-muted-foreground max-w-lg mx-auto">
              {lang === "ja"
                ? "まずは無料の在留資格診断からスタート。新規登録特典として3件分の申請パスが付与されています。"
                : "Start with our free instant diagnostic. Every registered account includes 3 complimentary passes."}
            </p>
            <div className="pt-2 flex flex-wrap items-center justify-center gap-3">
              <Link
                href="/scope"
                className="inline-flex items-center justify-center h-9 px-4 gap-2 text-xs font-bold rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-xs"
              >
                <span>{lang === "ja" ? "無料ビザ診断を開始" : "Start Free Scoping"}</span>
                <ArrowRight className="size-3.5" />
              </Link>
              <Link
                href="/cases"
                className="inline-flex items-center justify-center h-9 px-4 gap-2 text-xs font-bold rounded-md border border-input bg-background hover:bg-accent hover:text-accent-foreground transition-colors shadow-xs"
              >
                <span>{lang === "ja" ? "申請案件ダッシュボードへ" : "Go to My Cases"}</span>
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Key Features */}
      {activeTab === "features" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {features.map((f, idx) => {
              const Icon = f.icon;
              return (
                <div key={idx} className="rounded-xl border bg-card p-5 shadow-xs space-y-3">
                  <div className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary border border-primary/20">
                    <Icon className="size-5" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-foreground">
                      {lang === "ja" ? f.title_ja : f.title}
                    </h4>
                    <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                      {lang === "ja" ? f.desc_ja : f.desc}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>

          <Card className="border shadow-xs rounded-xl">
            <CardHeader>
              <CardTitle className="text-base font-bold flex items-center gap-2">
                <Globe2 className="size-5 text-primary" />
                <span>{lang === "ja" ? "出入国在留管理庁の主要申請に対応" : "Supported Japan Visa Categories"}</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
                <div className="p-2.5 rounded-lg border bg-muted/20 font-semibold">
                  💼 Engineer / Specialist in Humanities (技術・人文知識・国際業務)
                </div>
                <div className="p-2.5 rounded-lg border bg-muted/20 font-semibold">
                  🌟 Highly Skilled Professional 1a / 1b / 1c (高度専門職)
                </div>
                <div className="p-2.5 rounded-lg border bg-muted/20 font-semibold">
                  💍 Spouse or Child of Japanese National (日本人の配偶者等)
                </div>
                <div className="p-2.5 rounded-lg border bg-muted/20 font-semibold">
                  👨‍👩‍👧 Dependent / Family Stay (家族滞在)
                </div>
                <div className="p-2.5 rounded-lg border bg-muted/20 font-semibold">
                  🏢 Business Manager (経営・管理)
                </div>
                <div className="p-2.5 rounded-lg border bg-muted/20 font-semibold">
                  🎓 Student / Post-Graduation Search (留学・特定活動)
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tab 3: FAQ */}
      {activeTab === "faq" && (
        <div className="space-y-4">
          {faqs.map((faq, idx) => (
            <div key={idx} className="rounded-xl border bg-card p-5 shadow-xs space-y-2">
              <div className="flex items-start gap-2.5">
                <HelpCircle className="size-4 text-primary shrink-0 mt-0.5" />
                <h4 className="text-sm font-bold text-foreground">
                  {lang === "ja" ? faq.q_ja : faq.q}
                </h4>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed pl-6.5">
                {lang === "ja" ? faq.a_ja : faq.a}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
