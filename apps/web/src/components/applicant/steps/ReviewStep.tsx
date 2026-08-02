"use client";

import { Check, AlertTriangle, Loader2 } from "lucide-react";
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
