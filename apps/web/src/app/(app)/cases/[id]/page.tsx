"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft, Check, ChevronRight, FileText, Upload,
  Loader2, AlertTriangle, Send, Download, ExternalLink, Camera,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";
import { getProfile, type User } from "@/lib/api/auth";
import {
  getCase, getCaseGuidance, getIntake, answerIntake, evaluateEligibility, getEligibility,
  refreshChecklist, getChecklist, patchChecklistItem,
  generateForms, getForms, reviewCase, acknowledgeReview,
  buildPacket, getPacket, submitCase, getDocuments, registerDocument, confirmDocument,
  type Case, type CaseGuidance, type IntakeState, type EligibilityResult,
  type ChecklistItem, type GeneratedForm, type ReviewResult, type Document,
} from "@/lib/api/cases";
import { extractDocumentFields, extractFromFile, type OCRResult, type DocumentType } from "@/lib/api/ocr";
import { getWallet, type WalletDocument } from "@/lib/api/wallet";

type Step = "intake" | "eligibility" | "checklist" | "forms" | "review" | "packet";
const STEPS: { key: Step; label: string }[] = [
  { key: "intake", label: "Intake" },
  { key: "eligibility", label: "Eligibility" },
  { key: "checklist", label: "Checklist" },
  { key: "forms", label: "Forms" },
  { key: "review", label: "Review" },
  { key: "packet", label: "Packet" },
];

function phaseToStep(phase: string): Step {
  if (phase === "done") return "packet";
  if (phase === "blocked") return "intake";
  if (STEPS.some((s) => s.key === phase)) return phase as Step;
  return "intake";
}

function citationUrl(citation: Record<string, unknown> | undefined): string | null {
  const url = citation?.url;
  return typeof url === "string" && url.startsWith("http") ? url : null;
}

function citationVersion(citation: Record<string, unknown> | undefined): string | null {
  const v = citation?.source_version;
  return typeof v === "string" ? v : null;
}

