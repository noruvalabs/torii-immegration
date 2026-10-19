"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft, ArrowRight, ChevronRight, Loader2, AlertTriangle,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { formatScopeLabel } from "@/lib/utils";
import { useAuth } from "@/lib/auth-context";
import { getProfile, type User } from "@/lib/api/auth";
import {
  reviewCase, acknowledgeReview, buildPacket, recordCaseFiled,
  type ReviewResult,
} from "@/lib/api/cases";
import {
  useCaseQuery,
  useCaseGuidanceQuery,
  useIntakeQuery,
  useEligibilityQuery,
  useChecklistQuery,
  useFormsQuery,
  usePacketQuery,
  useAnswerIntakeMutation,
  useEvaluateEligibilityMutation,
  usePatchChecklistItemMutation,
  useRefreshChecklistMutation,
  useGenerateFormsMutation,
  caseKeys,
} from "@/lib/queries/cases";
import { useQueryClient } from "@tanstack/react-query";
import {
  IntakeStep, EligibilityStep, ChecklistStep, FormsStep, ReviewStep, PacketStep, ResearchStep,
  DeadlinesCard, PostSubmissionGuide,
  STEPS, phaseToStep, canVisitStep, nextWorkflowStep,
  type Step,
} from "@/components/applicant/steps";

