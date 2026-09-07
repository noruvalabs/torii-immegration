"use client";

import { useEffect, useRef, useState } from "react";
import { Check, ExternalLink, FileText, Clock, ShieldCheck, Search } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useLang } from "./i18n";
import { dictionary, type Dictionary } from "./dictionary";

type StepId = "intake" | "eligibility" | "checklist" | "forms" | "review" | "packet";

const STEP_ORDER: StepId[] = ["intake", "eligibility", "checklist", "forms", "review", "packet"];

const STEP_DURATION_MS = 3600;

const BADGE_TONES: Record<StepId, "default" | "success" | "warning"> = {
  intake: "default",
  eligibility: "default",
  checklist: "default",
  forms: "default",
  review: "warning",
  packet: "success",
};

function StepContent({ id, demo }: { id: StepId; demo: Dictionary["heroDemo"] }) {
  if (id === "intake") {
    return (
      <div className="animate-step-in space-y-2.5">
        <div className="flex items-center justify-between text-xs">
          <span className="font-medium text-muted-foreground">{demo.intake.question}</span>
          <span className="font-mono text-[11px] text-muted-foreground">Question 6 of 10</span>
        </div>
        <div className="rounded-md border border-border/80 bg-background/80 px-3.5 py-2.5 text-xs sm:text-sm">
          {demo.intake.prompt}
        </div>
        <div className="flex items-center justify-end">
          <div className="rounded-md bg-primary px-3.5 py-2 text-xs sm:text-sm font-medium text-primary-foreground shadow-sm">
            {demo.intake.answer}
          </div>
        </div>
        <div className="flex items-center gap-1.5 text-[11px] text-emerald-600 dark:text-emerald-400 font-medium pt-0.5">
          <Check className="size-3" />
          <span>Company verified with National Tax Agency · Sponsoring criteria met</span>
        </div>
      </div>
    );
  }

  if (id === "eligibility") {
    return (
      <div className="space-y-2.5">
        {demo.eligibility.checks.map((c, i) => (
          <div
            key={c}
            style={{ animationDelay: `${i * 120}ms` }}
            className="animate-step-in flex items-start gap-2.5 rounded-md border border-border/60 bg-background/50 p-2.5 text-xs sm:text-sm"
          >
            <Check className="mt-0.5 size-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
            <span className="text-foreground">{c}</span>
          </div>
        ))}
        <div className="flex items-center justify-between pt-1">
          <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400">
            {demo.eligibility.result}
          </span>
          <span className="text-[10px] text-muted-foreground font-mono">MOJ Standard 16-3</span>
        </div>
      </div>
    );
  }

  if (id === "checklist") {
    return (
      <div className="space-y-2">
        <div className="animate-step-in flex items-start gap-2.5 rounded-md border border-emerald-500/30 bg-emerald-500/5 p-2.5 sm:p-3">
          <Check className="mt-0.5 size-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
          <div className="min-w-0 flex-1">
            <p className="text-xs sm:text-sm font-medium text-foreground">{demo.checklist.coeTitle}</p>
            <p className="mt-0.5 text-[11px] text-muted-foreground">{demo.checklist.coeStatus}</p>
          </div>
          <span className="text-[10px] font-medium px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 shrink-0">
            Verified
          </span>
        </div>
        <div
          style={{ animationDelay: "120ms" }}
          className="animate-step-in flex items-start gap-2.5 rounded-md border border-border/80 bg-background/60 p-2.5 sm:p-3"
        >
          <Check className="mt-0.5 size-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
          <div className="min-w-0 flex-1">
            <p className="text-xs sm:text-sm font-medium text-foreground">{demo.checklist.employmentTitle}</p>
            <p className="mt-0.5 flex items-center gap-1 text-[11px] text-muted-foreground">
              {demo.checklist.employmentStatus}
              <ExternalLink className="size-3" />
            </p>
          </div>
          <span className="text-[10px] font-medium px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 shrink-0">
            Verified
          </span>
        </div>
      </div>
    );
  }

  if (id === "forms") {
    return (
      <div className="space-y-2">
        {demo.forms.fields.map((f, i) => (
          <div
            key={f.label}
            style={{ animationDelay: `${i * 120}ms` }}
            className="animate-step-in flex items-center justify-between gap-3 rounded-md border border-border/70 bg-background/70 px-3 py-2 text-xs sm:text-sm"
          >
            <span className="text-xs text-muted-foreground shrink-0">{f.label}</span>
            <span className="truncate font-medium text-foreground text-right">{f.value}</span>
          </div>
        ))}
        <div
          style={{ animationDelay: "360ms" }}
          className="animate-step-in flex items-center justify-between rounded-md border border-primary/25 bg-primary/5 px-3 py-2 text-xs"
        >
          <div className="flex items-center gap-2">
            <span className="font-mono font-semibold text-primary">MOJ-16-3</span>
            <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground font-mono">2026 Edition</span>
            <span className="text-[11px] text-muted-foreground">All 38 questions filled</span>
          </div>
          <span className="flex items-center gap-1 font-medium text-emerald-600 dark:text-emerald-400 text-xs">
            <Check className="size-3" /> {demo.forms.ready}
          </span>
        </div>
      </div>
    );
  }

  if (id === "review") {
    return (
      <div className="space-y-2">
        <p className="animate-step-in text-xs text-muted-foreground font-medium">{demo.review.checking}</p>
        {demo.review.checks.map((c, i) => (
          <div
            key={c}
            style={{ animationDelay: `${100 + i * 100}ms` }}
            className="animate-step-in flex items-start gap-2 rounded-md border border-border/60 bg-background/50 p-2 text-xs sm:text-sm"
          >
            <Check className="mt-0.5 size-3.5 shrink-0 text-emerald-600 dark:text-emerald-400" />
            <span className="text-muted-foreground">{c}</span>
          </div>
        ))}
        <div className="flex items-center justify-between pt-1">
          <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400">
            {demo.review.result}
          </span>
          <span className="text-[10px] text-muted-foreground font-medium">0 mistakes found</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="animate-step-in flex items-center gap-3 rounded-md border border-emerald-500/30 bg-background/80 p-3">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
          <FileText className="size-4" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-xs sm:text-sm font-semibold text-foreground">{demo.packet.filename}</p>
          <p className="mt-0.5 text-[11px] text-muted-foreground">{demo.packet.meta}</p>
        </div>
        <span className="inline-flex items-center gap-1 rounded bg-emerald-500/10 px-2 py-0.5 text-[11px] font-semibold text-emerald-600 dark:text-emerald-400">
          <Check className="size-3" /> Ready
        </span>
      </div>
      <div className="flex items-center justify-between text-[11px] text-muted-foreground px-1">
        <span>Includes ISA Official Application Form + Organization Sheets</span>
        <span className="font-mono">PDF &amp; Word Export</span>
      </div>
    </div>
  );
}

export function HeroDemo() {
  const { lang } = useLang();
  const t = dictionary[lang];
  const demo = t.heroDemo;

  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (paused) return;
    timerRef.current = setInterval(() => {
      setIndex((i) => (i + 1) % STEP_ORDER.length);
    }, STEP_DURATION_MS);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [paused]);

  const current = STEP_ORDER[index];
  const badgeTone = BADGE_TONES[current];
  const badgeText = demo.badges[current];

  return (
    <div className="relative">
      <div
        onMouseEnter={() => setPaused(true)}
        onMouseLeave={() => setPaused(false)}
        className="shadow-panel-lg rounded-2xl border border-border/70 bg-card/95 p-4 backdrop-blur-xl sm:p-5"
      >
        {/* Sleek Browser/App Chrome Header */}
        <div className="flex items-center justify-between border-b border-border/70 pb-3">
          <div className="flex items-center gap-2">
            <span className="size-2.5 rounded-full bg-red-400/80" />
            <span className="size-2.5 rounded-full bg-amber-400/80" />
            <span className="size-2.5 rounded-full bg-emerald-400/80" />
            <div className="ml-2 hidden sm:flex items-center gap-1.5 rounded border border-border/70 bg-background/60 px-2.5 py-0.5 text-[11px] text-muted-foreground font-mono">
              <Search className="size-2.5" />
              <span>app.torii.visa/{demo.caseId}</span>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="inline-flex items-center gap-1 rounded bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-600 dark:text-emerald-400">
              <span className="size-1 rounded-full bg-emerald-500 animate-pulse" />
              ISA 2026 Verified
            </span>
          </div>
        </div>

        {/* Case Metadata Bar */}
        <div className="mt-3 space-y-1">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-bold text-foreground">{demo.caseId}</span>
              <span className="rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-primary">
                Renewal
              </span>
            </div>
            <Badge
              tone={badgeTone === "default" ? undefined : badgeTone}
              className={cn("shrink-0 text-[11px]", badgeTone === "default" && "bg-primary/12 text-primary")}
            >
              {badgeText}
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground truncate">{demo.locale}</p>
        </div>

        {/* Statutory Filing Deadline Alert Banner */}
        <div className="mt-2.5 flex items-center justify-between rounded-md border border-amber-500/30 bg-amber-500/5 px-2.5 py-1.5 text-[11px] text-amber-700 dark:text-amber-300">
          <div className="flex items-center gap-1.5">
            <Clock className="size-3.5 shrink-0 text-amber-600 dark:text-amber-400" />
            <span>Filing window open: <strong>Sep 3 – Dec 2, 2026</strong></span>
          </div>
          <span className="text-[10px] font-medium text-amber-600/90 dark:text-amber-400/90 hidden sm:inline">
            Zero-day grace period
          </span>
        </div>

        {/* Interactive Step Tabs */}
        <div className="mt-3.5 grid grid-cols-3 sm:grid-cols-6 gap-1 text-xs">
          {STEP_ORDER.map((step, i) => (
            <button
              key={step}
              type="button"
              onClick={() => {
                setIndex(i);
                setPaused(true);
              }}
              className={cn(
                "rounded-md py-1.5 px-1 text-center text-[11px] sm:text-xs font-medium transition-all duration-150 border cursor-pointer truncate",
                i === index
                  ? "border-primary bg-primary text-primary-foreground shadow-sm"
                  : i < index
                    ? "border-border/60 bg-muted/40 text-foreground hover:bg-muted/80"
                    : "border-transparent text-muted-foreground hover:text-foreground hover:bg-muted/30",
              )}
            >
              {demo.steps[step]}
            </button>
          ))}
        </div>

        {/* Progress bar */}
        <div className="mt-2 h-0.5 w-full overflow-hidden rounded-full bg-muted">
          <div
            key={index}
            className="h-full rounded-full bg-primary/70"
            style={{
              animation: paused ? "none" : `hero-progress ${STEP_DURATION_MS}ms linear forwards`,
            }}
          />
        </div>

        {/* Step Dynamic Content View */}
        <div className="mt-3.5 min-h-37 border-t border-border/70 pt-3.5">
          <StepContent id={current} demo={demo} />
        </div>

        {/* Bottom Trust Badge */}
        <div className="mt-3.5 flex items-center justify-between border-t border-border/60 pt-2.5 text-[11px] text-muted-foreground">
          <div className="flex items-center gap-1.5 text-foreground/85 font-medium">
            <ShieldCheck className="size-3.5 text-emerald-600 dark:text-emerald-400" />
            <span>Official Japanese Ministry Forms</span>
          </div>
          <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-semibold">100% Guaranteed Format</span>
        </div>
      </div>
    </div>
  );
}
