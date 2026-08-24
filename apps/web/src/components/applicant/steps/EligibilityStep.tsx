"use client";

import { Check, AlertTriangle, ExternalLink, Loader2, ShieldCheck, Scale, AlertOctagon, HelpCircle, CheckCircle2, ArrowRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { EligibilityResult } from "./types";
import { citationUrl, citationVersion } from "./types";

type EligibilityStepProps = {
  result: EligibilityResult | null;
  loading: boolean;
  onEvaluate: () => void;
  jurisdictionCode?: string;
  jurisdictionName?: string;
  visaCategoryName?: string;
  onReturnToIntake?: (targetKey?: string) => void;
};

export function EligibilityStep({
  result,
  loading,
  onEvaluate,
  jurisdictionCode = "JP",
  jurisdictionName,
  visaCategoryName = "",
  onReturnToIntake,
}: EligibilityStepProps) {
  const code = jurisdictionCode?.toUpperCase() || "JP";
  const countryName = jurisdictionName || (code === "JP" ? "Japan" : code === "GB" || code === "UK" ? "United Kingdom" : code === "US" ? "United States" : "Destination");

  const catNorm = (visaCategoryName || "").toLowerCase();
  const isStudent = catNorm.includes("student") || catNorm.includes("study");
  const isWork = catNorm.includes("work") || catNorm.includes("h1b") || catNorm.includes("employment") || catNorm.includes("labor");

  // Dynamic header copy based on jurisdiction and category
  const headerTitle =
    code === "JP"
      ? `Japan ${isStudent ? "Student" : isWork ? "Work" : "Visa"} Eligibility Assessment`
      : code === "GB" || code === "UK"
        ? `UK Visa & Immigration (UKVI) ${isStudent ? "Student Route" : isWork ? "Skilled Worker" : "Standard Visitor"} Eligibility Assessment`
        : code === "US"
          ? `US Visa Eligibility & INA Section 214(b) Screening`
          : `${countryName} Visa Eligibility Screening`;

  const headerSubtitle =
    code === "GB" || code === "UK"
      ? isStudent
        ? "Evaluation under UK Immigration Rules (Appendix Student: Licensed Sponsor, CAS validity & Maintenance requirements)."
        : isWork
          ? "Evaluation under UK Immigration Rules (Appendix Skilled Worker: Certificate of Sponsorship & Salary threshold)."
          : "Evaluation under UK Immigration Rules (Appendix V: Visitor Route statutory criteria)."
      : code === "JP"
        ? "Deterministic evaluation under the Immigration Control and Refugee Recognition Act (出入国管理及び難民認定法) & MOFA criteria."
        : code === "US"
          ? "Deterministic rules evaluation under the Immigration and Nationality Act (INA) Section 214(b) & Section 212(a)."
          : `Deterministic rules evaluation against official ${countryName} immigration requirements.`;

  const overallTone =
    result?.result === "pass"
      ? "success"
      : result?.result === "at_risk"
        ? "warning"
        : result?.result === "out_of_scope"
          ? "muted"
          : "danger";

  // Group findings
  const findings = result?.findings || [];
  const passCount = findings.filter((f) => f.status === "pass").length;
  const failCount = findings.filter((f) => f.status === "fail").length;
  const atRiskCount = findings.filter((f) => f.status === "at_risk").length;
  const reviewCount = findings.filter((f) => f.status === "out_of_scope").length;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-foreground">{headerTitle}</h3>
          <p className="mt-0.5 text-xs text-muted-foreground">{headerSubtitle}</p>
        </div>

        {result && (
          <Button onClick={onEvaluate} disabled={loading} variant="outline" className="gap-1.5 shrink-0 h-8 px-3 text-xs">
            {loading ? <Loader2 className="size-3.5 animate-spin" /> : <Scale className="size-3.5" />}
            Re-evaluate screening
          </Button>
        )}
      </div>

      {!result ? (
        <div className="rounded-[var(--radius)] border border-dashed p-8 text-center bg-muted/20 space-y-3">
          <Scale className="mx-auto size-10 text-muted-foreground/40" />
          <h4 className="text-sm font-semibold">Eligibility check has not been run</h4>
          <p className="text-xs text-muted-foreground max-w-md mx-auto">
            Click &quot;Evaluate eligibility now&quot; above. Torii will evaluate your completed intake answers against official {countryName} immigration regulations, landing requirements, and financial criteria.
          </p>
          <Button onClick={onEvaluate} disabled={loading} className="mt-2">
            {loading ? <Loader2 className="mr-2 size-4 animate-spin" /> : <Scale className="mr-2 size-4" />}
            Evaluate eligibility now
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
                  : result.result === "out_of_scope"
                    ? "border-blue-500/30 bg-blue-500/5 text-blue-950 dark:text-blue-100"
                    : "border-[var(--color-danger)]/30 bg-[var(--color-danger)]/5 text-rose-950 dark:text-rose-100"
            }`}
          >
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <Badge tone={overallTone} className="uppercase font-bold tracking-wider text-xs px-2.5 py-0.5">
                  {result.result === "pass"
                    ? "PASS · FULLY ELIGIBLE"
                    : result.result === "at_risk"
                      ? "AT RISK · ATTENTION RECOMMENDED"
                      : result.result === "out_of_scope"
                        ? "INCOMPLETE · PENDING INTAKE ANSWERS"
                        : "INELIGIBLE · STATUTORY CRITICAL FLAG"}
                </Badge>
                <span className="text-xs font-semibold">
                  {result.result === "pass"
                    ? `Fulfills Core ${countryName} Visa Criteria`
                    : result.result === "at_risk"
                      ? "Preparation / Additional Documentation Recommended"
                      : result.result === "out_of_scope"
                        ? "Additional Intake Information Needed"
                        : "Statutory Disqualification or Inadmissibility Detected"}
                </span>
              </div>
              <p className="text-xs opacity-90 max-w-xl">
                {result.result === "pass"
                  ? `Your intake profile fulfills official ${countryName} statutory criteria. Proceed to prepare your supporting documents in the checklist.`
                  : result.result === "at_risk"
                    ? "One or more factors recommend stronger supporting evidence (e.g. liquid bank balance, leave approval letter, or sponsor guarantee)."
                    : result.result === "out_of_scope"
                      ? "Some required intake questions have not been answered yet. Return to Intake to complete all fields so full evaluation can run."
                      : "One or more answers conflict with statutory landing requirements (e.g. prior deportation or overstay ban). Consular review required."}
              </p>
              {result.result === "out_of_scope" && onReturnToIntake && (
                <div className="pt-2">
                  <Button
                    size="sm"
                    onClick={() => onReturnToIntake()}
                    className="h-7 text-xs gap-1.5 bg-blue-600 hover:bg-blue-700 text-white font-medium"
                  >
                    Return to Intake to Answer Missing Fields <ArrowRight className="size-3.5" />
                  </Button>
                </div>
              )}
            </div>

            <div className="flex gap-2 shrink-0">
              {failCount > 0 && (
                <Badge tone="danger" className="text-xs gap-1">
                  <AlertOctagon className="size-3" /> {failCount} Disqualified
                </Badge>
              )}
              {atRiskCount > 0 && (
                <Badge tone="warning" className="text-xs gap-1">
                  <AlertTriangle className="size-3" /> {atRiskCount} Warnings
                </Badge>
              )}
              {reviewCount > 0 && (
                <Badge tone="muted" className="text-xs gap-1">
                  <HelpCircle className="size-3" /> {reviewCount} Missing Answers
                </Badge>
              )}
              {failCount === 0 && atRiskCount === 0 && reviewCount === 0 && (
                <Badge tone="success" className="text-xs gap-1">
                  <CheckCircle2 className="size-3" /> {passCount} Checks Passed
                </Badge>
              )}
            </div>
          </div>

          {/* 4 Pillars Summary Cards (Dynamic by Jurisdiction & Category) */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <Card className="p-3.5 bg-card">
              <div className="flex items-start gap-2.5">
                <div className="size-7 rounded-md bg-primary/10 flex items-center justify-center text-primary font-bold text-xs shrink-0">
                  1
                </div>
                <div>
                  <h5 className="text-xs font-bold uppercase tracking-wider text-foreground">
                    Identity &amp; Passport
                  </h5>
                  <p className="text-[11px] text-muted-foreground mt-0.5">
                    Valid passport with required remaining validity and verified applicant nationality.
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
                    {isStudent
                      ? "Academic Course & Sponsor"
                      : isWork
                        ? "Job Offer & Employer Sponsor"
                        : "Travel Purpose & Plan"}
                  </h5>
                  <p className="text-[11px] text-muted-foreground mt-0.5">
                    {isStudent
                      ? code === "JP"
                        ? "Admission certificate, COE, or enrollment verification from a recognized Japanese institution."
                        : code === "US"
                          ? "Form I-20 issued by SEVP-certified institution and valid SEVIS registration."
                          : code === "GB" || code === "UK"
                            ? "Unconditional offer, valid CAS statement, and licensed education sponsor credentials."
                            : "Admission offer and verified educational sponsor credentials."
                      : isWork
                        ? code === "JP"
                          ? "Employment contract / job offer in Japan with authorized activities and remuneration."
                          : code === "US"
                            ? "Approved Form I-129 / LCA and qualifying specialty occupation employment offer."
                            : code === "GB" || code === "UK"
                              ? "Valid Certificate of Sponsorship (CoS), licensed employer details, and eligible role."
                              : "Valid employment offer, sponsoring employer details, and qualifying role duties."
                        : code === "JP"
                          ? "Genuine sightseeing or visitor purpose with concrete itinerary matching stay duration."
                          : code === "US"
                            ? "Nonimmigrant visitor intent with strong home-country ties under INA Section 214(b)."
                            : "Genuine sightseeing or visitor purpose with concrete schedule matching stay duration."}
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
                    {isStudent
                      ? "Living Costs & Tuition"
                      : isWork
                        ? "Maintenance & Salary"
                        : "Financial Capacity"}
                  </h5>
                  <p className="text-[11px] text-muted-foreground mt-0.5">
                    {isStudent
                      ? code === "JP"
                        ? "Financial proof (bank balance or sponsor income ~¥120,000/mo or ¥1.5M–¥2M/yr) plus tuition."
                        : code === "US"
                          ? "Proof of sufficient liquid funds ($ USD) or Form I-134 affidavit covering tuition and living costs."
                          : code === "GB" || code === "UK"
                            ? "Bank statements demonstrating 28-day maintenance living costs (£1,334/mo London, £1,023 outside) plus tuition."
                            : "Bank statements or financial sponsorship covering tuition and living expenses."
                      : isWork
                        ? code === "JP"
                          ? "Remuneration meeting statutory standards (JPY) and resident tax / pension compliance."
                          : code === "US"
                            ? "Prevailing wage compliance and approved employer compensation package ($ USD)."
                            : code === "GB" || code === "UK"
                              ? "Verified salary meeting minimum threshold and required maintenance funds covering initial stay."
                              : "Verified salary meeting minimum threshold and maintenance funds covering stay."
                        : code === "JP"
                          ? "Sufficient travel funds (JPY) covering intended stay and return travel tickets."
                          : code === "US"
                            ? "Demonstrated financial solvency to cover trip expenses without unauthorized employment."
                            : "Verified bank statements, stable employment, or official sponsor guarantee covering expenses."}
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
                    Immigration Compliance
                  </h5>
                  <p className="text-[11px] text-muted-foreground mt-0.5">
                    {code === "JP"
                      ? "Immigration Control Act compliance: clean record, no overstays or bans, tax/pension paid."
                      : code === "US"
                        ? "Statutory admissibility under INA 212(a): clean record, no overstays or unauthorized work."
                        : "Clean compliance history with no active entry bans, overstays, or disqualifying grounds."}
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
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {findings.map((finding) => {
                  const isFail = finding.status === "fail";
                  const isWarning = finding.status === "at_risk";
                  const isReview = finding.status === "out_of_scope";
                  const url = citationUrl(finding.citation);
                  const version = citationVersion(finding.citation);

                  return (
                    <div
                      key={`${finding.key}-${finding.status}`}
                      className={`rounded-[var(--radius)] border p-4 flex flex-col justify-between transition-all ${
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
                              tone={isFail ? "danger" : isWarning ? "warning" : isReview ? "muted" : "success"}
                              className="text-[10px] uppercase font-semibold"
                            >
                              {isFail ? "Disqualified" : isWarning ? "At Risk" : isReview ? "Incomplete" : "Passed"}
                            </Badge>
                          </div>
                          <p className="text-xs text-muted-foreground leading-relaxed">
                            {finding.message}
                          </p>

                          {isReview && onReturnToIntake && (
                            <div className="pt-1">
                              <button
                                type="button"
                                onClick={() => onReturnToIntake(finding.key)}
                                className="inline-flex items-center gap-1 text-[11px] font-semibold text-blue-600 dark:text-blue-400 hover:underline"
                              >
                                Answer in Intake <ArrowRight className="size-3" />
                              </button>
                            </div>
                          )}

                          {url && (
                            <div className="pt-1.5">
                              <a
                                href={url}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-1 text-[11px] text-primary hover:underline"
                              >
                                <span>
                                  {String(finding.citation?.authority || "Official regulation source")}
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
                })}
              </div>
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
