"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft, ChevronRight, Loader2, AlertTriangle,
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
  buildPacket, getPacket, submitCase,
  type Case, type CaseGuidance, type IntakeState, type EligibilityResult,
  type ChecklistItem, type GeneratedForm, type ReviewResult,
} from "@/lib/api/cases";
import {
  IntakeStep, EligibilityStep, ChecklistStep, FormsStep, ReviewStep, PacketStep,
  STEPS, phaseToStep,
  type Step,
} from "@/components/applicant/steps";

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
