import {
  LayoutDashboard,
  FolderKanban,
  FileText,
  type LucideIcon,
} from "lucide-react";

export type ApplicantNavItem = {
  label: string;
  href: string;
  icon: LucideIcon;
};

export const APPLICANT_NAV: ApplicantNavItem[] = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Cases", href: "/cases", icon: FolderKanban },
  { label: "Documents", href: "/documents", icon: FileText },
];

