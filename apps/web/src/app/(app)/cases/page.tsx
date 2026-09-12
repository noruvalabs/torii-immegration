"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Plus,
  ArrowRight,
  FolderKanban,
  Trash2,
  Search,
  LayoutList,
  Table as TableIcon,
  Archive,
  ArchiveRestore,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
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
import { formatScopeLabel } from "@/lib/utils";
import type { Case } from "@/lib/api/cases";
import {
  useCasesListQuery,
  useDeleteCaseMutation,
  useArchiveCaseMutation,
  useUnarchiveCaseMutation,
} from "@/lib/queries/cases";

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
  const { data: cases = [], isLoading } = useCasesListQuery(token);
  const deleteMutation = useDeleteCaseMutation(token);
  const archiveMutation = useArchiveCaseMutation(token);
  const unarchiveMutation = useUnarchiveCaseMutation(token);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [actionInProgressId, setActionInProgressId] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [viewMode, setViewMode] = useState<"table" | "cards">("table");
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const loading = isLoading && cases.length === 0;

  // Reset pagination on search/filter changes
  useEffect(() => {
    setCurrentPage(1);
  }, [search, filterStatus]);

  const handleDelete = useCallback(
    async (caseId: number) => {
      if (!token) return;
      const ok = window.confirm("Delete this case? This cannot be undone.");
      if (!ok) return;
      setDeletingId(caseId);
      try {
        await deleteMutation.mutateAsync(caseId);
      } catch {
        // Ignore; keep UX simple for now.
      } finally {
        setDeletingId(null);
      }
    },
    [token, deleteMutation],
  );

  const handleArchive = useCallback(
    async (caseId: number) => {
      if (!token) return;
      const ok = window.confirm(
        "Archive this case? It will be hidden from your active view, but can be restored anytime under the 'Archived' filter.",
      );
      if (!ok) return;
      setActionInProgressId(caseId);
      try {
        await archiveMutation.mutateAsync(caseId);
      } catch {
        // Ignore; keep UX simple for now.
      } finally {
        setActionInProgressId(null);
      }
    },
    [token, archiveMutation],
  );

  const handleUnarchive = useCallback(
    async (caseId: number) => {
      if (!token) return;
      setActionInProgressId(caseId);
      try {
        await unarchiveMutation.mutateAsync(caseId);
      } catch {
        // Ignore; keep UX simple for now.
      } finally {
        setActionInProgressId(null);
      }
    },
    [token, unarchiveMutation],
  );

  const filteredCases = useMemo(() => {
    return cases.filter((c) => {
      if (filterStatus === "archived") {
        if (!c.is_archived) return false;
      } else {
        if (c.is_archived) return false;
        if (filterStatus && c.status !== filterStatus) return false;
      }
      if (search) {
        const q = search.toLowerCase();
        const refMatch = c.reference?.toLowerCase().includes(q);
        const scopeMatch = c.scope_label?.toLowerCase().includes(q);
        const localeMatch = c.locale?.toLowerCase().includes(q);
        if (!refMatch && !scopeMatch && !localeMatch) return false;
      }
      return true;
    });
  }, [cases, filterStatus, search]);

  const totalPages = Math.ceil(filteredCases.length / pageSize) || 1;
  const paginatedCases = useMemo(() => {
    const startIndex = (currentPage - 1) * pageSize;
    return filteredCases.slice(startIndex, startIndex + pageSize);
  }, [filteredCases, currentPage, pageSize]);

  return (
    <div className="w-full max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Your Cases</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Track and manage your active visa and immigration applications.
          </p>
        </div>
        <Link
          href="/scope"
          className="inline-flex items-center gap-2 rounded-[var(--radius)] bg-primary px-3.5 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 shadow-xs"
        >
          <Plus className="size-4" /> New case
        </Link>
      </div>

      {/* Filter and View Mode Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3 flex-1">
          <div className="relative flex-1 sm:max-w-xs">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search reference or route…"
              className="h-9 w-full rounded-[var(--radius)] border bg-background pl-9 pr-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
          </div>

          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="h-9 rounded-[var(--radius)] border bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <option value="">All active cases</option>
            <option value="draft">Draft</option>
            <option value="intake_complete">Intake complete</option>
            <option value="checklist_ready">Checklist ready</option>
            <option value="forms_generated">Forms generated</option>
            <option value="packet_ready">Packet ready</option>
            <option value="submitted">Submitted</option>
            <option value="archived">Archived</option>
          </select>
        </div>

        {/* View Switcher */}
        <div className="flex items-center rounded-[var(--radius)] border bg-muted/40 p-0.5">
          <button
            type="button"
            onClick={() => setViewMode("table")}
            aria-label="Table view"
            className={`inline-flex items-center gap-1.5 rounded-[calc(var(--radius)-2px)] px-2.5 py-1 text-xs font-medium transition-colors ${
              viewMode === "table"
                ? "bg-background text-foreground shadow-xs font-semibold"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <TableIcon className="size-3.5" /> Table
          </button>
          <button
            type="button"
            onClick={() => setViewMode("cards")}
            aria-label="Cards view"
            className={`inline-flex items-center gap-1.5 rounded-[calc(var(--radius)-2px)] px-2.5 py-1 text-xs font-medium transition-colors ${
              viewMode === "cards"
                ? "bg-background text-foreground shadow-xs font-semibold"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <LayoutList className="size-3.5" /> Cards
          </button>
        </div>
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : filteredCases.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center py-12 text-center">
            <FolderKanban className="mb-3 size-10 text-muted-foreground/50" />
            <p className="text-sm text-muted-foreground">
              {cases.length === 0
                ? "No cases yet. Start one to begin."
                : "No cases match your filters."}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {viewMode === "table" ? (
            <Card>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="px-5">Application / Reference</TableHead>
                      <TableHead className="px-5">Next Step</TableHead>
                      <TableHead className="px-5">Status</TableHead>
                      <TableHead className="px-5">Created</TableHead>
                      <TableHead className="px-5 text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {paginatedCases.map((c) => {
                      const sc = statusConfig[c.status] ?? {
                        label: c.status,
                        tone: "default" as const,
                      };
                      return (
                        <TableRow key={c.id}>
                          <TableCell className="px-5">
                            <Link
                              href={`/cases/${c.id}`}
                              className="font-semibold text-sm hover:underline text-foreground block truncate"
                            >
                              {formatScopeLabel(c.scope_label) || c.reference}
                            </Link>
                            <span className="font-mono text-xs text-muted-foreground">
                              {c.reference}
                            </span>
                          </TableCell>
                          <TableCell className="px-5">
                            {c.next_title ? (
                              <p className="text-xs text-muted-foreground">
                                Next: {c.next_title}
                              </p>
                            ) : (
                              <p className="text-xs text-muted-foreground">
                                {c.locale.toUpperCase()}
                              </p>
                            )}
                          </TableCell>
                          <TableCell className="px-5">
                            <div className="flex items-center gap-1.5 flex-wrap">
                              <Badge tone={sc.tone} className="text-[10px] sm:text-xs">
                                {sc.label}
                              </Badge>
                              {c.is_archived && (
                                <Badge tone="muted" className="text-[10px] sm:text-xs">
                                  Archived
                                </Badge>
                              )}
                            </div>
                          </TableCell>
                          <TableCell className="px-5 text-xs text-muted-foreground">
                            {c.created_at
                              ? new Date(c.created_at).toLocaleDateString()
                              : "—"}
                          </TableCell>
                          <TableCell className="px-5 text-right">
                            <div className="flex items-center justify-end gap-2">
                              {c.is_archived ? (
                                <button
                                  type="button"
                                  onClick={() => void handleUnarchive(c.id)}
                                  disabled={actionInProgressId === c.id}
                                  className="inline-flex items-center gap-1 rounded-[var(--radius)] border border-border px-2 py-1 text-xs font-medium text-foreground hover:bg-accent disabled:opacity-50"
                                  title="Restore case to active list"
                                  aria-label={`Restore case ${c.reference}`}
                                >
                                  <ArchiveRestore className="size-3.5" />
                                  <span className="hidden sm:inline">Restore</span>
                                </button>
                              ) : c.status === "submitted" ? (
                                <button
                                  type="button"
                                  onClick={() => void handleArchive(c.id)}
                                  disabled={actionInProgressId === c.id}
                                  className="inline-flex items-center gap-1 rounded-[var(--radius)] border border-muted-foreground/30 px-2 py-1 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-50"
                                  title="Archive case (removes from active list)"
                                  aria-label={`Archive case ${c.reference}`}
                                >
                                  <Archive className="size-3.5" />
                                  <span className="hidden sm:inline">Archive</span>
                                </button>
                              ) : (
                                <button
                                  type="button"
                                  onClick={() => void handleDelete(c.id)}
                                  disabled={deletingId === c.id}
                                  className="inline-flex items-center gap-1 rounded-[var(--radius)] border border-[var(--color-danger)]/30 px-2 py-1 text-xs font-medium text-[var(--color-danger)] hover:bg-[var(--color-danger)]/10 disabled:opacity-50"
                                  aria-label={`Delete case ${c.reference}`}
                                >
                                  <Trash2 className="size-3.5" />
                                  <span className="hidden sm:inline">Delete</span>
                                </button>
                              )}
                              <Link
                                href={`/cases/${c.id}`}
                                className="inline-flex items-center gap-1 rounded-[var(--radius)] bg-primary/10 px-2.5 py-1 text-xs font-semibold text-primary hover:bg-primary/20"
                                aria-label={`Open case ${c.reference}`}
                              >
                                <span>Open</span>
                                <ArrowRight className="size-3.5" />
                              </Link>
                            </div>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          ) : (
            /* Cards View */
            <div className="space-y-3">
              {paginatedCases.map((c) => {
                const sc = statusConfig[c.status] ?? {
                  label: c.status,
                  tone: "default" as const,
                };
                return (
                  <Card key={c.id} className="transition-colors hover:bg-accent/50">
                    <CardContent className="flex items-center gap-3 sm:gap-4 p-4 sm:pt-5">
                      <div className="flex size-9 sm:size-10 shrink-0 items-center justify-center rounded-[var(--radius)] bg-accent">
                        <FolderKanban className="size-4 sm:size-5 text-muted-foreground" />
                      </div>

                      <Link href={`/cases/${c.id}`} className="min-w-0 flex-1">
                        <p className="text-sm font-semibold truncate text-foreground">
                          {formatScopeLabel(c.scope_label) || c.reference}
                        </p>
                        <p className="mt-0.5 text-xs text-muted-foreground truncate">
                          <span className="font-mono font-medium">{c.reference}</span>
                          {c.next_title ? ` · Next: ${c.next_title}` : ""}
                        </p>
                      </Link>

                      <div className="flex items-center gap-1.5 shrink-0 flex-wrap">
                        <Badge tone={sc.tone} className="shrink-0 text-[10px] sm:text-xs">
                          {sc.label}
                        </Badge>
                        {c.is_archived && (
                          <Badge tone="muted" className="shrink-0 text-[10px] sm:text-xs">
                            Archived
                          </Badge>
                        )}
                      </div>

                      <div className="flex items-center gap-1.5 shrink-0">
                        {c.is_archived ? (
                          <button
                            type="button"
                            onClick={() => void handleUnarchive(c.id)}
                            disabled={actionInProgressId === c.id}
                            className="inline-flex items-center gap-1 rounded-[var(--radius)] border border-border px-2 py-1 text-xs font-medium text-foreground hover:bg-accent disabled:opacity-50"
                            title="Restore case to active list"
                            aria-label={`Restore case ${c.reference}`}
                          >
                            <ArchiveRestore className="size-3.5" />
                            <span className="hidden sm:inline">Restore</span>
                          </button>
                        ) : c.status === "submitted" ? (
                          <button
                            type="button"
                            onClick={() => void handleArchive(c.id)}
                            disabled={actionInProgressId === c.id}
                            className="inline-flex items-center gap-1 rounded-[var(--radius)] border border-muted-foreground/30 px-2 py-1 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-50"
                            title="Archive case (removes from active list)"
                            aria-label={`Archive case ${c.reference}`}
                          >
                            <Archive className="size-3.5" />
                            <span className="hidden sm:inline">Archive</span>
                          </button>
                        ) : (
                          <button
                            type="button"
                            onClick={() => void handleDelete(c.id)}
                            disabled={deletingId === c.id}
                            className="inline-flex items-center gap-1 rounded-[var(--radius)] border border-[var(--color-danger)]/30 px-2 py-1 text-xs font-medium text-[var(--color-danger)] hover:bg-[var(--color-danger)]/10 disabled:opacity-50 shrink-0"
                            aria-label={`Delete case ${c.reference}`}
                          >
                            <Trash2 className="size-3.5" />
                            <span className="hidden sm:inline">Delete</span>
                          </button>
                        )}

                        <Link
                          href={`/cases/${c.id}`}
                          aria-label={`Open case ${c.reference}`}
                          className="shrink-0 p-1"
                        >
                          <ArrowRight className="size-4 text-muted-foreground" />
                        </Link>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}

          {/* Pagination Controls */}
          <PaginationBar
            currentPage={currentPage}
            totalPages={totalPages}
            totalItems={filteredCases.length}
            pageSize={pageSize}
            onPageChange={setCurrentPage}
            onPageSizeChange={(size) => {
              setPageSize(size);
              setCurrentPage(1);
            }}
            itemName="cases"
          />
        </div>
      )}
    </div>
  );
}

