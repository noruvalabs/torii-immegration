import {
  LayoutDashboard,
  FolderKanban,
  FileText,
  Coins,
  BookOpen,
  type LucideIcon,
} from "lucide-react";

export type ApplicantNavItem = {
  label: string;
  label_ja?: string;
  href: string;
  icon: LucideIcon;
};

export const APPLICANT_NAV: ApplicantNavItem[] = [
  { label: "Dashboard", label_ja: "ダッシュボード", href: "/dashboard", icon: LayoutDashboard },
  { label: "Cases", label_ja: "申請案件", href: "/cases", icon: FolderKanban },
  { label: "Documents", label_ja: "書類保管庫", href: "/documents", icon: FileText },
  { label: "Credits & Passes", label_ja: "クレジット・パス", href: "/credits", icon: Coins },
  { label: "Help & Guide", label_ja: "ご利用ガイド", href: "/help", icon: BookOpen },
];

