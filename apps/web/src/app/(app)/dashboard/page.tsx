"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Plus, ArrowRight, FolderKanban, Clock, CheckCircle2, AlertCircle, User } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/lib/auth-context";
import { listCases, type Case } from "@/lib/api/cases";

const statusConfig: Record<string, { label: string; tone: "default" | "success" | "warning" | "danger" | "muted" }> = {
  draft: { label: "Draft", tone: "muted" },
  intake_complete: { label: "Intake complete", tone: "default" },
  checklist_ready: { label: "Checklist ready", tone: "default" },
  forms_generated: { label: "Forms generated", tone: "default" },
  packet_ready: { label: "Packet ready", tone: "success" },
  submitted: { label: "Submitted", tone: "success" },
};

export default function DashboardPage() {
  const { token, user } = useAuth();
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      setCases(await listCases(token));
    } catch {
      setError("Could not load your cases.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { void load(); }, [load]);

  const active = cases.filter((c) => !["submitted", "packet_ready"].includes(c.status));
  const completed = cases.filter((c) => ["submitted", "packet_ready"].includes(c.status));

  return (
    <div className="mx-auto max-w-4xl space-y-8">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Welcome back</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Your immigration cases, all in one place.
          </p>
        </div>
        <Link
          href="/scope"
          className="inline-flex items-center gap-2 rounded-[var(--radius)] bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:opacity-90"
        >
          <Plus className="size-4" /> New case
        </Link>
      </div>

      {user && !user.profile_complete && (
        <Card className="border-primary/20 bg-primary/5">
          <CardContent className="flex items-center gap-4 pt-5">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-full bg-primary/10">
              <User className="size-5 text-primary" />
            </div>
            <div className="flex-1">
              <p className="font-medium">Complete your profile</p>
              <p className="text-sm text-muted-foreground">
                Save your name, nationality, and passport details once — they auto-fill for every new case.
              </p>
            </div>
            <Link
              href="/profile"
              className="inline-flex items-center gap-2 rounded-[var(--radius)] bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
            >
              Complete profile <ArrowRight className="size-4" />
            </Link>
          </CardContent>
        </Card>
      )}

      {error && (
        <p className="rounded-[var(--radius)] border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/10 px-4 py-3 text-sm text-[var(--color-danger)]">
          {error}
        </p>
      )}

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading your cases…</p>
      ) : cases.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center py-12 text-center">
            <FolderKanban className="mb-3 size-10 text-muted-foreground/50" />
            <h2 className="text-lg font-semibold">No cases yet</h2>
            <p className="mt-1 max-w-sm text-sm text-muted-foreground">
              Start your first case to get a personalized checklist, auto-filled forms, and
              submission-ready packet.
            </p>
            <Link
              href="/scope"
              className="mt-5 inline-flex items-center gap-2 rounded-[var(--radius)] bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground hover:opacity-90"
            >
              Start your first case <ArrowRight className="size-4" />
            </Link>
          </CardContent>
        </Card>
      ) : (
        <>
          {active.length > 0 && (
            <section>
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                Active cases
              </h2>
              <div className="space-y-3">
                {active.map((c) => (
                  <CaseCard key={c.id} caseData={c} />
                ))}
              </div>
            </section>
          )}

          {completed.length > 0 && (
            <section>
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                Completed
              </h2>
              <div className="space-y-3">
                {completed.map((c) => (
                  <CaseCard key={c.id} caseData={c} />
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}

function CaseCard({ caseData }: { caseData: Case }) {
  const sc = statusConfig[caseData.status] ?? { label: caseData.status, tone: "default" as const };
  return (
    <Link href={`/cases/${caseData.id}`}>
      <Card className="transition-colors hover:bg-accent/50">
        <CardContent className="flex items-center gap-4 pt-5">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-[var(--radius)] bg-accent">
            <FolderKanban className="size-5 text-muted-foreground" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="font-mono text-sm font-semibold">{caseData.reference}</p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {caseData.scope_label ?? `Locale: ${caseData.locale}`}
              {caseData.next_title ? ` · Next: ${caseData.next_title}` : ""}
            </p>
          </div>
          <Badge tone={sc.tone}>{sc.label}</Badge>
          <ArrowRight className="size-4 shrink-0 text-muted-foreground" />
        </CardContent>
      </Card>
    </Link>
  );
}
