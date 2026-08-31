"use client";

import { type FormEvent, useCallback, useEffect, useState } from "react";
import {
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Globe,
  Loader2,
  Plus,
  Radar,
  Trash2,
  XCircle,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";
import { matchCountry } from "@/lib/countries";
import { formatErrorMessage } from "@/lib/api/errors";
import {
  type AdminJurisdiction,
  type Discovery,
  type Scope,
  type ScopeKind,
  createJurisdiction,
  createScope,
  deleteJurisdiction,
  deleteScope,
  discoverScopes,
  listJurisdictions,
  listScopes,
  updateJurisdiction,
  updateScope,
} from "@/lib/api/jurisdictions";

const POPULAR_PRESETS = [
  { code: "JP", name: "Japan" },
  { code: "GB", name: "United Kingdom" },
  { code: "US", name: "United States" },
  { code: "CA", name: "Canada" },
  { code: "AU", name: "Australia" },
  { code: "DE", name: "Germany" },
  { code: "SG", name: "Singapore" },
];

/** What each `source` value means, said in the panel rather than left to be inferred. */
const SOURCE_LABEL: Record<string, string> = {
  pack: "From content pack",
  discovered: "Found on official pages",
  manual: "Added by hand",
};

export default function JurisdictionsPage() {
  const { token } = useAuth();
  const [items, setItems] = useState<AdminJurisdiction[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  // The country a just-finished discovery ran for, so its card can open on its results.
  const [justDiscovered, setJustDiscovered] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setItems(await listJurisdictions(token));
    } catch (e) {
      setError(formatErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }, [token]);

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
      const created = await createJurisdiction(token, {
        code: targetCode,
        name: targetName,
        is_live: true,
      });
      setCode("");
      setName("");
      setSuccessMsg(
        `Added ${targetName} (${targetCode}). Every route starts switched off — open it to see` +
          " what the country publishes and choose what to offer.",
      );
      await load();
      // Adding a country is the moment to ask what it offers, so the admin does not have to
      // know that themselves. The card opens on the answer.
      setJustDiscovered(created.id);
    } catch (e) {
      setError(formatErrorMessage(e));
    } finally {
      setSubmitting(false);
    }
  }

  async function toggleCountry(j: AdminJurisdiction) {
    setError(null);
    setSuccessMsg(null);
    try {
      await updateJurisdiction(token, j.id, { is_enabled: !j.is_enabled });
      setSuccessMsg(
        `${j.name} is now ${
          !j.is_enabled ? "open for applications" : "closed — hidden from applicants"
        }.`,
      );
      await load();
    } catch (e) {
      setError(formatErrorMessage(e));
    }
  }

  async function removeCountry(j: AdminJurisdiction) {
    if (!confirm(`Remove ${j.name} (${j.code}) and all of its routes?`)) return;
    setError(null);
    setSuccessMsg(null);
    try {
      await deleteJurisdiction(token, j.id);
      setSuccessMsg(`Removed ${j.name} (${j.code}).`);
      await load();
    } catch (e) {
      setError(formatErrorMessage(e));
    }
  }

  const openCount = items.filter((j) => j.is_enabled && j.is_live).length;

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-3.5">
          <div className="flex size-11 shrink-0 items-center justify-center rounded-[var(--radius)] bg-primary/10 text-primary">
            <Globe className="size-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight">Countries &amp; application routes</h1>
            <p className="mt-0.5 max-w-2xl text-xs text-muted-foreground">
              Choose which countries accept applications, and which of each country&apos;s visa
              routes and procedures applicants can pick. Everything here starts switched off.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1.5 self-start rounded-lg border bg-card px-3 py-1.5 text-xs">
          <span className="flex size-2 rounded-full bg-emerald-500" />
          <span className="font-semibold text-foreground">{openCount} open</span>
          <span className="text-muted-foreground">/ {items.length} configured</span>
        </div>
      </div>

      {/* ── Messages ───────────────────────────────────────────────────────── */}
      {error && (
        <div
          role="alert"
          className="flex items-start gap-2 rounded-[var(--radius)] border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/10 px-4 py-3 text-xs text-[var(--color-danger)]"
        >
          <XCircle className="mt-0.5 size-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}
      {successMsg && (
        <div
          role="status"
          className="flex items-start gap-2 rounded-[var(--radius)] border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-xs text-emerald-700 dark:text-emerald-300"
        >
          <CheckCircle2 className="mt-0.5 size-4 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* ── Add a country ──────────────────────────────────────────────────── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-bold text-foreground">Add a country</CardTitle>
          <p className="text-xs text-muted-foreground">
            Adding a country reads its own immigration pages to find out which visa routes and
            procedures it publishes. You then choose which of them to offer.
          </p>
        </CardHeader>
        <CardContent className="space-y-4 pt-0">
          <div>
            <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Quick add
            </span>
            <div className="mt-1.5 flex flex-wrap gap-2">
              {POPULAR_PRESETS.map((preset) => {
                const existing = items.find(
                  (i) => i.code.toUpperCase() === preset.code.toUpperCase(),
                );
                return (
                  <button
                    key={preset.code}
                    type="button"
                    disabled={Boolean(existing) || submitting}
                    onClick={() => void create(preset.code, preset.name)}
                    className={`inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium transition-all ${
                      existing
                        ? "cursor-not-allowed border-transparent bg-muted text-muted-foreground opacity-50"
                        : "bg-background text-foreground hover:border-primary/40 hover:bg-accent"
                    }`}
                  >
                    <span>{matchCountry(preset.code).flag}</span>
                    <span>{preset.name}</span>
                    {existing ? (
                      <span className="text-[10px] text-muted-foreground">(added)</span>
                    ) : (
                      <Plus className="size-3 text-primary" />
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              void create();
            }}
            className="flex flex-wrap items-end gap-3 border-t pt-3"
          >
            <label className="flex flex-col gap-1 text-xs">
              <span className="font-medium text-muted-foreground">ISO country code</span>
              <input
                required
                value={code}
                onChange={(e) => {
                  const val = e.target.value.toUpperCase();
                  setCode(val);
                  if (val.length === 2 && !name) {
                    const matched = matchCountry(val);
                    if (matched?.name) setName(matched.name);
                  }
                }}
                placeholder="e.g. CA"
                maxLength={8}
                className="h-9 w-28 rounded-[var(--radius)] border bg-background px-3 font-mono text-xs uppercase outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
            </label>
            <label className="flex flex-1 flex-col gap-1 text-xs">
              <span className="font-medium text-muted-foreground">Country name</span>
              <input
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Canada"
                className="h-9 min-w-44 rounded-[var(--radius)] border bg-background px-3 text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
            </label>
            <Button type="submit" size="sm" disabled={submitting || !code || !name} className="h-9 gap-1.5">
              {submitting ? <Loader2 className="size-4 animate-spin" /> : <Plus className="size-4" />}
              {submitting ? "Adding…" : "Add country"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* ── Configured countries ───────────────────────────────────────────── */}
      <div className="space-y-3">
        <h2 className="text-sm font-bold uppercase tracking-wider text-muted-foreground">
          Configured countries ({items.length})
        </h2>

        {loading ? (
          <p className="py-4 text-xs text-muted-foreground">Loading countries…</p>
        ) : items.length === 0 ? (
          <Card>
            <CardContent className="py-8 text-center text-xs text-muted-foreground">
              No countries configured yet. Use quick add above.
            </CardContent>
          </Card>
        ) : (
          items.map((j) => (
            <JurisdictionCard
              key={j.id}
              jurisdiction={j}
              token={token}
              autoDiscover={justDiscovered === j.id}
              onAutoDiscoverDone={() => setJustDiscovered(null)}
              onToggle={() => void toggleCountry(j)}
              onDelete={() => void removeCountry(j)}
              onError={setError}
            />
          ))
        )}
      </div>
    </div>
  );
}

/* ── One country: its switch, and the routes underneath it ──────────────────── */

function JurisdictionCard({
  jurisdiction: j,
  token,
  autoDiscover,
  onAutoDiscoverDone,
  onToggle,
  onDelete,
  onError,
}: {
  jurisdiction: AdminJurisdiction;
  token: string | null;
  autoDiscover: boolean;
  onAutoDiscoverDone: () => void;
  onToggle: () => void;
  onDelete: () => void;
  onError: (msg: string | null) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [categories, setCategories] = useState<Scope[]>([]);
  const [actions, setActions] = useState<Scope[]>([]);
  const [discovering, setDiscovering] = useState(false);
  const [discovery, setDiscovery] = useState<Discovery | null>(null);

  const flag = matchCountry(j.code).flag || "🌐";

  const loadScopes = useCallback(async () => {
    try {
      const [cats, acts] = await Promise.all([
        listScopes(token, j.id, "visa-categories"),
        listScopes(token, j.id, "case-actions"),
      ]);
      setCategories(cats);
      setActions(acts);
    } catch (e) {
      onError(formatErrorMessage(e));
    }
  }, [token, j.id, onError]);

  useEffect(() => {
    if (expanded) void loadScopes();
  }, [expanded, loadScopes]);

  const runDiscovery = useCallback(async () => {
    setDiscovering(true);
    setDiscovery(null);
    onError(null);
    try {
      const result = await discoverScopes(token, j.id);
      setDiscovery(result);
      await loadScopes();
    } catch (e) {
      onError(formatErrorMessage(e));
    } finally {
      setDiscovering(false);
    }
  }, [token, j.id, loadScopes, onError]);

  useEffect(() => {
    if (!autoDiscover) return;
    setExpanded(true);
    onAutoDiscoverDone();
    void runDiscovery();
  }, [autoDiscover, onAutoDiscoverDone, runDiscovery]);

  const liveRoutes = categories.filter((c) => c.is_enabled).length;

  return (
    <Card className={j.is_enabled ? "border-emerald-500/30" : "border-border opacity-90"}>
      <div className="flex flex-col justify-between gap-3 p-4 sm:flex-row sm:items-center">
        <div className="flex min-w-0 items-center gap-3">
          <span className="shrink-0 text-2xl">{flag}</span>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="truncate text-sm font-bold text-foreground">{j.name}</span>
              <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs font-semibold text-muted-foreground">
                {j.code}
              </span>
              {!j.is_live && (
                <Badge tone="muted" className="text-[10px]" title="No seeded content pack backs this country yet">
                  no content pack
                </Badge>
              )}
            </div>
            <p className="mt-0.5 text-[11px] text-muted-foreground">
              {j.is_enabled
                ? `Open for applications · ${expanded ? `${liveRoutes} of ${categories.length} routes on` : "open a country to manage its routes"}`
                : "Closed — hidden from applicants"}
            </p>
          </div>
        </div>

        <div className="flex shrink-0 flex-wrap items-center gap-2 self-end sm:self-auto">
          <button
            type="button"
            onClick={onToggle}
            aria-pressed={j.is_enabled}
            title={j.is_enabled ? "Close this country to applications" : "Open this country for applications"}
            className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold transition-all ${
              j.is_enabled
                ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 hover:bg-emerald-500/20 dark:text-emerald-300"
                : "border-border bg-muted text-muted-foreground hover:bg-muted/80"
            }`}
          >
            <span
              className={`size-2 rounded-full ${j.is_enabled ? "bg-emerald-500" : "bg-muted-foreground"}`}
            />
            <span>{j.is_enabled ? "Open" : "Closed"}</span>
          </button>

          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setExpanded(!expanded)}
            className="h-8 gap-1 text-xs"
            aria-expanded={expanded}
          >
            <span>Routes</span>
            {expanded ? <ChevronDown className="size-3.5" /> : <ChevronRight className="size-3.5" />}
          </Button>

          <button
            type="button"
            onClick={onDelete}
            title={`Remove ${j.name}`}
            className="inline-flex size-8 items-center justify-center rounded-[var(--radius)] text-muted-foreground transition-colors hover:bg-[var(--color-danger)]/10 hover:text-[var(--color-danger)]"
          >
            <Trash2 className="size-4" />
          </button>
        </div>
      </div>

      {expanded && (
        <div className="space-y-5 border-t bg-muted/20 px-4 py-4 sm:px-5">
          {/* ── Discovery ─────────────────────────────────────────────────── */}
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <p className="max-w-xl text-[11px] text-muted-foreground">
              Search {j.name}&apos;s official immigration pages for the routes and procedures it
              publishes. Anything new arrives switched off, with a link to the page it came from.
            </p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => void runDiscovery()}
              disabled={discovering}
              className="h-8 shrink-0 gap-1.5 text-xs"
            >
              {discovering ? <Loader2 className="size-3.5 animate-spin" /> : <Radar className="size-3.5" />}
              {discovering ? "Searching official pages…" : "Find available routes"}
            </Button>
          </div>

          {discovery && (
            <div className="rounded-md border bg-card px-3 py-2.5 text-[11px]">
              <p className="font-medium text-foreground">{discovery.message}</p>
              {discovery.source_pages.length > 0 && (
                <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1">
                  <span className="text-muted-foreground">Read:</span>
                  {discovery.source_pages.slice(0, 4).map((page) => (
                    <a
                      key={page.url}
                      href={page.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex max-w-full items-center gap-1 truncate text-primary hover:underline"
                    >
                      <span className="truncate">{hostOf(page.url)}</span>
                      <ExternalLink className="size-3 shrink-0" />
                    </a>
                  ))}
                </div>
              )}
            </div>
          )}

          <ScopeSection
            heading={`Visa routes for ${j.name}`}
            emptyLabel="No visa routes yet — search the official pages above, or add one by hand."
            kind="visa-categories"
            scopes={categories}
            token={token}
            jurisdictionId={j.id}
            codePlaceholder="code (e.g. work)"
            namePlaceholder="Route name (e.g. Skilled Worker)"
            onChanged={loadScopes}
            onError={onError}
          />

          <ScopeSection
            heading={`Application types for ${j.name}`}
            emptyLabel="No application types yet — search the official pages above, or add one by hand."
            kind="case-actions"
            scopes={actions}
            token={token}
            jurisdictionId={j.id}
            codePlaceholder="code (e.g. renewal)"
            namePlaceholder="Application type (e.g. Renewal / Extension)"
            onChanged={loadScopes}
            onError={onError}
          />
        </div>
      )}
    </Card>
  );
}

/* ── One list of routes or procedures, with its switches ────────────────────── */

function ScopeSection({
  heading,
  emptyLabel,
  kind,
  scopes,
  token,
  jurisdictionId,
  codePlaceholder,
  namePlaceholder,
  onChanged,
  onError,
}: {
  heading: string;
  emptyLabel: string;
  kind: ScopeKind;
  scopes: Scope[];
  token: string | null;
  jurisdictionId: number;
  codePlaceholder: string;
  namePlaceholder: string;
  onChanged: () => Promise<void>;
  onError: (msg: string | null) => void;
}) {
  const [newCode, setNewCode] = useState("");
  const [newName, setNewName] = useState("");
  const [busy, setBusy] = useState<number | "new" | null>(null);

  async function add(e: FormEvent) {
    e.preventDefault();
    onError(null);
    setBusy("new");
    try {
      await createScope(token, jurisdictionId, kind, {
        code: newCode.trim().toLowerCase(),
        name: newName.trim(),
        // Added by hand and switched on straight away: an admin typing a route in has
        // already made the decision that discovery leaves to them.
        is_enabled: true,
        research_enabled: true,
      });
      setNewCode("");
      setNewName("");
      await onChanged();
    } catch (err) {
      onError(formatErrorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  async function toggle(scope: Scope) {
    onError(null);
    setBusy(scope.id);
    try {
      await updateScope(token, jurisdictionId, kind, scope.id, { is_enabled: !scope.is_enabled });
      await onChanged();
    } catch (err) {
      onError(formatErrorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  async function remove(scope: Scope) {
    onError(null);
    setBusy(scope.id);
    try {
      await deleteScope(token, jurisdictionId, kind, scope.id);
      await onChanged();
    } catch (err) {
      onError(formatErrorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  const onCount = scopes.filter((s) => s.is_enabled).length;

  return (
    <div className="border-t pt-4 first:border-t-0 first:pt-0">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
          {heading}
        </h4>
        <span className="text-[11px] text-muted-foreground">
          {onCount} of {scopes.length} offered to applicants
        </span>
      </div>

      {scopes.length === 0 ? (
        <p className="mb-3 text-xs text-muted-foreground">{emptyLabel}</p>
      ) : (
        <ul className="mb-3 space-y-1.5">
          {scopes.map((scope) => (
            <li
              key={scope.id}
              className="flex flex-col gap-2 rounded-md border bg-card px-3 py-2 text-xs sm:flex-row sm:items-center sm:justify-between"
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-[11px] font-semibold text-muted-foreground">
                    {scope.code}
                  </span>
                  <span className="font-medium text-foreground">{scope.name}</span>
                  <Badge
                    tone={scope.source === "discovered" ? "info" : "muted"}
                    className="text-[10px]"
                  >
                    {SOURCE_LABEL[scope.source] ?? scope.source}
                  </Badge>
                </div>
                {scope.description && (
                  <p className="mt-0.5 text-[11px] text-muted-foreground">{scope.description}</p>
                )}
                {scope.citation?.url && (
                  <a
                    href={scope.citation.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-0.5 inline-flex items-center gap-1 text-[11px] text-primary hover:underline"
                  >
                    <span className="truncate">
                      {scope.citation.title || hostOf(scope.citation.url)}
                    </span>
                    <ExternalLink className="size-3 shrink-0" />
                  </a>
                )}
              </div>

              <div className="flex shrink-0 items-center gap-2 self-end sm:self-auto">
                <button
                  type="button"
                  onClick={() => void toggle(scope)}
                  disabled={busy === scope.id}
                  aria-pressed={scope.is_enabled}
                  title={
                    scope.is_enabled
                      ? "Stop offering this to applicants"
                      : "Offer this to applicants"
                  }
                  className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold transition-all disabled:opacity-50 ${
                    scope.is_enabled
                      ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 hover:bg-emerald-500/20 dark:text-emerald-300"
                      : "border-border bg-muted text-muted-foreground hover:bg-muted/80"
                  }`}
                >
                  {busy === scope.id ? (
                    <Loader2 className="size-3 animate-spin" />
                  ) : (
                    <span
                      className={`size-1.5 rounded-full ${
                        scope.is_enabled ? "bg-emerald-500" : "bg-muted-foreground"
                      }`}
                    />
                  )}
                  {scope.is_enabled ? "On" : "Off"}
                </button>
                <button
                  type="button"
                  onClick={() => void remove(scope)}
                  disabled={busy === scope.id}
                  title={`Delete ${scope.name}`}
                  className="text-muted-foreground transition-colors hover:text-[var(--color-danger)] disabled:opacity-50"
                >
                  <Trash2 className="size-3.5" />
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      <form onSubmit={(e) => void add(e)} className="flex flex-wrap items-end gap-2">
        <input
          required
          value={newCode}
          onChange={(e) => setNewCode(e.target.value)}
          placeholder={codePlaceholder}
          maxLength={32}
          className="h-8 w-28 rounded-[var(--radius)] border bg-background px-2.5 font-mono text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring"
        />
        <input
          required
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder={namePlaceholder}
          className="h-8 min-w-40 flex-1 rounded-[var(--radius)] border bg-background px-2.5 text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring"
        />
        <Button type="submit" size="sm" disabled={busy === "new"} className="h-8 gap-1 text-xs">
          <Plus className="size-3" /> Add
        </Button>
      </form>
    </div>
  );
}

function hostOf(url: string | undefined): string {
  if (!url) return "";
  try {
    return new URL(url).host.replace(/^www\./, "");
  } catch {
    return url;
  }
}
