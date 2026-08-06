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

  const checklist = Array.isArray(packet?.checklist)
    ? (packet.checklist as { name?: string; status?: string; is_required?: boolean }[])
    : [];

  const documentListStr = checklist
    .filter((c) => c.status && c.status !== "needed")
    .map((c, i) => `   ${i + 1}. ${c.name || "Supporting Document"} (Verified & Attached)`)
    .join("\n") || "   1. Valid Original Passport & Photocopies\n   2. Proof of Sufficient Financial Means\n   3. Travel & Accommodation Itinerary";

  return `DATE: ${dateStr}

TO:
The Consular Officer / Visa Issuing Authority
Embassy / Consulate General

SUBJECT: APPLICATION FOR VISA — COVER LETTER
Reference ID: ${reference}
Scope: ${scope}

Dear Consular Officer,

I am writing to formally submit my visa application for ${scope}. All required information and supporting documents have been assembled and verified for your review.

APPLICANT DETAILS:
- Full Name: ${fullName}
- Passport Number: ${passportNo}
- Nationality: ${nationality}
- Application Reference: ${reference}

PURPOSE OF VISIT & INTENT:
I am traveling strictly for the purpose outlined in my application intake (${scope}). I affirm that I possess adequate financial resources to cover all expenses incurred during my stay, including transportation, accommodation, and personal sustenance. I intend to return promptly to my home country prior to the expiration of my authorized stay.

ATTACHED DOSSIER INVENTORY:
The following verified documents are enclosed in this application filing package:
${documentListStr}

STATEMENT OF TRUTH:
I confirm that all information provided in this application package and filled in the accompanying official forms is complete, accurate, and true to the best of my knowledge.

Thank you for your time and consideration of my visa application.

Sincerely,

${fullName}
Signature: ______________________
Date: ${dateStr}
`;
}

function generateCompleteFilingKitText(source: Record<string, unknown>, caseData: Case): string {
  const forms = Array.isArray(source.forms)
    ? (source.forms as { form_code?: string; form_version?: string; filled_fields?: Record<string, unknown> }[])
    : [];
  const checklist = Array.isArray(source.checklist)
    ? (source.checklist as { name?: string; status?: string; is_required?: boolean; how_to_obtain?: string }[])
    : [];

  const coverLetter = generateCoverLetter(caseData, source);

  const formsFormatted = forms.length === 0
    ? "No generated form field mappings listed."
    : forms
        .map((f) => {
          const fieldEntries = f.filled_fields
            ? Object.entries(f.filled_fields)
                .map(([k, v]) => `    • ${k.replace(/_/g, " ")}: ${String(v)}`)
                .join("\n")
            : "    • (No filled fields recorded)";
          return `Form: ${f.form_code || "Form"} (v${f.form_version || "1.0"})\n${fieldEntries}`;
        })
        .join("\n\n");

  const checklistFormatted = checklist
    .map((item) => `• ${item.name || "Document"}: ${item.status || "needed"} ${item.is_required ? "(Required)" : "(Optional)"}`)
    .join("\n");

  return `================================================================================
TORII IMMIGRATION — COMPLETE OFFICIAL VISA FILING KIT
Reference: ${source.reference ?? caseData.reference}
Scope: ${caseData.scope_label ?? caseData.locale.toUpperCase()}
Generated: ${new Date().toISOString()}
================================================================================

--------------------------------------------------------------------------------
SECTION 1: OFFICIAL EMBASSY COVER LETTER
--------------------------------------------------------------------------------
${coverLetter}

--------------------------------------------------------------------------------
SECTION 2: AUTO-FILLED FORM FIELD GUIDE
(Copy these exact values into the official government portal)
--------------------------------------------------------------------------------
${formsFormatted}

--------------------------------------------------------------------------------
SECTION 3: VERIFIED DOCUMENT CHECKLIST & STATUS
--------------------------------------------------------------------------------
${checklistFormatted}

--------------------------------------------------------------------------------
SECTION 4: PHYSICAL DOSSIER ASSEMBLY STACK ORDER
(Arrange physical documents in this exact order before your interview/submission)
--------------------------------------------------------------------------------
1. Official Embassy Cover Letter (Signed)
2. Official Online Application Confirmation / Form Summary
3. Original Valid Passport & Clear Photocopies
4. Official Passport-Sized Photographs (Meeting Jurisdiction Specs)
5. Proof of Financial Guarantee (Bank Statements / Sponsorship)
6. Travel & Accommodation Itinerary (Flight & Hotel Reservations)
7. Employment Verification Letter / Business Registration Docs

--------------------------------------------------------------------------------
SECTION 5: OFFICIAL EMBASSY SUBMISSION ROADMAP
--------------------------------------------------------------------------------
Step 1: Copy your auto-filled form answers into the government submission portal.
Step 2: Pay the required embassy/consulate filing fee and print payment receipt.
Step 3: Book your biometrics & visa interview appointment at the embassy/VAC portal.
Step 4: Attend your scheduled appointment with your ordered physical dossier.

================================================================================
End of Filing Kit · Torii Immigration Platform
================================================================================
`;
}

