"use client";

import { useCallback, useEffect, useState } from "react";
import { FolderKanban, Search, ExternalLink } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/lib/auth-context";
import { adminListCases, type AdminCase } from "@/lib/api/cases";

const statusConfig: Record<string, { tone: "default" | "success" | "warning" | "danger" | "muted" }> = {
  draft: { tone: "muted" },
  intake_complete: { tone: "default" },
  checklist_ready: { tone: "default" },
  forms_generated: { tone: "default" },
  packet_ready: { tone: "success" },
  submitted: { tone: "success" },
};

export default function CasesPage() {
  const { token } = useAuth();
  const [cases, setCases] = useState<AdminCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");
  const [search, setSearch] = useState("");

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const data = await adminListCases(token, { status: filter || undefined });
      setCases(data);
    } catch {
      setError("Could not load cases.");
    } finally {
      setLoading(false);
    }
  }, [token, filter]);

  useEffect(() => { void load(); }, [load]);

  const filtered = cases.filter((c) => {
    if (search && c.reference && !c.reference.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-4">
        <div className="flex size-11 items-center justify-center rounded-[var(--radius)] bg-accent text-accent-foreground">
          <FolderKanban className="size-5" />
        </div>
        <div>
          <h2 className="text-xl font-semibold tracking-tight">Cases</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            The canonical case pipeline — self-serve, employer-managed, or lawyer-returned, all
            one case model with one status lifecycle (US-03, US-18, NF-6).
          </p>
        </div>
      </div>

      {error && (
        <p className="rounded-[var(--radius)] border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/10 px-4 py-3 text-sm text-[var(--color-danger)]">
          {error}
        </p>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 sm:max-w-xs">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by reference…"
            className="h-9 w-full rounded-[var(--radius)] border bg-background pl-9 pr-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
        </div>
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="h-9 rounded-[var(--radius)] border bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <option value="">All statuses</option>
          <option value="draft">Draft</option>
          <option value="intake_complete">Intake complete</option>
          <option value="checklist_ready">Checklist ready</option>
          <option value="forms_generated">Forms generated</option>
          <option value="packet_ready">Packet ready</option>
          <option value="submitted">Submitted</option>
        </select>
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading cases…</p>
      ) : filtered.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center">
            <FolderKanban className="mx-auto mb-3 size-8 text-muted-foreground/50" />
            <p className="text-sm text-muted-foreground">
              {cases.length === 0
                ? "No cases in the system yet. Cases appear here once applicants create them."
                : "No cases match your filter."}
            </p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-xs uppercase tracking-wider text-muted-foreground">
                    <th className="px-5 py-3 font-medium">Reference</th>
                    <th className="px-5 py-3 font-medium">Status</th>
                    <th className="px-5 py-3 font-medium">Locale</th>
                    <th className="px-5 py-3 font-medium">Created</th>
                    <th className="px-5 py-3 font-medium text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((c) => {
                    const sc = statusConfig[c.status] ?? { tone: "default" as const };
                    return (
                      <tr key={c.id} className="border-b last:border-0">
                        <td className="px-5 py-3 font-mono text-sm font-semibold">
                          {c.reference ?? `#${c.id}`}
                        </td>
                        <td className="px-5 py-3">
                          <Badge tone={sc.tone}>{c.status}</Badge>
                        </td>
                        <td className="px-5 py-3 text-muted-foreground">{c.locale ?? "—"}</td>
                        <td className="px-5 py-3 text-muted-foreground">
                          {c.created_at ? new Date(c.created_at).toLocaleDateString() : "—"}
                        </td>
                        <td className="px-5 py-3 text-right">
                          <button className="inline-flex items-center gap-1 text-xs text-primary hover:underline">
                            View <ExternalLink className="size-3" />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
