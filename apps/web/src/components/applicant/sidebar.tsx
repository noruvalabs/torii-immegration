"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { APPLICANT_NAV } from "./nav";
import { cn } from "@/lib/utils";
import { LogOut, UserCircle, Menu, X } from "lucide-react";

export function ApplicantSidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
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

  const isProfileActive = pathname.startsWith("/profile");

  const renderNavContent = (onItemClick?: () => void) => (
    <>
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-5">
        {APPLICANT_NAV.map((item) => {
          const active =
            item.href === "/dashboard"
              ? pathname === "/dashboard"
              : pathname.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onItemClick}
              className={cn(
                "flex items-center gap-3 rounded-[var(--radius)] px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
              )}
            >
              <Icon className="size-4 shrink-0" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t p-3 space-y-1">
        <Link
          href="/profile"
          title={user?.email ?? "Account"}
          onClick={onItemClick}
          className={cn(
            "flex items-center gap-3 rounded-[var(--radius)] px-3 py-2 text-sm font-medium transition-colors",
            isProfileActive
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
          )}
        >
          <UserCircle className="size-4 shrink-0" />
          <span className="truncate text-xs font-medium">
            {user?.email ?? "Account"}
          </span>
        </Link>

        {user && (
          <button
            onClick={() => {
              if (onItemClick) onItemClick();
              handleLogout();
            }}
            className="flex w-full items-center gap-3 rounded-[var(--radius)] px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
          >
            <LogOut className="size-4 shrink-0" />
            Sign out
          </button>
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
          <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium uppercase text-muted-foreground">
            Applicant
          </span>
        </div>
        <button
          type="button"
          onClick={() => setMobileOpen(true)}
          className="inline-flex size-9 items-center justify-center rounded-[var(--radius)] text-muted-foreground hover:bg-accent hover:text-accent-foreground"
          aria-label="Open navigation menu"
        >
          <Menu className="size-5" />
        </button>
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
            <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium uppercase text-muted-foreground">
              Applicant
            </span>
          </div>
          <button
            type="button"
            onClick={() => setMobileOpen(false)}
            className="inline-flex size-8 items-center justify-center rounded-[var(--radius)] text-muted-foreground hover:bg-accent hover:text-accent-foreground"
            aria-label="Close navigation menu"
          >
            <X className="size-5" />
          </button>
        </div>
        {renderNavContent(() => setMobileOpen(false))}
      </div>

      {/* Desktop Sidebar */}
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-r bg-card md:flex">
        <div className="flex h-16 items-center gap-2 border-b px-6">
          <span className="text-xl" aria-hidden>
            ⛩️
          </span>
          <span className="text-lg font-semibold tracking-tight">Torii</span>
          <span className="ml-auto rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium uppercase text-muted-foreground">
            Applicant
          </span>
        </div>
        {renderNavContent()}
      </aside>
    </>
  );
}
