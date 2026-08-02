"use client";

import { Check, AlertTriangle, ExternalLink, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { EligibilityResult } from "./types";
import { citationUrl, citationVersion } from "./types";

type EligibilityStepProps = {
  result: EligibilityResult | null;
  loading: boolean;
  onEvaluate: () => void;
};

export function EligibilityStep({ result, loading, onEvaluate }: EligibilityStepProps) {
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
