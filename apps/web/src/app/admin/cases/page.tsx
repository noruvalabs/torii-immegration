"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { FolderKanban, Search, ExternalLink } from "lucide-react";
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
import type { AdminCase } from "@/lib/api/cases";
import { useAdminCasesQuery } from "@/lib/queries/admin";

const statusConfig: Record<string, { label: string; tone: "default" | "success" | "warning" | "danger" | "muted" }> = {
  draft: { label: "Draft", tone: "muted" },
  intake_complete: { label: "Intake complete", tone: "default" },
  checklist_ready: { label: "Checklist ready", tone: "default" },
  forms_generated: { label: "Forms generated", tone: "default" },
  packet_ready: { label: "Packet ready", tone: "success" },
  submitted: { label: "Submitted", tone: "success" },
};

export default function CasesPage() {
  const { token } = useAuth();
  const [filter, setFilter] = useState("");
  const { data: cases = [], isLoading, isError } = useAdminCasesQuery(token, { status: filter || undefined });
  const [search, setSearch] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const loading = isLoading && cases.length === 0;
  const error = isError ? "Could not load cases." : null;

  // Reset to page 1 whenever filter or search query changes
  useEffect(() => {
    setCurrentPage(1);
  }, [filter, search]);

  const filtered = useMemo(() => {
    return cases.filter((c) => {
      if (search && c.reference && !c.reference.toLowerCase().includes(search.toLowerCase())) {
        return false;
      }
      return true;
    });
  }, [cases, search]);

  const totalPages = Math.ceil(filtered.length / pageSize) || 1;
  const paginatedCases = useMemo(() => {
    const startIndex = (currentPage - 1) * pageSize;
    return filtered.slice(startIndex, startIndex + pageSize);
  }, [filtered, currentPage, pageSize]);

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

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3 flex-1">
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
        <div className="space-y-4">
          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="px-5">Reference</TableHead>
                    <TableHead className="px-5">Status</TableHead>
                    <TableHead className="px-5">Locale</TableHead>
                    <TableHead className="px-5">Created</TableHead>
                    <TableHead className="px-5 text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {paginatedCases.map((c) => {
                    const sc = statusConfig[c.status] ?? { label: c.status, tone: "default" as const };
                    return (
                      <TableRow key={c.id}>
                        <TableCell className="px-5 font-mono text-sm font-semibold">
                          <Link
                            href={`/cases/${c.id}`}
                            className="hover:underline text-foreground"
                          >
                            {c.reference ?? `#${c.id}`}
                          </Link>
                        </TableCell>
                        <TableCell className="px-5">
                          <Badge tone={sc.tone}>{sc.label}</Badge>
                        </TableCell>
                        <TableCell className="px-5 text-muted-foreground">{c.locale ?? "—"}</TableCell>
                        <TableCell className="px-5 text-muted-foreground">
                          {c.created_at ? new Date(c.created_at).toLocaleDateString() : "—"}
                        </TableCell>
                        <TableCell className="px-5 text-right">
                          <Link
                            href={`/cases/${c.id}`}
                            className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                          >
                            View <ExternalLink className="size-3" />
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
            totalItems={filtered.length}
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

