"use client";

import React from "react";
import {
  Globe,
  Building2,
  FileCheck2,
  CheckCircle2,
  UserCheck,
  MapPin,
  Sparkles,
  Info,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import type { TrackSummary, SubmissionTrack } from "@/lib/api/cases";

interface RouteClarityBannerProps {
  trackSummary?: TrackSummary | null;
  submissionTrack?: SubmissionTrack | string | null;
  jurisdictionCode?: string | null;
  className?: string;
  compact?: boolean;
}

export function RouteClarityBanner({
  trackSummary,
  submissionTrack,
  jurisdictionCode,
  className = "",
  compact = false,
}: RouteClarityBannerProps) {
  const code = (jurisdictionCode || "").toUpperCase();
  const track = (trackSummary?.track || submissionTrack || (code === "IN" ? "hybrid" : code === "SA" ? "digital" : "consular")) as SubmissionTrack;

  // Track-specific styling & configurations
  const config = React.useMemo(() => {
    switch (track) {
      case "digital":
        return {
          icon: Globe,
          border: "border-emerald-500/30",
          bg: "bg-emerald-500/5 dark:bg-emerald-950/20",
          tone: "success" as const,
          badgeBg: "border-emerald-500/30",
          accentColor: "text-emerald-600 dark:text-emerald-400",
          title: trackSummary?.title || "100% Online Automated Submission",
          badgeLabel: trackSummary?.badge_label || "Digital eVisa (100% Online)",
          headline: trackSummary?.headline || "We submit on the official government portal and pay the visa fee for you.",
          toriiRole:
            trackSummary?.torii_role ||
            "Torii enters your verified data into the official government portal, pays the statutory visa fee using virtual cards, and downloads your approved visa.",
          applicantRole:
            trackSummary?.applicant_role ||
            "Sit back and relax. Zero embassy or consulate visits required. Your approved eVisa will be delivered directly to your dashboard.",
          center: trackSummary?.submission_center || "Official Government eVisa Portal",
          requiresInPerson: false,
        };
      case "hybrid":
        return {
          icon: Building2,
          border: "border-amber-500/30",
          bg: "bg-amber-500/5 dark:bg-amber-950/20",
          tone: "warning" as const,
          badgeBg: "border-amber-500/30",
          accentColor: "text-amber-600 dark:text-amber-400",
          title: trackSummary?.title || "Online Portal Filing & Appointment Dossier",
          badgeLabel: trackSummary?.badge_label || "Hybrid (Online Form + Center Drop-Off)",
          headline:
            trackSummary?.headline ||
            (code === "IN"
              ? "We complete your official portal registration; you drop off your packet at IVAC."
              : "We register your online application; you attend your biometrics drop-off."),
          toriiRole:
            trackSummary?.torii_role ||
            "Torii completes your official portal registration, verifies all documents, and compiles your barcode-stamped, ready-to-print appointment dossier.",
          applicantRole:
            trackSummary?.applicant_role ||
            (code === "IN"
              ? "Take your printed Torii dossier kit to IVAC (Indian Visa Application Center) for biometric enrollment and passport drop-off."
              : "Take your printed Torii appointment kit to the official visa center for biometrics and passport submission."),
          center: trackSummary?.submission_center || (code === "IN" ? "IVAC (Indian Visa Application Center)" : "Visa Application Center"),
          requiresInPerson: true,
        };
      case "consular":
      default:
        return {
          icon: FileCheck2,
          border: "border-blue-500/30",
          bg: "bg-blue-500/5 dark:bg-blue-950/20",
          tone: "info" as const,
          badgeBg: "border-blue-500/30",
          accentColor: "text-blue-600 dark:text-blue-400",
          title: trackSummary?.title || "Walk-In Ready Official Consular Dossier",
          badgeLabel: trackSummary?.badge_label || "Consular / VFS Dossier Preparation",
          headline: trackSummary?.headline || "We prepare a flawless, rejection-proof packet for your in-person appointment.",
          toriiRole:
            trackSummary?.torii_role ||
            "Torii generates your official typewritten government forms, custom day-by-day travel itinerary, financial solvency binder, and consular cover letters.",
          applicantRole:
            trackSummary?.applicant_role ||
            (code === "JP"
              ? "Print your prepared dossier kit, sign where indicated, and attend your appointment at VFS Global / Embassy of Japan. Pay consular fee only on approval."
              : "Print your prepared dossier kit, sign where indicated, and attend your appointment at VFS Global or the Embassy consular section."),
          center: trackSummary?.submission_center || (code === "JP" ? "VFS Global / Embassy of Japan" : "VFS Global / Consular Section"),
          requiresInPerson: true,
        };
    }
  }, [track, trackSummary, code]);

  const Icon = config.icon;

  if (compact) {
    return (
      <div className={`flex items-center gap-2 text-xs ${className}`}>
        <Badge tone={config.tone} className={`${config.badgeBg} font-medium py-0.5 px-2`}>
          <Icon className="size-3 mr-1 shrink-0" />
          {config.badgeLabel}
        </Badge>
        <span className="text-muted-foreground truncate">{config.headline}</span>
      </div>
    );
  }

  return (
    <Card className={`overflow-hidden border ${config.border} ${config.bg} shadow-xs ${className}`}>
      <CardContent className="p-4 sm:p-5">
        {/* Header row */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 pb-3.5 border-b border-border/50">
          <div className="flex items-center gap-2.5">
            <div className={`p-2 rounded-lg bg-background border border-border/60 ${config.accentColor} shrink-0`}>
              <Icon className="size-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <Badge tone={config.tone} className={`${config.badgeBg} font-semibold text-[11px]`}>
                  {config.badgeLabel}
                </Badge>
                <span className="text-[11px] text-muted-foreground flex items-center gap-1">
                  <MapPin className="size-3 shrink-0" />
                  {config.center}
                </span>
              </div>
              <h3 className="font-semibold text-sm text-foreground mt-0.5">{config.title}</h3>
            </div>
          </div>
          <p className="text-xs text-muted-foreground sm:text-right max-w-sm">
            {config.headline}
          </p>
        </div>

        {/* Roles Breakdown: What We Do vs What You Do */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5 pt-3.5">
          {/* Torii's Responsibility */}
          <div className="flex items-start gap-2.5 p-3 rounded-md bg-background/70 border border-border/40">
            <div className="p-1.5 rounded-full bg-primary/10 text-primary shrink-0 mt-0.5">
              <Sparkles className="size-3.5" />
            </div>
            <div className="text-xs">
              <span className="font-semibold text-foreground flex items-center gap-1">
                <CheckCircle2 className="size-3 text-emerald-600 dark:text-emerald-400 inline" />
                What Torii Does For You:
              </span>
              <p className="text-muted-foreground mt-1 leading-relaxed">
                {config.toriiRole}
              </p>
            </div>
          </div>

          {/* Applicant's Responsibility */}
          <div className="flex items-start gap-2.5 p-3 rounded-md bg-background/70 border border-border/40">
            <div className="p-1.5 rounded-full bg-muted text-muted-foreground shrink-0 mt-0.5">
              <UserCheck className="size-3.5" />
            </div>
            <div className="text-xs">
              <span className="font-semibold text-foreground flex items-center gap-1">
                <Info className="size-3 text-primary inline" />
                What You Need To Do:
              </span>
              <p className="text-muted-foreground mt-1 leading-relaxed">
                {config.applicantRole}
              </p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

