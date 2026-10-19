"use client";

import { useEffect, useState, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Copy,
  Check,
  ExternalLink,
  FileText,
  User,
  Globe,
  Calendar,
  CreditCard,
  ShieldCheck,
  CheckCircle2,
  Clock,
  Sparkles,
  Send,
  Save,
  Phone,
  Mail,
  MapPin,
  Building,
  FileCheck,
  Download,
  AlertCircle,
  HelpCircle,
  Loader2,
  Eye,
  X,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { useAuth } from "@/lib/auth-context";
import {
  getCase,
  patchCase,
  getCaseDocumentFileUrl,
  getChecklistItemFileUrl,
  type Case,
} from "@/lib/api/cases";
import { getCasePayment, type Payment } from "@/lib/api/payments";
import { useCaseQuery, useChecklistQuery, useDocumentsQuery } from "@/lib/queries/cases";
import { useQueryClient } from "@tanstack/react-query";
import { formatScopeLabel } from "@/lib/utils";

/**
 * Official government filing portal mapping by destination code.
 */
const GOVERNMENT_PORTALS: Record<
  string,
  { name: string; url: string; portalNotes: string }
> = {
  IN: {
    name: "Indian Visa Online (IVAC Portal)",
    url: "https://indianvisaonline.gov.in/",
    portalNotes: "Official portal for Regular / Paper Visa application & IVAC appointment booking in Bangladesh.",
  },
  SA: {
    name: "Visit Saudi Visa Portal (KSA MOFA)",
    url: "https://visa.visitsaudi.com/",
    portalNotes: "Official portal for Saudi Tourist eVisa and Umrah permits.",
  },
  JP: {
    name: "JAPAN eVISA Official Portal (MOFA)",
    url: "https://www.evisa.mofa.go.jp/",
    portalNotes: "Ministry of Foreign Affairs of Japan official electronic visa filing system.",
  },
  AE: {
    name: "ICP Smart Services (UAE Immigration)",
    url: "https://smartservices.icp.gov.ae/",
    portalNotes: "Federal Authority for Identity, Citizenship, Customs and Port Security.",
  },
  MY: {
    name: "Malaysia eVisa Official Portal",
    url: "https://malaysiavisa.imi.gov.my/",
    portalNotes: "Immigration Department of Malaysia official eVisa submission system.",
  },
  VN: {
    name: "Vietnam National Web Portal on Immigration",
    url: "https://evisa.xuatnhapcanh.gov.vn/",
    portalNotes: "Immigration Department of Vietnam official electronic visa system.",
  },
  EG: {
    name: "Egypt e-Visa Portal",
    url: "https://visa2egypt.gov.eg/",
    portalNotes: "Arab Republic of Egypt Ministry of Interior official e-Visa portal.",
  },
};

export default function AdminCaseFilingPage() {
  const params = useParams();
  const caseId = Number(params.id);
  const router = useRouter();
  const { token, user } = useAuth();
  const queryClient = useQueryClient();

  const { data: caseData, isLoading, refetch } = useCaseQuery(token, caseId);
  const { data: checklist = [] } = useChecklistQuery(token, caseId);
  const { data: documents = [] } = useDocumentsQuery(token, caseId);

  // Staff filing fields
  const [submissionRef, setSubmissionRef] = useState("");
  const [caseStatus, setCaseStatus] = useState("payment_completed");
  const [staffNotes, setStaffNotes] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [payment, setPayment] = useState<Payment | null>(null);

  // Document Preview Modal State
  const [previewDoc, setPreviewDoc] = useState<{
    id: number | null;
    checklistItemId?: number;
    name: string;
    filename: string;
    url: string;
    extractedFields?: Record<string, unknown>;
    confidence?: number | null;
  } | null>(null);

  useEffect(() => {
    if (caseData) {
      setSubmissionRef(caseData.submission_reference || "");
      setCaseStatus(caseData.status || "payment_completed");
      setStaffNotes(caseData.notes || "");
    }
  }, [caseData]);

  useEffect(() => {
    if (caseId) {
      getCasePayment(caseId)
        .then(setPayment)
        .catch(() => setPayment(null));
    }
  }, [caseId]);

  // Copy helper with visual feedback
  const copyToClipboard = (text: string, key: string) => {
    if (!text || text === "—") return;
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    toast.success(`Copied: ${text}`, { duration: 1500 });
    setTimeout(() => {
      setCopiedKey((curr) => (curr === key ? null : curr));
    }, 2000);
  };

  // Helper to extract intake answers
  const answers = useCaseDataAnswers(caseData);

  const portalInfo = useMemo(() => {
    const code = caseData?.jurisdiction_code?.toUpperCase() || "";
    return (
      GOVERNMENT_PORTALS[code] || {
        name: "Official Government Visa Portal",
        url: "https://google.com",
        portalNotes: "Official destination visa and immigration authority portal.",
      }
    );
  }, [caseData?.jurisdiction_code]);

  // Handle saving staff submission updates
  const handleSaveStaffFiling = async () => {
    if (!token) return;
    setIsSaving(true);
    try {
      await patchCase(token, caseId, {
        submission_reference: submissionRef.trim() || null,
        notes: staffNotes.trim() || undefined,
      });

      // Also trigger query invalidation
      await queryClient.invalidateQueries({ queryKey: ["cases"] });
      await refetch();
      toast.success("Case updated successfully!");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update case");
    } finally {
      setIsSaving(false);
    }
  };

  // Copy All Information as formatted plain text for staff
  const handleCopyAllText = () => {
    if (!caseData) return;
    const lines = [
      `======================================================`,
      `TORII IMMIGRATION - GOVERNMENT VISA FILING DOSSIER`,
      `Case Reference: ${caseData.reference}`,
      `Destination: ${caseData.jurisdiction_code} | Visa Category: ${caseData.visa_category_code}`,
      `Applicant Email: ${caseData.applicant_email || "N/A"}`,
      `======================================================\n`,
      `[1. PASSPORT & TRAVEL DOCUMENT]`,
      `Passport Number: ${answers.passportNumber}`,
      `Passport Type: ${answers.passportType}`,
      `Country of Issue: ${answers.passportIssueCountry}`,
      `Date of Issue: ${answers.passportIssueDate}`,
      `Date of Expiry: ${answers.passportExpiryDate}`,
      `Place of Issue: ${answers.passportIssuePlace}`,
      `National ID (NID): ${answers.nidNumber}\n`,
      `[2. PERSONAL PARTICULARS]`,
      `Given / First Name: ${answers.givenName}`,
      `Surname / Last Name: ${answers.surname}`,
      `Full Name: ${answers.fullName}`,
      `Date of Birth: ${answers.dob}`,
      `Gender: ${answers.gender}`,
      `Place of Birth (Town/City): ${answers.pobCity}`,
      `Country of Birth: ${answers.pobCountry}`,
      `Citizenship / Nationality: ${answers.citizenship}`,
      `Religion: ${answers.religion}`,
      `Marital Status: ${answers.maritalStatus}`,
      `Occupation / Profession: ${answers.occupation}\n`,
      `[3. FAMILY DETAILS]`,
      `Father's Full Name: ${answers.fatherName}`,
      `Father's Nationality: ${answers.fatherNationality}`,
      `Mother's Full Name: ${answers.motherName}`,
      `Mother's Nationality: ${answers.motherNationality}`,
      `Spouse's Full Name: ${answers.spouseName}\n`,
      `[4. ADDRESS & CONTACT]`,
      `Residential Address in BD: ${answers.presentAddress}`,
      `City / District: ${answers.district}`,
      `Postal Code: ${answers.postalCode}`,
      `Mobile Phone: ${answers.phone}`,
      `Email: ${caseData.applicant_email || answers.email}\n`,
      `[5. DESTINATION & TRAVEL DETAILS]`,
      `Port of Entry / Checkpost: ${answers.portOfEntry}`,
      `Expected Travel Date: ${answers.travelDate}`,
      `Reference / Hospital / Hotel in Destination: ${answers.destinationContactName}`,
      `Address in Destination: ${answers.destinationAddress}`,
      `Phone in Destination: ${answers.destinationPhone}`,
    ];

    if (answers.treatmentCategory !== "—") {
      lines.push(`Medical / Treatment Category: ${answers.treatmentCategory.replace(/_/g, " ")}`);
    }
    if (answers.attendantsCount !== "—") {
      lines.push(`Accompanying Attendants: ${answers.attendantsCount}`);
    }
    if (answers.residenceCountry !== "—") {
      lines.push(`Country of Residence: ${answers.residenceCountry}`);
    }

    const intakeEntries = Object.entries(caseData.intake_answers || {}).filter(
      ([k, v]) => !k.startsWith("_") && v !== null && v !== undefined && String(v).trim() !== ""
    );
    if (intakeEntries.length > 0) {
      lines.push(`\n[6. INTAKE QUESTIONNAIRE RESPONSES]`);
      for (const [k, v] of intakeEntries) {
        const label = k.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
        const display = typeof v === "boolean" ? (v ? "Yes" : "No") : Array.isArray(v) ? v.join(", ") : String(v);
        lines.push(`${label}: ${display}`);
      }
    }

    navigator.clipboard.writeText(lines.join("\n"));
    toast.success("Copied all applicant dossier information to clipboard!");
  };

  if (isLoading || !caseData) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <Loader2 className="size-7 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="w-full max-w-7xl mx-auto space-y-6 pb-16">
      {/* Navigation Breadcrumb */}
      <div className="flex items-center justify-between">
        <Link
          href="/admin/cases"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="size-3.5" /> Back to All Cases
        </Link>
        <div className="flex items-center gap-2">
          <Badge tone="default" className="text-[11px] px-2.5 py-0.5 font-mono">
            Staff Government Portal Assistant
          </Badge>
          <Link
            href={`/cases/${caseId}`}
            target="_blank"
            className="inline-flex items-center gap-1 text-xs text-primary font-medium hover:underline"
          >
            Applicant View <ExternalLink className="size-3" />
          </Link>
        </div>
      </div>

      {/* Main Header Card */}
      <div className="rounded-2xl border border-border bg-card p-6 shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="space-y-1.5">
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground font-mono">
              {caseData.reference}
            </h1>
            <Badge tone="success" className="text-xs capitalize font-semibold">
              {caseData.status.replace(/_/g, " ")}
            </Badge>
          </div>
          <p className="text-xs sm:text-sm text-muted-foreground">
            {formatScopeLabel(caseData.scope_label || `${caseData.jurisdiction_code} · ${caseData.visa_category_code}`)}
            {" · "}
            Applicant: <span className="font-medium text-foreground">{caseData.applicant_email || "Registered Applicant"}</span>
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleCopyAllText}
            className="text-xs gap-1.5 border-primary/20 bg-primary/5 text-primary hover:bg-primary/10"
          >
            <Copy className="size-3.5" /> Copy All Formatted Data
          </Button>
          <a
            href={portalInfo.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-xs font-bold text-primary-foreground shadow-xs hover:bg-primary/90 transition-colors"
          >
            <span>Open {portalInfo.name}</span>
            <ExternalLink className="size-3.5" />
          </a>
        </div>
      </div>

      {/* Government Portal Guidance Banner */}
      <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs">
        <div className="flex items-start gap-2.5">
          <Sparkles className="size-4 text-blue-500 shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <p className="font-bold text-foreground">
              Official Filing Destination: {portalInfo.name}
            </p>
            <p className="text-muted-foreground">
              {portalInfo.portalNotes} Open the portal and use the <strong>[Copy]</strong> buttons below to fill each government field directly.
            </p>
          </div>
        </div>
        <a
          href={portalInfo.url}
          target="_blank"
          rel="noopener noreferrer"
          className="shrink-0 text-blue-600 dark:text-blue-400 font-bold hover:underline inline-flex items-center gap-1"
        >
          Launch Portal <ExternalLink className="size-3" />
        </a>
      </div>

      {/* Two-Column Layout: Left = Structured Information, Right = Staff Filing Controls */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (2 Cols): Formatted Applicant Data */}
        <div className="lg:col-span-2 space-y-6">
          {/* Section 1: Passport & Travel Document */}
          <SectionCard
            title="1. Passport & Travel Document"
            description="Details required on the primary travel document page of government portals."
          >
            <FieldGrid>
              <CopyField
                label="Passport Number"
                value={answers.passportNumber}
                fieldKey="passportNumber"
                copiedKey={copiedKey}
                onCopy={copyToClipboard}
                isPrimary
              />
              <CopyField
                label="Passport Type"
                value={answers.passportType}
                fieldKey="passportType"
                copiedKey={copiedKey}
                onCopy={copyToClipboard}
              />
              <CopyField
                label="Country of Issue"
                value={answers.passportIssueCountry}
                fieldKey="passportIssueCountry"
                copiedKey={copiedKey}
                onCopy={copyToClipboard}
              />
              <CopyField
                label="Date of Expiry"
                value={answers.passportExpiryDate}
                fieldKey="passportExpiryDate"
                copiedKey={copiedKey}
                onCopy={copyToClipboard}
                isPrimary
              />
              <CopyField
                label="Date of Issue"
                value={answers.passportIssueDate}
                fieldKey="passportIssueDate"
                copiedKey={copiedKey}
                onCopy={copyToClipboard}
              />
              <CopyField
                label="Place of Issue"
                value={answers.passportIssuePlace}
                fieldKey="passportIssuePlace"
                copiedKey={copiedKey}
                onCopy={copyToClipboard}
              />
              <CopyField
                label="National ID (NID)"
                value={answers.nidNumber}
                fieldKey="nidNumber"
                copiedKey={copiedKey}
                onCopy={copyToClipboard}
              />
            </FieldGrid>
          </SectionCard>

          {/* Section 2: Personal Particulars */}
          <SectionCard
            title="2. Applicant Personal Particulars"
            description="Name, birth details, citizenship, and occupational background."
          >
            <FieldGrid>
              <CopyField
                label="Given / First Name"
                value={answers.givenName}
                fieldKey="givenName"
                copiedKey={copiedKey}
                onCopy={copyToClipboard}
                isPrimary
              />
              <CopyField
                label="Surname / Last Name"
                value={answers.surname}
                fieldKey="surname"
                copiedKey={copiedKey}
                onCopy={copyToClipboard}
                isPrimary
              />
              <CopyField
                label="Full Name (as in Passport)"
                value={answers.fullName}
                fieldKey="fullName"
                copiedKey={copiedKey}
                onCopy={copyToClipboard}
              />
              <CopyField
                label="Date of Birth"
                value={answers.dob}
                fieldKey="dob"
                copiedKey={copiedKey}
                onCopy={copyToClipboard}
                isPrimary
              />
              <CopyField
                label="Gender"
                value={answers.gender}
                fieldKey="gender"
                copiedKey={copiedKey}
                onCopy={copyToClipboard}
              />
              <CopyField
                label="Place of Birth (Town/City)"
                value={answers.pobCity}
                fieldKey="pobCity"
                copiedKey={copiedKey}
                onCopy={copyToClipboard}
              />
              <CopyField
                label="Country of Birth"
                value={answers.pobCountry}
                fieldKey="pobCountry"
                copiedKey={copiedKey}
                onCopy={copyToClipboard}
              />
              <CopyField
                label="Citizenship / Nationality"
                value={answers.citizenship}
                fieldKey="citizenship"
                copiedKey={copiedKey}
                onCopy={copyToClipboard}
              />
              <CopyField
                label="Religion"
                value={answers.religion}
                fieldKey="religion"
                copiedKey={copiedKey}
                onCopy={copyToClipboard}
              />
              <CopyField
                label="Marital Status"
                value={answers.maritalStatus}
                fieldKey="maritalStatus"
                copiedKey={copiedKey}
                onCopy={copyToClipboard}
              />
              <CopyField
                label="Occupation / Profession"
                value={answers.occupation}
                fieldKey="occupation"
                copiedKey={copiedKey}
                onCopy={copyToClipboard}
              />
            </FieldGrid>
          </SectionCard>

          {/* Section 3: Family Details */}
          <SectionCard
            title="3. Family Details"
            description="Parents and spouse information required on standard visa forms."
          >
            <FieldGrid>
              <CopyField
                label="Father's Full Name"
                value={answers.fatherName}
                fieldKey="fatherName"
                copiedKey={copiedKey}
                onCopy={copyToClipboard}
              />
              <CopyField
                label="Father's Nationality"
                value={answers.fatherNationality}
                fieldKey="fatherNationality"
                copiedKey={copiedKey}
                onCopy={copyToClipboard}
              />
              <CopyField
                label="Mother's Full Name"
                value={answers.motherName}
                fieldKey="motherName"
                copiedKey={copiedKey}
                onCopy={copyToClipboard}
              />
              <CopyField
                label="Mother's Nationality"
                value={answers.motherNationality}
                fieldKey="motherNationality"
                copiedKey={copiedKey}
                onCopy={copyToClipboard}
              />
              <CopyField
                label="Spouse's Full Name"
                value={answers.spouseName}
                fieldKey="spouseName"
                copiedKey={copiedKey}
                onCopy={copyToClipboard}
              />
            </FieldGrid>
          </SectionCard>

          {/* Section 4: Address & Contact */}
          <SectionCard
            title="4. Address & Contact Information"
            description="Current residential address in Bangladesh and applicant direct contact."
          >
            <FieldGrid>
              <CopyField
                label="Present Address in BD"
                value={answers.presentAddress}
                fieldKey="presentAddress"
                copiedKey={copiedKey}
                onCopy={copyToClipboard}
                isFullWidth
              />
              <CopyField
                label="City / District"
                value={answers.district}
                fieldKey="district"
                copiedKey={copiedKey}
                onCopy={copyToClipboard}
              />
              <CopyField
                label="Postal Code"
                value={answers.postalCode}
                fieldKey="postalCode"
                copiedKey={copiedKey}
                onCopy={copyToClipboard}
              />
              <CopyField
                label="Applicant Mobile Phone"
                value={answers.phone}
                fieldKey="phone"
                copiedKey={copiedKey}
                onCopy={copyToClipboard}
                isPrimary
              />
              <CopyField
                label="Applicant Email Address"
                value={caseData.applicant_email || answers.email}
                fieldKey="email"
                copiedKey={copiedKey}
                onCopy={copyToClipboard}
              />
            </FieldGrid>
          </SectionCard>

          {/* Section 5: Destination & Travel Details */}
          <SectionCard
            title="5. Destination & Travel Details"
            description="Port of arrival, purpose of visit, and reference contacts in destination."
          >
            <FieldGrid>
              <CopyField
                label="Reference / Hospital / Hotel in Destination"
                value={answers.destinationContactName}
                fieldKey="destinationContactName"
                copiedKey={copiedKey}
                onCopy={copyToClipboard}
                isFullWidth
                isPrimary
              />
              <CopyField
                label="Destination City / Address"
                value={answers.destinationAddress}
                fieldKey="destinationAddress"
                copiedKey={copiedKey}
                onCopy={copyToClipboard}
                isFullWidth
              />
              <CopyField
                label="Port of Arrival / Border Post"
                value={answers.portOfEntry}
                fieldKey="portOfEntry"
                copiedKey={copiedKey}
                onCopy={copyToClipboard}
              />
              <CopyField
                label="Expected Travel Date"
                value={answers.travelDate}
                fieldKey="travelDate"
                copiedKey={copiedKey}
                onCopy={copyToClipboard}
              />
              <CopyField
                label="Destination Phone"
                value={answers.destinationPhone}
                fieldKey="destinationPhone"
                copiedKey={copiedKey}
                onCopy={copyToClipboard}
              />
              {answers.treatmentCategory !== "—" && (
                <CopyField
                  label="Medical / Treatment Category"
                  value={answers.treatmentCategory.replace(/_/g, " ")}
                  fieldKey="treatmentCategory"
                  copiedKey={copiedKey}
                  onCopy={copyToClipboard}
                />
              )}
              {answers.attendantsCount !== "—" && (
                <CopyField
                  label="Accompanying Attendants"
                  value={`${answers.attendantsCount} attendant(s)`}
                  fieldKey="attendantsCount"
                  copiedKey={copiedKey}
                  onCopy={copyToClipboard}
                />
              )}
              {answers.residenceCountry !== "—" && (
                <CopyField
                  label="Current Residence Country"
                  value={answers.residenceCountry}
                  fieldKey="residenceCountry"
                  copiedKey={copiedKey}
                  onCopy={copyToClipboard}
                />
              )}
            </FieldGrid>
          </SectionCard>

          {/* Section 6: Complete Intake Questionnaire Answers */}
          <SectionCard
            title="6. Complete Intake Questionnaire Answers"
            description="All questions and specific answers provided by the applicant during the application questionnaire."
          >
            {Object.keys(caseData.intake_answers || {}).length === 0 ? (
              <p className="text-xs text-muted-foreground py-2">
                No questionnaire answers recorded for this case.
              </p>
            ) : (
              <FieldGrid>
                {Object.entries(caseData.intake_answers || {})
                  .filter(([key, val]) => {
                    if (val === null || val === undefined) return false;
                    if (typeof val === "string" && val.trim() === "") return false;
                    if (key.startsWith("_")) return false;
                    return true;
                  })
                  .map(([key, val]) => {
                    const label = key
                      .replace(/_/g, " ")
                      .replace(/\b\w/g, (c) => c.toUpperCase());

                    let displayVal = String(val);
                    if (typeof val === "boolean") {
                      displayVal = val ? "Yes" : "No";
                    } else if (Array.isArray(val)) {
                      displayVal = val.join(", ");
                    } else if (typeof val === "object") {
                      displayVal = JSON.stringify(val);
                    }

                    return (
                      <CopyField
                        key={key}
                        label={label}
                        value={displayVal}
                        fieldKey={`intake_${key}`}
                        copiedKey={copiedKey}
                        onCopy={copyToClipboard}
                      />
                    );
                  })}
              </FieldGrid>
            )}
          </SectionCard>

          {/* Section 7: Uploaded Documents */}
          <SectionCard
            title="7. Uploaded Documents & Photographs"
            description="Applicant's uploaded passport copy, photographs, and supporting proofs."
          >
            {checklist.length === 0 ? (
              <p className="text-xs text-muted-foreground py-2">
                No checklist documents recorded yet for this case.
              </p>
            ) : (
              <div className="space-y-2">
                {checklist.map((item) => {
                  const isDone =
                    item.status === "complete" ||
                    item.status === "uploaded" ||
                    item.status === "gathered" ||
                    Boolean(item.document_id);
                  const matchedDoc = item.document_id
                    ? documents.find((d) => d.id === item.document_id)
                    : documents.slice().reverse().find((d) => d.doc_type === item.code);
                  const fileUrl = matchedDoc
                    ? getCaseDocumentFileUrl(caseId, matchedDoc.id, token)
                    : getChecklistItemFileUrl(caseId, item.id, token);
                  const fileName = matchedDoc?.filename || `${item.code}.pdf`;

                  return (
                    <div
                      key={item.id}
                      className="flex flex-col sm:flex-row sm:items-center justify-between p-3.5 rounded-xl border border-border/70 bg-muted/20 text-xs gap-3 transition-colors hover:bg-muted/30"
                    >
                      <div className="flex items-start sm:items-center gap-3 min-w-0 flex-1">
                        <div className="p-2 rounded-lg bg-primary/10 text-primary shrink-0">
                          <FileCheck className="size-4" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <p className="font-semibold text-foreground text-sm">{item.name}</p>
                            {matchedDoc && (
                              <span
                                className="font-mono text-[10px] text-muted-foreground bg-muted/60 px-1.5 py-0.5 rounded border border-border/50 truncate max-w-[200px]"
                                title={matchedDoc.filename}
                              >
                                {matchedDoc.filename}
                              </span>
                            )}
                            {matchedDoc?.extracted_fields &&
                              Object.keys(matchedDoc.extracted_fields).length > 0 && (
                                <Badge tone="info" className="text-[9px] py-0 px-1.5 font-normal">
                                  ✨ AI Extracted ({Object.keys(matchedDoc.extracted_fields).length} fields)
                                </Badge>
                              )}
                          </div>
                          <p className="text-[11px] text-muted-foreground line-clamp-1">
                            {item.why_required || "Required Document"}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
                        <Badge tone={isDone ? "success" : "muted"} className="text-[10px] px-2 py-0.5">
                          {isDone ? "Uploaded & Ready" : "Pending"}
                        </Badge>

                        {isDone && (
                          <div className="flex items-center gap-1.5">
                            <Button
                              type="button"
                              size="sm"
                              variant="outline"
                              onClick={() => {
                                setPreviewDoc({
                                  id: matchedDoc?.id || null,
                                  checklistItemId: item.id,
                                  name: item.name,
                                  filename: fileName,
                                  url: fileUrl,
                                  extractedFields: matchedDoc?.extracted_fields as Record<string, unknown> | undefined,
                                  confidence: matchedDoc?.extraction_confidence,
                                });
                              }}
                              className="h-7 text-xs px-2.5 gap-1.5 bg-background shadow-xs hover:bg-primary/10 hover:text-primary hover:border-primary/50 transition-colors"
                            >
                              <Eye className="size-3.5" />
                              View
                            </Button>

                            <a
                              href={fileUrl}
                              download={fileName}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex"
                              title="Download file"
                            >
                              <Button
                                type="button"
                                size="sm"
                                variant="ghost"
                                className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground hover:bg-muted/50"
                              >
                                <Download className="size-3.5" />
                              </Button>
                            </a>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </SectionCard>
        </div>

        {/* Right Column (1 Col): Staff Filing & Submission Console */}
        <div className="space-y-6">
          {/* Payment & Fee Verification Card */}
          <Card className="border border-border shadow-xs">
            <CardHeader className="pb-3 border-b border-border/60">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CreditCard className="size-4 text-emerald-600 dark:text-emerald-400" />
                  <CardTitle className="text-sm font-bold">Payment &amp; Fees</CardTitle>
                </div>
                <Badge
                  tone={
                    payment?.status === "completed" ||
                    caseData.status === "payment_completed" ||
                    caseData.status === "submitted"
                      ? "success"
                      : "warning"
                  }
                  className="text-[10px]"
                >
                  {payment?.status === "completed" ||
                  caseData.status === "payment_completed" ||
                  caseData.status === "submitted"
                    ? "Paid & Verified"
                    : "Payment Pending"}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-3 pt-3 text-xs">
              <div className="flex justify-between items-center pb-2 border-b">
                <span className="text-muted-foreground">Transaction ID</span>
                <div className="flex items-center gap-1.5 font-mono font-bold text-foreground">
                  <span>{payment?.transaction_id || answers.paymentTxnId || "—"}</span>
                  {(payment?.transaction_id || answers.paymentTxnId) && (
                    <button
                      type="button"
                      onClick={() =>
                        copyToClipboard(
                          payment?.transaction_id || answers.paymentTxnId,
                          "paymentTxn"
                        )
                      }
                      className="text-muted-foreground hover:text-foreground"
                    >
                      <Copy className="size-3" />
                    </button>
                  )}
                </div>
              </div>
              <div className="flex justify-between items-center pb-2 border-b">
                <span className="text-muted-foreground">Method</span>
                <span className="font-semibold uppercase text-foreground">
                  {payment?.payment_method || answers.paymentMethod || "Online / bKash"}
                </span>
              </div>
              <div className="flex justify-between items-center pb-2 border-b">
                <span className="text-muted-foreground">Fee Paid</span>
                <span className="font-bold text-emerald-600 dark:text-emerald-400 font-mono">
                  {payment
                    ? `${payment.currency} ${payment.total_amount.toLocaleString()}`
                    : "BDT 2,000"}
                </span>
              </div>
              {answers.eligibilityScore !== "—" && (
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">Applicant Score</span>
                  <Badge tone="default" className="text-[10px] font-bold">
                    {answers.eligibilityScore}% Approval Score
                  </Badge>
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="border border-border shadow-xs sticky top-4">
            <CardHeader className="pb-3 border-b border-border/60">
              <div className="flex items-center gap-2">
                <ShieldCheck className="size-4 text-primary" />
                <CardTitle className="text-sm font-bold">Government Filing Controls</CardTitle>
              </div>
              <CardDescription className="text-xs">
                Update the official government filing status and reference number for the applicant.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 pt-4 text-xs">
              {/* Submission Reference Field */}
              <div className="space-y-1.5">
                <label className="font-semibold text-foreground block">
                  Official Web File / Application Reference
                </label>
                <input
                  type="text"
                  value={submissionRef}
                  onChange={(e) => setSubmissionRef(e.target.value)}
                  placeholder="e.g. BGDW10928374 or ARN-994"
                  className="w-full h-9 rounded-md border bg-background px-3 font-mono text-xs outline-none focus:ring-1 focus:ring-primary"
                />
                <p className="text-[10px] text-muted-foreground">
                  The official token/ARN generated by the destination government portal.
                </p>
              </div>

              {/* Status Indicator */}
              <div className="space-y-1.5">
                <label className="font-semibold text-foreground block">
                  Current Case State
                </label>
                <div className="p-2.5 rounded-lg border border-border/80 bg-muted/30 flex items-center justify-between">
                  <span className="font-medium capitalize">{caseData.status.replace(/_/g, " ")}</span>
                  <Badge tone="success" className="text-[10px]">Active</Badge>
                </div>
              </div>

              {/* Internal Staff Notes */}
              <div className="space-y-1.5">
                <label className="font-semibold text-foreground block">
                  Staff Filing Notes & Appointment Details
                </label>
                <textarea
                  rows={4}
                  value={staffNotes}
                  onChange={(e) => setStaffNotes(e.target.value)}
                  placeholder="e.g. Submitted on IVAC portal for Chittagong center on Nov 14, fee disbursed."
                  className="w-full rounded-md border bg-background p-2.5 text-xs outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              {/* Save Button */}
              <Button
                type="button"
                onClick={handleSaveStaffFiling}
                disabled={isSaving}
                className="w-full text-xs font-bold gap-2"
              >
                {isSaving ? (
                  <>
                    <Loader2 className="size-3.5 animate-spin" /> Saving...
                  </>
                ) : (
                  <>
                    <Save className="size-3.5" /> Save Staff Submission Updates
                  </>
                )}
              </Button>

              {/* Quick Helper Tips */}
              <div className="rounded-lg border border-border/60 bg-muted/20 p-3 space-y-1.5 text-[11px] text-muted-foreground">
                <p className="font-semibold text-foreground flex items-center gap-1.5">
                  <CheckCircle2 className="size-3 text-emerald-500" />
                  Staff Concierge Workflow:
                </p>
                <ol className="list-decimal pl-4 space-y-1">
                  <li>Open the official government website.</li>
                  <li>Copy-paste applicant particulars.</li>
                  <li>Disburse official government fee.</li>
                  <li>Enter the ARN / Application ID above.</li>
                  <li>Click Save so applicant sees confirmation.</li>
                </ol>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Document Preview & OCR Inspection Modal */}
      {previewDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-background/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div
            className="fixed inset-0"
            onClick={() => setPreviewDoc(null)}
            aria-hidden="true"
          />
          <div className="relative z-10 w-full max-w-5xl max-h-[92vh] flex flex-col bg-card rounded-2xl border border-border shadow-2xl overflow-hidden">
            {/* Modal Header */}
            <div className="flex items-center justify-between px-5 py-3.5 border-b border-border/80 bg-muted/30">
              <div className="flex items-center gap-3 min-w-0">
                <div className="p-2 rounded-xl bg-primary/10 text-primary shrink-0">
                  <FileText className="size-5" />
                </div>
                <div className="min-w-0">
                  <h3 className="text-sm sm:text-base font-bold text-foreground truncate">{previewDoc.name}</h3>
                  <p className="text-xs text-muted-foreground font-mono truncate">{previewDoc.filename}</p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <a
                  href={previewDoc.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border bg-background text-xs font-medium hover:bg-muted transition-colors text-foreground"
                >
                  <ExternalLink className="size-3.5" />
                  <span className="hidden sm:inline">Open in New Tab</span>
                </a>
                <a
                  href={previewDoc.url}
                  download={previewDoc.filename}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border bg-background text-xs font-medium hover:bg-muted transition-colors text-foreground"
                >
                  <Download className="size-3.5" />
                  <span className="hidden sm:inline">Download</span>
                </a>
                <button
                  type="button"
                  onClick={() => setPreviewDoc(null)}
                  className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors ml-1"
                >
                  <X className="size-5" />
                </button>
              </div>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto p-4 sm:p-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Document Viewer (Iframe / Image) */}
              <div className="lg:col-span-2 min-h-[460px] h-[550px] rounded-xl border border-border/70 overflow-hidden bg-muted/10 shadow-inner flex flex-col items-center justify-center">
                {previewDoc.filename.toLowerCase().match(/\.(jpg|jpeg|png|webp|gif)$/) ? (
                  <div className="w-full h-full flex items-center justify-center p-4 bg-muted/20 overflow-auto">
                    <img
                      src={previewDoc.url}
                      alt={previewDoc.name}
                      className="max-w-full max-h-full object-contain rounded-lg shadow-sm"
                    />
                  </div>
                ) : (
                  <iframe
                    src={previewDoc.url}
                    title={previewDoc.name}
                    className="w-full h-full border-0 rounded-xl"
                  />
                )}
              </div>

              {/* OCR / Extracted Details Panel */}
              <div className="space-y-4">
                <div className="rounded-xl border border-border/70 bg-muted/20 p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-foreground flex items-center gap-1.5">
                      <Sparkles className="size-3.5 text-amber-500" />
                      AI Extracted Data
                    </span>
                    {previewDoc.confidence && (
                      <Badge tone="info" className="text-[10px]">
                        {Math.round(previewDoc.confidence * 100)}% Confidence
                      </Badge>
                    )}
                  </div>

                  {previewDoc.extractedFields && Object.keys(previewDoc.extractedFields).length > 0 ? (
                    <div className="space-y-2 pt-1 max-h-[380px] overflow-y-auto pr-1">
                      {Object.entries(previewDoc.extractedFields).map(([key, rawVal]) => {
                        const val =
                          typeof rawVal === "object" && rawVal !== null && "value" in rawVal
                            ? String((rawVal as { value: unknown }).value)
                            : String(rawVal ?? "");
                        if (!val || val === "undefined") return null;

                        const formattedKey = key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
                        return (
                          <div
                            key={key}
                            className="p-2.5 rounded-lg bg-background/80 border border-border/60 text-xs flex items-center justify-between gap-2"
                          >
                            <div className="min-w-0">
                              <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider">
                                {formattedKey}
                              </p>
                              <p className="font-semibold text-foreground truncate">{val}</p>
                            </div>
                            <button
                              type="button"
                              onClick={() => copyToClipboard(val, `ocr-${key}`)}
                              className="p-1 rounded text-muted-foreground hover:text-foreground shrink-0 hover:bg-muted"
                              title="Copy to clipboard"
                            >
                              {copiedKey === `ocr-${key}` ? (
                                <Check className="size-3 text-emerald-500" />
                              ) : (
                                <Copy className="size-3" />
                              )}
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <p className="text-xs text-muted-foreground py-2">
                      No OCR extracted fields recorded for this document. You can verify the file directly using the embedded preview on the left.
                    </p>
                  )}
                </div>

                <div className="p-3.5 rounded-xl border border-primary/20 bg-primary/5 text-xs text-muted-foreground space-y-1">
                  <p className="font-semibold text-foreground flex items-center gap-1.5 text-[11px]">
                    <ShieldCheck className="size-3.5 text-primary" />
                    Staff Verification Note
                  </p>
                  <p className="text-[11px] leading-relaxed">
                    Ensure the applicant details on this document match the intake answers before entering them into the official visa portal.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Sub-components & Helpers
// ─────────────────────────────────────────────────────────────────────────────

function SectionCard({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <Card className="border border-border shadow-xs">
      <CardHeader className="pb-3 border-b border-border/60">
        <CardTitle className="text-sm font-bold text-foreground">{title}</CardTitle>
        <CardDescription className="text-xs text-muted-foreground">{description}</CardDescription>
      </CardHeader>
      <CardContent className="pt-4">{children}</CardContent>
    </Card>
  );
}

function FieldGrid({ children }: { children: React.ReactNode }) {
  return <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">{children}</div>;
}

function CopyField({
  label,
  value,
  fieldKey,
  copiedKey,
  onCopy,
  isPrimary,
  isFullWidth,
}: {
  label: string;
  value?: string;
  fieldKey: string;
  copiedKey: string | null;
  onCopy: (text: string, key: string) => void;
  isPrimary?: boolean;
  isFullWidth?: boolean;
}) {
  const displayVal = value && value.trim() ? value.trim() : "—";
  const isCopied = copiedKey === fieldKey;

  return (
    <div
      className={`rounded-xl border p-2.5 flex items-center justify-between gap-2 transition-all ${
        isFullWidth ? "sm:col-span-2" : ""
      } ${
        isCopied
          ? "border-emerald-500/50 bg-emerald-500/10"
          : isPrimary
          ? "border-primary/25 bg-primary/5"
          : "border-border/70 bg-card hover:border-border"
      }`}
    >
      <div className="flex flex-col min-w-0 flex-1">
        <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
          {label}
        </span>
        <span className={`text-xs font-semibold truncate ${displayVal === "—" ? "text-muted-foreground" : "text-foreground font-mono"}`}>
          {displayVal}
        </span>
      </div>

      {displayVal !== "—" && (
        <button
          type="button"
          onClick={() => onCopy(displayVal, fieldKey)}
          title={`Copy ${label}`}
          className={`shrink-0 flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] font-bold transition-all ${
            isCopied
              ? "bg-emerald-600 text-white"
              : "bg-muted text-foreground hover:bg-primary hover:text-primary-foreground"
          }`}
        >
          {isCopied ? (
            <>
              <Check className="size-3" />
              <span>Copied</span>
            </>
          ) : (
            <>
              <Copy className="size-3" />
              <span>Copy</span>
            </>
          )}
        </button>
      )}
    </div>
  );
}

// Extract canonical applicant answers from intake answers dictionary
function useCaseDataAnswers(caseData?: Case) {
  return useMemo(() => {
    const raw = (caseData?.intake_answers || {}) as Record<string, any>;

    const get = (...keys: string[]): string => {
      for (const k of keys) {
        if (raw[k] !== undefined && raw[k] !== null && String(raw[k]).trim() !== "") {
          return String(raw[k]);
        }
      }
      return "—";
    };

    const fullName = get("full_name", "applicant_name", "name");
    let givenName = get("given_name", "first_name");
    let surname = get("surname", "last_name", "family_name");

    // If only full name was provided, derive given and surname
    if (givenName === "—" && fullName !== "—") {
      const parts = fullName.split(" ");
      givenName = parts.slice(0, -1).join(" ") || parts[0];
      surname = parts.length > 1 ? parts[parts.length - 1] : "—";
    }

    return {
      fullName,
      givenName,
      surname,
      passportNumber: get("passport_number", "passport_num", "travel_document_number"),
      passportType: get("passport_type", "type_of_passport") || "Ordinary",
      passportIssueCountry: get("passport_issue_country", "country_of_issue") || get("nationality", "citizenship") || "Bangladesh",
      passportIssueDate: get("passport_issue_date", "issue_date"),
      passportExpiryDate: get("passport_expiry", "passport_expiry_date", "expiration_date"),
      passportIssuePlace: get("passport_issue_place", "place_of_issue"),
      nidNumber: get("national_id", "nid", "nid_number"),
      dob: get("date_of_birth", "dob", "birth_date"),
      gender: get("gender", "sex"),
      pobCity: get("place_of_birth_city", "place_of_birth", "birth_city"),
      pobCountry: get("place_of_birth_country", "birth_country"),
      citizenship: get("nationality", "citizenship", "origin_country") || "Bangladeshi",
      religion: get("religion"),
      maritalStatus: get("marital_status"),
      occupation: get("occupation", "profession", "job_title"),
      fatherName: get("father_name", "fathers_name"),
      fatherNationality: get("father_nationality"),
      motherName: get("mother_name", "mothers_name"),
      motherNationality: get("mother_nationality"),
      spouseName: get("spouse_name", "spouses_name"),
      presentAddress: get("present_address", "residential_address", "address_bd", "address"),
      district: get("district", "city"),
      postalCode: get("postal_code", "zip_code"),
      phone: get("phone", "mobile_phone", "applicant_phone"),
      email: get("email", "applicant_email"),
      portOfEntry: get("port_of_entry", "arrival_port", "border_post"),
      travelDate: get("expected_travel_date", "travel_date", "arrival_date"),
      destinationContactName: get("destination_hospital", "destination_contact_name", "hospital_name", "hotel_name", "sponsor_name"),
      destinationAddress: get("hospital_city", "destination_address", "hotel_address", "hospital_address"),
      destinationPhone: get("destination_phone", "hospital_phone", "hotel_phone"),
      hospitalCity: get("hospital_city", "destination_city"),
      treatmentCategory: get("illness_treatment_category", "treatment_category", "purpose_of_visit"),
      attendantsCount: get("accompanying_attendants_count", "attendants_count"),
      residenceCountry: get("current_residence_country", "country_of_residence"),
      hasHospitalInvitation: get("has_indian_hospital_invitation"),
      hasMedicalReferral: get("has_local_medical_referral"),
      hasSufficientFunds: get("has_sufficient_funds"),
      eligibilityScore: get("eligibility_score"),
      paymentMethod: get("payment_method"),
      paymentTxnId: get("payment_txn_id"),
    };
  }, [caseData]);
}
