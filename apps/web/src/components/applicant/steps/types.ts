import type {
  Case,
  CaseGuidance,
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

export type Step = "intake" | "eligibility" | "checklist" | "forms" | "review" | "packet";

export const STEPS: { key: Step; label: string }[] = [
  { key: "intake", label: "Intake" },
  { key: "eligibility", label: "Eligibility" },
  { key: "checklist", label: "Checklist" },
  { key: "forms", label: "Forms" },
  { key: "review", label: "Review" },
  { key: "packet", label: "Packet" },
];

export function phaseToStep(phase: string): Step {
  if (phase === "done") return "packet";
  if (phase === "blocked") return "intake";
  if (STEPS.some((s) => s.key === phase)) return phase as Step;
  return "intake";
}

export function citationUrl(citation: Record<string, unknown> | undefined): string | null {
  const url = citation?.url;
  return typeof url === "string" && url.startsWith("http") ? url : null;
}

export function citationVersion(citation: Record<string, unknown> | undefined): string | null {
  const v = citation?.source_version;
  return typeof v === "string" ? v : null;
}
