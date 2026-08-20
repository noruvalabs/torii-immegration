"use client";

import React, { createContext, useContext, useEffect, useState, type ReactNode } from "react";

export type Lang = "en" | "ja";

const STORAGE_KEY = "torii_lang";

export const DICTIONARY = {
  en: {
    // Navigation
    nav_dashboard: "Dashboard",
    nav_cases: "Case Management",
    nav_review_queue: "Review Queue",
    nav_jurisdictions: "Jurisdictions & Rules",
    nav_forms: "Form Templates",
    nav_employers: "Employer Accounts",
    nav_staff: "Staff & Reviewers",
    nav_knowledge_base: "Knowledge Base",
    nav_reports: "Reports & Analytics",
    nav_settings: "Settings & Keys",
    nav_role_admin: "ADMIN",
    nav_role_ops: "OPS",
    nav_role_employer: "EMPLOYER",
    nav_role_guest: "GUEST",
    nav_disclaimer: "Guided immigration form preparation — not legal advice. Sourced citations.",

    // Topbar & Common
    search_placeholder: "Search cases, applicants, references…",
    sign_out: "Sign out",
    sign_in: "Sign in",
    language: "Language",
    english: "English",
    japanese: "日本語",
    loading: "Loading…",
    refresh: "Refresh",
    filter: "Filter",
    all_statuses: "All statuses",
    export: "Export",
    save: "Save",
    cancel: "Cancel",
    delete: "Delete",
    actions: "Actions",
    details: "Details",
    status: "Status",
    date: "Date",
    reference: "Reference",
    applicant: "Applicant",
    jurisdiction: "Jurisdiction",
    route: "Route / Purpose",

    // Admin Dashboard KPI
    kpi_live_jurisdictions: "Live Jurisdictions",
    kpi_live_jurisdictions_sub: "Active legal corridors configured",
    kpi_active_cases: "Active Cases",
    kpi_active_cases_sub: "Intake & preparation in progress",
    kpi_review_queue: "Review Queue",
    kpi_review_queue_sub: "High-risk & statutory review queue",
    kpi_submitted_cases: "Submitted Cases",
    kpi_submitted_cases_sub: "Packets sent & verified",
    kpi_approval_rate: "Packet Readiness Rate",
    kpi_approval_rate_sub: "Verified dossiers without flags",
    kpi_avg_processing: "Avg Turnaround",
    kpi_avg_processing_sub: "From intake to dossier ready",

    // Admin Dashboard Sections
    recent_cases_title: "Recent Immigration Applications",
    recent_cases_desc: "Real-time stream of incoming visa and status change applications across all corridors.",
    view_all_cases: "View all cases",
    no_cases_found: "No cases match the selected filter.",
    system_status_title: "Platform Core Status",
    api_status: "API (System of Record)",
    api_connected: "Connected & Healthy",
    ai_engine: "AI Citation Engine",
    ai_active: "Active (Groq / Qwen 2.5)",
    jurisdiction_engine: "Jurisdiction Ruleset",
    jurisdiction_active: "Dynamic & Scraped",
    quick_links: "Operational Shortcuts",
    configure_jurisdiction: "Configure Corridors",
    review_escalations: "Review Escalations",
    manage_forms: "Manage Forms",
    batch_export: "Batch Export Snapshot",

    // Status Badges
    status_draft: "Draft",
    status_intake_complete: "Intake Complete",
    status_checklist_ready: "Checklist Ready",
    status_forms_generated: "Forms Generated",
    status_review_ready: "Review Ready",
    status_packet_ready: "Packet Ready",
    status_submitted: "Submitted",

    // Auth & Social Login
    auth_welcome_back: "Sign in to Torii",
    auth_welcome_sub: "Official immigration application and dossier management system.",
    auth_google_continue: "Continue with Google",
    auth_or_divider: "Or continue with email",
    auth_email_username: "Email or username",
    auth_password: "Password",
    auth_confirm_password: "Confirm password",
    auth_username_optional: "Username (optional)",
    auth_forgot_password: "Forgot password?",
    auth_no_account: "No account?",
    auth_have_account: "Already have an account?",
    auth_create_one: "Create account",
    auth_register_title: "Create your Torii account",
    auth_register_sub: "Begin your verified immigration application with official guidance.",

    // Notifications
    lang_switched_jp: "言語を日本語に切り替えました",
    lang_switched_en: "Switched language to English",
  },
  ja: {
    // Navigation
    nav_dashboard: "ダッシュボード",
    nav_cases: "申請案件管理",
    nav_review_queue: "審査キュー",
    nav_jurisdictions: "国・法域ルール管理",
    nav_forms: "申請書式テンプレート",
    nav_employers: "所属機関・企業管理",
    nav_staff: "査証担当・スタッフ",
    nav_knowledge_base: "ナレッジベース",
    nav_reports: "分析・レポート",
    nav_settings: "システム設定",
    nav_role_admin: "管理者",
    nav_role_ops: "業務担当",
    nav_role_employer: "企業・所属機関",
    nav_role_guest: "ゲスト",
    nav_disclaimer: "法務手続支援システム — 法的助言ではありません。根拠条文・公示基準準拠。",

    // Topbar & Common
    search_placeholder: "案件番号、申請者名、受付番号を検索…",
    sign_out: "ログアウト",
    sign_in: "ログイン",
    language: "言語切替",
    english: "English",
    japanese: "日本語",
    loading: "読み込み中…",
    refresh: "更新",
    filter: "フィルター",
    all_statuses: "すべてのステータス",
    export: "エクスポート",
    save: "保存",
    cancel: "キャンセル",
    delete: "削除",
    actions: "操作",
    details: "詳細",
    status: "進捗状態",
    date: "作成日",
    reference: "案件参照番号",
    applicant: "申請人",
    jurisdiction: "対象国・管轄",
    route: "在留資格 / 手続種別",

    // Admin Dashboard KPI
    kpi_live_jurisdictions: "対応国・法域数",
    kpi_live_jurisdictions_sub: "稼働中の公式査証手続ルート",
    kpi_active_cases: "進行中案件数",
    kpi_active_cases_sub: "ヒアリング・書類作成進行中",
    kpi_review_queue: "審査要確認キュー",
    kpi_review_queue_sub: "要確認・低信頼度・法的確認案件",
    kpi_submitted_cases: "申請完了案件",
    kpi_submitted_cases_sub: "出入国在留管理局/公館提出済",
    kpi_approval_rate: "書類充足率",
    kpi_approval_rate_sub: "不備・指摘事項なしの完成割合",
    kpi_avg_processing: "平均作成所要時間",
    kpi_avg_processing_sub: "情報入力から一式完成まで",

    // Admin Dashboard Sections
    recent_cases_title: "最新の査証・在留資格申請案件",
    recent_cases_desc: "全ルートからリアルタイムで受け付けられた申請および変更手続きの一覧。",
    view_all_cases: "すべての案件を表示",
    no_cases_found: "該当する申請案件が見つかりません。",
    system_status_title: "システム基盤稼働状況",
    api_status: "基幹API (System of Record)",
    api_connected: "正常稼働中 (Connected)",
    ai_engine: "法令引用AIエンジン",
    ai_active: "稼働中 (Groq / Qwen 2.5)",
    jurisdiction_engine: "法規・基準判定エンジン",
    jurisdiction_active: "公示基準同期済",
    quick_links: "業務クイックアクセス",
    configure_jurisdiction: "法域・手続設定",
    review_escalations: "審査案件一覧",
    manage_forms: "書式マスタ管理",
    batch_export: "一括データ出力",

    // Status Badges
    status_draft: "下書き",
    status_intake_complete: "ヒアリング完了",
    status_checklist_ready: "必要書類確定",
    status_forms_generated: "申請書生成済",
    status_review_ready: "審査前確認",
    status_packet_ready: "一式書類完成",
    status_submitted: "提出完了",

    // Auth & Social Login
    auth_welcome_back: "Toriiにサインイン",
    auth_welcome_sub: "公式ビザ・在留資格申請管理プラットフォーム",
    auth_google_continue: "Googleでログイン",
    auth_or_divider: "またはメールアドレスでログイン",
    auth_email_username: "メールアドレス または ユーザー名",
    auth_password: "パスワード",
    auth_confirm_password: "パスワード（確認）",
    auth_username_optional: "ユーザー名（任意）",
    auth_forgot_password: "パスワードをお忘れですか？",
    auth_no_account: "アカウントをお持ちでないですか？",
    auth_have_account: "既にアカウントをお持ちですか？",
    auth_create_one: "新規アカウント登録",
    auth_register_title: "Torii アカウント作成",
    auth_register_sub: "公式基準に基づく確実なビザ・在留資格手続きを開始します。",

    // Notifications
    lang_switched_jp: "言語を日本語に切り替えました",
    lang_switched_en: "Switched language to English",
  },
};

