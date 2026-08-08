"use client";

import { Check, AlertTriangle, Info } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ReviewResult } from "./types";

type ReviewStepProps = {
  result: ReviewResult | null;
  loading: boolean;
  onReview: () => void;
  onAcknowledge: () => void;
};

export function ReviewStep({ result, loading, onReview, onAcknowledge }: ReviewStepProps) {
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
      ) : (
        <div className="space-y-4">
          {/* Review checks */}
          {result.checks.length > 0 && (
            <div className="space-y-2">
              {result.checks.map((check, i) => (
                <div
                  key={`${check.code}-${i}`}
                  className={`flex items-start gap-2 rounded-[var(--radius)] border px-4 py-2.5 ${
                    check.passed
                      ? "border-[var(--color-success)]/20 bg-[var(--color-success)]/5"
                      : "border-[var(--color-warning)]/20 bg-[var(--color-warning)]/5"
                  }`}
                >
                  {check.passed ? (
                    <Check className="mt-0.5 size-3.5 shrink-0 text-[var(--color-success)]" />
                  ) : (
                    <Info className="mt-0.5 size-3.5 shrink-0 text-[var(--color-warning)]" />
                  )}
                  <p className="text-xs text-foreground/80">{check.message}</p>
                </div>
              ))}
            </div>
          )}

          {/* Review flags (problems) */}
          {result.flags.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-medium text-[var(--color-danger)]">Issues found:</p>
              {result.flags.map((flag, i) => (
                <div
                  key={i}
                  className="rounded-[var(--radius)] border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/5 p-4"
                >
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="mt-0.5 size-4 shrink-0 text-[var(--color-danger)]" />
                    <div>
                      <p className="text-xs font-medium">{flag.code}</p>
                      <p className="mt-0.5 text-xs text-muted-foreground">{flag.message}</p>
                      {flag.fields && flag.fields.length > 0 && (
                        <p className="mt-1 text-[10px] text-muted-foreground">
                          Fields: {flag.fields.join(", ")}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Ready banner */}
          {result.ready && (
            <div className="flex flex-col items-center rounded-[var(--radius)] border border-[var(--color-success)]/30 bg-[var(--color-success)]/5 py-6 text-center">
              <Check className="mb-3 size-8 text-[var(--color-success)]" />
              <p className="text-sm font-medium">All checks passed</p>
              <p className="mt-1 text-xs text-muted-foreground">Your packet is ready for assembly.</p>
              <Button onClick={onAcknowledge} className="mt-4">
                Continue to packet
              </Button>
            </div>
          )}

          {/* Acknowledge button when there are flags */}
          {!result.ready && result.flags.length > 0 && (
            <Button onClick={onAcknowledge} className="mt-2">
              Acknowledge and continue
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
