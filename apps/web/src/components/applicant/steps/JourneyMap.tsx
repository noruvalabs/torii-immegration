"use client";

import { useEffect, useState } from "react";
import {
  AlertTriangle,
  Check,
  ChevronDown,
  Clock,
  ExternalLink,
  HelpCircle,
  Loader2,
  Scale,
  Sparkles,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  buildCasePlan,
  getCaseJourney,
  getCasePlan,
  type CaseJourney,
  type CasePlan,
  type JourneyExternalTask,
  type JourneyStage,
  type PlanAction,
} from "@/lib/api/cases";
import type { Case } from "./types";

type JourneyMapProps = {
  token: string | null;
  caseData: Case;
};

/** Short enough to sit inline next to a step title. */
const OWNER_LABEL: Record<JourneyStage["owner"], string> = {
  torii: "Torii",
  you: "You",
  authority: "The office",
  third_party: "Someone else",
};

function isArranged(task: JourneyExternalTask): boolean {
  return task.status === "gathered" || task.status === "uploaded";
}

/** A line the applicant can open when they want the detail, and ignore when they don't. */
function Disclosure({
  label,
  count,
  children,
}: {
  label: string;
  count?: number;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="inline-flex items-center gap-1 text-[11px] font-medium text-muted-foreground hover:text-foreground"
      >
        <ChevronDown className={`size-3 transition-transform ${open ? "" : "-rotate-90"}`} />
        {label}
        {count !== undefined && ` (${count})`}
      </button>
      {open && <div className="mt-2">{children}</div>}
    </div>
  );
}