export default function CaseDetailPage() {
  const params = useParams();
  const caseId = Number(params.id);
  const { token } = useAuth();

  const [caseData, setCaseData] = useState<Case | null>(null);
  const [guidance, setGuidance] = useState<CaseGuidance | null>(null);
  const [activeStep, setActiveStep] = useState<Step>("intake");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [intake, setIntake] = useState<IntakeState | null>(null);
  const [eligibility, setEligibility] = useState<EligibilityResult | null>(null);
  const [checklist, setChecklist] = useState<ChecklistItem[]>([]);
  const [forms, setForms] = useState<GeneratedForm[]>([]);
  const [review, setReview] = useState<ReviewResult | null>(null);
  const [packet, setPacket] = useState<Record<string, unknown> | null>(null);
  const [stepError, setStepError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [profile, setProfile] = useState<User | null>(null);

  const loadCase = useCallback(async () => {
    if (!token || !caseId) return;
    setLoading(true);
    try {
      const [c, g] = await Promise.all([
        getCase(token, caseId),
        getCaseGuidance(token, caseId),
      ]);
      setCaseData(c);
      setGuidance(g);
      setActiveStep(phaseToStep(g.phase));
      getProfile(token).then(setProfile).catch(() => {});
    } catch {
      setError("Could not load case.");
    } finally {
      setLoading(false);
    }
  }, [token, caseId]);

  useEffect(() => { void loadCase(); }, [loadCase]);

  useEffect(() => {
    if (!token || !caseId) return;
    setStepError(null);
    if (activeStep === "intake") {
      getIntake(token, caseId).then(setIntake).catch(() => setStepError("Intake questionnaire is not available for this case scope."));
    } else if (activeStep === "eligibility") {
      getEligibility(token, caseId).then(setEligibility).catch(() => { setEligibility(null); setStepError(null); });
    } else if (activeStep === "checklist") {
      getChecklist(token, caseId).then(setChecklist).catch(() => setStepError("Checklist is not available for this case scope."));
    } else if (activeStep === "forms") {
      getForms(token, caseId).then(setForms).catch(() => setStepError("Forms are not available for this case scope."));
    } else if (activeStep === "review") {
      setReview(null);
    } else if (activeStep === "packet") {
      getPacket(token, caseId).then(setPacket).catch(() => { setPacket(null); });
    }
  }, [token, caseId, activeStep]);

  async function refreshGuidance() {
    if (!token) return;
    try {
      const g = await getCaseGuidance(token, caseId);
      setGuidance(g);
      const c = await getCase(token, caseId);
      setCaseData(c);
    } catch { /* ignore */ }
  }

  async function handleAnswer(key: string, value: unknown) {
    if (!token) return;
    setError(null);
    try {
      const state = await answerIntake(token, caseId, key, value);
      setIntake(state);
      await refreshGuidance();
      if (state.progress.complete) setActiveStep("eligibility");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Answer failed");
    }
  }

  async function handleEvaluateEligibility() {
    if (!token) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await evaluateEligibility(token, caseId);
      setEligibility(result);
      await refreshGuidance();
      setActiveStep("checklist");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Evaluation failed");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRefreshChecklist() {
    if (!token) return;
    setSubmitting(true);
    setError(null);
    try {
      const items = await refreshChecklist(token, caseId);
      setChecklist(items);
      await refreshGuidance();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to refresh checklist");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleChecklistStatus(itemId: number, status: string) {
    if (!token) return;
    try {
      await patchChecklistItem(token, caseId, itemId, status);
      setChecklist((prev) => prev.map((i) => (i.id === itemId ? { ...i, status } : i)));
      await refreshGuidance();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Update failed");
    }
  }

  async function handleGenerateForms() {
    if (!token) return;
    setSubmitting(true);
    setError(null);
    try {
      const generated = await generateForms(token, caseId);
      setForms(generated);
      await refreshGuidance();
      setActiveStep("review");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Form generation failed");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleReview() {
    if (!token) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await reviewCase(token, caseId);
      setReview(result);
      await refreshGuidance();
      if (result.ready) setActiveStep("packet");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Review failed");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleAcknowledgeReview() {
    if (!token) return;
    try {
      await acknowledgeReview(token, caseId);
      await refreshGuidance();
      setActiveStep("packet");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Acknowledge failed");
    }
  }

  async function handleBuildPacket() {
    if (!token) return;
    setSubmitting(true);
    setError(null);
    try {
      const built = await buildPacket(token, caseId);
      setPacket(built);
      await refreshGuidance();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Packet build failed");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSubmit() {
    if (!token) return;
    setSubmitting(true);
    setError(null);
    try {
      await submitCase(token, caseId);
      await loadCase();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Submission failed");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!caseData) {
    return (
      <div className="mx-auto max-w-2xl py-12 text-center">
        <p className="text-muted-foreground">Case not found.</p>
        <Link href="/cases" className="mt-4 inline-block text-sm text-primary hover:underline">
          Back to cases
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="flex items-start gap-4">
        <Link href="/cases" className="mt-1 text-muted-foreground hover:text-foreground">
          <ArrowLeft className="size-5" />
        </Link>
        <div className="flex-1">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-xl font-semibold tracking-tight">{caseData.reference}</h1>
            <Badge tone={caseData.status === "submitted" ? "success" : "default"}>
              {caseData.status}
            </Badge>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            {caseData.scope_label ?? "Scoped case"} · {caseData.locale.toUpperCase()}
          </p>
        </div>
      </div>

      {guidance && guidance.phase !== "done" && (
        <Card className="border-primary/30 bg-primary/5">
          <CardContent className="flex flex-col gap-3 pt-5 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-primary">What to do next</p>
              <h2 className="mt-1 text-base font-semibold">{guidance.title}</h2>
              <p className="mt-1 text-sm text-muted-foreground">{guidance.instruction}</p>
              {guidance.blocked_reason && (
                <p className="mt-2 text-sm text-[var(--color-danger)]">{guidance.blocked_reason}</p>
              )}
            </div>
            {guidance.phase !== "blocked" && (
              <Button onClick={() => setActiveStep(phaseToStep(guidance.phase))}>
                {guidance.cta_label}
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {error && (
        <p className="rounded-[var(--radius)] border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/10 px-4 py-3 text-sm text-[var(--color-danger)]">
          {error}
        </p>
      )}

      <div className="flex items-center gap-1 overflow-x-auto pb-2">
        {STEPS.map((s, i) => {
          const isActive = s.key === activeStep;
          return (
            <div key={s.key} className="flex items-center">
              {i > 0 && <ChevronRight className="mx-1 size-3.5 shrink-0 text-muted-foreground" />}
              <button
                onClick={() => setActiveStep(s.key)}
                className={`whitespace-nowrap rounded-[var(--radius)] px-3 py-1.5 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent"
                }`}
              >
                {s.label}
              </button>
            </div>
          );
        })}
      </div>

      <Card>
        <CardContent className="pt-5">
          {stepError && (
            <div className="rounded-[var(--radius)] border border-[var(--color-warning)]/30 bg-[var(--color-warning)]/5 px-4 py-8 text-center">
              <AlertTriangle className="mx-auto mb-3 size-8 text-[var(--color-warning)]/50" />
              <p className="text-sm text-muted-foreground">{stepError}</p>
            </div>
          )}
          {!stepError && activeStep === "intake" && intake && (
            <IntakeStep state={intake} profile={profile} onAnswer={handleAnswer} />
          )}
          {!stepError && activeStep === "eligibility" && (
            <EligibilityStep
              result={eligibility}
              loading={submitting}
              onEvaluate={handleEvaluateEligibility}
            />
          )}
          {!stepError && activeStep === "checklist" && (
            <ChecklistStep
              items={checklist}
              caseId={caseId}
              loading={submitting}
              onRefresh={handleRefreshChecklist}
              onStatusChange={handleChecklistStatus}
            />
          )}
          {!stepError && activeStep === "forms" && (
            <FormsStep
              forms={forms}
              loading={submitting}
              onGenerate={handleGenerateForms}
            />
          )}
          {!stepError && activeStep === "review" && (
            <ReviewStep
              result={review}
              loading={submitting}
              onReview={handleReview}
              onAcknowledge={handleAcknowledgeReview}
            />
          )}
          {!stepError && activeStep === "packet" && (
            <PacketStep
              packet={packet}
              caseData={caseData}
              loading={submitting}
              onBuild={handleBuildPacket}
              onSubmit={handleSubmit}
            />
          )}
        </CardContent>
      </Card>

    </div>
  );
}

function IntakeStep({
  state,
  profile,
  onAnswer,
}: {
  state: IntakeState;
  profile: User | null;
  onAnswer: (key: string, value: unknown) => void;
}) {
  const [drafts, setDrafts] = useState<Record<string, unknown>>({});
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
    };
    const toAutoFill: Record<string, unknown> = {};
    for (const q of state.questions) {
      if (state.answers[q.key] !== undefined || autoSubmittedRef.current.has(q.key)) continue;
      const val = profileMap[q.key];
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

  const pct = state.progress.total > 0
    ? Math.round((state.progress.answered / state.progress.total) * 100)
    : 0;

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-sm font-medium text-muted-foreground">Intake questionnaire</h3>
        <p className="mt-1 text-xs text-muted-foreground">
          {state.progress.answered} of {state.progress.total} questions answered ({pct}%)
          {state.progress.complete ? " · Complete — continue to eligibility" : ""}
        </p>
        <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-muted">
          <div className="h-full bg-primary transition-all" style={{ width: `${pct}%` }} />
        </div>
      </div>

      {state.questions.length === 0 ? (
        <p className="text-sm text-muted-foreground">No questions available for this scope.</p>
      ) : (
        <div className="space-y-4">
          {state.questions.map((q) => {
            const current = (state.answers[q.key] ?? drafts[q.key]) as string | number | boolean | undefined;
            return (
              <div key={q.key} className="space-y-1.5">
                <label className="text-sm font-medium">
                  {q.prompt}
                  {q.required !== false && <span className="ml-1 text-[var(--color-danger)]">*</span>}
                </label>
                {q.type === "enum" && q.options ? (
                  <div className="flex flex-wrap gap-2">
                    {q.options.map((opt) => (
                      <button
                        key={opt}
                        onClick={() => onAnswer(q.key, opt)}
                        className={`rounded-[var(--radius)] border px-3 py-2 text-sm transition-colors ${
                          current === opt
                            ? "border-primary bg-primary/10 text-primary"
                            : "hover:bg-accent"
                        }`}
                      >
                        {opt.replaceAll("_", " ")}
                      </button>
                    ))}
                  </div>
                ) : q.type === "boolean" ? (
                  <div className="flex gap-2">
                    {[true, false].map((v) => (
                      <button
                        key={String(v)}
                        onClick={() => onAnswer(q.key, v)}
                        className={`rounded-[var(--radius)] border px-4 py-2 text-sm transition-colors ${
                          current === v
                            ? "border-primary bg-primary/10 text-primary"
                            : "hover:bg-accent"
                        }`}
                      >
                        {v ? "Yes" : "No"}
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className="flex gap-2">
                    <input
                      type={q.type === "integer" ? "number" : "text"}
                      value={String(current ?? "")}
                      onChange={(e) => handleChange(q.key, e.target.value)}
                      className="h-9 flex-1 rounded-[var(--radius)] border bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    />
                    <Button onClick={() => handleSubmit(q.key)}>Save</Button>
                  </div>
                )}
                {state.answers[q.key] !== undefined && (
                  <p className="text-xs text-[var(--color-success)]">
                    <Check className="mr-1 inline size-3" />
                    Saved
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function EligibilityStep({
  result,
  loading,
  onEvaluate,
}: {
  result: EligibilityResult | null;
  loading: boolean;
  onEvaluate: () => void;
}) {
  const tone =
    result?.result === "pass"
      ? "success"
      : result?.result === "at_risk"
        ? "warning"
        : "danger";

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-sm font-medium text-muted-foreground">Eligibility screening</h3>
        <p className="mt-1 text-xs text-muted-foreground">
          Your answers are checked against published eligibility criteria.
        </p>
      </div>

      {!result ? (
        <div className="flex flex-col items-center py-8 text-center">
          <AlertTriangle className="mb-3 size-8 text-muted-foreground/50" />
          <p className="text-sm text-muted-foreground">
            Eligibility has not been evaluated yet.
          </p>
          <Button onClick={onEvaluate} disabled={loading} className="mt-4">
            {loading ? <Loader2 className="size-4 animate-spin" /> : null}
            Evaluate eligibility
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Badge tone={tone}>{result.result.replaceAll("_", " ")}</Badge>
          </div>
          {result.findings.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No rule failures found for the answers provided.
            </p>
          ) : (
            result.findings.map((finding) => {
              const passed = finding.status === "pass";
              const url = citationUrl(finding.citation);
              const version = citationVersion(finding.citation);
              return (
                <div
                  key={`${finding.key}-${finding.status}`}
                  className={`rounded-[var(--radius)] border p-4 ${
                    passed
                      ? "border-[var(--color-success)]/30 bg-[var(--color-success)]/5"
                      : "border-[var(--color-danger)]/30 bg-[var(--color-danger)]/5"
                  }`}
                >
                  <div className="flex items-start gap-2">
                    {passed ? (
                      <Check className="mt-0.5 size-4 shrink-0 text-[var(--color-success)]" />
                    ) : (
                      <AlertTriangle className="mt-0.5 size-4 shrink-0 text-[var(--color-danger)]" />
                    )}
                    <div className="flex-1">
                      <p className="text-sm font-medium">{finding.key.replaceAll("_", " ")}</p>
                      <p className="mt-1 text-xs text-muted-foreground">{finding.message}</p>
                      {url && (
                        <a
                          href={url}
                          target="_blank"
                          rel="noreferrer"
                          className="mt-2 inline-flex items-center gap-1 text-xs text-primary hover:underline"
                        >
                          Official source{version ? ` (${version})` : ""} <ExternalLink className="size-3" />
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              );
            })
          )}
          <p className="text-xs text-muted-foreground">{result.disclaimer}</p>
        </div>
      )}
    </div>
  );
}

function ChecklistStep({
  items,
  caseId,
  loading,
  onRefresh,
  onStatusChange,
}: {
  items: ChecklistItem[];
  caseId: number;
  loading: boolean;
  onRefresh: () => void;
  onStatusChange: (itemId: number, status: string) => void;
}) {
  const { token } = useAuth();
  const [walletDocs, setWalletDocs] = useState<WalletDocument[]>([]);
  const [attaching, setAttaching] = useState<number | null>(null);
  const [showPicker, setShowPicker] = useState<number | null>(null);
  const [uploading, setUploading] = useState<number | null>(null);
  const [ocrResult, setOcrResult] = useState<OCRResult | null>(null);
  const [ocrLoading, setOcrLoading] = useState(false);
  const [ocrError, setOcrError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pendingItemRef = useRef<ChecklistItem | null>(null);

  useEffect(() => {
    if (!token) return;
    getWallet().then(setWalletDocs).catch(() => {});
  }, [token]);

  function mapDocType(checklistCode: string): DocumentType {
    const code = checklistCode.toLowerCase();
    if (code.includes("passport")) return "passport";
    if (code.includes("residence") || code.includes("card")) return "residence_card";
    return "employment_contract";
  }

  function matchWalletToChecklist(walletDoc: WalletDocument, checklistCode: string): boolean {
    const docType = walletDoc.doc_type.toLowerCase();
    const code = checklistCode.toLowerCase();
    if (code.includes("passport") && docType.includes("passport")) return true;
    if ((code.includes("residence") || code.includes("card")) && docType.includes("residence")) return true;
    if (code.includes("employment") && docType.includes("employment")) return true;
    return docType === code;
  }

  function getMatchingWalletDocs(checklistCode: string): WalletDocument[] {
    return walletDocs.filter((d) => d.status === "active" && matchWalletToChecklist(d, checklistCode));
  }

  async function handleAttachWallet(itemId: number, walletDoc: WalletDocument) {
    if (!token) return;
    setAttaching(itemId);
    try {
      await registerDocument(token, caseId, {
        doc_type: walletDoc.doc_type,
        filename: walletDoc.filename,
        storage_key: `wallet/${walletDoc.id}`,
        extracted_fields: {},
        content_type: walletDoc.content_type,
      });
      await onStatusChange(itemId, "gathered");
      setShowPicker(null);
    } catch {
    } finally {
      setAttaching(null);
    }
  }

  function handleUploadClick(item: ChecklistItem) {
    pendingItemRef.current = item;
    setOcrResult(null);
    setOcrError(null);
    fileInputRef.current?.click();
  }

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    const item = pendingItemRef.current;
    if (!file || !item || !token) return;

    setOcrLoading(true);
    setOcrError(null);
    setUploading(item.id);

    try {
      const docType = mapDocType(item.code);
      const result = await extractFromFile(file, docType);
      setOcrResult(result);

      if (result.needs_recapture) {
        setOcrError("Could not extract fields. Try a clearer image or mark gathered manually.");
      }
    } catch (err) {
      setOcrError(err instanceof Error ? err.message : "OCR failed");
    } finally {
      setOcrLoading(false);
      setUploading(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleConfirmExtracted() {
    const item = pendingItemRef.current;
    if (!item || !token || !ocrResult) return;

    try {
      await registerDocument(token, caseId, {
        doc_type: mapDocType(item.code),
        filename: `checklist-${item.code}.txt`,
        storage_key: `checklist/${item.id}`,
        extracted_fields: ocrResult.fields,
        extraction_confidence: Object.values(ocrResult.fields)[0]?.confidence ?? 0,
      });

      try {
        const { uploadDocument } = await import("@/lib/api/wallet");
        const blob = new Blob([JSON.stringify(ocrResult.fields)], { type: "application/json" });
        const file = new File([blob], `checklist-${item.code}.json`, { type: "application/json" });
        await uploadDocument(file, mapDocType(item.code), item.name);
      } catch {
        // Wallet upload is optional
      }

      await onStatusChange(item.id, "gathered");
      setOcrResult(null);
    } catch (err) {
      setOcrError(err instanceof Error ? err.message : "Registration failed");
    }
  }

  return (
    <div className="space-y-6">
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*,.pdf"
        className="hidden"
        onChange={handleFileChange}
      />

      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-medium text-muted-foreground">Document checklist</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            {items.filter((i) => i.status !== "needed").length} of {items.length} gathered — reuse
            uploaded docs or scan new ones.
          </p>
        </div>
        <Button variant="outline" onClick={onRefresh} disabled={loading}>
          {items.length === 0 ? "Generate checklist" : "Refresh"}
        </Button>
      </div>

      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No checklist items yet. Generate your personalized list after eligibility.
        </p>
      ) : (
        <div className="space-y-3">
          {items.map((item) => {
            const url = citationUrl(item.citation);
            const version = citationVersion(item.citation);
            const matchingDocs = getMatchingWalletDocs(item.code);
            const isGathered = item.status !== "needed";

            return (
              <div
                key={item.id}
                className="rounded-[var(--radius)] border p-4"
              >
                <div className="flex items-start gap-3">
                  <div className="mt-0.5">
                    {isGathered ? (
                      <Check className="size-4 text-[var(--color-success)]" />
                    ) : (
                      <div className="size-4 rounded border border-muted-foreground/30" />
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-sm font-medium">{item.name}</p>
                      {item.is_required && <Badge tone="danger">Required</Badge>}
                      {isGathered && <Badge tone="success">Gathered</Badge>}
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      <span className="font-medium text-foreground">How: </span>
                      {item.how_to_obtain}
                    </p>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      <span className="font-medium text-foreground">Why: </span>
                      {item.why_required}
                    </p>
                    {url && (
                      <a
                        href={url}
                        target="_blank"
                        rel="noreferrer"
                        className="mt-2 inline-flex items-center gap-1 text-xs text-primary hover:underline"
                      >
                        Official source{version ? ` (${version})` : ""} <ExternalLink className="size-3" />
                      </a>
                    )}
                  </div>
                  <div className="flex flex-col gap-1">
                    {!isGathered && matchingDocs.length > 0 && (
                      <button
                        onClick={() => setShowPicker(showPicker === item.id ? null : item.id)}
                        className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs text-primary hover:bg-accent"
                      >
                        <Upload className="size-3" />
                        Reuse ({matchingDocs.length})
                      </button>
                    )}
                    {!isGathered && (
                      <>
                        <button
                          onClick={() => handleUploadClick(item)}
                          disabled={ocrLoading && uploading === item.id}
                          className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs text-primary hover:bg-accent disabled:opacity-50"
                        >
                          {ocrLoading && uploading === item.id ? (
                            <Loader2 className="size-3 animate-spin" />
                          ) : (
                            <Camera className="size-3" />
                          )}
                          Scan
                        </button>
                        <button
                          onClick={() => onStatusChange(item.id, "gathered")}
                          className="rounded px-2 py-1 text-xs text-muted-foreground hover:bg-accent"
                        >
                          Mark gathered
                        </button>
                      </>
                    )}
                    {isGathered && (
                      <button
                        onClick={() => setShowPicker(showPicker === item.id ? null : item.id)}
                        className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs text-muted-foreground hover:bg-accent"
                      >
                        Change
                      </button>
                    )}
                  </div>
                </div>

                {showPicker === item.id && (
                  <div className="mt-3 rounded-[var(--radius)] border border-dashed bg-muted/30 p-3">
                    <p className="mb-2 text-xs font-medium text-muted-foreground">
                      {isGathered ? "Replace with:" : "Select from your documents:"}
                    </p>
                    {matchingDocs.length === 0 ? (
                      <p className="text-xs text-muted-foreground">
                        No matching documents in your wallet. Upload a new one.
                      </p>
                    ) : (
                      <div className="space-y-2">
                        {matchingDocs.map((doc) => (
                          <div
                            key={doc.id}
                            className="flex items-center justify-between rounded border bg-background px-3 py-2"
                          >
                            <div className="min-w-0 flex-1">
                              <p className="truncate text-xs font-medium">{doc.name}</p>
                              <p className="text-[10px] text-muted-foreground">
                                {doc.doc_type} · v{doc.version}
                                {doc.expiry_date && ` · exp ${doc.expiry_date}`}
                              </p>
                            </div>
                            <Button
                              onClick={() => handleAttachWallet(item.id, doc)}
                              disabled={attaching === item.id}
                            >
                              {attaching === item.id ? (
                                <Loader2 className="size-3 animate-spin" />
                              ) : (
                                "Use"
                              )}
                            </Button>
                          </div>
                        ))}
                      </div>
                    )}
                    <button
                      onClick={() => setShowPicker(null)}
                      className="mt-2 text-[10px] text-muted-foreground hover:underline"
                    >
                      Cancel
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {ocrResult && !ocrResult.needs_recapture && (
        <Card className="border-primary/30 bg-primary/5">
          <CardContent className="space-y-3 pt-4">
            <div className="flex items-center gap-2">
              <Check className="size-4 text-[var(--color-success)]" />
              <p className="text-sm font-medium">Document scanned</p>
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              {Object.entries(ocrResult.fields).map(([key, field]) => (
                <div key={key} className="text-xs">
                  <span className="text-muted-foreground">{key.replace(/_/g, " ")}: </span>
                  <span className="font-medium">{field.value}</span>
                  <span className="ml-1 text-muted-foreground">
                    ({Math.round(field.confidence * 100)}%)
                  </span>
                </div>
              ))}
            </div>
            <div className="flex gap-2 pt-1">
              <Button onClick={handleConfirmExtracted}>
                <Check className="size-3" />
                Confirm &amp; attach
              </Button>
              <Button variant="outline" onClick={() => setOcrResult(null)}>
                Dismiss
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {ocrError && (
        <div className="rounded-[var(--radius)] border border-[var(--color-warning)]/30 bg-[var(--color-warning)]/5 px-4 py-3 text-sm text-[var(--color-warning)]">
          {ocrError}
        </div>
      )}
    </div>
  );
}

function FormsStep({
  forms,
  loading,
  onGenerate,
}: {
  forms: GeneratedForm[];
  loading: boolean;
  onGenerate: () => void;
}) {
  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-sm font-medium text-muted-foreground">Generated forms</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            Government forms auto-filled from your intake data.
          </p>
        </div>
        <Button onClick={onGenerate} disabled={loading}>
          {loading ? <Loader2 className="size-4 animate-spin" /> : <FileText className="size-4" />}
          Generate forms
        </Button>
      </div>

      {forms.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No forms generated yet. Complete intake and click generate.
        </p>
      ) : (
        <div className="space-y-4">
          {forms.map((form) => (
            <div key={form.id} className="rounded-[var(--radius)] border p-4">
              <div className="flex items-center gap-2">
                <FileText className="size-4 text-muted-foreground" />
                <p className="font-mono text-sm font-semibold">{form.form_code}</p>
                <Badge tone="muted">v{form.form_version}</Badge>
                {form.missing_required_fields.length > 0 && (
                  <Badge tone="danger">
                    {form.missing_required_fields.length} missing fields
                  </Badge>
                )}
              </div>
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                {Object.entries(form.filled_fields).map(([key, val]) => (
                  <div key={key} className="text-xs">
                    <span className="text-muted-foreground">{key}: </span>
                    <span className="font-medium">{String(val)}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ReviewStep({
  result,
  loading,
  onReview,
  onAcknowledge,
}: {
  result: ReviewResult | null;
  loading: boolean;
  onReview: () => void;
  onAcknowledge: () => void;
}) {
  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-sm font-medium text-muted-foreground">Pre-submission review</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            Consistency check: required fields, cross-document matches, current form versions.
          </p>
        </div>
        <Button variant="outline" onClick={onReview} disabled={loading}>
          Run review
        </Button>
      </div>

      {!result ? (
        <p className="text-sm text-muted-foreground">Click &quot;Run review&quot; to check your packet.</p>
      ) : result.ready ? (
        <div className="flex flex-col items-center py-8 text-center">
          <Check className="mb-3 size-8 text-[var(--color-success)]" />
          <p className="text-sm font-medium">All checks passed</p>
          <p className="mt-1 text-xs text-muted-foreground">Your packet is ready for assembly.</p>
          <Button onClick={onAcknowledge} className="mt-4">
            Continue to packet
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          {result.flags.map((flag, i) => (
            <div
              key={i}
              className="rounded-[var(--radius)] border border-[var(--color-warning)]/30 bg-[var(--color-warning)]/5 p-4"
            >
              <div className="flex items-start gap-2">
                <AlertTriangle className="mt-0.5 size-4 shrink-0 text-[var(--color-warning)]" />
                <div>
                  <p className="text-xs font-medium">{flag.code}</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">{flag.message}</p>
                </div>
              </div>
            </div>
          ))}
          <Button onClick={onAcknowledge} className="mt-2">
            Acknowledge and continue
          </Button>
        </div>
      )}
    </div>
  );
}

function PacketStep({
  packet,
  caseData,
  loading,
  onBuild,
  onSubmit,
}: {
  packet: Record<string, unknown> | null;
  caseData: Case;
  loading: boolean;
  onBuild: () => void;
  onSubmit: () => void;
}) {
  function packetSummaryText(source: Record<string, unknown>): string {
    const forms = Array.isArray(source.forms)
      ? (source.forms as { form_code?: string; form_version?: string }[])
      : [];
    const checklist = Array.isArray(source.checklist)
      ? (source.checklist as { name?: string; status?: string; is_required?: boolean }[])
      : [];
    const requiredTotal = checklist.filter((i) => i.is_required).length;
    const requiredDone = checklist.filter(
      (i) => i.is_required && i.status && i.status !== "needed",
    ).length;
    const lines = [
      "Torii Application Packet Summary",
      `Reference: ${String(source.reference ?? caseData.reference)}`,
      `Scope: ${caseData.scope_label ?? caseData.locale.toUpperCase()}`,
      `Generated at: ${new Date().toISOString()}`,
      "",
      "Forms",
      forms.length === 0
        ? "- No generated forms listed in this packet."
        : forms
          .map((form) => `- ${String(form.form_code ?? "form")} (v${String(form.form_version ?? "n/a")})`)
          .join("\n"),
      "",
      "Checklist",
      `- Required gathered: ${requiredDone}/${requiredTotal}`,
      ...checklist.map(
        (item) => `- ${String(item.name ?? "Document")}: ${String(item.status ?? "needed")}`,
      ),
      "",
      "Submission",
      "- This jurisdiction may require mail/in-person submission if e-file is unavailable.",
    ];
    return lines.join("\n");
  }

  function downloadPacket() {
    if (!packet) return;
    const filename = `${caseData.reference}-packet-summary.txt`;
    const blob = new Blob([packetSummaryText(packet)], {
      type: "text/plain;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-sm font-medium text-muted-foreground">Submission packet</h3>
        <p className="mt-1 text-xs text-muted-foreground">
          Your assembled forms and checklist, ready for submission.
        </p>
      </div>

      {!packet ? (
        <div className="flex flex-col items-center py-8 text-center">
          <Download className="mb-3 size-8 text-muted-foreground/50" />
          <p className="text-sm text-muted-foreground">Packet not yet assembled.</p>
          <Button onClick={onBuild} disabled={loading} className="mt-4">
            {loading ? <Loader2 className="size-4 animate-spin" /> : <Download className="size-4" />}
            Build packet
          </Button>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="rounded-[var(--radius)] border border-[var(--color-success)]/30 bg-[var(--color-success)]/5 p-4">
            <div className="flex items-center gap-2">
              <Check className="size-4 text-[var(--color-success)]" />
              <p className="text-sm font-medium">Packet assembled</p>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              Reference: {String(packet.reference ?? caseData.reference)}
            </p>
          </div>

          <Button variant="outline" onClick={downloadPacket}>
            <Download className="size-4" />
            Download summary
          </Button>

          {caseData.status !== "submitted" && (
            <Button onClick={onSubmit} disabled={loading}>
              {loading ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
              Submit application
            </Button>
          )}

          {caseData.status === "submitted" && (
            <div className="rounded-[var(--radius)] border border-[var(--color-success)]/30 bg-[var(--color-success)]/5 p-4">
              <p className="text-sm font-medium">Submitted</p>
              {caseData.submission_reference && (
                <p className="mt-1 font-mono text-xs">{caseData.submission_reference}</p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
