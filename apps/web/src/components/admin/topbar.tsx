import { Search } from "lucide-react";
import { ThemeToggle } from "./theme-toggle";

export function Topbar({ title }: { title: string }) {
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
        <div className="flex size-9 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground">
          OP
        </div>
      </div>
    </header>
  );
}
