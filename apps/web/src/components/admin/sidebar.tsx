"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV } from "./nav";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth-context";
import { useI18n } from "@/lib/i18n";
import { useAdminSidebar } from "./admin-sidebar-context";
import { PanelLeftClose, PanelLeftOpen, X } from "lucide-react";

export function Sidebar() {
  const pathname = usePathname();
  const { user } = useAuth();
  const { lang, t } = useI18n();
  const { collapsed, toggleCollapsed, mobileOpen, setMobileOpen } = useAdminSidebar();
  const role = user?.role ?? "";

  const visibleNav = NAV.map((group) => ({
    ...group,
    headingDisplay: lang === "ja" && group.heading_ja ? group.heading_ja : group.heading,
    items: group.items
      .filter((item) => !item.roles || item.roles.includes(role))
      .map((item) => ({
        ...item,
        labelDisplay: lang === "ja" && item.label_ja ? item.label_ja : item.label,
        hintDisplay: lang === "ja" && item.hint_ja ? item.hint_ja : item.hint,
      })),
  })).filter((group) => group.items.length > 0);

  const roleLabels: Record<string, string> = {
    admin: t("nav_role_admin", "ADMIN"),
    ops: t("nav_role_ops", "OPS"),
    employer: t("nav_role_employer", "EMPLOYER"),
  };

  const renderNav = (onItemClick?: () => void, isCompact = false) => (
    <nav className={cn("flex-1 overflow-y-auto py-4", isCompact ? "space-y-4 px-2" : "space-y-5 px-3")}>
      {visibleNav.map((group) => (
        <div key={group.heading}>
          {!isCompact && (
            <p className="px-3 pb-1.5 text-[10px] font-bold uppercase tracking-wider text-muted-foreground/80">
              {group.headingDisplay}
            </p>
          )}
          {isCompact && (
            <div className="mx-auto mb-2 w-6 border-t border-border/60" />
          )}
          <ul className="space-y-1">
            {group.items.map((item) => {
              const active =
                item.href === "/admin"
                  ? pathname === "/admin"
                  : pathname.startsWith(item.href);
              const Icon = item.icon;

              if (isCompact) {
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      onClick={onItemClick}
                      title={`${item.labelDisplay}${item.hintDisplay ? ` — ${item.hintDisplay}` : ""}`}
                      className={cn(
                        "group relative flex size-11 items-center justify-center rounded-xl transition-all mx-auto",
                        active
                          ? "bg-primary text-primary-foreground shadow-xs font-bold"
                          : "text-muted-foreground hover:bg-muted hover:text-foreground",
                      )}
                    >
                      <Icon className="size-5 shrink-0" />
                    </Link>
                  </li>
                );
              }

              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    onClick={onItemClick}
                    title={item.hintDisplay}
                    className={cn(
                      "flex items-center gap-3 rounded-lg px-3 py-2 text-xs font-semibold transition-all",
                      active
                        ? "bg-primary text-primary-foreground shadow-xs"
                        : "text-muted-foreground hover:bg-muted hover:text-foreground",
                    )}
                  >
                    <Icon className="size-4 shrink-0" />
                    <span>{item.labelDisplay}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );

  return (
    <>
      {/* Mobile Drawer Backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-background/80 backdrop-blur-sm md:hidden animate-in fade-in duration-200"
          onClick={() => setMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Mobile Drawer Panel */}
      <div
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r bg-card shadow-2xl transition-transform duration-300 ease-in-out md:hidden",
          mobileOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex h-16 items-center justify-between border-b px-4">
          <div className="flex items-center gap-2">
            <span className="text-2xl" aria-hidden>
              ⛩️
            </span>
            <div className="flex flex-col">
              <span className="text-base font-bold tracking-tight bg-gradient-to-r from-primary to-primary/70 bg-clip-text text-transparent">
                Torii
              </span>
              <span className="text-[10px] text-muted-foreground -mt-0.5">
                {lang === "ja" ? "在留・査証管理基盤" : "Immigration Core"}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="rounded-full bg-primary/10 border border-primary/20 px-2 py-0.5 text-[10px] font-bold uppercase text-primary">
              {roleLabels[role] || role.toUpperCase() || "GUEST"}
            </span>
            <button
              type="button"
              onClick={() => setMobileOpen(false)}
              className="inline-flex size-8 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
              aria-label="Close navigation menu"
            >
              <X className="size-5" />
            </button>
          </div>
        </div>

        {renderNav(() => setMobileOpen(false), false)}

        <div className="border-t p-4 text-[11px] leading-relaxed text-muted-foreground bg-muted/20">
          {t("nav_disclaimer", "Guided immigration form preparation — not legal advice.")}
        </div>
      </div>

      {/* Desktop Sidebar */}
      <aside
        className={cn(
          "sticky top-0 hidden h-screen shrink-0 flex-col border-r bg-card/95 backdrop-blur transition-[width] duration-300 ease-in-out md:flex",
          collapsed ? "w-[68px]" : "w-64",
        )}
      >
        {/* Desktop Header */}
        <div className={cn("flex h-16 items-center border-b", collapsed ? "justify-center px-2" : "justify-between px-4")}>
          {collapsed ? (
            <button
              type="button"
              onClick={toggleCollapsed}
              title={lang === "ja" ? "サイドバーを展開" : "Expand sidebar"}
              className="flex size-9 items-center justify-center rounded-xl text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
            >
              <PanelLeftOpen className="size-5" />
            </button>
          ) : (
            <>
              <div className="flex items-center gap-2.5 min-w-0">
                <span className="text-2xl shrink-0" aria-hidden>
                  ⛩️
                </span>
                <div className="flex flex-col min-w-0">
                  <span className="text-base font-bold tracking-tight bg-gradient-to-r from-primary to-primary/70 bg-clip-text text-transparent truncate">
                    Torii
                  </span>
                  <span className="text-[10px] text-muted-foreground -mt-0.5 truncate">
                    {lang === "ja" ? "在留・査証管理基盤" : "Immigration Core"}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-1.5 shrink-0">
                <span className="rounded-full bg-primary/10 border border-primary/20 px-2 py-0.5 text-[10px] font-bold uppercase text-primary">
                  {roleLabels[role] || role.toUpperCase() || "GUEST"}
                </span>
                <button
                  type="button"
                  onClick={toggleCollapsed}
                  title={lang === "ja" ? "サイドバーを折りたたむ" : "Collapse sidebar"}
                  className="flex size-8 items-center justify-center rounded-lg text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
                >
                  <PanelLeftClose className="size-4.5" />
                </button>
              </div>
            </>
          )}
        </div>

        {renderNav(undefined, collapsed)}

        {!collapsed && (
          <div className="border-t p-4 text-[11px] leading-relaxed text-muted-foreground bg-muted/20">
            {t("nav_disclaimer", "Guided immigration form preparation — not legal advice.")}
          </div>
        )}
      </aside>
    </>
  );
}
