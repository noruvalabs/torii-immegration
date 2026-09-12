"use client";

import { useEffect, useState } from "react";
import {
  Check,
  Download,
  Send,
  Loader2,
  FileText,
  Copy,
  Sparkles,
  Layers,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { useAuth } from "@/lib/auth-context";
import { useCredits } from "@/lib/credits-context";
import { draftDocument } from "@/lib/api/ai";
import { exportCaseDocuments, type ExportFormat } from "@/lib/api/cases";
import { toast } from "@/components/ui/sonner";
import { formatScopeLabel } from "@/lib/utils";
import { JourneyMap } from "./JourneyMap";
import type { Case } from "./types";

type PacketStepProps = {
  packet: Record<string, unknown> | null;
  caseData: Case;
  loading: boolean;
  onBuild: () => void;
  onSubmit: () => void;
};

// These are drafts the applicant completes and signs, not finished official documents.
// Nothing here may assert a fact the applicant has not stated: an earlier version
// invented a hotel ("Tokyo Central Hotel"), its address and phone number, a day-by-day
// itinerary generated from `day % 3`, and had the applicant certify that all travel costs
// were "fully provided for and guaranteed" with bank statements enclosed — regardless of
// what they had actually answered or attached.
const BLANK = "\u2014";

function answered(answers: Record<string, unknown>, ...keys: string[]): string {
  for (const key of keys) {
    const value = answers[key];
    if (value !== undefined && value !== null && String(value).trim() !== "") {
      return String(value).trim();
    }
  }
  return BLANK;
}

function gatheredDocuments(
  packet: Record<string, unknown> | null,
  matching?: RegExp,
): { name?: string; status?: string }[] {
  const checklist = Array.isArray(packet?.checklist)
    ? (packet.checklist as { name?: string; status?: string }[])
    : [];
  return checklist
    .filter((item) => item.status && item.status !== "needed")
    .filter((item) => !matching || matching.test(item.name ?? ""));
}

function numberedOrNone(items: { name?: string }[], emptyNote: string): string {
  if (!items.length) return `   ${emptyNote}`;
  return items.map((item, index) => `   ${index + 1}. ${item.name ?? "Document"}`).join("\n");
}

function generateCoverLetter(caseData: Case, packet: Record<string, unknown> | null): string {
  const reference = String(packet?.reference ?? caseData.reference);
  const scope = caseData.scope_label ?? caseData.locale.toUpperCase();
  const dateStr = new Date().toLocaleDateString("en-GB", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  const answers = caseData.intake_answers || {};
  const fullName = answered(answers, "full_name", "applicant_name");
  const passportNo = answered(answers, "passport_number", "passport_no");
  const nationality = answered(answers, "nationality");
  const purpose = answered(answers, "main_purpose", "purpose_of_visit");
  const stayDays = answered(answers, "stay_duration_days", "intended_length_of_stay_days");
  const arrivalDate = answered(answers, "planned_arrival_date");

  const documents = numberedOrNone(
    gatheredDocuments(packet),
    "(No documents recorded yet — complete your checklist.)",
  );

  return `APPLICATION COVER LETTER  (draft — check and sign before filing)

Reference: ${reference}
Scope: ${scope}
Date: ${dateStr}

Applicant: ${fullName}
Nationality: ${nationality}
Passport number: ${passportNo}

Purpose of visit: ${purpose}
Intended length of stay: ${stayDays}
Planned arrival: ${arrivalDate}

Enclosed documents:
${documents}

I submit this application and the documents listed above for your consideration.
Please contact me if any further document or clarification is required.

Signature: ______________________________
Name: ${fullName}
Date: ${dateStr}
`;
}

function generateScheduleOfStay(caseData: Case, packet: Record<string, unknown> | null): string {
  const answers = caseData.intake_answers || {};
  const fullName = answered(answers, "full_name", "applicant_name");
  const arrivalDate = answered(answers, "planned_arrival_date");
  const accommodation = answered(answers, "accommodation_name");
  const accommodationAddress = answered(answers, "accommodation_address");
  const rawDays = answers.stay_duration_days ?? answers.intended_length_of_stay_days;
  const stayDays = Number.parseInt(String(rawDays ?? ""), 10);

  // The itinerary is the applicant's to write. Generating plausible activities would put
  // a fictional plan in front of a consular officer over the applicant's own signature,
  // so the rows are left blank — dated where the arrival date is known.
  const base = arrivalDate !== BLANK ? new Date(arrivalDate) : null;
  const dayCount = Number.isFinite(stayDays) && stayDays > 0 ? Math.min(stayDays, 15) : 0;
  let rows = "";
  for (let day = 1; day <= dayCount; day++) {
    let dateLabel = `Day ${day}`;
    if (base && !Number.isNaN(base.getTime())) {
      const current = new Date(base);
      current.setDate(base.getDate() + (day - 1));
      dateLabel = `Day ${day} (${current.toISOString().split("T")[0]})`;
    }
    rows += `${dateLabel.padEnd(22)}|                                        |\n`;
  }
  if (!rows) {
    rows = "(Answer your arrival date and length of stay to get dated rows.)\n";
  }

  return `SCHEDULE OF STAY / 滞在予定表  (draft — complete and sign before filing)

Applicant: ${fullName}
Planned arrival: ${arrivalDate}
Length of stay: ${stayDays > 0 ? `${stayDays} days` : BLANK}
Accommodation: ${accommodation}
Address and telephone: ${accommodationAddress}

Write what you will actually do each day. The consulate compares this against your
bookings, so it has to match them.

Date                  | Plan for the day                       |
----------------------+----------------------------------------+
${rows}----------------------+----------------------------------------+

Signature: ______________________________
Date: ${new Date().toISOString().split("T")[0]}
`;
}

function generateReasonForVisit(caseData: Case, packet: Record<string, unknown> | null): string {
  const answers = caseData.intake_answers || {};
  const fullName = answered(answers, "full_name", "applicant_name");
  const passportNo = answered(answers, "passport_number", "passport_no");
  const nationality = answered(answers, "nationality");
  const residence = answered(answers, "current_residence_country", "residence_country");
  const purpose = answered(answers, "main_purpose", "purpose_of_visit");
  const stayDays = answered(answers, "stay_duration_days", "intended_length_of_stay_days");
  const occupation = answered(answers, "occupation");
  const employer = answered(answers, "employer_name");

  return `STATEMENT OF PURPOSE / 理由書  (draft — write this in your own words)

Applicant: ${fullName}
Nationality: ${nationality}
Passport number: ${passportNo}
Country of residence: ${residence}
Occupation: ${occupation}
Employer: ${employer}
Purpose of visit: ${purpose}
Intended length of stay: ${stayDays}

Write your statement below. A consular officer is reading for your reasons in your own
words, so cover why you are travelling, what ties you to your home country, and how the
trip is paid for. Torii does not write this for you: a statement you did not write is one
you cannot stand behind at an interview.


____________________________________________________________________________________

____________________________________________________________________________________

____________________________________________________________________________________


Signature: ______________________________
Date: ${new Date().toISOString().split("T")[0]}
`;
}

function generateFinancialGuarantee(
  caseData: Case,
  packet: Record<string, unknown> | null,
): string {
  const answers = caseData.intake_answers || {};
  const fullName = answered(answers, "full_name", "applicant_name");
  const passportNo = answered(answers, "passport_number", "passport_no");
  const payer = answered(answers, "trip_payer");
  const salary = answered(answers, "monthly_salary", "annual_salary_jpy");
  const savings = answered(answers, "estimated_savings_available");
  const employer = answered(answers, "employer_name");

  const enclosed = numberedOrNone(
    gatheredDocuments(packet, /bank|financial|tax|income|salary|fund/i),
    "(None recorded yet — attach your financial evidence and list it here.)",
  );

  return `EXPLANATION OF EXPENSES / 経費支弁書  (draft — check and sign before filing)

Applicant: ${fullName}
Passport number: ${passportNo}

Who is paying for the trip: ${payer}
Employer: ${employer}
Stated income: ${salary}
Stated available funds: ${savings}

Financial evidence recorded so far:
${enclosed}

Check every figure above against the documents you are attaching before you sign. This is
a declaration to a government: it must state what you can evidence, and nothing more.

Signature: ______________________________
Name: ${fullName}
Date: ${new Date().toISOString().split("T")[0]}
`;
}

type DocType = "cover" | "schedule" | "reason" | "financial";

/** Tab order, and the order documents are written into a "download everything" zip. */
const DOC_ORDER: DocType[] = ["cover", "schedule", "reason", "financial"];

const FORMAT_LABELS: Record<ExportFormat, string> = {
  pdf: "PDF",
  docx: "Word (.docx)",
};

export function PacketStep({ packet, caseData, loading, onBuild, onSubmit }: PacketStepProps) {
  const { token } = useAuth();
  const { balance, unlockCase } = useCredits();
  const [activeDoc, setActiveDoc] = useState<DocType>("cover");
  const [copiedDoc, setCopiedDoc] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState<string | null>(null);
  const [exportFormat, setExportFormat] = useState<ExportFormat>("pdf");
  const [exporting, setExporting] = useState<string | null>(null);
  const [isUnlocking, setIsUnlocking] = useState(false);
  const [unlocked, setUnlocked] = useState(
    Boolean(caseData.is_entitled || caseData.status === "submitted"),
  );
  const [aiDrafts, setAiDrafts] = useState<Partial<Record<DocType, string>>>({});
  const [aiDrafting, setAiDrafting] = useState<DocType | null>(null);
  const [customInstructions, setCustomInstructions] = useState("");
  const [showPromptInput, setShowPromptInput] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);

  useEffect(() => {
    if (caseData.is_entitled || caseData.status === "submitted") {
      setUnlocked(true);
    }
  }, [caseData.is_entitled, caseData.status]);

  async function handleGenerateAIDraft(targetDoc?: DocType) {
    const doc = targetDoc || activeDoc;
    setAiDrafting(doc);
    setAiError(null);
    try {
      const docTypeMapping: Record<DocType, string> = {
        cover: "cover_letter",
        reason: "statement_of_reason",
        schedule: "schedule_of_stay",
        financial: "financial_solvency",
      };
      const res = await draftDocument({
        doc_type: docTypeMapping[doc] || doc,
        jurisdiction_code: caseData.reference ? caseData.reference.split("-")[0] : "JP",
        scope_label: caseData.scope_label || caseData.locale.toUpperCase(),
        case_reference: caseData.reference || `CASE-${caseData.id}`,
        intake_answers: caseData.intake_answers || {},
        checklist: Array.isArray(packet?.checklist) ? (packet.checklist as Record<string, unknown>[]) : [],
        custom_instructions: customInstructions || undefined,
      });
      setAiDrafts((prev) => ({ ...prev, [doc]: res.content }));
      setShowPromptInput(false);
    } catch (err) {
      setAiError(err instanceof Error ? err.message : "AI drafting failed");
    } finally {
      setAiDrafting(null);
    }
  }

  function handleResetToTemplate() {
    setAiDrafts((prev) => {
      const next = { ...prev };
      delete next[activeDoc];
      return next;
    });
  }

  function handleTextEdit(val: string) {
    setAiDrafts((prev) => ({ ...prev, [activeDoc]: val }));
  }

  async function downloadPdf(
    endpoint: "application-form" | "cover-letter" | "dossier-packet",
    defaultFilename: string
  ) {
    const activeToken = token || (typeof window !== "undefined" ? localStorage.getItem("torii_token") : null);
    if (!activeToken) return;

    if (endpoint === "dossier-packet" && !unlocked && caseData.status !== "submitted") {
      setIsUnlocking(true);
      const res = await unlockCase(caseData.id);
      setIsUnlocking(false);
      if (!res.success) return;
      setUnlocked(true);
    }

    setDownloadingPdf(endpoint);
    try {
      const res = await fetch(`/backend/v1/cases/${caseData.id}/export/${endpoint}?format=base64`, {
        headers: {
          Authorization: `Bearer ${activeToken}`,
          Accept: "application/json",
        },
      });
      if (!res.ok) {
        const errDetail = await res.text();
        console.error("PDF download failed:", res.status, errDetail);
        toast.error(`Failed to download PDF (${res.status}): ${errDetail || res.statusText}`);
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
      link.download = data.filename || defaultFilename;
      document.body.appendChild(link);
      link.click();
      toast.success("PDF dossier downloaded successfully!");
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

  const scopeLower = (caseData.scope_label || "").toLowerCase();
  const isJapan = scopeLower.includes("japan") || caseData.locale === "jp";
  const isUSA = scopeLower.includes("united states") || scopeLower.includes("usa") || scopeLower.includes("us ") || scopeLower.includes("b1/b2") || scopeLower.includes("f-1") || scopeLower.includes("h-1b");
  const isUK = scopeLower.includes("united kingdom") || scopeLower.includes("uk") || scopeLower.includes("great britain");
  const isSchengen = scopeLower.includes("schengen") || scopeLower.includes("france") || scopeLower.includes("germany") || scopeLower.includes("italy") || scopeLower.includes("spain");

  const isWork = scopeLower.includes("work") || scopeLower.includes("h-1b") || scopeLower.includes("employment");
  const isStudent = scopeLower.includes("student") || scopeLower.includes("f-1") || scopeLower.includes("study");

  function getDocLabels() {
    if (isJapan) {
      if (isWork) {
        return {
          cover: "Bureau Cover Letter",
          schedule: "Job Duties Specification",
          reason: "Statement of Reason",
          financial: "Tax & Income Proof",
        };
      }
      if (isStudent) {
        return {
          cover: "Embassy Cover Letter",
          schedule: "Study & Activity Plan",
          reason: "Statement of Purpose",
          financial: "Sponsor Affidavit",
        };
      }
      return {
        cover: "Embassy Cover Letter",
        schedule: "Schedule of Stay",
        reason: "Reason for Visit",
        financial: "Financial Guarantee",
      };
    }

    if (isUSA) {
      return {
        cover: "Consular Cover Letter",
        schedule: "Travel Itinerary",
        reason: "Statement of Purpose",
        financial: "Financial Solvency Affidavit",
      };
    }

    if (isUK) {
      return {
        cover: "UKVI Cover Letter",
        schedule: "Travel & Stay Itinerary",
        reason: "Purpose of Visit",
        financial: "Maintenance & Solvency",
      };
    }

    if (isSchengen) {
      return {
        cover: "Schengen Cover Letter",
        schedule: "Travel Itinerary",
        reason: "Travel Intent Declaration",
        financial: "Proof of Subsistence",
      };
    }

    return {
      cover: "Cover Letter",
      schedule: "Schedule of Stay",
      reason: "Statement of Purpose",
      financial: "Financial Declaration",
    };
  }

  const docLabels = getDocLabels();
  const effectivePacket =
    packet ||
    (caseData.packet_snapshot as Record<string, unknown> | null) ||
    (["packet_ready", "submitted"].includes(caseData.status)
      ? { reference: caseData.reference, checklist: [], forms: [], dossier_order: [] }
      : null);

  function getDocText(doc: DocType): {
    title: string;
    stem: string;
    text: string;
    isAi: boolean;
  } {
    let base = { title: "", stem: "", text: "" };
    switch (doc) {
      case "schedule":
        base = {
          title: docLabels.schedule,
          stem: `${caseData.reference}-schedule`,
          text: generateScheduleOfStay(caseData, effectivePacket),
        };
        break;
      case "reason":
        base = {
          title: docLabels.reason,
          stem: `${caseData.reference}-statement-of-purpose`,
          text: generateReasonForVisit(caseData, effectivePacket),
        };
        break;
      case "financial":
        base = {
          title: docLabels.financial,
          stem: `${caseData.reference}-financial-affidavit`,
          text: generateFinancialGuarantee(caseData, effectivePacket),
        };
        break;
      case "cover":
      default:
        base = {
          title: docLabels.cover,
          stem: `${caseData.reference}-cover-letter`,
          text: generateCoverLetter(caseData, effectivePacket),
        };
        break;
    }

    if (aiDrafts[doc]) {
      return { ...base, text: aiDrafts[doc]!, isAi: true };
    }
    return { ...base, isAi: false };
  }

  function getActiveDocText() {
    return getDocText(activeDoc);
  }

  function handleCopyActiveDoc() {
    const { text } = getActiveDocText();
    void navigator.clipboard.writeText(text);
    setCopiedDoc(true);
    setTimeout(() => setCopiedDoc(false), 2000);
  }

  function saveFile(bytes: BlobPart, filename: string, mediaType: string) {
    const url = URL.createObjectURL(new Blob([bytes], { type: mediaType }));
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

  /**
   * Render the drafts as real files.
   *
   * The text is sent to the server rather than saved from the browser because the same
   * text has to come back as a paginated PDF or an editable Word file, not only as the
   * plain `.txt` this step used to be limited to. What is sent is exactly what is on
   * screen — template, AI draft, or either after the applicant edited it.
   */
  async function exportDocuments(fmt: ExportFormat, scope: "active" | "all") {
    const activeToken =
      token || (typeof window !== "undefined" ? localStorage.getItem("torii_token") : null);
    if (!activeToken) {
      toast.error("Please sign in again to download your documents.");
      return;
    }

    const selected: DocType[] = scope === "all" ? DOC_ORDER : [activeDoc];
    const documents = selected.map((doc) => {
      const { title, stem, text } = getDocText(doc);
      return { title, content: text, filename_stem: stem };
    });

    setExporting(`${scope}:${fmt}`);
    try {
      const file = await exportCaseDocuments(activeToken, caseData.id, {
        documents,
        format: fmt,
        separate: scope === "all",
      });
      const binary = atob(file.data_base64);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      saveFile(bytes, file.filename, file.media_type);
      toast.success(
        scope === "all"
          ? `All ${documents.length} documents downloaded as ${fmt.toUpperCase()} in a zip.`
          : `${FORMAT_LABELS[fmt]} downloaded.`,
      );
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Download failed. Please try again.");
    } finally {
      setExporting(null);
    }
  }


  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between border-b pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-semibold text-foreground">
              {formatScopeLabel(caseData.scope_label) || "Application Package"}
            </h3>
            <Badge tone="success" className="text-[11px]">
              {caseData.status === "submitted" ? "Submitted" : "Ready to File"}
            </Badge>
          </div>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Ref: <span className="font-mono font-medium text-foreground">{caseData.reference}</span>
          </p>
        </div>
      </div>

      {!effectivePacket ? (
        <Card>
          <CardContent className="flex flex-col items-center py-10 text-center space-y-3">
            <Sparkles className="size-8 text-primary/60" />
            <div>
              <p className="text-sm font-semibold">Assemble Filing Package</p>
              <p className="text-xs text-muted-foreground mt-1 max-w-md mx-auto">
                Generate your official forms, cover letter, and document package.
              </p>
            </div>
            <Button onClick={onBuild} disabled={loading} size="sm" className="mt-2 text-xs">
              {loading ? <Loader2 className="mr-1.5 size-3.5 animate-spin" /> : <Layers className="mr-1.5 size-3.5" />}
              Assemble Package
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          {/* Supporting Letters & Statements Editor */}
          <Card>
            <CardContent className="p-4 sm:p-5 space-y-4">
              {/* Toolbar */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b pb-3">
                <div>
                  <h4 className="text-sm font-semibold text-foreground">
                    Supporting Letters &amp; Statements
                  </h4>
                  <p className="text-[11px] text-muted-foreground">
                    Review or customize required statements before signing.
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleGenerateAIDraft()}
                    disabled={aiDrafting !== null}
                    className="text-xs h-8"
                  >
                    {aiDrafting === activeDoc ? (
                      <Loader2 className="mr-1.5 size-3.5 animate-spin" />
                    ) : (
                      <Sparkles className="mr-1.5 size-3.5 text-primary" />
                    )}
                    {getActiveDocText().isAi ? "Regenerate" : "Draft with AI"}
                  </Button>

                  {getActiveDocText().isAi && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleResetToTemplate}
                      className="text-xs h-8 text-muted-foreground hover:text-foreground"
                    >
                      Reset
                    </Button>
                  )}

                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowPromptInput((prev) => !prev)}
                    className="text-xs h-8 text-muted-foreground hover:text-foreground"
                    title="Customize AI instructions"
                  >
                    Instructions
                  </Button>

                  <div className="h-4 w-px bg-border mx-0.5" />

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleCopyActiveDoc}
                    className="text-xs h-8"
                  >
                    {copiedDoc ? (
                      <>
                        <Check className="mr-1.5 size-3.5 text-[var(--color-success)]" /> Copied
                      </>
                    ) : (
                      <>
                        <Copy className="mr-1.5 size-3.5" /> Copy
                      </>
                    )}
                  </Button>

                  {/* Format Toggle */}
                  <div className="inline-flex overflow-hidden rounded-md border text-xs">
                    {(["pdf", "docx"] as ExportFormat[]).map((fmt) => (
                      <button
                        key={fmt}
                        type="button"
                        onClick={() => setExportFormat(fmt)}
                        className={`px-2.5 py-1 text-[11px] font-medium transition-colors ${
                          exportFormat === fmt
                            ? "bg-primary text-primary-foreground"
                            : "bg-transparent text-muted-foreground hover:bg-accent"
                        }`}
                      >
                        {fmt === "docx" ? "Word" : fmt.toUpperCase()}
                      </button>
                    ))}
                  </div>

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => void exportDocuments(exportFormat, "active")}
                    disabled={exporting !== null}
                    className="text-xs h-8"
                  >
                    {exporting === `active:${exportFormat}` ? (
                      <Loader2 className="mr-1.5 size-3.5 animate-spin" />
                    ) : (
                      <Download className="mr-1.5 size-3.5" />
                    )}
                    Download
                  </Button>

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => void exportDocuments(exportFormat, "all")}
                    disabled={exporting !== null}
                    className="text-xs h-8"
                    title={`Download all ${DOC_ORDER.length} statements in a zip`}
                  >
                    {exporting === `all:${exportFormat}` ? (
                      <Loader2 className="mr-1.5 size-3.5 animate-spin" />
                    ) : (
                      <Layers className="mr-1.5 size-3.5" />
                    )}
                    All (.zip)
                  </Button>
                </div>
              </div>

              {/* Optional Custom Instructions Input */}
              {showPromptInput && (
                <div className="rounded-md border bg-muted/20 p-2.5 space-y-2">
                  <div className="flex items-center justify-between">
                    <label className="text-[11px] font-medium text-foreground">
                      Custom AI Drafting Instructions (Optional)
                    </label>
                  </div>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={customInstructions}
                      onChange={(e) => setCustomInstructions(e.target.value)}
                      placeholder="e.g. Emphasize work history and Japanese proficiency..."
                      className="flex-1 rounded-md border bg-background px-3 py-1.5 text-xs outline-none focus-visible:ring-1 focus-visible:ring-ring"
                    />
                    <Button
                      size="sm"
                      onClick={() => handleGenerateAIDraft()}
                      disabled={aiDrafting !== null}
                      className="text-xs shrink-0"
                    >
                      {aiDrafting === activeDoc ? <Loader2 className="size-3.5 animate-spin" /> : "Apply"}
                    </Button>
                  </div>
                </div>
              )}

              {aiError && (
                <div className="rounded-md border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/10 p-2.5 text-xs text-[var(--color-danger)]">
                  {aiError}
                </div>
              )}

              {/* Clean Tabs */}
              <div className="flex flex-wrap gap-1 border-b pb-2.5">
                {[
                  { id: "cover" as DocType, label: docLabels.cover },
                  { id: "schedule" as DocType, label: docLabels.schedule },
                  { id: "reason" as DocType, label: docLabels.reason },
                  { id: "financial" as DocType, label: docLabels.financial },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveDoc(tab.id)}
                    className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-all ${
                      activeDoc === tab.id
                        ? "bg-muted text-foreground font-semibold shadow-xs"
                        : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                    }`}
                  >
                    <span>{tab.label}</span>
                    {aiDrafts[tab.id] && (
                      <span className="size-1.5 rounded-full bg-emerald-500" />
                    )}
                  </button>
                ))}
              </div>

              {/* Active Document Indicator */}
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-foreground">{getActiveDocText().title}</span>
                  {getActiveDocText().isAi && (
                    <Badge tone="success" className="text-[10px] py-0 px-1.5">AI Drafted</Badge>
                  )}
                </div>
                <span className="font-mono text-[11px]">{getActiveDocText().stem}.{exportFormat}</span>
              </div>

              {/* Textarea or Loading */}
              {aiDrafting === activeDoc ? (
                <div className="rounded-md border bg-muted/10 p-8 flex flex-col items-center justify-center gap-2 text-center">
                  <Loader2 className="size-5 text-primary animate-spin" />
                  <p className="text-xs font-medium text-foreground">Drafting with AI...</p>
                </div>
              ) : (
                <textarea
                  value={getActiveDocText().text}
                  onChange={(e) => handleTextEdit(e.target.value)}
                  rows={12}
                  className="w-full rounded-md border bg-muted/20 p-3.5 font-mono text-xs text-foreground/90 whitespace-pre leading-relaxed outline-none focus-visible:ring-1 focus-visible:ring-ring resize-y"
                  placeholder="Document text..."
                />
              )}
            </CardContent>
          </Card>

          {/* Journey Map */}
          <JourneyMap token={token} caseData={caseData} />

          {/* Document Submission Order */}
          <Card>
            <CardContent className="p-4 space-y-2.5">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Document Submission Order
              </h4>
              {effectivePacket && Array.isArray(effectivePacket.dossier_order) && effectivePacket.dossier_order.length > 0 ? (
                <ol className="space-y-1.5 text-xs text-foreground">
                  {(effectivePacket.dossier_order as string[]).map((item, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <Badge tone="muted" className="text-[10px] shrink-0">{idx + 1}</Badge>
                      <span>{item.replace(/^\d+\.\s*/, "")}</span>
                    </li>
                  ))}
                </ol>
              ) : (
                <ol className="space-y-1.5 text-xs text-foreground">
                  <li className="flex items-center gap-2">
                    <Badge tone="muted" className="text-[10px]">1</Badge> Signed Application Form
                  </li>
                  <li className="flex items-center gap-2">
                    <Badge tone="muted" className="text-[10px]">2</Badge> Cover Letter &amp; Statements
                  </li>
                  <li className="flex items-center gap-2">
                    <Badge tone="muted" className="text-[10px]">3</Badge> Valid Passport &amp; Bio-Data Copy
                  </li>
                  <li className="flex items-center gap-2">
                    <Badge tone="muted" className="text-[10px]">4</Badge> Passport Photographs
                  </li>
                  <li className="flex items-center gap-2">
                    <Badge tone="muted" className="text-[10px]">5</Badge> Proof of Financial Solvency (Bank Statements)
                  </li>
                  <li className="flex items-center gap-2">
                    <Badge tone="muted" className="text-[10px]">6</Badge> Flight / Travel Bookings &amp; Itinerary
                  </li>
                </ol>
              )}
            </CardContent>
          </Card>

          {/* Mark as Filed */}
          {caseData.status !== "submitted" ? (
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between border-t pt-4">
              <p className="text-xs text-muted-foreground">
                Ready to submit? Mark this application as filed to track status and deadlines.
              </p>
              <Button onClick={onSubmit} disabled={loading} className="shrink-0">
                {loading ? <Loader2 className="mr-2 size-4 animate-spin" /> : <Send className="mr-2 size-4" />}
                Mark as Filed
              </Button>
            </div>
          ) : (
            <div className="flex items-center gap-2 rounded-lg border border-[var(--color-success)]/30 bg-[var(--color-success)]/10 p-3 text-xs text-[var(--color-success)]">
              <Check className="size-4 shrink-0" />
              <span>
                Recorded as filed ·{" "}
                <span className="font-mono font-bold">
                  {caseData.submission_reference || caseData.reference}
                </span>
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
