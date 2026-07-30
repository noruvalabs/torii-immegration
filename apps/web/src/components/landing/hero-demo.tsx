"use client";

import { useEffect, useRef, useState } from "react";
import { Check, ExternalLink, FileText } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useLang } from "./i18n";
import { dictionary, type Dictionary } from "./dictionary";

type StepId = "intake" | "eligibility" | "checklist" | "forms" | "review" | "packet";

const STEP_ORDER: StepId[] = ["intake", "eligibility", "checklist", "forms", "review", "packet"];

const STEP_DURATION_MS = 3200;

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
        <p className="text-xs font-medium text-muted-foreground">{demo.intake.question}</p>
        <p className="rounded-[var(--radius)] border bg-background px-3 py-2 text-sm">{demo.intake.prompt}</p>
        <p className="ml-auto w-fit rounded-[var(--radius)] bg-primary px-3 py-2 text-sm font-medium text-primary-foreground">
          {demo.intake.answer}
        </p>
      </div>
    );
  }

  if (id === "eligibility") {
    return (
      <div className="space-y-2">
        {demo.eligibility.checks.map((c, i) => (
          <div
            key={c}
            style={{ animationDelay: `${i * 140}ms` }}
            className="animate-step-in flex items-start gap-2.5 text-sm"
          >
            <Check className="mt-0.5 size-4 shrink-0 text-[var(--color-success)]" />
            <span className="text-muted-foreground">{c}</span>
          </div>
        ))}
        <p className="pt-1 text-sm font-medium text-[var(--color-success)]">{demo.eligibility.result}</p>
      </div>
    );
  }

  if (id === "checklist") {
    return (
      <div className="space-y-2.5">
        <div className="animate-step-in flex items-start gap-2.5 rounded-[var(--radius)] border border-[var(--color-success)]/25 bg-[var(--color-success)]/5 p-3">
          <Check className="mt-0.5 size-4 shrink-0 text-[var(--color-success)]" />
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium">{demo.checklist.coeTitle}</p>
            <p className="mt-0.5 text-xs text-muted-foreground">{demo.checklist.coeStatus}</p>
          </div>
        </div>
        <div
          style={{ animationDelay: "140ms" }}
          className="animate-step-in flex items-start gap-2.5 rounded-[var(--radius)] border p-3"
        >
          <div className="mt-0.5 size-4 shrink-0 rounded border border-muted-foreground/30" />
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium">{demo.checklist.employmentTitle}</p>
            <p className="mt-0.5 flex items-center gap-1 text-xs text-muted-foreground">
              {demo.checklist.employmentStatus}
              <ExternalLink className="size-3" />
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (id === "forms") {
    return (
      <div className="space-y-2.5">
        {demo.forms.fields.map((f, i) => (
          <div
            key={f.label}
            style={{ animationDelay: `${i * 140}ms` }}
            className="animate-step-in flex items-center justify-between gap-3 rounded-[var(--radius)] border bg-background px-3 py-2 text-sm"
          >
            <span className="text-xs text-muted-foreground">{f.label}</span>
            <span className="truncate font-medium">{f.value}</span>
          </div>
        ))}
        <div
          style={{ animationDelay: "420ms" }}
          className="animate-step-in flex items-center gap-2 rounded-[var(--radius)] border bg-background px-3 py-2 text-xs"
        >
          <span className="font-mono font-semibold">COE-7</span>
          <span className="rounded-full bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">v2024.1</span>
          <span className="ml-auto flex items-center gap-1 text-[var(--color-success)]">
            <Check className="size-3" /> {demo.forms.ready}
          </span>
        </div>
      </div>
    );
  }

  if (id === "review") {
    return (
      <div className="space-y-2">
        <p className="animate-step-in text-xs text-muted-foreground">{demo.review.checking}</p>
        {demo.review.checks.map((c, i) => (
          <div
            key={c}
            style={{ animationDelay: `${140 + i * 140}ms` }}
            className="animate-step-in flex items-start gap-2.5 text-sm"
          >
            <Check className="mt-0.5 size-4 shrink-0 text-[var(--color-success)]" />
            <span className="text-muted-foreground">{c}</span>
          </div>
        ))}
        <p style={{ animationDelay: "420ms" }} className="animate-step-in pt-1 text-sm font-medium">
          {demo.review.result}
        </p>
      </div>
    );
  }

  return (
    <div className="animate-step-in flex items-center gap-3 rounded-[var(--radius)] border bg-background p-3">
      <span className="flex size-9 shrink-0 items-center justify-center rounded-[var(--radius)] bg-primary/10 text-primary">
        <FileText className="size-4" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{demo.packet.filename}</p>
        <p className="mt-0.5 text-xs text-muted-foreground">{demo.packet.meta}</p>
      </div>
      <Check className="size-4 shrink-0 text-[var(--color-success)]" />
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
        className="rounded-[var(--radius-lg)] border bg-card p-5 shadow-[0_1px_0_0_rgba(0,0,0,0.02),0_24px_60px_-25px_rgba(0,0,0,0.45)] sm:p-6"
      >
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="font-mono text-sm font-semibold">{demo.caseId}</p>
            <p className="mt-0.5 text-xs text-muted-foreground">{demo.locale}</p>
          </div>
          <Badge
            tone={badgeTone === "default" ? undefined : badgeTone}
            className={cn("shrink-0", badgeTone === "default" && "animate-badge-pulse bg-primary/12 text-primary")}
          >
            {badgeText}
          </Badge>
        </div>

        <div className="mt-5 flex flex-wrap items-center gap-1 text-xs">
          {STEP_ORDER.map((step, i) => (
            <span key={step} className="flex items-center">
              {i > 0 && <span className="mx-1 text-muted-foreground/50">›</span>}
              <span
                className={
                  i < index
                    ? "rounded-full bg-primary px-2.5 py-1 font-medium text-primary-foreground transition-colors"
                    : i === index
                      ? "rounded-full border border-primary bg-primary/10 px-2.5 py-1 font-medium text-primary transition-colors"
                      : "rounded-full px-2.5 py-1 text-muted-foreground transition-colors"
                }
              >
                {demo.steps[step]}
              </span>
            </span>
          ))}
        </div>

        <div className="mt-1.5 h-0.5 w-full overflow-hidden rounded-full bg-muted">
          <div
            key={index}
            className="h-full rounded-full bg-primary/70"
            style={{
              animation: paused ? "none" : `hero-progress ${STEP_DURATION_MS}ms linear forwards`,
            }}
          />
        </div>

        <div className="mt-5 min-h-[132px] border-t pt-5">
          <StepContent id={current} demo={demo} />
        </div>
      </div>

      <div className="pointer-events-none absolute -bottom-4 -right-4 -z-10 size-full rounded-[var(--radius-lg)] border border-primary/20 sm:-bottom-5 sm:-right-5" />
    </div>
  );
}
