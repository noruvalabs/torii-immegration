"use client";

import { useCallback, useEffect, useState } from "react";
import { ChevronDown, ChevronRight, Globe, Plus, Trash2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";

type Jurisdiction = { id: number; code: string; name: string; is_live: boolean };
type Category = { id: number; jurisdiction_id: number; code: string; name: string; is_live: boolean };

const API = "/backend/v1/jurisdictions";

export default function JurisdictionsPage() {
  const { token } = useAuth();
  const [items, setItems] = useState<Jurisdiction[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [isLive, setIsLive] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const hdrs = useCallback((): Record<string, string> => {
    const h: Record<string, string> = { "content-type": "application/json" };
    if (token) h.Authorization = `Bearer ${token}`;
    return h;
  }, [token]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(API, { cache: "no-store", headers: hdrs() });
      if (!res.ok) throw new Error(`API returned ${res.status}`);
      setItems(await res.json());
    } catch {
      setError("Could not reach the API. Is torii-api running on :8000?");
    } finally {
      setLoading(false);
    }
  }, [hdrs]);

  useEffect(() => {
    void load();
  }, [load]);

  async function create() {
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch(API, {
        method: "POST",
        headers: hdrs(),
        body: JSON.stringify({ code, name, is_live: isLive }),
      });
      if (res.status === 409) {
        setError(`Jurisdiction '${code.toUpperCase()}' already exists.`);
        return;
      }
      if (!res.ok) throw new Error(`API returned ${res.status}`);
      setCode("");
      setName("");
      setIsLive(false);
      await load();
    } catch {
      setError("Create failed — check the API is running.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="flex items-start gap-4">
        <div className="flex size-11 items-center justify-center rounded-[var(--radius)] bg-accent text-accent-foreground">
          <Globe className="size-5" />
        </div>
        <div>
          <h2 className="text-xl font-semibold tracking-tight">Jurisdictions</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Configure countries, visa categories, and case actions. Only{" "}
            <strong>live</strong> items are offered to applicants (US-01, US-29).
          </p>
        </div>
      </div>

      <Card>
        <CardContent className="pt-5">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void create();
            }}
            className="flex flex-wrap items-end gap-3"
          >
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-muted-foreground">Code</span>
              <input
                required
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="JP"
                maxLength={8}
                className="h-9 w-24 rounded-[var(--radius)] border bg-background px-3 uppercase outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
            </label>
            <label className="flex flex-1 flex-col gap-1 text-sm">
              <span className="text-muted-foreground">Name</span>
              <input
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Japan"
                className="h-9 min-w-40 rounded-[var(--radius)] border bg-background px-3 outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
            </label>
            <label className="flex h-9 items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={isLive}
                onChange={(e) => setIsLive(e.target.checked)}
                className="size-4"
              />
              Live
            </label>
            <Button type="submit" disabled={submitting}>
              <Plus className="size-4" />
              {submitting ? "Adding…" : "Add"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {error && (
        <p className="rounded-[var(--radius)] border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/10 px-4 py-3 text-sm text-[var(--color-danger)]">
          {error}
        </p>
      )}

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No jurisdictions yet. Add one above (try Japan — the beachhead market).
        </p>
      ) : (
        <div className="space-y-3">
          {items.map((j) => (
            <JurisdictionRow
              key={j.id}
              jurisdiction={j}
              hdrs={hdrs()}
              onError={setError}
              onReload={load}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Expandable jurisdiction row ─────────────────────────────────────────── */

function JurisdictionRow({
  jurisdiction: j,
  hdrs,
  onError,
  onReload,
}: {
  jurisdiction: Jurisdiction;
  hdrs: Record<string, string>;
  onError: (msg: string | null) => void;
  onReload: () => Promise<void>;
}) {
  const [expanded, setExpanded] = useState(false);
  const [categories, setCategories] = useState<Category[]>([]);
  const [actions, setActions] = useState<Category[]>([]);
  const [catCode, setCatCode] = useState("");
  const [catName, setCatName] = useState("");
  const [actCode, setActCode] = useState("");
  const [actName, setActName] = useState("");

  const loadSub = useCallback(async () => {
    try {
      const [catRes, actRes] = await Promise.all([
        fetch(`${API}/${j.id}/visa-categories`, { cache: "no-store", headers: hdrs }),
        fetch(`${API}/${j.id}/case-actions`, { cache: "no-store", headers: hdrs }),
      ]);
      if (catRes.ok) setCategories(await catRes.json());
      if (actRes.ok) setActions(await actRes.json());
    } catch {
      /* silent */
    }
  }, [j.id, hdrs]);

  useEffect(() => {
    if (expanded) void loadSub();
  }, [expanded, loadSub]);

  async function toggleLive(field: "is_live", value: boolean) {
    onError(null);
    try {
      const res = await fetch(`${API}/${j.id}`, {
        method: "PATCH",
        headers: hdrs,
        body: JSON.stringify({ [field]: value }),
      });
      if (!res.ok) throw new Error(`API returned ${res.status}`);
      await onReload();
    } catch (e) {
      onError(e instanceof Error ? e.message : "Update failed");
    }
  }

  async function addCategory(e: React.FormEvent) {
    e.preventDefault();
    onError(null);
    try {
      const res = await fetch(`${API}/${j.id}/visa-categories`, {
        method: "POST",
        headers: hdrs,
        body: JSON.stringify({ code: catCode, name: catName, is_live: true }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `API returned ${res.status}`);
      }
      setCatCode("");
      setCatName("");
      await loadSub();
    } catch (e) {
      onError(e instanceof Error ? e.message : "Add failed");
    }
  }

  async function addAction(e: React.FormEvent) {
    e.preventDefault();
    onError(null);
    try {
      const res = await fetch(`${API}/${j.id}/case-actions`, {
        method: "POST",
        headers: hdrs,
        body: JSON.stringify({ code: actCode, name: actName, is_live: true }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `API returned ${res.status}`);
      }
      setActCode("");
      setActName("");
      await loadSub();
    } catch (e) {
      onError(e instanceof Error ? e.message : "Add failed");
    }
  }

  async function deleteCategory(id: number) {
    onError(null);
    try {
      const res = await fetch(`${API}/${j.id}/visa-categories/${id}`, {
        method: "DELETE",
        headers: hdrs,
      });
      if (!res.ok && res.status !== 204) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `API returned ${res.status}`);
      }
      await loadSub();
    } catch (e) {
      onError(e instanceof Error ? e.message : "Delete failed");
    }
  }

  async function deleteAction(id: number) {
    onError(null);
    try {
      const res = await fetch(`${API}/${j.id}/case-actions/${id}`, {
        method: "DELETE",
        headers: hdrs,
      });
      if (!res.ok && res.status !== 204) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `API returned ${res.status}`);
      }
      await loadSub();
    } catch (e) {
      onError(e instanceof Error ? e.message : "Delete failed");
    }
  }

  async function toggleCatLive(id: number, live: boolean) {
    onError(null);
    await fetch(`${API}/${j.id}/visa-categories/${id}`, {
      method: "PATCH",
      headers: hdrs,
      body: JSON.stringify({ is_live: live }),
    });
    await loadSub();
  }

  async function toggleActLive(id: number, live: boolean) {
    onError(null);
    await fetch(`${API}/${j.id}/case-actions/${id}`, {
      method: "PATCH",
      headers: hdrs,
      body: JSON.stringify({ is_live: live }),
    });
    await loadSub();
  }

  return (
    <Card>
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-3 px-5 py-4 text-left transition-colors hover:bg-accent/50"
      >
        {expanded ? (
          <ChevronDown className="size-4 shrink-0 text-muted-foreground" />
        ) : (
          <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
        )}
        <span className="font-mono text-sm font-semibold">{j.code}</span>
        <span className="flex-1 text-sm">{j.name}</span>
        <Badge tone={j.is_live ? "success" : "muted"}>
          {j.is_live ? "live" : "draft"}
        </Badge>
      </button>

      {expanded && (
        <div className="border-t px-5 py-4 space-y-5">
          {/* Toggle live */}
          <div className="flex items-center gap-4 text-sm">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={j.is_live}
                onChange={(e) => void toggleLive("is_live", e.target.checked)}
                className="size-4"
              />
              Live (visible to applicants)
            </label>
          </div>

          {/* Visa categories */}
          <div>
            <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Visa categories
            </h4>
            {categories.length > 0 ? (
              <div className="mb-2 space-y-1">
                {categories.map((c) => (
                  <div key={c.id} className="flex items-center gap-2 text-sm">
                    <span className="font-mono">{c.code}</span>
                    <span className="flex-1">{c.name}</span>
                    <Badge tone={c.is_live ? "success" : "muted"}>
                      {c.is_live ? "live" : "draft"}
                    </Badge>
                    <button
                      onClick={() => void toggleCatLive(c.id, !c.is_live)}
                      className="text-xs text-muted-foreground hover:underline"
                    >
                      {c.is_live ? "unpublish" : "publish"}
                    </button>
                    <button
                      onClick={() => void deleteCategory(c.id)}
                      className="text-muted-foreground hover:text-[var(--color-danger)]"
                    >
                      <Trash2 className="size-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mb-2 text-xs text-muted-foreground">None configured.</p>
            )}
            <form onSubmit={(e) => void addCategory(e)} className="flex items-end gap-2">
              <input
                required
                value={catCode}
                onChange={(e) => setCatCode(e.target.value)}
                placeholder="code"
                maxLength={32}
                className="h-8 w-24 rounded-[var(--radius)] border bg-background px-2 text-xs font-mono outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
              <input
                required
                value={catName}
                onChange={(e) => setCatName(e.target.value)}
                placeholder="Work Visa"
                className="h-8 flex-1 rounded-[var(--radius)] border bg-background px-2 text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
              <button
                type="submit"
                className="inline-flex h-8 items-center gap-1 rounded-[var(--radius)] bg-primary px-3 text-xs font-medium text-primary-foreground hover:opacity-90"
              >
                <Plus className="size-3" /> Add
              </button>
            </form>
          </div>

          {/* Case actions */}
          <div>
            <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Case actions
            </h4>
            {actions.length > 0 ? (
              <div className="mb-2 space-y-1">
                {actions.map((a) => (
                  <div key={a.id} className="flex items-center gap-2 text-sm">
                    <span className="font-mono">{a.code}</span>
                    <span className="flex-1">{a.name}</span>
                    <Badge tone={a.is_live ? "success" : "muted"}>
                      {a.is_live ? "live" : "draft"}
                    </Badge>
                    <button
                      onClick={() => void toggleActLive(a.id, !a.is_live)}
                      className="text-xs text-muted-foreground hover:underline"
                    >
                      {a.is_live ? "unpublish" : "publish"}
                    </button>
                    <button
                      onClick={() => void deleteAction(a.id)}
                      className="text-muted-foreground hover:text-[var(--color-danger)]"
                    >
                      <Trash2 className="size-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mb-2 text-xs text-muted-foreground">None configured.</p>
            )}
            <form onSubmit={(e) => void addAction(e)} className="flex items-end gap-2">
              <input
                required
                value={actCode}
                onChange={(e) => setActCode(e.target.value)}
                placeholder="code"
                maxLength={32}
                className="h-8 w-24 rounded-[var(--radius)] border bg-background px-2 text-xs font-mono outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
              <input
                required
                value={actName}
                onChange={(e) => setActName(e.target.value)}
                placeholder="Renewal"
                className="h-8 flex-1 rounded-[var(--radius)] border bg-background px-2 text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
              <button
                type="submit"
                className="inline-flex h-8 items-center gap-1 rounded-[var(--radius)] bg-primary px-3 text-xs font-medium text-primary-foreground hover:opacity-90"
              >
                <Plus className="size-3" /> Add
              </button>
            </form>
          </div>
        </div>
      )}
    </Card>
  );
}
