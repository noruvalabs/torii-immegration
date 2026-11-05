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
  CheckCircle2,
  AlertTriangle,
  Upload,
  Bot,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { useAuth } from "@/lib/auth-context";
import { useCredits } from "@/lib/credits-context";
import { draftDocument } from "@/lib/api/ai";
import { exportCaseDocuments, type ExportFormat } from "@/lib/api/cases";
import { dispatchPortalBot, type PortalJob } from "@/lib/api/portal-bot";
import { PortalBotConsole } from "@/components/applicant/PortalBotConsole";
import { toast } from "@/components/ui/sonner";
import { PostSubmissionGuide } from "./PostSubmissionGuide";
import type { Case } from "./types";

type PacketStepProps = {
  packet: Record<string, unknown> | null;
  caseData: Case;
  loading: boolean;
  onBuild: () => void;
  onSubmit: () => void;
  canSubmit?: boolean;
  missingDocsCount?: number;
  onGoToChecklist?: () => void;
};

// These are drafts the applicant completes and signs, not finished official documents.
// Nothing here may assert a fact the applicant has not stated.
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
  const fullName = answered(answers, "full_name", "applicant_name", "name") || "Applicant";
  const passportNo = answered(answers, "passport_number", "passport_no") || "On File";
  const passportExpiry = answered(answers, "passport_expiry", "passport_expiry_date");
  const nationality = answered(answers, "nationality", "citizenship", "country_of_citizenship") || "Citizen";
  const residenceCountry = answered(answers, "current_residence_country", "current_country", "residence_country");
  const dob = answered(answers, "date_of_birth", "dob");

  const isIndia =
    reference.startsWith("IN-") ||
    caseData.jurisdiction_code === "IN" ||
    scope.toLowerCase().includes("india");

  const isUK =
    reference.startsWith("UK-") ||
    reference.startsWith("GB-") ||
    caseData.jurisdiction_code === "UK" ||
    scope.toLowerCase().includes("united kingdom");

  // Medical visa specific fields
  const hospital = answered(answers, "destination_hospital", "hospital_name");
  const hospitalCity = answered(answers, "hospital_city");
  const treatment = answered(answers, "illness_treatment_category", "medical_condition");
  const attendants = answered(answers, "accompanying_attendants_count");

  // General visit / work fields
  const purpose = answered(answers, "main_purpose", "purpose_of_visit", "illness_treatment_category");
  const stayDays = answered(answers, "stay_duration_days", "intended_length_of_stay_days");
  const arrivalDate = answered(answers, "planned_arrival_date");
  const employer = answered(answers, "employer_name", "company_name");
  const occupation = answered(answers, "occupation", "job_title");

  // 1. Indian Medical Visa
  if (isIndia && (scope.toLowerCase().includes("medical") || hospital !== BLANK || treatment !== BLANK)) {
    return `To:
The Consular Officer / Visa Section
High Commission of India / Embassy of India

Date: ${dateStr}
Reference: ${reference}

SUBJECT: APPLICATION FOR INDIAN MEDICAL VISA (MED-1) – ${fullName.toUpperCase()}

Dear Consular Officer,

I am writing to formally submit my visa application for an Indian Medical Visa (MED-1) to undergo specialized medical treatment in India.

1. APPLICANT PARTICULARS:
   • Full Name: ${fullName}
   • Nationality: ${nationality}
   • Passport Number: ${passportNo}${passportExpiry !== BLANK ? ` (Valid until: ${passportExpiry})` : ""}
   • Country of Residence: ${residenceCountry !== BLANK ? residenceCountry : nationality}
   ${dob !== BLANK ? `• Date of Birth: ${dob}` : ""}

2. PURPOSE OF VISIT & TREATMENT DETAILS:
   • Medical Condition / Category: ${treatment !== BLANK ? treatment : "Specialized Medical Treatment"}
   • Destination Hospital: ${hospital !== BLANK ? hospital : "Recognized Specialized Hospital"}${hospitalCity !== BLANK ? `, ${hospitalCity}` : ""}, India
   • Hospital Invitation: Secured from the treating hospital in India
   • Referral: Local physician referral and diagnostic case history enclosed
   ${attendants !== BLANK && Number(attendants) > 0 ? `• Accompanying Caregiver(s): ${attendants} attendant(s) under Medical Attendant (MED-2) route` : ""}

3. FINANCIAL UNDERTAKING:
   I confirm that all financial expenses relating to my medical consultation, hospital procedures, boarding, lodging, and return travel will be fully borne by myself. Proof of adequate financial solvency and bank statements are enclosed.

4. ENCLOSED SUPPORTING DOCUMENTS:
   1. Valid Passport and bio-data page copy
   2. Official Medical Visa Invitation Letter from ${hospital !== BLANK ? hospital : "Recognized Hospital in India"}
   3. Local medical referral certificate & diagnostic history
   4. Proof of financial solvency & recent bank statements
   5. Recent passport-sized color photographs

I respectfully request that my Medical Visa application be granted to facilitate my scheduled medical treatment in India. Please contact me if any further information is required.

Thank you for your assistance.

Sincerely yours,

________________________________________
${fullName}
Passport No: ${passportNo}
Date: ${dateStr}
`;
  }

  // 2. UK Visas
  if (isUK) {
    return `To:
UK Visas and Immigration (UKVI)
Home Office, United Kingdom

Date: ${dateStr}
Reference: ${reference}

SUBJECT: VISA APPLICATION COVER LETTER – ${fullName.toUpperCase()}
Category: ${scope}

Dear Visa Officer,

I am writing to formally submit my visa application for entry clearance to the United Kingdom under the ${scope} route.

1. APPLICANT DETAILS:
   • Full Name: ${fullName}
   • Nationality: ${nationality}
   • Passport Number: ${passportNo}${passportExpiry !== BLANK ? ` (Valid until: ${passportExpiry})` : ""}
   • Country of Residence: ${residenceCountry !== BLANK ? residenceCountry : nationality}

2. APPLICATION DETAILS & PURPOSE:
   • Category: ${scope}
   • Purpose of Travel: ${purpose !== BLANK ? purpose : "Travel and authorized stay in the United Kingdom"}
   ${stayDays !== BLANK ? `• Intended Duration of Stay: ${stayDays} days` : ""}
   ${arrivalDate !== BLANK ? `• Planned Arrival: ${arrivalDate}` : ""}
   ${employer !== BLANK ? `• Sponsor / Employer: ${employer}` : ""}

3. FINANCIAL DECLARATION & COMPLIANCE:
   I confirm that I possess sufficient funds to support myself throughout my intended stay in the United Kingdom without recourse to public funds. I undertake to abide by all immigration conditions and leave the United Kingdom upon conclusion of my authorized stay.

4. ENCLOSED DOCUMENTS:
   1. Valid Passport bio-data copy
   2. Comprehensive evidence of financial solvency and bank statements
   3. Supporting documentation and letters relevant to ${scope}
   4. Travel and accommodation details

Thank you for considering my application.

Yours sincerely,

________________________________________
${fullName}
Passport No: ${passportNo}
Date: ${dateStr}
`;
  }

  // 3. Japan / Generic Consular Visas
  return `To:
The Consular Section / Immigration Services Agency
Visa & Immigration Department

Date: ${dateStr}
Reference: ${reference}

SUBJECT: APPLICATION COVER LETTER – ${fullName.toUpperCase()}
Scope: ${scope}

Dear Consular Officer,

I respectfully submit my visa application for consideration under the ${scope} route.

1. APPLICANT INFORMATION:
   • Full Name: ${fullName}
   • Nationality: ${nationality}
   • Passport Number: ${passportNo}${passportExpiry !== BLANK ? ` (Valid until: ${passportExpiry})` : ""}
   • Current Residence: ${residenceCountry !== BLANK ? residenceCountry : nationality}

2. PURPOSE OF VISIT & INTENDED STAY:
   • Purpose: ${purpose !== BLANK ? purpose : "Travel and stay under designated visa category"}
   ${stayDays !== BLANK ? `• Intended Duration: ${stayDays} days` : ""}
   ${arrivalDate !== BLANK ? `• Planned Arrival: ${arrivalDate}` : ""}
   ${occupation !== BLANK ? `• Current Occupation: ${occupation}` : ""}
   ${employer !== BLANK ? `• Organization / Sponsor: ${employer}` : ""}

3. DECLARATION:
   All information provided in my application and supporting documents is genuine, complete, and accurate. All expenses incurred during my stay will be adequately covered. I will strictly adhere to the immigration laws and regulations of the destination country.

4. ENCLOSED DOCUMENTS:
   1. Valid Passport bio-data copy
   2. Financial documentation demonstrating solvency
   3. Supporting letters and certificates relevant to ${scope}
   4. Passport photographs

I respectfully request favorable consideration of my application.

Sincerely yours,

________________________________________
${fullName}
Passport No: ${passportNo}
Date: ${dateStr}
`;
}

