"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Check, Globe, Loader2, ArrowRight } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/lib/auth-context";
import {
  getAllGeoData,
  type GeoData,
  type Destination,
  type VisaType,
  type ApplicationType,
} from "@/lib/api/geo";
import {
  scopeCase,
} from "@/lib/api/cases";

type CaseResult = { id: number; reference: string; status: string };

type Step = "residence" | "destination" | "visa_type" | "app_type" | "review";

export default function ScopePage() {
  const { token } = useAuth();
  const [step, setStep] = useState<Step>("residence");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Geo data
  const [geoData, setGeoData] = useState<GeoData | null>(null);

  // Selections
  const [residenceCountry, setResidenceCountry] = useState<string>("JP");
  const [selectedDestination, setSelectedDestination] = useState<Destination | null>(null);
  const [selectedVisaType, setSelectedVisaType] = useState<VisaType | null>(null);
  const [selectedAppType, setSelectedAppType] = useState<ApplicationType | null>(null);

  const [submitting, setSubmitting] = useState(false);
  const [createdCase, setCreatedCase] = useState<CaseResult | null>(null);

  // Load geo data on mount
  useEffect(() => {
    if (!token) return;
    void (async () => {
      try {
        setLoading(true);
        const data = await getAllGeoData();
        setGeoData(data);
        setResidenceCountry(data.detected_country.country_code);
      } catch {
        setError("Could not load destination data. Is the API running?");
      } finally {
        setLoading(false);
      }
    })();
  }, [token]);

  function goBack() {
    setError(null);
    if (step === "destination") setStep("residence");
    else if (step === "visa_type") setStep("destination");
    else if (step === "app_type") setStep("visa_type");
    else if (step === "review") setStep("app_type");
  }

  function selectDestination(d: Destination) {
    setSelectedDestination(d);
    setSelectedVisaType(null);
    setSelectedAppType(null);
    setStep("visa_type");
  }

  function selectVisaType(v: VisaType) {
    setSelectedVisaType(v);
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
      // Map the new system to the old jurisdiction codes
      const jurisdictionCode = selectedDestination.code;
      const visaCategoryCode = selectedVisaType.code;
      const actionCode = selectedAppType.code;

      const result = await scopeCase(token, {
        jurisdiction_code: jurisdictionCode,
        visa_category_code: visaCategoryCode,
        action_code: actionCode,
      });
      setCreatedCase(result);
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
  const visaTypes = geoData?.visa_types ?? [];
  const appTypes = geoData?.application_types ?? [];

  return (
    <div className="mx-auto max-w-2xl space-y-6 py-8">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight">
          Start a new application
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Apply for a visa from {geoData?.detected_country.country_name ?? "your country"} to any destination worldwide.
        </p>
      </div>

      {/* Progress */}
      <div className="flex items-center gap-2 text-sm">
        {(["residence", "destination", "visa_type", "app_type", "review"] as Step[]).map(
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
                {s === "residence"
                  ? "Residence"
                  : s === "destination"
                    ? "Destination"
                    : s === "visa_type"
                      ? "Visa type"
                      : s === "app_type"
                        ? "Application"
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

      {/* Step: residence */}
      {step === "residence" && (
        <div className="space-y-3">
          <button onClick={goBack} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
            <ArrowLeft className="size-3.5" /> Back
          </button>
          <h3 className="text-sm font-medium text-muted-foreground">
            Your country of residence
          </h3>
          <div className="rounded-[var(--radius)] border border-primary/20 bg-primary/5 px-4 py-3 text-sm">
            <span className="font-medium">Auto-detected:</span>{" "}
            <span className="text-muted-foreground">
              {geoData?.detected_country.country_name} ({geoData?.detected_country.country_code})
            </span>
          </div>
          <button
            onClick={() => setStep("destination")}
            className="inline-flex w-full items-center justify-center gap-2 rounded-[var(--radius)] bg-primary px-4 py-3 text-sm font-medium text-primary-foreground transition-colors hover:opacity-90"
          >
            Continue with {geoData?.detected_country.country_name} <ArrowRight className="size-4" />
          </button>
        </div>
      )}

      {/* Step: destination */}
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
            destinations.map((d) => (
              <button
                key={d.code}
                onClick={() => selectDestination(d)}
                className="flex w-full items-center gap-4 rounded-[var(--radius)] border bg-card p-4 text-left transition-colors hover:bg-accent"
              >
                <span className="text-2xl">{d.flag}</span>
                <div className="flex-1">
                  <p className="font-medium">{d.name}</p>
                  <p className="text-xs text-muted-foreground">{d.currency}</p>
                </div>
                <ArrowRight className="size-4 text-muted-foreground" />
              </button>
            ))
          )}
        </div>
      )}

      {/* Step: visa type */}
      {step === "visa_type" && (
        <div className="space-y-3">
          <button onClick={goBack} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
            <ArrowLeft className="size-3.5" /> Back
          </button>
          <h3 className="text-sm font-medium text-muted-foreground">
            Visa type for <strong>{selectedDestination?.flag} {selectedDestination?.name}</strong>
          </h3>
          {visaTypes.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No visa types available.
            </p>
          ) : (
            visaTypes.map((v) => (
              <button
                key={v.code}
                onClick={() => selectVisaType(v)}
                className="flex w-full items-center gap-4 rounded-[var(--radius)] border bg-card p-4 text-left transition-colors hover:bg-accent"
              >
                <div className="flex-1">
                  <p className="font-medium">{v.name}</p>
                  <p className="text-xs text-muted-foreground">{v.description}</p>
                </div>
                <ArrowRight className="size-4 text-muted-foreground" />
              </button>
            ))
          )}
        </div>
      )}

      {/* Step: application type */}
      {step === "app_type" && (
        <div className="space-y-3">
          <button onClick={goBack} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
            <ArrowLeft className="size-3.5" /> Back
          </button>
          <h3 className="text-sm font-medium text-muted-foreground">
            Application type
          </h3>
          {appTypes.map((a) => (
            <button
              key={a.code}
              onClick={() => selectAppType(a)}
              className="flex w-full items-center gap-4 rounded-[var(--radius)] border bg-card p-4 text-left transition-colors hover:bg-accent"
            >
              <div className="flex-1">
                <p className="font-medium">{a.name}</p>
                <p className="text-xs text-muted-foreground">{a.description}</p>
              </div>
              <ArrowRight className="size-4 text-muted-foreground" />
            </button>
          ))}
        </div>
      )}

      {/* Step: review */}
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
                <span className="text-muted-foreground">From</span>
                <span className="font-medium">{geoData?.detected_country.country_name}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">To</span>
                <span className="font-medium">{selectedDestination?.flag} {selectedDestination?.name}</span>
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
