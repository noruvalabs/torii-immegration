"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Plus,
  ArrowRight,
  FolderKanban,
  User,
  ShieldCheck,
  FileText,
  Globe2,
  AlertTriangle,
  CheckCircle2,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/lib/auth-context";
import type { Case } from "@/lib/api/cases";
import type { WalletDocument, WalletSummary } from "@/lib/api/wallet";
import { useCasesListQuery } from "@/lib/queries/cases";
import { useWalletQuery, useWalletSummaryQuery } from "@/lib/queries/wallet";

const statusConfig: Record<
  string,
  { label: string; tone: "default" | "success" | "warning" | "danger" | "muted" }
> = {
  draft: { label: "Draft", tone: "muted" },
  intake_complete: { label: "Intake complete", tone: "default" },
  checklist_ready: { label: "Checklist ready", tone: "default" },
  forms_generated: { label: "Forms generated", tone: "default" },
  packet_ready: { label: "Packet ready", tone: "success" },
  submitted: { label: "Submitted", tone: "success" },
};

export default function DashboardPage() {
  const { token, user } = useAuth();
  const { data: cases = [], isLoading: casesLoading } = useCasesListQuery(token);
  const { data: walletDocs = [], isLoading: walletLoading } = useWalletQuery(token);
  const { data: walletSummary = null, isLoading: summaryLoading } = useWalletSummaryQuery(token);
  const [error, setError] = useState<string | null>(null);

  const loading = (casesLoading || walletLoading || summaryLoading) && cases.length === 0;

  const activeCases = useMemo(() => {
    return cases.filter((c) => !c.is_archived && !["submitted", "packet_ready"].includes(c.status));
  }, [cases]);

  const activeDocsCount = walletDocs.filter((d) => d.status === "active").length;
  const expiringCount = walletSummary?.expiring_soon?.length ?? 0;
  const displayName = user?.username || (user?.email ? user.email.split("@")[0] : "");

  return (
    <div className="w-full max-w-6xl mx-auto space-y-6">
      {/* ── HEADER ───────────────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Welcome back{displayName ? `, ${displayName}` : ""}
          </h1>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Track your visa applications, manage documents, and prepare filing packets.
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <Link
            href="/scope"
            className="inline-flex items-center gap-1.5 rounded-[var(--radius)] bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground hover:opacity-90 shadow-xs transition-colors"
          >
            <Plus className="size-4" /> Start Application
          </Link>
        </div>
      </div>

      {/* ── PROFILE COMPLETION REMINDER BANNER ──────────────────────────────── */}
      {user && !user.profile_complete && (
        <Card className="border-primary/30 bg-primary/5">
          <CardContent className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between p-4">
            <div className="flex items-center gap-3">
              <div className="flex size-9 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
                <User className="size-4" />
              </div>
              <div>
                <p className="font-semibold text-xs text-foreground">Complete your applicant profile</p>
                <p className="text-[11px] text-muted-foreground mt-0.5">
                  Save your passport and identity details once to auto-fill every visa form and checklist.
                </p>
              </div>
            </div>
            <Link
              href="/profile"
              className="inline-flex items-center justify-center gap-1 rounded-[var(--radius)] bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground hover:opacity-90 shrink-0"
            >
              Complete Profile <ArrowRight className="size-3" />
            </Link>
          </CardContent>
        </Card>
      )}

      {error && (
        <p className="rounded-[var(--radius)] border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/10 px-4 py-3 text-xs text-[var(--color-danger)]">
          {error}
        </p>
      )}

      {/* ── 2 STREAMLINED OVERVIEW CARDS ────────────────────────────────────── */}
      <div className="grid gap-4 sm:grid-cols-2">
        {/* Overview 1: Active Cases */}
        <Link href="/cases" className="group">
          <Card className="h-full transition-all hover:border-primary/40 hover:shadow-xs">
            <CardContent className="p-4 flex items-center justify-between">
              <div>
                <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                  Active Applications
                </p>
                <p className="text-2xl font-bold text-foreground mt-1">
                  {loading ? "—" : activeCases.length}
                </p>
                <p className="text-[11px] text-muted-foreground mt-0.5 flex items-center gap-1">
                  <span>{activeCases.length === 1 ? "1 case in progress" : `${activeCases.length} cases in progress`}</span>
                  <ArrowRight className="size-3 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-primary" />
                </p>
              </div>
              <div className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <FolderKanban className="size-5" />
              </div>
            </CardContent>
          </Card>
        </Link>

        {/* Overview 2: Document Vault */}
        <Link href="/documents" className="group">
          <Card className="h-full transition-all hover:border-primary/40 hover:shadow-xs">
            <CardContent className="p-4 flex items-center justify-between">
              <div>
                <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                  Document Vault
                </p>
                <p className="text-2xl font-bold text-foreground mt-1">
                  {loading ? "—" : walletDocs.length}
                </p>
                <p className="text-[11px] text-muted-foreground mt-0.5 flex items-center gap-1">
                  {expiringCount > 0 ? (
                    <span className="text-[var(--color-warning)] font-semibold flex items-center gap-1">
                      <AlertTriangle className="size-3" /> {expiringCount} expiring soon
                    </span>
                  ) : (
                    <span>{activeDocsCount} reusable documents</span>
                  )}
                  <ArrowRight className="size-3 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-primary" />
                </p>
              </div>
              <div className="flex size-10 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-600">
                <ShieldCheck className="size-5" />
              </div>
            </CardContent>
          </Card>
        </Link>
      </div>

      {/* ── ACTIVE APPLICATIONS SECTION ─────────────────────────────────────── */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold tracking-tight text-foreground">Ongoing Applications</h2>
            <p className="text-xs text-muted-foreground">
              Continue your active visa filing packets and checklist steps.
            </p>
          </div>
          {activeCases.length > 0 && (
            <Link
              href="/cases"
              className="text-xs font-semibold text-primary hover:underline inline-flex items-center gap-1"
            >
              View all ({cases.filter((c) => !c.is_archived).length}) <ArrowRight className="size-3" />
            </Link>
          )}
        </div>

        {loading ? (
          <p className="text-xs text-muted-foreground py-4">Loading your cases…</p>
        ) : activeCases.length === 0 ? (
          <Card className="border-dashed">
            <CardContent className="flex flex-col items-center py-8 text-center">
              <div className="flex size-11 items-center justify-center rounded-full bg-muted text-muted-foreground mb-2">
                <FolderKanban className="size-5" />
              </div>
              <p className="text-sm font-semibold text-foreground">No active applications</p>
              <p className="mt-1 max-w-sm text-xs text-muted-foreground">
                Select one of the available destination countries below to start your personalized visa checklist.
              </p>
              <Link
                href="/scope"
                className="mt-3.5 inline-flex items-center gap-1.5 rounded-[var(--radius)] bg-primary px-3.5 py-1.5 text-xs font-medium text-primary-foreground hover:opacity-90 shadow-xs"
              >
                <Plus className="size-3.5" /> Start New Application
              </Link>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-2.5">
            {activeCases.slice(0, 5).map((c) => (
              <CaseCard key={c.id} caseData={c} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function CaseCard({ caseData }: { caseData: Case }) {
  const sc = statusConfig[caseData.status] ?? { label: caseData.status, tone: "default" as const };
  const countryCode = (
    caseData.jurisdiction_code ||
    (caseData.reference ? caseData.reference.split("-")[0] : null) ||
    "JP"
  ).toUpperCase();

  return (
    <Link href={`/cases/${caseData.id}`}>
      <Card className="transition-all hover:border-primary/40 hover:bg-accent/30">
        <CardContent className="flex items-center gap-3.5 p-3.5 sm:p-4">
          <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary font-bold text-xs font-mono">
            {countryCode}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-xs font-bold text-foreground">{caseData.reference}</span>
              <Badge tone={sc.tone} className="text-[10px] py-0 px-1.5">
                {sc.label}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground mt-0.5 truncate">
              {caseData.scope_label || `Destination: ${countryCode}`}
              {caseData.next_title ? ` · Next step: ${caseData.next_title}` : ""}
            </p>
          </div>
          <span className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline shrink-0">
            Continue <ArrowRight className="size-3" />
          </span>
        </CardContent>
      </Card>
    </Link>
  );
}

