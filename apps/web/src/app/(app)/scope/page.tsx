"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Check, Globe, Loader2, ArrowRight } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/lib/auth-context";
import {
  listJurisdictions,
  listVisaCategories,
  listCaseActions,
  scopeCase,
  type Jurisdiction,
  type VisaCategory,
  type CaseAction,
} from "@/lib/api/cases";

type CaseResult = { id: number; reference: string; status: string };

type Step = "jurisdiction" | "category" | "action" | "review";

export default function ScopePage() {
  const { token } = useAuth();
  const [step, setStep] = useState<Step>("jurisdiction");
  const [error, setError] = useState<string | null>(null);

  // Data
  const [jurisdictions, setJurisdictions] = useState<Jurisdiction[]>([]);
  const [categories, setCategories] = useState<VisaCategory[]>([]);
  const [actions, setActions] = useState<CaseAction[]>([]);

  // Selections
  const [selectedJurisdiction, setSelectedJurisdiction] = useState<Jurisdiction | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<VisaCategory | null>(null);
  const [selectedAction, setSelectedAction] = useState<CaseAction | null>(null);

  const [submitting, setSubmitting] = useState(false);
  const [createdCase, setCreatedCase] = useState<CaseResult | null>(null);

  // Load jurisdictions on mount
  useEffect(() => {
    if (!token) return;
    void (async () => {
      try {
        setJurisdictions(await listJurisdictions(token, false));
      } catch {
        setError("Could not load jurisdictions. Is the API running?");
      }
    })();
  }, [token]);

  // Load categories when jurisdiction is selected
  useEffect(() => {
    if (!selectedJurisdiction || !token) return;
    void (async () => {
      try {
        setCategories(await listVisaCategories(token, selectedJurisdiction.code, false));
      } catch {
        setError("Could not load visa categories.");
      }
    })();
  }, [selectedJurisdiction, token]);

  // Load actions when jurisdiction is selected
  useEffect(() => {
    if (!selectedJurisdiction || !token) return;
    void (async () => {
      try {
        setActions(await listCaseActions(token, selectedJurisdiction.code, false));
      } catch {
        setError("Could not load case actions.");
      }
    })();
  }, [selectedJurisdiction, token]);

  function goBack() {
    setError(null);
    if (step === "category") setStep("jurisdiction");
    else if (step === "action") setStep("category");
    else if (step === "review") setStep("action");
  }

  function selectJurisdiction(j: Jurisdiction) {
    if (!j.is_live) return;
    setSelectedJurisdiction(j);
    setSelectedCategory(null);
    setSelectedAction(null);
    setStep("category");
  }

  function selectCategory(c: VisaCategory) {
    if (!c.is_live) return;
    setSelectedCategory(c);
    setStep("action");
  }

  function selectAction(a: CaseAction) {
    if (!a.is_live) return;
    setSelectedAction(a);
    setStep("review");
  }

  async function createCase() {
    if (!token || !selectedJurisdiction || !selectedCategory || !selectedAction) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await scopeCase(token, {
        jurisdiction_code: selectedJurisdiction.code,
        visa_category_code: selectedCategory.code,
        action_code: selectedAction.code,
      });
      setCreatedCase(result);
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
          ready. We will walk you through intake, eligibility, documents, forms, and packet.
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
        <ol className="space-y-2 text-left text-sm text-muted-foreground">
          <li>1. Answer intake questions</li>
          <li>2. Check published eligibility rules</li>
          <li>3. Gather required documents</li>
          <li>4. Generate forms and build your packet</li>
        </ol>
        <Link
          href={`/cases/${createdCase.id}`}
          className="inline-flex items-center justify-center gap-2 rounded-[var(--radius)] bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground hover:opacity-90"
        >
          Continue to intake <ArrowRight className="size-4" />
        </Link>
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
                disabled={!j.is_live}
                className={`flex w-full items-center gap-4 rounded-[var(--radius)] border bg-card p-4 text-left transition-colors ${
                  j.is_live ? "hover:bg-accent" : "cursor-not-allowed opacity-60"
                }`}
              >
                <Globe className="size-5 text-muted-foreground" />
                <div className="flex-1">
                  <p className="font-medium">{j.name}</p>
                  <p className="text-xs text-muted-foreground font-mono">{j.code}</p>
                </div>
                <Badge tone={j.is_live ? "success" : "muted"}>
                  {j.is_live ? "Available" : "Coming soon"}
                </Badge>
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
                disabled={!c.is_live}
                className={`flex w-full items-center gap-4 rounded-[var(--radius)] border bg-card p-4 text-left transition-colors ${
                  c.is_live ? "hover:bg-accent" : "cursor-not-allowed opacity-60"
                }`}
              >
                <div className="flex-1">
                  <p className="font-medium">{c.name}</p>
                  <p className="text-xs text-muted-foreground font-mono">{c.code}</p>
                </div>
                <Badge tone={c.is_live ? "success" : "muted"}>
                  {c.is_live ? "Available" : "Coming soon"}
                </Badge>
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
                disabled={!a.is_live}
                className={`flex w-full items-center gap-4 rounded-[var(--radius)] border bg-card p-4 text-left transition-colors ${
                  a.is_live ? "hover:bg-accent" : "cursor-not-allowed opacity-60"
                }`}
              >
                <div className="flex-1">
                  <p className="font-medium">{a.name}</p>
                  <p className="text-xs text-muted-foreground font-mono">{a.code}</p>
                </div>
                <Badge tone={a.is_live ? "success" : "muted"}>
                  {a.is_live ? "Available" : "Coming soon"}
                </Badge>
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
