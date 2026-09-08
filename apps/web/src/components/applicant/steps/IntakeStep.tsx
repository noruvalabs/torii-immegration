"use client";

import { useEffect, useRef, useState, useMemo } from "react";
import {
  Check,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  Search,
  ArrowRight,
  CheckCircle2,
  ListChecks,
  LayoutGrid,
  AlertCircle,
  AlertTriangle,
  ShieldCheck,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ALL_COUNTRIES, matchCountry, searchCountries, type Country } from "@/lib/countries";
import type { IntakeState, IntakeQuestion, User } from "./types";
import { findQuestionByKey } from "./types";

type IntakeStepProps = {
  state: IntakeState;
  profile: User | null;
  onAnswer: (key: string, value: unknown) => void;
  onProceedToEligibility?: () => void;
  targetKey?: string | null;
  targetTimestamp?: number;
};

/** Map profile country names to common ISO codes used in intake enums. */
const COUNTRY_ALIASES: Record<string, string> = {
  japan: "JP",
  "united states": "US",
  "united kingdom": "UK",
  canada: "CA",
  australia: "AU",
  germany: "DE",
  france: "FR",
  singapore: "SG",
  "south korea": "KR",
  korea: "KR",
  bangladesh: "BD",
  india: "IN",
  pakistan: "PK",
  china: "CN",
  philippines: "PH",
  vietnam: "VN",
  nepal: "NP",
  "sri lanka": "LK",
};

function matchEnumOption(value: string, options: string[]): string | null {
  if (options.includes(value)) return value;
  const upper = value.toUpperCase();
  const byCode = options.find((o) => o.toUpperCase() === upper);
  if (byCode) return byCode;
  const byName = options.find((o) => o.toLowerCase() === value.toLowerCase());
  if (byName) return byName;
  const alias = COUNTRY_ALIASES[value.toLowerCase()];
  if (alias) {
    const hit = options.find((o) => o.toUpperCase() === alias || o === alias);
    if (hit) return hit;
  }
  return null;
}

const PROFILE_ALIASES: Record<string, keyof User> = {
  full_name: "full_name",
  applicant_name: "full_name",
  name: "full_name",
  legal_name: "full_name",
  full_legal_name: "full_name",

  nationality: "nationality",
  citizenship: "nationality",
  country_of_citizenship: "nationality",
  country_of_nationality: "nationality",

  passport_number: "passport_number",
  passport_no: "passport_number",
  passport_num: "passport_number",
  travel_document_number: "passport_number",

  passport_expiry: "passport_expiry",
  passport_expiry_date: "passport_expiry",
  passport_expiration_date: "passport_expiry",
  passport_valid_until: "passport_expiry",

  date_of_birth: "date_of_birth",
  dob: "date_of_birth",
  birth_date: "date_of_birth",
  applicant_dob: "date_of_birth",
  applicant_date_of_birth: "date_of_birth",

  current_country: "current_country",
  current_residence_country: "current_country",
  current_location_country: "current_country",
  residence_country: "current_country",
  country_of_residence: "current_country",
};

function getProfileValueForQuestion(key: string, prompt: string, profile: User): string | null {
  const normKey = key.toLowerCase();
  const normPrompt = prompt.toLowerCase();

  // Direct alias check
  const mappedField = PROFILE_ALIASES[normKey];
  if (mappedField) {
    const val = profile[mappedField];
    if (val && typeof val === "string" && val.trim()) return val.trim();
  }

  // Fuzzy match on key and prompt
  if (
    normKey.includes("date_of_birth") ||
    normKey === "dob" ||
    normKey.includes("birth_date") ||
    (normPrompt.includes("date of birth") && !normPrompt.includes("father") && !normPrompt.includes("mother") && !normPrompt.includes("spouse") && !normPrompt.includes("child"))
  ) {
    if (profile.date_of_birth?.trim()) return profile.date_of_birth.trim();
  }

  if (
    (normKey.includes("passport") && (normKey.includes("expiry") || normKey.includes("expiration"))) ||
    (normPrompt.includes("passport") && (normPrompt.includes("expiry") || normPrompt.includes("expiration")))
  ) {
    if (profile.passport_expiry?.trim()) return profile.passport_expiry.trim();
  }

  if (
    (normKey.includes("passport") && (normKey.includes("number") || normKey.includes("no") || normKey.includes("num"))) ||
    normKey === "passport_number" ||
    (normPrompt.includes("passport number") || normPrompt.includes("passport no"))
  ) {
    if (profile.passport_number?.trim()) return profile.passport_number.trim();
  }

  if (
    normKey === "full_name" ||
    normKey === "applicant_name" ||
    (normPrompt.includes("full name") && !normPrompt.includes("father") && !normPrompt.includes("mother") && !normPrompt.includes("spouse") && !normPrompt.includes("employer"))
  ) {
    if (profile.full_name?.trim()) return profile.full_name.trim();
  }

  if (
    normKey === "nationality" ||
    normKey === "citizenship" ||
    (normPrompt.includes("nationality") && !normPrompt.includes("spouse") && !normPrompt.includes("father"))
  ) {
    if (profile.nationality?.trim()) return profile.nationality.trim();
  }

  if (
    normKey.includes("residence_country") ||
    normKey.includes("current_country") ||
    normKey.includes("location_country")
  ) {
    if (profile.current_country?.trim()) return profile.current_country.trim();
  }

  return null;
}

