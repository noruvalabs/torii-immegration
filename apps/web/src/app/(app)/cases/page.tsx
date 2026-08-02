"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Plus, ArrowRight, FolderKanban, Trash2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/lib/auth-context";
import { listCases, deleteCase, type Case } from "@/lib/api/cases";

const statusConfig: Record<string, { label: string; tone: "default" | "success" | "warning" | "danger" | "muted" }> = {
  draft: { label: "Draft", tone: "muted" },
  intake_complete: { label: "Intake complete", tone: "default" },
  checklist_ready: { label: "Checklist ready", tone: "default" },
  forms_generated: { label: "Forms generated", tone: "default" },
  packet_ready: { label: "Packet ready", tone: "success" },
  submitted: { label: "Submitted", tone: "success" },
};

export default function CasesListPage() {
  const { token } = useAuth();
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try { setCases(await listCases(token)); } catch { /* ignore */ }
    finally { setLoading(false); }
  }, [token]);

  useEffect(() => { void load(); }, [load]);

  const handleDelete = useCallback(
    async (caseId: number) => {
      if (!token) return;
      const ok = window.confirm("Delete this case? This cannot be undone.");
      if (!ok) return;
      setDeletingId(caseId);
      try {
        await deleteCase(token, caseId);
        await load();
      } catch {
        // Ignore; keep UX simple for now.
      } finally {
        setDeletingId(null);
      }
    },
    [token, load],
  );

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">My cases</h1>
        <Link
          href="/scope"
          className="inline-flex items-center gap-2 rounded-[var(--radius)] bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
        >
          <Plus className="size-4" /> New case
        </Link>
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : cases.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center py-12 text-center">
            <FolderKanban className="mb-3 size-10 text-muted-foreground/50" />
            <p className="text-sm text-muted-foreground">No cases yet. Start one to begin.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {cases.map((c) => {
            const sc = statusConfig[c.status] ?? { label: c.status, tone: "default" as const };
            return (
              <Card key={c.id} className="transition-colors hover:bg-accent/50">
                <CardContent className="flex items-center gap-4 pt-5">
                  <div className="flex size-10 shrink-0 items-center justify-center rounded-[var(--radius)] bg-accent">
                    <FolderKanban className="size-5 text-muted-foreground" />
                  </div>

                  <Link href={`/cases/${c.id}`} className="min-w-0 flex-1">
                    <p className="font-mono text-sm font-semibold">{c.reference}</p>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {c.scope_label ?? c.locale.toUpperCase()}
                      {c.next_title ? ` · Next: ${c.next_title}` : ""}
                    </p>
                  </Link>

                  <Badge tone={sc.tone}>{sc.label}</Badge>

                  {c.status !== "submitted" && (
                    <button
                      type="button"
                      onClick={() => void handleDelete(c.id)}
                      disabled={deletingId === c.id}
                      className="inline-flex items-center gap-1 rounded-[var(--radius)] border border-[var(--color-danger)]/30 px-2 py-1 text-xs font-medium text-[var(--color-danger)] hover:bg-[var(--color-danger)]/10 disabled:opacity-50"
                      aria-label={`Delete case ${c.reference}`}
                    >
                      <Trash2 className="size-3.5" />
                      Delete
                    </button>
                  )}

                  <Link href={`/cases/${c.id}`} aria-label={`Open case ${c.reference}`}>
                    <ArrowRight className="size-4 shrink-0 text-muted-foreground" />
                  </Link>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
