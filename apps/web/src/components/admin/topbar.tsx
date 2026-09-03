"use client";

import { Menu, Search } from "lucide-react";
import { ThemeToggle } from "./theme-toggle";
import { useI18n, LanguageSwitcher } from "@/lib/i18n";
import { useAdminSidebar } from "./admin-sidebar-context";

export function Topbar({ title }: { title: string }) {
  const { t } = useI18n();
  const { setMobileOpen } = useAdminSidebar();

  return (
    <header className="flex h-16 items-center gap-3 border-b bg-card/60 px-4 sm:px-6 backdrop-blur sticky top-0 z-30">
      <button
        type="button"
        onClick={() => setMobileOpen(true)}
        className="inline-flex size-9 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground md:hidden transition-colors"
        aria-label="Open navigation menu"
      >
        <Menu className="size-5" />
      </button>

      <h1 className="text-base font-bold tracking-tight text-foreground truncate">{title}</h1>

      <div className="ml-auto flex items-center gap-3">
        <div className="relative hidden md:block">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
          <input
            type="search"
            placeholder={t("search_placeholder", "Search cases, applicants…")}
            className="h-8.5 w-64 rounded-lg border bg-background/80 pl-8.5 pr-3 text-xs outline-none focus-visible:ring-1 focus-visible:ring-ring"
          />
        </div>

        {/* Global Language Switcher EN / JP */}
        <LanguageSwitcher />

        <ThemeToggle />
      </div>
    </header>
  );
}
