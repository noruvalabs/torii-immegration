"use client";

import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ArrowLeft,
  Check,
  Loader2,
  ArrowRight,
  Search,
  X,
  ChevronDown,
} from "lucide-react";
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
import { useCorridorCheckQuery } from "@/lib/queries/corridors";
import { useQueryClient } from "@tanstack/react-query";
import { updateProfile } from "@/lib/api/auth";
import {
  type Case,
  scopeCase,
} from "@/lib/api/cases";
import { CountrySelector } from "@/components/ui/country-selector";
import { CountryFlag } from "@/components/landing/country-flag";
import { ALL_COUNTRIES, matchCountry, isSameCountry } from "@/lib/countries";
import { cn, formatScopeLabel } from "@/lib/utils";

type CaseResult = Case;

const POPULAR_PASSPORTS = [
  { code: "BD", name: "Bangladesh" },
  { code: "IN", name: "India" },
  { code: "PH", name: "Philippines" },
  { code: "US", name: "United States" },
  { code: "GB", name: "United Kingdom" },
  { code: "CA", name: "Canada" },
  { code: "AU", name: "Australia" },
  { code: "PK", name: "Pakistan" },
  { code: "SG", name: "Singapore" },
  { code: "AE", name: "United Arab Emirates" },
  { code: "MY", name: "Malaysia" },
  { code: "DE", name: "Germany" },
];

/** Destination (with Nationality & Residence), then visa → app → review */
type Step = "destination" | "visa_type" | "app_type" | "review";

