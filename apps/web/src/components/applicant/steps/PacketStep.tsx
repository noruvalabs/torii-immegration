"use client";

import { useState } from "react";
import {
  Check,
  Download,
  Send,
  Loader2,
  FileText,
  Copy,
  ExternalLink,
  ShieldCheck,
  CheckSquare,
  Sparkles,
  Layers,
  ArrowRight,
  Coins,
  Zap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { useAuth } from "@/lib/auth-context";
import { useCredits } from "@/lib/credits-context";
import { draftDocument } from "@/lib/api/ai";
import { toast } from "@/components/ui/sonner";
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

function generateCompleteOfficialForm(
  caseData: Case,
  packet: Record<string, unknown> | null,
): string {
  const answers = caseData.intake_answers || {};
  let fieldsStr = "";
  for (const [key, value] of Object.entries(answers)) {
    if (value !== null && value !== "") {
      fieldsStr += `  ${key.replace(/_/g, " ").padEnd(38)}: ${String(value)}\n`;
    }
  }

  return `YOUR ANSWERS, AS RECORDED
(Check these against the official form before you sign it.)

${fieldsStr || "  No answers recorded yet."}
`;
}

function generateCompleteFilingKitText(source: Record<string, unknown>, caseData: Case): string {
  const coverLetter = generateCoverLetter(caseData, source);
  const schedule = generateScheduleOfStay(caseData, source);
  const reason = generateReasonForVisit(caseData, source);
  const financial = generateFinancialGuarantee(caseData, source);
  const formSheet = generateCompleteOfficialForm(caseData, source);

  return `================================================================================
TORII IMMIGRATION — COMPLETE OFFICIAL VISA FILING KIT & DOSSIER
Reference: ${source.reference ?? caseData.reference}
Scope: ${caseData.scope_label ?? caseData.locale.toUpperCase()}
Generated: ${new Date().toISOString()}
================================================================================

================================================================================
DOCUMENT 1: OFFICIAL EMBASSY COVER LETTER
================================================================================
${coverLetter}

================================================================================
DOCUMENT 2: SCHEDULE OF STAY / DAILY ITINERARY (滞在予定表)
================================================================================
${schedule}

================================================================================
DOCUMENT 3: REASON FOR VISIT / PERSONAL STATEMENT (理由書)
================================================================================
${reason}

================================================================================
DOCUMENT 4: FINANCIAL GUARANTEE & EXPENSE DECLARATION (身元保証書 / 経費支弁書)
================================================================================
${financial}

================================================================================
DOCUMENT 5: OFFICIAL VISA APPLICATION FORM DATA SHEET
================================================================================
${formSheet}

================================================================================
DOCUMENT 6: PHYSICAL DOSSIER ASSEMBLY ORDER & PACKING SLIP
================================================================================
Arrange physical paper documents in this exact order:
1. Official Signed Visa Application Form (with photo)
2. Day-by-Day Schedule of Stay (Itinerary Table)
3. Official Embassy Cover Letter
4. Statement of Reason for Visit (Personal Statement)
5. Financial Guarantee & Bank Statements
6. Valid Original Passport & Bio-Data Photocopy
7. Proof of Employment / Business Registration
8. Accommodation & Flight Bookings

================================================================================
End of Complete Filing Kit · Torii Immigration Platform
================================================================================
`;
}

type DocType = "cover" | "schedule" | "reason" | "financial" | "form" | "full";

export function PacketStep({ packet, caseData, loading, onBuild, onSubmit }: PacketStepProps) {
  const { token } = useAuth();
  const { balance, unlockCase } = useCredits();
  const [activeDoc, setActiveDoc] = useState<DocType>("cover");
  const [copiedDoc, setCopiedDoc] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState<string | null>(null);
  const [isUnlocking, setIsUnlocking] = useState(false);
  const [unlocked, setUnlocked] = useState(Boolean(caseData.is_entitled));
  const [aiDrafts, setAiDrafts] = useState<Partial<Record<DocType, string>>>({});
  const [aiDrafting, setAiDrafting] = useState<DocType | null>(null);
  const [customInstructions, setCustomInstructions] = useState("");
  const [showPromptInput, setShowPromptInput] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);
  const [trackedSteps, setTrackedSteps] = useState({
    filledOnline: false,
    paidFee: false,
    bookedAppointment: false,
    submittedDossier: caseData.status === "submitted",
  });

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
        form: "official_form_data",
        full: "complete_filing_kit",
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

    if (endpoint === "dossier-packet" && !unlocked) {
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
          cover: "📄 Bureau Cover Letter",
          schedule: "💼 Job Duties Specification (職務内容説明書)",
          reason: "✍️ Statement of Reason (採用理由書)",
          financial: "💰 Tax & Income Proof (納税・所得証明)",
          form: "📋 ISA Form Data Sheet",
          full: "📦 Complete Dossier Kit",
        };
      }
      if (isStudent) {
        return {
          cover: "📄 Embassy Cover Letter",
          schedule: "🎓 Study & Activity Plan",
          reason: "✍️ Statement of Purpose (志望理由書)",
          financial: "💰 Sponsor & Solvency Affidavit",
          form: "📋 Student Visa Form Data",
          full: "📦 Complete Student Dossier",
        };
      }
      return {
        cover: "📄 Embassy Cover Letter",
        schedule: "🗓️ Schedule of Stay (滞在予定表)",
        reason: "✍️ Reason for Visit (招へい理由書)",
        financial: "💰 Financial Guarantee (身元保証書)",
        form: "📋 Visa Form Data Sheet",
        full: "📦 Complete Tourist Pack",
      };
    }

    if (isUSA) {
      return {
        cover: "📄 Consular Cover Letter",
        schedule: "🗓️ Travel Itinerary & Flight Plan",
        reason: "✍️ Statement of Purpose",
        financial: "💰 Financial Solvency Affidavit",
        form: "📋 DS-160 Filing Summary",
        full: "📦 Complete US Visa Packet",
      };
    }

    if (isUK) {
      return {
        cover: "📄 UKVI Cover Letter",
        schedule: "🗓️ UK Travel & Stay Itinerary",
        reason: "✍️ Purpose of Visit Statement",
        financial: "💰 Maintenance & Solvency Proof",
        form: "📋 UKVI Application Data",
        full: "📦 Complete UK Visa Kit",
      };
    }

    if (isSchengen) {
      return {
        cover: "📄 Schengen Cover Letter",
        schedule: "🗓️ Multi-City Schengen Itinerary",
        reason: "✍️ Travel Intent Declaration",
        financial: "💰 Proof of Means of Subsistence",
        form: "📋 Uniform Schengen Form Data",
        full: "📦 Complete Schengen Dossier",
      };
    }

    return {
      cover: "📄 Formal Cover Letter",
      schedule: "🗓️ Schedule of Stay",
      reason: "✍️ Statement of Purpose",
      financial: "💰 Financial Declaration",
      form: "📋 Application Form Summary",
      full: "📦 Complete Filing Dossier",
    };
  }

  const docLabels = getDocLabels();
  const effectivePacket =
    packet ||
    (caseData.packet_snapshot as Record<string, unknown> | null) ||
    (caseData.status === "packet_ready" ? { reference: caseData.reference } : null);

  function getActiveDocText(): { title: string; filename: string; text: string; isAi: boolean } {
    let base = { title: "", filename: "", text: "" };
    switch (activeDoc) {
      case "schedule":
        base = {
          title: docLabels.schedule.replace(/^[^\w]+/, ""),
          filename: `${caseData.reference}-schedule-of-stay.txt`,
          text: generateScheduleOfStay(caseData, effectivePacket),
        };
        break;
      case "reason":
        base = {
          title: docLabels.reason.replace(/^[^\w]+/, ""),
          filename: `${caseData.reference}-reason-for-visit.txt`,
          text: generateReasonForVisit(caseData, effectivePacket),
        };
        break;
      case "financial":
        base = {
          title: docLabels.financial.replace(/^[^\w]+/, ""),
          filename: `${caseData.reference}-financial-guarantee.txt`,
          text: generateFinancialGuarantee(caseData, effectivePacket),
        };
        break;
      case "form":
        base = {
          title: docLabels.form.replace(/^[^\w]+/, ""),
          filename: `${caseData.reference}-official-form-data.txt`,
          text: generateCompleteOfficialForm(caseData, effectivePacket),
        };
        break;
      case "full":
        base = {
          title: docLabels.full.replace(/^[^\w]+/, ""),
          filename: `${caseData.reference}-complete-filing-kit.txt`,
          text: generateCompleteFilingKitText(effectivePacket || {}, caseData),
        };
        break;
      case "cover":
      default:
        base = {
          title: docLabels.cover.replace(/^[^\w]+/, ""),
          filename: `${caseData.reference}-embassy-cover-letter.txt`,
          text: generateCoverLetter(caseData, effectivePacket),
        };
        break;
    }

    if (aiDrafts[activeDoc]) {
      return { ...base, text: aiDrafts[activeDoc]!, isAi: true };
    }
    return { ...base, isAi: false };
  }

  function handleCopyActiveDoc() {
    const { text } = getActiveDocText();
    void navigator.clipboard.writeText(text);
    setCopiedDoc(true);
    setTimeout(() => setCopiedDoc(false), 2000);
  }

  function handleDownloadActiveDoc() {
    const { filename, text } = getActiveDocText();
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    setTimeout(() => {
      link.remove();
      URL.revokeObjectURL(url);
    }, 5000);
  }

  function downloadFullFilingKit() {
    if (!effectivePacket) return;
    const filename = `${caseData.reference}-complete-filing-kit.txt`;
    const blob = new Blob([generateCompleteFilingKitText(effectivePacket, caseData)], {
      type: "text/plain;charset=utf-8",
    });
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


  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-base font-semibold text-foreground">Application Filing Kit &amp; Package</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            Everything assembled for your application — Official PDFs, Cover Letter, Form Guide, and Filing Kit.
          </p>
        </div>
        <Badge tone="success" className="w-fit">
          <ShieldCheck className="mr-1 size-3.5" /> Agency-Grade Package Ready
        </Badge>
      </div>

      {!effectivePacket ? (
        <Card>
          <CardContent className="flex flex-col items-center py-10 text-center space-y-3">
            <Sparkles className="size-10 text-primary/50" />
            <div>
              <p className="text-base font-semibold">Assemble Your Complete Filing Kit</p>
              <p className="text-xs text-muted-foreground mt-1 max-w-md mx-auto">
                Generate your personalized Embassy Cover Letter, Step-by-Step Filing Instructions, and Official PDF Package.
              </p>
            </div>
            <Button onClick={onBuild} disabled={loading} className="mt-2">
              {loading ? <Loader2 className="mr-2 size-4 animate-spin" /> : <Layers className="mr-2 size-4" />}
              Assemble Filing Kit
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          {/* Top Banner: Success & Agency Value */}
          <Card className="border-[var(--color-success)]/30 bg-[var(--color-success)]/5">
            <CardContent className="p-5 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="flex size-10 items-center justify-center rounded-full bg-[var(--color-success)]/20 text-[var(--color-success)] shrink-0">
                  <Check className="size-5" />
                </div>
                <div>
                  <h4 className="text-base font-bold tracking-tight text-foreground">
                    Filing Kit Assembled for {caseData.reference}
                  </h4>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    Scope: <span className="font-semibold text-foreground">{caseData.scope_label ?? caseData.locale.toUpperCase()}</span>
                  </p>
                  <p className="mt-1 text-xs text-foreground/80">
                    Your official forms are filled from your answers and your documents are
                    listed. Check every entry and sign before you file — Torii prepares the
                    paperwork, it does not verify your documents or approve your application.
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2 shrink-0">
                <Button
                  onClick={() =>
                    downloadPdf("dossier-packet", `${caseData.reference}-Complete-Dossier.pdf`)
                  }
                  disabled={downloadingPdf === "dossier-packet"}
                  className="px-3.5 py-1.5 text-xs font-semibold shadow"
                >
                  {downloadingPdf === "dossier-packet" ? (
                    <Loader2 className="mr-1.5 size-4 animate-spin" />
                  ) : (
                    <Download className="mr-1.5 size-4" />
                  )}
                  Download Official Dossier (PDF)
                </Button>
                <Button
                  variant="outline"
                  onClick={() =>
                    downloadPdf("application-form", `${caseData.reference}-Application-Form.pdf`)
                  }
                  disabled={downloadingPdf === "application-form"}
                  className="px-3 py-1.5 text-xs"
                >
                  {downloadingPdf === "application-form" ? (
                    <Loader2 className="mr-1.5 size-4 animate-spin" />
                  ) : (
                    <FileText className="mr-1.5 size-4 text-primary" />
                  )}
                  Application Form (PDF)
                </Button>
                <Button
                  variant="outline"
                  onClick={() =>
                    downloadPdf("cover-letter", `${caseData.reference}-Cover-Letter.pdf`)
                  }
                  disabled={downloadingPdf === "cover-letter"}
                  className="px-3 py-1.5 text-xs"
                >
                  {downloadingPdf === "cover-letter" ? (
                    <Loader2 className="mr-1.5 size-4 animate-spin" />
                  ) : (
                    <FileText className="mr-1.5 size-4" />
                  )}
                  Cover Letter (PDF)
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Feature 1: Comprehensive AI Document Suite Generator */}
          <Card className="border-primary/20">
            <CardContent className="p-5 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b pb-4">
                <div className="flex items-center gap-2.5">
                  <FileText className="size-5 text-primary" />
                  <div>
                    <h4 className="text-sm font-bold tracking-tight">AI Generated Official Document Suite</h4>
                    <p className="text-[11px] text-muted-foreground">
                      All required embassy drafts generated automatically from your intake answers and verified criteria.
                    </p>
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <Button
                    onClick={() => handleGenerateAIDraft()}
                    disabled={aiDrafting !== null}
                    className="px-3 py-1 text-xs font-semibold bg-gradient-to-r from-primary to-primary/80 hover:from-primary/90 hover:to-primary text-primary-foreground shadow"
                  >
                    {aiDrafting === activeDoc ? (
                      <Loader2 className="mr-1.5 size-3.5 animate-spin" />
                    ) : (
                      <Sparkles className="mr-1.5 size-3.5" />
                    )}
                    {getActiveDocText().isAi ? "Regenerate with AI" : "✨ Draft with AI"}
                  </Button>

                  {getActiveDocText().isAi && (
                    <Button
                      variant="ghost"
                      onClick={handleResetToTemplate}
                      className="px-2 py-1 text-xs text-muted-foreground hover:text-foreground"
                    >
                      Reset to Template
                    </Button>
                  )}

                  <Button
                    variant="outline"
                    onClick={() => setShowPromptInput((prev) => !prev)}
                    className="px-2.5 py-1 text-xs"
                    title="Customize AI prompt instructions"
                  >
                    Custom Prompt
                  </Button>

                  <Button variant="outline" onClick={handleCopyActiveDoc} className="px-2.5 py-1 text-xs">
                    {copiedDoc ? (
                      <>
                        <Check className="mr-1.5 size-3.5 text-[var(--color-success)]" /> Copied!
                      </>
                    ) : (
                      <>
                        <Copy className="mr-1.5 size-3.5" /> Copy
                      </>
                    )}
                  </Button>
                  <Button variant="outline" onClick={handleDownloadActiveDoc} className="px-2.5 py-1 text-xs">
                    <Download className="mr-1.5 size-3.5" /> Download (.txt)
                  </Button>
                </div>
              </div>

              {/* Optional Custom Instructions Input */}
              {showPromptInput && (
                <div className="rounded-lg border bg-muted/20 p-3 space-y-2 animate-in fade-in">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                      <Sparkles className="size-3 text-primary" />
                      Custom AI Drafting Instructions (Optional)
                    </label>
                    <span className="text-[10px] text-muted-foreground">e.g. emphasize work background, specific salary or itinerary</span>
                  </div>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={customInstructions}
                      onChange={(e) => setCustomInstructions(e.target.value)}
                      placeholder="e.g. Focus on my 5 years in Tokyo as a software engineer and Japanese proficiency..."
                      className="flex-1 rounded-md border bg-background px-3 py-1.5 text-xs outline-none focus-visible:ring-1 focus-visible:ring-ring"
                    />
                    <Button
                      onClick={() => handleGenerateAIDraft()}
                      disabled={aiDrafting !== null}
                      className="text-xs px-3 py-1.5 font-medium shrink-0"
                    >
                      {aiDrafting === activeDoc ? <Loader2 className="size-3.5 animate-spin" /> : "Generate"}
                    </Button>
                  </div>
                </div>
              )}

              {aiError && (
                <div className="rounded-md border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/10 p-2.5 text-xs text-[var(--color-danger)]">
                  {aiError}
                </div>
              )}

              {/* Document Selector Navigation Tabs */}
              <div className="flex flex-wrap gap-1.5 border-b pb-3">
                {[
                  { id: "cover" as DocType, label: docLabels.cover },
                  { id: "schedule" as DocType, label: docLabels.schedule },
                  { id: "reason" as DocType, label: docLabels.reason },
                  { id: "financial" as DocType, label: docLabels.financial },
                  { id: "form" as DocType, label: docLabels.form },
                  { id: "full" as DocType, label: docLabels.full },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveDoc(tab.id)}
                    className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${
                      activeDoc === tab.id
                        ? "bg-primary text-primary-foreground shadow-sm"
                        : "bg-muted/40 text-muted-foreground hover:bg-muted hover:text-foreground"
                    }`}
                  >
                    <span>{tab.label}</span>
                    {aiDrafts[tab.id] && (
                      <span className="size-1.5 rounded-full bg-emerald-400" />
                    )}
                  </button>
                ))}
              </div>

              {/* Active Document Header & Preview */}
              <div className="flex items-center justify-between pt-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-foreground">
                    {getActiveDocText().title}
                  </span>
                  {getActiveDocText().isAi && (
                    <Badge tone="success">✨ AI Personalized</Badge>
                  )}
                </div>
                <span className="text-[10px] text-muted-foreground font-mono">
                  {getActiveDocText().filename}
                </span>
              </div>

              {aiDrafting === activeDoc ? (
                <div className="rounded-md border bg-muted/20 p-8 flex flex-col items-center justify-center gap-3 text-center">
                  <Loader2 className="size-6 text-primary animate-spin" />
                  <div className="space-y-1">
                    <p className="text-xs font-semibold text-foreground">Drafting official document with AI...</p>
                    <p className="text-[11px] text-muted-foreground">Synthesizing your verified documents, case scope, and background details</p>
                  </div>
                </div>
              ) : (
                <textarea
                  value={getActiveDocText().text}
                  onChange={(e) => handleTextEdit(e.target.value)}
                  rows={14}
                  className="w-full rounded-md border bg-muted/30 p-4 font-mono text-xs text-foreground/90 whitespace-pre leading-relaxed shadow-inner outline-none focus-visible:ring-1 focus-visible:ring-ring resize-y"
                  placeholder="Official document text..."
                />
              )}
            </CardContent>
          </Card>

          {/* Feature 2: Official Step-by-Step Submission Roadmap */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-bold tracking-tight flex items-center gap-2">
                <ArrowRight className="size-4 text-primary" /> Official Submission Roadmap &amp; Filing Channels
              </h4>
              <span className="text-[11px] text-muted-foreground">Every instruction backed by official government source</span>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              {effectivePacket && Array.isArray(effectivePacket.submission_steps) && effectivePacket.submission_steps.length > 0 ? (
                (effectivePacket.submission_steps as {
                  step?: number;
                  title?: string;
                  description?: string;
                  portal_url?: string | null;
                  authority?: string | null;
                  official_citation_url?: string | null;
                  category?: string | null;
                }[]).map((st, i) => (
                  <div key={i} className="rounded-xl border border-border bg-card p-4 space-y-2 flex flex-col justify-between shadow-xs">
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between gap-2">
                        <Badge tone="default">Step {st.step ?? i + 1}</Badge>
                        {st.authority && (
                          <span className="text-[10px] text-muted-foreground truncate max-w-[190px]" title={st.authority}>
                            🏛️ {st.authority}
                          </span>
                        )}
                      </div>
                      <p className="text-xs font-bold text-foreground pt-1">{st.title}</p>
                      <p className="text-[11px] text-muted-foreground leading-relaxed">{st.description}</p>
                    </div>

                    <div className="pt-2 border-t flex flex-wrap items-center justify-between gap-2 text-[11px]">
                      {st.portal_url ? (
                        <a
                          href={st.portal_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-primary hover:underline font-semibold"
                        >
                          <ExternalLink className="size-3" />
                          Open Official Portal
                        </a>
                      ) : (
                        <span className="text-muted-foreground text-[10px]">In-Person / Consular Channel</span>
                      )}

                      {st.official_citation_url && (
                        <a
                          href={st.official_citation_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-muted-foreground hover:text-foreground text-[10px]"
                          title="Verify official government regulation"
                        >
                          Verify Source ↗
                        </a>
                      )}
                    </div>
                  </div>
                ))
              ) : (
                <>
                  <div className="rounded-xl border bg-card p-4 space-y-1">
                    <div className="flex items-center justify-between">
                      <Badge tone="default">Step 1</Badge>
                      <span className="text-[10px] text-primary font-semibold">Online Portal</span>
                    </div>
                    <p className="text-xs font-semibold text-foreground pt-1">Fill Official Government Form</p>
                    <p className="text-[11px] text-muted-foreground">
                      Use Torii&apos;s copyable field guide from the Forms tab to fill out the embassy web portal.
                    </p>
                  </div>
                  <div className="rounded-xl border bg-card p-4 space-y-1">
                    <div className="flex items-center justify-between">
                      <Badge tone="default">Step 2</Badge>
                      <span className="text-[10px] text-primary font-semibold">Filing Fee</span>
                    </div>
                    <p className="text-xs font-semibold text-foreground pt-1">Pay Official Visa Fee</p>
                    <p className="text-[11px] text-muted-foreground">
                      Pay required fee through the government payment gateway and save receipt.
                    </p>
                  </div>
                  <div className="rounded-xl border bg-card p-4 space-y-1">
                    <div className="flex items-center justify-between">
                      <Badge tone="default">Step 3</Badge>
                      <span className="text-[10px] text-primary font-semibold">Appointment</span>
                    </div>
                    <p className="text-xs font-semibold text-foreground pt-1">Book Biometrics &amp; Interview</p>
                    <p className="text-[11px] text-muted-foreground">
                      Schedule appointment date at the nearest Visa Application Center or Embassy.
                    </p>
                  </div>
                  <div className="rounded-xl border bg-card p-4 space-y-1">
                    <div className="flex items-center justify-between">
                      <Badge tone="default">Step 4</Badge>
                      <span className="text-[10px] text-primary font-semibold">Dossier</span>
                    </div>
                    <p className="text-xs font-semibold text-foreground pt-1">Stack Physical Dossier</p>
                    <p className="text-[11px] text-muted-foreground">
                      Arrange physical documents in exact order specified in your Torii filing kit.
                    </p>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Feature 3: Physical Dossier Assembly Stack Order */}
          <Card>
            <CardContent className="p-4 space-y-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Physical Dossier Stacking Order (For Embassy Interview / VAC Dropoff)
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
                    <Badge tone="muted" className="text-[10px]">1</Badge> Signed Official Cover Letter (Generated by Torii above)
                  </li>
                  <li className="flex items-center gap-2">
                    <Badge tone="muted" className="text-[10px]">2</Badge> Government Application Confirmation / Summary Page
                  </li>
                  <li className="flex items-center gap-2">
                    <Badge tone="muted" className="text-[10px]">3</Badge> Original Valid Passport &amp; Previous Passports
                  </li>
                  <li className="flex items-center gap-2">
                    <Badge tone="muted" className="text-[10px]">4</Badge> Official Passport Photographs (Matching specifications)
                  </li>
                  <li className="flex items-center gap-2">
                    <Badge tone="muted" className="text-[10px]">5</Badge> Proof of Financial Capability (Bank Statements / Salary Slips)
                  </li>
                  <li className="flex items-center gap-2">
                    <Badge tone="muted" className="text-[10px]">6</Badge> Confirmed Travel Itinerary &amp; Hotel Bookings
                  </li>
                </ol>
              )}
            </CardContent>
          </Card>

          {/* Feature 4: Interactive Progress & Submission Button */}
          <Card className="border-primary/30">
            <CardContent className="p-5 space-y-4">
              <div className="flex items-center gap-2">
                <CheckSquare className="size-5 text-primary" />
                <h4 className="text-sm font-bold tracking-tight">Filing Tracker &amp; Finalize Case</h4>
              </div>

              <div className="space-y-2 text-xs">
                <label className="flex items-center gap-2.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={trackedSteps.filledOnline}
                    onChange={(e) => setTrackedSteps({ ...trackedSteps, filledOnline: e.target.checked })}
                    className="rounded text-primary focus:ring-primary size-4"
                  />
                  <span>I have entered my application data into the official government portal.</span>
                </label>

                <label className="flex items-center gap-2.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={trackedSteps.paidFee}
                    onChange={(e) => setTrackedSteps({ ...trackedSteps, paidFee: e.target.checked })}
                    className="rounded text-primary focus:ring-primary size-4"
                  />
                  <span>I have paid the embassy/consulate filing fee and saved the receipt.</span>
                </label>

                <label className="flex items-center gap-2.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={trackedSteps.bookedAppointment}
                    onChange={(e) => setTrackedSteps({ ...trackedSteps, bookedAppointment: e.target.checked })}
                    className="rounded text-primary focus:ring-primary size-4"
                  />
                  <span>I have scheduled my visa interview / biometrics appointment.</span>
                </label>
              </div>

              {caseData.status !== "submitted" ? (
                <div className="pt-2">
                  <Button onClick={onSubmit} disabled={loading} className="w-full sm:w-auto">
                    {loading ? <Loader2 className="mr-2 size-4 animate-spin" /> : <Send className="mr-2 size-4" />}
                    Mark Application Submitted in Torii
                  </Button>
                </div>
              ) : (
                <div className="rounded border border-[var(--color-success)]/30 bg-[var(--color-success)]/10 p-3 text-xs flex items-center gap-2 text-[var(--color-success)]">
                  <Check className="size-4 shrink-0" />
                  <span>
                    Case Submitted Successfully! Reference:{" "}
                    <span className="font-mono font-bold">{caseData.submission_reference || caseData.reference}</span>
                  </span>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
