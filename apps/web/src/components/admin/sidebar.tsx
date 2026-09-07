"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { NAV } from "./nav";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth-context";
import { useI18n } from "@/lib/i18n";
import { useAdminSidebar } from "./admin-sidebar-context";
import {
  PanelLeftClose,
  PanelLeftOpen,
  X,
  ChevronRight,
  LogOut,
  Settings,
  User as UserIcon,
} from "lucide-react";
import { ToriiLogo } from "@/components/brand/ToriiLogo";
import { UserAvatar } from "@/components/ui/avatar";

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const { lang, t } = useI18n();
  const { collapsed, toggleCollapsed, mobileOpen, setMobileOpen } = useAdminSidebar();
  const role = user?.role ?? "";

  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    }
    if (menuOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [menuOpen]);

  function handleLogout() {
    logout();
    router.push("/login");
  }

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

  const initials = (user?.full_name || user?.username || user?.email || "AD")
    .split(" ")
    .map((n) => n[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  const displayName =
    user?.full_name || user?.username || user?.email?.split("@")[0] || "Admin";
  const userRole = roleLabels[role] || (role ? role.toUpperCase() : "GUEST");

  const renderUserMenu = (onItemClick?: () => void, isCompact = false) => (
    <div className={cn("relative border-t bg-muted/10", isCompact ? "p-2 flex flex-col items-center gap-2" : "p-3")} ref={menuRef}>
      {/* Floating Popover Menu */}
      {menuOpen && (
        <div
          className={cn(
            "absolute bottom-full mb-2 z-50 rounded-2xl border bg-popover/95 text-popover-foreground shadow-2xl backdrop-blur-xl animate-in fade-in slide-in-from-bottom-2 duration-150 p-1.5 space-y-1",
            isCompact ? "left-2 w-56" : "left-3 right-3",
          )}
        >
          {/* Account / Settings Item */}
          <Link
            href="/admin/settings"
            onClick={() => {
              setMenuOpen(false);
              if (onItemClick) onItemClick();
            }}
            className="flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-xs font-semibold text-foreground hover:bg-muted/70 transition-colors group"
          >
            <UserAvatar
              src={user?.avatar_url}
              alt={displayName}
              initials={initials}
              sizeClassName="size-7"
              textClassName="text-[11px]"
              gradientClassName="bg-gradient-to-br from-primary to-primary/70 text-primary-foreground"
            />
            <div className="flex flex-col min-w-0 flex-1">
              <span className="text-xs font-bold text-foreground truncate">{displayName}</span>
              <span className="text-[10px] text-muted-foreground truncate">{user?.email}</span>
            </div>
            <ChevronRight className="size-4 text-muted-foreground group-hover:translate-x-0.5 transition-transform" />
          </Link>

          {/* System Settings Item */}
          <Link
            href="/admin/settings"
            onClick={() => {
              setMenuOpen(false);
              if (onItemClick) onItemClick();
            }}
            className="flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-xs font-semibold text-foreground hover:bg-muted/70 transition-colors group"
          >
            <div className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary border border-primary/20">
              <Settings className="size-3.5" />
            </div>
            <div className="flex flex-col min-w-0 flex-1">
              <span className="text-xs font-bold text-foreground truncate">{lang === "ja" ? "システム設定" : "System Settings"}</span>
              <span className="text-[10px] text-muted-foreground truncate">{lang === "ja" ? "管理・環境設定" : "Configuration & Staff"}</span>
            </div>
            <ChevronRight className="size-4 text-muted-foreground group-hover:translate-x-0.5 transition-transform" />
          </Link>

          {/* Profile Item */}
          <Link
            href="/profile"
            onClick={() => {
              setMenuOpen(false);
              if (onItemClick) onItemClick();
            }}
            className="flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-xs font-semibold text-foreground hover:bg-muted/70 transition-colors group"
          >
            <div className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-muted text-foreground border">
              <UserIcon className="size-3.5" />
            </div>
            <div className="flex flex-col min-w-0 flex-1">
              <span className="text-xs font-bold text-foreground truncate">{lang === "ja" ? "個人設定" : "Personal Profile"}</span>
              <span className="text-[10px] text-muted-foreground truncate">{lang === "ja" ? "プロフィール確認" : "View profile details"}</span>
            </div>
            <ChevronRight className="size-4 text-muted-foreground group-hover:translate-x-0.5 transition-transform" />
          </Link>

          <div className="border-t border-border/60 my-1" />

          {/* Logout Item */}
          <button
            type="button"
            onClick={() => {
              setMenuOpen(false);
              if (onItemClick) onItemClick();
              handleLogout();
            }}
            className="flex w-full items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-semibold text-[var(--color-danger)] hover:bg-[var(--color-danger)]/10 transition-colors"
          >
            <LogOut className="size-4 shrink-0" />
            <span>{lang === "ja" ? "ログアウト" : "Log out"}</span>
          </button>
        </div>
      )}

      {isCompact ? (
        <button
          type="button"
          onClick={() => setMenuOpen(!menuOpen)}
          title={`${displayName} (${userRole})`}
          className={cn(
            "flex size-10 items-center justify-center rounded-xl transition-all border",
            menuOpen
              ? "bg-muted border-border shadow-xs"
              : "border-transparent hover:bg-muted/50 hover:border-border/60",
          )}
        >
          <UserAvatar
            src={user?.avatar_url}
            alt={displayName}
            initials={initials}
            sizeClassName="size-8"
            textClassName="text-xs"
            gradientClassName="bg-gradient-to-br from-primary to-primary/70 text-primary-foreground"
          />
        </button>
      ) : (
        <button
          type="button"
          onClick={() => setMenuOpen(!menuOpen)}
          className={cn(
            "flex w-full items-center justify-between gap-2.5 rounded-xl p-2 transition-all border text-left",
            menuOpen
              ? "bg-muted border-border shadow-xs"
              : "border-transparent hover:bg-muted/50 hover:border-border/60",
          )}
        >
          <div className="flex items-center gap-2.5 min-w-0">
            <UserAvatar
              src={user?.avatar_url}
              alt={displayName}
              initials={initials}
              sizeClassName="size-8"
              textClassName="text-xs"
              gradientClassName="bg-gradient-to-br from-primary to-primary/70 text-primary-foreground"
            />
            <div className="flex flex-col min-w-0">
              <span className="truncate text-xs font-semibold text-foreground leading-tight">
                {displayName}
              </span>
              <span className="truncate text-[10px] text-muted-foreground leading-tight mt-0.5 flex items-center gap-1.5">
                <span className="font-semibold text-primary">{userRole}</span>
                <span>•</span>
                <span className="truncate">{user?.email}</span>
              </span>
            </div>
          </div>
          <ChevronRight className={`size-4 text-muted-foreground transition-transform duration-200 ${menuOpen ? "rotate-90" : ""}`} />
        </button>
      )}
    </div>
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
          <div className="flex items-center gap-3">
            <ToriiLogo size={34} />
            <div className="flex flex-col">
              <span className="text-lg font-bold tracking-tight bg-gradient-to-r from-primary to-primary/70 bg-clip-text text-transparent">
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
        {renderUserMenu(() => setMobileOpen(false), false)}
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
              className="flex size-11 items-center justify-center rounded-xl text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
            >
              <ToriiLogo size={26} />
            </button>
          ) : (
            <>
              <div className="flex items-center gap-3 min-w-0">
                <ToriiLogo size={34} />
                <div className="flex flex-col min-w-0">
                  <span className="text-lg font-bold tracking-tight bg-gradient-to-r from-primary to-primary/70 bg-clip-text text-transparent truncate">
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
        {renderUserMenu(undefined, collapsed)}
      </aside>
    </>
  );
}
