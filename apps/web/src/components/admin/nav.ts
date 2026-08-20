import {
  LayoutDashboard,
  FolderKanban,
  Globe,
  BookOpen,
  ClipboardCheck,
  FileText,
  Building2,
  Users,
  BarChart3,
  Settings,
  type LucideIcon,
} from "lucide-react";

export type NavItem = {
  label: string;
  label_ja?: string;
  href: string;
  icon: LucideIcon;
  /** Short gloss shown in tooltips / section headers. */
  hint?: string;
  hint_ja?: string;
  /** Roles that can see this item. If omitted, visible to all. */
  roles?: string[];
};

export type NavGroup = {
  heading: string;
  heading_ja?: string;
  items: NavItem[];
};

/** Back-office navigation — the operations/admin surface (docs/specs/02_requirements.md,
 *  personas OPS / ADM / EMP). Deliberately no commerce: this is a case pipeline, not a store. */
export const NAV: NavGroup[] = [
  {
    heading: "Overview",
    heading_ja: "概要・分析",
    items: [{ label: "Dashboard", label_ja: "ダッシュボード", href: "/admin", icon: LayoutDashboard }],
  },
  {
    heading: "Casework",
    heading_ja: "申請業務",
    items: [
      { label: "Cases", label_ja: "申請案件管理", href: "/admin/cases", icon: FolderKanban, hint: "The canonical case pipeline", hint_ja: "受付・進行中案件パイプライン", roles: ["admin", "ops"] },
      { label: "Review queue", label_ja: "審査確認キュー", href: "/admin/review-queue", icon: ClipboardCheck, hint: "Escalated & low-confidence cases", hint_ja: "要確認・低信頼度案件", roles: ["admin", "ops"] },
      { label: "Employers", label_ja: "企業・所属機関", href: "/admin/employers", icon: Building2, hint: "Workforce-sponsored cases", hint_ja: "企業主導・就労ビザ支援", roles: ["admin", "employer"] },
    ],
  },
  {
    heading: "Content & rules",
    heading_ja: "法規・基準・書式",
    items: [
      { label: "Jurisdictions", label_ja: "対象国・法域基準", href: "/admin/jurisdictions", icon: Globe, hint: "Countries, visas, eligibility", hint_ja: "対象国・在留資格要件マスタ", roles: ["admin", "ops"] },
      { label: "Forms & mappings", label_ja: "申請書式マスタ", href: "/admin/forms", icon: FileText, hint: "Templates + versioned field maps", hint_ja: "法定様式とマッピング", roles: ["admin", "ops"] },
      { label: "Knowledge base", label_ja: "公式ナレッジ", href: "/admin/knowledge-base", icon: BookOpen, hint: "Official-source corpus", hint_ja: "官公庁公式情報・根拠条文", roles: ["admin", "ops"] },
    ],
  },
  {
    heading: "Administration",
    heading_ja: "システム管理",
    items: [
      { label: "Staff & roles", label_ja: "担当者・権限管理", href: "/admin/staff", icon: Users, roles: ["admin"] },
      { label: "Reports", label_ja: "分析レポート", href: "/admin/reports", icon: BarChart3, roles: ["admin"] },
      { label: "Settings", label_ja: "設定・APIキー", href: "/admin/settings", icon: Settings, roles: ["admin"] },
    ],
  },
];
