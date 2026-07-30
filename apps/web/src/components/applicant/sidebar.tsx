"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { APPLICANT_NAV } from "./nav";
import { cn } from "@/lib/utils";
import { LogOut } from "lucide-react";

export function ApplicantSidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const router = useRouter();

  function handleLogout() {
    logout();
    router.push("/login");
  }

  return (
    <aside className="hidden w-64 shrink-0 flex-col border-r bg-card md:flex">
      <div className="flex h-16 items-center gap-2 border-b px-6">
        <span className="text-xl" aria-hidden>⛩️</span>
        <span className="text-lg font-semibold tracking-tight">Torii</span>
        <span className="ml-auto rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium uppercase text-muted-foreground">
          Applicant
        </span>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-5">
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

      {user && (
        <div className="border-t p-4">
          <p className="mb-2 truncate text-xs text-muted-foreground">{user.email}</p>
          <button
            onClick={handleLogout}
            className="flex w-full items-center gap-2 rounded-[var(--radius)] px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
          >
            <LogOut className="size-4" />
            Sign out
          </button>
        </div>
      )}
    </aside>
  );
}
