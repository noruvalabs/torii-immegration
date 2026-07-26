import { LogOut, Search } from "lucide-react";
import { ThemeToggle } from "./theme-toggle";
import { useAuth } from "@/lib/auth-context";
import { useRouter } from "next/navigation";

export function Topbar({ title }: { title: string }) {
  const { user, logout } = useAuth();
  const router = useRouter();

  function handleLogout() {
    logout();
    router.push("/login");
  }

  return (
    <header className="flex h-16 items-center gap-4 border-b bg-background/80 px-6 backdrop-blur">
      <h1 className="text-lg font-semibold tracking-tight">{title}</h1>

      <div className="ml-auto flex items-center gap-3">
        <div className="relative hidden sm:block">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="search"
            placeholder="Search cases, applicants…"
            className="h-9 w-64 rounded-[var(--radius)] border bg-card pl-9 pr-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
        </div>
        <ThemeToggle />
        {user && (
          <>
            <span className="hidden text-sm text-muted-foreground sm:inline">{user.email}</span>
            <button
              onClick={handleLogout}
              title="Sign out"
              className="inline-flex size-9 items-center justify-center rounded-[var(--radius)] text-muted-foreground hover:bg-accent hover:text-accent-foreground"
            >
              <LogOut className="size-4" />
            </button>
          </>
        )}
      </div>
    </header>
  );
}
