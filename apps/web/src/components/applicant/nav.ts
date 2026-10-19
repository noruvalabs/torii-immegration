import {
  Home,
  LayoutDashboard,
  FolderKanban,
  FileText,
  type LucideIcon,
} from "lucide-react";

export type ApplicantNavItem = {
  label: string;
  label_ja?: string;
  href: string;
  icon: LucideIcon;
};

export const APPLICANT_NAV: ApplicantNavItem[] = [
  { label: "Home", label_ja: "ホーム", href: "/", icon: Home },
  { label: "Dashboard", label_ja: "ダッシュボード", href: "/dashboard", icon: LayoutDashboard },
  { label: "Cases", label_ja: "申請案件", href: "/cases", icon: FolderKanban },
  { label: "Documents", label_ja: "書類保管庫", href: "/documents", icon: FileText },
];

