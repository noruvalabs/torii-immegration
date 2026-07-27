"use client";

import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Check, Globe, Loader2, ArrowRight } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/lib/auth-context";

type Jurisdiction = { id: number; code: string; name: string; is_live: boolean };
type Category = { id: number; code: string; name: string; is_live: boolean };
type CaseResult = { id: number; reference: string; status: string };

const API = "/backend/v1";

type Step = "jurisdiction" | "category" | "action" | "review";

export default function ScopePage() {
  const { token } = useAuth();
  const [step, setStep] = useState<Step>("jurisdiction");
  const [error, setError] = useState<string | null>(null);

  // Data
  const [jurisdictions, setJurisdictions] = useState<Jurisdiction[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [actions, setActions] = useState<Category[]>([]);

  // Selections
  const [selectedJurisdiction, setSelectedJurisdiction] = useState<Jurisdiction | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<Category | null>(null);
  const [selectedAction, setSelectedAction] = useState<Category | null>(null);

  const [submitting, setSubmitting] = useState(false);
  const [createdCase, setCreatedCase] = useState<CaseResult | null>(null);

  const hdrs = useCallback((): Record<string, string> => {
    const h: Record<string, string> = { "content-type": "application/json" };
    if (token) h.Authorization = `Bearer ${token}`;
    return h;
  }, [token]);

  // Load jurisdictions on mount
  useEffect(() => {
    void (async () => {
      try {
        const res = await fetch(`${API}/jurisdictions?live_only=true`, {
          cache: "no-store",
          headers: hdrs(),
        });
        if (!res.ok) throw new Error(`API returned ${res.status}`);
        setJurisdictions(await res.json());
      } catch {
        setError("Could not load jurisdictions. Is the API running?");
      }
    })();
  }, [hdrs]);

  // Load categories when jurisdiction is selected
  useEffect(() => {
    if (!selectedJurisdiction) return;
    void (async () => {
      try {
        const res = await fetch(
          `${API}/cases/visa-categories?jurisdiction_code=${selectedJurisdiction.code}&live_only=true`,
          { cache: "no-store", headers: hdrs() },
        );
        if (!res.ok) throw new Error(`API returned ${res.status}`);
        setCategories(await res.json());
      } catch {
        setError("Could not load visa categories.");
      }
    })();
  }, [selectedJurisdiction, hdrs]);

  // Load actions when jurisdiction is selected
  useEffect(() => {
    if (!selectedJurisdiction) return;
    void (async () => {
      try {
        const res = await fetch(
          `${API}/cases/case-actions?jurisdiction_code=${selectedJurisdiction.code}&live_only=true`,
          { cache: "no-store", headers: hdrs() },
        );
        if (!res.ok) throw new Error(`API returned ${res.status}`);
        setActions(await res.json());
      } catch {
        setError("Could not load case actions.");
      }
    })();
  }, [selectedJurisdiction, hdrs]);

  function goBack() {
    setError(null);
    if (step === "category") setStep("jurisdiction");
    else if (step === "action") setStep("category");
    else if (step === "review") setStep("action");
  }

  function selectJurisdiction(j: Jurisdiction) {
    setSelectedJurisdiction(j);
    setSelectedCategory(null);
    setSelectedAction(null);
    setStep("category");
  }

  function selectCategory(c: Category) {
    setSelectedCategory(c);
    setStep("action");
  }

  function selectAction(a: Category) {
    setSelectedAction(a);
    setStep("review");
  }

  async function createCase() {
    if (!selectedJurisdiction || !selectedCategory || !selectedAction) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch(`${API}/cases/scope`, {
        method: "POST",
        headers: hdrs(),
        body: JSON.stringify({
          jurisdiction_code: selectedJurisdiction.code,
          visa_category_code: selectedCategory.code,
          action_code: selectedAction.code,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `API returned ${res.status}`);
      }
      setCreatedCase(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create case");
    } finally {
      setSubmitting(false);
    }
  }

  if (createdCase) {
    return (
      <div className="mx-auto max-w-lg space-y-6 py-12 text-center">
        <div className="mx-auto flex size-16 items-center justify-center rounded-full bg-[var(--color-success)]/15">
          <Check className="size-8 text-[var(--color-success)]" />
        </div>
        <h2 className="text-2xl font-semibold">Case created</h2>
        <p className="text-muted-foreground">
          Your case <strong className="font-mono">{createdCase.reference}</strong> is
          ready. Next step: complete the intake questionnaire.
        </p>
        <Card>
          <CardContent className="flex items-center justify-between pt-5">
            <div className="text-left">
              <p className="text-xs text-muted-foreground">Reference</p>
              <p className="font-mono font-semibold">{createdCase.reference}</p>
            </div>
            <Badge tone="success">{createdCase.status}</Badge>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6 py-8">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight">
          Start a new case
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Select your country, visa type, and what you need help with. Only
          supported combinations are shown.
        </p>
      </div>

      {/* Progress */}
      <div className="flex items-center gap-2 text-sm">
        {(["jurisdiction", "category", "action", "review"] as Step[]).map(
          (s, i) => (
            <div key={s} className="flex items-center gap-2">
              {i > 0 && <span className="text-muted-foreground">/</span>}
              <span
                className={
                  step === s
                    ? "font-medium text-foreground"
                    : "text-muted-foreground"
                }
              >
                {s === "jurisdiction"
                  ? "Country"
                  : s === "category"
                    ? "Visa type"
                    : s === "action"
                      ? "Action"
                      : "Review"}
              </span>
            </div>
          ),
        )}
      </div>

      {error && (
        <p className="rounded-[var(--radius)] border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/10 px-4 py-3 text-sm text-[var(--color-danger)]">
          {error}
        </p>
      )}

      {/* Step: jurisdiction */}
      {step === "jurisdiction" && (
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-muted-foreground">
            Select a country
          </h3>
          {jurisdictions.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No live jurisdictions available.
            </p>
          ) : (
            jurisdictions.map((j) => (
              <button
                key={j.id}
                onClick={() => selectJurisdiction(j)}
                className="flex w-full items-center gap-4 rounded-[var(--radius)] border bg-card p-4 text-left transition-colors hover:bg-accent"
              >
                <Globe className="size-5 text-muted-foreground" />
                <div className="flex-1">
                  <p className="font-medium">{j.name}</p>
                  <p className="text-xs text-muted-foreground font-mono">{j.code}</p>
                </div>
                <ArrowRight className="size-4 text-muted-foreground" />
              </button>
            ))
          )}
        </div>
      )}

      {/* Step: category */}
      {step === "category" && (
        <div className="space-y-3">
          <button onClick={goBack} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
            <ArrowLeft className="size-3.5" /> Back
          </button>
          <h3 className="text-sm font-medium text-muted-foreground">
            Select a visa type for <strong>{selectedJurisdiction?.name}</strong>
          </h3>
          {categories.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No visa categories available for this jurisdiction.
            </p>
          ) : (
            categories.map((c) => (
              <button
                key={c.id}
                onClick={() => selectCategory(c)}
                className="flex w-full items-center gap-4 rounded-[var(--radius)] border bg-card p-4 text-left transition-colors hover:bg-accent"
              >
                <div className="flex-1">
                  <p className="font-medium">{c.name}</p>
                  <p className="text-xs text-muted-foreground font-mono">{c.code}</p>
                </div>
                <ArrowRight className="size-4 text-muted-foreground" />
              </button>
            ))
          )}
        </div>
      )}

      {/* Step: action */}
      {step === "action" && (
        <div className="space-y-3">
          <button onClick={goBack} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
            <ArrowLeft className="size-3.5" /> Back
          </button>
          <h3 className="text-sm font-medium text-muted-foreground">
            What do you need to do?
          </h3>
          {actions.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No actions available for this jurisdiction.
            </p>
          ) : (
            actions.map((a) => (
              <button
                key={a.id}
                onClick={() => selectAction(a)}
                className="flex w-full items-center gap-4 rounded-[var(--radius)] border bg-card p-4 text-left transition-colors hover:bg-accent"
              >
                <div className="flex-1">
                  <p className="font-medium">{a.name}</p>
                  <p className="text-xs text-muted-foreground font-mono">{a.code}</p>
                </div>
                <ArrowRight className="size-4 text-muted-foreground" />
              </button>
            ))
          )}
        </div>
      )}

      {/* Step: review */}
      {step === "review" && (
        <div className="space-y-4">
          <button onClick={goBack} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
            <ArrowLeft className="size-3.5" /> Back
          </button>
          <h3 className="text-sm font-medium text-muted-foreground">
            Confirm your case details
          </h3>
          <Card>
            <CardContent className="space-y-3 pt-5">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Country</span>
                <span className="font-medium">{selectedJurisdiction?.name}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Visa type</span>
                <span className="font-medium">{selectedCategory?.name}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Action</span>
                <span className="font-medium">{selectedAction?.name}</span>
              </div>
            </CardContent>
          </Card>
          <button
            onClick={() => void createCase()}
            disabled={submitting}
            className="inline-flex w-full items-center justify-center gap-2 rounded-[var(--radius)] bg-primary px-4 py-3 text-sm font-medium text-primary-foreground transition-colors hover:opacity-90 disabled:pointer-events-none disabled:opacity-50"
          >
            {submitting ? (
              <>
                <Loader2 className="size-4 animate-spin" /> Creating…
              </>
            ) : (
              "Create case"
            )}
          </button>
        </div>
      )}
    </div>
  );
}
