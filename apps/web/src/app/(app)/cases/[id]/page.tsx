"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft, ArrowRight, ChevronRight, Loader2, AlertTriangle, ExternalLink, CheckCircle2,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { formatScopeLabel } from "@/lib/utils";
import { useAuth } from "@/lib/auth-context";
import { getProfile, type User } from "@/lib/api/auth";
import {
  reviewCase, acknowledgeReview, buildPacket, recordCaseFiled, patchCase,
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
  QuickEligibilityAndPayment,
  DeadlinesCard, PostSubmissionGuide,
  STEPS, phaseToStep, canVisitStep, nextWorkflowStep,
  type Step,
} from "@/components/applicant/steps";

export default function CaseDetailPage() {
  const params = useParams();
  const caseId = Number(params.id);
  const { token, user } = useAuth();
  const queryClient = useQueryClient();

  const [activeStep, setActiveStep] = useState<Step>("eligibility");
  const [error, setError] = useState<string | null>(null);
  const [stepError, setStepError] = useState<string | null>(null);
  const [review, setReview] = useState<ReviewResult | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [profile, setProfile] = useState<User | null>(user);
  const [intakeTargetKey, setIntakeTargetKey] = useState<string | null>(null);
  const [intakeTargetTimestamp, setIntakeTargetTimestamp] = useState<number>(0);
  const stepInitializedRef = useRef(false);
  const checklistAutoTriggeredRef = useRef(false);

  // Cached React Query data
  const { data: caseData, isLoading: caseLoading, isError: caseError } = useCaseQuery(token, caseId);
  const { data: guidance, isLoading: guidanceLoading } = useCaseGuidanceQuery(token, caseId);

  const { data: intake = null } = useIntakeQuery(token, caseId);
  const { data: eligibility = null } = useEligibilityQuery(token, caseId);
  const { data: checklist = [] } = useChecklistQuery(token, caseId);
  const { data: forms = [] } = useFormsQuery(token, caseId);
  const { data: packetFromQuery } = usePacketQuery(token, caseId);

  const packet = packetFromQuery || (caseData?.packet_snapshot as Record<string, unknown> | null) || null;

  const requiredChecklistItems = useMemo(
    () => checklist.filter((item) => item.is_required),
    [checklist]
  );
  const missingRequiredDocs = useMemo(
    () => requiredChecklistItems.filter((item) => item.status === "needed"),
    [requiredChecklistItems]
  );
  const areAllRequiredDocsUploaded =
    checklist.length > 0 && missingRequiredDocs.length === 0;

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

  // Determine if payment & eligibility screening are complete
  const isCasePaid = useMemo(() => {
    if (!caseData) return false;
    const ia = (caseData.intake_answers || {}) as Record<string, unknown>;
    return (
      caseData.status === "payment_completed" ||
      caseData.status === "submitted" ||
      caseData.status === "eligibility_checked" ||
      caseData.status === "checklist_ready" ||
      caseData.status === "forms_generated" ||
      caseData.status === "packet_ready" ||
      ia.payment_status === "completed" ||
      Boolean(ia.payment_txn_id) ||
      Boolean(caseData.is_entitled)
    );
  }, [caseData]);

  // Jump to appropriate phase on initial load
  useEffect(() => {
    if (caseData && !stepInitializedRef.current) {
      if (!isCasePaid) {
        setActiveStep("eligibility");
      } else if (guidance && guidance.phase !== "blocked") {
        setActiveStep(phaseToStep(guidance.phase));
      } else {
        setActiveStep("intake");
      }
      stepInitializedRef.current = true;
    }
  }, [guidance, caseData, isCasePaid]);

  useEffect(() => {
    if (token) {
      getProfile(token).then(setProfile).catch(() => {});
    }
  }, [token]);

  useEffect(() => {
    if (activeStep === "forms" || activeStep === "review") {
      setActiveStep("packet");
    }
  }, [activeStep]);

  useEffect(() => {
    if (
      activeStep === "checklist" &&
      checklist.length === 0 &&
      !refreshChecklistMutation.isPending &&
      token &&
      !checklistAutoTriggeredRef.current
    ) {
      checklistAutoTriggeredRef.current = true;
      void handleRefreshChecklist();
    }
  }, [activeStep, checklist.length, refreshChecklistMutation.isPending, token]);

  // Poll silently in background every 3 seconds while research is running
  useEffect(() => {
    if (guidance?.phase !== "research") return;
    const interval = setInterval(() => {
      void queryClient.invalidateQueries({ queryKey: caseKeys.guidance(caseId) });
      void queryClient.invalidateQueries({ queryKey: caseKeys.intake(caseId) });
      void queryClient.invalidateQueries({ queryKey: caseKeys.checklist(caseId) });
    }, 3000);
    return () => clearInterval(interval);
  }, [guidance?.phase, caseId, queryClient]);

  // Toast notification when AI background research finishes
  const prevPhaseRef = useRef(guidance?.phase);
  useEffect(() => {
    if (prevPhaseRef.current === "research" && guidance?.phase && guidance.phase !== "research") {
      toast.success("✨ Embassy requirements successfully tailored to your profile!", {
        id: "research-complete-toast",
        duration: 4500,
      });
      void queryClient.invalidateQueries({ queryKey: caseKeys.intake(caseId) });
      void queryClient.invalidateQueries({ queryKey: caseKeys.checklist(caseId) });
    }
    prevPhaseRef.current = guidance?.phase;
  }, [guidance?.phase, caseId, queryClient]);

  const handleResearchPhaseChange = useCallback((phase: string) => {
    setActiveStep(phaseToStep(phase));
    void queryClient.invalidateQueries({ queryKey: caseKeys.guidance(caseId) });
    void queryClient.invalidateQueries({ queryKey: caseKeys.detail(caseId) });
  }, [caseId, queryClient]);

  function trySetStep(step: Step) {
    if (guidance?.phase === "research" && (step === "checklist" || step === "packet")) {
      toast.info("Torii AI is currently finalizing your custom document checklist. Please continue filling out your application form below!", {
        id: "research-in-progress",
      });
      setActiveStep("intake");
      return;
    }
    if (step === "packet" && !areAllRequiredDocsUploaded && caseData?.status !== "submitted") {
      toast.error(
        `Please upload all required documents (${missingRequiredDocs.length} remaining) before moving to submission.`,
        { id: "missing-docs-packet-blocked" }
      );
      setActiveStep("checklist");
      return;
    }
    setError(null);
    setStepError(null);
    setActiveStep(step);
    if (step === "eligibility" && !eligibility) {
      void handleEvaluateEligibility();
    }
    if (step === "checklist" && checklist.length === 0 && !refreshChecklistMutation.isPending) {
      void handleRefreshChecklist();
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

  /** Submit the completed case to the database and Torii operations console */
  async function handleSubmit() {
    if (!token) return;
    if (!areAllRequiredDocsUploaded && caseData?.status !== "submitted") {
      toast.error(
        `Cannot submit application: Please upload all ${missingRequiredDocs.length} remaining required document(s) before submitting.`,
        { id: "missing-docs-submit-blocked" }
      );
      setActiveStep("checklist");
      return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
      try {
        await buildPacket(token, caseId);
      } catch {
        // Continue if build packet has warnings
      }
      await patchCase(token, caseId, { status: "submitted" });
      try {
        await recordCaseFiled(token, caseId);
      } catch {
        // Fallback
      }
      void queryClient.invalidateQueries({ queryKey: caseKeys.detail(caseId) });
      void queryClient.invalidateQueries({ queryKey: caseKeys.guidance(caseId) });
      toast.success("Application successfully submitted to Torii Operations Concierge!");
      setActiveStep("packet");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not record the application as submitted");
    } finally {
      setIsSubmitting(false);
    }
  }

  /** Whether the current view is complete enough to move to the server next phase. */
  function canAdvanceFromCurrent(): boolean {
    if (activeStep === "checklist") {
      return areAllRequiredDocsUploaded;
    }
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
    activeStep !== "eligibility" &&
    activeStep !== "intake" &&
    activeStep !== "research" &&
    activeStep !== "review" &&
    activeStep !== "packet";

  return (
    <div className="w-full max-w-7xl mx-auto space-y-6 pb-16 sm:pb-24">
      {(user?.role === "admin" || user?.role === "ops") && (
        <div className="rounded-xl border border-primary/30 bg-primary/10 p-3.5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="default" className="text-[10px] uppercase font-bold tracking-wider">
              Staff Concierge Mode
            </Badge>
            <span className="text-foreground font-medium">
              You are inspecting this case as Staff. All particulars are formatted for government portal filing.
            </span>
          </div>
          <Link
            href={`/admin/cases/${caseId}`}
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-bold text-primary-foreground shadow-xs hover:bg-primary/90 transition-colors shrink-0"
          >
            <span>Open Government Filing Console</span>
            <ExternalLink className="size-3.5" />
          </Link>
        </div>
      )}

      <div className="flex items-start gap-4">
        <Link href="/cases" className="mt-1 text-muted-foreground hover:text-foreground">
          <ArrowLeft className="size-5" />
        </Link>
        <div className="flex-1">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-xl font-semibold tracking-tight">
              {formatScopeLabel(caseData.scope_label) || caseData.reference}
            </h1>
            <Badge
              tone={isCasePaid ? "success" : "warning"}
              className="gap-1 font-semibold"
            >
              {caseData.status === "submitted"
                ? "Submitted to Embassy"
                : isCasePaid
                  ? "Paid · In Concierge Queue"
                  : "Eligibility & Payment Pending"}
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
        isCasePaid && guidance && guidance.phase !== "done" && (
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
          const isPacketLocked = s.key === "packet" && !areAllRequiredDocsUploaded && caseData?.status !== "submitted";
          const allowed = (!guidance || canVisitStep(s.key, guidance.phase)) && !isPacketLocked;
          return (
            <div key={s.key} className="flex items-center">
              {i > 0 && <ChevronRight className="mx-1 size-3.5 shrink-0 text-muted-foreground" />}
              <button
                onClick={() => trySetStep(s.key)}
                disabled={!allowed}
                title={
                  isPacketLocked
                    ? `Upload all required documents (${missingRequiredDocs.length} remaining) to unlock submission`
                    : allowed
                      ? s.label
                      : "Complete earlier required steps first"
                }
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

      {guidance?.phase === "research" && activeStep !== "research" && (
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 rounded-lg border border-primary/30 bg-primary/10 p-3.5 text-xs text-primary shadow-xs">
          <div className="flex items-start sm:items-center gap-2.5 min-w-0">
            <Loader2 className="size-4 animate-spin text-primary shrink-0 mt-0.5 sm:mt-0" />
            <div>
              <p className="font-semibold text-primary-900 dark:text-primary-100">
                Torii AI is analyzing official embassy requirements in the background...
              </p>
              <p className="text-[11px] text-primary-700 dark:text-primary-300 mt-0.5">
                Go ahead and fill out your personal & passport information below. Your customized document checklist will be ready by the time you finish!
              </p>
            </div>
          </div>
          <span className="inline-flex items-center rounded-full bg-primary/20 px-2.5 py-0.5 text-[11px] font-medium text-primary shrink-0">
            Auto-syncing
          </span>
        </div>
      )}

      {intake && !intake.progress.complete && activeStep !== "intake" && activeStep !== "research" && activeStep !== "eligibility" && caseData?.status !== "submitted" && (
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3.5 text-xs text-amber-900 dark:text-amber-200 shadow-xs">
          <div className="flex items-start sm:items-center gap-2.5 min-w-0">
            <AlertTriangle className="size-4 shrink-0 text-amber-600 dark:text-amber-400 mt-0.5 sm:mt-0" />
            <div>
              <p className="font-semibold text-amber-900 dark:text-amber-100">
                Intake Questionnaire has {intake.progress.total - intake.progress.answered} incomplete question(s).
              </p>
              <p className="text-[11px] text-amber-700 dark:text-amber-300 mt-0.5">
                You can preview checklists and forms, but all required fields must be answered before final staff submission.
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
          {!stepError && activeStep === "eligibility" && (
            <QuickEligibilityAndPayment
              caseData={caseData}
              token={token}
              onProceedToForm={() => {
                setError(null);
                setActiveStep("intake");
              }}
              onPaymentSuccess={() => {
                void queryClient.invalidateQueries({ queryKey: caseKeys.detail(caseId) });
                void queryClient.invalidateQueries({ queryKey: caseKeys.guidance(caseId) });
              }}
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
                setActiveStep("checklist");
                void handleRefreshChecklist();
                if (!intake.progress.complete) {
                  const remaining = intake.progress.total - intake.progress.answered;
                  toast.warning("Incomplete Intake Questionnaire", {
                    id: "incomplete-intake-warning",
                    description: `You have ${remaining} incomplete question(s). You can continue with documents, but ensure all fields are answered before final filing.`,
                    duration: 4500,
                  });
                }
              }}
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
              canSubmit={areAllRequiredDocsUploaded || caseData?.status === "submitted"}
              missingDocsCount={missingRequiredDocs.length}
              onGoToChecklist={() => setActiveStep("checklist")}
            />
          )}

          {showContinue && (
            <div className="mt-6 flex flex-col gap-2 border-t pt-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="space-y-0.5">
                <p className="text-xs text-muted-foreground">
                  {activeStep === "checklist" ? (
                    areAllRequiredDocsUploaded ? (
                      <span className="text-emerald-600 dark:text-emerald-400 font-semibold flex items-center gap-1.5">
                        <CheckCircle2 className="size-3.5" />
                        All required documents uploaded ({requiredChecklistItems.length}/{requiredChecklistItems.length}). Ready to submit.
                      </span>
                    ) : (
                      <span className="text-amber-600 dark:text-amber-400 font-semibold flex items-center gap-1.5">
                        <AlertTriangle className="size-3.5" />
                        {missingRequiredDocs.length} required document{missingRequiredDocs.length > 1 ? "s" : ""} must be uploaded before submitting.
                      </span>
                    )
                  ) : (
                    "Steps only unlock when required work for the current phase is complete."
                  )}
                </p>
                {activeStep === "checklist" && !areAllRequiredDocsUploaded && missingRequiredDocs.length > 0 && (
                  <p className="text-[11px] text-muted-foreground">
                    Required: {missingRequiredDocs.slice(0, 3).map((d) => d.name).join(", ")}
                    {missingRequiredDocs.length > 3 ? ` +${missingRequiredDocs.length - 3} more` : ""}
                  </p>
                )}
              </div>
              <Button
                onClick={activeStep === "checklist" ? handleSubmit : continueNext}
                disabled={!canAdvanceFromCurrent() || isSubmitting}
                className={
                  activeStep === "checklist"
                    ? areAllRequiredDocsUploaded
                      ? "bg-emerald-600 hover:bg-emerald-700 text-white font-semibold shadow-sm gap-2"
                      : "bg-muted text-muted-foreground cursor-not-allowed opacity-60 gap-2 border"
                    : "gap-2"
                }
              >
                {activeStep === "checklist" ? (
                  isSubmitting ? (
                    <>
                      <Loader2 className="size-4 animate-spin" />
                      <span>Submitting...</span>
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="size-4" />
                      <span>Submit to Operations</span>
                    </>
                  )
                ) : (
                  <>
                    <span>Continue to next step</span>
                    <ArrowRight className="size-4" />
                  </>
                )}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