export default function CaseDetailPage() {
  const params = useParams();
  const caseId = Number(params.id);
  const { token, user } = useAuth();
  const queryClient = useQueryClient();

  const [activeStep, setActiveStep] = useState<Step>("intake");
  const [error, setError] = useState<string | null>(null);
  const [stepError, setStepError] = useState<string | null>(null);
  const [review, setReview] = useState<ReviewResult | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [profile, setProfile] = useState<User | null>(user);
  const [intakeTargetKey, setIntakeTargetKey] = useState<string | null>(null);
  const [intakeTargetTimestamp, setIntakeTargetTimestamp] = useState<number>(0);
  const stepInitializedRef = useRef(false);

  // Cached React Query data
  const { data: caseData, isLoading: caseLoading, isError: caseError } = useCaseQuery(token, caseId);
  const { data: guidance, isLoading: guidanceLoading } = useCaseGuidanceQuery(token, caseId);

  const { data: intake = null } = useIntakeQuery(token, caseId);
  const { data: eligibility = null } = useEligibilityQuery(token, caseId);
  const { data: checklist = [] } = useChecklistQuery(token, caseId);
  const { data: forms = [] } = useFormsQuery(token, caseId);
  const { data: packetFromQuery } = usePacketQuery(token, caseId);

  const packet = packetFromQuery || (caseData?.packet_snapshot as Record<string, unknown> | null) || null;

  // Mutations
  const answerMutation = useAnswerIntakeMutation(token, caseId);
  const evaluateMutation = useEvaluateEligibilityMutation(token, caseId);
  const patchChecklistMutation = usePatchChecklistItemMutation(token, caseId);
  const refreshChecklistMutation = useRefreshChecklistMutation(token, caseId);
  const generateFormsMutation = useGenerateFormsMutation(token, caseId);

  const submitting =
    isSubmitting ||
    answerMutation.isPending ||
    evaluateMutation.isPending ||
    patchChecklistMutation.isPending ||
    refreshChecklistMutation.isPending ||
    generateFormsMutation.isPending;

  // Jump to guidance phase only on initial load
  useEffect(() => {
    if (guidance && !stepInitializedRef.current) {
      setActiveStep(phaseToStep(guidance.phase));
      stepInitializedRef.current = true;
    }
  }, [guidance]);

  useEffect(() => {
    if (token) {
      getProfile(token).then(setProfile).catch(() => {});
    }
  }, [token]);

  // Auto-evaluate if eligibility step opened and no result yet
  useEffect(() => {
    if (activeStep === "eligibility" && token && caseId && eligibility === null && !evaluateMutation.isPending) {
      void evaluateMutation.mutateAsync().catch(() => {});
    }
  }, [activeStep, token, caseId, eligibility, evaluateMutation]);

  const handleResearchPhaseChange = useCallback((phase: string) => {
    setActiveStep(phaseToStep(phase));
    void queryClient.invalidateQueries({ queryKey: caseKeys.guidance(caseId) });
    void queryClient.invalidateQueries({ queryKey: caseKeys.detail(caseId) });
  }, [caseId, queryClient]);

  function trySetStep(step: Step) {
    if (guidance?.phase === "research" && step !== "research") {
      toast.error("Requirements research is currently in progress. Please wait a moment.", {
        id: "research-in-progress",
      });
      return;
    }
    setError(null);
    setStepError(null);
    setActiveStep(step);
    if (step === "eligibility" && !eligibility) {
      void handleEvaluateEligibility();
    }
  }

  function goToGuidancePhase() {
    if (!guidance) return;
    setError(null);
    setActiveStep(phaseToStep(guidance.phase));
  }

  const handleNavigateToIntakeQuestion = useCallback((targetKey?: string | null) => {
    setError(null);
    setStepError(null);
    setIntakeTargetKey(targetKey || null);
    setIntakeTargetTimestamp(Date.now());
    setActiveStep("intake");
  }, []);

  async function handleAnswer(key: string, value: unknown) {
    if (!token) return;
    setError(null);
    try {
      const state = await answerMutation.mutateAsync({ key, value });
      if (state.progress.complete) {
        toast.dismiss("incomplete-intake-warning");
      }
    } catch (e) {
      throw e;
    }
  }

  async function handleEvaluateEligibility() {
    if (!token) return;
    setError(null);
    try {
      await evaluateMutation.mutateAsync();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Evaluation failed");
    }
  }

  async function handleRefreshChecklist() {
    if (!token) return;
    setError(null);
    try {
      await refreshChecklistMutation.mutateAsync();
      const prof = await getProfile(token).catch(() => null);
      if (prof) setProfile(prof);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to refresh checklist");
    }
  }

  async function handleChecklistStatus(itemId: number, status: string) {
    if (!token) return;
    try {
      await patchChecklistMutation.mutateAsync({ itemId, status });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Update failed");
    }
  }

  async function handleGenerateForms() {
    if (!token) return;
    setError(null);
    try {
      await generateFormsMutation.mutateAsync();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Form generation failed");
    }
  }

  async function handleReview() {
    if (!token) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const result = await reviewCase(token, caseId);
      setReview(result);
      void queryClient.invalidateQueries({ queryKey: caseKeys.guidance(caseId) });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Review failed");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleAcknowledgeReview() {
    if (!token) return;
    try {
      await acknowledgeReview(token, caseId);
      void queryClient.invalidateQueries({ queryKey: caseKeys.guidance(caseId) });
      setActiveStep("packet");
      try {
        const built = await buildPacket(token, caseId);
        queryClient.setQueryData(caseKeys.packet(caseId), built);
      } catch {
        // Fallback: PacketStep UI renders manual build button
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Acknowledge failed");
    }
  }

  async function handleBuildPacket() {
    if (!token) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const built = await buildPacket(token, caseId);
      queryClient.setQueryData(caseKeys.packet(caseId), built);
      void queryClient.invalidateQueries({ queryKey: caseKeys.guidance(caseId) });
      void queryClient.invalidateQueries({ queryKey: caseKeys.detail(caseId) });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Packet build failed");
    } finally {
      setIsSubmitting(false);
    }
  }

  /** The applicant telling us they have filed it — not a request for Torii to file it. */
  async function handleSubmit() {
    if (!token) return;
    setIsSubmitting(true);
    setError(null);
    try {
      await recordCaseFiled(token, caseId);
      void queryClient.invalidateQueries({ queryKey: caseKeys.detail(caseId) });
      void queryClient.invalidateQueries({ queryKey: caseKeys.guidance(caseId) });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not record the application as filed");
    } finally {
      setIsSubmitting(false);
    }
  }

  /** Whether the current view is complete enough to move to the server next phase. */
  function canAdvanceFromCurrent(): boolean {
    return true;
  }

  function continueNext() {
    setError(null);
    const next = nextWorkflowStep(activeStep);
    if (next) {
      setActiveStep(next);
      if (next === "eligibility" && !eligibility) {
        void handleEvaluateEligibility();
      }
      return;
    }
    const phaseStep = phaseToStep(guidance?.phase || "intake");
    setActiveStep(phaseStep);
  }

  const initialLoading = (caseLoading || guidanceLoading) && !caseData;
  if (initialLoading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (caseError || !caseData) {
    return (
      <div className="mx-auto max-w-2xl py-12 text-center">
        <p className="text-muted-foreground">Case not found.</p>
        <Link href="/cases" className="mt-4 inline-block text-sm text-primary hover:underline">
          Back to cases
        </Link>
      </div>
    );
  }

  const showContinue =
    guidance &&
    guidance.phase !== "blocked" &&
    guidance.phase !== "done" &&
    activeStep !== "intake" &&
    activeStep !== "research" &&
    activeStep !== "review" &&
    activeStep !== "packet";

  return (
    <div className="w-full max-w-7xl mx-auto space-y-6">
      <div className="flex items-start gap-4">
        <Link href="/cases" className="mt-1 text-muted-foreground hover:text-foreground">
          <ArrowLeft className="size-5" />
        </Link>
        <div className="flex-1">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-xl font-semibold tracking-tight">
              {formatScopeLabel(caseData.scope_label) || caseData.reference}
            </h1>
            <Badge tone={caseData.status === "submitted" ? "success" : "default"}>
              {caseData.status}
            </Badge>
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            <span className="font-mono text-xs bg-muted px-2 py-0.5 rounded font-medium text-foreground">
              {caseData.reference}
            </span>
            <span>·</span>
            <span>{caseData.locale.toUpperCase()}</span>
          </div>
        </div>
      </div>

      {/* Filing deadlines surface whenever guidance carries them (residence expiry known). */}
      {guidance && guidance.deadlines && (
        <DeadlinesCard deadlines={guidance.deadlines} />
      )}

      {/* Post-submission guidance & next steps */}
      {caseData.status === "submitted" ? (
        activeStep !== "packet" ? (
          <PostSubmissionGuide
            token={token}
            caseData={caseData}
            onRefresh={() => {
              void queryClient.invalidateQueries({ queryKey: caseKeys.detail(caseId) });
              void queryClient.invalidateQueries({ queryKey: caseKeys.guidance(caseId) });
            }}
          />
        ) : null
      ) : (
        guidance && guidance.phase !== "done" && (
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
              {guidance.phase !== "blocked" && phaseToStep(guidance.phase) !== activeStep && (
                <Button onClick={goToGuidancePhase} className="shrink-0">
                  {guidance.cta_label}
                </Button>
              )}
            </CardContent>
          </Card>
        )
      )}

      {error && (
        <p className="rounded-[var(--radius)] border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/10 px-4 py-3 text-sm text-[var(--color-danger)]">
          {error}
        </p>
      )}

      <div className="flex items-center gap-1 overflow-x-auto pb-2">
        {STEPS.map((s, i) => {
          const isActive = s.key === activeStep;
          const allowed = !guidance || canVisitStep(s.key, guidance.phase);
          return (
            <div key={s.key} className="flex items-center">
              {i > 0 && <ChevronRight className="mx-1 size-3.5 shrink-0 text-muted-foreground" />}
              <button
                onClick={() => trySetStep(s.key)}
                disabled={!allowed}
                title={allowed ? s.label : "Complete earlier required steps first"}
                className={`whitespace-nowrap rounded-[var(--radius)] px-3 py-1.5 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : allowed
                      ? "text-muted-foreground hover:bg-accent"
                      : "cursor-not-allowed text-muted-foreground/40"
                }`}
              >
                {s.label}
              </button>
            </div>
          );
        })}
      </div>

      {intake && !intake.progress.complete && activeStep !== "intake" && activeStep !== "research" && caseData?.status !== "submitted" && (
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3.5 text-xs text-amber-900 dark:text-amber-200 shadow-xs">
          <div className="flex items-start sm:items-center gap-2.5 min-w-0">
            <AlertTriangle className="size-4 shrink-0 text-amber-600 dark:text-amber-400 mt-0.5 sm:mt-0" />
            <div>
              <p className="font-semibold text-amber-900 dark:text-amber-100">
                Intake Questionnaire has {intake.progress.total - intake.progress.answered} incomplete question(s).
              </p>
              <p className="text-[11px] text-amber-700 dark:text-amber-300 mt-0.5">
                You can preview eligibility, checklists, and forms, but all required fields must be answered before final packet submission.
              </p>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setError(null);
              setActiveStep("intake");
            }}
            className="h-7 text-xs border-amber-500/40 text-amber-800 dark:text-amber-200 hover:bg-amber-500/20 shrink-0 self-end sm:self-auto font-medium"
          >
            Return to Intake
          </Button>
        </div>
      )}

      <Card>
        <CardContent className="pt-5">
          {stepError && (
            <div className="rounded-[var(--radius)] border border-[var(--color-warning)]/30 bg-[var(--color-warning)]/5 px-4 py-8 text-center">
              <AlertTriangle className="mx-auto mb-3 size-8 text-[var(--color-warning)]/50" />
              <p className="text-sm text-muted-foreground">{stepError}</p>
            </div>
          )}
          {!stepError && activeStep === "research" && token && (
            <ResearchStep
              caseId={caseId}
              token={token}
              onPhaseChange={handleResearchPhaseChange}
            />
          )}
          {!stepError && activeStep === "intake" && intake && (
            <IntakeStep
              state={intake}
              profile={profile || user}
              onAnswer={handleAnswer}
              targetKey={intakeTargetKey}
              targetTimestamp={intakeTargetTimestamp}
              token={token || undefined}
              caseId={caseId}
              onRefresh={() => {
                void queryClient.invalidateQueries({ queryKey: caseKeys.intake(caseId) });
                void queryClient.invalidateQueries({ queryKey: caseKeys.detail(caseId) });
                if (token) getProfile(token).then(setProfile).catch(() => {});
              }}
              onProceedToEligibility={() => {
                setError(null);
                setActiveStep("eligibility");
                void handleEvaluateEligibility();
                if (!intake.progress.complete) {
                  const remaining = intake.progress.total - intake.progress.answered;
                  toast.warning("Incomplete Intake Questionnaire", {
                    id: "incomplete-intake-warning",
                    description: `You have ${remaining} incomplete question(s). You can preview subsequent steps, but all required fields must be answered before final packet submission.`,
                    duration: 4500,
                  });
                }
              }}
            />
          )}
          {!stepError && activeStep === "eligibility" && (
            <EligibilityStep
              result={eligibility}
              loading={submitting}
              onEvaluate={handleEvaluateEligibility}
              jurisdictionCode={caseData?.reference ? caseData.reference.split("-")[0] : "JP"}
              jurisdictionName={caseData?.scope_label ? caseData.scope_label.split("·")[0]?.trim() : undefined}
              visaCategoryName={caseData?.scope_label || caseData?.visa_category_code || ""}
              onReturnToIntake={handleNavigateToIntakeQuestion}
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
              intakeAnswers={caseData.intake_answers}
              caseId={caseId}
              reference={caseData.reference}
            />
          )}
          {!stepError && activeStep === "review" && (
            <ReviewStep
              result={review}
              loading={submitting}
              onReview={handleReview}
              onAcknowledge={handleAcknowledgeReview}
              questions={intake?.questions}
              onNavigateToQuestion={handleNavigateToIntakeQuestion}
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

          {showContinue && (
            <div className="mt-6 flex flex-col gap-2 border-t pt-4 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-xs text-muted-foreground">
                Steps only unlock when required work for the current phase is complete.
              </p>
              <Button
                onClick={continueNext}
                disabled={!canAdvanceFromCurrent()}
              >
                Continue to next step
                <ArrowRight className="size-4" />
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

