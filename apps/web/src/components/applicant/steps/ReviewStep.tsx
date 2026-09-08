"use client";

import { Check, AlertTriangle, Info, ShieldCheck, ShieldAlert, Sparkles, ExternalLink, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import type { ReviewResult, IntakeQuestion } from "./types";
import { resolveFieldInfo } from "./types";

type ReviewStepProps = {
  result: ReviewResult | null;
  loading: boolean;
  onReview: () => void;
  onAcknowledge: () => void;
  questions?: IntakeQuestion[];
  onNavigateToQuestion?: (targetKey: string) => void;
};

export function ReviewStep({
  result,
  loading,
  onReview,
  onAcknowledge,
  questions = [],
  onNavigateToQuestion,
}: ReviewStepProps) {
  // Calculate Visa Readiness Score
  const totalChecks = (result?.checks?.length || 0) + (result?.flags?.length || 0);
  const passedChecks = result?.checks?.filter((c) => c.passed).length || 0;
  const score = totalChecks > 0 ? Math.round((passedChecks / totalChecks) * 100) : 100;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-base font-semibold text-foreground">Pre-Submission Rejection Risk Audit</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            Multi-pillar consistency check: passport validity, statutory filing window, salary threshold, and tax compliance.
          </p>
        </div>
        {result && (
          <Button onClick={onReview} disabled={loading} variant="outline" className="w-fit h-8 text-xs">
            <Sparkles className="mr-1.5 size-3.5" />
            {loading ? "Auditing Application..." : "Re-run Risk Audit"}
          </Button>
        )}
      </div>

      {!result ? (
        <Card>
          <CardContent className="flex flex-col items-center py-10 text-center space-y-3">
            <ShieldCheck className="size-10 text-primary/50" />
            <div>
              <p className="text-base font-semibold">Perform Automated Legal &amp; Consistency Audit</p>
              <p className="text-xs text-muted-foreground mt-1 max-w-md mx-auto">
                Scan your answers against official government criteria (ICAO passport rules, ISA 90-day filing window, minimum salary standards, and attendance gates).
              </p>
            </div>
            <Button onClick={onReview} disabled={loading} className="mt-2">
              Run Pre-Submission Audit
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          {/* Top Audit Score Header Card */}
          <Card className={result.ready ? "border-emerald-500/30 bg-emerald-500/5" : "border-amber-500/30 bg-amber-500/5"}>
            <CardContent className="p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-center gap-3.5">
                <div className={`flex size-12 items-center justify-center rounded-2xl border ${result.ready ? "bg-emerald-500/10 text-emerald-600 border-emerald-500/20" : "bg-amber-500/10 text-amber-600 border-amber-500/20"}`}>
                  {result.ready ? <ShieldCheck className="size-6" /> : <ShieldAlert className="size-6" />}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h4 className="text-base font-bold text-foreground">
                      {result.ready ? "Application Certified Ready for Submission" : "Audit Advisory & Discrepancy Findings"}
                    </h4>
                    <Badge tone={result.ready ? "success" : "warning"}>
                      Health Score: {score}/100
                    </Badge>
                  </div>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {result.ready
                      ? "All statutory government criteria passed. Zero blocking discrepancy flags detected."
                      : `${result.flags.length} issue(s) or advisory notes require your confirmation prior to dossier assembly.`}
                  </p>
                </div>
              </div>

              {result.ready ? (
                <Button onClick={onAcknowledge} className="shrink-0 font-semibold shadow">
                  Proceed to Filing Kit &amp; Packet
                </Button>
              ) : (
                <Button onClick={onAcknowledge} variant="outline" className="shrink-0 font-semibold">
                  Acknowledge &amp; Proceed
                </Button>
              )}
            </CardContent>
          </Card>

          {/* Audit Flags (Issues or Warnings) */}
          {result.flags.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--color-danger)] flex items-center gap-1.5">
                <AlertTriangle className="size-3.5" />
                Action Required / Advisory Flags ({result.flags.length})
              </h4>
              <div className="grid gap-2.5">
                {result.flags.map((flag, i) => {
                  const hasFields = flag.fields && flag.fields.length > 0;
                  const firstTargetKey = hasFields ? resolveFieldInfo(flag.fields![0], questions).targetKey : null;
                  const isMissingFieldsFlag = flag.code === "missing_form_fields";

                  return (
                    <div
                      key={i}
                      className="rounded-xl border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/5 p-4 space-y-2 transition-all"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-start gap-2.5 flex-1 min-w-0">
                          <AlertTriangle className="mt-0.5 size-4 shrink-0 text-[var(--color-danger)]" />
                          <div className="space-y-1.5 flex-1 min-w-0">
                            <p className="text-xs font-bold text-foreground uppercase tracking-wide">
                              {flag.code.replace(/_/g, " ")}
                            </p>
                            <p className="text-xs text-foreground/90 leading-relaxed">
                              {isMissingFieldsFlag
                                ? "Required fields in official application forms are incomplete. Answer the corresponding intake questions below:"
                                : flag.message}
                            </p>
                            {hasFields && (
                              <div className="pt-1 flex flex-wrap items-center gap-1.5">
                                <span className="text-[11px] font-semibold text-muted-foreground mr-1">
                                  {isMissingFieldsFlag ? "Required Question(s):" : "Associated Field(s):"}
                                </span>
                                {flag.fields!.map((field) => {
                                  const info = resolveFieldInfo(field, questions);
                                  return (
                                    <button
                                      key={field}
                                      type="button"
                                      onClick={() => onNavigateToQuestion?.(info.targetKey)}
                                      title={
                                        info.prompt
                                          ? `Go directly to: "${info.prompt}"`
                                          : `Go directly to ${info.displayName} in Intake`
                                      }
                                      className="group inline-flex items-center gap-1.5 rounded-lg border border-rose-500/30 bg-background/90 hover:bg-rose-500/10 hover:border-rose-500/60 px-2.5 py-1 text-xs font-medium text-foreground transition-all shadow-2xs hover:shadow-xs cursor-pointer"
                                    >
                                      <span className="text-rose-600 dark:text-rose-400 font-semibold">
                                        {info.displayName}
                                      </span>
                                      <span className="text-[10px] text-muted-foreground font-mono">
                                        ({info.exactFieldName})
                                      </span>
                                      <ArrowRight className="size-3 text-muted-foreground group-hover:text-rose-600 dark:group-hover:text-rose-400 transition-transform group-hover:translate-x-0.5" />
                                    </button>
                                  );
                                })}
                              </div>
                            )}
                          </div>
                        </div>

                        {onNavigateToQuestion && firstTargetKey ? (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => onNavigateToQuestion(firstTargetKey)}
                            className="h-7 text-[11px] gap-1 shrink-0 border-rose-500/40 text-rose-700 dark:text-rose-300 hover:bg-rose-500/10 hover:border-rose-500 font-semibold shadow-2xs cursor-pointer"
                          >
                            <span>Fix in Intake</span>
                            <ArrowRight className="size-3" />
                          </Button>
                        ) : (
                          <Badge tone="danger" className="text-[10px] shrink-0">
                            Check Required
                          </Badge>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Verified Statutory Checks */}
          {result.checks.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <Check className="size-3.5 text-emerald-600" />
                Verified Statutory Checks ({result.checks.length})
              </h4>
              <div className="grid gap-2 sm:grid-cols-2">
                {result.checks.map((check, i) => (
                  <div
                    key={`${check.code}-${i}`}
                    className="flex items-start gap-2.5 rounded-xl border border-border bg-card p-3.5 shadow-xs"
                  >
                    <div className="flex size-5 shrink-0 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-600 mt-0.5">
                      <Check className="size-3" />
                    </div>
                    <div className="space-y-0.5">
                      <p className="text-xs font-semibold text-foreground">
                        {check.code.replace(/_/g, " ").replace(/^form /, "Form ").replace(/ ok$/, " (Verified)")}
                      </p>
                      <p className="text-[11px] text-muted-foreground leading-snug">{check.message}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
