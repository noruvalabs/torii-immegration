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
  Clock,
  Sparkles,
  Compass,
  AlertTriangle,
  CheckCircle2,
  Table as TableIcon,
  LayoutList,
  ExternalLink,
  Bot,
  Globe2,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { PaginationBar } from "@/components/ui/pagination";
import { useAuth } from "@/lib/auth-context";
import { listCases, type Case } from "@/lib/api/cases";
import {
  getWallet,
  getWalletSummary,
  type WalletDocument,
  type WalletSummary,
} from "@/lib/api/wallet";

const statusConfig: Record<string, { label: string; tone: "default" | "success" | "warning" | "danger" | "muted" }> = {
  draft: { label: "Draft", tone: "muted" },
  intake_complete: { label: "Intake complete", tone: "default" },
  checklist_ready: { label: "Checklist ready", tone: "default" },
  forms_generated: { label: "Forms generated", tone: "default" },
  packet_ready: { label: "Packet ready", tone: "success" },
  submitted: { label: "Submitted", tone: "success" },
};

const POPULAR_CORRIDORS = [
  {
    country: "Japan",
    flag: "🇯🇵",
    code: "JP",
    route: "Work Visa (Specialist in Humanities / Engineering)",
    description: "For engineers, consultants, interpreters, and international business specialists.",
  },
  {
    country: "Japan",
    flag: "🇯🇵",
    code: "JP",
    route: "Highly Skilled Professional (HSP)",
    description: "Fast-track permanent residency based on points for advanced researchers and specialists.",
  },
  {
    country: "Japan",
    flag: "🇯🇵",
    code: "JP",
    route: "Business Manager Visa",
    description: "For entrepreneurs founding or operating a registered company in Japan.",
  },
];

