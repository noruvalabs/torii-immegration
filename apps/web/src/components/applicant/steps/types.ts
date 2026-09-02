import type {
  Case,
  CaseGuidance,
  CaseDeadlines,
  IntakeState,
  IntakeQuestion,
  EligibilityResult,
  ChecklistItem,
  GeneratedForm,
  ReviewResult,
  Document,
} from "@/lib/api/cases";
import type { User } from "@/lib/api/auth";
import type { OCRResult, DocumentType } from "@/lib/api/ocr";
import type { WalletDocument } from "@/lib/api/wallet";

export type {
  Case,
  CaseGuidance,
  CaseDeadlines,
  IntakeState,
  IntakeQuestion,
  EligibilityResult,
  ChecklistItem,
  GeneratedForm,
  ReviewResult,
  Document,
  User,
  OCRResult,
  DocumentType,
  WalletDocument,
};

export type Step = "intake" | "eligibility" | "checklist" | "forms" | "review" | "packet" | "research";

export const STEPS: { key: Step; label: string }[] = [
  { key: "intake", label: "Intake" },
  { key: "eligibility", label: "Eligibility" },
  { key: "checklist", label: "Checklist" },
  { key: "forms", label: "Forms" },
  { key: "review", label: "Review" },
  { key: "packet", label: "Packet" },
];

/** Workflow order for phase gating (research is a pre-intake state). */
export const STEP_ORDER: Step[] = [
  "research",
  "intake",
  "eligibility",
  "checklist",
  "forms",
  "review",
  "packet",
];

export function phaseToStep(phase: string): Step {
  if (phase === "done") return "packet";
  if (phase === "blocked") return "intake";
  if (phase === "research") return "research";
  if (STEPS.some((s) => s.key === phase)) return phase as Step;
  return "intake";
}

/** Highest step the applicant may open, based on server guidance phase. */
export function maxReachableStep(phase: string): Step {
  if (phase === "done") return "packet";
  if (phase === "blocked") return "intake";
  return phaseToStep(phase);
}

export function stepIndex(step: Step): number {
  return STEP_ORDER.indexOf(step);
}

/** True when the step can be visited by the applicant. */
export function canVisitStep(target: Step, guidancePhase: string): boolean {
  if (guidancePhase === "research") return target === "research";
  if (guidancePhase === "blocked") return target === "intake";
  return stepIndex(target) >= stepIndex("intake");
}

export function nextWorkflowStep(step: Step): Step | null {
  const i = stepIndex(step);
  if (i < 0 || i >= STEP_ORDER.length - 1) return null;
  const next = STEP_ORDER[i + 1];
  return next === undefined || next === "research" ? null : next;
}

export function citationUrl(citation: Record<string, unknown> | undefined): string | null {
  const url = citation?.url;
  return typeof url === "string" && url.startsWith("http") ? url : null;
}

export function citationVersion(citation: Record<string, unknown> | undefined): string | null {
  const v = citation?.source_version;
  return typeof v === "string" ? v : null;
}