export type DictionaryKey = keyof typeof DICTIONARY.en;

interface I18nContextType {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: (key: DictionaryKey | string, fallback?: string) => string;
  isJapanUser: boolean;
}

const I18nContext = createContext<I18nContextType>({
  lang: "en",
  setLang: () => {},
  t: (key: string, fallback?: string) => fallback || key,
  isJapanUser: false,
});

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>("en");
  const [isJapanUser, setIsJapanUser] = useState(false);

  useEffect(() => {
    // 1. Check user explicitly saved preference
    const saved = typeof window !== "undefined" ? localStorage.getItem(STORAGE_KEY) : null;
    if (saved === "en" || saved === "ja") {
      setLangState(saved);
      if (saved === "ja") setIsJapanUser(true);
      return;
    }

    // 2. Check browser locale or IP geolocation
    const browserLang = typeof navigator !== "undefined" ? navigator.language?.toLowerCase() ?? "" : "";
    const isBrowserJa = browserLang.startsWith("ja");

    // Fetch geo-detection from backend
    fetch("/backend/v1/geo/detect")
      .then((res) => (res.ok ? res.json() : null))
      .then((geo) => {
        if (geo?.is_japan || geo?.country_code === "JP" || isBrowserJa) {
          setIsJapanUser(true);
          setLangState("ja");
          if (typeof window !== "undefined") {
            localStorage.setItem(STORAGE_KEY, "ja");
          }
        } else {
          setLangState("en");
          if (typeof window !== "undefined") {
            localStorage.setItem(STORAGE_KEY, "en");
          }
        }
      })
      .catch(() => {
        if (isBrowserJa) {
          setIsJapanUser(true);
          setLangState("ja");
        } else {
          setLangState("en");
        }
      });
  }, []);

  const setLang = (next: Lang) => {
    setLangState(next);
    if (typeof window !== "undefined") {
      localStorage.setItem(STORAGE_KEY, next);
      localStorage.setItem("torii-landing-lang", next);
    }
  };

  const t = (key: DictionaryKey | string, fallback?: string): string => {
    const dict = DICTIONARY[lang] as Record<string, string>;
    if (dict && dict[key]) {
      return dict[key];
    }
    const enDict = DICTIONARY.en as Record<string, string>;
    if (enDict && enDict[key]) {
      return enDict[key];
    }
    return fallback || key;
  };

  return (
    <I18nContext.Provider value={{ lang, setLang, t, isJapanUser }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n() {
  return useContext(I18nContext);
}

export function LanguageSwitcher({ className = "" }: { className?: string }) {
  const { lang, setLang } = useI18n();

  return (
    <div
      className={`inline-flex items-center rounded-lg border bg-card/90 p-0.5 shadow-xs text-xs backdrop-blur ${className}`}
      role="group"
      aria-label="Language selection"
    >
      <button
        type="button"
        onClick={() => setLang("en")}
        className={`flex items-center gap-1 rounded-md px-2.5 py-1 font-medium transition-all ${
          lang === "en"
            ? "bg-primary text-primary-foreground shadow-xs font-semibold"
            : "text-muted-foreground hover:text-foreground"
        }`}
        title="English"
      >
        <span className="text-[12px]">🇺🇸</span>
        <span>EN</span>
      </button>
      <button
        type="button"
        onClick={() => setLang("ja")}
        className={`flex items-center gap-1 rounded-md px-2.5 py-1 font-medium transition-all ${
          lang === "ja"
            ? "bg-primary text-primary-foreground shadow-xs font-semibold"
            : "text-muted-foreground hover:text-foreground"
        }`}
        title="日本語 (Japanese)"
      >
        <span className="text-[12px]">🇯🇵</span>
        <span>日本語</span>
      </button>
    </div>
  );
}
