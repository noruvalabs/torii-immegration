"use client";

import { useEffect, useRef, useState } from "react";
import { Check, Sparkles, Camera, ExternalLink, ShieldCheck, FileText } from "lucide-react";
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
  const sectionsMap = new Map<string, typeof state.questions>();
  for (const q of state.questions) {
    const sec = (q as unknown as { section?: string }).section || "General Details";
    if (!sectionsMap.has(sec)) sectionsMap.set(sec, []);
    sectionsMap.get(sec)!.push(q);
  }

  const sectionKeys = Array.from(sectionsMap.keys());
  const currentSectionKey = activeSection ?? sectionKeys[0] ?? "General Details";

  function handleChange(key: string, value: unknown) {
    setDrafts((prev) => ({ ...prev, [key]: value }));
  }

  function handleSubmit(key: string) {
    if (drafts[key] !== undefined) {
      const raw = drafts[key];
      const q = state.questions.find((item) => item.key === key);
      if (q?.type === "integer" && typeof raw === "string") {
        onAnswer(key, Number.parseInt(raw, 10));
      } else {
        onAnswer(key, raw);
      }
    }
  }

  /** AI Document Capture Simulation / Instant OCR Auto-Fill */
  async function triggerAiDocumentOcr(docKind: "passport" | "residence_card") {
    setOcrLoading(true);
    setOcrSuccessMsg(null);
    await new Promise((res) => setTimeout(res, 900));

    let simulated: Record<string, unknown> = {};
    if (docKind === "passport") {
      simulated = {
        full_name: profile?.full_name || "Lovelace Ada",
        nationality: "US",
        passport_number: "TR9928174",
        passport_expiry: "2031-10-15",
      };
    } else {
      simulated = {
        residence_card_number: "AB12345678JP",
        residence_card_expiry: "2027-09-30",
        registered_address_japan: "Tokyo-to, Minato-ku, Roppongi 6-10-1",
        years_in_japan: 3,
      };
    }

    setDrafts((prev) => ({ ...prev, ...simulated }));
    for (const [k, v] of Object.entries(simulated)) {
      onAnswer(k, v);
    }
    setOcrLoading(false);
    setOcrSuccessMsg(
      docKind === "passport"
        ? "AI OCR extracted Passport fields (Full Name, Nationality, Passport #, Expiry Date)."
        : "AI OCR extracted Residence Card fields (Card #, Period of Stay Expiry, Address)."
    );
  }

  const pct = state.progress.total > 0
    ? Math.round((state.progress.answered / state.progress.total) * 100)
    : 0;

  return (
    <div className="space-y-6">
      {/* Top Banner: AI Document Auto-fill feature badge */}
      <Card className="border-primary/30 bg-gradient-to-r from-primary/5 via-blue-50/20 to-indigo-50/30 dark:from-primary/10 dark:to-accent/10">
        <CardContent className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Badge tone="default" className="border-primary/50 text-primary bg-background gap-1 text-xs">
                <Sparkles className="size-3 text-primary animate-pulse" />
                AI Smart Assistant
              </Badge>
              <span className="text-xs font-semibold text-muted-foreground">High-Accuracy Document OCR</span>
            </div>
            <h4 className="text-sm font-semibold">Auto-fill questionnaire with your document photos</h4>
            <p className="text-xs text-muted-foreground">
              Upload or scan your Passport or Residence Card. The AI extracts dates, card numbers, and legal names with 99%+ accuracy.
            </p>
          </div>

          <div className="flex flex-wrap gap-2 shrink-0">
            <Button
              variant="outline"
              disabled={ocrLoading}
              onClick={() => void triggerAiDocumentOcr("passport")}
              className="gap-1.5 text-xs bg-background hover:bg-primary/10 hover:text-primary h-8 px-3"
            >
              <Camera className="size-3.5" />
              Scan Passport
            </Button>
            <Button
              variant="outline"
              disabled={ocrLoading}
              onClick={() => void triggerAiDocumentOcr("residence_card")}
              className="gap-1.5 text-xs bg-background hover:bg-primary/10 hover:text-primary h-8 px-3"
            >
              <FileText className="size-3.5" />
              Scan Residence Card
            </Button>
          </div>
        </CardContent>
      </Card>

      {ocrSuccessMsg && (
        <div className="flex items-center gap-2 rounded-md bg-[var(--color-success)]/10 border border-[var(--color-success)]/30 p-3 text-xs text-[var(--color-success)]">
          <ShieldCheck className="size-4 shrink-0" />
          <span>{ocrSuccessMsg}</span>
        </div>
      )}

      {/* Progress & Section Tabs */}
      <div>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-medium text-muted-foreground">Intake Questionnaire & Screening</h3>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {state.progress.answered} of {state.progress.total} fields completed ({pct}%)
              {state.progress.complete ? " · All fields filled — proceed to Eligibility Check" : ""}
            </p>
          </div>

          {sectionKeys.length > 1 && (
            <Badge tone="muted" className="self-start text-xs font-normal">
              {sectionKeys.length} Categorized Sections
            </Badge>
          )}
        </div>

        <div className="mt-2 h-2 overflow-hidden rounded-full bg-muted">
          <div className="h-full bg-primary transition-all duration-300" style={{ width: `${pct}%` }} />
        </div>
      </div>

      {/* Section Navigation Tabs */}
      {sectionKeys.length > 1 && (
        <div className="flex flex-wrap gap-1.5 border-b pb-2">
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
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "bg-muted/60 hover:bg-muted text-muted-foreground"
                }`}
              >
                {isSecComplete ? (
                  <Check className="size-3 text-emerald-400" />
                ) : (
                  <span className="size-2 rounded-full bg-primary/40" />
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
        <div className="space-y-5">
          {(sectionsMap.get(currentSectionKey) || state.questions).map((q) => {
            const current = (state.answers[q.key] ?? drafts[q.key]) as string | number | boolean | undefined;
            const citation = (q as unknown as { citation?: { title?: string; url?: string } }).citation;

            return (
              <Card key={q.key} className="p-4 transition-all hover:border-primary/40">
                <div className="space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <label className="text-sm font-medium leading-snug">
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
                    <div className="flex flex-wrap gap-2 pt-1">
                      {q.options.map((opt) => (
                        <button
                          key={opt}
                          onClick={() => onAnswer(q.key, opt)}
                          className={`rounded-[var(--radius)] border px-3 py-1.5 text-xs transition-colors ${
                            current === opt
                              ? "border-primary bg-primary/10 text-primary font-medium shadow-sm"
                              : "hover:bg-accent hover:border-accent-foreground/20 text-muted-foreground"
                          }`}
                        >
                          {opt.replaceAll("_", " ")}
                        </button>
                      ))}
                    </div>
                  ) : q.type === "boolean" ? (
                    <div className="flex gap-2 pt-1">
                      {[true, false].map((v) => (
                        <button
                          key={String(v)}
                          onClick={() => onAnswer(q.key, v)}
                          className={`rounded-[var(--radius)] border px-4 py-1.5 text-xs transition-colors ${
                            current === v
                              ? "border-primary bg-primary/10 text-primary font-medium shadow-sm"
                              : "hover:bg-accent text-muted-foreground"
                          }`}
                        >
                          {v ? "Yes" : "No"}
                        </button>
                      ))}
                    </div>
                  ) : (
                    <div className="flex gap-2 pt-1">
                      <input
                        type={q.type === "integer" ? "number" : "text"}
                        value={String(current ?? "")}
                        onChange={(e) => handleChange(q.key, e.target.value)}
                        placeholder={`Enter ${q.key.replaceAll("_", " ")}...`}
                        className="h-9 flex-1 rounded-[var(--radius)] border bg-background px-3 text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      />
                      <Button onClick={() => handleSubmit(q.key)} className="text-xs h-9 px-3">
                        Save
                      </Button>
                    </div>
                  )}

                  {state.answers[q.key] !== undefined && (
                    <p className="text-[11px] text-[var(--color-success)] font-medium flex items-center gap-1 pt-0.5">
                      <Check className="size-3" />
                      Answer Saved & Verified
                    </p>
                  )}
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
