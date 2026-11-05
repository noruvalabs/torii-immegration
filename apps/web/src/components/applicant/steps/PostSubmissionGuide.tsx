"use client";

import { useEffect, useState } from "react";
import {
  Bot,
  CheckCircle2,
  Clock,
  ShieldCheck,
  FileText,
  Calendar,
  Sparkles,
  Phone,
  MessageCircle,
  RefreshCw,
  Copy,
  Check,
  Download,
  KeyRound,
  Loader2,
  ArrowRight,
  ExternalLink,
  RotateCcw,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { SUPPORT_CONFIG } from "@/lib/support";
import { PortalBotConsole } from "@/components/applicant/PortalBotConsole";
import { getLatestPortalJob, dispatchPortalBot, type PortalJob } from "@/lib/api/portal-bot";
import type { Case } from "./types";

type PostSubmissionGuideProps = {
  token: string | null;
  caseData: Case;
  onRefresh?: () => void;
  onDownloadPdf?: () => void;
  isExportingPdf?: boolean;
};

export function PostSubmissionGuide({
  token,
  caseData,
  onRefresh,
  onDownloadPdf,
  isExportingPdf = false,
}: PostSubmissionGuideProps) {
  const [copiedRef, setCopiedRef] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isDownloadingDirect, setIsDownloadingDirect] = useState(false);
  const [botJob, setBotJob] = useState<PortalJob | null>(null);
  const [botConsoleOpen, setBotConsoleOpen] = useState(false);
  const [botRunning, setBotRunning] = useState(false);

  const jCode = (caseData.jurisdiction_code || "").toUpperCase();
  const refCode = (caseData.reference || "").toUpperCase();
  const isDigitalCorridor =
    caseData.submission_track === "digital" ||
    jCode === "SA" ||
    jCode === "VN" ||
    refCode.startsWith("SA-") ||
    refCode.startsWith("VN-");
  const portalName = jCode === "SA" ? "ksavisa.sa (Saudi MOFA)" : jCode === "VN" ? "evisa.gov.vn" : "Official Portal";
  const isOtpWaiting = botJob?.status === "manual_takeover" || botJob?.status === "awaiting_otp";

  useEffect(() => {
    if (!token || !caseData.id || !isDigitalCorridor) return;
    void getLatestPortalJob(token, caseData.id).then((job) => {
      if (job) setBotJob(job);
    });
  }, [token, caseData.id, isDigitalCorridor]);

  // Periodic status poll when console is open or bot is running
  useEffect(() => {
    if (!token || !caseData.id || !isDigitalCorridor) return;
    if (!botConsoleOpen && !botRunning) return;

    const interval = setInterval(() => {
      void getLatestPortalJob(token, caseData.id).then((job) => {
        if (job) setBotJob(job);
      });
    }, 2500);

    return () => clearInterval(interval);
  }, [token, caseData.id, isDigitalCorridor, botConsoleOpen, botRunning]);

  async function handleRerunBot() {
    if (!token || !caseData.id) return;
    setBotRunning(true);
    try {
      const job = await dispatchPortalBot(token, caseData.id);
      setBotJob(job);
      toast.success("Portal worker dispatched!");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to launch portal bot");
    } finally {
      setBotRunning(false);
    }
  }

  async function handleLaunchOrViewBot() {
    setBotConsoleOpen(true);
    if ((!botJob || botJob.status === "failed") && token) {
      await handleRerunBot();
    }
  }

  const isIndia =
    caseData.reference.startsWith("IN-") ||
    caseData.jurisdiction_code === "IN" ||
    (caseData.scope_label && caseData.scope_label.toLowerCase().includes("india"));

  const destinationName = isIndia ? "India" : caseData.jurisdiction_code || "Destination";
  const hasStaffFilingRef =
    Boolean(caseData.submission_reference) &&
    caseData.submission_reference !== caseData.reference &&
    !caseData.submission_reference?.startsWith("EFILE-");

  const handleCopyRef = () => {
    void navigator.clipboard.writeText(caseData.reference);
    setCopiedRef(true);
    toast.success("Tracking reference copied to clipboard");
    setTimeout(() => setCopiedRef(false), 2000);
  };

  const handleRefreshClick = () => {
    setIsRefreshing(true);
    if (onRefresh) {
      onRefresh();
    }
    setTimeout(() => {
      setIsRefreshing(false);
      toast.success("Status refreshed from Torii operations queue");
    }, 600);
  };

  const handleDownload = async () => {
    if (onDownloadPdf) {
      onDownloadPdf();
      return;
    }

    const activeToken =
      token || (typeof window !== "undefined" ? localStorage.getItem("torii_token") : null);
    if (!activeToken) {
      toast.error("Please sign in again to download documents.");
      return;
    }

    setIsDownloadingDirect(true);
    try {
      const res = await fetch(
        `/backend/v1/cases/${caseData.id}/export/cover-letter?format=base64`,
        {
          headers: {
            Authorization: `Bearer ${activeToken}`,
            Accept: "application/json",
          },
        }
      );
      if (!res.ok) {
        throw new Error(`Export failed (${res.status})`);
      }
      const data = await res.json();
      if (!data?.data_base64) {
        throw new Error("Missing PDF file data.");
      }
      const binaryString = atob(data.data_base64);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      const blob = new Blob([bytes], { type: "application/pdf" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = data.filename || `${caseData.reference}-application-packet.pdf`;
      document.body.appendChild(link);
      link.click();
      toast.success("Application packet downloaded successfully!");
      setTimeout(() => {
        link.remove();
        URL.revokeObjectURL(url);
      }, 10000);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Download failed. Please try again.");
    } finally {
      setIsDownloadingDirect(false);
    }
  };

  const downloading = isExportingPdf || isDownloadingDirect;

  return (
    <div className="space-y-6">
      {/* ── BIG HERO CARD: APPLICATION SUCCESSFUL ── */}
      <Card className="relative overflow-hidden border-2 border-emerald-500/30 bg-gradient-to-b from-emerald-500/10 via-card to-card shadow-xl rounded-2xl">
        {/* Subtle decorative glow */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-3/4 h-32 bg-emerald-500/15 blur-3xl pointer-events-none rounded-full" />

        <CardContent className="relative p-6 sm:p-10 space-y-8">
          {/* Hero Celebration Badge & Headline */}
          <div className="text-center space-y-3">
            <div className="relative mx-auto flex size-20 items-center justify-center rounded-full bg-emerald-500/15 border-2 border-emerald-500/40 text-emerald-500 shadow-xl shadow-emerald-500/20">
              <CheckCircle2 className="size-10 text-emerald-500 animate-in zoom-in-75 duration-300" />
              <div className="absolute -top-1 -right-1 flex size-6 items-center justify-center rounded-full bg-emerald-500 text-white shadow-xs">
                <Sparkles className="size-3.5" />
              </div>
            </div>

            <div className="space-y-1.5 max-w-2xl mx-auto">
              <div className="inline-flex items-center gap-2 rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-bold text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 mb-1">
                <span className="flex size-2 rounded-full bg-emerald-500 animate-pulse" />
                OFFICIAL VISA FILING QUEUE
              </div>
              <h2 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold text-foreground tracking-tight">
                Application Submitted Successfully!
              </h2>
              <p className="text-sm sm:text-base text-muted-foreground leading-relaxed">
                Your visa application has been received and registered in our concierge queue.
                Our dedicated operations team is now handling your official government submission and fee payment.
              </p>
            </div>

            {/* Tracking Reference Pill */}
            <div className="pt-2">
              <div className="inline-flex items-center gap-2 rounded-full border border-border/80 bg-muted/40 px-4 py-1.5 text-xs shadow-2xs">
                <span className="text-muted-foreground font-medium">Tracking Reference:</span>
                <span className="font-mono font-bold text-foreground text-sm tracking-wide">
                  {caseData.reference}
                </span>
                <button
                  type="button"
                  onClick={handleCopyRef}
                  className="rounded p-1 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                  title="Copy Tracking ID"
                >
                  {copiedRef ? (
                    <Check className="size-3.5 text-emerald-500" />
                  ) : (
                    <Copy className="size-3.5" />
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* ── 3 HIGH-SIGNAL METRIC TILES ── */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
            <div className="rounded-xl border border-border/70 bg-card/80 p-4 text-center sm:text-left space-y-1 shadow-2xs">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground flex items-center justify-center sm:justify-start gap-1.5">
                <span className="flex size-2 rounded-full bg-emerald-500" /> Current Status
              </span>
              <p className="text-sm font-bold text-foreground">
                {hasStaffFilingRef ? "Officially Filed" : "Assigned to Staff"}
              </p>
              <p className="text-[11px] text-muted-foreground">In Embassy Operations Queue</p>
            </div>

            <div className="rounded-xl border border-border/70 bg-card/80 p-4 text-center sm:text-left space-y-1 shadow-2xs">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground flex items-center justify-center sm:justify-start gap-1.5">
                <Clock className="size-3 text-primary" /> Estimated Turnaround
              </span>
              <p className="text-sm font-bold text-emerald-600 dark:text-emerald-400">
                2 – 6 Business Hours
              </p>
              <p className="text-[11px] text-muted-foreground">Prompt processing guaranteed</p>
            </div>

            <div className="rounded-xl border border-border/70 bg-card/80 p-4 text-center sm:text-left space-y-1 shadow-2xs">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground flex items-center justify-center sm:justify-start gap-1.5">
                <MessageCircle className="size-3 text-emerald-500" /> Delivery Channels
              </span>
              <p className="text-sm font-bold text-foreground">SMS &amp; WhatsApp</p>
              <p className="text-[11px] text-muted-foreground">Real-time alerts on your phone</p>
            </div>
          </div>

          {/* ── MINIMAL 3-STEP ROADMAP (WHAT HAPPENS NEXT) ── */}
          <div className="space-y-3 pt-2">
            <div className="flex items-center justify-between border-b pb-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                What Happens Next
              </h4>
              <span className="text-[11px] text-muted-foreground font-medium">
                Step 2 of 3 in progress
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {/* Step 1 */}
              <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="flex size-7 items-center justify-center rounded-lg bg-emerald-500 text-white font-bold text-xs shadow-xs">
                    ✓
                  </span>
                  <Badge tone="success" className="text-[10px] font-bold">
                    Completed
                  </Badge>
                </div>
                <div>
                  <h5 className="text-xs sm:text-sm font-bold text-foreground">
                    1. Information &amp; Payment
                  </h5>
                  <p className="text-[11px] text-muted-foreground mt-0.5 leading-snug">
                    Your personal particulars, medical details, and service charge are confirmed.
                  </p>
                </div>
              </div>

              {/* Step 2 */}
              <div className="rounded-xl border-2 border-primary bg-primary/[0.04] p-4 space-y-3 ring-2 ring-primary/20 shadow-xs">
                <div className="flex items-center justify-between">
                  <span className="flex size-7 items-center justify-center rounded-lg bg-primary text-primary-foreground font-bold text-xs shadow-xs">
                    2
                  </span>
                  {isOtpWaiting ? (
                    <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/20 px-2 py-0.5 text-[10px] font-bold text-amber-500 animate-pulse border border-amber-500/30">
                      <KeyRound className="size-3" /> OTP Required
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-bold text-primary animate-pulse">
                      <Clock className="size-3" /> In Progress
                    </span>
                  )}
                </div>
                <div>
                  <h5 className="text-xs sm:text-sm font-bold text-foreground flex items-center gap-1">
                    <ShieldCheck className="size-3.5 text-primary shrink-0" />
                    2. Official Portal Filing
                  </h5>
                  <p className="text-[11px] text-muted-foreground mt-0.5 leading-snug">
                    {isDigitalCorridor
                      ? `Automated portal bot filing on ${portalName}.`
                      : `Our operations officer is entering your dossier into the ${destinationName} portal & paying consular fees.`}
                  </p>
                </div>

                {isDigitalCorridor && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleLaunchOrViewBot}
                    className={`w-full text-xs h-8 font-bold gap-1.5 cursor-pointer ${
                      isOtpWaiting
                        ? "bg-amber-600 hover:bg-amber-500 text-white border-amber-500 shadow-sm animate-pulse"
                        : botJob?.status === "failed"
                          ? "bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border-rose-500/40"
                          : "border-primary/40 hover:bg-primary/10 text-primary"
                    }`}
                  >
                    {isOtpWaiting ? (
                      <>
                        <KeyRound className="size-3.5" />
                        <span>Enter Verification Code (OTP)</span>
                      </>
                    ) : botRunning ? (
                      <>
                        <Loader2 className="size-3.5 animate-spin" />
                        <span>Bot Filing in Progress…</span>
                      </>
                    ) : botJob?.status === "failed" ? (
                      <>
                        <RotateCcw className="size-3.5" />
                        <span>Retry Submission Bot</span>
                      </>
                    ) : (
                      <>
                        <Bot className="size-3.5" />
                        <span>{botJob ? "View Bot Console" : "Launch Submission Bot"}</span>
                      </>
                    )}
                  </Button>
                )}
              </div>

              {/* Step 3 */}
              <div className="rounded-xl border border-border/80 bg-muted/20 p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="flex size-7 items-center justify-center rounded-lg bg-muted text-muted-foreground font-bold text-xs">
                    3
                  </span>
                  <Badge tone="default" className="text-[10px] font-semibold">
                    Upcoming
                  </Badge>
                </div>
                <div>
                  <h5 className="text-xs sm:text-sm font-bold text-foreground flex items-center gap-1">
                    <Calendar className="size-3.5 text-muted-foreground shrink-0" />
                    3. Appointment &amp; Web File
                  </h5>
                  <p className="text-[11px] text-muted-foreground mt-0.5 leading-snug">
                    Your official appointment slip and government ARN/Web File # will be delivered to your WhatsApp.
                  </p>
                </div>
              </div>
            </div>

            {/* Reassuring Zero-Action Callout */}
            <div className="rounded-lg bg-muted/40 p-3.5 flex items-start sm:items-center gap-3 text-xs text-muted-foreground border">
              <Sparkles className="size-4 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5 sm:mt-0" />
              <div>
                <span className="font-semibold text-foreground">No further action is required from you. </span>
                <span>
                  You do not need to visit any other website. We will notify you via SMS &amp; WhatsApp the moment your government appointment slip is ready.
                </span>
              </div>
            </div>
          </div>

          {/* Official ARN Banner (when assigned) */}
          {hasStaffFilingRef && (
            <div className="rounded-xl bg-emerald-500/10 border border-emerald-500/30 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs sm:text-sm">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="size-5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                <div>
                  <span className="font-bold text-emerald-950 dark:text-emerald-100 block">
                    Official Government Submission Number:
                  </span>
                  <span className="font-mono font-black text-emerald-700 dark:text-emerald-300 text-base sm:text-lg">
                    {caseData.submission_reference}
                  </span>
                </div>
              </div>
              <Badge tone="success" className="shrink-0 font-bold px-3 py-1 text-xs">
                ✓ Officially Registered
              </Badge>
            </div>
          )}

          {/* ── ACTIONS BAR ── */}
          <div className="pt-2 border-t flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2.5 w-full sm:w-auto">
              <Button
                onClick={handleDownload}
                disabled={downloading}
                className="bg-primary hover:bg-primary/90 text-primary-foreground font-bold px-5 h-10 text-xs gap-2 shadow-md w-full sm:w-auto"
              >
                {downloading ? (
                  <>
                    <Loader2 className="size-4 animate-spin" />
                    <span>Preparing Document...</span>
                  </>
                ) : (
                  <>
                    <Download className="size-4" />
                    <span>Download Application Copy (PDF)</span>
                  </>
                )}
              </Button>

              <Button
                variant="outline"
                onClick={handleRefreshClick}
                disabled={isRefreshing}
                className="h-10 text-xs font-semibold gap-1.5 w-full sm:w-auto text-muted-foreground hover:text-foreground"
              >
                <RefreshCw className={`size-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
                <span>Refresh Status</span>
              </Button>
            </div>

            <div className="text-xs text-muted-foreground text-center sm:text-right">
              <span>Status updates automatically in real-time</span>
            </div>
          </div>

          {/* ── MINIMAL HELPLINE / SUPPORT BAR ── */}
          <div className="rounded-xl border border-primary/20 bg-primary/5 p-4 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2.5 text-center sm:text-left">
              <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/20 text-primary">
                <Phone className="size-4" />
              </div>
              <div>
                <span className="font-bold text-foreground block">
                  Have questions about your appointment or visa?
                </span>
                <span className="text-muted-foreground text-[11px]">
                  Our visa operations team is available {SUPPORT_CONFIG.hours}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2 w-full sm:w-auto shrink-0 justify-center">
              <a
                href={SUPPORT_CONFIG.telLink}
                className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-background border px-3 py-1.5 text-xs font-semibold text-foreground hover:bg-accent transition-colors shadow-2xs"
              >
                <Phone className="size-3 text-primary" />
                <span>{SUPPORT_CONFIG.phoneDisplay}</span>
              </a>

              <a
                href={SUPPORT_CONFIG.whatsappLink}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-[#25D366] hover:bg-[#20ba5a] text-white px-3 py-1.5 text-xs font-bold transition-colors shadow-2xs"
              >
                <MessageCircle className="size-3" />
                <span>WhatsApp</span>
              </a>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Live Portal Submission Bot Console */}
      <PortalBotConsole
        isOpen={botConsoleOpen}
        onClose={() => setBotConsoleOpen(false)}
        job={botJob}
        loading={botRunning}
        caseId={caseData.id}
        onJobUpdated={(updated) => {
          setBotJob(updated);
          if (updated.status === "succeeded") {
            toast.success(`Government registration captured: ${updated.portal_reference}`);
            if (onRefresh) onRefresh();
          }
        }}
        onRetry={handleRerunBot}
      />
    </div>
  );
}
