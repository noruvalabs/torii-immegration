"use client";

import { useCallback, useEffect, useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  Globe,
  Plus,
  Trash2,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";
import { matchCountry } from "@/lib/countries";

type Jurisdiction = { id: number; code: string; name: string; is_live: boolean };
type Category = { id: number; jurisdiction_id: number; code: string; name: string; is_live: boolean };

const API = "/backend/v1/jurisdictions";

const POPULAR_PRESETS = [
  { code: "JP", name: "Japan" },
  { code: "GB", name: "United Kingdom" },
  { code: "US", name: "United States" },
  { code: "CA", name: "Canada" },
  { code: "AU", name: "Australia" },
  { code: "DE", name: "Germany" },
  { code: "SG", name: "Singapore" },
];

export default function JurisdictionsPage() {
  const { token } = useAuth();
  const [items, setItems] = useState<Jurisdiction[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [isLive, setIsLive] = useState(true);
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

  async function create(presetCode?: string, presetName?: string) {
    const targetCode = (presetCode || code).trim().toUpperCase();
    const targetName = (presetName || name).trim();
    if (!targetCode || !targetName) return;

    setSubmitting(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const res = await fetch(API, {
        method: "POST",
        headers: hdrs(),
        body: JSON.stringify({ code: targetCode, name: targetName, is_live: isLive }),
      });
      if (res.status === 409) {
        setError(`Country / Jurisdiction '${targetCode}' already exists.`);
        return;
      }
      if (!res.ok) throw new Error(`API returned ${res.status}`);
      setCode("");
      setName("");
      setIsLive(true);
      setSuccessMsg(`Added ${targetName} (${targetCode}) with default visa routes.`);
      await load();
    } catch {
      setError("Create failed — check that the API server is running.");
    } finally {
      setSubmitting(false);
    }
  }

  async function toggleJurisdictionLive(j: Jurisdiction) {
    setError(null);
    setSuccessMsg(null);
    try {
      const res = await fetch(`${API}/${j.id}`, {
        method: "PATCH",
        headers: hdrs(),
        body: JSON.stringify({ is_live: !j.is_live }),
      });
      if (!res.ok) throw new Error(`API returned ${res.status}`);
      setSuccessMsg(`${j.name} is now ${!j.is_live ? "LIVE (applicants can apply)" : "DISABLED (hidden from applicants)"}.`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Update failed");
    }
  }

  async function deleteJurisdiction(j: Jurisdiction) {
    if (!confirm(`Are you sure you want to remove ${j.name} (${j.code})?`)) return;
    setError(null);
    setSuccessMsg(null);
    try {
      const res = await fetch(`${API}/${j.id}`, {
        method: "DELETE",
        headers: hdrs(),
      });
      if (!res.ok && res.status !== 204) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Cannot delete jurisdiction with active cases.`);
      }
      setSuccessMsg(`Removed ${j.name} (${j.code}).`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    }
  }

  const liveCount = items.filter((j) => j.is_live).length;

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      {/* ── HEADER ───────────────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3.5">
          <div className="flex size-11 items-center justify-center rounded-[var(--radius)] bg-primary/10 text-primary shrink-0">
            <Globe className="size-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight">Application Countries &amp; Jurisdictions</h1>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Select which countries are active for applicant visa filings. Applicants can only apply to <strong>Live</strong> countries.
            </p>
          </div>
        </div>

        {/* Quick Stats Pill */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 rounded-lg border bg-card px-3 py-1.5 text-xs">
            <span className="flex size-2 rounded-full bg-emerald-500" />
            <span className="font-semibold text-foreground">{liveCount} Live</span>
            <span className="text-muted-foreground">/ {items.length} total</span>
          </div>
        </div>
      </div>

      {/* ── ALERT MESSAGES ──────────────────────────────────────────────────── */}
      {error && (
        <div className="flex items-center gap-2 rounded-[var(--radius)] border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/10 px-4 py-3 text-xs text-[var(--color-danger)]">
          <XCircle className="size-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}
      {successMsg && (
        <div className="flex items-center gap-2 rounded-[var(--radius)] border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-xs text-emerald-700 dark:text-emerald-300">
          <CheckCircle2 className="size-4 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* ── ADD JURISDICTION & PRESETS CARD ─────────────────────────────────── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-bold text-foreground">Add New Application Country</CardTitle>
          <p className="text-xs text-muted-foreground">
            Add a destination country and auto-provision standard visa categories (Work, Student, Tourist) and actions.
          </p>
        </CardHeader>
        <CardContent className="space-y-4 pt-0">
          {/* Quick presets */}
          <div>
            <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Quick Add Popular Countries:</span>
            <div className="mt-1.5 flex flex-wrap gap-2">
              {POPULAR_PRESETS.map((preset) => {
                const existing = items.find((i) => i.code.toUpperCase() === preset.code.toUpperCase());
                const flag = matchCountry(preset.code).flag;
                return (
                  <button
                    key={preset.code}
                    type="button"
                    disabled={Boolean(existing) || submitting}
                    onClick={() => void create(preset.code, preset.name)}
                    className={`inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium transition-all ${
                      existing
                        ? "opacity-50 cursor-not-allowed bg-muted text-muted-foreground border-transparent"
                        : "bg-background text-foreground hover:bg-accent hover:border-primary/40"
                    }`}
                  >
                    <span>{flag}</span>
                    <span>{preset.name}</span>
                    {existing ? (
                      <span className="text-[10px] text-muted-foreground">(Added)</span>
                    ) : (
                      <Plus className="size-3 text-primary" />
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Custom Form */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void create();
            }}
            className="flex flex-wrap items-end gap-3 pt-2 border-t"
          >
            <label className="flex flex-col gap-1 text-xs">
              <span className="text-muted-foreground font-medium">ISO Country Code</span>
              <input
                required
                value={code}
                onChange={(e) => {
                  const val = e.target.value.toUpperCase();
                  setCode(val);
                  if (val.length === 2 && !name) {
                    const matched = matchCountry(val);
                    if (matched && matched.name) setName(matched.name);
                  }
                }}
                placeholder="e.g. CA"
                maxLength={8}
                className="h-9 w-28 rounded-[var(--radius)] border bg-background px-3 font-mono uppercase text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
            </label>
            <label className="flex flex-1 flex-col gap-1 text-xs">
              <span className="text-muted-foreground font-medium">Country Name</span>
              <input
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Canada"
                className="h-9 min-w-44 rounded-[var(--radius)] border bg-background px-3 text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
            </label>
            <label className="flex h-9 items-center gap-2 text-xs font-medium cursor-pointer">
              <input
                type="checkbox"
                checked={isLive}
                onChange={(e) => setIsLive(e.target.checked)}
                className="size-4 rounded accent-primary"
              />
              Live for Applications
            </label>
            <Button type="submit" size="sm" disabled={submitting || !code || !name} className="gap-1.5">
              <Plus className="size-4" />
              {submitting ? "Adding…" : "Add Country"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* ── CONFIGURED COUNTRIES LIST ───────────────────────────────────────── */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold uppercase tracking-wider text-muted-foreground">
            Configured Countries ({items.length})
          </h2>
          <p className="text-xs text-muted-foreground">
            Click toggle switch to instantly enable/disable applications for that country.
          </p>
        </div>

        {loading ? (
          <p className="text-xs text-muted-foreground py-4">Loading countries…</p>
        ) : items.length === 0 ? (
          <Card>
            <CardContent className="py-8 text-center text-xs text-muted-foreground">
              No jurisdictions configured. Use the quick presets above to add Japan, UK, or US.
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {items.map((j) => (
              <JurisdictionCard
                key={j.id}
                jurisdiction={j}
                hdrs={hdrs()}
                onToggleLive={() => void toggleJurisdictionLive(j)}
                onDelete={() => void deleteJurisdiction(j)}
                onError={setError}
                onReload={load}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Individual Country Card with Quick Toggle & Expandable Settings ─────────── */

function JurisdictionCard({
  jurisdiction: j,
  hdrs,
  onToggleLive,
  onDelete,
  onError,
  onReload,
}: {
  jurisdiction: Jurisdiction;
  hdrs: Record<string, string>;
  onToggleLive: () => void;
  onDelete: () => void;
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

  const countryMeta = matchCountry(j.code);
  const flag = countryMeta.flag || "🌐";

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

  async function addCategory(e: React.FormEvent) {
    e.preventDefault();
    onError(null);
    try {
      const res = await fetch(`${API}/${j.id}/visa-categories`, {
        method: "POST",
        headers: hdrs,
        body: JSON.stringify({ code: catCode.toLowerCase(), name: catName, is_live: true }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `API returned ${res.status}`);
      }
      setCatCode("");
      setCatName("");
      await loadSub();
    } catch (e) {
      onError(e instanceof Error ? e.message : "Add category failed");
    }
  }

  async function addAction(e: React.FormEvent) {
    e.preventDefault();
    onError(null);
    try {
      const res = await fetch(`${API}/${j.id}/case-actions`, {
        method: "POST",
        headers: hdrs,
        body: JSON.stringify({ code: actCode.toLowerCase(), name: actName, is_live: true }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `API returned ${res.status}`);
      }
      setActCode("");
      setActName("");
      await loadSub();
    } catch (e) {
      onError(e instanceof Error ? e.message : "Add action failed");
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
      onError(e instanceof Error ? e.message : "Delete category failed");
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
      onError(e instanceof Error ? e.message : "Delete action failed");
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
    <Card className={`transition-all ${j.is_live ? "border-emerald-500/30" : "border-border opacity-85"}`}>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between p-4 gap-3">
        {/* Country Info & Flag */}
        <div className="flex items-center gap-3 min-w-0">
          <span className="text-2xl shrink-0">{flag}</span>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-bold text-sm text-foreground truncate">{j.name}</span>
              <span className="font-mono text-xs font-semibold px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                {j.code}
              </span>
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              {j.is_live ? "Open for applicant filings" : "Disabled / Hidden from applicants"}
            </p>
          </div>
        </div>

        {/* Action Controls: Live Switch, Manage, Delete */}
        <div className="flex items-center gap-2.5 shrink-0 self-end sm:self-auto">
          {/* Quick Toggle Live Switch */}
          <button
            type="button"
            onClick={onToggleLive}
            title={j.is_live ? "Click to disable applications" : "Click to enable applications"}
            className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold transition-all border ${
              j.is_live
                ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-300 hover:bg-emerald-500/20"
                : "bg-muted border-border text-muted-foreground hover:bg-muted/80"
            }`}
          >
            <span className={`size-2 rounded-full ${j.is_live ? "bg-emerald-500 animate-pulse" : "bg-muted-foreground"}`} />
            <span>{j.is_live ? "Live for Applications" : "Disabled"}</span>
          </button>

          {/* Expand Button for Visa Categories & Actions */}
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setExpanded(!expanded)}
            className="h-8 gap-1 text-xs"
          >
            <span>Routes &amp; Rules</span>
            {expanded ? <ChevronDown className="size-3.5" /> : <ChevronRight className="size-3.5" />}
          </Button>

          {/* Delete Button */}
          <button
            type="button"
            onClick={onDelete}
            title="Remove country"
            className="inline-flex size-8 items-center justify-center rounded-[var(--radius)] text-muted-foreground hover:bg-[var(--color-danger)]/10 hover:text-[var(--color-danger)] transition-colors"
          >
            <Trash2 className="size-4" />
          </button>
        </div>
      </div>

      {/* Expanded Accordion: Visa Categories & Case Actions */}
      {expanded && (
        <div className="border-t bg-muted/20 px-5 py-4 space-y-5">
          {/* Visa Categories */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Visa Categories for {j.name}
              </h4>
              <span className="text-[11px] text-muted-foreground">{categories.length} category routes</span>
            </div>

            {categories.length > 0 ? (
              <div className="space-y-1.5 mb-3">
                {categories.map((c) => (
                  <div
                    key={c.id}
                    className="flex items-center justify-between rounded-md border bg-card px-3 py-2 text-xs"
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-semibold text-[11px] text-muted-foreground">{c.code}</span>
                      <span className="font-medium text-foreground">{c.name}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge tone={c.is_live ? "success" : "muted"} className="text-[10px]">
                        {c.is_live ? "live" : "draft"}
                      </Badge>
                      <button
                        type="button"
                        onClick={() => void toggleCatLive(c.id, !c.is_live)}
                        className="text-[11px] text-muted-foreground hover:underline font-medium"
                      >
                        {c.is_live ? "unpublish" : "publish"}
                      </button>
                      <button
                        type="button"
                        onClick={() => void deleteCategory(c.id)}
                        className="text-muted-foreground hover:text-[var(--color-danger)] transition-colors"
                      >
                        <Trash2 className="size-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mb-3 text-xs text-muted-foreground">No specific visa categories added yet.</p>
            )}

            <form onSubmit={(e) => void addCategory(e)} className="flex items-end gap-2">
              <input
                required
                value={catCode}
                onChange={(e) => setCatCode(e.target.value)}
                placeholder="code (e.g. work)"
                maxLength={32}
                className="h-8 w-28 rounded-[var(--radius)] border bg-background px-2.5 text-xs font-mono outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
              <input
                required
                value={catName}
                onChange={(e) => setCatName(e.target.value)}
                placeholder="Route Name (e.g. Highly Skilled Professional)"
                className="h-8 flex-1 rounded-[var(--radius)] border bg-background px-2.5 text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
              <Button type="submit" size="sm" className="h-8 gap-1 text-xs">
                <Plus className="size-3" /> Add Category
              </Button>
            </form>
          </div>

          {/* Case Actions */}
          <div className="pt-3 border-t">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Application Actions for {j.name}
              </h4>
              <span className="text-[11px] text-muted-foreground">{actions.length} action types</span>
            </div>

            {actions.length > 0 ? (
              <div className="space-y-1.5 mb-3">
                {actions.map((a) => (
                  <div
                    key={a.id}
                    className="flex items-center justify-between rounded-md border bg-card px-3 py-2 text-xs"
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-semibold text-[11px] text-muted-foreground">{a.code}</span>
                      <span className="font-medium text-foreground">{a.name}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge tone={a.is_live ? "success" : "muted"} className="text-[10px]">
                        {a.is_live ? "live" : "draft"}
                      </Badge>
                      <button
                        type="button"
                        onClick={() => void toggleActLive(a.id, !a.is_live)}
                        className="text-[11px] text-muted-foreground hover:underline font-medium"
                      >
                        {a.is_live ? "unpublish" : "publish"}
                      </button>
                      <button
                        type="button"
                        onClick={() => void deleteAction(a.id)}
                        className="text-muted-foreground hover:text-[var(--color-danger)] transition-colors"
                      >
                        <Trash2 className="size-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mb-3 text-xs text-muted-foreground">No specific case actions added yet.</p>
            )}

            <form onSubmit={(e) => void addAction(e)} className="flex items-end gap-2">
              <input
                required
                value={actCode}
                onChange={(e) => setActCode(e.target.value)}
                placeholder="code (e.g. new)"
                maxLength={32}
                className="h-8 w-28 rounded-[var(--radius)] border bg-background px-2.5 text-xs font-mono outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
              <input
                required
                value={actName}
                onChange={(e) => setActName(e.target.value)}
                placeholder="Action Name (e.g. New Application / Extension)"
                className="h-8 flex-1 rounded-[var(--radius)] border bg-background px-2.5 text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
              <Button type="submit" size="sm" className="h-8 gap-1 text-xs">
                <Plus className="size-3" /> Add Action
              </Button>
            </form>
          </div>
        </div>
      )}
    </Card>
  );
}

