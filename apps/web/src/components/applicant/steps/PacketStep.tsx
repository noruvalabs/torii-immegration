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
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { useAuth } from "@/lib/auth-context";
import type { Case } from "./types";

type PacketStepProps = {
  packet: Record<string, unknown> | null;
  caseData: Case;
  loading: boolean;
  onBuild: () => void;
  onSubmit: () => void;
};

function generateCoverLetter(caseData: Case, packet: Record<string, unknown> | null): string {
  const reference = String(packet?.reference ?? caseData.reference);
  const scope = caseData.scope_label ?? caseData.locale.toUpperCase();
  const dateStr = new Date().toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  const answers = caseData.intake_answers || {};
  const fullName = String(answers.full_name || answers.applicant_name || "Applicant");
  const passportNo = String(answers.passport_number || answers.passport_no || "See Attached Passport");
  const nationality = String(answers.nationality || "See Passport");
  const purpose = String(answers.main_purpose || answers.purpose_of_visit || "Tourism and cultural sightseeing");
  const stayDays = String(answers.stay_duration_days || answers.intended_length_of_stay_days || "15");
  const arrivalDate = String(answers.planned_arrival_date || "Upcoming scheduled date");

  const checklist = Array.isArray(packet?.checklist)
    ? (packet.checklist as { name?: string; status?: string; is_required?: boolean }[])
    : [];

  const documentListStr = checklist
    .filter((c) => c.status && c.status !== "needed")
    .map((c, i) => `   ${i + 1}. ${c.name || "Supporting Document"} (Verified & Attached)`)
    .join("\n") || "   1. Valid Original Passport & Bio-Data Photocopies\n   2. Official Visa Application Form (Signed)\n   3. Day-by-Day Schedule of Stay (Itinerary Table)\n   4. Bank Statements / Proof of Financial Solvency\n   5. Employment Certificate / Business Registration\n   6. Accommodation & Flight Reservations";

  return `DATE: ${dateStr}

TO:
The Visa Section / Consular Division
Embassy / Consulate General / VFS Application Center

SUBJECT: FORMAL VISA APPLICATION COVER LETTER & DOSSIER SUBMISSION
Applicant Name: ${fullName}
Passport Number: ${passportNo}
Nationality: ${nationality}
Application Reference: ${reference}
Visa Category / Scope: ${scope}

Dear Consular Officer,

I have the honor to submit my formal application for a Short-Term Visitor Visa for ${scope}. All required information, official forms, and verified supporting documents have been assembled in strict accordance with published consular guidelines.

1. PURPOSE OF VISIT & ITINERARY:
My primary purpose of travel is ${purpose}. I plan to arrive in the destination on ${arrivalDate} and intend to stay for a duration of ${stayDays} days. A detailed day-by-day Schedule of Stay (Itinerary) is attached for your reference.

2. FINANCIAL MEANS & EXPENSE COVERAGE:
I confirm that I possess sufficient personal funds and liquid financial reserves to fully support all expenses during my travel, including airfare, accommodation, dining, domestic transport, and incidental expenses. Official bank certificates and statements demonstrating steady income are enclosed.

3. TIES TO HOME COUNTRY & COMMITMENT TO RETURN:
I maintain strong personal, familial, and professional ties in my home country (${nationality}), including active employment/business commitments. I solemnly affirm that I will strictly abide by all immigration laws, will not engage in any unauthorized activities, and will depart the destination promptly upon completion of my visit.

4. ENCLOSED DOCUMENT INVENTORY:
The following documents are organized and enclosed in this submission dossier:
${documentListStr}

I certify that all statements and attached records are true, complete, and authentic. Thank you for your time and kind consideration of my visa application.

Respectfully yours,


________________________________________
${fullName}
Passport No: ${passportNo}
Date: ${dateStr}
`;
}

