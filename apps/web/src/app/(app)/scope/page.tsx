"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Check, Loader2, ArrowRight, Search, X } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/lib/auth-context";
import {
  type Destination,
  type VisaType,
  type ApplicationType,
} from "@/lib/api/geo";
import {
  useGeoDataQuery,
  useVisaTypesQuery,
  useApplicationTypesQuery,
} from "@/lib/queries/geo";
import { caseKeys } from "@/lib/queries/cases";
import { useQueryClient } from "@tanstack/react-query";
import { updateProfile } from "@/lib/api/auth";
import {
  scopeCase,
} from "@/lib/api/cases";
import { CountrySelector } from "@/components/ui/country-selector";
import { matchCountry } from "@/lib/countries";

type CaseResult = { id: number; reference: string; status: string };

/** Combined residence + nationality, then destination → visa → app → review */
type Step = "identity" | "destination" | "visa_type" | "app_type" | "review";

const STEP_ORDER: Step[] = ["identity", "destination", "visa_type", "app_type", "review"];

/**
 * True when a description adds something the name has not already said.
 *
 * Route names carry their own gloss — "Student Visa - 留学 (Study at a university, college,
 * or language school)" — so a generic "Study at an educational institution" underneath is
 * noise. Comparing for equality alone missed that, and left three rows in eight wearing a
 * subtitle for no reason anyone reading the list could work out.
 */
function isExtraDetail(description: string, name: string): boolean {
  const d = description.trim().toLowerCase();
  if (!d) return false;
  const n = name.trim().toLowerCase();
  return d !== n && !n.includes(d);
}

const STEP_LABELS: Record<Step, string> = {
  identity: "Residence & Nationality",
  destination: "Destination",
  visa_type: "Visa type",
  app_type: "Application",
  review: "Review",
};