export function PacketStep({ packet, caseData, loading, onBuild, onSubmit }: PacketStepProps) {
  const [copiedLetter, setCopiedLetter] = useState(false);
  const [trackedSteps, setTrackedSteps] = useState({
    filledOnline: false,
    paidFee: false,
    bookedAppointment: false,
    submittedDossier: caseData.status === "submitted",
  });

  function copyCoverLetter() {
    const text = generateCoverLetter(caseData, packet);
    void navigator.clipboard.writeText(text);
    setCopiedLetter(true);
    setTimeout(() => setCopiedLetter(false), 2500);
  }

  function downloadCoverLetter() {
    const text = generateCoverLetter(caseData, packet);
    const filename = `${caseData.reference}-embassy-cover-letter.txt`;
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
            Everything assembled for your application — Cover Letter, Form Guide, Submission Roadmap, and Filing Kit.
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
                Generate your personalized Embassy Cover Letter, Step-by-Step Filing Instructions, and Complete Download Package.
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
            <CardContent className="p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
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
                    🎉 Torii has auto-filled your forms, verified your document checklist, and drafted your Embassy Cover Letter.
                  </p>
                </div>
              </div>

              <Button onClick={downloadFullFilingKit} className="shrink-0 px-3 py-1.5 text-xs">
                <Download className="mr-2 size-4" /> Download Complete Kit (.txt)
              </Button>
            </CardContent>
          </Card>

          {/* Feature 1: Embassy Cover Letter Generator */}
          <Card className="border-primary/20">
            <CardContent className="p-5 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b pb-3">
                <div className="flex items-center gap-2">
                  <FileText className="size-5 text-primary" />
                  <div>
                    <h4 className="text-sm font-bold tracking-tight">Official Embassy Cover Letter</h4>
                    <p className="text-[11px] text-muted-foreground">
                      Custom-crafted formal statement to the Consular Officer explaining travel scope &amp; document inventory.
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="outline" onClick={copyCoverLetter} className="px-2.5 py-1 text-xs">
                    {copiedLetter ? (
                      <>
                        <Check className="mr-1.5 size-3.5 text-[var(--color-success)]" /> Copied!
                      </>
                    ) : (
                      <>
                        <Copy className="mr-1.5 size-3.5" /> Copy Letter
                      </>
                    )}
                  </Button>
                  <Button variant="outline" onClick={downloadCoverLetter} className="px-2.5 py-1 text-xs">
                    <Download className="mr-1.5 size-3.5" /> Save Letter
                  </Button>
                </div>
              </div>

              <div className="rounded-md border bg-muted/40 p-4 font-mono text-xs text-foreground/90 whitespace-pre-wrap leading-relaxed max-h-72 overflow-y-auto">
                {generateCoverLetter(caseData, packet)}
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
