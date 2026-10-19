"use client";

import { useEffect, useState } from "react";
import {
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
  Lock,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { SUPPORT_CONFIG } from "@/lib/support";
import type { Case } from "./types";

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
  const [copiedRef, setCopiedRef] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

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
    navigator.clipboard.writeText(caseData.reference);
    setCopiedRef(true);
    toast.success("Case reference copied to clipboard");
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

  return (
    <Card className="border-2 border-emerald-500/30 bg-gradient-to-b from-card via-card to-emerald-500/[0.03] shadow-md overflow-hidden">
      <CardContent className="p-5 sm:p-7 space-y-6">
        {/* Top Celebration & Staff Queue Banner */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border/80 pb-6">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2.5">
              <span className="flex size-8 items-center justify-center rounded-xl bg-emerald-500 text-white shadow-md shadow-emerald-500/20">
                <CheckCircle2 className="size-5" />
              </span>
              <h3 className="text-lg sm:text-xl font-extrabold text-foreground tracking-tight">
                Visa Application Request Successful!
              </h3>
              <Badge tone="success" className="text-[11px] font-bold px-2.5 py-0.5 uppercase tracking-wide">
                Assigned to Staff
              </Badge>
            </div>
            <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed pl-10 sm:max-w-2xl">
              All your information has been received. Our dedicated operations team is now handling your official government visa submission and fee payment on your behalf.
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0 pl-10 sm:pl-0">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefreshClick}
              disabled={isRefreshing}
              className="text-xs h-9 gap-1.5 font-medium"
            >
              <RefreshCw className={`size-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
              Refresh Status
            </Button>
          </div>
        </div>

        {/* 3 Concierge Process Stages */}
        <div className="grid gap-4 sm:gap-5 md:grid-cols-3">
          {/* ── Stage 1: Info & Payment Received (Completed) ── */}
          <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-5 flex flex-col justify-between space-y-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="flex size-8 items-center justify-center rounded-lg bg-emerald-500 text-white font-bold text-xs shadow-xs">
                  ✓
                </span>
                <Badge tone="success" className="text-[10px] font-bold">
                  Completed
                </Badge>
              </div>

              <div>
                <h4 className="text-sm sm:text-base font-bold text-foreground">
                  1. Information &amp; Payment Received
                </h4>
                <p className="mt-1.5 text-xs text-muted-foreground leading-relaxed">
                  Your personal particulars, passport information, and service charge are confirmed and verified.
                </p>
              </div>
            </div>

            <div className="pt-2 border-t border-emerald-500/20 flex items-center justify-between text-[11px] text-muted-foreground">
              <span>Status:</span>
              <span className="font-semibold text-emerald-600 dark:text-emerald-400">Verified &amp; Locked</span>
            </div>
          </div>

          {/* ── Stage 2: Staff Submitting on Gov Portal (Active In Progress) ── */}
          <div className="rounded-xl border-2 border-primary bg-primary/[0.04] p-5 flex flex-col justify-between space-y-4 shadow-sm relative ring-2 ring-primary/20">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground font-bold text-xs shadow-xs">
                  2
                </span>
                <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-bold text-primary animate-pulse">
                  <Clock className="size-3" /> In Progress
                </span>
              </div>

              <div>
                <h4 className="text-sm sm:text-base font-bold text-foreground flex items-center gap-1.5">
                  <ShieldCheck className="size-4.5 text-primary shrink-0" />
                  Staff Government Portal Filing
                </h4>
                <p className="mt-1.5 text-xs text-muted-foreground leading-relaxed">
                  Our operations staff is logging into the official {destinationName} visa portal, entering your full dossier, and paying the government fee on your behalf.
                </p>
              </div>
            </div>

            <div className="pt-2 border-t border-primary/20 flex items-center justify-between text-[11px]">
              <span className="text-muted-foreground">Action required by you:</span>
              <span className="font-bold text-primary">None (Please wait)</span>
            </div>
          </div>

          {/* ── Stage 3: Official Appointment & Stamped Slip (Next) ── */}
          <div className="rounded-xl border border-border/80 bg-muted/20 p-5 flex flex-col justify-between space-y-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="flex size-8 items-center justify-center rounded-lg bg-muted text-muted-foreground font-bold text-xs">
                  3
                </span>
                <Badge tone="default" className="text-[10px] font-semibold">
                  Upcoming
                </Badge>
              </div>

              <div>
                <h4 className="text-sm sm:text-base font-bold text-foreground flex items-center gap-1.5">
                  <Calendar className="size-4 text-muted-foreground shrink-0" />
                  Appointment Slip &amp; Dossier
                </h4>
                <p className="mt-1.5 text-xs text-muted-foreground leading-relaxed">
                  As soon as staff filing completes, you will receive your official government Web File / ARN #, biometric appointment slip, and stamped PDF packet.
                </p>
              </div>
            </div>

            <div className="pt-2 border-t border-border/50 flex items-center justify-between text-[11px] text-muted-foreground">
              <span>Delivery mode:</span>
              <span className="font-semibold text-foreground">Online &amp; WhatsApp</span>
            </div>
          </div>
        </div>

        {/* Staff Filing Status / Official ARN Banner */}
        <div className="rounded-xl border bg-card p-4 sm:p-5 space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border/70">
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Torii Concierge Case Reference
              </p>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="font-mono text-base font-black text-foreground">
                  {caseData.reference}
                </span>
                <button
                  type="button"
                  onClick={handleCopyRef}
                  className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                  title="Copy Reference"
                >
                  {copiedRef ? <Check className="size-3.5 text-emerald-500" /> : <Copy className="size-3.5" />}
                </button>
              </div>
            </div>

            <div className="text-left sm:text-right">
              <span className="text-xs text-muted-foreground block">Estimated Completion Time</span>
              <span className="text-xs sm:text-sm font-bold text-emerald-600 dark:text-emerald-400">
                Within 2 – 6 Business Hours
              </span>
            </div>
          </div>

          {hasStaffFilingRef ? (
            <div className="rounded-lg bg-emerald-500/10 border border-emerald-500/30 p-3.5 flex items-center justify-between gap-3 text-xs sm:text-sm">
              <div className="flex items-center gap-2.5">
                <CheckCircle2 className="size-5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                <div>
                  <span className="font-bold text-emerald-950 dark:text-emerald-100 block">
                    Official Government Submission Number:
                  </span>
                  <span className="font-mono font-black text-emerald-700 dark:text-emerald-300 text-sm sm:text-base">
                    {caseData.submission_reference}
                  </span>
                </div>
              </div>
              <Badge tone="success" className="shrink-0 font-bold">
                Officially Filed
              </Badge>
            </div>
          ) : (
            <div className="rounded-lg bg-muted/40 p-3.5 flex items-start sm:items-center gap-3 text-xs text-muted-foreground">
              <Sparkles className="size-4 text-primary shrink-0 mt-0.5 sm:mt-0" />
              <div>
                <span className="font-semibold text-foreground">You do not need to visit any other website. </span>
                <span>Our staff is processing your official portal filing. We will notify you via SMS and WhatsApp as soon as your government appointment slip is ready.</span>
              </div>
            </div>
          )}
        </div>

        {/* Direct Contact & Call Helpline Section */}
        <div className="rounded-xl border-2 border-primary/20 bg-gradient-to-r from-primary/10 via-card to-background p-4 sm:p-5 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="flex size-7 items-center justify-center rounded-lg bg-primary/20 text-primary">
                <Phone className="size-4" />
              </span>
              <h4 className="text-sm sm:text-base font-bold text-foreground">
                Have a Query? Call Our Visa Team Directly
              </h4>
            </div>
            <p className="text-xs text-muted-foreground pl-9 max-w-xl">
              Our operations officers are ready to answer any questions regarding hospital referrals, urgent processing, or appointment dates.
            </p>
            <div className="flex flex-wrap items-center gap-3 pl-9 pt-0.5 text-[11px] text-muted-foreground">
              <span className="flex items-center gap-1 font-medium">
                <Clock className="size-3 text-primary" /> {SUPPORT_CONFIG.hours}
              </span>
              <span>·</span>
              <span className="text-emerald-600 dark:text-emerald-400 font-semibold">
                {SUPPORT_CONFIG.emergencySupport}
              </span>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2.5 w-full md:w-auto shrink-0 pl-9 md:pl-0">
            <a
              href={SUPPORT_CONFIG.telLink}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-xs font-bold text-primary-foreground shadow-md hover:bg-primary/90 transition-all flex-1 md:flex-initial"
            >
              <Phone className="size-4" />
              <span>Call: {SUPPORT_CONFIG.phoneDisplay}</span>
            </a>

            <a
              href={SUPPORT_CONFIG.whatsappLink}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-[#25D366] hover:bg-[#20ba5a] text-white px-4 py-2.5 text-xs font-bold shadow-md transition-all flex-1 md:flex-initial"
            >
              <MessageCircle className="size-4" />
              <span>WhatsApp Us</span>
            </a>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
