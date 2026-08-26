"use client";

import { useEffect, useState } from "react";
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
  AlertCircle,
  Zap,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";
import { answerIntake, downloadOfficialForm, getFiling, getOfficialForms } from "@/lib/api/cases";
import type { FilingInfo, OfficialForm, PortalPack } from "@/lib/api/cases";
import { toast } from "@/components/ui/sonner";
import type { GeneratedForm } from "./types";

type FormsStepProps = {
  forms: GeneratedForm[];
  loading: boolean;
  onGenerate: () => void;
  intakeAnswers?: Record<string, unknown>;
  caseId?: number;
  reference?: string;
};

function getFormMetadata(code: string, fallbackTitle?: string, fallbackUrl?: string): { title: string; purpose: string; officialUrl?: string } {
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
  if (c === "change_of_status" || c.includes("change_of_status")) {
    return {
      title: "Application for Change of Status of Residence (在留資格変更許可申請書)",
      purpose: "Official statutory application form submitted to the Immigration Services Agency of Japan (出入国在留管理庁) to change residence status.",
      officialUrl: "https://www.moj.go.jp/isa/applications/procedures/16-2.html",
    };
  }
  if (c === "extension_of_stay" || c.includes("extension")) {
    return {
      title: "Application for Extension of Period of Stay — Applicant Part (在留期間更新許可申請書)",
      purpose: "Official statutory application form submitted to the Immigration Services Agency of Japan (出入国在留管理庁) to extend authorized stay.",
      officialUrl: "https://www.moj.go.jp/isa/applications/procedures/16-1.html",
    };
  }
  if (c === "student_visa_application" || c.includes("student_visa") || c.includes("mofa")) {
    return {
      title: "Visa Application Form to Enter Japan (日本国査証申請書)",
      purpose: "Official Ministry of Foreign Affairs (MOFA) entry visa application filed with a Japanese Embassy or Consulate overseas.",
      officialUrl: "https://www.mofa.go.jp/j_info/visit/visa/index.html",
    };
  }
  if (c === "isa_application" || c.includes("isa") || c.includes("16-1") || c.includes("16-3")) {
    return {
      title: "Application for Certificate of Eligibility / Status (在留諸申請書)",
      purpose: "Standard official application form submitted to the Immigration Services Agency of Japan (出入国在留管理庁).",
      officialUrl: "https://www.moj.go.jp/isa/applications/procedures/16-1.html",
    };
  }
  if (c.includes("institution") || c.includes("school")) {
    return {
      title: "Application — Educational Institution Part (所属機関等作成用)",
      purpose: "Section completed and sealed by the sponsoring Japanese educational institution or university verifying enrollment and attendance.",
      officialUrl: "https://www.moj.go.jp/isa/applications/procedures/16-1.html",
    };
  }
  if (c.includes("organization") || c.includes("employer")) {
    return {
      title: "Application — Sponsoring Organization / Employer Part (所属機関等作成用)",
      purpose: "Section completed by the sponsoring employer or host organization in Japan declaring corporate category, remuneration, and contract terms.",
      officialUrl: "https://www.moj.go.jp/isa/applications/procedures/16-3.html",
    };
  }
  if (c.includes("schengen")) {
    return {
      title: "Harmonised Schengen Visa Application Form",
      purpose: "Uniform application form for entry and stay in the Schengen area for up to 90 days in any 180-day period.",
      officialUrl: "https://home-affairs.ec.europa.eu/policies/schengen-borders-visa/visa-policy/applying-schengen-visa_en",
    };
  }
  if (c.includes("uk") || c.includes("ukvi") || c.includes("visitor")) {
    return {
      title: "UK Visas and Immigration (UKVI) Application Form",
      purpose: "Standard application schedule and declarations for UK entry clearance or further leave to remain.",
      officialUrl: "https://www.gov.uk/browse/visas-immigration",
    };
  }
  return {
    title: fallbackTitle || `Official Application Form (${code})`,
    purpose: "Official government immigration filing form required by published statutory regulations.",
    officialUrl: fallbackUrl,
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
  const [missingFieldInputs, setMissingFieldInputs] = useState<Record<string, string>>({});
  const [savingMissingField, setSavingMissingField] = useState<string | null>(null);
  const [quickSaveNotice, setQuickSaveNotice] = useState<string | null>(null);
  const [officialForms, setOfficialForms] = useState<OfficialForm[]>([]);
  const [filing, setFiling] = useState<FilingInfo | null>(null);

  useEffect(() => {
    if (!token || !caseId) return;
    let cancelled = false;
    Promise.allSettled([getOfficialForms(token, caseId), getFiling(token, caseId)]).then(
      ([formsResult, filingResult]) => {
        if (cancelled) return;
        // Both are additive; the rest of the step stands without either.
        setOfficialForms(formsResult.status === "fulfilled" ? formsResult.value.forms : []);
        setFiling(filingResult.status === "fulfilled" ? filingResult.value : null);
      },
    );
    return () => {
      cancelled = true;
    };
  }, [token, caseId]);

  const portalPack: PortalPack | undefined =
    filing?.filing_mode === "online_portal" ? filing.portal_pack : undefined;

  function saveBlob(bytes: Uint8Array<ArrayBuffer>, filename: string) {
    const blob = new Blob([bytes], { type: "application/pdf" });
    if (blob.size === 0) throw new Error("Generated PDF file is empty (0 bytes).");
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    setTimeout(() => {
      link.remove();
      URL.revokeObjectURL(url);
    }, 10000);
  }

  function decodeBase64(data: string): Uint8Array<ArrayBuffer> {
    const binary = atob(data);
    const bytes = new Uint8Array(new ArrayBuffer(binary.length));
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    return bytes;
  }

  async function handleDownloadOfficialForm(formCode: string) {
    const activeToken =
      token || (typeof window !== "undefined" ? localStorage.getItem("torii_token") : null);
    if (!caseId || !activeToken) return;
    setDownloadingPdf(formCode);
    try {
      const data = await downloadOfficialForm(activeToken, caseId, formCode);
      if (!data?.data_base64) throw new Error("Invalid server response: missing PDF data.");
      saveBlob(decodeBase64(data.data_base64), data.filename);
      toast.success("Official form downloaded.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Download failed. Please try again.");
    } finally {
      setDownloadingPdf(null);
    }
  }

  function handleCopy(key: string, value: string) {
    void navigator.clipboard.writeText(value);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  }

  async function handleSaveMissingField(fieldKey: string) {
    if (!token || !caseId) return;
    const cleanKey = fieldKey.split(".").pop() || fieldKey;
    const val = missingFieldInputs[cleanKey] || missingFieldInputs[fieldKey];
    if (!val) {
      toast.error(`Please enter a value for ${cleanKey.replace(/_/g, " ")}`);
      return;
    }
    setSavingMissingField(cleanKey);
    try {
      await answerIntake(token, caseId, cleanKey, val);
      toast.success(`Saved ${cleanKey.replace(/_/g, " ")}! Form refreshed.`);
      onGenerate();
    } catch (e) {
      const errMsg = e instanceof Error ? e.message : "Failed to save missing field";
      toast.error(errMsg);
    } finally {
      setSavingMissingField(null);
    }
  }

  async function handleDownloadPdf(formCode: string) {
    const activeToken = token || (typeof window !== "undefined" ? localStorage.getItem("torii_token") : null);
    if (!caseId || !activeToken) return;
    setDownloadingPdf(formCode);
    try {
      const res = await fetch(`/backend/v1/cases/${caseId}/export/application-form?format=base64`, {
        headers: {
          Authorization: `Bearer ${activeToken}`,
          Accept: "application/json",
        },
      });
      if (!res.ok) {
        const errDetail = await res.text();
        console.error("PDF download failed:", res.status, errDetail);
        toast.error(`Failed to download PDF form (${res.status}): ${errDetail || res.statusText}`);
        return;
      }
      if (res.status === 204) {
        throw new Error("Received empty response (204). Please check browser extension settings.");
      }
      const data = await res.json();
      if (!data?.data_base64) {
        throw new Error("Invalid server response: missing PDF data.");
      }
      const binaryString = atob(data.data_base64);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      const blob = new Blob([bytes], { type: "application/pdf" });
      if (blob.size === 0) {
        throw new Error("Generated PDF file is empty (0 bytes).");
      }
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = data.filename || `${reference || `Case-${caseId}`}_Application_Form.pdf`;
      document.body.appendChild(link);
      link.click();
      toast.success("PDF downloaded successfully!");
      setTimeout(() => {
        link.remove();
        URL.revokeObjectURL(url);
      }, 10000);
    } catch (err) {
      console.error("PDF download error:", err);
      toast.error(err instanceof Error ? err.message : "PDF download failed. Please try again.");
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
        {forms.length > 0 && (
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={onGenerate} disabled={loading} className="text-xs h-8">
              {loading ? <Loader2 className="mr-1.5 size-3.5 animate-spin" /> : <Sparkles className="mr-1.5 size-3.5" />}
              Regenerate forms
            </Button>
          </div>
        )}
      </div>

      {quickSaveNotice && (
        <div className="rounded-md border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-800 dark:text-emerald-300 font-medium">
          {quickSaveNotice}
        </div>
      )}

      {portalPack && (
        <div className="space-y-3">
          <div className="rounded-[var(--radius)] border border-amber-500/30 bg-amber-500/5 p-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-amber-700 dark:text-amber-400">
              Filed online — there is no form to submit
            </p>
            <p className="mt-1.5 text-xs text-muted-foreground">
              {portalPack.scope_label} is completed on the government&apos;s own website.
              Torii prepares your answers in the order the service asks for them so you can
              work down the screen and copy each one across.
            </p>
            {filing?.apply_url && (
              <a
                href={filing.apply_url}
                target="_blank"
                rel="noreferrer"
                className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
              >
                <ExternalLink className="size-3" />
                Apply at {filing.apply_url.replace(/^https?:\/\//, "")}
              </a>
            )}
          </div>

          <div className="rounded-[var(--radius)] border bg-card p-4 space-y-4">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-sm font-semibold">
                {portalPack.answered_count} of{" "}
                {portalPack.answered_count + portalPack.outstanding_count} questions answered
              </p>
              <Button
                onClick={() => handleDownloadPdf("portal-pack")}
                disabled={downloadingPdf === "portal-pack"}
                className="text-xs h-8 shrink-0"
              >
                {downloadingPdf === "portal-pack" ? (
                  <Loader2 className="mr-1.5 size-3.5 animate-spin" />
                ) : (
                  <Download className="mr-1.5 size-3.5" />
                )}
                Download answer pack
              </Button>
            </div>

            {portalPack.sections.map((section) => (
              <div key={section.key} className="space-y-1.5">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  {section.title}
                </p>
                <div className="rounded-md border divide-y">
                  {section.fields.map((field) => (
                    <div
                      key={field.field}
                      className="flex items-baseline gap-3 px-3 py-1.5 text-xs"
                    >
                      <span className="w-1/2 shrink-0 text-muted-foreground">
                        {field.label}
                        {field.required && <span className="text-amber-600"> *</span>}
                      </span>
                      {field.answered ? (
                        <span className="font-medium break-words">{field.value}</span>
                      ) : (
                        <span className="italic text-muted-foreground/60">not answered yet</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}

            {portalPack.outstanding.length > 0 && (
              <p className="text-xs text-amber-700 dark:text-amber-400">
                <AlertCircle className="mr-1 inline size-3.5 align-text-bottom" />
                The service will ask for {portalPack.outstanding.length} more:{" "}
                {portalPack.outstanding.join(", ")}.
              </p>
            )}
          </div>
        </div>
      )}

      {officialForms.length > 0 && (
        <div className="space-y-3">
          <div>
            <h4 className="text-sm font-semibold text-foreground">
              The official form{officialForms.length > 1 ? "s" : ""} for your application type
            </h4>
            <p className="mt-1 text-xs text-muted-foreground">
              Downloaded straight from the issuing ministry and filled with your answers — the
              exact sheet your residence status and procedure require, not a copy of it.
            </p>
          </div>

          {officialForms.map((form) => {
            const missing = form.missing_answer_keys ?? [];
            const total = form.total_items ?? 0;
            const answered = Math.max(0, total - missing.length);
            return (
              <div key={form.code} className="rounded-[var(--radius)] border bg-card p-4 space-y-3">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold tracking-tight">{form.title_ja}</p>
                    <p className="text-xs text-muted-foreground">{form.title_en}</p>
                    <div className="mt-2 flex flex-wrap items-center gap-1.5">
                      {form.series && (
                        <Badge tone="muted" className="text-[10px] font-normal">
                          {form.series}
                        </Badge>
                      )}
                      <Badge tone="muted" className="text-[10px] font-normal">
                        {form.pages} page{form.pages > 1 ? "s" : ""}
                      </Badge>
                      {total > 0 && (
                        <Badge
                          tone={missing.length === 0 ? "success" : "warning"}
                          className="text-[10px] font-normal"
                        >
                          {answered}/{total} items filled
                        </Badge>
                      )}
                    </div>
                  </div>
                  <Button
                    onClick={() => handleDownloadOfficialForm(form.code)}
                    disabled={downloadingPdf === form.code}
                    className="text-xs h-8 shrink-0"
                  >
                    {downloadingPdf === form.code ? (
                      <Loader2 className="mr-1.5 size-3.5 animate-spin" />
                    ) : (
                      <Download className="mr-1.5 size-3.5" />
                    )}
                    Download filled form
                  </Button>
                </div>

                {missing.length > 0 && (
                  <p className="text-xs text-amber-700 dark:text-amber-400">
                    <AlertCircle className="mr-1 inline size-3.5 align-text-bottom" />
                    Still blank on the form: {missing.map((key) => key.replace(/_/g, " ")).join(", ")}.
                    Answer these in intake and download again.
                  </p>
                )}

                {form.note && <p className="text-xs text-muted-foreground">{form.note}</p>}

                <a
                  href={form.source_page_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                >
                  <ExternalLink className="size-3" />
                  {form.authority}
                </a>
              </div>
            );
          })}
        </div>
      )}

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
            const meta = getFormMetadata(
              form.form_code,
              typeof form.citation?.title === "string" ? form.citation.title : undefined,
              typeof form.citation?.url === "string" ? form.citation.url : undefined,
            );
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
                          {form.missing_required_fields.length} field{form.missing_required_fields.length > 1 ? "s" : ""} missing
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
                        className="text-xs h-8"
                      >
                        {downloadingPdf === form.form_code ? (
                          <Loader2 className="mr-1.5 size-3.5 animate-spin" />
                        ) : (
                          <Download className="mr-1.5 size-3.5" />
                        )}
                        Download Form (PDF)
                      </Button>
                    )}
                    {meta.officialUrl && (
                      <a
                        href={meta.officialUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                      >
                        Official Specs <ExternalLink className="size-3" />
                      </a>
                    )}
                  </div>
                </div>

                {/* Form Purpose Guide */}
                <div className="rounded bg-muted/40 p-3 flex items-start gap-2.5">
                  <HelpCircle className="size-4 text-muted-foreground shrink-0 mt-0.5" />
                  <p className="text-xs text-muted-foreground leading-relaxed">{meta.purpose}</p>
                </div>

                {/* Missing Fields Inline Quick-Fixer */}
                {form.missing_required_fields.length > 0 && (
                  <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3.5 space-y-2.5 text-xs">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-amber-800 dark:text-amber-300 font-semibold">
                        <AlertCircle className="size-4 shrink-0 text-amber-600 dark:text-amber-400" />
                        <span>Missing Required Form Field{form.missing_required_fields.length > 1 ? "s" : ""}:</span>
                      </div>
                      <span className="text-[10px] text-muted-foreground">Required by official Japanese Immigration Bureau form</span>
                    </div>
                    <p className="text-[11px] text-muted-foreground">
                      The official form template requires values for: <strong className="text-foreground">{form.missing_required_fields.join(", ")}</strong>. You can enter the missing value below and click Save:
                    </p>
                    <div className="flex flex-wrap gap-2.5 pt-1">
                      {form.missing_required_fields.map((field) => {
                        const cleanKey = field.split(".").pop() || field;
                        const label = cleanKey.replace(/_/g, " ");
                        const placeholder = cleanKey.includes("attendance") ? "e.g. 95 (percent)" : `Enter ${label}...`;

                        return (
                          <div key={field} className="flex items-center gap-2 bg-background/90 rounded-md border p-1.5 shadow-sm">
                            <span className="font-mono text-[11px] font-medium text-foreground">{label}:</span>
                            <input
                              type="text"
                              placeholder={placeholder}
                              value={missingFieldInputs[cleanKey] ?? ""}
                              onChange={(e) =>
                                setMissingFieldInputs((prev) => ({ ...prev, [cleanKey]: e.target.value }))
                              }
                              onKeyDown={(e) => {
                                if (e.key === "Enter") handleSaveMissingField(cleanKey);
                              }}
                              className="w-36 rounded border bg-background px-2 py-1 text-xs outline-none focus:ring-1 focus:ring-primary"
                            />
                            <Button
                              disabled={!missingFieldInputs[cleanKey] || savingMissingField === cleanKey}
                              onClick={() => handleSaveMissingField(cleanKey)}
                              className="h-7 px-2.5 text-[11px] font-medium"
                            >
                              {savingMissingField === cleanKey ? (
                                <Loader2 className="size-3 animate-spin" />
                              ) : (
                                <>
                                  <Zap className="mr-1 size-3" /> Save & Re-fill
                                </>
                              )}
                            </Button>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Auto-Filled Mapped Fields Grid */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <p className="text-xs font-semibold text-foreground">
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
                              <Check className="size-3.5 text-emerald-600" />
                            ) : (
                              <Copy className="size-3.5" />
                            )}
                          </button>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
