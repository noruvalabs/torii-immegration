"use client";

import { useCallback, useEffect, useState } from "react";
import { ClipboardCheck, AlertTriangle, Check, X } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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

export default function ReviewQueuePage() {
  const { token } = useAuth();
  const [items, setItems] = useState<Escalation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading queue…</p>
      ) : items.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center">
            <ClipboardCheck className="mx-auto mb-3 size-8 text-muted-foreground/50" />
            <p className="text-sm font-medium">Queue is empty</p>
            <p className="mt-1 text-xs text-muted-foreground">
              No escalations or low-confidence cases at the moment. Cases will appear here when
              the AI assistant escalates or the applicant requests professional help.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <Card key={item.id}>
              <CardContent className="flex items-start gap-4 pt-5">
                <AlertTriangle className="mt-1 size-5 shrink-0 text-[var(--color-warning)]" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="font-mono text-sm font-semibold">Case #{item.case_id}</p>
                    <Badge tone={statusTone[item.status] ?? "default"}>
                      {item.status}
                    </Badge>
                  </div>
                  <p className="mt-1 text-sm">
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
    </div>
  );
}