function ActionList({
  actions,
  numbered = false,
}: {
  actions: PlanAction[];
  numbered?: boolean;
}) {
  return (
    <ol className="space-y-2">
      {actions.map((action, index) => (
        <li key={action.title} className="flex gap-2.5">
          <span
            className={`mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold ${
              numbered
                ? "bg-primary/10 text-primary"
                : "border border-dashed border-border text-muted-foreground"
            }`}
          >
            {index + 1}
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-xs font-semibold leading-snug text-foreground">{action.title}</p>
            {action.detail && (
              <p className="mt-0.5 text-[11px] leading-relaxed text-muted-foreground">
                {action.detail}
              </p>
            )}
            {action.lead_time && (
              <p className="mt-1 inline-flex items-center gap-1 text-[10px] text-[var(--color-warning)]">
                <Clock className="size-3" /> {action.lead_time}
              </p>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}

function PlanView({ plan }: { plan: CasePlan }) {
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <p className="max-w-2xl text-xs font-medium leading-relaxed text-foreground">
          {plan.headline}
        </p>
        <Badge tone={plan.ready_to_file ? "success" : "warning"} className="shrink-0 text-[10px]">
          {plan.ready_to_file ? "Ready to file" : plan.time_to_ready || "Not ready yet"}
        </Badge>
      </div>

      {plan.start_now.length > 0 && (
        <div className="space-y-2">
          <p className="text-[11px] font-bold uppercase tracking-wider text-primary">Start today</p>
          <ActionList actions={plan.start_now} numbered />
        </div>
      )}

      {plan.then.length > 0 && (
        <div className="space-y-2 border-t pt-3">
          <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
            Then
          </p>
          <ActionList actions={plan.then} />
        </div>
      )}

      {plan.risks.length > 0 && (
        <div className="space-y-2 rounded-lg border border-[var(--color-warning)]/30 bg-[var(--color-warning)]/5 p-3">
          <p className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-[var(--color-warning)]">
            <AlertTriangle className="size-3" /> What gets this handed back
          </p>
          {plan.risks.map((risk) => (
            <div key={risk.title}>
              <p className="text-xs font-semibold text-foreground">{risk.title}</p>
              <p className="text-[11px] leading-relaxed text-muted-foreground">{risk.detail}</p>
            </div>
          ))}
        </div>
      )}

      {plan.questions.length > 0 && (
        <div className="space-y-1.5 border-t pt-3">
          <p className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
            <HelpCircle className="size-3" /> Torii could not work these out — only you can
          </p>
          {plan.questions.map((question) => (
            <p key={question} className="text-[11px] leading-relaxed text-foreground/85">
              • {question}
            </p>
          ))}
        </div>
      )}

      <p className="text-[10px] leading-relaxed text-muted-foreground">{plan.disclaimer}</p>
    </div>
  );
}

function ExternalTaskRow({ task }: { task: JourneyExternalTask }) {
  const arranged = isArranged(task);
  return (
    <div className="rounded-lg border bg-card p-3">
      <div className="flex items-start gap-2.5">
        <div
          className={`mt-0.5 flex size-4 shrink-0 items-center justify-center rounded-full ${
            arranged
              ? "bg-[var(--color-success)]/15 text-[var(--color-success)]"
              : "border border-dashed border-border"
          }`}
        >
          {arranged && <Check className="size-2.5" />}
        </div>
        <div className="min-w-0 flex-1 space-y-1">
          <p className="text-xs font-semibold leading-snug text-foreground">{task.title}</p>
          <p className="text-[11px] text-muted-foreground">
            From {task.arranged_with}
            {!task.is_required && " · only if it applies to you"}
          </p>
          <p className="inline-flex items-start gap-1.5 text-[11px] leading-relaxed text-foreground/80">
            <Clock className="mt-0.5 size-3 shrink-0 text-[var(--color-warning)]" />
            <span>{task.lead_time}</span>
          </p>
          <Disclosure label="What it has to show">
            <div className="space-y-1.5 text-[11px] leading-relaxed text-muted-foreground">
              {task.how_to_obtain && <p>{task.how_to_obtain}</p>}
              <p>{task.guidance}</p>
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 pt-0.5 text-[10px]">
                {task.options.map((option) =>
                  option.url ? (
                    <a
                      key={option.label}
                      href={option.url}
                      target="_blank"
                      rel="noopener noreferrer nofollow"
                      className="inline-flex items-center gap-1 font-medium text-primary hover:underline"
                    >
                      {option.label}
                      <ExternalLink className="size-2.5" />
                    </a>
                  ) : (
                    <span key={option.label}>{option.label}</span>
                  ),
                )}
              </div>
            </div>
          </Disclosure>
        </div>
      </div>
    </div>
  );
}

function StageList({ stages }: { stages: JourneyStage[] }) {
  return (
    <ol className="space-y-2.5">
      {stages.map((stage) => (
        <li key={stage.key} className="flex gap-2.5">
          <div
            className={`mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold ${
              stage.status === "done"
                ? "bg-[var(--color-success)]/15 text-[var(--color-success)]"
                : stage.status === "current"
                  ? "bg-primary text-primary-foreground"
                  : "border border-dashed border-border text-muted-foreground"
            }`}
          >
            {stage.status === "done" ? <Check className="size-3" /> : stage.order}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-xs font-semibold text-foreground">{stage.title}</p>
              {stage.owner !== "you" && (
                <Badge tone="muted" className="text-[10px]">
                  {OWNER_LABEL[stage.owner]}
                </Badge>
              )}
            </div>
            <p className="mt-0.5 text-[11px] leading-relaxed text-muted-foreground">
              {stage.detail}
            </p>
          </div>
        </li>
      ))}
    </ol>
  );
}

/**
 * One panel: the plan for this application, and the detail behind it.
 *
 * An earlier version listed all sixteen stages of the procedure. That is a diagram, not
 * advice — most of the rows describe something the applicant either already did or
 * cannot act on today. The plan leads instead: what to start now (ordered by the lead
 * times that actually decide the filing date), what follows, and what gets applications
 * handed back. The full step list and the third-party items stay one click away.
 */
export function JourneyMap({ token, caseData }: JourneyMapProps) {
  const caseId = caseData.id;
  const [journey, setJourney] = useState<CaseJourney | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [plan, setPlan] = useState<CasePlan | null>(null);
  const [planning, setPlanning] = useState(false);
  const [planError, setPlanError] = useState<string | null>(null);

  useEffect(() => {
    const activeToken =
      token || (typeof window !== "undefined" ? localStorage.getItem("torii_token") : null);
    if (!activeToken || !caseId) {
      // Never leave the panel spinning on a missing session — say so instead.
      setLoading(false);
      setError("Sign in again to see your plan.");
      return;
    }
    let cancelled = false;
    setLoading(true);
    // The plan is built once and kept on the case, so re-opening this step reads back
    // the same words the applicant saw last time instead of paying for them again.
    Promise.all([getCaseJourney(activeToken, caseId), getCasePlan(activeToken, caseId)])
      .then(([journeyData, planData]) => {
        if (cancelled) return;
        setJourney(journeyData);
        setPlan(planData.plan);
        setError(null);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Could not load your next steps.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token, caseId, caseData.status]);

  async function handleBuildPlan() {
    const activeToken =
      token || (typeof window !== "undefined" ? localStorage.getItem("torii_token") : null);
    if (!activeToken) return;
    setPlanning(true);
    setPlanError(null);
    try {
      const built = await buildCasePlan(activeToken, caseId);
      setPlan(built.plan);
    } catch (err) {
      setPlanError(err instanceof Error ? err.message : "Could not build your plan.");
    } finally {
      setPlanning(false);
    }
  }

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center gap-2 py-6 text-xs text-muted-foreground">
          <Loader2 className="size-4 animate-spin" /> Loading your case…
        </CardContent>
      </Card>
    );
  }

  if (error || !journey) {
    return (
      <Card>
        <CardContent className="flex items-start gap-2 py-5 text-xs text-muted-foreground">
          <AlertTriangle className="mt-0.5 size-4 shrink-0 text-[var(--color-warning)]" />
          <span>{error ?? "Your plan is not available for this case yet."}</span>
        </CardContent>
      </Card>
    );
  }

  const outstanding = journey.external_tasks.filter((task) => !isArranged(task));
  const facts = [journey.office, journey.filed_by, journey.fee_note].filter(Boolean);

  return (
    <Card className="border-primary/20">
      <CardContent className="space-y-4 p-5">
        <div className="flex flex-col gap-3 border-b pb-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-2.5">
            <Scale className="mt-0.5 size-5 shrink-0 text-primary" />
            <div>
              <h4 className="text-sm font-bold tracking-tight">Your plan from here</h4>
              <p className="text-[11px] leading-relaxed text-muted-foreground">
                {plan
                  ? `Built ${new Date(plan.generated_at).toLocaleDateString()} from your case as it stood then. Assembling the filing kit again rebuilds it.`
                  : "Torii reads your whole case — answers, open documents, what has to come from a bank or an airline — and tells you what to do next, the way an adviser would."}
              </p>
            </div>
          </div>
          {/* Built once. There is no rebuild button: a second plan from the same case
              says the same thing, and asking for it costs the applicant another wait. */}
          {!plan && (
            <Button
              onClick={() => void handleBuildPlan()}
              disabled={planning}
              className="shrink-0 px-3 py-1.5 text-xs font-semibold"
            >
              {planning ? (
                <Loader2 className="mr-1.5 size-3.5 animate-spin" />
              ) : (
                <Sparkles className="mr-1.5 size-3.5" />
              )}
              Build my plan
            </Button>
          )}
        </div>

        {planError && (
          <div className="rounded-md border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/10 p-2.5 text-xs text-[var(--color-danger)]">
            {planError}
          </div>
        )}

        {planning && !plan && (
          <div className="flex flex-col items-center gap-2 py-6 text-center">
            <Loader2 className="size-5 animate-spin text-primary" />
            <p className="text-xs font-semibold">Reading your case…</p>
            <p className="text-[11px] text-muted-foreground">
              Weighing your outstanding documents against their lead times.
            </p>
          </div>
        )}

        {plan ? (
          <PlanView plan={plan} />
        ) : (
          !planning && (
            <div className="rounded-lg border border-dashed bg-muted/20 p-4 text-center">
              <p className="text-xs font-semibold text-foreground">
                {outstanding.length > 0
                  ? `${outstanding.length} item(s) still have to come from somewhere else.`
                  : "Everything on your checklist is recorded."}
              </p>
              <p className="mx-auto mt-1 max-w-md text-[11px] leading-relaxed text-muted-foreground">
                Build the plan to see which of them to start today, what follows, and what gets
                applications like yours handed back at the counter.
              </p>
            </div>
          )
        )}

        <div className="flex flex-wrap items-center gap-x-5 gap-y-2 border-t pt-3">
          {journey.external_tasks.length > 0 && (
            <Disclosure label="Items to arrange elsewhere" count={journey.external_tasks.length}>
              <div className="grid gap-2 lg:grid-cols-2">
                {journey.external_tasks.map((task) => (
                  <ExternalTaskRow key={task.code} task={task} />
                ))}
              </div>
              <p className="mt-2 text-[10px] leading-relaxed text-muted-foreground">
                Named services are examples only — Torii is not affiliated with them and does not
                check what you book.
              </p>
            </Disclosure>
          )}
          <Disclosure label="Every step of the procedure" count={journey.stages.length}>
            <StageList stages={journey.stages} />
          </Disclosure>
        </div>

        {facts.length > 0 && (
          <p className="text-[11px] leading-relaxed text-muted-foreground">{facts.join(" · ")}</p>
        )}
      </CardContent>
    </Card>
  );
}