function generateScheduleOfStay(caseData: Case, packet: Record<string, unknown> | null): string {
  const answers = caseData.intake_answers || {};
  const fullName = String(answers.full_name || answers.applicant_name || "Applicant");
  const arrivalDate = String(answers.planned_arrival_date || "2026-09-01");
  const stayDays = parseInt(String(answers.stay_duration_days || answers.intended_length_of_stay_days || "15"), 10) || 15;
  const hotel = String(answers.accommodation_name || answers.accommodation_type || "Tokyo Central Hotel");
  const hotelAddress = String(answers.accommodation_address || "Chiyoda-ku, Tokyo, Japan / Tel: +81-3-0000-0000");

  let rows = "";
  const baseDate = new Date(arrivalDate);
  const validBase = isNaN(baseDate.getTime()) ? new Date() : baseDate;

  for (let day = 1; day <= Math.min(stayDays, 15); day++) {
    const currentDate = new Date(validBase);
    currentDate.setDate(validBase.getDate() + (day - 1));
    const dStr = currentDate.toISOString().split("T")[0];

    let activity = "";
    if (day === 1) {
      activity = "Arrival at Airport, immigration clearance, check-in at accommodation.";
    } else if (day === Math.min(stayDays, 15)) {
      activity = "Check-out from hotel, souvenir shopping, depart from airport back to home country.";
    } else if (day % 3 === 0) {
      activity = "Cultural sightseeing, visiting historical heritage sites and museums.";
    } else if (day % 3 === 1) {
      activity = "City exploration, shopping in central district, local culinary tour.";
    } else {
      activity = "Scenic day tour, visiting parks and scenic observatory.";
    }

    rows += `| Day ${day} (${dStr}) | ${activity.padEnd(45)} | ${hotel.padEnd(20)} | ${hotelAddress} |\n`;
  }

  return `================================================================================
OFFICIAL SCHEDULE OF STAY / DAY-BY-DAY ITINERARY (滞在予定表)
Applicant: ${fullName}
Planned Arrival: ${arrivalDate} | Duration: ${stayDays} Days
================================================================================

+-------------------+-----------------------------------------------+----------------------+----------------------------------------------+
| Date              | Activity Plan & Destination                   | Accommodation / Contact | Address & Contact Phone                      |
+-------------------+-----------------------------------------------+----------------------+----------------------------------------------+
${rows}+-------------------+-----------------------------------------------+----------------------+----------------------------------------------+

Notes:
- All accommodations and transport routes have been prepared in accordance with the planned schedule.
- The applicant will reside at the specified accommodation throughout the visit.

Applicant Signature: ______________________   Date: ${new Date().toISOString().split("T")[0]}
`;
}

function generateReasonForVisit(caseData: Case, packet: Record<string, unknown> | null): string {
  const answers = caseData.intake_answers || {};
  const fullName = String(answers.full_name || answers.applicant_name || "Applicant");
  const passportNo = String(answers.passport_number || answers.passport_no || "N/A");
  const nationality = String(answers.nationality || "N/A");
  const residence = String(answers.current_residence_country || answers.residence_country || nationality);
  const purpose = String(answers.main_purpose || answers.purpose_of_visit || "Tourism and sightseeing");
  const stayDays = String(answers.stay_duration_days || answers.intended_length_of_stay_days || "15");
  const occupation = String(answers.occupation || "Employed Professional");
  const employer = String(answers.employer_name || "Company / Business Organization");

  return `STATEMENT OF REASON FOR INVITATION / VISIT (理由書 - STATEMENT OF PURPOSE)

TO:
The Ministry of Foreign Affairs / Consular Division

1. APPLICANT INFORMATION:
- Name: ${fullName}
- Nationality: ${nationality}
- Country of Residence: ${residence}
- Passport Number: ${passportNo}
- Current Occupation: ${occupation} (${employer})

2. DETAILED BACKGROUND & REASON FOR VISIT:
I am submitting this statement to explain the genuine intent and circumstances of my upcoming visit. I have long held a profound interest in exploring the rich cultural heritage, historical landmarks, and world-renowned scenic attractions of the destination.

My scheduled stay is for ${stayDays} days, specifically dedicated to ${purpose}. During this period, I will follow a structured itinerary and stay at verified accommodations.

3. FINANCIAL CAPACITY & EXPENSE DISCLOSURE:
As demonstrated by the enclosed bank statements and proof of income from my occupation at ${employer}, I have accumulated sufficient personal liquid funds to comfortably support all aspects of my trip without recourse to public funds or unauthorized work.

4. GUARANTEE OF RETURN:
I have binding professional, social, and financial obligations in ${residence}, including my ongoing career and family commitments. I solemnly declare that I will strictly observe the laws and visa regulations, and I will depart the destination before the expiration of my permitted stay.

I respectfully request that my visa application be granted.


Signature: ______________________________
Full Name: ${fullName}
Date: ${new Date().toISOString().split("T")[0]}
`;
}