const STEP_ORDER: Step[] = ["destination", "visa_type", "app_type", "review"];

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
  const [step, setStep] = useState<Step>("destination");
  const [error, setError] = useState<string | null>(null);

  const [residenceCountry, setResidenceCountry] = useState<string>("");
  const [nationality, setNationality] = useState<string>("");
  const [differentResidence, setDifferentResidence] = useState<boolean>(false);
  const [selectedDestination, setSelectedDestination] = useState<Destination | null>(null);
  const [selectedVisaType, setSelectedVisaType] = useState<VisaType | null>(null);
  const [selectedAppType, setSelectedAppType] = useState<ApplicationType | null>(null);

  const [submitting, setSubmitting] = useState(false);
  const [visaFilter, setVisaFilter] = useState("");

  const barRef = useRef<HTMLDivElement>(null);
  const [passportOpen, setPassportOpen] = useState(false);
  const [destinationOpen, setDestinationOpen] = useState(false);
  const [passportSearch, setPassportSearch] = useState("");
  const [destinationSearch, setDestinationSearch] = useState("");

  const originParam =
    searchParams.get("origin") || searchParams.get("from") || searchParams.get("passport");
  const seededOriginRef = useRef(false);
  const seededFromProfileRef = useRef(false);

  const { data: geoData = null, isLoading: geoLoading } = useGeoDataQuery(Boolean(token));
  const { data: dynamicVisaTypes = null, isLoading: loadingVisaTypes } = useVisaTypesQuery(
    selectedDestination?.code,
  );
  const { data: dynamicAppTypes = null, isLoading: loadingAppTypes } = useApplicationTypesQuery(
    selectedDestination?.code,
    selectedVisaType?.code,
  );

  // Close dropdowns on click outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (barRef.current && !barRef.current.contains(e.target as Node)) {
        setPassportOpen(false);
        setDestinationOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const { data: corridorReview } = useCorridorCheckQuery(
    step === "review" && selectedDestination && selectedVisaType && selectedAppType
      ? {
          destination_code: selectedDestination.code,
          purpose_code: selectedVisaType.code,
          action_code: selectedAppType.code,
          nationality: nationality || null,
          residence_country: residenceCountry || null,
        }
      : null,
    token,
  );

  // Pre-seed nationality / residence if passed via URL (e.g. ?origin=PH or ?from=PH).
  // Explicit URL query parameters override profile defaults. This runs BEFORE profile seeding.
  useEffect(() => {
    if (!seededOriginRef.current && originParam) {
      const matched = matchCountry(originParam);
      if (matched?.code) {
        setNationality(matched.code);
        setResidenceCountry(matched.code);
        seededOriginRef.current = true;
      }
    }
  }, [originParam]);

  // Auto-select from user profile only if NOT specified via URL query parameter.
  // Wait until seededOriginRef is settled (URL param takes precedence).
  useEffect(() => {
    if (!seededFromProfileRef.current && user) {
      // If a URL origin param is present, skip profile seeding entirely.
      if (originParam) {
        seededFromProfileRef.current = true;
        return;
      }
      let natCode = "";
      let resCode = "";
      if (user.nationality && user.nationality.trim()) {
        const matched = matchCountry(user.nationality);
        if (matched?.code) {
          natCode = matched.code;
          setNationality(matched.code);
        }
      }
      if (user.current_country && user.current_country.trim()) {
        const matched = matchCountry(user.current_country);
        if (matched?.code) {
          resCode = matched.code;
          setResidenceCountry(matched.code);
        }
      }
      if (natCode && resCode && natCode !== resCode) {
        setDifferentResidence(true);
      } else if (natCode && !resCode) {
        setResidenceCountry(natCode);
      } else if (!natCode && resCode) {
        setNationality(resCode);
      }
      seededFromProfileRef.current = true;
    }
  }, [user, originParam]);

  const loading = geoLoading && !geoData;

  // Pre-seed destination if passed via URL (e.g., ?destination=GB or ?destination=UK or ?destination=JP)
  useEffect(() => {
    if (!seededDestinationRef.current && destinationParam && geoData?.destinations) {
      const cleanParam = destinationParam.trim();
      const matched = geoData.destinations.find(
        (d) =>
          d.code.toUpperCase() === cleanParam.toUpperCase() ||
          isSameCountry(d.code, cleanParam) ||
          d.name.toLowerCase() === cleanParam.toLowerCase() ||
          d.name.toLowerCase().replace(/\s+/g, "-") === cleanParam.toLowerCase(),
      );
      if (matched) {
        setSelectedDestination(matched);
        seededDestinationRef.current = true;
      }
    }
  }, [destinationParam, geoData]);

  const categoryParam = searchParams.get("category") || searchParams.get("visa");
  const seededCategoryRef = useRef(false);

  // Pre-seed visa category if passed via URL (e.g. ?category=medical)
  useEffect(() => {
    if (!seededCategoryRef.current && categoryParam && dynamicVisaTypes?.length) {
      const matched = dynamicVisaTypes.find(
        (v) =>
          v.code.toLowerCase() === categoryParam.toLowerCase() ||
          v.name.toLowerCase().includes(categoryParam.toLowerCase()),
      );
      if (matched) {
        setSelectedVisaType(matched);
        seededCategoryRef.current = true;
      }
    }
  }, [categoryParam, dynamicVisaTypes]);

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

  function selectDestination(d: Destination) {
    if (!nationality) {
      setError("Please select your passport country / nationality first.");
      return;
    }
    const finalResidence = differentResidence ? (residenceCountry || nationality) : nationality;
    if (!residenceCountry || !differentResidence) {
      setResidenceCountry(finalResidence);
    }
    setError(null);
    setSelectedDestination(d);
    setSelectedVisaType(null);
    setSelectedAppType(null);
    setVisaFilter("");
    setStep("visa_type");

    if (token) {
      try {
        const natName = matchCountry(nationality).name;
        const resName = matchCountry(finalResidence).name;
        void updateProfile(token, {
          nationality: natName,
          current_country: resName,
        });
      } catch {
        // Profile save is best-effort; scoping can continue.
      }
    }
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
      void queryClient.invalidateQueries({ queryKey: caseKeys.list() });
      router.push(`/cases/${result.id}`);
    } catch (e) {
      setSubmitting(false);
      setError(e instanceof Error ? e.message : "Failed to create case");
    }
  }

  const destinationFlag =
    selectedDestination
      ? selectedDestination.flag || matchCountry(selectedDestination.code).flag || "🌐"
      : "";
  const residenceLabel = residenceCountry ? matchCountry(residenceCountry).name : "";
  const nationalityLabel = nationality ? matchCountry(nationality).name : "";

  const destinations = useMemo(
    () => geoData?.destinations ?? [],
    [geoData?.destinations],
  );

  const filteredPassports = useMemo(() => {
    const q = passportSearch.trim().toLowerCase();
    if (!q) {
      const popularCodes = new Set(POPULAR_PASSPORTS.map((p) => p.code));
      const popularList = POPULAR_PASSPORTS.map((p) => matchCountry(p.code));
      const rest = ALL_COUNTRIES.filter((c) => !popularCodes.has(c.code));
      return [...popularList, ...rest];
    }
    return ALL_COUNTRIES.filter(
      (c) => c.name.toLowerCase().includes(q) || c.code.toLowerCase() === q,
    );
  }, [passportSearch]);

  const filteredDestinations = useMemo(() => {
    const q = destinationSearch.trim().toLowerCase();
    if (!q) return destinations;
    return destinations.filter(
      (d) =>
        d.name.toLowerCase().includes(q) ||
        d.code.toLowerCase() === q ||
        d.currency.toLowerCase().includes(q),
    );
  }, [destinations, destinationSearch]);

  if (loading) {
    return (
      <div className="mx-auto max-w-lg space-y-6 py-12 text-center">
        <Loader2 className="mx-auto size-8 animate-spin text-muted-foreground" />
        <p className="text-sm text-muted-foreground">Loading destinations...</p>
      </div>
    );
  }

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
          {residenceLabel && selectedDestination
            ? `Apply for a visa from ${residenceLabel} to ${selectedDestination.name}.`
            : residenceLabel
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

      {/* Sleek Atlys-style Unified Route Bar (Passport + Destination) */}
      {step === "destination" && (
        <div className="space-y-6">
          <div ref={barRef} className="space-y-2">
            {/* Main Rounded Bar Container (matches image) */}
            <div className="relative z-30 rounded-2xl border border-border/80 bg-card p-1.5 sm:p-2 shadow-xl backdrop-blur-xl dark:border-white/10 dark:bg-[#101424]">
              <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr_auto] gap-2 items-center">
                {/* 1. Passport Country Segment */}
                <div className="relative">
                  <button
                    type="button"
                    onClick={() => {
                      setPassportOpen(!passportOpen);
                      setDestinationOpen(false);
                    }}
                    className={cn(
                      "w-full flex items-center justify-between py-2 px-3 rounded-xl text-left transition-all hover:bg-muted/50 cursor-pointer",
                      passportOpen && "bg-muted/70 ring-1 ring-primary/50",
                    )}
                  >
                    <div className="flex flex-col space-y-0.5 min-w-0">
                      <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
                        Passport Country
                      </span>
                      <div className="flex items-center gap-2 truncate">
                        {nationality ? (
                          <>
                            <CountryFlag code={nationality} className="size-4.5 shrink-0 rounded-xs shadow-xs" />
                            <span className="font-bold text-sm text-foreground truncate">
                              {matchCountry(nationality).name}
                            </span>
                          </>
                        ) : (
                          <span className="text-sm font-medium text-muted-foreground">
                            Select passport country...
                          </span>
                        )}
                      </div>
                    </div>
                    <ChevronDown
                      className={cn(
                        "size-4 text-muted-foreground shrink-0 transition-transform duration-200 ml-2",
                        passportOpen && "rotate-180 text-foreground",
                      )}
                    />
                  </button>

                  {/* Passport Dropdown Menu */}
                  {passportOpen && (
                    <div className="absolute left-0 top-full mt-2 w-80 max-w-[calc(100vw-2rem)] z-50 rounded-xl border border-border/80 bg-popover text-popover-foreground p-2 shadow-2xl backdrop-blur-2xl animate-in fade-in slide-in-from-top-1 duration-150 text-left">
                      <div className="relative mb-2">
                        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground" />
                        <input
                          type="text"
                          value={passportSearch}
                          onChange={(e) => setPassportSearch(e.target.value)}
                          placeholder="Search passport country..."
                          className="w-full rounded-lg bg-muted/50 pl-8 pr-3 py-1.5 text-xs text-foreground placeholder:text-muted-foreground border border-border outline-none focus:ring-1 focus:ring-primary"
                          autoFocus
                        />
                      </div>
                      <div className="px-2 py-1 text-[10px] font-bold uppercase text-muted-foreground tracking-wider">
                        {passportSearch.trim() ? "Search Results" : "Countries"}
                      </div>
                      <div className="max-h-60 overflow-y-auto space-y-0.5 pr-1">
                        {filteredPassports.map((p) => {
                          const isSelected = p.code === nationality;
                          return (
                            <button
                              key={p.code}
                              type="button"
                              onClick={() => {
                                setNationality(p.code);
                                if (!differentResidence) {
                                  setResidenceCountry(p.code);
                                }
                                setPassportOpen(false);
                                setPassportSearch("");
                              }}
                              className={cn(
                                "w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-colors cursor-pointer",
                                isSelected
                                  ? "bg-primary text-primary-foreground font-semibold"
                                  : "text-foreground hover:bg-muted",
                              )}
                            >
                              <div className="flex items-center gap-2.5 truncate">
                                <CountryFlag code={p.code} className="size-4 shrink-0 rounded-xs" />
                                <span className="truncate">{p.name}</span>
                              </div>
                              {isSelected && <Check className="size-3.5 shrink-0" />}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>

                {/* Vertical Divider */}
                <div className="hidden md:block h-8 w-px bg-border/60 dark:bg-white/10" />

                {/* 2. Destination Country Segment */}
                <div className="relative">
                  <button
                    type="button"
                    onClick={() => {
                      setDestinationOpen(!destinationOpen);
                      setPassportOpen(false);
                    }}
                    className={cn(
                      "w-full flex items-center justify-between py-2 px-3 rounded-xl text-left transition-all hover:bg-muted/50 cursor-pointer",
                      destinationOpen && "bg-muted/70 ring-1 ring-primary/50",
                    )}
                  >
                    <div className="flex flex-col space-y-0.5 min-w-0">
                      <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
                        Destination Country
                      </span>
                      <div className="flex items-center gap-2 truncate">
                        {selectedDestination ? (
                          <>
                            <CountryFlag code={selectedDestination.code} className="size-4.5 shrink-0 rounded-xs shadow-xs" />
                            <span className="font-bold text-sm text-foreground truncate">
                              {selectedDestination.name}
                            </span>
                          </>
                        ) : (
                          <span className="text-sm font-medium text-muted-foreground">
                            Select destination country...
                          </span>
                        )}
                      </div>
                    </div>
                    <ChevronDown
                      className={cn(
                        "size-4 text-muted-foreground shrink-0 transition-transform duration-200 ml-2",
                        destinationOpen && "rotate-180 text-foreground",
                      )}
                    />
                  </button>

                  {/* Destination Dropdown Menu */}
                  {destinationOpen && (
                    <div className="absolute left-0 md:left-auto md:right-0 top-full mt-2 w-80 max-w-[calc(100vw-2rem)] z-50 rounded-xl border border-border/80 bg-popover text-popover-foreground p-2 shadow-2xl backdrop-blur-2xl animate-in fade-in slide-in-from-top-1 duration-150 text-left">
                      {destinations.length > 5 && (
                        <div className="relative mb-2">
                          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground" />
                          <input
                            type="text"
                            value={destinationSearch}
                            onChange={(e) => setDestinationSearch(e.target.value)}
                            placeholder="Search destination..."
                            className="w-full rounded-lg bg-muted/50 pl-8 pr-3 py-1.5 text-xs text-foreground placeholder:text-muted-foreground border border-border outline-none focus:ring-1 focus:ring-primary"
                            autoFocus
                          />
                        </div>
                      )}
                      <div className="px-2 py-1 text-[10px] font-bold uppercase text-muted-foreground tracking-wider">
                        Supported Destinations ({filteredDestinations.length})
                      </div>
                      <div className="max-h-60 overflow-y-auto space-y-0.5 pr-1">
                        {filteredDestinations.length === 0 ? (
                          <p className="px-3 py-2 text-xs text-muted-foreground">No destinations found</p>
                        ) : (
                          filteredDestinations.map((d) => {
                            const isSelected = selectedDestination?.code === d.code;
                            return (
                              <button
                                key={d.code}
                                type="button"
                                onClick={() => {
                                  setSelectedDestination(d);
                                  setDestinationOpen(false);
                                  setDestinationSearch("");
                                }}
                                className={cn(
                                  "w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-colors cursor-pointer",
                                  isSelected
                                    ? "bg-primary text-primary-foreground font-semibold"
                                    : "text-foreground hover:bg-muted",
                                )}
                              >
                                <div className="flex items-center gap-2.5 truncate">
                                  <CountryFlag code={d.code} className="size-4 shrink-0 rounded-xs" />
                                  <span className="truncate">{d.name}</span>
                                </div>
                                <div className="flex items-center gap-2">
                                  <span className={cn("text-[11px]", isSelected ? "text-primary-foreground/80" : "text-muted-foreground")}>
                                    {d.currency}
                                  </span>
                                  {isSelected && <Check className="size-3.5 shrink-0" />}
                                </div>
                              </button>
                            );
                          })
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {/* 3. Apply for Visa Solid Pill Button */}
                <button
                  type="button"
                  onClick={() => {
                    if (!nationality) {
                      setPassportOpen(true);
                      setError("Please select your passport country first.");
                      return;
                    }
                    if (!selectedDestination) {
                      setDestinationOpen(true);
                      setError("Please select a destination country.");
                      return;
                    }
                    selectDestination(selectedDestination);
                  }}
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-6 py-3.5 text-sm font-semibold text-primary-foreground shadow-sm transition-all hover:opacity-90 active:scale-[0.98] shrink-0 cursor-pointer"
                >
                  Apply for Visa
                  <ArrowRight className="size-4" />
                </button>
              </div>
            </div>

            {/* Living in different country toggle */}
            <div className="flex items-center justify-between px-2 pt-1">
              <label className="inline-flex items-center gap-2 cursor-pointer text-xs font-medium text-muted-foreground hover:text-foreground select-none">
                <input
                  type="checkbox"
                  checked={differentResidence}
                  onChange={(e) => {
                    const checked = e.target.checked;
                    setDifferentResidence(checked);
                    if (!checked && nationality) {
                      setResidenceCountry(nationality);
                    }
                  }}
                  className="size-3.5 rounded border-border text-primary focus:ring-primary/20 accent-primary cursor-pointer"
                />
                <span>Living in a different country than your passport?</span>
              </label>
              {nationality && (
                <span className="text-xs text-muted-foreground hidden sm:inline">
                  Current Residence: <strong className="text-foreground">{residenceLabel}</strong>
                </span>
              )}
            </div>

            {/* Residence country selector dropdown if living abroad */}
            {differentResidence && (
              <div className="rounded-xl border bg-card p-4 shadow-xs space-y-2 animate-in fade-in duration-150">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-foreground">
                    Current Country of Residence
                  </span>
                  {user?.current_country &&
                    residenceCountry &&
                    residenceCountry === matchCountry(user.current_country).code && (
                      <span className="text-[10px] font-medium text-primary bg-primary/10 px-2 py-0.5 rounded-full">
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
            )}
          </div>

          {/* Quick-Pick Supported Destinations Grid */}
          <div className="pt-4 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-foreground">
                  Explore Destinations
                </h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Or select a destination directly to get started
                </p>
              </div>
              <span className="text-xs text-muted-foreground">
                {destinations.length} destinations
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {destinations.map((d) => {
                const isSelected = selectedDestination?.code === d.code;
                return (
                  <button
                    key={d.code}
                    type="button"
                    onClick={() => {
                      setSelectedDestination(d);
                      selectDestination(d);
                    }}
                    className={cn(
                      "flex items-center gap-3.5 rounded-xl border bg-card p-4 text-left transition-all hover:bg-accent hover:border-primary/40 group cursor-pointer",
                      isSelected && "border-primary/60 bg-primary/5 ring-1 ring-primary/40",
                    )}
                  >
                    <CountryFlag code={d.code} className="size-8 shrink-0 shadow-xs rounded-xs" />
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-sm text-foreground group-hover:text-primary transition-colors truncate">
                        {d.name}
                      </p>
                      <p className="text-xs text-muted-foreground">{d.currency}</p>
                    </div>
                    <ArrowRight className="size-4 text-muted-foreground group-hover:text-primary transition-colors shrink-0" />
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {step === "visa_type" && (
        <div className="space-y-3">
          <button onClick={goBack} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
            <ArrowLeft className="size-3.5" /> Back
          </button>
          <h3 className="text-sm font-medium text-muted-foreground flex items-center gap-1.5 flex-wrap">
            <span>Visa type for</span>
            {selectedDestination?.code && (
              <CountryFlag code={selectedDestination.code} className="size-4 shrink-0 inline-block" />
            )}
            <strong className="text-foreground">{selectedDestination?.name}</strong>
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
        <div className="space-y-5">
          <button
            onClick={goBack}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="size-3.5" /> Back
          </button>

          <div className="space-y-1">
            <h3 className="text-lg font-bold tracking-tight text-foreground">
              Confirm application details
            </h3>
            <p className="text-xs text-muted-foreground">
              Review your selection before screening your visa eligibility.
            </p>
          </div>

          {/* Details Card */}
          <Card className="rounded-xl border border-border/90 dark:border-slate-800 bg-card shadow-xs overflow-hidden">
            <CardContent className="p-4 sm:p-5 divide-y divide-border/60">
              <div className="flex items-center justify-between py-2.5 first:pt-0">
                <span className="text-xs text-muted-foreground">Residence</span>
                <span className="text-xs sm:text-sm font-semibold text-foreground">{residenceLabel}</span>
              </div>
              <div className="flex items-center justify-between py-2.5">
                <span className="text-xs text-muted-foreground">Nationality</span>
                <span className="text-xs sm:text-sm font-semibold text-foreground">{nationalityLabel}</span>
              </div>
              <div className="flex items-center justify-between py-2.5">
                <span className="text-xs text-muted-foreground">Destination</span>
                <span className="text-xs sm:text-sm font-semibold text-foreground inline-flex items-center gap-1.5">
                  <span>{destinationFlag}</span>
                  <span>{selectedDestination?.name}</span>
                </span>
              </div>
              <div className="flex items-center justify-between py-2.5">
                <span className="text-xs text-muted-foreground">Visa Type</span>
                <span className="text-xs sm:text-sm font-semibold text-primary">{selectedVisaType?.name}</span>
              </div>
              <div className="flex items-center justify-between py-2.5">
                <span className="text-xs text-muted-foreground">Application Category</span>
                <span className="text-xs sm:text-sm font-semibold text-foreground">{selectedAppType?.name}</span>
              </div>
              {corridorReview?.status === "completed" && (
                <div className="flex items-center justify-between py-2.5 last:pb-0 bg-emerald-500/5 -mx-4 sm:-mx-5 px-4 sm:px-5">
                  <span className="text-xs text-muted-foreground">Official Verification</span>
                  <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 inline-flex items-center gap-1">
                    <Check className="size-3.5" /> Verified by Official Embassy Sources
                  </span>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Next Steps List */}
          <div className="rounded-xl border border-border/80 dark:border-slate-800 bg-muted/20 p-4 sm:p-5 text-left space-y-3">
            <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
              What happens next
            </p>
            <div className="space-y-2.5">
              <div className="flex items-start gap-3">
                <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[10px] font-bold text-primary mt-0.5">
                  1
                </span>
                <div>
                  <p className="text-xs font-semibold text-foreground">Eligibility Screening</p>
                  <p className="text-[11px] text-muted-foreground">Answer 5 essential criteria questions to compute your approval likelihood.</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[10px] font-bold text-primary mt-0.5">
                  2
                </span>
                <div>
                  <p className="text-xs font-semibold text-foreground">Secure Payment</p>
                  <p className="text-[11px] text-muted-foreground">Pay consular service fee via bKash, Nagad, or Debit/Credit Card.</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[10px] font-bold text-primary mt-0.5">
                  3
                </span>
                <div>
                  <p className="text-xs font-semibold text-foreground">Intake &amp; Document Checklist</p>
                  <p className="text-[11px] text-muted-foreground">Fill in questionnaire details and upload required supporting proofs.</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[10px] font-bold text-primary mt-0.5">
                  4
                </span>
                <div>
                  <p className="text-xs font-semibold text-foreground">Consular Submission &amp; Filing</p>
                  <p className="text-[11px] text-muted-foreground">Our team registers your dossier and books your IVAC appointment.</p>
                </div>
              </div>
            </div>
          </div>

          <button
            onClick={() => void createCase()}
            disabled={submitting}
            className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-5 py-3.5 text-sm font-semibold text-primary-foreground shadow-sm transition-all hover:opacity-95 disabled:pointer-events-none disabled:opacity-50"
          >
            {submitting ? (
              <>
                <Loader2 className="size-4 animate-spin" /> Starting application…
              </>
            ) : (
              <>
                Check Visa Eligibility &amp; Start <ArrowRight className="size-4" />
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
