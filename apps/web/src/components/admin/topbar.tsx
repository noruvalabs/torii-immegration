import { LogOut, Search } from "lucide-react";
import { ThemeToggle } from "./theme-toggle";
import { useAuth } from "@/lib/auth-context";
import { useI18n, LanguageSwitcher } from "@/lib/i18n";
import { useRouter } from "next/navigation";
import { AppBreadcrumb } from "@/components/breadcrumb-nav";

export function Topbar({ title }: { title: string }) {
  const { user, logout } = useAuth();
  const { t } = useI18n();
  const router = useRouter();

  function handleLogout() {
    logout();
    router.push("/login");
  }

  return (
    <header className="flex h-16 items-center gap-4 border-b bg-card/60 px-6 backdrop-blur sticky top-0 z-30">
      <div className="flex flex-col justify-center min-w-0">
        <AppBreadcrumb />
      </div>

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

        {user && (
          <div className="flex items-center gap-2 border-l pl-3">
            <div className="flex flex-col text-right hidden sm:flex">
              <span className="text-xs font-semibold text-foreground leading-tight">
                {user.full_name || user.username || user.email.split("@")[0]}
              </span>
              <span className="text-[10px] text-muted-foreground leading-tight">{user.email}</span>
            </div>
            <button
              onClick={handleLogout}
              title={t("sign_out", "Sign out")}
              className="inline-flex size-8.5 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
            >
              <LogOut className="size-4" />
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
