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
  href: string;
  icon: LucideIcon;
  /** Short gloss shown in tooltips / section headers. */
  hint?: string;
  /** Roles that can see this item. If omitted, visible to all. */
  roles?: string[];
};

export type NavGroup = {
  heading: string;
  items: NavItem[];
};

/** Back-office navigation — the operations/admin surface (docs/specs/02_requirements.md,
 *  personas OPS / ADM / EMP). Deliberately no commerce: this is a case pipeline, not a store. */
export const NAV: NavGroup[] = [
  {
    heading: "Overview",
    items: [{ label: "Dashboard", href: "/admin", icon: LayoutDashboard }],
  },
  {
    heading: "Casework",
    items: [
      { label: "Cases", href: "/admin/cases", icon: FolderKanban, hint: "The canonical case pipeline", roles: ["admin", "ops"] },
      { label: "Review queue", href: "/admin/review-queue", icon: ClipboardCheck, hint: "Escalated & low-confidence cases", roles: ["admin", "ops"] },
      { label: "Employers", href: "/admin/employers", icon: Building2, hint: "Workforce-sponsored cases", roles: ["admin", "employer"] },
    ],
  },
  {
    heading: "Content & rules",
    items: [
      { label: "Jurisdictions", href: "/admin/jurisdictions", icon: Globe, hint: "Countries, visas, eligibility", roles: ["admin", "ops"] },
      { label: "Forms & mappings", href: "/admin/forms", icon: FileText, hint: "Templates + versioned field maps", roles: ["admin", "ops"] },
      { label: "Knowledge base", href: "/admin/knowledge-base", icon: BookOpen, hint: "Official-source corpus", roles: ["admin", "ops"] },
    ],
  },
  {
    heading: "Administration",
    items: [
      { label: "Staff & roles", href: "/admin/staff", icon: Users, roles: ["admin"] },
      { label: "Reports", href: "/admin/reports", icon: BarChart3, roles: ["admin"] },
      { label: "Settings", href: "/admin/settings", icon: Settings, roles: ["admin"] },
    ],
  },
];
