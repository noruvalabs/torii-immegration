"use client";

import { useEffect, useState } from "react";
import {
  ExternalLink,
  Globe,
  CreditCard,
  FileText,
  CheckCircle2,
  Loader2,
  Check,
  ArrowDown,
  Hash,
  ShieldCheck,
  Search,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import {
  getCaseJourney,
  patchCase,
  type CaseJourney,
  type Case,
} from "@/lib/api/cases";

type PostSubmissionGuideProps = {
  token: string | null;
  caseData: Case;
  onRefresh?: () => void;
};

export function PostSubmissionGuide({
  token,
  caseData,
  onRefresh,
}: PostSubmissionGuideProps) {
  const [journey, setJourney] = useState<CaseJourney | null>(null);
  const [arnInput, setArnInput] = useState("");
  const [savingArn, setSavingArn] = useState(false);
  const [editingArn, setEditingArn] = useState(false);

  const isIndia =
    caseData.reference.startsWith("IN-") ||
    caseData.jurisdiction_code === "IN" ||
    (caseData.scope_label && caseData.scope_label.toLowerCase().includes("india"));

  const isMedical =
    Boolean(caseData.scope_label && caseData.scope_label.toLowerCase().includes("medical")) ||
    caseData.reference.toLowerCase().includes("medical");

  const isUK =
    caseData.reference.startsWith("UK-") ||
    caseData.reference.startsWith("GB-") ||
    caseData.jurisdiction_code === "UK" ||
    (caseData.scope_label && caseData.scope_label.toLowerCase().includes("united kingdom"));

  useEffect(() => {
    if (!token || !caseData.id) return;
    let active = true;
    getCaseJourney(token, caseData.id)
      .then((data) => {
        if (active) setJourney(data);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [token, caseData.id]);

  // Exact Official Government Direct Links
  const officialPortalUrl = isIndia
    ? "https://indianvisaonline.gov.in/visa/registration"
    : isUK
      ? "https://www.gov.uk/browse/visas-immigration"
      : journey?.apply_url || null;

  const officialPaymentUrl = isIndia
    ? "https://indianvisaonline.gov.in/evisa/PaymentCheck"
    : isUK
      ? "https://www.gov.uk/healthcare-immigration-application"
      : officialPortalUrl;

  const officialTrackingUrl = isIndia
    ? "https://indianvisaonline.gov.in/visa/VisaEnquiry"
    : isUK
      ? "https://www.gov.uk/view-prove-immigration-status"
      : null;

  const hasCustomArn =
    Boolean(caseData.submission_reference) &&
    caseData.submission_reference !== caseData.reference &&
    !caseData.submission_reference?.startsWith("EFILE-");

  async function handleSaveArn() {
    if (!token || !arnInput.trim()) return;
    setSavingArn(true);
    try {
      await patchCase(token, caseData.id, {
        submission_reference: arnInput.trim(),
      });
      toast.success("Government receipt number saved!");
      setEditingArn(false);
      if (onRefresh) onRefresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save reference number");
    } finally {
      setSavingArn(false);
    }
  }

  function handleScrollToLetter() {
    const el = document.getElementById("cover-letter-card");
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  }

  return (
    <Card className="border-primary/30 bg-gradient-to-b from-card to-card/95 shadow-md overflow-hidden">
      <CardContent className="p-5 sm:p-6 lg:p-7 space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border/80 pb-5">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5">
              <span className="flex size-7 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <ShieldCheck className="size-4.5" />
              </span>
              <h3 className="text-base sm:text-lg font-bold text-foreground tracking-tight">
                Next Steps: Official Visa Submission &amp; Payment
              </h3>
              <Badge tone="success" className="text-[11px] font-semibold px-2">
                Ready to Submit
              </Badge>
            </div>
            <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed pl-9">
              Your cover letter has been prepared by Torii. Follow these 3 clear steps to submit your application and complete official payment.
            </p>
          </div>

          {officialPortalUrl && (
            <div className="flex items-center gap-2 self-start sm:self-auto shrink-0 pl-9 sm:pl-0">
              <a
                href={officialPortalUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground shadow-sm hover:bg-primary/90 transition-all"
              >
                <Globe className="size-4" />
                {isIndia && isMedical ? "Open Medical Visa Form" : "Open Gov Portal"}
                <ExternalLink className="size-3.5 opacity-80" />
              </a>
            </div>
          )}
        </div>

        {/* 3 Large, Actionable Step Cards */}
        <div className="grid gap-4 sm:gap-5 md:grid-cols-3">
          {/* ── Step 1: Download Cover Letter ── */}
          <div className="group rounded-xl border border-border/80 bg-muted/20 hover:border-blue-500/40 hover:bg-blue-500/[0.02] p-5 flex flex-col justify-between transition-all space-y-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="flex size-9 items-center justify-center rounded-xl bg-blue-500/10 text-blue-600 dark:text-blue-400 font-bold text-sm border border-blue-500/20 shadow-xs">
                  1
                </span>
                <Badge tone="info" className="text-[10px] font-semibold">
                  Step 1
                </Badge>
              </div>

              <div>
                <h4 className="text-sm sm:text-base font-semibold text-foreground flex items-center gap-1.5">
                  <FileText className="size-4 text-blue-500" />
                  Download Cover Letter
                </h4>
                <p className="mt-1.5 text-xs text-muted-foreground leading-relaxed">
                  Your customized embassy cover letter is ready with your passport details, purpose of travel, and dates.
                </p>
              </div>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={handleScrollToLetter}
              className="w-full text-xs font-medium border-blue-500/30 text-blue-600 dark:text-blue-400 hover:bg-blue-500/10 hover:text-blue-700 dark:hover:text-blue-300 gap-1.5 h-9"
            >
              <ArrowDown className="size-3.5" />
              Review Cover Letter Below
            </Button>
          </div>

          {/* ── Step 2: Apply & Pay Fee (Crucial Highlighted Step) ── */}
          <div className="group rounded-xl border-2 border-primary/40 bg-primary/[0.04] hover:border-primary p-5 flex flex-col justify-between transition-all space-y-4 shadow-sm relative ring-1 ring-primary/20">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="flex size-9 items-center justify-center rounded-xl bg-primary text-primary-foreground font-bold text-sm shadow-sm">
                  2
                </span>
                <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold text-primary">
                  Official Portal
                </span>
              </div>

              <div>
                <h4 className="text-sm sm:text-base font-semibold text-foreground flex items-center gap-1.5">
                  <Globe className="size-4 text-primary" />
                  Fill Form &amp; Pay Visa Fee
                </h4>
                <p className="mt-1.5 text-xs text-muted-foreground leading-relaxed">
                  {isIndia && isMedical
                    ? "Go directly to the Indian Medical Visa online registration form. Fill in your details, upload documents, and complete fee payment."
                    : "Go to the official government visa website, fill in your application, upload your documents, and complete fee payment."}
                </p>
              </div>
            </div>

            {/* Direct Links to Gov Portal & Payment */}
            <div className="space-y-2 pt-1">
              {isIndia && isMedical ? (
                <>
                  <a
                    href="https://indianvisaonline.gov.in/visa/registration"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center justify-between gap-2 w-full rounded-lg bg-primary py-2.5 px-3.5 text-xs font-semibold text-primary-foreground shadow-sm hover:bg-primary/90 transition-all text-left"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <Globe className="size-4 shrink-0" />
                      <div className="flex flex-col truncate">
                        <span>Apply for Medical Visa</span>
                        <span className="text-[10px] font-normal opacity-90 truncate">Direct Government Online Registration Form</span>
                      </div>
                    </div>
                    <ExternalLink className="size-3.5 shrink-0 opacity-80" />
                  </a>

                  {officialPaymentUrl && (
                    <a
                      href={officialPaymentUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center justify-between gap-2 w-full rounded-lg bg-emerald-600 hover:bg-emerald-700 py-2.5 px-3.5 text-xs font-semibold text-white shadow-xs transition-all text-left"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <CreditCard className="size-4 shrink-0" />
                        <div className="flex flex-col truncate">
                          <span>Pay Visa Fee Online</span>
                          <span className="text-[10px] font-normal opacity-90 truncate">Verify &amp; pay consular fee</span>
                        </div>
                      </div>
                      <ExternalLink className="size-3.5 shrink-0 opacity-80" />
                    </a>
                  )}

                  <div className="rounded-lg border border-amber-500/25 bg-amber-500/10 p-2.5 text-[11px] leading-relaxed text-amber-900 dark:text-amber-200 flex items-start gap-2">
                    <span className="font-bold text-xs text-amber-600 dark:text-amber-400 mt-0.5 shrink-0">💡 Tip:</span>
                    <span>
                      On the portal form, select <strong>&ldquo;MEDICAL VISA&rdquo;</strong> under Visa Type and <strong>&ldquo;FOR MEDICAL TREATMENT&rdquo;</strong> under Purpose.
                    </span>
                  </div>
                </>
              ) : (
                <>
                  {officialPortalUrl && (
                    <a
                      href={officialPortalUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center justify-center gap-2 w-full rounded-lg bg-primary py-2.5 px-3.5 text-xs font-semibold text-primary-foreground shadow-sm hover:bg-primary/90 transition-all text-center"
                    >
                      <Globe className="size-4 shrink-0" />
                      <span>Go to Official Gov Website</span>
                      <ExternalLink className="size-3.5 shrink-0 ml-auto opacity-75" />
                    </a>
                  )}

                  {officialPaymentUrl && (
                    <a
                      href={officialPaymentUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center justify-center gap-2 w-full rounded-lg bg-emerald-600 hover:bg-emerald-700 py-2.5 px-3.5 text-xs font-semibold text-white shadow-xs transition-all text-center"
                    >
                      <CreditCard className="size-4 shrink-0" />
                      <span>Pay Visa Fee Online</span>
                      <ExternalLink className="size-3.5 shrink-0 ml-auto opacity-75" />
                    </a>
                  )}
                </>
              )}
            </div>
          </div>

          {/* ── Step 3: Track Application & Save ARN ── */}
          <div className="group rounded-xl border border-border/80 bg-muted/20 hover:border-purple-500/40 hover:bg-purple-500/[0.02] p-5 flex flex-col justify-between transition-all space-y-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="flex size-9 items-center justify-center rounded-xl bg-purple-500/10 text-purple-600 dark:text-purple-400 font-bold text-sm border border-purple-500/20 shadow-xs">
                  3
                </span>
                <Badge tone="muted" className="text-[10px] font-semibold">
                  Step 3
                </Badge>
              </div>

              <div>
                <h4 className="text-sm sm:text-base font-semibold text-foreground flex items-center gap-1.5">
                  <CheckCircle2 className="size-4 text-purple-500" />
                  Track Your Application
                </h4>
                <p className="mt-1.5 text-xs text-muted-foreground leading-relaxed">
                  After submitting online, you receive a Government Web File / ARN #. Save it here to keep your records updated.
                </p>
              </div>
            </div>

            {/* ARN Tracking Widget */}
            <div className="rounded-lg border bg-background/80 p-2.5 space-y-2">
              {hasCustomArn && !editingArn ? (
                <div className="space-y-2">
                  <div className="flex items-center justify-between gap-1.5 text-xs">
                    <span className="text-[11px] text-muted-foreground">Gov ARN:</span>
                    <span className="font-mono font-bold text-[var(--color-success)] text-xs truncate">
                      {caseData.submission_reference}
                    </span>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        setArnInput(caseData.submission_reference || "");
                        setEditingArn(true);
                      }}
                      className="h-6 px-1.5 text-[10px] text-muted-foreground hover:text-foreground shrink-0"
                    >
                      Edit
                    </Button>
                  </div>

                  {officialTrackingUrl && (
                    <a
                      href={officialTrackingUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center justify-center gap-1.5 w-full rounded border border-purple-500/30 bg-purple-500/5 py-1.5 px-2 text-[11px] font-medium text-purple-600 dark:text-purple-300 hover:bg-purple-500/10 transition-colors"
                    >
                      <Search className="size-3" />
                      Track on Gov Website
                      <ExternalLink className="size-3" />
                    </a>
                  )}
                </div>
              ) : (
                <div className="space-y-2">
                  <div className="flex items-center gap-1.5">
                    <input
                      type="text"
                      placeholder="Enter ARN / Web File #"
                      value={arnInput}
                      onChange={(e) => setArnInput(e.target.value)}
                      className="h-8 w-full rounded border bg-background px-2.5 font-mono text-xs outline-none focus:ring-1 focus:ring-primary"
                    />
                    <Button
                      size="sm"
                      onClick={handleSaveArn}
                      disabled={savingArn || !arnInput.trim()}
                      className="h-8 px-3 text-xs shrink-0 font-medium"
                    >
                      {savingArn ? <Loader2 className="size-3 animate-spin" /> : "Save"}
                    </Button>
                  </div>
                  {editingArn && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setEditingArn(false)}
                      className="h-5 px-1.5 text-[10px] text-muted-foreground w-full"
                    >
                      Cancel
                    </Button>
                  )}
                  {isIndia && (
                    <div className="pt-1 flex items-center justify-between text-[11px] border-t border-border/50">
                      <a
                        href="https://indianvisaonline.gov.in/visa/VisaEnquiry"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-purple-600 dark:text-purple-400 hover:underline"
                      >
                        <Search className="size-3" /> Track Status
                        <ExternalLink className="size-2.5 opacity-70" />
                      </a>
                      <a
                        href="https://indianvisaonline.gov.in/visa/PrintApplication"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-muted-foreground hover:text-foreground hover:underline"
                      >
                        <FileText className="size-3" /> Reprint Form
                        <ExternalLink className="size-2.5 opacity-70" />
                      </a>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
