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
  UserCircle,
  Menu,
  X,
  Sparkles,
  Clock,
  User,
  Settings,
  HelpCircle,
  ChevronRight,
} from "lucide-react";

import { CreditBalanceBadge } from "@/components/credits/CreditBalanceBadge";

export function ApplicantSidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const { lang, t } = useI18n();
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

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

  const renderNavContent = (onItemClick?: () => void) => (
    <>
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {APPLICANT_NAV.map((item) => {
          const active =
            item.href === "/dashboard"
              ? pathname === "/dashboard"
              : pathname.startsWith(item.href);
          const Icon = item.icon;
          const label = lang === "ja" && item.label_ja ? item.label_ja : item.label;
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

      {/* ChatGPT-style Popup User Profile & Logout Menu */}
      <div className="relative border-t p-3 bg-muted/10" ref={menuRef}>
        {/* Floating Popover Menu */}
        {menuOpen && (
          <div className="absolute bottom-full left-3 right-3 mb-2 z-50 rounded-2xl border bg-popover/95 text-popover-foreground shadow-2xl backdrop-blur-xl animate-in fade-in slide-in-from-bottom-2 duration-150 p-1.5 space-y-1">
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

        {/* Trigger Button Matching Screenshot */}
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
              <span className="truncate text-[10px] text-muted-foreground leading-tight mt-0.5">
                {userPlan}
              </span>
            </div>
          </div>
          <ChevronRight className={`size-4 text-muted-foreground transition-transform duration-200 ${menuOpen ? "rotate-90" : ""}`} />
        </button>
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
            className="inline-flex size-9 items-center justify-center rounded-[var(--radius)] text-muted-foreground hover:bg-accent hover:text-accent-foreground"
            aria-label="Open navigation menu"
          >
            <Menu className="size-5" />
          </button>
        </div>
      </header>

      {/* Mobile Drawer Backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-background/80 backdrop-blur-sm md:hidden"
          onClick={() => setMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Mobile Drawer Panel */}
      <div
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r bg-card shadow-2xl transition-transform duration-200 ease-in-out md:hidden",
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
              className="inline-flex size-8 items-center justify-center rounded-[var(--radius)] text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              aria-label="Close navigation menu"
            >
              <X className="size-5" />
            </button>
          </div>
        </div>
        {renderNavContent(() => setMobileOpen(false))}
      </div>

      {/* Desktop Sidebar */}
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-r bg-card md:flex">
        <div className="flex h-16 items-center justify-between border-b px-5">
          <div className="flex items-center gap-2">
            <span className="text-xl" aria-hidden>
              ⛩️
            </span>
            <span className="text-lg font-bold tracking-tight">Torii</span>
          </div>
          <CreditBalanceBadge />
        </div>
        {renderNavContent()}
      </aside>
    </>
  );
}
