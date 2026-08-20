"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV } from "./nav";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth-context";
import { useI18n } from "@/lib/i18n";

export function Sidebar() {
  const pathname = usePathname();
  const { user } = useAuth();
  const { lang, t } = useI18n();
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

  return (
    <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-r bg-card/95 backdrop-blur md:flex">
      <div className="flex h-16 items-center gap-2.5 border-b px-6">
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
        <span className="ml-auto rounded-full bg-primary/10 border border-primary/20 px-2 py-0.5 text-[10px] font-bold uppercase text-primary">
          {roleLabels[role] || role.toUpperCase() || "GUEST"}
        </span>
      </div>

      <nav className="flex-1 space-y-5 overflow-y-auto px-3 py-4">
        {visibleNav.map((group) => (
          <div key={group.heading}>
            <p className="px-3 pb-1.5 text-[10px] font-bold uppercase tracking-wider text-muted-foreground/80">
              {group.headingDisplay}
            </p>
            <ul className="space-y-0.5">
              {group.items.map((item) => {
                const active =
                  item.href === "/admin"
                    ? pathname === "/admin"
                    : pathname.startsWith(item.href);
                const Icon = item.icon;
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
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

      <div className="border-t p-4 text-[11px] leading-relaxed text-muted-foreground bg-muted/20">
        {t("nav_disclaimer", "Guided immigration form preparation — not legal advice.")}
      </div>
    </aside>
  );
}
