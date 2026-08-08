"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  Check,
  FileSearch,
  Globe,
  Loader2,
  RotateCcw,
  Search,
  Send,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  createEscalation,
  getCaseGuidance,
  requestResearch,
  type CaseGuidance,
  type ResearchStepLog,
} from "@/lib/api/cases";

const POLL_MS = 2000;
const STALL_THRESHOLD_SEC = 120;

type ResearchStepProps = {
  caseId: number;
  token: string;
  onPhaseChange: (phase: string) => void;
};

type LocalStep = {
  key: string;
  label: string;
  detail: string;
  state: "done" | "active" | "pending";
};

/** Client-side yield timeline when the worker has not yet published steps. */
const FALLBACK_STAGES: { key: string; label: string; detail: string; afterSec: number }[] = [
  {
    key: "queued",
    label: "Queuing research job",
    detail: "Waiting for the official-source worker",
    afterSec: 0,
  },
  {
    key: "prepare",
    label: "Preparing destination research",
    detail: "Matching jurisdiction, visa type, and residence profile",
    afterSec: 3,
  },
  {
    key: "search",
    label: "Searching official government sources",
    detail: "Looking up published eligibility and document guidance",
    afterSec: 8,
  },
  {
    key: "discover",
    label: "Reviewing official pages",
    detail: "Collecting cited government pages for this route",
    afterSec: 18,
  },
  {
    key: "fetch",
    label: "Reading government page content",
    detail: "Extracting the sections that apply to applicants",
    afterSec: 28,
  },
  {
    key: "extract",
    label: "Building eligibility rules and document list",
    detail: "Structuring intake questions and form mappings",
    afterSec: 40,
  },
  {
    key: "validate",
    label: "Checking sources and packaging results",
    detail: "Ensuring every item has an official citation",
    afterSec: 55,
  },
];

function* yieldFallbackSteps(elapsedSec: number): Generator<LocalStep> {
  for (let i = 0; i < FALLBACK_STAGES.length; i++) {
    const stage = FALLBACK_STAGES[i]!;
    const next = FALLBACK_STAGES[i + 1];
    let state: LocalStep["state"] = "pending";
    if (elapsedSec >= stage.afterSec) {
      state = next && elapsedSec >= next.afterSec ? "done" : "active";
    }
    yield {
      key: stage.key,
      label: stage.label,
      detail: stage.detail,
      state,
    };
  }
}

function mapServerSteps(steps: ResearchStepLog[], running: boolean): LocalStep[] {
  if (steps.length === 0) return [];
  return steps.map((s, i) => ({
    key: s.key,
    label: s.label,
    detail: s.detail,
    state: i < steps.length - 1 ? "done" : running ? "active" : "done",
  }));
}

function stageIcon(key: string, state: LocalStep["state"]) {
  if (state === "done") {
    return <Check className="size-3.5 text-[var(--color-success)]" />;
  }
  if (state === "active") {
    return <Loader2 className="size-3.5 animate-spin text-primary" />;
  }
  if (key.includes("search") || key.includes("discover")) {
    return <Search className="size-3.5 text-muted-foreground/50" />;
  }
  if (key.includes("fetch") || key.includes("read")) {
    return <Globe className="size-3.5 text-muted-foreground/50" />;
  }
  if (key.includes("extract") || key.includes("validate")) {
    return <FileSearch className="size-3.5 text-muted-foreground/50" />;
  }
  return <Sparkles className="size-3.5 text-muted-foreground/50" />;
}