export default function DashboardPage() {
  const { token, user } = useAuth();
  const [cases, setCases] = useState<Case[]>([]);
  const [walletDocs, setWalletDocs] = useState<WalletDocument[]>([]);
  const [walletSummary, setWalletSummary] = useState<WalletSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [caseViewMode, setCaseViewMode] = useState<"table" | "cards">("cards");
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(5);

  const loadData = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const [casesRes, docsRes, summaryRes] = await Promise.allSettled([
        listCases(token),
        getWallet(token),
        getWalletSummary(token),
      ]);

      if (casesRes.status === "fulfilled") {
        setCases(casesRes.value);
      } else {
        setError("Could not load your cases.");
      }

      if (docsRes.status === "fulfilled") {
        setWalletDocs(docsRes.value || []);
      }

      if (summaryRes.status === "fulfilled") {
        setWalletSummary(summaryRes.value);
      }
    } catch {
      setError("Failed to load dashboard overview.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const activeCases = useMemo(() => {
    return cases.filter((c) => !["submitted", "packet_ready"].includes(c.status));
  }, [cases]);

  const completedCases = useMemo(() => {
    return cases.filter((c) => ["submitted", "packet_ready"].includes(c.status));
  }, [cases]);

  const totalPages = Math.ceil(activeCases.length / pageSize) || 1;
  const paginatedActiveCases = useMemo(() => {
    const startIndex = (currentPage - 1) * pageSize;
    return activeCases.slice(startIndex, startIndex + pageSize);
  }, [activeCases, currentPage, pageSize]);

  const activeDocsCount = walletDocs.filter((d) => d.status === "active").length;
  const expiringCount = walletSummary?.expiring_soon?.length ?? 0;

  return (
    <div className="w-full max-w-7xl mx-auto space-y-8">
      {/* ── HEADER ───────────────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight">
              Welcome back{user?.username ? `, ${user.username}` : user?.email ? `, ${user.email.split("@")[0]}` : ""}
            </h1>
            <Badge tone="default" className="text-[11px] font-normal">
              Applicant Hub
            </Badge>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            Track active visa cases, manage reusable documents, and check application readiness.
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <Link
            href="/documents"
            className="inline-flex items-center gap-1.5 rounded-[var(--radius)] border bg-background px-3.5 py-2 text-sm font-medium hover:bg-accent transition-colors"
          >
            <FolderKanban className="size-4 text-muted-foreground" /> Document Vault
          </Link>
          <Link
            href="/scope"
            className="inline-flex items-center gap-2 rounded-[var(--radius)] bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 shadow-xs transition-colors"
          >
            <Plus className="size-4" /> New Case
          </Link>
        </div>
      </div>

      {/* ── PROFILE COMPLETION BANNER ───────────────────────────────────────── */}
      {user && !user.profile_complete && (
        <Card className="border-primary/30 bg-primary/5">
          <CardContent className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between p-4 sm:p-5">
            <div className="flex items-center gap-3.5">
              <div className="flex size-10 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
                <User className="size-5" />
              </div>
              <div>
                <p className="font-semibold text-sm text-foreground">Complete your applicant profile</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Save your official name, nationality, and passport info once to auto-fill every visa form and checklist item.
                </p>
              </div>
            </div>
            <Link
              href="/profile"
              className="inline-flex items-center justify-center gap-1.5 rounded-[var(--radius)] bg-primary px-3.5 py-2 text-xs font-semibold text-primary-foreground hover:opacity-90 shrink-0"
            >
              Complete Profile <ArrowRight className="size-3.5" />
            </Link>
          </CardContent>
        </Card>
      )}

      {error && (
        <p className="rounded-[var(--radius)] border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/10 px-4 py-3 text-sm text-[var(--color-danger)]">
          {error}
        </p>
      )}

      {/* ── METRIC STATS CARDS ──────────────────────────────────────────────── */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Stat 1: Active Cases */}
        <Card className="transition-all hover:border-primary/30">
          <CardContent className="flex items-center justify-between p-5">
            <div>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Active Cases</p>
              <p className="text-2xl font-bold mt-1 text-foreground">
                {loading ? "—" : activeCases.length}
              </p>
              <p className="text-[11px] text-muted-foreground mt-0.5">
                {completedCases.length} completed application{completedCases.length === 1 ? "" : "s"}
              </p>
            </div>
            <div className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <FolderKanban className="size-5" />
            </div>
          </CardContent>
        </Card>

        {/* Stat 2: Document Vault */}
        <Card className="transition-all hover:border-primary/30">
          <CardContent className="flex items-center justify-between p-5">
            <div>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Vault Documents</p>
              <p className="text-2xl font-bold mt-1 text-foreground">
                {loading ? "—" : walletDocs.length}
              </p>
              <p className="text-[11px] text-muted-foreground mt-0.5">
                {activeDocsCount} reusable across cases
              </p>
            </div>
            <div className="flex size-10 items-center justify-center rounded-lg bg-[var(--color-success)]/10 text-[var(--color-success)]">
              <ShieldCheck className="size-5" />
            </div>
          </CardContent>
        </Card>

        {/* Stat 3: Next Actions & Deadlines */}
        <Card className="transition-all hover:border-primary/30">
          <CardContent className="flex items-center justify-between p-5">
            <div>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Action Items</p>
              <p className="text-2xl font-bold mt-1 text-foreground">
                {loading ? "—" : activeCases.length > 0 ? activeCases.length : 0}
              </p>
              <p className="text-[11px] text-muted-foreground mt-0.5">
                {expiringCount > 0 ? `${expiringCount} expiring document alert` : "All documents in order"}
              </p>
            </div>
            <div className={`flex size-10 items-center justify-center rounded-lg ${expiringCount > 0 ? "bg-[var(--color-warning)]/10 text-[var(--color-warning)]" : "bg-accent text-accent-foreground"}`}>
              {expiringCount > 0 ? <AlertTriangle className="size-5" /> : <Clock className="size-5" />}
            </div>
          </CardContent>
        </Card>

        {/* Stat 4: AI Copilot */}
        <Card className="transition-all hover:border-primary/30">
          <CardContent className="flex items-center justify-between p-5">
            <div>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">AI Visa Copilot</p>
              <div className="flex items-center gap-1.5 mt-1">
                <span className="flex size-2 rounded-full bg-emerald-500 animate-pulse" />
                <p className="text-sm font-bold text-foreground">Active & Ready</p>
              </div>
              <p className="text-[11px] text-muted-foreground mt-0.5">
                Immigration rules & guidelines
              </p>
            </div>
            <div className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Sparkles className="size-5" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ── QUICK ACTION TILES ───────────────────────────────────────────────── */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Link
          href="/scope"
          className="group flex flex-col justify-between rounded-[var(--radius)] border bg-card p-4 transition-all hover:border-primary/50 hover:shadow-xs"
        >
          <div className="flex items-center justify-between">
            <div className="flex size-8 items-center justify-center rounded-md bg-primary/10 text-primary">
              <Compass className="size-4" />
            </div>
            <ArrowRight className="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-primary" />
          </div>
          <div className="mt-3">
            <p className="text-sm font-semibold text-foreground">Start New Case</p>
            <p className="text-xs text-muted-foreground mt-0.5">Screen eligibility & pick visa route</p>
          </div>
        </Link>

        <Link
          href="/documents"
          className="group flex flex-col justify-between rounded-[var(--radius)] border bg-card p-4 transition-all hover:border-primary/50 hover:shadow-xs"
        >
          <div className="flex items-center justify-between">
            <div className="flex size-8 items-center justify-center rounded-md bg-emerald-500/10 text-emerald-600">
              <FileText className="size-4" />
            </div>
            <ArrowRight className="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-primary" />
          </div>
          <div className="mt-3">
            <p className="text-sm font-semibold text-foreground">Document Vault</p>
            <p className="text-xs text-muted-foreground mt-0.5">Manage passports, photos & proofs</p>
          </div>
        </Link>

        <Link
          href="/assistant"
          className="group flex flex-col justify-between rounded-[var(--radius)] border bg-card p-4 transition-all hover:border-primary/50 hover:shadow-xs"
        >
          <div className="flex items-center justify-between">
            <div className="flex size-8 items-center justify-center rounded-md bg-indigo-500/10 text-indigo-600">
              <Bot className="size-4" />
            </div>
            <ArrowRight className="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-primary" />
          </div>
          <div className="mt-3">
            <p className="text-sm font-semibold text-foreground">AI Visa Assistant</p>
            <p className="text-xs text-muted-foreground mt-0.5">Ask questions about visa laws & files</p>
          </div>
        </Link>

        <Link
          href="/profile"
          className="group flex flex-col justify-between rounded-[var(--radius)] border bg-card p-4 transition-all hover:border-primary/50 hover:shadow-xs"
        >
          <div className="flex items-center justify-between">
            <div className="flex size-8 items-center justify-center rounded-md bg-amber-500/10 text-amber-600">
              <User className="size-4" />
            </div>
            <ArrowRight className="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-primary" />
          </div>
          <div className="mt-3">
            <p className="text-sm font-semibold text-foreground">Profile & Details</p>
            <p className="text-xs text-muted-foreground mt-0.5">Manage personal & travel info</p>
          </div>
        </Link>
      </div>

      {/* ── ACTIVE CASES SECTION ────────────────────────────────────────────── */}
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold tracking-tight">Active Applications</h2>
            <p className="text-xs text-muted-foreground">
              Your ongoing visa cases with next required steps.
            </p>
          </div>

          {activeCases.length > 0 && (
            <div className="flex items-center rounded-[var(--radius)] border bg-muted/40 p-0.5">
              <button
                type="button"
                onClick={() => setCaseViewMode("cards")}
                aria-label="Cards view"
                className={`inline-flex items-center gap-1 rounded-[calc(var(--radius)-2px)] px-2.5 py-1 text-xs font-medium transition-colors ${
                  caseViewMode === "cards"
                    ? "bg-background text-foreground shadow-xs font-semibold"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <LayoutList className="size-3.5" /> Cards
              </button>
              <button
                type="button"
                onClick={() => setCaseViewMode("table")}
                aria-label="Table view"
                className={`inline-flex items-center gap-1 rounded-[calc(var(--radius)-2px)] px-2.5 py-1 text-xs font-medium transition-colors ${
                  caseViewMode === "table"
                    ? "bg-background text-foreground shadow-xs font-semibold"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <TableIcon className="size-3.5" /> Table
              </button>
            </div>
          )}
        </div>

        {loading ? (
          <p className="text-sm text-muted-foreground py-4">Loading your cases…</p>
        ) : activeCases.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center py-12 text-center">
              <FolderKanban className="mb-3 size-10 text-muted-foreground/50" />
              <h3 className="text-base font-semibold">No active cases</h3>
              <p className="mt-1 max-w-sm text-xs text-muted-foreground">
                Start your first case to get a personalized checklist, pre-filled forms, and submission packet.
              </p>
              <Link
                href="/scope"
                className="mt-4 inline-flex items-center gap-2 rounded-[var(--radius)] bg-primary px-4 py-2 text-xs font-medium text-primary-foreground hover:opacity-90 shadow-xs"
              >
                Start New Case <ArrowRight className="size-3.5" />
              </Link>
            </CardContent>
          </Card>
        ) : caseViewMode === "table" ? (
          /* Table View */
          <div className="space-y-4">
            <Card>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="px-5">Reference</TableHead>
                      <TableHead className="px-5">Destination & Route</TableHead>
                      <TableHead className="px-5">Next Task</TableHead>
                      <TableHead className="px-5">Status</TableHead>
                      <TableHead className="px-5 text-right">Action</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {paginatedActiveCases.map((c) => {
                      const sc = statusConfig[c.status] ?? {
                        label: c.status,
                        tone: "default" as const,
                      };
                      return (
                        <TableRow key={c.id}>
                          <TableCell className="px-5 font-mono text-sm font-semibold">
                            <Link href={`/cases/${c.id}`} className="hover:underline text-foreground">
                              {c.reference}
                            </Link>
                          </TableCell>
                          <TableCell className="px-5">
                            <p className="font-medium text-xs text-foreground">
                              {c.scope_label ?? c.locale.toUpperCase()}
                            </p>
                            <p className="text-[11px] text-muted-foreground">Locale: {c.locale}</p>
                          </TableCell>
                          <TableCell className="px-5 text-xs text-muted-foreground">
                            {c.next_title || "Review & prepare documents"}
                          </TableCell>
                          <TableCell className="px-5">
                            <Badge tone={sc.tone} className="text-[10px]">
                              {sc.label}
                            </Badge>
                          </TableCell>
                          <TableCell className="px-5 text-right">
                            <Link
                              href={`/cases/${c.id}`}
                              className="inline-flex items-center gap-1 rounded-[var(--radius)] bg-primary px-2.5 py-1 text-xs font-medium text-primary-foreground hover:opacity-90 shadow-xs"
                            >
                              Continue <ArrowRight className="size-3" />
                            </Link>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>

            <PaginationBar
              currentPage={currentPage}
              totalPages={totalPages}
              totalItems={activeCases.length}
              pageSize={pageSize}
              onPageChange={setCurrentPage}
              onPageSizeChange={(size) => {
                setPageSize(size);
                setCurrentPage(1);
              }}
              itemName="active cases"
            />
          </div>
        ) : (
          /* Cards View */
          <div className="space-y-4">
            <div className="space-y-3">
              {paginatedActiveCases.map((c) => (
                <CaseCard key={c.id} caseData={c} />
              ))}
            </div>

            <PaginationBar
              currentPage={currentPage}
              totalPages={totalPages}
              totalItems={activeCases.length}
              pageSize={pageSize}
              onPageChange={setCurrentPage}
              onPageSizeChange={(size) => {
                setPageSize(size);
                setCurrentPage(1);
              }}
              itemName="active cases"
            />
          </div>
        )}
      </div>

      {/* ── TWO COLUMN WIDGETS: DOCUMENT VAULT & CORRIDORS ────────────────────── */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Widget 1: Document Vault Quick Status */}
        <Card className="flex flex-col justify-between">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <div>
              <CardTitle className="text-base font-bold text-foreground">Document Vault Overview</CardTitle>
              <p className="text-xs text-muted-foreground mt-0.5">Reusable documents ready for present & future filings</p>
            </div>
            <Link
              href="/documents"
              className="text-xs font-semibold text-primary hover:underline inline-flex items-center gap-1"
            >
              View Vault <ArrowRight className="size-3" />
            </Link>
          </CardHeader>
          <CardContent className="space-y-3 pt-0">
            {expiringCount > 0 && (
              <div className="rounded-[var(--radius)] border border-[var(--color-warning)]/30 bg-[var(--color-warning)]/10 p-3 text-xs flex items-start gap-2.5">
                <AlertTriangle className="size-4 text-[var(--color-warning)] shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="font-semibold text-foreground">Action Needed: Expiring Documents</p>
                  <p className="text-muted-foreground mt-0.5">
                    {expiringCount} document{expiringCount === 1 ? "" : "s"} will expire soon. Please upload refreshed copies.
                  </p>
                </div>
              </div>
            )}

            {walletDocs.length === 0 ? (
              <div className="rounded border bg-muted/20 p-4 text-center">
                <p className="text-xs text-muted-foreground">No documents uploaded yet.</p>
                <Link
                  href="/documents"
                  className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline"
                >
                  <Plus className="size-3" /> Add Passport or Bank Statement
                </Link>
              </div>
            ) : (
              <div className="space-y-2">
                {walletDocs.slice(0, 3).map((doc) => (
                  <div
                    key={doc.id}
                    className="flex items-center justify-between rounded-lg border bg-muted/20 p-2.5 text-xs"
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <div className="flex size-7 items-center justify-center rounded bg-primary/10 text-primary shrink-0">
                        <FileText className="size-3.5" />
                      </div>
                      <div className="min-w-0">
                        <p className="font-medium text-foreground truncate">{doc.name}</p>
                        <p className="text-[11px] text-muted-foreground">{doc.doc_type} · v{doc.version}</p>
                      </div>
                    </div>
                    <Badge tone={doc.status === "active" ? "success" : "muted"} className="text-[10px]">
                      {doc.status}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Widget 2: Popular Visa Corridors & Beachhead Routes */}
        <Card className="flex flex-col justify-between">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <div>
              <CardTitle className="text-base font-bold text-foreground">Featured Visa Corridors</CardTitle>
              <p className="text-xs text-muted-foreground mt-0.5">Explore requirements & eligibility for popular destinations</p>
            </div>
            <Link
              href="/scope"
              className="text-xs font-semibold text-primary hover:underline inline-flex items-center gap-1"
            >
              Explore All <Globe2 className="size-3" />
            </Link>
          </CardHeader>
          <CardContent className="space-y-2.5 pt-0">
            {POPULAR_CORRIDORS.map((corridor, idx) => (
              <Link
                key={idx}
                href="/scope"
                className="group flex items-center justify-between rounded-lg border bg-muted/20 p-3 text-xs transition-colors hover:border-primary/40 hover:bg-muted/40"
              >
                <div className="flex items-start gap-2.5 min-w-0">
                  <span className="text-base shrink-0">{corridor.flag}</span>
                  <div className="min-w-0">
                    <p className="font-semibold text-foreground group-hover:text-primary transition-colors truncate">
                      {corridor.route}
                    </p>
                    <p className="text-[11px] text-muted-foreground line-clamp-1">{corridor.description}</p>
                  </div>
                </div>
                <ArrowRight className="size-3.5 text-muted-foreground shrink-0 transition-transform group-hover:translate-x-0.5 group-hover:text-primary" />
              </Link>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* ── COMPLETED CASES SECTION ─────────────────────────────────────────── */}
      {completedCases.length > 0 && (
        <section className="space-y-3 pt-2">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
            Completed &amp; Submitted ({completedCases.length})
          </h2>
          <div className="space-y-3">
            {completedCases.map((c) => (
              <CaseCard key={c.id} caseData={c} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function CaseCard({ caseData }: { caseData: Case }) {
  const sc = statusConfig[caseData.status] ?? { label: caseData.status, tone: "default" as const };
  return (
    <Link href={`/cases/${caseData.id}`}>
      <Card className="transition-all hover:border-primary/40 hover:bg-accent/40">
        <CardContent className="flex items-center gap-4 p-4 sm:pt-5">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-[var(--radius)] bg-accent">
            <FolderKanban className="size-5 text-muted-foreground" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="font-mono text-sm font-semibold text-foreground">{caseData.reference}</p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {caseData.scope_label ?? `Locale: ${caseData.locale}`}
              {caseData.next_title ? ` · Next: ${caseData.next_title}` : ""}
            </p>
          </div>
          <Badge tone={sc.tone} className="shrink-0 text-xs">{sc.label}</Badge>
          <ArrowRight className="size-4 shrink-0 text-muted-foreground" />
        </CardContent>
      </Card>
    </Link>
  );
}

