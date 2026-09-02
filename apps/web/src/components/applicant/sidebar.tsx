"use client";

import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { useI18n } from "@/lib/i18n";
import { APPLICANT_NAV } from "./nav";
import { cn } from "@/lib/utils";
import {
  LogOut,
  Menu,
  X,
  ChevronRight,
  PanelLeftClose,
  PanelLeftOpen,
  Coins,
} from "lucide-react";

import { CreditBalanceBadge } from "@/components/credits/CreditBalanceBadge";
import { useCredits } from "@/lib/credits-context";

export function ApplicantSidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const { balance } = useCredits();
  const { lang } = useI18n();
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  // Load user collapse preference
  useEffect(() => {
    const saved = localStorage.getItem("torii_user_sidebar_collapsed");
    if (saved !== null) {
      setCollapsed(saved === "true");
    }
  }, []);

  function toggleCollapsed() {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem("torii_user_sidebar_collapsed", String(next));
      return next;
    });
  }

  // Close mobile drawer on route change
  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  // Handle ESC key for mobile drawer
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setMobileOpen(false);
    }
    if (mobileOpen) {
      window.addEventListener("keydown", handleKeyDown);
      return () => window.removeEventListener("keydown", handleKeyDown);
    }
  }, [mobileOpen]);

  function handleLogout() {
    logout();
    router.push("/login");
  }

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

  const initials = (user?.full_name || user?.username || user?.email || "HA")
    .split(" ")
    .map((n) => n[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  const displayName =
    user?.full_name || user?.username || user?.email?.split("@")[0] || "User";
  const userPlan = user?.role === "admin" ? "Admin" : user?.role === "ops" ? "Operations" : "Free";

  const renderNavContent = (onItemClick?: () => void, isCompact = false) => (
    <>
      <nav className={cn("flex-1 space-y-1.5 overflow-y-auto py-4", isCompact ? "px-2" : "px-3")}>
        {APPLICANT_NAV.map((item) => {
          const active =
            item.href === "/dashboard"
              ? pathname === "/dashboard"
              : pathname.startsWith(item.href);
          const Icon = item.icon;
          const label = lang === "ja" && item.label_ja ? item.label_ja : item.label;

          if (isCompact) {
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={onItemClick}
                title={label}
                className={cn(
                  "group relative flex size-11 items-center justify-center rounded-xl transition-all mx-auto",
                  active
                    ? "bg-primary text-primary-foreground shadow-xs font-bold"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground",
                )}
              >
                <Icon className="size-5 shrink-0" />
              </Link>
            );
          }

          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onItemClick}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-xs font-semibold transition-all",
                active
                  ? "bg-primary text-primary-foreground shadow-xs font-bold"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground",
              )}
            >
              <Icon className="size-4 shrink-0" />
              <span>{label}</span>
            </Link>
          );
        })}
      </nav>

      {/* User Profile & Logout Menu */}
      <div className={cn("relative border-t bg-muted/10", isCompact ? "p-2 flex flex-col items-center gap-2" : "p-3")} ref={menuRef}>
        {/* Floating Popover Menu */}
        {menuOpen && (
          <div
            className={cn(
              "absolute bottom-full mb-2 z-50 rounded-2xl border bg-popover/95 text-popover-foreground shadow-2xl backdrop-blur-xl animate-in fade-in slide-in-from-bottom-2 duration-150 p-1.5 space-y-1",
              isCompact ? "left-2 w-56" : "left-3 right-3",
            )}
          >
            {/* Account / Profile Item */}
            <Link
              href="/profile"
              onClick={() => {
                setMenuOpen(false);
                if (onItemClick) onItemClick();
              }}
              className="flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-xs font-semibold text-foreground hover:bg-muted/70 transition-colors group"
            >
              <div className="flex size-7 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-amber-600 to-orange-500 text-white font-bold text-[11px] shadow-xs">
                {initials}
              </div>
              <div className="flex flex-col min-w-0 flex-1">
                <span className="text-xs font-bold text-foreground truncate">{displayName}</span>
                <span className="text-[10px] text-muted-foreground">{lang === "ja" ? "アカウント設定" : "Account & Profile"}</span>
              </div>
              <ChevronRight className="size-4 text-muted-foreground group-hover:translate-x-0.5 transition-transform" />
            </Link>

            {/* Credits & Passes Item */}
            <Link
              href="/credits"
              onClick={() => {
                setMenuOpen(false);
                if (onItemClick) onItemClick();
              }}
              className="flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-xs font-semibold text-foreground hover:bg-muted/70 transition-colors group"
            >
              <div className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-amber-500/10 text-amber-500 border border-amber-500/20">
                <Coins className="size-3.5" />
              </div>
              <div className="flex flex-col min-w-0 flex-1">
                <span className="text-xs font-bold text-foreground truncate">{lang === "ja" ? "クレジット・パス" : "Credits & Passes"}</span>
                <span className="text-[10px] text-amber-600 dark:text-amber-400 font-semibold">{balance} {balance === 1 ? "Pass" : "Passes"} Available</span>
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
          <div className="flex flex-col items-center gap-2">
            <CreditBalanceBadge compact />
            <button
              type="button"
              onClick={() => setMenuOpen(!menuOpen)}
              title={`${displayName} (${balance} passes)`}
              className={cn(
                "flex size-10 items-center justify-center rounded-xl transition-all border",
                menuOpen
                  ? "bg-muted border-border shadow-xs"
                  : "border-transparent hover:bg-muted/50 hover:border-border/60",
              )}
            >
              <div className="flex size-8 items-center justify-center rounded-full bg-gradient-to-br from-amber-600 to-orange-500 text-white font-bold text-xs shadow-xs">
                {initials}
              </div>
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            {/* Quick Credit Banner in Avatar Section */}
            <Link
              href="/credits"
              onClick={() => {
                if (onItemClick) onItemClick();
              }}
              className="flex items-center justify-between gap-2 px-3 py-2 rounded-xl border border-amber-500/30 bg-amber-500/10 hover:bg-amber-500/20 text-amber-700 dark:text-amber-300 transition-all group shadow-xs"
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-amber-500 text-white shadow-xs group-hover:scale-105 transition-transform">
                  <Coins className="size-4" />
                </div>
                <div className="flex flex-col min-w-0">
                  <span className="text-xs font-bold leading-none truncate text-foreground">
                    {balance} {balance === 1 ? "Pass" : "Passes"} Available
                  </span>
                  <span className="text-[10px] text-muted-foreground leading-tight mt-0.5 truncate">
                    {lang === "ja" ? "残高確認・パス購入" : "View balance & top up"}
                  </span>
                </div>
              </div>
              <ChevronRight className="size-3.5 text-muted-foreground group-hover:translate-x-0.5 transition-transform" />
            </Link>

            {/* Avatar Profile Button */}
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
                <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-amber-600 to-orange-500 text-white font-bold text-xs shadow-xs">
                  {initials}
                </div>
                <div className="flex flex-col min-w-0">
                  <span className="truncate text-xs font-semibold text-foreground leading-tight">
                    {displayName}
                  </span>
                  <span className="truncate text-[10px] text-muted-foreground leading-tight mt-0.5 flex items-center gap-1.5">
                    <span>{userPlan}</span>
                    <span>•</span>
                    <span className="text-amber-600 dark:text-amber-400 font-semibold">{balance} {balance === 1 ? "Pass" : "Passes"}</span>
                  </span>
                </div>
              </div>
              <ChevronRight className={`size-4 text-muted-foreground transition-transform duration-200 ${menuOpen ? "rotate-90" : ""}`} />
            </button>
          </div>
        )}
      </div>
    </>
  );

  return (
    <>
      {/* Mobile Top Header */}
      <header className="flex h-14 shrink-0 items-center justify-between border-b bg-card px-4 md:hidden">
        <div className="flex items-center gap-2">
          <span className="text-xl" aria-hidden>
            ⛩️
          </span>
          <span className="text-lg font-semibold tracking-tight">Torii</span>
        </div>
        <div className="flex items-center gap-2">
          <CreditBalanceBadge />
          <button
            type="button"
            onClick={() => setMobileOpen(true)}
            className="inline-flex size-9 items-center justify-center rounded-[var(--radius)] text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
            aria-label="Open navigation menu"
          >
            <Menu className="size-5" />
          </button>
        </div>
      </header>

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
        <div className="flex h-14 items-center justify-between border-b px-4">
          <div className="flex items-center gap-2">
            <span className="text-xl" aria-hidden>
              ⛩️
            </span>
            <span className="text-lg font-semibold tracking-tight">Torii</span>
          </div>
          <div className="flex items-center gap-2">
            <CreditBalanceBadge />
            <button
              type="button"
              onClick={() => setMobileOpen(false)}
              className="inline-flex size-8 items-center justify-center rounded-[var(--radius)] text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
              aria-label="Close navigation menu"
            >
              <X className="size-5" />
            </button>
          </div>
        </div>
        {renderNavContent(() => setMobileOpen(false), false)}
      </div>

      {/* Desktop Sidebar */}
      <aside
        className={cn(
          "sticky top-0 hidden h-screen shrink-0 flex-col border-r bg-card transition-[width] duration-300 ease-in-out md:flex",
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
              <div className="flex items-center gap-2">
                <span className="text-xl" aria-hidden>
                  ⛩️
                </span>
                <span className="text-lg font-bold tracking-tight">Torii</span>
              </div>
              <div className="flex items-center gap-1.5">
                <CreditBalanceBadge />
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
        {renderNavContent(undefined, collapsed)}
      </aside>
    </>
  );
}