export function ResearchStep({ caseId, token, onPhaseChange }: ResearchStepProps) {
  const [guidance, setGuidance] = useState<CaseGuidance | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [escalating, setEscalating] = useState(false);
  const [escalated, setEscalated] = useState(false);
  const [escalationMessage, setEscalationMessage] = useState("");
  const [escalationError, setEscalationError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const startedAt = useRef<number>(Date.now());
  const lastServerStepAt = useRef<number>(Date.now());

  useEffect(() => {
    const id = setInterval(() => {
      setElapsed(Math.round((Date.now() - startedAt.current) / 1000));
    }, 500);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    let stopped = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function poll() {
      try {
        const g = await getCaseGuidance(token, caseId);
        if (stopped) return;
        setGuidance(g);
        if (g.phase !== "research") {
          onPhaseChange(g.phase);
          return;
        }
        if ((g.research_steps?.length ?? 0) > 0) {
          lastServerStepAt.current = Date.now();
        }
      } catch {
        // transient network error; keep polling
      }
      timer = setTimeout(poll, POLL_MS);
    }

    void poll();
    return () => {
      stopped = true;
      if (timer) clearTimeout(timer);
    };
  }, [caseId, token, onPhaseChange, refreshKey]);

  const failed = guidance?.blocked_reason === "research_failed";
  const researchStatus = guidance?.research_status ?? (failed ? "failed" : "running");
  const serverSteps = guidance?.research_steps ?? [];

  const displaySteps = useMemo(() => {
    if (failed) {
      return FALLBACK_STAGES.map((s) => ({
        key: s.key,
        label: s.label,
        detail: s.detail,
        state: "done" as const,
      }));
    }
    if (serverSteps.length > 0) {
      return mapServerSteps(serverSteps, researchStatus === "running" || researchStatus === "queued");
    }
    return Array.from(yieldFallbackSteps(elapsed));
  }, [serverSteps, researchStatus, elapsed, failed]);

  const doneCount = displaySteps.filter((s) => s.state === "done").length;
  const totalCount = Math.max(displaySteps.length, 1);
  const pct = Math.min(95, Math.round((doneCount / totalCount) * 100) + (researchStatus === "running" ? 4 : 0));
  const active = displaySteps.find((s) => s.state === "active") ?? displaySteps[displaySteps.length - 1];

  const stalled =
    !failed &&
    researchStatus !== "completed" &&
    elapsed >= STALL_THRESHOLD_SEC &&
    Date.now() - lastServerStepAt.current >= STALL_THRESHOLD_SEC * 1000;

  async function retryResearch() {
    setEscalationError(null);
    startedAt.current = Date.now();
    lastServerStepAt.current = Date.now();
    setElapsed(0);
    try {
      await requestResearch(token, caseId);
      setRefreshKey((k) => k + 1);
    } catch (e) {
      setEscalationError(e instanceof Error ? e.message : "Could not restart research");
    }
  }

  async function handleEscalate() {
    setEscalating(true);
    setEscalationError(null);
    try {
      await createEscalation(token, caseId, {
        reason: "research_failed",
        message: escalationMessage.trim() || "Live research failed for this scope.",
        consent_to_share: true,
      });
      setEscalated(true);
    } catch (e) {
      setEscalationError(e instanceof Error ? e.message : "Escalation failed");
    } finally {
      setEscalating(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-sm font-medium text-muted-foreground">Researching this application</h3>
        <p className="mt-1 text-xs text-muted-foreground">
          No seeded guide exists for this scope, so we research official government requirements
          live — every item must keep an official source citation.
        </p>
      </div>

      {failed ? (
        <div className="space-y-4">
          <div className="flex items-start gap-3 rounded-[var(--radius)] border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/5 p-4">
            <AlertTriangle className="mt-0.5 size-4 shrink-0 text-[var(--color-danger)]" />
            <div className="flex-1">
              <p className="text-sm font-medium">We could not research this case automatically</p>
              <p className="mt-1 text-xs text-muted-foreground">
                The official sources could not be reached. You can retry, or ask our team to build
                this guide manually.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button variant="outline" onClick={() => void retryResearch()}>
              <RotateCcw className="size-4" />
              Retry research
            </Button>
          </div>

          {!escalated ? (
            <div className="space-y-3 rounded-[var(--radius)] border p-4">
              <p className="text-sm font-medium">Request manual help</p>
              <textarea
                value={escalationMessage}
                onChange={(e) => setEscalationMessage(e.target.value)}
                placeholder="Anything specific you are applying for? (optional)"
                rows={3}
                className="w-full rounded-[var(--radius)] border bg-transparent px-3 py-2 text-sm outline-none focus:border-primary"
              />
              {escalationError && (
                <p className="text-xs text-[var(--color-danger)]">{escalationError}</p>
              )}
              <Button onClick={() => void handleEscalate()} disabled={escalating}>
                {escalating ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
                Send to our team
              </Button>
            </div>
          ) : (
            <div className="rounded-[var(--radius)] border border-[var(--color-success)]/30 bg-[var(--color-success)]/5 p-4">
              <p className="text-sm font-medium">Request sent</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Our team has been notified and will build the guide for you.
              </p>
            </div>
          )}
        </div>
      ) : stalled ? (
        <div className="space-y-4">
          <div className="flex items-start gap-3 rounded-[var(--radius)] border border-[var(--color-warning)]/30 bg-[var(--color-warning)]/5 p-4">
            <AlertTriangle className="mt-0.5 size-4 shrink-0 text-[var(--color-warning)]" />
            <div className="flex-1">
              <p className="text-sm font-medium">Research seems to be taking longer than expected</p>
              <p className="mt-1 text-xs text-muted-foreground">
                The research has been running for over {Math.floor(elapsed / 60)}m {elapsed % 60}s.
                You can retry or request manual help from our team.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button variant="outline" onClick={() => void retryResearch()}>
              <RotateCcw className="size-4" />
              Retry research
            </Button>
          </div>

          {!escalated ? (
            <div className="space-y-3 rounded-[var(--radius)] border p-4">
              <p className="text-sm font-medium">Request manual help</p>
              <textarea
                value={escalationMessage}
                onChange={(e) => setEscalationMessage(e.target.value)}
                placeholder="Anything specific you are applying for? (optional)"
                rows={3}
                className="w-full rounded-[var(--radius)] border bg-transparent px-3 py-2 text-sm outline-none focus:border-primary"
              />
              {escalationError && (
                <p className="text-xs text-[var(--color-danger)]">{escalationError}</p>
              )}
              <Button onClick={() => void handleEscalate()} disabled={escalating}>
                {escalating ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
                Send to our team
              </Button>
            </div>
          ) : (
            <div className="rounded-[var(--radius)] border border-[var(--color-success)]/30 bg-[var(--color-success)]/5 p-4">
              <p className="text-sm font-medium">Request sent</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Our team has been notified and will build the guide for you.
              </p>
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-5">
          {/* Current yield headline */}
          <div className="rounded-[var(--radius)] border border-primary/25 bg-primary/5 p-4">
            <div className="flex items-start gap-3">
              <div className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full bg-primary/15">
                <Loader2 className="size-4 animate-spin text-primary" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-semibold uppercase tracking-wider text-primary">
                  Now working on
                </p>
                <p className="mt-1 text-sm font-medium text-foreground">
                  {active?.label ?? guidance?.title ?? "Researching official sources"}
                </p>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {active?.detail ||
                    guidance?.instruction ||
                    "Checking government portals and published requirements."}
                </p>
              </div>
              <div className="shrink-0 text-right">
                <p className="font-mono text-xs text-muted-foreground">{elapsed}s</p>
                <p className="text-[10px] uppercase tracking-wide text-muted-foreground/70">
                  {researchStatus}
                </p>
              </div>
            </div>

            <div className="mt-4">
              <div className="mb-1.5 flex items-center justify-between text-[11px] text-muted-foreground">
                <span>Research progress</span>
                <span>{pct}%</span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-primary transition-all duration-700 ease-out"
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          </div>

          {/* Yielded process list */}
          <ol className="space-y-0">
            {displaySteps.map((step, i) => {
              const isLast = i === displaySteps.length - 1;
              return (
                <li key={`${step.key}-${i}`} className="flex gap-3">
                  <div className="flex flex-col items-center">
                    <div
                      className={`flex size-7 shrink-0 items-center justify-center rounded-full border ${
                        step.state === "done"
                          ? "border-[var(--color-success)]/40 bg-[var(--color-success)]/10"
                          : step.state === "active"
                            ? "border-primary/50 bg-primary/10"
                            : "border-border bg-muted/40"
                      }`}
                    >
                      {stageIcon(step.key, step.state)}
                    </div>
                    {!isLast && (
                      <div
                        className={`my-1 w-px flex-1 min-h-5 ${
                          step.state === "done" ? "bg-[var(--color-success)]/30" : "bg-border"
                        }`}
                      />
                    )}
                  </div>
                  <div className={`pb-4 ${step.state === "pending" ? "opacity-50" : ""}`}>
                    <p
                      className={`text-sm ${
                        step.state === "active" ? "font-medium text-foreground" : "text-foreground/90"
                      }`}
                    >
                      {step.label}
                    </p>
                    {step.detail && (
                      <p className="mt-0.5 text-xs text-muted-foreground">{step.detail}</p>
                    )}
                  </div>
                </li>
              );
            })}
          </ol>

          <p className="text-center text-[11px] text-muted-foreground">
            This usually takes under a minute. Steps update live as sources are checked.
          </p>
        </div>
      )}
    </div>
  );
}
