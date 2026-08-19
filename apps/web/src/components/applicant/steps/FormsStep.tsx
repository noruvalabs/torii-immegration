"use client";

import { useState } from "react";
import {
  FileText,
  Loader2,
  CheckCircle2,
  Sparkles,
  Copy,
  Check,
  HelpCircle,
  ExternalLink,
  ShieldCheck,
  Download,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";
import type { GeneratedForm } from "./types";

type FormsStepProps = {
  forms: GeneratedForm[];
  loading: boolean;
  onGenerate: () => void;
  intakeAnswers?: Record<string, unknown>;
  caseId?: number;
  reference?: string;
};

function getFormMetadata(code: string): { title: string; purpose: string; officialUrl?: string } {
  const c = code.toLowerCase();
  if (c === "i901" || c.includes("i901") || c.includes("sevis_fee")) {
    return {
      title: "Form I-901 (SEVIS Fee Payment Confirmation)",
      purpose: "Mandatory Student and Exchange Visitor Program (SEVP) fee payment filed online at FMJfee.com ($350 for F-1 / $220 for J-1). Required before consular interview.",
      officialUrl: "https://www.fmjfee.com/i901fee/index.html",
    };
  }
  if (c === "i20" || c.includes("i20") || c.includes("i-20")) {
    return {
      title: "Form I-20 (Certificate of Eligibility for F-1 Student Status)",
      purpose: "Official Department of Homeland Security certificate issued by your SEVP-certified U.S. school confirming admission, SEVIS ID, degree level, and estimated cost.",
      officialUrl: "https://www.ice.gov/sevis",
    };
  }
  if (c === "i134" || c.includes("i134") || c.includes("i-134") || c.includes("affidavit")) {
    return {
      title: "Form I-134 (Declaration of Financial Support)",
      purpose: "USCIS declaration executed by a sponsor (parent, relative, or employer) proving sufficient liquid funds and income to support the applicant without unauthorized work.",
      officialUrl: "https://www.uscis.gov/i-134",
    };
  }
  if (c.includes("appointment") || c.includes("mrv")) {
    return {
      title: "U.S. Visa Appointment Portal & MRV Fee Scheduling",
      purpose: "Official U.S. Embassy scheduling profile generating the MRV fee payment slip ($185) and the in-person interview confirmation appointment letter.",
      officialUrl: "https://travel.state.gov/content/travel/en/us-visas/visa-information-resources/policy-updates.html",
    };
  }
  if (c.includes("ds_160") || c.includes("ds160") || c.includes("b1") || c.includes("b2") || c.includes("f1")) {
    return {
      title: "Online Nonimmigrant Visa Application (Form DS-160)",
      purpose: "Official U.S. Department of State application submitted via CEAC. Collects biographical data, passport info, travel plans, SEVIS/educational records, and security screening.",
      officialUrl: "https://ceac.state.gov/genniv/",
    };
  }
  if (c.includes("schengen")) {
    return {
      title: "Schengen Harmonised Visa Application Form (Short Stay C)",
      purpose: "Official harmonized application required by Schengen border authorities. Evaluates main travel destination, financial backing, and return commitment.",
      officialUrl: "https://eeas.europa.eu/",
    };
  }
  if (c.includes("uk") || c.includes("visitor")) {
    return {
      title: "UK Standard Visitor Visa Application Form",
      purpose: "UK Visas and Immigration (UKVI) declaration detailing visitor purpose, accommodation proof, and financial self-sufficiency.",
      officialUrl: "https://www.gov.uk/standard-visitor-visa/apply",
    };
  }
  if (c.includes("extension") || c.includes("stay")) {
    return {
      title: "Application for Extension of Period of Stay (在留期間更新許可申請書)",
      purpose: "Official Immigration Services Agency of Japan (MOJ) form for extending lawful residence status in Japan.",
      officialUrl: "https://www.moj.go.jp/isa/applications/procedures/16-3.html",
    };
  }
  return {
    title: "Official Visa Application Form",
    purpose: "Mandated government filing form required by immigration authorities to verify applicant credentials, itinerary, and financial backing.",
    officialUrl: undefined,
  };
}

export function FormsStep({
  forms,
  loading,
  onGenerate,
  intakeAnswers,
  caseId,
  reference,
}: FormsStepProps) {
  const { token } = useAuth();
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [downloadingPdf, setDownloadingPdf] = useState<string | null>(null);

  function handleCopy(key: string, value: string) {
    void navigator.clipboard.writeText(value);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  }

  async function handleDownloadPdf(formCode: string) {
    const activeToken = token || (typeof window !== "undefined" ? localStorage.getItem("torii_token") : null);
    if (!activeToken || !caseId) return;
    setDownloadingPdf(formCode);
    try {
      const res = await fetch(`/backend/v1/cases/${caseId}/pdf/application-form`, {
        headers: { Authorization: `Bearer ${activeToken}` },
      });
      if (!res.ok) {
        const errDetail = await res.text();
        console.error("PDF download failed:", res.status, errDetail);
        alert(`Failed to download form PDF: ${errDetail || res.statusText}`);
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${reference || `Case-${caseId}`}_Application_Form.pdf`;
      document.body.appendChild(link);
      link.click();
      setTimeout(() => {
        link.remove();
        URL.revokeObjectURL(url);
      }, 10000);
    } catch (err) {
      console.error("PDF download error:", err);
    } finally {
      setDownloadingPdf(null);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="text-base font-semibold text-foreground">Official Government Forms</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            Torii automatically maps your intake data and scanned documents directly into official embassy application forms.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {caseId && forms.length > 0 && (
            <Button
              variant="outline"
              onClick={() => handleDownloadPdf("all")}
              disabled={downloadingPdf !== null}
              className="gap-1.5"
            >
              {downloadingPdf ? <Loader2 className="size-4 animate-spin" /> : <Download className="size-4" />}
              Download PDF Form
            </Button>
          )}
          <Button onClick={onGenerate} disabled={loading}>
            {loading ? <Loader2 className="mr-2 size-4 animate-spin" /> : <Sparkles className="mr-2 size-4" />}
            {forms.length === 0 ? "Auto-fill official forms" : "Regenerate forms"}
          </Button>
        </div>
      </div>

      {forms.length === 0 ? (
        <div className="rounded-[var(--radius)] border border-dashed p-8 text-center bg-muted/20 space-y-3">
          <FileText className="mx-auto size-10 text-muted-foreground/40" />
          <p className="text-sm font-medium">No forms generated yet</p>
          <p className="text-xs text-muted-foreground max-w-md mx-auto">
            Click &quot;Auto-fill official forms&quot; above. Torii will take your intake answers and document vault information to generate all required government forms in seconds.
          </p>
          <Button onClick={onGenerate} disabled={loading} className="mt-2">
            {loading ? <Loader2 className="mr-2 size-4 animate-spin" /> : <Sparkles className="mr-2 size-4" />}
            Auto-fill forms now
          </Button>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Automation Callout Banner */}
          <div className="rounded-[var(--radius)] border border-primary/30 bg-primary/5 p-4 flex items-start gap-3">
            <ShieldCheck className="size-5 text-primary shrink-0 mt-0.5" />
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-primary">
                🤖 Torii Intelligent Form Automation
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                All fields below have been automatically mapped and verified against your passport and intake answers. You can use this field guide to effortlessly copy values into the government submission portal.
              </p>
            </div>
          </div>

          {forms.map((form) => {
            const meta = getFormMetadata(form.form_code);
            const hasFilledFields = Object.keys(form.filled_fields).length > 0;
            const displayFields = hasFilledFields
              ? form.filled_fields
              : intakeAnswers && Object.keys(intakeAnswers).length > 0
                ? intakeAnswers
                : form.filled_fields;

            const totalFieldsCount = Object.keys(displayFields).length;

            return (
              <div key={form.id} className="rounded-[var(--radius)] border bg-card p-5 space-y-4 shadow-sm">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between border-b pb-4">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h4 className="text-base font-bold tracking-tight">{meta.title}</h4>
                      <Badge tone="muted" className="font-mono text-[10px]">
                        {form.form_code} v{form.form_version}
                      </Badge>
                      {form.missing_required_fields.length === 0 ? (
                        <Badge tone="success">
                          <CheckCircle2 className="mr-1 size-3" /> 100% Ready
                        </Badge>
                      ) : (
                        <Badge tone="danger">
                          {form.missing_required_fields.length} fields missing
                        </Badge>
                      )}
                    </div>
                    {Boolean(form.citation?.authority) && (
                      <p className="mt-1 text-[11px] text-muted-foreground">
                        Official Authority: <span className="font-medium text-foreground">{String(form.citation.authority)}</span>
                        {form.citation.title ? ` — ${String(form.citation.title)}` : ""}
                      </p>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    {caseId && (
                      <Button
                        variant="outline"
                        onClick={() => handleDownloadPdf(form.form_code)}
                        disabled={downloadingPdf === form.form_code}
                        className="text-xs h-8 gap-1.5 px-3 py-1"
                      >
                        {downloadingPdf === form.form_code ? (
                          <Loader2 className="size-3.5 animate-spin" />
                        ) : (
                          <Download className="size-3.5" />
                        )}
                        Download PDF
                      </Button>
                    )}
                    {meta.officialUrl && (
                      <a
                        href={meta.officialUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 text-xs text-primary font-medium hover:underline shrink-0"
                      >
                        Government Portal <ExternalLink className="size-3" />
                      </a>
                    )}
                  </div>
                </div>

                {/* Why required explanation */}
                <div className="rounded border bg-muted/30 p-3 text-xs flex items-start gap-2.5">
                  <HelpCircle className="size-4 text-muted-foreground shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold text-foreground">Why this form is required: </span>
                    <span className="text-muted-foreground">{meta.purpose}</span>
                  </div>
                </div>

                {/* Field breakdown */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Auto-Filled Form Fields ({totalFieldsCount})
                    </p>
                    <p className="text-[10px] text-muted-foreground">Click copy to paste into embassy forms</p>
                  </div>

                  <div className="grid gap-2 sm:grid-cols-2">
                    {Object.entries(displayFields).map(([key, val]) => {
                      const valStr = String(val ?? "");
                      const isCopied = copiedKey === key;

                      return (
                        <div
                          key={key}
                          className="flex items-center justify-between rounded border bg-background px-3 py-2 text-xs"
                        >
                          <div className="min-w-0 flex-1 pr-2">
                            <p className="text-[10px] uppercase font-mono text-muted-foreground truncate">
                              {key.replace(/_/g, " ")}
                            </p>
                            <p className="font-semibold text-foreground truncate">{valStr}</p>
                          </div>
                          <button
                            onClick={() => handleCopy(key, valStr)}
                            title="Copy field value"
                            className="rounded p-1 text-muted-foreground hover:bg-accent hover:text-foreground transition-colors shrink-0"
                          >
                            {isCopied ? (
                              <Check className="size-3.5 text-[var(--color-success)]" />
                            ) : (
                              <Copy className="size-3.5" />
                            )}
                          </button>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {form.missing_required_fields.length > 0 && (
                  <div className="rounded border border-[var(--color-warning)]/30 bg-[var(--color-warning)]/5 px-3 py-2 text-xs text-[var(--color-warning)]">
                    <span className="font-semibold">Missing required fields: </span>
                    {form.missing_required_fields.join(", ")}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
