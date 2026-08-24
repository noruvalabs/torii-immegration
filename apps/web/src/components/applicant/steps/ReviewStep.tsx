"use client";

import { Check, AlertTriangle, Info, ShieldCheck, ShieldAlert, Sparkles, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import type { ReviewResult } from "./types";

type ReviewStepProps = {
  result: ReviewResult | null;
  loading: boolean;
  onReview: () => void;
  onAcknowledge: () => void;
};

export function ReviewStep({ result, loading, onReview, onAcknowledge }: ReviewStepProps) {
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
        <Button onClick={onReview} disabled={loading} className="w-fit">
          <Sparkles className="mr-1.5 size-4" />
          {loading ? "Auditing Application..." : "Run Risk Audit"}
        </Button>
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
                {result.flags.map((flag, i) => (
                  <div
                    key={i}
                    className="rounded-xl border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/5 p-4 space-y-1.5 transition-all"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-start gap-2">
                        <AlertTriangle className="mt-0.5 size-4 shrink-0 text-[var(--color-danger)]" />
                        <div>
                          <p className="text-xs font-bold text-foreground uppercase tracking-wide">
                            {flag.code.replace(/_/g, " ")}
                          </p>
                          <p className="mt-0.5 text-xs text-foreground/90 leading-relaxed">{flag.message}</p>
                          {flag.fields && flag.fields.length > 0 && (
                            <p className="mt-1 text-[11px] text-muted-foreground font-mono">
                              Associated Field(s): {flag.fields.join(", ")}
                            </p>
                          )}
                        </div>
                      </div>
                      <Badge tone="danger" className="text-[10px] shrink-0">
                        Check Required
                      </Badge>
                    </div>
                  </div>
                ))}
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
