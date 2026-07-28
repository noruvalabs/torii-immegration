"use client";

import { useCallback, useEffect, useState } from "react";
import { FileText, Plus, Trash2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";

type FormTemplate = {
  id: number;
  code: string;
  version: string;
  official_title: string;
  is_live: boolean;
  jurisdiction_id: number;
  field_mappings: unknown[];
};

export default function FormsPage() {
  const { token } = useAuth();
  const [templates, setTemplates] = useState<FormTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [code, setCode] = useState("");
  const [version, setVersion] = useState("");
  const [title, setTitle] = useState("");

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      // Form template CRUD not yet exposed to admin — show empty state
      setTemplates([]);
    } catch {
      setError("Could not load form templates.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { void load(); }, [load]);

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-4">
        <div className="flex size-11 items-center justify-center rounded-[var(--radius)] bg-accent text-accent-foreground">
          <FileText className="size-5" />
        </div>
        <div className="flex-1">
          <h2 className="text-xl font-semibold tracking-tight">Forms & mappings</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Government form templates and the pre-validated intake-to-field mapping. First-class
            content owned by ops, not code — so form generation keeps pace with government
            changes (US-07, US-08, US-28).
          </p>
        </div>
        <Button onClick={() => setShowAdd(!showAdd)}>
          <Plus className="size-4" /> Add template
        </Button>
      </div>

      {error && (
        <p className="rounded-[var(--radius)] border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/10 px-4 py-3 text-sm text-[var(--color-danger)]">
          {error}
        </p>
      )}

      {showAdd && (
        <Card>
          <CardContent className="pt-5">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                setShowAdd(false);
                setCode("");
                setVersion("");
                setTitle("");
              }}
              className="space-y-3"
            >
              <div className="grid gap-3 sm:grid-cols-3">
                <label className="flex flex-col gap-1 text-sm">
                  <span className="text-muted-foreground">Form code</span>
                  <input
                    required
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                    placeholder="COE-01"
                    className="h-9 rounded-[var(--radius)] border bg-background px-3 text-sm font-mono outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  />
                </label>
                <label className="flex flex-col gap-1 text-sm">
                  <span className="text-muted-foreground">Version</span>
                  <input
                    required
                    value={version}
                    onChange={(e) => setVersion(e.target.value)}
                    placeholder="2026-01"
                    className="h-9 rounded-[var(--radius)] border bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  />
                </label>
                <label className="flex flex-col gap-1 text-sm">
                  <span className="text-muted-foreground">Official title</span>
                  <input
                    required
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="Certificate of Eligibility"
                    className="h-9 rounded-[var(--radius)] border bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  />
                </label>
              </div>
              <div className="flex gap-2">
                <Button type="submit">Save template</Button>
                <Button variant="ghost" onClick={() => setShowAdd(false)}>Cancel</Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading templates…</p>
      ) : templates.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center">
            <FileText className="mx-auto mb-3 size-8 text-muted-foreground/50" />
            <p className="text-sm font-medium">No form templates yet</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Add government form templates with version tracking and field mappings.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {templates.map((t) => (
            <Card key={t.id}>
              <CardContent className="flex items-start gap-4 pt-5">
                <FileText className="mt-1 size-4 shrink-0 text-muted-foreground" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="font-mono text-sm font-semibold">{t.code}</p>
                    <Badge tone="muted">v{t.version}</Badge>
                    <Badge tone={t.is_live ? "success" : "muted"}>
                      {t.is_live ? "live" : "draft"}
                    </Badge>
                  </div>
                  <p className="mt-1 text-sm">{t.official_title}</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {Array.isArray(t.field_mappings) ? t.field_mappings.length : 0} field mappings
                  </p>
                </div>
                <button className="text-muted-foreground hover:text-[var(--color-danger)]">
                  <Trash2 className="size-3.5" />
                </button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
