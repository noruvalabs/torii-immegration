"use client";

import React from "react";
import { usePathname } from "next/navigation";
import { Home } from "lucide-react";
import { useI18n } from "@/lib/i18n";
import {
  Breadcrumb,
  BreadcrumbList,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";

export interface BreadcrumbItemDef {
  label: string;
  href?: string;
  active?: boolean;
}

interface AppBreadcrumbProps {
  items?: BreadcrumbItemDef[];
  showHomeIcon?: boolean;
  className?: string;
}

const ROUTE_LABELS: Record<
  string,
  { en: string; ja: string; parent?: { href: string; en: string; ja: string } }
> = {
  // Applicant portal routes
  dashboard: { en: "Dashboard", ja: "ダッシュボード" },
  cases: {
    en: "Cases",
    ja: "申請案件",
    parent: { href: "/admin/cases", en: "Casework", ja: "申請業務" },
  },
  documents: { en: "Document Vault", ja: "書類保管庫" },
  scope: { en: "New Application", ja: "新規申請" },
  profile: { en: "Profile", ja: "アカウント設定" },
  assistant: { en: "AI Assistant", ja: "AIアシスタント" },

  // Admin portal routes
  admin: { en: "Admin", ja: "管理ポータル" },
  "review-queue": {
    en: "Review Queue",
    ja: "審査確認キュー",
    parent: { href: "/admin", en: "Casework", ja: "申請業務" },
  },
  employers: {
    en: "Employers",
    ja: "企業・所属機関",
    parent: { href: "/admin", en: "Casework", ja: "申請業務" },
  },
  jurisdictions: {
    en: "Jurisdictions",
    ja: "対象国・法域基準",
    parent: { href: "/admin", en: "Content & rules", ja: "法規・基準・書式" },
  },
  forms: {
    en: "Forms & Mappings",
    ja: "申請書式マスタ",
    parent: { href: "/admin", en: "Content & rules", ja: "法規・基準・書式" },
  },
  "knowledge-base": {
    en: "Knowledge Base",
    ja: "公式ナレッジ",
    parent: { href: "/admin", en: "Content & rules", ja: "法規・基準・書式" },
  },
  staff: {
    en: "Staff & Roles",
    ja: "担当者・権限管理",
    parent: { href: "/admin", en: "Administration", ja: "システム管理" },
  },
  reports: {
    en: "Reports",
    ja: "分析レポート",
    parent: { href: "/admin", en: "Administration", ja: "システム管理" },
  },
  settings: {
    en: "Settings",
    ja: "設定・APIキー",
    parent: { href: "/admin", en: "Administration", ja: "システム管理" },
  },
};

export function AppBreadcrumb({
  items: customItems,
  showHomeIcon = false,
  className = "",
}: AppBreadcrumbProps) {
  const pathname = usePathname();
  const { lang } = useI18n();

  const items: BreadcrumbItemDef[] = React.useMemo(() => {
    if (customItems && customItems.length > 0) {
      return customItems;
    }

    if (!pathname || pathname === "/") {
      return [];
    }

    const segments = pathname.split("/").filter(Boolean);
    const isAdmin = segments[0] === "admin";
    const result: BreadcrumbItemDef[] = [];

    // Root breadcrumb
    if (isAdmin) {
      result.push({
        label: lang === "ja" ? "管理ポータル" : "Admin",
        href: segments.length > 1 ? "/admin" : undefined,
        active: segments.length === 1,
      });

      if (segments.length > 1) {
        const subSegment = segments[1];
        const routeInfo = ROUTE_LABELS[subSegment];

        if (routeInfo?.parent) {
          result.push({
            label: lang === "ja" ? routeInfo.parent.ja : routeInfo.parent.en,
          });
        }

        const label =
          routeInfo
            ? lang === "ja"
              ? routeInfo.ja
              : routeInfo.en
            : subSegment.charAt(0).toUpperCase() + subSegment.slice(1);

        result.push({
          label,
          href: segments.length > 2 ? `/admin/${subSegment}` : undefined,
          active: segments.length === 2,
        });

        if (segments.length > 2) {
          const detailSegment = segments[2];
          result.push({
            label: `#${detailSegment}`,
            active: true,
          });
        }
      }
    } else {
      // Applicant portal breadcrumb trail
      const rootSegment = segments[0];
      const isDashboard = rootSegment === "dashboard";

      if (!isDashboard) {
        result.push({
          label: lang === "ja" ? "ダッシュボード" : "Dashboard",
          href: "/dashboard",
        });
      }

      const routeInfo = ROUTE_LABELS[rootSegment];
      const label =
        routeInfo
          ? lang === "ja"
            ? routeInfo.ja
            : routeInfo.en
          : rootSegment.charAt(0).toUpperCase() + rootSegment.slice(1);

      result.push({
        label,
        href: segments.length > 1 ? `/${rootSegment}` : undefined,
        active: segments.length === 1,
      });

      if (segments.length > 1) {
        const detailSegment = segments[1];
        result.push({
          label: `#${detailSegment}`,
          active: true,
        });
      }
    }

    return result;
  }, [customItems, pathname, lang]);

  if (!items || items.length === 0) {
    return null;
  }

  return (
    <Breadcrumb className={className}>
      <BreadcrumbList>
        {showHomeIcon && (
          <BreadcrumbItem>
            <BreadcrumbLink
              href={pathname?.startsWith("/admin") ? "/admin" : "/dashboard"}
              aria-label="Home"
              className="inline-flex items-center"
            >
              <Home className="size-3.5" />
            </BreadcrumbLink>
            <BreadcrumbSeparator />
          </BreadcrumbItem>
        )}

        {items.map((item, index) => {
          const isLast = index === items.length - 1 || item.active;

          return (
            <React.Fragment key={`${item.label}-${index}`}>
              <BreadcrumbItem>
                {isLast ? (
                  <BreadcrumbPage>{item.label}</BreadcrumbPage>
                ) : (
                  <BreadcrumbLink href={item.href}>{item.label}</BreadcrumbLink>
                )}
              </BreadcrumbItem>
              {!isLast && <BreadcrumbSeparator />}
            </React.Fragment>
          );
        })}
      </BreadcrumbList>
    </Breadcrumb>
  );
}