export default function ScopePage() {
  const { token, user } = useAuth();
  const queryClient = useQueryClient();
  const [step, setStep] = useState<Step>("identity");
  const [error, setError] = useState<string | null>(null);
  const [savingIdentity, setSavingIdentity] = useState(false);

  const [residenceCountry, setResidenceCountry] = useState<string>("BD");
  const [nationality, setNationality] = useState<string>("BD");
  const [selectedDestination, setSelectedDestination] = useState<Destination | null>(null);
  const [selectedVisaType, setSelectedVisaType] = useState<VisaType | null>(null);
  const [selectedAppType, setSelectedAppType] = useState<ApplicationType | null>(null);

  const [submitting, setSubmitting] = useState(false);
  const [createdCase, setCreatedCase] = useState<CaseResult | null>(null);
  const [visaFilter, setVisaFilter] = useState("");

  const { data: geoData = null, isLoading: geoLoading } = useGeoDataQuery(Boolean(token));
  const { data: dynamicVisaTypes = null, isLoading: loadingVisaTypes } = useVisaTypesQuery(
    selectedDestination?.code,
  );
  const { data: dynamicAppTypes = null, isLoading: loadingAppTypes } = useApplicationTypesQuery(
    selectedDestination?.code,
    selectedVisaType?.code,
  );

  const loading = geoLoading && !geoData;

  // Seed residence/nationality once from profile — never re-run after Continue saves profile.
  const seededFromProfileRef = useRef(false);
  const userRef = useRef(user);
  userRef.current = user;

  useEffect(() => {
    if (geoData && !seededFromProfileRef.current) {
      const profile = userRef.current;
      const fallback = geoData.detected_country.country_code;
      setResidenceCountry(matchCountry(profile?.current_country, fallback).code);
      setNationality(matchCountry(profile?.nationality, fallback).code);
      seededFromProfileRef.current = true;
    }
  }, [geoData]);

  function goBack() {
    const i = STEP_ORDER.indexOf(step);
    if (i > 0) goToStep(STEP_ORDER[i - 1]);
  }

  /** Jump to an earlier step. Forward moves stay with the step's own confirm action. */
  function goToStep(target: Step) {
    if (STEP_ORDER.indexOf(target) > STEP_ORDER.indexOf(step)) return;
    setError(null);
    setStep(target);
  }

  async function confirmIdentity() {
    if (!residenceCountry || !nationality || savingIdentity) return;
    setError(null);
    setSavingIdentity(true);
    // Advance immediately so a profile save cannot yank the user back to identity.
    setStep("destination");
    if (token) {
      try {
        const natName = matchCountry(nationality).name;
        const resName = matchCountry(residenceCountry).name;
        // Do not call setAuth here — updating global user re-triggered this page previously.
        await updateProfile(token, {
          nationality: natName,
          current_country: resName,
        });
      } catch {
        // Profile save is best-effort; scoping can continue.
      }
    }
    setSavingIdentity(false);
  }

  function selectDestination(d: Destination) {
    setError(null);
    setSelectedDestination(d);
    setSelectedVisaType(null);
    setSelectedAppType(null);
    setVisaFilter("");
    setStep("visa_type");
  }

  function selectVisaType(v: VisaType) {
    setError(null);
    setSelectedVisaType(v);
    setSelectedAppType(null);
    setStep("app_type");
  }

  function selectAppType(a: ApplicationType) {
    setSelectedAppType(a);
    setStep("review");
  }

  async function createCase() {
    if (!token || !selectedDestination || !selectedVisaType || !selectedAppType) return;
    setSubmitting(true);
    setError(null);
    try {
      const jurisdictionCode = selectedDestination.code;
      const visaCategoryCode = selectedVisaType.code;
      const actionCode = selectedAppType.code;

      const result = await scopeCase(token, {
        jurisdiction_code: jurisdictionCode,
        visa_category_code: visaCategoryCode,
        action_code: actionCode,
        origin_country: nationality,
        residence_country: residenceCountry,
      });
      setCreatedCase(result);
      void queryClient.invalidateQueries({ queryKey: caseKeys.list() });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create case");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-lg space-y-6 py-12 text-center">
        <Loader2 className="mx-auto size-8 animate-spin text-muted-foreground" />
        <p className="text-sm text-muted-foreground">Loading destinations...</p>
      </div>
    );
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

  const destinations = geoData?.destinations ?? [];
  // Only the bootstrap payload's generic list may stand in before a destination is picked.
  // After one is, offering tourist/student/work for a country whose rows do not include
  // them walks the applicant to a refusal on the last click.
  const visaTypes = selectedDestination
    ? (dynamicVisaTypes ?? [])
    : (geoData?.visa_types ?? []);
  const appTypes =
    selectedDestination && selectedVisaType
      ? (dynamicAppTypes ?? [])
      : (geoData?.application_types ?? []);
  const visaQuery = visaFilter.trim().toLowerCase();
  const filteredVisaTypes = visaQuery
    ? visaTypes.filter((v) =>
        `${v.name} ${v.description} ${v.code}`.toLowerCase().includes(visaQuery),
      )
    : visaTypes;
  const destinationFlag =
    selectedDestination
      ? selectedDestination.flag || matchCountry(selectedDestination.code).flag || "🌐"
      : "";
  const nationalities = geoData?.nationalities ?? [];
  const residenceLabel = matchCountry(residenceCountry).name;
  const nationalityLabel = matchCountry(nationality).name;

  return (
    <div className="w-full max-w-7xl mx-auto space-y-6 py-6">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight">
          Start a new application
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Apply for a visa from {residenceLabel || geoData?.detected_country?.country_name || "your residence"} to our supported destinations.
        </p>
      </div>

      <nav aria-label="Application steps">
        <ol className="flex flex-wrap items-center gap-2 text-sm">
          {STEP_ORDER.map((s, i) => {
            const currentIndex = STEP_ORDER.indexOf(step);
            // A step already passed can be returned to; one not yet reached cannot, since
            // the answer it needs has not been given.
            const isDone = i < currentIndex;
            return (
              <li key={s} className="flex items-center gap-2">
                {i > 0 && (
                  <span aria-hidden="true" className="text-muted-foreground">
                    /
                  </span>
                )}
                {isDone ? (
                  <button
                    type="button"
                    onClick={() => goToStep(s)}
                    className="rounded-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    {STEP_LABELS[s]}
                  </button>
                ) : (
                  <span
                    aria-current={step === s ? "step" : undefined}
                    className={
                      step === s ? "font-medium text-foreground" : "text-muted-foreground"
                    }
                  >
                    {STEP_LABELS[s]}
                  </span>
                )}
              </li>
            );
          })}
        </ol>
      </nav>

      {error && (
        <p className="rounded-[var(--radius)] border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/10 px-4 py-3 text-sm text-[var(--color-danger)]">
          {error}
        </p>
      )}

      {/* Combined residence + nationality */}
      {/* Combined residence + nationality in 2 columns */}
      {step === "identity" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
            {/* Column 1: Country of residence */}
            <div className="space-y-3 rounded-xl border bg-card p-5 shadow-xs flex flex-col">
              <div>
                <h3 className="text-sm font-semibold text-foreground">
                  Country of Residence
                </h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Where you currently reside or have legal residency.
                </p>
              </div>

              {(user?.current_country || geoData?.detected_country) && (
                <div className="rounded-[var(--radius)] border border-primary/20 bg-primary/5 px-3 py-2 text-xs flex items-center justify-between">
                  <span className="font-medium text-foreground">
                    {user?.current_country ? "Profile / auto-detected:" : "Auto-detected:"}
                  </span>
                  <span className="font-semibold text-primary">
                    {residenceLabel}
                  </span>
                </div>
              )}

              <CountrySelector
                mode="grid"
                valueType="code"
                value={residenceCountry}
                onChange={(code) => setResidenceCountry(code)}
                gridMaxHeightClass="max-h-72"
                gridColsClass="grid-cols-1 sm:grid-cols-2"
              />
            </div>

            {/* Column 2: Nationality */}
            <div className="space-y-3 rounded-xl border bg-card p-5 shadow-xs flex flex-col">
              <div>
                <h3 className="text-sm font-semibold text-foreground">
                  Nationality (Passport Country)
                </h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Some visas differ by nationality. We use this to tailor official requirements.
                </p>
              </div>

              <div className="rounded-[var(--radius)] border border-muted bg-muted/40 px-3 py-2 text-xs flex items-center justify-between">
                <span className="font-medium text-muted-foreground">
                  Selected Passport:
                </span>
                <span className="font-semibold text-foreground">
                  {nationalityLabel}
                </span>
              </div>

              <CountrySelector
                mode="grid"
                valueType="code"
                value={nationality}
                onChange={(code) => setNationality(code)}
                gridMaxHeightClass="max-h-72"
                gridColsClass="grid-cols-1 sm:grid-cols-2"
              />
            </div>
          </div>

          <button
            type="button"
            onClick={() => void confirmIdentity()}
            disabled={!residenceCountry || !nationality || savingIdentity}
            className="inline-flex w-full items-center justify-center gap-2 rounded-[var(--radius)] bg-primary px-4 py-3.5 text-sm font-medium text-primary-foreground transition-colors hover:opacity-90 disabled:pointer-events-none disabled:opacity-50 shadow-sm"
          >
            {savingIdentity ? (
              <>
                <Loader2 className="size-4 animate-spin" /> Continuing…
              </>
            ) : (
              <>
                Continue with {residenceLabel} · {nationalityLabel}
                <ArrowRight className="size-4" />
              </>
            )}
          </button>
        </div>
      )}

      {step === "destination" && (
        <div className="space-y-3">
          <button onClick={goBack} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
            <ArrowLeft className="size-3.5" /> Back
          </button>
          <h3 className="text-sm font-medium text-muted-foreground">
            Where are you applying to?
          </h3>
          {destinations.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No destinations available.
            </p>
          ) : (
            destinations.map((d) => {
              const flag = d.flag || matchCountry(d.code).flag || "🌐";
              return (
                <button
                  key={d.code}
                  onClick={() => selectDestination(d)}
                  className="flex w-full items-center gap-4 rounded-[var(--radius)] border bg-card p-4 text-left transition-colors hover:bg-accent"
                >
                  <span className="text-2xl">{flag}</span>
                  <div className="flex-1">
                    <p className="font-medium">{d.name}</p>
                    <p className="text-xs text-muted-foreground">{d.currency}</p>
                  </div>
                  <ArrowRight className="size-4 text-muted-foreground" />
                </button>
              );
            })
          )}
        </div>
      )}

      {step === "visa_type" && (
        <div className="space-y-3">
          <button onClick={goBack} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
            <ArrowLeft className="size-3.5" /> Back
          </button>
          <h3 className="text-sm font-medium text-muted-foreground">
            Visa type for <strong>{destinationFlag} {selectedDestination?.name}</strong>
          </h3>
          {/* A fully-discovered country can publish dozens of routes, which is more than
              anyone wants to scroll. The box appears only once the list earns it. */}
          {!loadingVisaTypes && visaTypes.length > 8 && (
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                value={visaFilter}
                onChange={(e) => setVisaFilter(e.target.value)}
                placeholder={`Filter ${visaTypes.length} visa types...`}
                aria-label="Filter visa types"
                className="h-9 w-full rounded-[var(--radius)] border bg-background pl-9 pr-8 text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
              {visaFilter && (
                <button
                  type="button"
                  onClick={() => setVisaFilter("")}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground"
                  aria-label="Clear filter"
                >
                  <X className="size-3.5" />
                </button>
              )}
            </div>
          )}
          {loadingVisaTypes ? (
            <div className="py-8 text-center">
              <Loader2 className="mx-auto size-6 animate-spin text-muted-foreground" />
              <p className="mt-2 text-xs text-muted-foreground">Loading available visa types…</p>
            </div>
          ) : visaTypes.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No visa types available for this destination.
            </p>
          ) : filteredVisaTypes.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No visa type matches “{visaFilter}”.
            </p>
          ) : (
            filteredVisaTypes.map((v) => (
              <button
                key={v.code}
                onClick={() => selectVisaType(v)}
                className="flex w-full items-center gap-4 rounded-[var(--radius)] border bg-card p-4 text-left transition-colors hover:bg-accent"
              >
                <div className="flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-medium">{v.name}</p>
                    {v.is_research && (
                      <Badge tone="info" title="Requirements are read from official sources when you apply, rather than from a reviewed pack.">
                        Live research
                      </Badge>
                    )}
                  </div>
                  {isExtraDetail(v.description, v.name) && (
                    <p className="text-xs text-muted-foreground mt-0.5">{v.description}</p>
                  )}
                </div>
                <ArrowRight className="size-4 text-muted-foreground" />
              </button>
            ))
          )}
        </div>
      )}

      {step === "app_type" && (
        <div className="space-y-3">
          <button onClick={goBack} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
            <ArrowLeft className="size-3.5" /> Back
          </button>
          <h3 className="text-sm font-medium text-muted-foreground">
            Application type for <strong>{destinationFlag} {selectedDestination?.name} — {selectedVisaType?.name}</strong>
          </h3>
          {loadingAppTypes ? (
            <div className="py-8 text-center">
              <Loader2 className="mx-auto size-6 animate-spin text-muted-foreground" />
              <p className="mt-2 text-xs text-muted-foreground">Loading available application types…</p>
            </div>
          ) : appTypes.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No application types available for this visa type.
            </p>
          ) : (
            appTypes.map((a) => (
              <button
                key={a.code}
                onClick={() => selectAppType(a)}
                className="flex w-full items-center gap-4 rounded-[var(--radius)] border bg-card p-4 text-left transition-colors hover:bg-accent"
              >
                <div className="flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-medium">{a.name}</p>
                    {a.is_research && (
                      <Badge tone="info" title="Requirements are read from official sources when you apply, rather than from a reviewed pack.">
                        Live research
                      </Badge>
                    )}
                  </div>
                  {isExtraDetail(a.description, a.name) && (
                    <p className="text-xs text-muted-foreground mt-0.5">{a.description}</p>
                  )}
                </div>
                <ArrowRight className="size-4 text-muted-foreground" />
              </button>
            ))
          )}
        </div>
      )}

      {step === "review" && (
        <div className="space-y-4">
          <button onClick={goBack} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
            <ArrowLeft className="size-3.5" /> Back
          </button>
          <h3 className="text-sm font-medium text-muted-foreground">
            Confirm your application details
          </h3>
          <Card>
            <CardContent className="space-y-3 pt-5">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Residence</span>
                <span className="font-medium">{residenceLabel}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Nationality</span>
                <span className="font-medium">{nationalityLabel}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">To</span>
                <span className="font-medium">{destinationFlag} {selectedDestination?.name}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Visa type</span>
                <span className="font-medium">{selectedVisaType?.name}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Application</span>
                <span className="font-medium">{selectedAppType?.name}</span>
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
              "Start application"
            )}
          </button>
        </div>
      )}
    </div>
  );
}