function SectionSourceBanner({ questions }: { questions: IntakeState["questions"] }) {
  const sources = useMemo(() => {
    const map = new Map<string, { authority: string; title: string; url: string }>();
    for (const q of questions) {
      const cit = q.citation as { authority?: string; title?: string; url?: string } | null | undefined;
      if (cit?.url) {
        if (!map.has(cit.url)) {
          map.set(cit.url, {
            authority: cit.authority || "Official Government Authority",
            title: cit.title || "Statutory Immigration Standard",
            url: cit.url,
          });
        }
      }
    }
    return Array.from(map.values());
  }, [questions]);

  if (sources.length === 0) return null;

  return (
    <div className="rounded-lg border border-primary/20 bg-primary/5 p-3 text-xs shadow-2xs space-y-2">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2">
          <ShieldCheck className="size-4 text-primary shrink-0" />
          <div>
            <span className="font-semibold text-foreground text-xs">
              Official Statutory Authority &amp; Verified Legal Basis
            </span>
            <span className="text-[11px] text-muted-foreground ml-1.5 hidden sm:inline">
              (Questions in this section are verified against statutory government standards)
            </span>
          </div>
        </div>
        <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-700 dark:text-emerald-300 bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 rounded-full">
          ✓ Verified Legal Source
        </span>
      </div>

      <div className="flex items-center gap-2 flex-wrap pt-1 border-t border-border/40">
        <span className="text-[11px] font-medium text-muted-foreground">Official Government Sources:</span>
        {sources.map((src, i) => (
          <a
            key={i}
            href={src.url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 rounded-md border border-border/80 bg-background hover:bg-accent px-2.5 py-1 text-[11px] font-medium text-foreground hover:text-primary transition-colors shadow-2xs"
            title={`${src.title} — ${src.authority}`}
          >
            <span>{src.authority}</span>
            <ExternalLink className="size-3 text-muted-foreground" />
          </a>
        ))}
      </div>
    </div>
  );
}

export function IntakeStep({
  state,
  profile,
  onAnswer,
  onProceedToEligibility,
  targetKey,
  targetTimestamp,
}: IntakeStepProps) {
  const [drafts, setDrafts] = useState<Record<string, unknown>>({});
  const [fieldErrors, setFieldErrors] = useState<Record<string, string | null>>({});
  const [activeSection, setActiveSection] = useState<string | null>(null);
  const [enumSearch, setEnumSearch] = useState<Record<string, string>>({});
  const [openSelectorKey, setOpenSelectorKey] = useState<string | null>(null);
  const [viewAll, setViewAll] = useState<boolean>(false);
  const [highlightedKey, setHighlightedKey] = useState<string | null>(null);

  const onAnswerRef = useRef(onAnswer);
  onAnswerRef.current = onAnswer;
  const autoSubmittedRef = useRef<Set<string>>(new Set());

  function validateField(q: (typeof state.questions)[number], value: unknown): string | null {
    const isOptional = q.required === false;
    if (value === undefined || value === null || (typeof value === "string" && value.trim() === "")) {
      return isOptional ? null : "This field is required.";
    }

    if (q.type === "integer") {
      const num = typeof value === "number" ? value : Number(value);
      if (isNaN(num) || !Number.isInteger(num)) {
        return "Please enter a valid whole number.";
      }
      if (q.min_value !== undefined && q.min_value !== null && num < q.min_value) {
        return `Value must be at least ${q.min_value}.`;
      }
      if (q.max_value !== undefined && q.max_value !== null && num > q.max_value) {
        return `Value must be at most ${q.max_value}.`;
      }
      return null;
    }

    if (q.type === "string") {
      const str = String(value).trim();
      if (q.min_length !== undefined && q.min_length !== null && str.length < q.min_length) {
        return `Must be at least ${q.min_length} characters.`;
      }
      if (q.max_length !== undefined && q.max_length !== null && str.length > q.max_length) {
        return `Must be at most ${q.max_length} characters.`;
      }
      return null;
    }

    if (q.type === "date") {
      const str = String(value).trim();
      if (!/^\d{4}-\d{2}-\d{2}$/.test(str)) {
        return "Please enter a valid date in YYYY-MM-DD format.";
      }
      const d = new Date(str);
      if (isNaN(d.getTime())) {
        return "Please enter a valid calendar date.";
      }
      return null;
    }

    if (q.type === "enum" && q.options && q.options.length > 0) {
      const str = String(value).trim();
      if (!q.options.includes(str)) {
        return "Please choose a valid option.";
      }
      return null;
    }

    return null;
  }

  useEffect(() => {
    if (!profile) return;
    const toAutoFill: Record<string, unknown> = {};
    for (const q of state.questions) {
      if (state.answers[q.key] !== undefined || autoSubmittedRef.current.has(q.key)) continue;
      let val = getProfileValueForQuestion(q.key, q.prompt, profile);
      if (val && q.type === "enum" && q.options?.length) {
        val = matchEnumOption(val, q.options);
      }
      if (val) toAutoFill[q.key] = val;
    }
    if (Object.keys(toAutoFill).length > 0) {
      setDrafts((prev) => ({ ...prev, ...toAutoFill }));
      for (const [key, val] of Object.entries(toAutoFill)) {
        if (val !== undefined) {
          autoSubmittedRef.current.add(key);
          void onAnswerRef.current(key, val);
        }
      }
    }
  }, [profile, state.questions, state.answers]);

  // Group questions by section if present, or assign defaults
  const sectionsMap = useMemo(() => {
    const map = new Map<string, IntakeQuestion[]>();
    for (const q of state.questions) {
      const sec = q.section || "General Details";
      if (!map.has(sec)) map.set(sec, []);
      map.get(sec)!.push(q);
    }
    return map;
  }, [state.questions]);

  const sectionKeys = useMemo(() => Array.from(sectionsMap.keys()), [sectionsMap]);

  // Compute first incomplete section so users are automatically taken to unanswered fields
  const firstIncompleteSection = useMemo(() => {
    for (const sec of sectionKeys) {
      const qs = sectionsMap.get(sec) || [];
      const answered = qs.filter((q) => state.answers[q.key] !== undefined).length;
      if (answered < qs.length) return sec;
    }
    return sectionKeys[0] ?? null;
  }, [sectionKeys, sectionsMap, state.answers]);

  // Switch to targetKey section, smoothly scroll to question, and highlight
  useEffect(() => {
    if (targetKey) {
      const q = findQuestionByKey(state.questions, targetKey);
      if (q) {
        if (q.section && sectionKeys.includes(q.section)) {
          setActiveSection(q.section);
        }
        setHighlightedKey(q.key);

        const scrollTimer = setTimeout(() => {
          const el = document.getElementById(`question-${q.key}`);
          if (el) {
            el.scrollIntoView({ behavior: "smooth", block: "center" });
            const input = el.querySelector<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>(
              "input, select, textarea"
            );
            if (input) {
              input.focus({ preventScroll: true });
            }
          }
        }, 150);

        const fadeTimer = setTimeout(() => {
          setHighlightedKey((prev) => (prev === q.key ? null : prev));
        }, 6000);

        return () => {
          clearTimeout(scrollTimer);
          clearTimeout(fadeTimer);
        };
      }
    }
  }, [targetKey, targetTimestamp, state.questions, sectionKeys]);

  const currentSectionKey = useMemo(() => {
    if (activeSection && sectionKeys.includes(activeSection)) {
      return activeSection;
    }
    return firstIncompleteSection ?? sectionKeys[0] ?? "General Details";
  }, [activeSection, sectionKeys, firstIncompleteSection]);

  const currentSectionIndex = sectionKeys.indexOf(currentSectionKey);

  function handleChange(key: string, value: unknown) {
    setDrafts((prev) => ({ ...prev, [key]: value }));
    if (fieldErrors[key]) {
      const q = state.questions.find((item) => item.key === key);
      if (q) {
        const err = validateField(q, value);
        setFieldErrors((prev) => ({ ...prev, [key]: err }));
      }
    }
  }

  async function handleSubmit(key: string) {
    if (drafts[key] !== undefined) {
      const raw = drafts[key];
      const q = state.questions.find((item) => item.key === key);
      if (!q) return;

      let valToSend: unknown = raw;
      if (q.type === "integer") {
        if (typeof raw === "string") {
          if (raw.trim() === "") {
            valToSend = q.required === false ? null : "";
          } else {
            const parsed = Number.parseInt(raw, 10);
            valToSend = Number.isNaN(parsed) ? raw : parsed;
          }
        }
      } else if (typeof raw === "string" && raw.trim() === "") {
        valToSend = q.required === false ? null : "";
      }

      const clientError = validateField(q, valToSend);
      if (clientError) {
        setFieldErrors((prev) => ({ ...prev, [key]: clientError }));
        return;
      }

      setFieldErrors((prev) => ({ ...prev, [key]: null }));

      try {
        await onAnswer(key, valToSend);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Invalid answer provided.";
        setFieldErrors((prev) => ({ ...prev, [key]: msg }));
      }
    }
  }

  async function handleDirectAnswer(key: string, value: unknown) {
    setDrafts((prev) => {
      const next = { ...prev };
      delete next[key];
      return next;
    });
    setFieldErrors((prev) => ({ ...prev, [key]: null }));
    try {
      await onAnswer(key, value);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Invalid selection.";
      setFieldErrors((prev) => ({ ...prev, [key]: msg }));
    }
  }

  // Clear drafts that have successfully synced to state.answers
  useEffect(() => {
    setDrafts((prev) => {
      let changed = false;
      const next = { ...prev };
      for (const k of Object.keys(next)) {
        if (state.answers[k] !== undefined && state.answers[k] === next[k]) {
          delete next[k];
          changed = true;
        }
      }
      return changed ? next : prev;
    });
  }, [state.answers]);

  const pct = state.progress.total > 0
    ? Math.round((state.progress.answered / state.progress.total) * 100)
    : 0;

  const currentQuestions = sectionsMap.get(currentSectionKey) || state.questions;
  const currentRequired = currentQuestions.filter((q) => q.required !== false);
  const currentAnsweredCount = currentQuestions.filter((q) => state.answers[q.key] !== undefined && state.answers[q.key] !== "").length;
  const currentAnsweredRequired = currentRequired.filter((q) => state.answers[q.key] !== undefined && state.answers[q.key] !== "").length;
  const isCurrentSectionComplete = currentRequired.length > 0
    ? currentAnsweredRequired >= currentRequired.length
    : currentQuestions.every((q) => state.answers[q.key] !== undefined);
  const remainingInCurrent = currentRequired.length > 0
    ? Math.max(0, currentRequired.length - currentAnsweredRequired)
    : Math.max(0, currentQuestions.length - currentAnsweredCount);

  function optionLabel(q: (typeof state.questions)[number], option: string): string {
    // The printed wording where the form has one; otherwise the value made readable.
    return q.option_labels?.[option] ?? option.replaceAll("_", " ");
  }

  function renderQuestion(q: (typeof state.questions)[number]) {
    const current = (drafts[q.key] !== undefined ? drafts[q.key] : state.answers[q.key]) as string | number | boolean | undefined;
    const hasOptions = q.type === "enum" && q.options && q.options.length > 0;
    const optionsCount = q.options?.length ?? 0;
    const isLongEnum = hasOptions && optionsCount > 5;
    const searchVal = enumSearch[q.key] || "";
    const filteredOptions = isLongEnum && searchVal
      ? q.options!.filter((opt) =>
          `${opt} ${q.option_labels?.[opt] ?? ""}`.toLowerCase().includes(searchVal.toLowerCase()),
        )
      : q.options || [];

    const isDateInput =
      q.type === "date" ||
      ((q.key.includes("date") ||
        q.key.includes("expiry") ||
        q.key.includes("expiration") ||
        q.key === "dob" ||
        q.key.includes("date_of_birth") ||
        q.key.includes("birth_date") ||
        q.prompt.toLowerCase().includes("yyyy-mm-dd") ||
        q.prompt.toLowerCase().includes("date of birth") ||
        q.prompt.toLowerCase().includes("expiry date")) &&
        !q.key.includes("place") &&
        !q.prompt.toLowerCase().includes("where were you born") &&
        !q.prompt.toLowerCase().includes("place of birth"));

    const isFullWidth = hasOptions && optionsCount > 8;

    const isHighlighted = q.key === highlightedKey;

    const isOptional = q.required === false;

    const fieldError = fieldErrors[q.key];

    return (
      <Card
        key={q.key}
        id={`question-${q.key}`}
        className={`p-4 flex flex-col justify-between transition-all hover:border-primary/40 bg-card shadow-sm ${
          isFullWidth ? "col-span-1 md:col-span-2" : "col-span-1"
        } ${
          fieldError
            ? "border-rose-500 ring-2 ring-rose-500/20 bg-rose-500/[0.02] shadow-sm"
            : isHighlighted
              ? "ring-2 ring-blue-500 border-blue-500 bg-blue-500/5 shadow-md"
              : state.answers[q.key] === undefined && !isOptional
                ? "border-amber-500/30 ring-1 ring-amber-500/10"
                : ""
        }`}
      >
        <div className="space-y-2">
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-1.5 flex-wrap">
              <label className={`text-xs font-semibold leading-snug ${fieldError ? "text-rose-700 dark:text-rose-400" : "text-foreground"}`}>
                {q.prompt}
                {!isOptional && <span className="ml-1 text-[var(--color-danger)] font-bold">*</span>}
              </label>
              {isHighlighted && (
                <span className="text-[10px] font-semibold text-blue-600 dark:text-blue-400 bg-blue-500/10 px-1.5 py-0.5 rounded border border-blue-500/30 animate-pulse">
                  Target Field
                </span>
              )}
              {isOptional && !q.hint && (
                <span className="text-[10px] font-medium text-muted-foreground bg-muted/80 px-1.5 py-0.5 rounded border border-border/50">
                  Optional
                </span>
              )}
              {q.hint && (
                <span className="text-[10px] font-medium text-primary bg-primary/10 px-1.5 py-0.5 rounded border border-primary/20">
                  On your form
                </span>
              )}
            </div>
          </div>

          {/* Names the box this answer fills, so leaving it blank is a visible choice
              rather than an invisible gap on a sheet the applicant signs. */}
          {q.hint && <p className="text-[11px] leading-snug text-muted-foreground">{q.hint}</p>}

          {(() => {
            const isCountryQuestion =
              !["education_country", "study_location", "school_location"].includes(q.key) &&
              (
                q.key === "nationality" ||
                q.key.endsWith("_nationality") ||
                q.key === "citizenship" ||
                q.key.endsWith("_citizenship") ||
                q.key === "passport_country" ||
                q.key === "birth_country" ||
                q.key === "current_residence_country" ||
                q.key === "residence_country" ||
                q.prompt.toLowerCase().includes("what is your nationality") ||
                q.prompt.toLowerCase().includes("supporter's nationality") ||
                q.prompt.toLowerCase().includes("guarantor's nationality") ||
                q.prompt.toLowerCase().includes("country of citizenship") ||
                q.prompt.toLowerCase().includes("passport country")
              );

            const hasSelected = current !== undefined && current !== "" && current !== null;
            const isEditing = openSelectorKey === q.key;

            // ── 1. Genuine Country / Nationality Picker (Searches all 240+ countries) ──
            if (isCountryQuestion) {
              if (hasSelected && !isEditing) {
                const currentStr = String(current);
                const isOther = currentStr.toLowerCase() === "other";
                const cMeta = isOther
                  ? { flag: "🌐", name: "Other / Not Listed", code: "other" }
                  : matchCountry(currentStr);
                return (
                  <div className={`flex items-center justify-between rounded-lg border p-3 text-xs shadow-xs ${fieldError ? "border-rose-500 bg-rose-500/5" : "border-primary/30 bg-primary/5"}`}>
                    <div className="flex items-center gap-3 min-w-0">
                      <span className="text-2xl shrink-0">{cMeta.flag}</span>
                      <div className="min-w-0">
                        <p className="font-bold text-sm text-foreground truncate">{cMeta.name}</p>
                        <p className="text-[11px] text-muted-foreground font-mono">
                          Selected Code: {cMeta.code || currentStr.toUpperCase()}
                        </p>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        setOpenSelectorKey(q.key);
                        setEnumSearch((prev) => ({ ...prev, [q.key]: "" }));
                      }}
                      className="rounded-md border bg-background px-3 py-1.5 text-xs font-semibold text-primary hover:bg-accent shadow-xs transition-colors shrink-0"
                    >
                      Change
                    </button>
                  </div>
                );
              }

              const countriesToDisplay = searchVal
                ? searchCountries(searchVal, 40)
                : ALL_COUNTRIES.slice(0, 30);

              return (
                <div className="space-y-2 pt-1">
                  <div className="relative">
                    <Search className="absolute left-2.5 top-2.5 size-3.5 text-muted-foreground" />
                    <input
                      type="text"
                      value={searchVal}
                      onChange={(e) => setEnumSearch((prev) => ({ ...prev, [q.key]: e.target.value }))}
                      placeholder="Search any country name or code (e.g. Bangladesh, Japan, US, Canada)..."
                      autoFocus={isEditing}
                      className={`h-8 w-full rounded-md border bg-background pl-8 pr-3 text-xs outline-none focus-visible:ring-2 font-normal ${fieldError ? "border-rose-500 focus-visible:ring-rose-500/50" : "focus-visible:ring-ring"}`}
                    />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 max-h-56 overflow-y-auto pr-1">
                    {countriesToDisplay.map((country) => {
                      const isSelected =
                        String(current).toUpperCase() === country.code.toUpperCase() ||
                        String(current).toLowerCase() === country.name.toLowerCase();
                      return (
                        <button
                          key={country.code}
                          type="button"
                          onClick={() => {
                            const answerVal =
                              q.type === "enum" && q.options && q.options.some((o) => o.toLowerCase() === country.name.toLowerCase())
                                ? country.name
                                : country.code;
                            void handleDirectAnswer(q.key, answerVal);
                            setOpenSelectorKey(null);
                            setEnumSearch((prev) => ({ ...prev, [q.key]: "" }));
                          }}
                          className={`flex items-center gap-2 rounded-md border px-2.5 py-2 text-left text-xs transition-all ${
                            isSelected
                              ? "border-primary bg-primary/10 text-primary font-semibold ring-1 ring-primary/40"
                              : "hover:bg-accent text-foreground bg-background"
                          }`}
                        >
                          <span className="text-base shrink-0">{country.flag}</span>
                          <span className="truncate flex-1 font-medium">{country.name}</span>
                          <span className="text-[10px] text-muted-foreground font-mono">{country.code}</span>
                        </button>
                      );
                    })}
                    {countriesToDisplay.length === 0 && (
                      <p className="col-span-2 text-center text-[11px] text-muted-foreground py-3">
                        No countries match &ldquo;{searchVal}&rdquo;
                      </p>
                    )}
                  </div>
                </div>
              );
            }

            // ── 2. Standard Enum Questions ──────────────────────────────────────
            if (q.type === "enum" && q.options) {
              // General small enum (<= 4 options, e.g. education_country, sex, etc.)
              if (optionsCount <= 4) {
                return (
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {q.options.map((opt) => (
                      <button
                        key={opt}
                        type="button"
                        onClick={() => void handleDirectAnswer(q.key, opt)}
                        className={`rounded-md border px-3 py-1.5 text-xs transition-all ${
                          current === opt
                            ? "border-primary bg-primary/10 text-primary font-semibold shadow-sm ring-1 ring-primary/40"
                            : "hover:bg-accent text-muted-foreground bg-background"
                        }`}
                      >
                        {optionLabel(q, opt)}
                      </button>
                    ))}
                  </div>
                );
              }

              // General large enum (> 4 options)
              if (hasSelected && !isEditing) {
                return (
                  <div className={`flex items-center justify-between rounded-lg border p-2.5 text-xs shadow-xs ${fieldError ? "border-rose-500 bg-rose-500/5" : "border-primary/30 bg-primary/5"}`}>
                    <span className="font-semibold text-foreground truncate">{optionLabel(q, String(current))}</span>
                    <button
                      type="button"
                      onClick={() => {
                        setOpenSelectorKey(q.key);
                        setEnumSearch((prev) => ({ ...prev, [q.key]: "" }));
                      }}
                      className="rounded-md border bg-background px-2.5 py-1 text-xs font-semibold text-primary hover:bg-accent shadow-xs transition-colors shrink-0"
                    >
                      Change
                    </button>
                  </div>
                );
              }

              return (
                <div className="space-y-2 pt-1">
                  <div className="relative">
                    <Search className="absolute left-2.5 top-2.5 size-3.5 text-muted-foreground" />
                    <input
                      type="text"
                      value={searchVal}
                      onChange={(e) => setEnumSearch((prev) => ({ ...prev, [q.key]: e.target.value }))}
                      placeholder={`Search ${optionsCount} options...`}
                      autoFocus={isEditing}
                      className={`h-8 w-full rounded-md border bg-background pl-8 pr-3 text-xs outline-none focus-visible:ring-2 font-normal ${fieldError ? "border-rose-500 focus-visible:ring-rose-500/50" : "focus-visible:ring-ring"}`}
                    />
                  </div>

                  <div className="flex flex-wrap gap-1.5 max-h-48 overflow-y-auto pr-1">
                    {filteredOptions.map((opt) => (
                      <button
                        key={opt}
                        type="button"
                        onClick={() => {
                          void handleDirectAnswer(q.key, opt);
                          setOpenSelectorKey(null);
                          setEnumSearch((prev) => ({ ...prev, [q.key]: "" }));
                        }}
                        className={`rounded-md border px-2.5 py-1 text-xs transition-all ${
                          current === opt
                            ? "border-primary bg-primary/10 text-primary font-semibold shadow-sm ring-1 ring-primary/40"
                            : "hover:bg-accent text-muted-foreground bg-background"
                        }`}
                      >
                        {optionLabel(q, opt)}
                      </button>
                    ))}
                    {filteredOptions.length === 0 && (
                      <p className="text-[11px] text-muted-foreground py-1">No options match &quot;{searchVal}&quot;</p>
                    )}
                  </div>
                </div>
              );
            }

            // ── 3. Boolean Questions ────────────────────────────────────────────
            if (q.type === "boolean") {
              return (
                <div className="flex gap-2 pt-1">
                  <button
                    type="button"
                    onClick={() => void handleDirectAnswer(q.key, true)}
                    className={`flex-1 rounded-md border py-2 text-xs font-medium transition-all ${
                      current === true
                        ? "border-emerald-500 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 font-bold shadow-sm ring-1 ring-emerald-500/40"
                        : "hover:bg-accent text-muted-foreground bg-background"
                    }`}
                  >
                    Yes
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleDirectAnswer(q.key, false)}
                    className={`flex-1 rounded-md border py-2 text-xs font-medium transition-all ${
                      current === false
                        ? "border-rose-500 bg-rose-500/10 text-rose-700 dark:text-rose-300 font-bold shadow-sm ring-1 ring-rose-500/40"
                        : "hover:bg-accent text-muted-foreground bg-background"
                    }`}
                  >
                    No
                  </button>
                </div>
              );
            }

            // ── 4. Inputs: text, number, date ───────────────────────────────────
            return (
              <div className="pt-1">
                <input
                  type={q.type === "integer" ? "number" : isDateInput ? "date" : "text"}
                  value={String(current ?? "")}
                  onChange={(e) => handleChange(q.key, e.target.value)}
                  onBlur={() => void handleSubmit(q.key)}
                  onPaste={(e) => {
                    const text = e.clipboardData.getData("text").trim();
                    if (text) {
                      handleChange(q.key, text);
                      const parsed = q.type === "integer" ? (parseInt(text, 10) || text) : text;
                      void handleDirectAnswer(q.key, parsed);
                    }
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      void handleSubmit(q.key);
                      (e.target as HTMLInputElement).blur();
                    }
                  }}
                  placeholder={`Enter ${q.key.replaceAll("_", " ")}...`}
                  className={`h-9 w-full rounded-md border bg-background px-3 text-xs outline-none focus-visible:ring-2 font-normal transition-colors ${
                    fieldError
                      ? "border-rose-500 focus-visible:ring-rose-500/50 bg-rose-500/[0.02]"
                      : "focus-visible:ring-ring"
                  }`}
                />
              </div>
            );
          })()}
        </div>

        {fieldError && (
          <div className="flex items-center gap-1.5 text-xs text-rose-600 dark:text-rose-400 font-medium pt-2 animate-in fade-in duration-200">
            <AlertCircle className="size-3.5 shrink-0 text-rose-500" />
            <span>{fieldError}</span>
          </div>
        )}

        {!fieldError && state.answers[q.key] !== undefined && (
          <div className="flex items-center gap-1 text-[11px] text-emerald-600 dark:text-emerald-400 font-medium pt-2">
            <Check className="size-3.5 shrink-0" />
            <span>Answer Saved</span>
          </div>
        )}
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Progress & Section Tabs Header */}
      <div className="space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-semibold text-foreground">Intake Questionnaire &amp; Screening</h3>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {state.progress.answered} of {state.progress.total} total fields completed ({pct}%)
              {state.progress.complete ? " · Ready for Eligibility Evaluation" : ""}
            </p>
          </div>

          <div className="flex items-center gap-2 self-start sm:self-auto">
            {sectionKeys.length > 1 && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setViewAll((prev) => !prev)}
                className="h-7 text-xs gap-1 px-2.5 text-muted-foreground hover:text-foreground"
              >
                {viewAll ? <LayoutGrid className="size-3.5" /> : <ListChecks className="size-3.5" />}
                {viewAll ? "Tabbed View" : "View All Questions"}
              </Button>
            )}
            <Badge tone={pct === 100 ? "success" : "default"} className="text-xs font-medium">
              {sectionKeys.length} Modules ({pct}% complete)
            </Badge>
          </div>
        </div>

        <div className="h-2 overflow-hidden rounded-full bg-muted">
          <div className="h-full bg-primary transition-all duration-300" style={{ width: `${pct}%` }} />
        </div>
      </div>

      {/* Section Navigation Tabs (Tabbed Mode) */}
      {!viewAll && sectionKeys.length > 1 && (
        <div className="flex flex-wrap gap-2 border-b pb-3">
          {sectionKeys.map((secName) => {
            const secQuestions = sectionsMap.get(secName) || [];
            const reqQuestions = secQuestions.filter((q) => q.required !== false);
            const answeredInSec = secQuestions.filter((q) => state.answers[q.key] !== undefined && state.answers[q.key] !== "").length;
            const answeredReqInSec = reqQuestions.filter((q) => state.answers[q.key] !== undefined && state.answers[q.key] !== "").length;
            const isSecComplete = reqQuestions.length > 0
              ? answeredReqInSec >= reqQuestions.length
              : answeredInSec === secQuestions.length;
            const isActive = secName === currentSectionKey;

            return (
              <button
                key={secName}
                onClick={() => setActiveSection(secName)}
                className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-all ${
                  isActive
                    ? "bg-primary text-primary-foreground shadow-sm font-semibold ring-2 ring-primary/30"
                    : isSecComplete
                      ? "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800"
                      : "bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground border"
                }`}
              >
                {isSecComplete ? (
                  <Check className="size-3 text-emerald-500 shrink-0" />
                ) : (
                  <AlertCircle className="size-3 text-muted-foreground/60 shrink-0" />
                )}
                <span>{secName}</span>
                <span className={`text-[10px] font-semibold ${isSecComplete ? "opacity-80" : "text-muted-foreground"}`}>
                  ({answeredInSec}/{secQuestions.length})
                </span>
              </button>
            );
          })}
        </div>
      )}

      {/* Questions Rendering */}
      {state.questions.length === 0 ? (
        <p className="text-sm text-muted-foreground">No questions available for this scope.</p>
      ) : viewAll ? (
        /* View All Mode: Render all sections sequentially */
        <div className="space-y-8">
          {sectionKeys.map((secName) => {
            const secQuestions = sectionsMap.get(secName) || [];
            const reqQuestions = secQuestions.filter((q) => q.required !== false);
            const secAnswered = secQuestions.filter((q) => state.answers[q.key] !== undefined && state.answers[q.key] !== "").length;
            const secReqAnswered = reqQuestions.filter((q) => state.answers[q.key] !== undefined && state.answers[q.key] !== "").length;
            const isComplete = reqQuestions.length > 0
              ? secReqAnswered >= reqQuestions.length
              : secAnswered === secQuestions.length;

            return (
              <div key={secName} className="space-y-3">
                <div className="flex items-center justify-between border-b pb-2">
                  <h4 className="text-sm font-bold text-foreground flex items-center gap-2">
                    <span>{secName}</span>
                    <Badge tone={isComplete ? "success" : "warning"} className="text-[10px]">
                      {secAnswered} / {secQuestions.length} answered
                    </Badge>
                  </h4>
                </div>

                <SectionSourceBanner questions={secQuestions} />

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {secQuestions.map(renderQuestion)}
                </div>
              </div>
            );
          })}

          {/* View All Bottom Completion Banner */}
          <div className="rounded-[var(--radius)] border p-4 bg-muted/30 flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="text-xs text-muted-foreground flex items-center gap-2">
              {!state.progress.complete && (
                <AlertTriangle className="size-4 text-amber-500 shrink-0" />
              )}
              <span>
                {state.progress.complete
                  ? "All required questions answered across all modules."
                  : `${state.progress.total - state.progress.answered} question(s) remaining. You may proceed to preview eligibility.`}
              </span>
            </div>
            {onProceedToEligibility && (
              <Button
                onClick={onProceedToEligibility}
                className={`gap-2 text-xs font-semibold text-white shadow-sm ${
                  state.progress.complete
                    ? "bg-emerald-600 hover:bg-emerald-700"
                    : "bg-primary hover:bg-primary/90"
                }`}
              >
                {state.progress.complete ? (
                  <CheckCircle2 className="size-4" />
                ) : (
                  <AlertTriangle className="size-3.5 text-amber-300" />
                )}
                {state.progress.complete
                  ? "Proceed to Eligibility Screening"
                  : `Proceed to Eligibility (${state.progress.total - state.progress.answered} incomplete)`}{" "}
                <ArrowRight className="size-4" />
              </Button>
            )}
          </div>
        </div>
      ) : (
        /* Tabbed Active Section Mode */
        <div className="space-y-4">
          <div className="flex items-center justify-between pb-1">
            <h4 className="text-sm font-semibold text-foreground flex items-center gap-2">
              <span>{currentSectionKey}</span>
              <Badge tone={isCurrentSectionComplete ? "success" : "warning"} className="text-[10px] font-normal">
                {currentAnsweredCount} / {currentQuestions.length} answered
              </Badge>
            </h4>
          </div>

          <SectionSourceBanner questions={currentQuestions} />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {currentQuestions.map(renderQuestion)}
          </div>

          {/* Section Navigation Wizard Footer */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 border-t pt-5 mt-6">
            {currentSectionIndex > 0 ? (
              <Button
                variant="outline"
                onClick={() => setActiveSection(sectionKeys[currentSectionIndex - 1])}
                className="h-9 text-xs gap-1.5 px-3 justify-center sm:justify-start"
              >
                <ChevronLeft className="size-3.5" /> Previous: {sectionKeys[currentSectionIndex - 1]}
              </Button>
            ) : <div />}

            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
              {!isCurrentSectionComplete && (
                <span className="text-xs text-muted-foreground font-medium text-center sm:text-left">
                  {remainingInCurrent} question(s) left in this module
                </span>
              )}

              {currentSectionIndex < sectionKeys.length - 1 ? (
                <div className="flex flex-wrap items-center gap-2 justify-end">
                  <Button
                    onClick={() => setActiveSection(sectionKeys[currentSectionIndex + 1])}
                    className="h-9 text-xs gap-1.5 px-4 font-semibold shadow-sm justify-center sm:justify-start"
                  >
                    Continue to: {sectionKeys[currentSectionIndex + 1]} <ChevronRight className="size-3.5" />
                  </Button>
                  {onProceedToEligibility && (
                    <Button
                      variant="outline"
                      onClick={onProceedToEligibility}
                      className="h-9 text-xs gap-1.5 px-3 text-muted-foreground hover:text-foreground border-border/80"
                      title="Preview Eligibility and subsequent steps"
                    >
                      Skip to Eligibility <ArrowRight className="size-3.5" />
                    </Button>
                  )}
                </div>
              ) : (
                <div className="flex flex-wrap items-center gap-2 justify-end">
                  {firstIncompleteSection && firstIncompleteSection !== currentSectionKey && (
                    <Button
                      variant="outline"
                      onClick={() => setActiveSection(firstIncompleteSection)}
                      className="h-9 text-xs gap-1.5 px-3 text-primary border-primary/30 hover:bg-primary/5"
                    >
                      Review Incomplete: {firstIncompleteSection}
                    </Button>
                  )}
                  {onProceedToEligibility && (
                    <Button
                      onClick={onProceedToEligibility}
                      className={`h-9 text-xs gap-1.5 px-4 font-semibold text-white shadow-sm ${
                        state.progress.complete
                          ? "bg-emerald-600 hover:bg-emerald-700"
                          : "bg-primary hover:bg-primary/90"
                      }`}
                    >
                      {state.progress.complete ? (
                        <CheckCircle2 className="size-4" />
                      ) : (
                        <AlertTriangle className="size-3.5 text-amber-300" />
                      )}
                      {state.progress.complete
                        ? "All Sections Complete — Proceed to Eligibility"
                        : `Proceed to Eligibility (${state.progress.total - state.progress.answered} incomplete)`}{" "}
                      <ArrowRight className="size-4" />
                    </Button>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