function generateFinancialGuarantee(caseData: Case, packet: Record<string, unknown> | null): string {
  const answers = caseData.intake_answers || {};
  const fullName = String(answers.full_name || answers.applicant_name || "Applicant");
  const passportNo = String(answers.passport_number || answers.passport_no || "N/A");
  const payer = String(answers.trip_payer || "Self");
  const salary = answers.monthly_salary ? `Monthly Salary: ${String(answers.monthly_salary)}` : "Verified regular income";
  const employer = String(answers.employer_name || answers.occupation || "Self-Employed / Business / Company");

  return `FINANCIAL GUARANTEE & EXPLANATION OF EXPENSES (身元保証書 / 経費支弁書)

TO:
The Consular Officer / Visa Section

I, ${fullName}, holder of Passport No. ${passportNo}, hereby declare the following regarding the financial coverage and guarantee for my travel:

1. FUNDING SOURCE:
- Trip Payer: ${payer.toUpperCase()}
- Professional Affiliation / Source of Funds: ${employer}
- Income Verification: ${salary}

2. EXPENSES UNDERTAKEN:
I hereby certify that all costs and expenses incurred during this trip—including roundtrip international airfare, domestic transportation within the destination, hotel accommodations, meals, travel medical insurance, and unforeseen emergencies—are fully provided for and guaranteed.

3. ENCLOSED FINANCIAL PROOF:
- Official Bank Statement / Bank Balance Certificate (Last 3–6 Months)
- Income Tax Returns (ITR) / Salary Certificates
- Confirmed Flight & Accommodation Reservations

I guarantee that the applicant will not become a public burden in any manner and will comply with all immigration requirements.


Guarantor / Applicant Signature: ______________________________
Name: ${fullName}
Date: ${new Date().toISOString().split("T")[0]}
`;
}

