"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
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
  type Case,
  scopeCase,
} from "@/lib/api/cases";
import { CountrySelector } from "@/components/ui/country-selector";
import { matchCountry } from "@/lib/countries";
import { formatScopeLabel } from "@/lib/utils";

type CaseResult = Case;

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

function ScopePageInner() {
  const router = useRouter();
  const { token, user } = useAuth();
  const searchParams = useSearchParams();
  const destinationParam = searchParams.get("destination");
  const seededDestinationRef = useRef(false);
  const queryClient = useQueryClient();
  const [step, setStep] = useState<Step>("identity");
  const [error, setError] = useState<string | null>(null);
  const [savingIdentity, setSavingIdentity] = useState(false);

  const [residenceCountry, setResidenceCountry] = useState<string>("");
  const [nationality, setNationality] = useState<string>("");
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

  // Auto-select from profile if saved in profile.
  // If not saved in profile, leave empty (do not default to BD or any other country).
  const seededFromProfileRef = useRef(false);

  useEffect(() => {
    if (!seededFromProfileRef.current && user) {
      if (user.current_country && user.current_country.trim()) {
        const matched = matchCountry(user.current_country);
        if (matched?.code) {
          setResidenceCountry(matched.code);
        }
      }
      if (user.nationality && user.nationality.trim()) {
        const matched = matchCountry(user.nationality);
        if (matched?.code) {
          setNationality(matched.code);
        }
      }
      seededFromProfileRef.current = true;
    }
  }, [user]);

  // Pre-seed destination if passed via URL (e.g., ?destination=JP or ?destination=IN)
  useEffect(() => {
    if (!seededDestinationRef.current && destinationParam && geoData?.destinations) {
      const matched = geoData.destinations.find(
        (d) =>
          d.code.toUpperCase() === destinationParam.toUpperCase() ||
          d.name.toLowerCase() === destinationParam.toLowerCase(),
      );
      if (matched) {
        setSelectedDestination(matched);
        seededDestinationRef.current = true;
      }
    }
  }, [destinationParam, geoData]);

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
    // If destination was pre-seeded from URL, jump directly to visa_type
    setStep(selectedDestination ? "visa_type" : "destination");
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
      router.push(`/cases/${result.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create case");
    } finally {
      setSubmitting(false);
    }
  }

  const destinationFlag =
    selectedDestination
      ? selectedDestination.flag || matchCountry(selectedDestination.code).flag || "🌐"
      : "";
  const residenceLabel = residenceCountry ? matchCountry(residenceCountry).name : "";
  const nationalityLabel = nationality ? matchCountry(nationality).name : "";

  if (loading) {
    return (
      <div className="mx-auto max-w-lg space-y-6 py-12 text-center">
        <Loader2 className="mx-auto size-8 animate-spin text-muted-foreground" />
        <p className="text-sm text-muted-foreground">Loading destinations...</p>
      </div>
    );
  }

  if (createdCase) {
    const appTitle =
      formatScopeLabel(
        createdCase.scope_label ||
        [selectedDestination?.name, selectedVisaType?.name, selectedAppType?.name]
          .filter(Boolean)
          .join(" · ")
      ) || "New Visa Application";

    const destName = selectedDestination?.name || createdCase.jurisdiction_code || "";
    const visaName = formatScopeLabel(selectedVisaType?.name || createdCase.visa_category_code || "");
    const actionName = selectedAppType?.name || createdCase.case_action_code || "";

    return (
      <div className="mx-auto max-w-xl space-y-6 py-8 text-center">
        <div className="mx-auto flex size-16 items-center justify-center rounded-full bg-[var(--color-success)]/15 ring-8 ring-[var(--color-success)]/5">
          <Check className="size-8 text-[var(--color-success)]" />
        </div>

        <div className="space-y-2">
          <Badge tone="success" className="px-3 py-1 text-xs font-semibold uppercase tracking-wider">
            Application Created
          </Badge>
          <h2 className="text-2xl font-bold tracking-tight sm:text-3xl text-foreground">
            {appTitle}
          </h2>
          <p className="text-sm text-muted-foreground max-w-md mx-auto">
            Your application is ready. We will guide you step-by-step through intake, eligibility, documents, and filing preparation.
          </p>
        </div>

        <Card className="text-left border border-border/80 shadow-sm">
          <CardContent className="space-y-4 pt-5">
            <div className="flex items-center justify-between pb-3 border-b border-border/60">
              <div>
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Case Reference</p>
                <p className="font-mono text-sm sm:text-base font-bold text-foreground mt-0.5">
                  {createdCase.reference}
                </p>
              </div>
              <Badge tone="success" className="capitalize">
                {createdCase.status}
              </Badge>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs sm:text-sm">
              {destName && (
                <div>
                  <span className="text-muted-foreground block text-xs">Destination</span>
                  <span className="font-medium text-foreground">
                    {destName}
                  </span>
                </div>
              )}
              {visaName && (
                <div>
                  <span className="text-muted-foreground block text-xs">Visa Category</span>
                  <span className="font-medium text-foreground">{visaName}</span>
                </div>
              )}
              {actionName && (
                <div>
                  <span className="text-muted-foreground block text-xs">Application Type</span>
                  <span className="font-medium text-foreground">{actionName}</span>
                </div>
              )}
              {(residenceLabel || nationalityLabel) && (
                <div>
                  <span className="text-muted-foreground block text-xs">Applicant Context</span>
                  <span className="font-medium text-foreground">
                    {[
                      nationalityLabel ? `Citizen of ${nationalityLabel}` : null,
                      residenceLabel ? `Living in ${residenceLabel}` : null,
                    ]
                      .filter(Boolean)
                      .join(" · ") || "—"}
                  </span>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        <div className="rounded-lg border border-border/60 bg-muted/30 p-4 text-left">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
            Next steps in your application
          </p>
          <ol className="space-y-2 text-xs sm:text-sm text-muted-foreground">
            <li className="flex items-center gap-2">
              <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[10px] font-semibold text-primary">1</span>
              <span>Quick 60-second eligibility screening &amp; approval likelihood score (100%)</span>
            </li>
            <li className="flex items-center gap-2">
              <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[10px] font-semibold text-primary">2</span>
              <span>Pay service fee securely via bKash, Nagad, or Credit/Debit Card</span>
            </li>
            <li className="flex items-center gap-2">
              <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[10px] font-semibold text-primary">3</span>
              <span>Fill out personal particulars &amp; upload required documents</span>
            </li>
            <li className="flex items-center gap-2">
              <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[10px] font-semibold text-primary">4</span>
              <span>Torii staff submits on government portal &amp; issues appointment confirmation</span>
            </li>
          </ol>
        </div>

        <div>
          <Link
            href={`/cases/${createdCase.id}`}
            className="inline-flex w-full sm:w-auto items-center justify-center gap-2 rounded-[var(--radius)] bg-primary px-6 py-3.5 text-sm font-bold text-primary-foreground shadow-md hover:opacity-90 transition-opacity"
          >
            Check Visa Eligibility &amp; Start (Free) <ArrowRight className="size-4" />
          </Link>
        </div>
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
  const nationalities = geoData?.nationalities ?? [];

  return (
    <div className="w-full max-w-7xl mx-auto space-y-6 py-6">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight">
          Start a new application
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          {residenceLabel
            ? `Apply for a visa from ${residenceLabel} to our supported destinations.`
            : "Apply for a visa to our supported destinations worldwide."}
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
            <div className="space-y-3 rounded-xl border bg-card p-5 shadow-xs flex flex-col relative">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h3 className="text-sm font-semibold text-foreground">
                    Country of Residence
                  </h3>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Where you currently reside or have legal residency.
                  </p>
                </div>
                {user?.current_country &&
                  residenceCountry &&
                  residenceCountry === matchCountry(user.current_country).code && (
                    <span className="text-[11px] font-medium text-primary bg-primary/10 px-2 py-0.5 rounded-full shrink-0">
                      Profile prefilled
                    </span>
                  )}
              </div>

              <CountrySelector
                valueType="code"
                value={residenceCountry}
                onChange={(code) => setResidenceCountry(code)}
                placeholder="Select country of residence..."
              />
            </div>

            {/* Column 2: Nationality */}
            <div className="space-y-3 rounded-xl border bg-card p-5 shadow-xs flex flex-col relative">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h3 className="text-sm font-semibold text-foreground">
                    Nationality (Passport Country)
                  </h3>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Some visas differ by nationality. We use this to tailor official requirements.
                  </p>
                </div>
                {user?.nationality &&
                  nationality &&
                  nationality === matchCountry(user.nationality).code && (
                    <span className="text-[11px] font-medium text-primary bg-primary/10 px-2 py-0.5 rounded-full shrink-0">
                      Profile prefilled
                    </span>
                  )}
              </div>

              <CountrySelector
                valueType="code"
                value={nationality}
                onChange={(code) => setNationality(code)}
                placeholder="Select nationality / passport country..."
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
            ) : residenceCountry && nationality ? (
              <>
                Continue with {residenceLabel} · {nationalityLabel}
                <ArrowRight className="size-4" />
              </>
            ) : (
              <>
                Select residence & nationality to continue
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
          
          <div className="space-y-1">
            <h3 className="text-base font-bold text-foreground">
              Confirm your application details
            </h3>
            <p className="text-xs text-muted-foreground">
              Review your selection. Next, you will complete a quick 60-second eligibility screening.
            </p>
          </div>

          <Card className="border border-border/80 shadow-xs">
            <CardContent className="space-y-3 pt-5">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Residence</span>
                <span className="font-medium text-foreground">{residenceLabel}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Nationality</span>
                <span className="font-medium text-foreground">{nationalityLabel}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">To</span>
                <span className="font-medium text-foreground">{destinationFlag} {selectedDestination?.name}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Visa type</span>
                <span className="font-medium text-foreground">{selectedVisaType?.name}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Application</span>
                <span className="font-medium text-foreground">{selectedAppType?.name}</span>
              </div>
            </CardContent>
          </Card>

          <div className="rounded-lg border border-border/60 bg-muted/30 p-4 text-left">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
              Next steps in your application
            </p>
            <ol className="space-y-2 text-xs sm:text-sm text-muted-foreground">
              <li className="flex items-center gap-2">
                <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[10px] font-semibold text-primary">1</span>
                <span>Quick 60-second eligibility screening &amp; approval likelihood score (100%)</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[10px] font-semibold text-primary">2</span>
                <span>Pay service fee securely via bKash, Nagad, or Credit/Debit Card</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[10px] font-semibold text-primary">3</span>
                <span>Fill out personal particulars &amp; upload required documents</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[10px] font-semibold text-primary">4</span>
                <span>Torii staff submits on government portal &amp; issues appointment confirmation</span>
              </li>
            </ol>
          </div>

          <button
            onClick={() => void createCase()}
            disabled={submitting}
            className="inline-flex w-full items-center justify-center gap-2 rounded-[var(--radius)] bg-primary px-5 py-3.5 text-sm font-bold text-primary-foreground shadow-md transition-opacity hover:opacity-90 disabled:pointer-events-none disabled:opacity-50"
          >
            {submitting ? (
              <>
                <Loader2 className="size-4 animate-spin" /> Starting application &amp; loading eligibility…
              </>
            ) : (
              <>
                Check Visa Eligibility &amp; Start (Free) <ArrowRight className="size-4" />
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
}

export default function ScopePage() {
  return (
    <Suspense
      fallback={
        <div className="mx-auto max-w-lg space-y-6 py-12 text-center">
          <Loader2 className="mx-auto size-8 animate-spin text-muted-foreground" />
        </div>
      }
    >
      <ScopePageInner />
    </Suspense>
  );
}
