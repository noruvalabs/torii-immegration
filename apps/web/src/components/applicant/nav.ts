import {
  LayoutDashboard,
  FolderKanban,
  Plus,
  MessageSquare,
  UserCircle,
  type LucideIcon,
} from "lucide-react";

export type ApplicantNavItem = {
  label: string;
  href: string;
  icon: LucideIcon;
};

export const APPLICANT_NAV: ApplicantNavItem[] = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "My cases", href: "/cases", icon: FolderKanban },
  { label: "New case", href: "/scope", icon: Plus },
  { label: "Assistant", href: "/assistant", icon: MessageSquare },
  { label: "Profile", href: "/profile", icon: UserCircle },
];