function generateCompleteOfficialForm(caseData: Case, packet: Record<string, unknown> | null): string {
  const answers = caseData.intake_answers || {};
  let fieldsStr = "";
  for (const [k, v] of Object.entries(answers)) {
    if (v !== null && v !== "") {
      fieldsStr += `  • ${k.replace(/_/g, " ").toUpperCase().padEnd(36)} : ${String(v)}\n`;
    }
  }

  return `================================================================================
OFFICIAL VISA APPLICATION FORM — PRE-FILLED FIELD DATA SHEET
(Use this verified field guide to fill or verify the official embassy PDF / portal)
================================================================================

APPLICANT PROFILE DATA:
${fieldsStr || "  • No intake answers recorded."}

DECLARATION & SIGNATURE SECTION:
I hereby declare that the statement given above is true and correct. I understand that visa issuance is at the discretion of the embassy and that any false statement may result in visa denial or immediate deportation.

Applicant Signature: ______________________________
Date: ${new Date().toISOString().split("T")[0]}
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
  const [activeDoc, setActiveDoc] = useState<DocType>("cover");
  const [copiedDoc, setCopiedDoc] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState<string | null>(null);
  const [trackedSteps, setTrackedSteps] = useState({
    filledOnline: false,
    paidFee: false,
    bookedAppointment: false,
    submittedDossier: caseData.status === "submitted",
  });

  async function downloadPdf(
    endpoint: "application-form" | "cover-letter" | "dossier-packet",
    defaultFilename: string
  ) {
    const activeToken = token || (typeof window !== "undefined" ? localStorage.getItem("torii_token") : null);
    if (!activeToken) return;
    setDownloadingPdf(endpoint);
    try {
      const res = await fetch(`/backend/v1/cases/${caseData.id}/pdf/${endpoint}`, {
        headers: { Authorization: `Bearer ${activeToken}` },
      });
      if (!res.ok) {
        const errDetail = await res.text();
        console.error("PDF download failed:", res.status, errDetail);
        alert(`Failed to download PDF (${res.status}): ${errDetail || res.statusText}`);
        return;
      }
      const buffer = await res.arrayBuffer();
      const blob = new Blob([buffer], { type: "application/pdf" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = defaultFilename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("PDF download error:", err);
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
          full: "📦 Complete Japan Work Kit",
        };
      }
      if (isStudent) {
        return {
          cover: "📄 Consular / School Cover Letter",
          schedule: "🎓 Study & Academic Plan (就学計画書)",
          reason: "✍️ Statement of Study Intent (就学理由書)",
          financial: "💰 Sponsor Guarantee (経費支弁書)",
          form: "📋 Student Form Data Sheet",
          full: "📦 Complete Japan Student Kit",
        };
      }
      return {
        cover: "📄 Embassy Cover Letter",
        schedule: "🗓️ Schedule of Stay (滞在予定表)",
        reason: "✍️ Reason for Visit (理由書)",
        financial: "💰 Financial Guarantee (身元保証書)",
        form: "📋 Full Form Data Sheet",
        full: "📦 Complete Dossier Kit",
      };
    }

    if (isUSA) {
      if (isWork) {
        return {
          cover: "📄 USCIS / Consular Cover Letter",
          schedule: "💼 LCA & Job Position Specification",
          reason: "✍️ Form I-129 Employer Petition Letter",
          financial: "💰 Prevailing Wage & Salary Proof",
          form: "📋 DS-160 & I-129 Data Sheet",
          full: "📦 Complete U.S. Work Visa Kit",
        };
      }
      if (isStudent) {
        return {
          cover: "📄 U.S. Embassy Consular Cover Letter",
          schedule: "🎓 SEVIS Academic Study Plan",
          reason: "✍️ Statement of Intent & Nonimmigrant Ties",
          financial: "💰 Sponsor Affidavit of Support (Form I-134)",
          form: "📋 Form DS-160 & I-901 SEVIS Guide",
          full: "📦 Complete U.S. Student Kit",
        };
      }
      return {
        cover: "📄 U.S. Consular Cover Letter",
        schedule: "🗓️ Day-by-Day Travel Itinerary",
        reason: "✍️ Statement of Purpose (B-1/B-2)",
        financial: "💰 Affidavit of Support (Form I-134)",
        form: "📋 Form DS-160 Data Guide",
        full: "📦 Complete U.S. Submission Kit",
      };
    }

    if (isUK) {
      return {
        cover: "📄 UKVI / High Commission Cover Letter",
        schedule: isWork ? "💼 UK Job Specification & CoS" : isStudent ? "🎓 CAS Study & Course Plan" : "🗓️ UK Travel Itinerary & Lodging",
        reason: "✍️ Statement of Purpose & Genuine Ties",
        financial: "💰 Proof of Financial Solvency & Maintenance",
        form: "📋 GOV.UK Visa Field Guide",
        full: "📦 Complete UK Submission Kit",
      };
    }

    if (isSchengen) {
      return {
        cover: "📄 Schengen Consular Cover Letter",
        schedule: "🗓️ Schengen Travel Itinerary & Bookings",
        reason: "✍️ Statement of Purpose & Travel Intent",
        financial: "💰 Proof of Means & Travel Insurance",
        form: "📋 Harmonised Schengen Form Data",
        full: "📦 Complete Schengen Dossier",
      };
    }

    return {
      cover: "📄 Visa Submission Cover Letter",
      schedule: isWork ? "💼 Job Position & Duties Overview" : isStudent ? "🎓 Study Plan & Curriculum Overview" : "🗓️ Travel Itinerary & Accommodation",
      reason: "✍️ Statement of Purpose",
      financial: "💰 Financial Guarantee & Solvency Proof",
      form: "📋 Application Form Data Guide",
      full: "📦 Complete Filing Dossier",
    };
  }

  const docLabels = getDocLabels();

  function getActiveDocText(): { title: string; filename: string; text: string } {
    switch (activeDoc) {
      case "schedule":
        return {
          title: docLabels.schedule.replace(/^[^\w]+/, ""),
          filename: `${caseData.reference}-schedule-of-stay.txt`,
          text: generateScheduleOfStay(caseData, packet),
        };
      case "reason":
        return {
          title: docLabels.reason.replace(/^[^\w]+/, ""),
          filename: `${caseData.reference}-reason-for-visit.txt`,
          text: generateReasonForVisit(caseData, packet),
        };
      case "financial":
        return {
          title: docLabels.financial.replace(/^[^\w]+/, ""),
          filename: `${caseData.reference}-financial-guarantee.txt`,
          text: generateFinancialGuarantee(caseData, packet),
        };
      case "form":
        return {
          title: docLabels.form.replace(/^[^\w]+/, ""),
          filename: `${caseData.reference}-official-form-data.txt`,
          text: generateCompleteOfficialForm(caseData, packet),
        };
      case "full":
        return {
          title: docLabels.full.replace(/^[^\w]+/, ""),
          filename: `${caseData.reference}-complete-filing-kit.txt`,
          text: generateCompleteFilingKitText(packet || {}, caseData),
        };
      case "cover":
      default:
        return {
          title: docLabels.cover.replace(/^[^\w]+/, ""),
          filename: `${caseData.reference}-embassy-cover-letter.txt`,
          text: generateCoverLetter(caseData, packet),
        };
    }
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
    link.remove();
    URL.revokeObjectURL(url);
  }

  function downloadFullFilingKit() {
    if (!packet) return;
    const filename = `${caseData.reference}-complete-filing-kit.txt`;
    const blob = new Blob([generateCompleteFilingKitText(packet, caseData)], {
      type: "text/plain;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
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

      {!packet ? (
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
                    🎉 Torii has auto-filled your official forms, verified your document checklist, and prepared your official PDF package.
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
                  <Button variant="outline" onClick={handleCopyActiveDoc} className="px-2.5 py-1 text-xs">
                    {copiedDoc ? (
                      <>
                        <Check className="mr-1.5 size-3.5 text-[var(--color-success)]" /> Copied!
                      </>
                    ) : (
                      <>
                        <Copy className="mr-1.5 size-3.5" /> Copy Document
                      </>
                    )}
                  </Button>
                  <Button variant="outline" onClick={handleDownloadActiveDoc} className="px-2.5 py-1 text-xs">
                    <Download className="mr-1.5 size-3.5" /> Download (.txt)
                  </Button>
                </div>
              </div>

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
                  </button>
                ))}
              </div>

              {/* Active Document Header & Preview */}
              <div className="flex items-center justify-between pt-1">
                <span className="text-xs font-semibold text-foreground">
                  {getActiveDocText().title}
                </span>
                <span className="text-[10px] text-muted-foreground font-mono">
                  {getActiveDocText().filename}
                </span>
              </div>

              <div className="rounded-md border bg-muted/40 p-4 font-mono text-xs text-foreground/90 whitespace-pre-wrap leading-relaxed max-h-96 overflow-y-auto shadow-inner">
                {getActiveDocText().text}
              </div>
            </CardContent>
          </Card>

          {/* Feature 2: Official Step-by-Step Submission Roadmap */}
          <div className="space-y-3">
            <h4 className="text-sm font-bold tracking-tight flex items-center gap-2">
              <ArrowRight className="size-4 text-primary" /> Step-by-Step Submission Roadmap
            </h4>
            <div className="grid gap-3 sm:grid-cols-2">
              {Array.isArray(packet.submission_steps) && packet.submission_steps.length > 0 ? (
                (packet.submission_steps as { step?: number; title?: string; description?: string }[]).map((st, i) => (
                  <div key={i} className="rounded-[var(--radius)] border bg-card p-4 space-y-1">
                    <div className="flex items-center justify-between">
                      <Badge tone="default">Step {st.step ?? i + 1}</Badge>
                      <span className="text-[10px] text-primary font-semibold">Official Requirement</span>
                    </div>
                    <p className="text-xs font-semibold text-foreground pt-1">{st.title}</p>
                    <p className="text-[11px] text-muted-foreground">{st.description}</p>
                  </div>
                ))
              ) : (
                <>
                  <div className="rounded-[var(--radius)] border bg-card p-4 space-y-1">
                    <div className="flex items-center justify-between">
                      <Badge tone="default">Step 1</Badge>
                      <span className="text-[10px] text-primary font-semibold">Online Portal</span>
                    </div>
                    <p className="text-xs font-semibold text-foreground pt-1">Fill Official Government Form</p>
                    <p className="text-[11px] text-muted-foreground">
                      Use Torii&apos;s copyable field guide from the Forms tab to fill out the embassy web portal.
                    </p>
                  </div>
                  <div className="rounded-[var(--radius)] border bg-card p-4 space-y-1">
                    <div className="flex items-center justify-between">
                      <Badge tone="default">Step 2</Badge>
                      <span className="text-[10px] text-primary font-semibold">Filing Fee</span>
                    </div>
                    <p className="text-xs font-semibold text-foreground pt-1">Pay Official Visa Fee</p>
                    <p className="text-[11px] text-muted-foreground">
                      Pay required fee through the government payment gateway and save receipt.
                    </p>
                  </div>
                  <div className="rounded-[var(--radius)] border bg-card p-4 space-y-1">
                    <div className="flex items-center justify-between">
                      <Badge tone="default">Step 3</Badge>
                      <span className="text-[10px] text-primary font-semibold">Appointment</span>
                    </div>
                    <p className="text-xs font-semibold text-foreground pt-1">Book Biometrics &amp; Interview</p>
                    <p className="text-[11px] text-muted-foreground">
                      Schedule appointment date at the nearest Visa Application Center or Embassy.
                    </p>
                  </div>
                  <div className="rounded-[var(--radius)] border bg-card p-4 space-y-1">
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
              {Array.isArray(packet.dossier_order) && packet.dossier_order.length > 0 ? (
                <ol className="space-y-1.5 text-xs text-foreground">
                  {(packet.dossier_order as string[]).map((item, idx) => (
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
