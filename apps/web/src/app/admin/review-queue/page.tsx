"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  ClipboardCheck,
  AlertTriangle,
  Check,
  X,
  Search,
  ExternalLink,
  LayoutList,
  Table as TableIcon,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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

type Escalation = {
  id: number;
  case_id: number;
  reason: string;
  message: string;
  status: string;
  outcome: string | null;
  created_at: string | null;
};

const API = "/backend/v1";

const reasonLabels: Record<string, string> = {
  out_of_scope: "Out of scope",
  low_confidence: "Low confidence",
  requires_legal_advice: "Requires legal advice",
  unsupported_request: "Unsupported request",
};

const statusTone: Record<string, "default" | "success" | "warning" | "danger" | "muted"> = {
  open: "warning",
  in_review: "default",
  resolved: "success",
  dismissed: "muted",
};

export default function ReviewQueuePage() {
  const { token } = useAuth();
  const [items, setItems] = useState<Escalation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [viewMode, setViewMode] = useState<"cards" | "table">("cards");
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/admin/escalations`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to load");
      const data = await res.json();
      setItems(data);
    } catch {
      setError("Could not load review queue.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { void load(); }, [load]);

  useEffect(() => {
    setCurrentPage(1);
  }, [search, filterStatus]);

  const handleAction = useCallback(async (id: number, action: "resolved" | "dismissed") => {
    if (!token) return;
    try {
      await fetch(`${API}/admin/escalations/${id}`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${token}`, "content-type": "application/json" },
        body: JSON.stringify({ status: action }),
      });
      setItems((prev) => prev.filter((e) => e.id !== id));
    } catch {
      setError("Failed to update escalation.");
    }
  }, [token]);

  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      if (filterStatus && item.status !== filterStatus) return false;
      if (search) {
        const q = search.toLowerCase();
        const caseMatch = `case #${item.case_id}`.toLowerCase().includes(q) || String(item.case_id).includes(q);
        const reasonMatch = (reasonLabels[item.reason] ?? item.reason).toLowerCase().includes(q);
        const msgMatch = item.message?.toLowerCase().includes(q);
        if (!caseMatch && !reasonMatch && !msgMatch) return false;
      }
      return true;
    });
  }, [items, filterStatus, search]);

  const totalPages = Math.ceil(filteredItems.length / pageSize) || 1;
  const paginatedItems = useMemo(() => {
    const startIndex = (currentPage - 1) * pageSize;
    return filteredItems.slice(startIndex, startIndex + pageSize);
  }, [filteredItems, currentPage, pageSize]);

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-4">
        <div className="flex size-11 items-center justify-center rounded-[var(--radius)] bg-accent text-accent-foreground">
          <ClipboardCheck className="size-5" />
        </div>
        <div>
          <h2 className="text-xl font-semibold tracking-tight">Review queue</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Escalated and low-confidence cases awaiting human review. Every case the platform
            couldn&apos;t resolve lands here (US-13, US-15, US-27).
          </p>
        </div>
      </div>

      {error && (
        <p className="rounded-[var(--radius)] border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/10 px-4 py-3 text-sm text-[var(--color-danger)]">
          {error}
        </p>
      )}

      {/* Filter and View mode bar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3 flex-1">
          <div className="relative flex-1 sm:max-w-xs">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search case # or reason…"
              className="h-9 w-full rounded-[var(--radius)] border bg-background pl-9 pr-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
          </div>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="h-9 rounded-[var(--radius)] border bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <option value="">All statuses</option>
            <option value="open">Open</option>
            <option value="in_review">In Review</option>
            <option value="resolved">Resolved</option>
            <option value="dismissed">Dismissed</option>
          </select>
        </div>

        <div className="flex items-center rounded-[var(--radius)] border bg-muted/40 p-0.5">
          <button
            type="button"
            onClick={() => setViewMode("cards")}
            aria-label="Cards view"
            className={`inline-flex items-center gap-1 rounded-[calc(var(--radius)-2px)] px-2.5 py-1 text-xs font-medium transition-colors ${
              viewMode === "cards"
                ? "bg-background text-foreground shadow-xs font-semibold"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <LayoutList className="size-3.5" /> Cards
          </button>
          <button
            type="button"
            onClick={() => setViewMode("table")}
            aria-label="Table view"
            className={`inline-flex items-center gap-1 rounded-[calc(var(--radius)-2px)] px-2.5 py-1 text-xs font-medium transition-colors ${
              viewMode === "table"
                ? "bg-background text-foreground shadow-xs font-semibold"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <TableIcon className="size-3.5" /> Table
          </button>
        </div>
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading queue…</p>
      ) : filteredItems.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center">
            <ClipboardCheck className="mx-auto mb-3 size-8 text-muted-foreground/50" />
            <p className="text-sm font-medium">Queue is empty</p>
            <p className="mt-1 text-xs text-muted-foreground">
              {items.length === 0
                ? "No escalations or low-confidence cases at the moment. Cases will appear here when the AI assistant escalates or the applicant requests professional help."
                : "No escalations match your filters."}
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
                      <TableHead className="px-5">Case</TableHead>
                      <TableHead className="px-5">Reason</TableHead>
                      <TableHead className="px-5">Details</TableHead>
                      <TableHead className="px-5">Status</TableHead>
                      <TableHead className="px-5 text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {paginatedItems.map((item) => (
                      <TableRow key={item.id}>
                        <TableCell className="px-5 font-mono text-sm font-semibold">
                          <Link
                            href={`/cases/${item.case_id}`}
                            className="inline-flex items-center gap-1 hover:underline text-foreground"
                          >
                            Case #{item.case_id}
                            <ExternalLink className="size-3 text-muted-foreground" />
                          </Link>
                        </TableCell>
                        <TableCell className="px-5 font-medium text-xs">
                          {reasonLabels[item.reason] ?? item.reason}
                        </TableCell>
                        <TableCell className="px-5 text-xs text-muted-foreground max-w-xs">
                          <p className="line-clamp-2">{item.message}</p>
                        </TableCell>
                        <TableCell className="px-5">
                          <Badge tone={statusTone[item.status] ?? "default"}>
                            {item.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="px-5 text-right">
                          {item.status === "open" ? (
                            <div className="flex items-center justify-end gap-1.5">
                              <Button
                                variant="outline"
                                onClick={() => handleAction(item.id, "resolved")}
                                className="h-7 px-2 text-xs gap-1"
                              >
                                <Check className="size-3" /> Resolve
                              </Button>
                              <Button
                                variant="ghost"
                                onClick={() => handleAction(item.id, "dismissed")}
                                className="h-7 px-2 text-xs gap-1"
                              >
                                <X className="size-3" /> Dismiss
                              </Button>
                            </div>
                          ) : (
                            <span className="text-xs text-muted-foreground capitalize">{item.status}</span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          ) : (
            /* Cards View */
            <div className="space-y-3">
              {paginatedItems.map((item) => (
                <Card key={item.id}>
                  <CardContent className="flex items-start gap-4 pt-5">
                    <AlertTriangle className="mt-1 size-5 shrink-0 text-[var(--color-warning)]" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <Link
                          href={`/cases/${item.case_id}`}
                          className="font-mono text-sm font-semibold hover:underline"
                        >
                          Case #{item.case_id}
                        </Link>
                        <Badge tone={statusTone[item.status] ?? "default"}>
                          {item.status}
                        </Badge>
                      </div>
                      <p className="mt-1 text-sm font-medium">
                        {reasonLabels[item.reason] ?? item.reason}
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground line-clamp-2">
                        {item.message}
                      </p>
                    </div>
                    {item.status === "open" && (
                      <div className="flex gap-1">
                        <Button variant="outline" onClick={() => handleAction(item.id, "resolved")}>
                          <Check className="size-3.5" /> Resolve
                        </Button>
                        <Button variant="ghost" onClick={() => handleAction(item.id, "dismissed")}>
                          <X className="size-3.5" /> Dismiss
                        </Button>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          <PaginationBar
            currentPage={currentPage}
            totalPages={totalPages}
            totalItems={filteredItems.length}
            pageSize={pageSize}
            onPageChange={setCurrentPage}
            onPageSizeChange={(size) => {
              setPageSize(size);
              setCurrentPage(1);
            }}
            itemName="escalations"
          />
        </div>
      )}
    </div>
  );
}

