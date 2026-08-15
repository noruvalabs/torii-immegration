"use client";

import { Check, AlertTriangle, ExternalLink, Loader2, ShieldCheck, Scale, AlertOctagon, HelpCircle, CheckCircle2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { EligibilityResult } from "./types";
import { citationUrl, citationVersion } from "./types";

type EligibilityStepProps = {
  result: EligibilityResult | null;
  loading: boolean;
  onEvaluate: () => void;
};

export function EligibilityStep({ result, loading, onEvaluate }: EligibilityStepProps) {
  const overallTone =
    result?.result === "pass"
      ? "success"
      : result?.result === "at_risk"
        ? "warning"
        : "danger";

  // Group findings or evaluate pillar status
  const findings = result?.findings || [];
  const failCount = findings.filter((f) => f.status === "fail").length;
  const atRiskCount = findings.filter((f) => f.status === "at_risk").length;
  const reviewCount = findings.filter((f) => f.status === "out_of_scope").length;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-foreground">Section 214(b) INA Eligibility Screening</h3>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Deterministic rules evaluation under the Immigration and Nationality Act (INA) Section 214(b) &amp; Section 212(a).
          </p>
        </div>

        <Button onClick={onEvaluate} disabled={loading} className="gap-1.5 shrink-0 h-8 px-3 text-xs">
          {loading ? <Loader2 className="size-4 animate-spin" /> : <Scale className="size-4" />}
          {result ? "Re-evaluate screening" : "Evaluate eligibility now"}
        </Button>
      </div>

      {!result ? (
        <div className="rounded-[var(--radius)] border border-dashed p-8 text-center bg-muted/20 space-y-3">
          <Scale className="mx-auto size-10 text-muted-foreground/40" />
          <h4 className="text-sm font-semibold">Eligibility check has not been run</h4>
          <p className="text-xs text-muted-foreground max-w-md mx-auto">
            Click &quot;Evaluate eligibility now&quot; above. Torii will assess your profile across the 4 statutory pillars: Institutional/Trip Feasibility, Financial Capacity, Nonimmigrant Ties, and Inadmissibility Screening.
          </p>
          <Button onClick={onEvaluate} disabled={loading} className="mt-2">
            {loading ? <Loader2 className="mr-2 size-4 animate-spin" /> : <Scale className="mr-2 size-4" />}
            Run 4-Pillar evaluation
          </Button>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Status Header Banner */}
          <div
            className={`rounded-[var(--radius)] border p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-sm ${
              result.result === "pass"
                ? "border-emerald-500/30 bg-emerald-500/5 text-emerald-950 dark:text-emerald-100"
                : result.result === "at_risk"
                  ? "border-amber-500/30 bg-amber-500/5 text-amber-950 dark:text-amber-100"
                  : "border-[var(--color-danger)]/30 bg-[var(--color-danger)]/5 text-rose-950 dark:text-rose-100"
            }`}
          >
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <Badge tone={overallTone} className="uppercase font-bold tracking-wider text-xs px-2.5 py-0.5">
                  {result.result.replaceAll("_", " ")}
                </Badge>
                <span className="text-xs font-semibold">
                  {result.result === "pass"
                    ? "Strong Nonimmigrant Profile"
                    : result.result === "at_risk"
                      ? "Attention / Preparation Recommended"
                      : "Critical Inadmissibility / Ineligibility Flag"}
                </span>
              </div>
              <p className="text-xs opacity-90 max-w-xl">
                {result.result === "pass"
                  ? "Your intake profile fulfills core INA 214(b) statutory criteria. Proceed to prepare required supporting documents."
                  : result.result === "at_risk"
                    ? "One or more factors require additional supporting documentation (e.g. proof of liquid funds, employer leave letter)."
                    : "Statutory ineligibility or disqualification detected. Consular review and formal explanations will be required."}
              </p>
            </div>

            <div className="flex gap-2 shrink-0">
              {failCount > 0 && (
                <Badge tone="danger" className="text-xs gap-1">
                  <AlertOctagon className="size-3" /> {failCount} Red Flags
                </Badge>
              )}
              {atRiskCount > 0 && (
                <Badge tone="warning" className="text-xs gap-1">
                  <AlertTriangle className="size-3" /> {atRiskCount} Warnings
                </Badge>
              )}
              {reviewCount > 0 && (
                <Badge tone="muted" className="text-xs gap-1">
                  <HelpCircle className="size-3" /> {reviewCount} Reviews
                </Badge>
              )}
              {failCount === 0 && atRiskCount === 0 && (
                <Badge tone="success" className="text-xs gap-1">
                  <CheckCircle2 className="size-3" /> 100% Eligible
                </Badge>
              )}
            </div>
          </div>

          {/* 4 Pillars Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <Card className="p-3.5 bg-card">
              <div className="flex items-start gap-2.5">
                <div className="size-7 rounded-md bg-primary/10 flex items-center justify-center text-primary font-bold text-xs shrink-0">
                  1
                </div>
                <div>
                  <h5 className="text-xs font-bold uppercase tracking-wider text-foreground">
                    Institutional &amp; Trip Qualification
                  </h5>
                  <p className="text-[11px] text-muted-foreground mt-0.5">
                    Valid I-20/SEVIS registration or concrete tourist itinerary matching declared duration.
                  </p>
                </div>
              </div>
            </Card>

            <Card className="p-3.5 bg-card">
              <div className="flex items-start gap-2.5">
                <div className="size-7 rounded-md bg-emerald-500/10 flex items-center justify-center text-emerald-600 font-bold text-xs shrink-0">
                  2
                </div>
                <div>
                  <h5 className="text-xs font-bold uppercase tracking-wider text-foreground">
                    Financial Capacity (INA 214(b))
                  </h5>
                  <p className="text-[11px] text-muted-foreground mt-0.5">
                    Liquid bank balance covering Year 1 total cost / full travel budget without unauthorized U.S. work.
                  </p>
                </div>
              </div>
            </Card>

            <Card className="p-3.5 bg-card">
              <div className="flex items-start gap-2.5">
                <div className="size-7 rounded-md bg-blue-500/10 flex items-center justify-center text-blue-600 font-bold text-xs shrink-0">
                  3
                </div>
                <div>
                  <h5 className="text-xs font-bold uppercase tracking-wider text-foreground">
                    Nonimmigrant Intent &amp; Japan Ties
                  </h5>
                  <p className="text-[11px] text-muted-foreground mt-0.5">
                    Stable employment, valid residence status in Japan, and clear return roadmap.
                  </p>
                </div>
              </div>
            </Card>

            <Card className="p-3.5 bg-card">
              <div className="flex items-start gap-2.5">
                <div className="size-7 rounded-md bg-purple-500/10 flex items-center justify-center text-purple-600 font-bold text-xs shrink-0">
                  4
                </div>
                <div>
                  <h5 className="text-xs font-bold uppercase tracking-wider text-foreground">
                    General Admissibility (INA 212(a))
                  </h5>
                  <p className="text-[11px] text-muted-foreground mt-0.5">
                    Clean immigration history, no unresolved visa overstays, and interview preparedness.
                  </p>
                </div>
              </div>
            </Card>
          </div>

          {/* Detailed Findings List */}
          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-foreground">Evaluated Rule Findings &amp; Regulatory Citations</h4>

            {findings.length === 0 ? (
              <div className="rounded-[var(--radius)] border p-4 bg-emerald-500/5 text-center text-xs text-muted-foreground">
                All statutory rules and checks passed successfully. No compliance red flags found.
              </div>
            ) : (
              findings.map((finding) => {
                const isFail = finding.status === "fail";
                const isWarning = finding.status === "at_risk";
                const isReview = finding.status === "out_of_scope";
                const url = citationUrl(finding.citation);
                const version = citationVersion(finding.citation);

                return (
                  <div
                    key={`${finding.key}-${finding.status}`}
                    className={`rounded-[var(--radius)] border p-4 transition-all ${
                      isFail
                        ? "border-[var(--color-danger)]/30 bg-[var(--color-danger)]/5"
                        : isWarning
                          ? "border-[var(--color-warning)]/30 bg-[var(--color-warning)]/5"
                          : isReview
                            ? "border-blue-500/30 bg-blue-500/5"
                            : "border-emerald-500/30 bg-emerald-500/5"
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      {isFail ? (
                        <AlertOctagon className="mt-0.5 size-5 shrink-0 text-[var(--color-danger)]" />
                      ) : isWarning ? (
                        <AlertTriangle className="mt-0.5 size-5 shrink-0 text-[var(--color-warning)]" />
                      ) : isReview ? (
                        <HelpCircle className="mt-0.5 size-5 shrink-0 text-blue-500" />
                      ) : (
                        <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-emerald-500" />
                      )}

                      <div className="flex-1 space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="text-sm font-bold capitalize text-foreground">
                            {finding.key.replaceAll("_", " ")}
                          </p>
                          <Badge
                            tone={isFail ? "danger" : isWarning ? "warning" : "muted"}
                            className="text-[10px] uppercase font-semibold"
                          >
                            {finding.status}
                          </Badge>
                        </div>

                        <p className="text-xs text-foreground/80 leading-relaxed">{finding.message}</p>

                        {url && (
                          <div className="pt-1">
                            <a
                              href={url}
                              target="_blank"
                              rel="noreferrer"
                              className="inline-flex items-center gap-1 text-[11px] text-primary hover:underline font-medium"
                            >
                              <span>
                                {String(finding.citation?.authority || "Official Authority")}: {String(finding.citation?.title || "Regulatory Source")}
                                {version ? ` (${version})` : ""}
                              </span>
                              <ExternalLink className="size-3" />
                            </a>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          <div className="rounded-md bg-muted/40 p-3 text-[11px] text-muted-foreground flex items-center gap-2 border">
            <ShieldCheck className="size-4 text-primary shrink-0" />
            <span>{result.disclaimer}</span>
          </div>
        </div>
      )}
    </div>
  );
}
