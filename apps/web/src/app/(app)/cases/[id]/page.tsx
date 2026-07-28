"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft, Check, ChevronRight, ClipboardCheck, FileText,
  Loader2, AlertTriangle, Send, Download,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";
import {
  getCase, getIntake, answerIntake, evaluateEligibility, getEligibility,
  refreshChecklist, getChecklist, patchChecklistItem,
  generateForms, getForms, reviewCase, acknowledgeReview,
  buildPacket, getPacket, submitCase,
  type Case, type IntakeState, type EligibilityResult,
  type ChecklistItem, type GeneratedForm, type ReviewResult,
} from "@/lib/api/cases";

type Step = "intake" | "eligibility" | "checklist" | "forms" | "review" | "packet";

const STEPS: { key: Step; label: string }[] = [
  { key: "intake", label: "Intake" },
  { key: "eligibility", label: "Eligibility" },
  { key: "checklist", label: "Checklist" },
  { key: "forms", label: "Forms" },
  { key: "review", label: "Review" },
  { key: "packet", label: "Packet" },
];

export default function CaseDetailPage() {
  const params = useParams();
  const caseId = Number(params.id);
  const { token } = useAuth();
  const router = useRouter();

  const [caseData, setCaseData] = useState<Case | null>(null);
  const [activeStep, setActiveStep] = useState<Step>("intake");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Step data
  const [intake, setIntake] = useState<IntakeState | null>(null);
  const [eligibility, setEligibility] = useState<EligibilityResult | null>(null);
  const [checklist, setChecklist] = useState<ChecklistItem[]>([]);
  const [forms, setForms] = useState<GeneratedForm[]>([]);
  const [review, setReview] = useState<ReviewResult | null>(null);
  const [packet, setPacket] = useState<Record<string, unknown> | null>(null);

  const [submitting, setSubmitting] = useState(false);

  const loadCase = useCallback(async () => {
    if (!token || !caseId) return;
    setLoading(true);
    try {
      const c = await getCase(token, caseId);
      setCaseData(c);
      // Determine starting step from case status
      if (c.status === "draft") setActiveStep("intake");
      else if (c.status === "intake_complete") setActiveStep("eligibility");
      else if (c.status === "checklist_ready") setActiveStep("checklist");
      else if (c.status === "forms_generated") setActiveStep("forms");
      else if (c.status === "packet_ready") setActiveStep("packet");
      else setActiveStep("intake");
    } catch {
      setError("Could not load case.");
    } finally {
      setLoading(false);
    }
  }, [token, caseId]);

  useEffect(() => { void loadCase(); }, [loadCase]);

  // Load step data when activeStep changes
  useEffect(() => {
    if (!token || !caseId) return;
    if (activeStep === "intake") {
      getIntake(token, caseId).then(setIntake).catch(() => {});
    } else if (activeStep === "eligibility") {
      getEligibility(token, caseId).then(setEligibility).catch(() => setEligibility(null));
    } else if (activeStep === "checklist") {
      getChecklist(token, caseId).then(setChecklist).catch(() => {});
    } else if (activeStep === "forms") {
      getForms(token, caseId).then(setForms).catch(() => {});
    } else if (activeStep === "review") {
      reviewCase(token, caseId).then(setReview).catch(() => {});
    } else if (activeStep === "packet") {
      getPacket(token, caseId).then(setPacket).catch(() => setPacket(null));
    }
  }, [token, caseId, activeStep]);

  async function handleAnswer(key: string, value: unknown) {
    if (!token) return;
    setError(null);
    try {
      const state = await answerIntake(token, caseId, key, value);
      setIntake(state);
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
      setActiveStep("packet");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to acknowledge");
    }
  }

  async function handleBuildPacket() {
    if (!token) return;
    setSubmitting(true);
    setError(null);
    try {
      const snap = await buildPacket(token, caseId);
      setPacket(snap);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Packet assembly failed");
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
      {/* Header */}
      <div className="flex items-start gap-4">
        <Link href="/cases" className="mt-1 text-muted-foreground hover:text-foreground">
          <ArrowLeft className="size-5" />
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-semibold tracking-tight">{caseData.reference}</h1>
            <Badge tone={caseData.status === "submitted" ? "success" : "default"}>
              {caseData.status}
            </Badge>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            {caseData.locale.toUpperCase()} locale · Complete each step below.
          </p>
        </div>
      </div>

      {error && (
        <p className="rounded-[var(--radius)] border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/10 px-4 py-3 text-sm text-[var(--color-danger)]">
          {error}
        </p>
      )}

      {/* Step nav */}
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

      {/* Step content */}
      <Card>
        <CardContent className="pt-5">
          {activeStep === "intake" && intake && (
            <IntakeStep state={intake} onAnswer={handleAnswer} />
          )}
          {activeStep === "eligibility" && (
            <EligibilityStep
              result={eligibility}
              loading={submitting}
              onEvaluate={handleEvaluateEligibility}
            />
          )}
          {activeStep === "checklist" && (
            <ChecklistStep
              items={checklist}
              loading={submitting}
              onRefresh={handleRefreshChecklist}
              onStatusChange={handleChecklistStatus}
            />
          )}
          {activeStep === "forms" && (
            <FormsStep
              forms={forms}
              loading={submitting}
              onGenerate={handleGenerateForms}
            />
          )}
          {activeStep === "review" && (
            <ReviewStep
              result={review}
              loading={submitting}
              onReview={handleReview}
              onAcknowledge={handleAcknowledgeReview}
            />
          )}
          {activeStep === "packet" && (
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

// ── Intake Step ────────────────────────────────────────────────────────────────

function IntakeStep({
  state,
  onAnswer,
}: {
  state: IntakeState;
  onAnswer: (key: string, value: unknown) => void;
}) {
  const [drafts, setDrafts] = useState<Record<string, unknown>>({});

  function handleChange(key: string, value: unknown) {
    setDrafts((prev) => ({ ...prev, [key]: value }));
  }

  function handleSubmit(key: string) {
    if (drafts[key] !== undefined) {
      onAnswer(key, drafts[key]);
    }
  }

  const pct = state.progress.total > 0
    ? Math.round((state.progress.current / state.progress.total) * 100)
    : 0;

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-sm font-medium text-muted-foreground">Intake questionnaire</h3>
        <p className="mt-1 text-xs text-muted-foreground">
          {state.progress.current} of {state.progress.total} questions answered ({pct}%)
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
                  {q.label}
                  {q.required && <span className="ml-1 text-[var(--color-danger)]">*</span>}
                </label>
                {q.hint && <p className="text-xs text-muted-foreground">{q.hint}</p>}
                {q.kind === "select" && q.options ? (
                  <div className="flex gap-2">
                    {q.options.map((opt) => (
                      <button
                        key={opt.value}
                        onClick={() => {
                          handleChange(q.key, opt.value);
                          handleSubmit(q.key);
                        }}
                        className={`rounded-[var(--radius)] border px-3 py-2 text-sm transition-colors ${
                          current === opt.value
                            ? "border-primary bg-primary/10 text-primary"
                            : "hover:bg-accent"
                        }`}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                ) : q.kind === "bool" ? (
                  <div className="flex gap-2">
                    {["true", "false"].map((v) => (
                      <button
                        key={v}
                        onClick={() => {
                          handleChange(q.key, v === "true");
                          handleSubmit(q.key);
                        }}
                        className={`rounded-[var(--radius)] border px-4 py-2 text-sm transition-colors ${
                          String(current) === v
                            ? "border-primary bg-primary/10 text-primary"
                            : "hover:bg-accent"
                        }`}
                      >
                        {v === "true" ? "Yes" : "No"}
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className="flex gap-2">
                    <input
                      type={q.kind === "number" ? "number" : q.kind === "date" ? "date" : "text"}
                      value={String(current ?? "")}
                      onChange={(e) => handleChange(q.key, e.target.value)}
                      className="h-9 flex-1 rounded-[var(--radius)] border bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      placeholder={q.hint ?? ""}
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

// ── Eligibility Step ───────────────────────────────────────────────────────────

function EligibilityStep({
  result,
  loading,
  onEvaluate,
}: {
  result: EligibilityResult | null;
  loading: boolean;
  onEvaluate: () => void;
}) {
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
            <Badge tone={result.eligible ? "success" : "danger"}>
              {result.eligible ? "Eligible" : "Issues found"}
            </Badge>
          </div>
          {result.checks.map((check) => (
            <div
              key={check.key}
              className={`rounded-[var(--radius)] border p-4 ${
                check.passed
                  ? "border-[var(--color-success)]/30 bg-[var(--color-success)]/5"
                  : "border-[var(--color-danger)]/30 bg-[var(--color-danger)]/5"
              }`}
            >
              <div className="flex items-start gap-2">
                {check.passed ? (
                  <Check className="mt-0.5 size-4 shrink-0 text-[var(--color-success)]" />
                ) : (
                  <AlertTriangle className="mt-0.5 size-4 shrink-0 text-[var(--color-danger)]" />
                )}
                <div className="flex-1">
                  <p className="text-sm font-medium">{check.label}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{check.message}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Checklist Step ─────────────────────────────────────────────────────────────

function ChecklistStep({
  items,
  loading,
  onRefresh,
  onStatusChange,
}: {
  items: ChecklistItem[];
  loading: boolean;
  onRefresh: () => void;
  onStatusChange: (itemId: number, status: string) => void;
}) {
  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-sm font-medium text-muted-foreground">Document checklist</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            {items.filter((i) => i.status !== "needed").length} of {items.length} completed
          </p>
        </div>
        <Button variant="outline" onClick={onRefresh} disabled={loading}>
          Refresh
        </Button>
      </div>

      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">No checklist items yet. Click refresh to generate.</p>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <div
              key={item.id}
              className="flex items-start gap-3 rounded-[var(--radius)] border p-4"
            >
              <div className="mt-0.5">
                {item.status === "uploaded" ? (
                  <Check className="size-4 text-[var(--color-success)]" />
                ) : item.status === "gathered" ? (
                  <Check className="size-4 text-[var(--color-warning)]" />
                ) : (
                  <div className="size-4 rounded border border-muted-foreground/30" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-medium">{item.name}</p>
                  {item.is_required && <Badge tone="danger">Required</Badge>}
                  {item.status === "uploaded" && <Badge tone="success">Uploaded</Badge>}
                  {item.status === "gathered" && <Badge tone="warning">Gathered</Badge>}
                </div>
                <p className="mt-1 text-xs text-muted-foreground">{item.how_to_obtain}</p>
                <p className="mt-0.5 text-xs text-muted-foreground italic">Why: {item.why_required}</p>
              </div>
              <div className="flex gap-1">
                {item.status === "needed" && (
                  <button
                    onClick={() => onStatusChange(item.id, "gathered")}
                    className="rounded px-2 py-1 text-xs text-muted-foreground hover:bg-accent"
                  >
                    Mark gathered
                  </button>
                )}
                {item.status === "gathered" && (
                  <button
                    onClick={() => onStatusChange(item.id, "uploaded")}
                    className="rounded px-2 py-1 text-xs text-muted-foreground hover:bg-accent"
                  >
                    Mark uploaded
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Forms Step ─────────────────────────────────────────────────────────────────

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
              {form.missing_required_fields.length > 0 && (
                <p className="mt-2 text-xs text-[var(--color-danger)]">
                  Missing: {form.missing_required_fields.join(", ")}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Review Step ────────────────────────────────────────────────────────────────

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
      ) : result.flags.length === 0 ? (
        <div className="flex flex-col items-center py-8 text-center">
          <Check className="mb-3 size-8 text-[var(--color-success)]" />
          <p className="text-sm font-medium">All checks passed</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Your packet is ready for assembly.
          </p>
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

// ── Packet Step ────────────────────────────────────────────────────────────────

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

          {Array.isArray(packet.forms) && (
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Forms included
              </p>
              {(packet.forms as { form_code?: string; form_version?: string }[]).map((f, i) => (
                <div key={i} className="flex items-center gap-2 py-1 text-sm">
                  <FileText className="size-3.5 text-muted-foreground" />
                  <span className="font-mono">{String(f.form_code)}</span>
                  <Badge tone="muted">v{String(f.form_version)}</Badge>
                </div>
              ))}
            </div>
          )}

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
