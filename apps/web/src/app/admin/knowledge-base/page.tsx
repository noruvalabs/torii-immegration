"use client";

import { useCallback, useEffect, useState } from "react";
import { BookOpen, Plus, Trash2, ExternalLink } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";

type KnowledgeItem = {
  id: number;
  title: string;
  source_url: string;
  source_type: string;
  jurisdiction_code: string;
  status: string;
  retrieved_at: string;
};

export default function KnowledgeBasePage() {
  const { token } = useAuth();
  const [items, setItems] = useState<KnowledgeItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [title, setTitle] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [sourceType, setSourceType] = useState("government_page");
  const [jurisdictionCode, setJurisdictionCode] = useState("");

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      // Knowledge base CRUD not yet in API — show empty state with intent
      setItems([]);
    } catch {
      setError("Could not load knowledge base.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { void load(); }, [load]);

  const sourceTypes = [
    { value: "government_page", label: "Government page" },
    { value: "form_instructions", label: "Form instructions" },
    { value: "regulation", label: "Regulation / statute" },
    { value: "policy_guideline", label: "Policy guideline" },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-4">
        <div className="flex size-11 items-center justify-center rounded-[var(--radius)] bg-accent text-accent-foreground">
          <BookOpen className="size-5" />
        </div>
        <div className="flex-1">
          <h2 className="text-xl font-semibold tracking-tight">Knowledge base</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            The curated corpus of official government sources the platform cites from. Every
            instruction, checklist item, and eligibility rule traces back here (US-11, US-25, US-26).
          </p>
        </div>
        <Button onClick={() => setShowAdd(!showAdd)}>
          <Plus className="size-4" /> Add source
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
                // TODO: POST to knowledge base API when available
                setShowAdd(false);
                setTitle("");
                setSourceUrl("");
                setJurisdictionCode("");
              }}
              className="space-y-3"
            >
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="flex flex-col gap-1 text-sm">
                  <span className="text-muted-foreground">Title</span>
                  <input
                    required
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="Immigration Control Act Art. 7-1-2"
                    className="h-9 rounded-[var(--radius)] border bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  />
                </label>
                <label className="flex flex-col gap-1 text-sm">
                  <span className="text-muted-foreground">Jurisdiction code</span>
                  <input
                    required
                    value={jurisdictionCode}
                    onChange={(e) => setJurisdictionCode(e.target.value)}
                    placeholder="JP"
                    maxLength={8}
                    className="h-9 rounded-[var(--radius)] border bg-background px-3 text-sm uppercase outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  />
                </label>
              </div>
              <label className="flex flex-col gap-1 text-sm">
                <span className="text-muted-foreground">Source URL</span>
                <input
                  required
                  type="url"
                  value={sourceUrl}
                  onChange={(e) => setSourceUrl(e.target.value)}
                  placeholder="https://www.moj.go.jp/…"
                  className="h-9 rounded-[var(--radius)] border bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                />
              </label>
              <label className="flex flex-col gap-1 text-sm">
                <span className="text-muted-foreground">Source type</span>
                <select
                  value={sourceType}
                  onChange={(e) => setSourceType(e.target.value)}
                  className="h-9 rounded-[var(--radius)] border bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {sourceTypes.map((st) => (
                    <option key={st.value} value={st.value}>{st.label}</option>
                  ))}
                </select>
              </label>
              <div className="flex gap-2">
                <Button type="submit">Save source</Button>
                <Button variant="ghost" onClick={() => setShowAdd(false)}>
                  Cancel
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading knowledge base…</p>
      ) : items.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center">
            <BookOpen className="mx-auto mb-3 size-8 text-muted-foreground/50" />
            <p className="text-sm font-medium">No sources yet</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Add official government sources to back the platform&apos;s instructions and citations.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <Card key={item.id}>
              <CardContent className="flex items-start gap-4 pt-5">
                <BookOpen className="mt-1 size-4 shrink-0 text-muted-foreground" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium">{item.title}</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {item.jurisdiction_code} · {item.source_type.replace(/_/g, " ")}
                  </p>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    Retrieved: {item.retrieved_at}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge tone={item.status === "live" ? "success" : "muted"}>
                    {item.status}
                  </Badge>
                  <a
                    href={item.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-muted-foreground hover:text-foreground"
                  >
                    <ExternalLink className="size-3.5" />
                  </a>
                  <button className="text-muted-foreground hover:text-[var(--color-danger)]">
                    <Trash2 className="size-3.5" />
                  </button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
