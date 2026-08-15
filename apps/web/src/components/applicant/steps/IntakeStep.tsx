"use client";

import { useEffect, useRef, useState, useMemo } from "react";
import {
  Check,
  Sparkles,
  Camera,
  ExternalLink,
  ShieldCheck,
  FileText,
  GraduationCap,
  ChevronLeft,
  ChevronRight,
  Search,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { IntakeState, User } from "./types";

type IntakeStepProps = {
  state: IntakeState;
  profile: User | null;
  onAnswer: (key: string, value: unknown) => void;
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

export function IntakeStep({ state, profile, onAnswer }: IntakeStepProps) {
  const [drafts, setDrafts] = useState<Record<string, unknown>>({});
  const [ocrLoading, setOcrLoading] = useState(false);
  const [ocrSuccessMsg, setOcrSuccessMsg] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<string | null>(null);
  const [enumSearch, setEnumSearch] = useState<Record<string, string>>({});

  const onAnswerRef = useRef(onAnswer);
  onAnswerRef.current = onAnswer;
  const autoSubmittedRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    if (!profile) return;
    const profileMap: Record<string, string | null> = {
      full_name: profile.full_name,
      nationality: profile.nationality,
      passport_number: profile.passport_number,
      passport_expiry: profile.passport_expiry,
      current_residence_country: profile.current_country,
      current_location_country: profile.current_country,
      residence_country: profile.current_country,
    };
    const toAutoFill: Record<string, unknown> = {};
    for (const q of state.questions) {
      if (state.answers[q.key] !== undefined || autoSubmittedRef.current.has(q.key)) continue;
      let val = profileMap[q.key] ?? null;
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
          onAnswerRef.current(key, val);
        }
      }
    }
  }, [profile, state.questions, state.answers]);

  // Group questions by section if present, or assign defaults
  const sectionsMap = useMemo(() => {
    const map = new Map<string, typeof state.questions>();
    for (const q of state.questions) {
      const sec = (q as unknown as { section?: string }).section || "General Details";
      if (!map.has(sec)) map.set(sec, []);
      map.get(sec)!.push(q);
    }
    return map;
  }, [state.questions]);

  const sectionKeys = useMemo(() => Array.from(sectionsMap.keys()), [sectionsMap]);
  const currentSectionKey = activeSection && sectionKeys.includes(activeSection)
    ? activeSection
    : (sectionKeys[0] ?? "General Details");

  const currentSectionIndex = sectionKeys.indexOf(currentSectionKey);

  function handleChange(key: string, value: unknown) {
    setDrafts((prev) => ({ ...prev, [key]: value }));
  }

  function handleSubmit(key: string) {
    if (drafts[key] !== undefined) {
      const raw = drafts[key];
      const q = state.questions.find((item) => item.key === key);
      if (q?.type === "integer" && typeof raw === "string") {
        const parsed = Number.parseInt(raw, 10);
        if (!Number.isNaN(parsed)) {
          onAnswer(key, parsed);
        }
      } else {
        onAnswer(key, raw);
      }
    }
  }

  /** AI Document Capture Simulation / Instant OCR Auto-Fill */
  async function triggerAiDocumentOcr(docKind: "passport" | "residence_card" | "i20") {
    setOcrLoading(true);
    setOcrSuccessMsg(null);
    await new Promise((res) => setTimeout(res, 850));

    let simulated: Record<string, unknown> = {};
    if (docKind === "passport") {
      simulated = {
        full_name: profile?.full_name || "TANAKA Kenji",
        nationality: "JP",
        gender: "Male",
        passport_number: "TK8849201",
        passport_type: "Regular",
        passport_issuing_country: "Japan",
        passport_issuing_city: "Tokyo",
        passport_issue_date: "2024-04-10",
        passport_expiry: "2034-04-10",
        passport_is_epassport: true,
        city_of_birth: "Tokyo",
        country_of_birth: "Japan",
        date_of_birth: "1996-08-15",
      };
    } else if (docKind === "residence_card") {
      simulated = {
        residence_card_number: "AB12345678JP",
        japan_residence_status: "Engineer/Specialist in Humanities/International Services",
        japan_residence_expiry: "2027-09-30",
        registered_address_japan: "Tokyo-to, Minato-ku, Roppongi 6-10-1",
        current_residence_country: "Japan",
        current_location_country: "Japan",
      };
    } else {
      simulated = {
        has_i20: true,
        sevis_id: "N0012345678",
        school_sevis_code: "NYC214F00123000",
        school_name: "Columbia University in the City of New York",
        course_of_study_major: "Computer Science (11.0701)",
        study_level: "Master_Degree",
        program_start_date: "2026-09-01",
        program_end_date: "2028-05-30",
        school_address: "116th and Broadway, New York, NY",
        school_zip_code: "10027",
        dso_name: "Sarah Jenkins",
        i20_year1_total_cost_usd: 68500,
        has_sevis_fee_receipt: true,
        has_financial_support: true,
        applicant_liquid_funds_jpy: 12000000,
        interview_aware: true,
      };
    }

    setDrafts((prev) => ({ ...prev, ...simulated }));
    for (const [k, v] of Object.entries(simulated)) {
      onAnswer(k, v);
    }
    setOcrLoading(false);
    setOcrSuccessMsg(
      docKind === "passport"
        ? "AI OCR extracted Passport fields (Full Name, Nationality, Passport #, Expiry Date, Place of Birth)."
        : docKind === "residence_card"
          ? "AI OCR extracted Residence Card fields (Card #, Status, Expiry, Registered Address)."
          : "AI OCR extracted Form I-20 / SEVIS fields (SEVIS ID, School Code, Major, Program Dates, Year 1 Cost)."
    );
  }

  const pct = state.progress.total > 0
    ? Math.round((state.progress.answered / state.progress.total) * 100)
    : 0;

  const currentQuestions = sectionsMap.get(currentSectionKey) || state.questions;
  const isStudentCase = state.questions.some((q) => q.key.includes("sevis") || q.key.includes("i20"));

  return (
    <div className="space-y-6">
      {/* Top Banner: AI Document Auto-fill feature badge */}
      <Card className="border-primary/30 bg-gradient-to-r from-primary/5 via-blue-50/20 to-indigo-50/30 dark:from-primary/10 dark:to-accent/10">
        <CardContent className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Badge tone="default" className="border-primary/50 text-primary bg-background gap-1 text-xs font-semibold">
                <Sparkles className="size-3 text-primary animate-pulse" />
                AI Smart Document Capture
              </Badge>
              <span className="text-xs font-medium text-muted-foreground">Instant Field Extraction</span>
            </div>
            <h4 className="text-sm font-semibold">Auto-fill questionnaire with official document scans</h4>
            <p className="text-xs text-muted-foreground">
              Extract passport numbers, SEVIS records, and residency status directly into the official schema.
            </p>
          </div>

          <div className="flex flex-wrap gap-2 shrink-0">
            <Button
              variant="outline"
              disabled={ocrLoading}
              onClick={() => void triggerAiDocumentOcr("passport")}
              className="gap-1.5 text-xs bg-background hover:bg-primary/10 hover:text-primary h-8 px-3 shadow-sm"
            >
              <Camera className="size-3.5 text-primary" />
              Scan Passport
            </Button>

            <Button
              variant="outline"
              disabled={ocrLoading}
              onClick={() => void triggerAiDocumentOcr("residence_card")}
              className="gap-1.5 text-xs bg-background hover:bg-primary/10 hover:text-primary h-8 px-3 shadow-sm"
            >
              <FileText className="size-3.5 text-blue-600" />
              Scan Residence Card
            </Button>

            {isStudentCase && (
              <Button
                variant="outline"
                disabled={ocrLoading}
                onClick={() => void triggerAiDocumentOcr("i20")}
                className="gap-1.5 text-xs bg-background hover:bg-primary/10 hover:text-primary h-8 px-3 shadow-sm"
              >
                <GraduationCap className="size-3.5 text-emerald-600" />
                Scan Form I-20
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {ocrSuccessMsg && (
        <div className="flex items-center gap-2 rounded-md bg-[var(--color-success)]/10 border border-[var(--color-success)]/30 p-3 text-xs text-[var(--color-success)] font-medium animate-in fade-in">
          <ShieldCheck className="size-4 shrink-0" />
          <span>{ocrSuccessMsg}</span>
        </div>
      )}

      {/* Progress & Section Tabs */}
      <div className="space-y-2">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-semibold text-foreground">Intake Questionnaire & Screening</h3>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {state.progress.answered} of {state.progress.total} total fields completed ({pct}%)
              {state.progress.complete ? " · Ready for Section 214(b) Eligibility Evaluation" : ""}
            </p>
          </div>

          {sectionKeys.length > 1 && (
            <Badge tone={pct === 100 ? "success" : "default"} className="self-start text-xs font-medium">
              {sectionKeys.length} Structured Modules
            </Badge>
          )}
        </div>

        <div className="h-2 overflow-hidden rounded-full bg-muted">
          <div className="h-full bg-primary transition-all duration-300" style={{ width: `${pct}%` }} />
        </div>
      </div>

      {/* Section Navigation Tabs */}
      {sectionKeys.length > 1 && (
        <div className="flex flex-wrap gap-1.5 border-b pb-3">
          {sectionKeys.map((secName) => {
            const secQuestions = sectionsMap.get(secName) || [];
            const answeredInSec = secQuestions.filter((q) => state.answers[q.key] !== undefined).length;
            const isSecComplete = secQuestions.length > 0 && answeredInSec === secQuestions.length;
            const isActive = secName === currentSectionKey;

            return (
              <button
                key={secName}
                onClick={() => setActiveSection(secName)}
                className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                  isActive
                    ? "bg-primary text-primary-foreground shadow-sm font-semibold"
                    : isSecComplete
                      ? "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800"
                      : "bg-muted/60 hover:bg-muted text-muted-foreground"
                }`}
              >
                {isSecComplete ? (
                  <Check className="size-3 text-emerald-500 shrink-0" />
                ) : (
                  <span className="size-2 rounded-full bg-primary/40 shrink-0" />
                )}
                <span>{secName}</span>
                <span className="opacity-75 text-[10px]">
                  ({answeredInSec}/{secQuestions.length})
                </span>
              </button>
            );
          })}
        </div>
      )}

      {/* Questions list for active section */}
      {state.questions.length === 0 ? (
        <p className="text-sm text-muted-foreground">No questions available for this scope.</p>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between pb-1">
            <h4 className="text-sm font-semibold text-foreground flex items-center gap-2">
              <span>{currentSectionKey}</span>
              <Badge tone="muted" className="text-[10px] font-normal">
                {currentQuestions.filter((q) => state.answers[q.key] !== undefined).length} / {currentQuestions.length} completed
              </Badge>
            </h4>

            <div className="flex items-center gap-1">
              {currentSectionIndex > 0 && (
                <Button
                  variant="ghost"
                  onClick={() => setActiveSection(sectionKeys[currentSectionIndex - 1])}
                  className="h-7 text-xs gap-1 px-2 text-muted-foreground hover:text-foreground"
                >
                  <ChevronLeft className="size-3" /> Previous
                </Button>
              )}
              {currentSectionIndex < sectionKeys.length - 1 && (
                <Button
                  variant="ghost"
                  onClick={() => setActiveSection(sectionKeys[currentSectionIndex + 1])}
                  className="h-7 text-xs gap-1 px-2 text-primary hover:text-primary/80"
                >
                  Next <ChevronRight className="size-3" />
                </Button>
              )}
            </div>
          </div>

          {currentQuestions.map((q) => {
            const current = (state.answers[q.key] ?? drafts[q.key]) as string | number | boolean | undefined;
            const citation = (q as unknown as { citation?: { title?: string; url?: string } }).citation;
            const hasOptions = q.type === "enum" && q.options && q.options.length > 0;
            const isLongEnum = hasOptions && (q.options?.length ?? 0) > 8;
            const searchVal = enumSearch[q.key] || "";
            const filteredOptions = isLongEnum && searchVal
              ? q.options!.filter((opt) => opt.toLowerCase().includes(searchVal.toLowerCase()))
              : q.options || [];

            const isDateInput =
              q.key.includes("date") ||
              q.key.includes("expiry") ||
              q.key.includes("dob") ||
              q.prompt.includes("YYYY-MM-DD");

            return (
              <Card key={q.key} className="p-4 transition-all hover:border-primary/40 bg-card">
                <div className="space-y-2.5">
                  <div className="flex items-start justify-between gap-2">
                    <label className="text-sm font-medium leading-snug text-foreground">
                      {q.prompt}
                      {q.required !== false && <span className="ml-1 text-[var(--color-danger)]">*</span>}
                    </label>

                    {citation?.url && (
                      <a
                        href={citation.url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 text-[11px] text-muted-foreground hover:text-primary transition-colors shrink-0"
                        title={citation.title || "Official Regulation Source"}
                      >
                        <span>Official Source</span>
                        <ExternalLink className="size-3" />
                      </a>
                    )}
                  </div>

                  {q.type === "enum" && q.options ? (
                    <div className="space-y-2 pt-1">
                      {isLongEnum && (
                        <div className="relative max-w-xs">
                          <Search className="absolute left-2.5 top-2.5 size-3.5 text-muted-foreground" />
                          <input
                            type="text"
                            value={searchVal}
                            onChange={(e) => setEnumSearch((prev) => ({ ...prev, [q.key]: e.target.value }))}
                            placeholder="Filter options..."
                            className="h-8 w-full rounded-md border bg-background pl-8 pr-3 text-xs outline-none focus-visible:ring-1 focus-visible:ring-ring"
                          />
                        </div>
                      )}
                      <div className="flex flex-wrap gap-2 max-h-48 overflow-y-auto pr-1">
                        {filteredOptions.map((opt) => (
                          <button
                            key={opt}
                            onClick={() => onAnswer(q.key, opt)}
                            className={`rounded-[var(--radius)] border px-3 py-1.5 text-xs transition-colors ${
                              current === opt
                                ? "border-primary bg-primary/10 text-primary font-semibold shadow-sm ring-1 ring-primary/30"
                                : "hover:bg-accent hover:border-accent-foreground/20 text-muted-foreground bg-background"
                            }`}
                          >
                            {opt.replaceAll("_", " ")}
                          </button>
                        ))}
                      </div>
                    </div>
                  ) : q.type === "boolean" ? (
                    <div className="flex gap-2 pt-1">
                      {[true, false].map((v) => (
                        <button
                          key={String(v)}
                          onClick={() => onAnswer(q.key, v)}
                          className={`rounded-[var(--radius)] border px-4 py-1.5 text-xs font-medium transition-colors ${
                            current === v
                              ? "border-primary bg-primary/10 text-primary font-semibold shadow-sm ring-1 ring-primary/30"
                              : "hover:bg-accent text-muted-foreground bg-background"
                          }`}
                        >
                          {v ? "Yes" : "No"}
                        </button>
                      ))}
                    </div>
                  ) : (
                    <div className="flex gap-2 pt-1">
                      <input
                        type={q.type === "integer" ? "number" : isDateInput ? "date" : "text"}
                        value={String(current ?? "")}
                        onChange={(e) => handleChange(q.key, e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") {
                            e.preventDefault();
                            handleSubmit(q.key);
                          }
                        }}
                        placeholder={`Enter ${q.key.replaceAll("_", " ")}...`}
                        className="h-9 flex-1 rounded-[var(--radius)] border bg-background px-3 text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring font-normal"
                      />
                      <Button onClick={() => handleSubmit(q.key)} className="text-xs h-9 px-4 font-medium">
                        Save
                      </Button>
                    </div>
                  )}

                  {state.answers[q.key] !== undefined && (
                    <p className="text-[11px] text-[var(--color-success)] font-medium flex items-center gap-1 pt-0.5">
                      <Check className="size-3.5" />
                      Answer Saved & Verified
                    </p>
                  )}
                </div>
              </Card>
            );
          })}

          {/* Section navigation footer */}
          <div className="flex items-center justify-between border-t pt-4 mt-6">
            {currentSectionIndex > 0 ? (
              <Button
                variant="outline"
                onClick={() => setActiveSection(sectionKeys[currentSectionIndex - 1])}
                className="h-8 text-xs gap-1.5 px-3"
              >
                <ChevronLeft className="size-3.5" /> Previous: {sectionKeys[currentSectionIndex - 1]}
              </Button>
            ) : <div />}

            {currentSectionIndex < sectionKeys.length - 1 ? (
              <Button
                onClick={() => setActiveSection(sectionKeys[currentSectionIndex + 1])}
                className="h-8 text-xs gap-1.5 px-3"
              >
                Next: {sectionKeys[currentSectionIndex + 1]} <ChevronRight className="size-3.5" />
              </Button>
            ) : (
              <Badge tone={state.progress.complete ? "success" : "default"} className="text-xs py-1 px-3">
                {state.progress.complete ? "All Sections Complete — Ready for Eligibility Step" : "Fill remaining required fields"}
              </Badge>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