export function generateScheduleOfStay(caseData: Case, packet: Record<string, unknown> | null): string {
  const answers = caseData.intake_answers || {};
  const fullName = answered(answers, "full_name", "applicant_name");
  const arrivalDate = answered(answers, "planned_arrival_date");
  const accommodation = answered(answers, "accommodation_name");
  const accommodationAddress = answered(answers, "accommodation_address");
  const rawDays = answers.stay_duration_days ?? answers.intended_length_of_stay_days;
  const stayDays = Number.parseInt(String(rawDays ?? ""), 10);

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

type DocType = "cover";

/** Tab order, and the order documents are written into a "download everything" zip. */
const DOC_ORDER: DocType[] = ["cover"];

const FORMAT_LABELS: Record<ExportFormat, string> = {
  pdf: "PDF",
  docx: "Word (.docx)",
};

export function PacketStep({
  packet,
  caseData,
  loading,
  onBuild,
  onSubmit,
  canSubmit = true,
  missingDocsCount = 0,
  onGoToChecklist,
}: PacketStepProps) {
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
  const [botJob, setBotJob] = useState<PortalJob | null>(null);
  const [botConsoleOpen, setBotConsoleOpen] = useState(false);
  const [botRunning, setBotRunning] = useState(false);

  const jCode = (caseData.jurisdiction_code || "").toUpperCase();
  const refCode = (caseData.reference || "").toUpperCase();
  const isAutomatedPortalTrack =
    caseData.submission_track === "digital" &&
    (jCode === "VN" || jCode === "SA" || refCode.startsWith("VN-") || refCode.startsWith("SA-"));
  const portalName = jCode === "SA" ? "ksavisa.sa" : jCode === "VN" ? "evisa.gov.vn" : "portal";

  async function handleLaunchPortalBot() {
    if (!token) return;
    setBotRunning(true);
    setBotConsoleOpen(true);
    try {
      const job = await dispatchPortalBot(token, caseData.id);
      setBotJob(job);
      if (job.status === "succeeded" && job.portal_reference) {
        toast.success(`Government registration captured: ${job.portal_reference}`);
        onSubmit();
      } else if (job.status === "manual_takeover" || job.status === "awaiting_otp") {
        toast.info(
          "Government verification code required. Enter your code in the console to complete.",
        );
      } else if (job.status === "failed") {
        toast.error(job.error_message || "Portal worker could not complete.");
      }
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Portal bot submission encountered an issue");
    } finally {
      setBotRunning(false);
    }
  }

  useEffect(() => {
    if (caseData.is_entitled || caseData.status === "submitted") {
      setUnlocked(true);
    }
  }, [caseData.is_entitled, caseData.status]);

  async function handleGenerateAIDraft() {
    setAiDrafting("cover");
    setAiError(null);
    try {
      const res = await draftDocument({
        doc_type: "cover_letter",
        jurisdiction_code: caseData.reference ? caseData.reference.split("-")[0] : "JP",
        scope_label: caseData.scope_label || caseData.locale.toUpperCase(),
        case_reference: caseData.reference || `CASE-${caseData.id}`,
        intake_answers: caseData.intake_answers || {},
        checklist: Array.isArray(packet?.checklist) ? (packet.checklist as Record<string, unknown>[]) : [],
        custom_instructions: customInstructions || undefined,
      });
      setAiDrafts((prev) => ({ ...prev, cover: res.content }));
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

  function getDocLabels() {
    if (isJapan) {
      return {
        cover: isWork ? "Bureau Cover Letter" : "Embassy Cover Letter",
      };
    }

    if (isUSA) {
      return {
        cover: "Consular Cover Letter",
      };
    }

    if (isUK) {
      return {
        cover: "UKVI Cover Letter",
      };
    }

    if (isSchengen) {
      return {
        cover: "Schengen Cover Letter",
      };
    }

    return {
      cover: "Cover Letter",
    };
  }

  const docLabels = getDocLabels();
  const effectivePacket =
    packet ||
    (caseData.packet_snapshot as Record<string, unknown> | null) ||
    (["packet_ready", "submitted"].includes(caseData.status)
      ? { reference: caseData.reference, checklist: [], forms: [], dossier_order: [] }
      : null);

  function getDocText(_doc: DocType = "cover"): {
    title: string;
    stem: string;
    text: string;
    isAi: boolean;
  } {
    const base = {
      title: docLabels.cover,
      stem: `${caseData.reference}-cover-letter`,
      text: generateCoverLetter(caseData, effectivePacket),
    };

    if (aiDrafts.cover) {
      return { ...base, text: aiDrafts.cover, isAi: true };
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

  async function exportDocuments(fmt: ExportFormat) {
    const activeToken =
      token || (typeof window !== "undefined" ? localStorage.getItem("torii_token") : null);
    if (!activeToken) {
      toast.error("Please sign in again to download your documents.");
      return;
    }

    const { title, stem, text } = getDocText("cover");
    const documents = [{ title, content: text, filename_stem: stem }];

    setExporting(fmt);
    try {
      const file = await exportCaseDocuments(activeToken, caseData.id, {
        documents,
        format: fmt,
        separate: false,
      });
      const binary = atob(file.data_base64);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      saveFile(bytes, file.filename, file.media_type);
      toast.success(`${FORMAT_LABELS[fmt]} downloaded.`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Download failed. Please try again.");
    } finally {
      setExporting(null);
    }
  }


  if (caseData.status === "submitted") {
    return (
      <div className="space-y-6">
        <PostSubmissionGuide
          token={token}
          caseData={caseData}
          onDownloadPdf={() => void exportDocuments("pdf")}
          isExportingPdf={exporting === "pdf"}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Official Government Submission Action Banner */}
      <Card
        className={`border-2 shadow-sm ${
          canSubmit
            ? "border-emerald-500/40 bg-emerald-500/5"
            : "border-amber-500/40 bg-amber-500/5"
        }`}
      >
        <CardContent className="p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Badge
                tone={canSubmit ? "default" : "warning"}
                className="text-xs font-bold uppercase tracking-wider"
              >
                {canSubmit ? "Final Step" : "Documents Missing"}
              </Badge>
              <h3 className="text-base font-bold text-foreground">
                {canSubmit
                  ? isAutomatedPortalTrack
                    ? `${jCode === "SA" ? "Saudi Arabia eVisa" : "Vietnam eVisa"} — fill ${portalName} from this case`
                    : "Ready to Submit to Torii Operations & Government Console"
                  : "Required Documents Must Be Uploaded"}
              </h3>
            </div>
            <p className="text-xs text-muted-foreground max-w-xl">
              {canSubmit
                ? isAutomatedPortalTrack
                  ? `This opens the official government portal (${portalName}) and fills matching fields from your case. When an OTP verification is requested, you can enter it directly in the console.`
                  : "Your dossier, questionnaire particulars, and required documents are compiled. Click below to submit your application directly to the Torii concierge operations team for official embassy portal filing."
                : `You cannot submit this application yet because ${missingDocsCount} required document(s) have not been uploaded. All required documents must be uploaded before final submission.`}
            </p>
          </div>
          {canSubmit ? (
            <Button
              size="lg"
              onClick={isAutomatedPortalTrack ? handleLaunchPortalBot : onSubmit}
              disabled={loading || botRunning}
              className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-6 shrink-0 shadow-md gap-2 cursor-pointer"
            >
              {loading || botRunning ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  <span>{botRunning ? `Connecting to ${portalName}…` : "Submitting…"}</span>
                </>
              ) : isAutomatedPortalTrack ? (
                <>
                  <Bot className="size-4" />
                  <span>{jCode === "SA" ? "Fill Saudi eVisa (ksavisa.sa)" : "Fill Vietnam eVisa form"}</span>
                </>
              ) : (
                <>
                  <Send className="size-4" />
                  <span>Submit Application</span>
                </>
              )}
            </Button>
          ) : (
            <Button
              size="lg"
              onClick={onGoToChecklist}
              className="bg-amber-600 hover:bg-amber-700 text-white font-bold px-6 shrink-0 shadow-md gap-2"
            >
              <Upload className="size-4" />
              <span>Upload Documents ({missingDocsCount} missing)</span>
            </Button>
          )}
        </CardContent>
      </Card>

      {/* Clean Application Copy & Cover Letter Download */}
      <Card className="border border-border/80 bg-card shadow-xs">
        <CardContent className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3 min-w-0">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <FileText className="size-5" />
            </div>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h4 className="text-sm font-bold text-foreground">
                  Official Embassy Cover Letter &amp; Summary
                </h4>
                <Badge tone="success" className="text-[10px] py-0 px-2 font-semibold">
                  Prepared by Staff
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5 max-w-xl">
                A formal consular cover letter with your passport details, travel purpose, and document citations has been generated by our team. You can download a personal copy for your records.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0 self-end sm:self-auto">
            <Button
              variant="outline"
              size="sm"
              onClick={() => void exportDocuments("pdf")}
              disabled={exporting !== null}
              className="text-xs h-9 gap-1.5 font-semibold px-4"
            >
              {exporting === "pdf" ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Download className="size-3.5" />
              )}
              Download PDF Copy
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Thing 3: Live eVisa Submission Bot Console */}
      <PortalBotConsole
        isOpen={botConsoleOpen}
        onClose={() => {
          setBotConsoleOpen(false);
          if (botJob?.status === "succeeded" && botJob.portal_reference) {
            onSubmit();
          }
        }}
        job={botJob}
        loading={botRunning}
        caseId={caseData.id}
        onJobUpdated={(updated) => {
          setBotJob(updated);
          if (updated.status === "succeeded" && updated.portal_reference) {
            toast.success(`Application verified & captured: ${updated.portal_reference}`);
            onSubmit();
          }
        }}
        onRetry={handleLaunchPortalBot}
      />
    </div>
  );
}
