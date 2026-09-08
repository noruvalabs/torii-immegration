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

export const FIELD_KEY_ALIASES: Record<string, string[]> = {
  current_status: ["school_completed", "current_visa_status", "status_of_residence"],
  school_completed: ["current_status", "enrollment_status", "school_enrollment_status"],
  "employer.job_description": ["job_description"],
  job_description: ["employer.job_description", "role_description"],
  "employer.annual_salary_jpy": ["annual_salary_jpy", "monthly_salary", "salary"],
  annual_salary_jpy: ["employer.annual_salary_jpy", "monthly_salary", "salary"],
  "employer.name": ["employer_name", "company_name"],
  employer_name: ["employer.name", "company_name"],
  "applicant.full_name": ["full_name", "applicant_name"],
  "applicant.nationality": ["nationality", "citizenship", "country_of_citizenship"],
  "applicant.passport_number": ["passport_number", "passport_no"],
  "applicant.passport_expiry": ["passport_expiry", "passport_expiry_date"],
  passport_expiry_date: ["passport_expiry", "passport_expiry_date"],
  passport_expiry: ["passport_expiry_date"],
  "residence.card_number": ["residence_card_number", "zairyu_card_number"],
  "residence.card_expiry": ["residence_card_expiry", "zairyu_card_expiry"],
  "residence.address": ["registered_address_japan", "current_japan_address"],
  residence_card_expiry: ["residence.card_expiry", "zairyu_card_expiry"],
  residence_card_number: ["residence.card_number", "zairyu_card_number"],
  registered_address_japan: ["residence.address"],
};

export function findQuestionByKey(
  questions: IntakeQuestion[] = [],
  key?: string | null
): IntakeQuestion | undefined {
  if (!key) return undefined;

  // 1. Exact match
  let hit = questions.find((q) => q.key === key);
  if (hit) return hit;

  // 2. Unprefixed key (strip before dot: "employer.job_description" -> "job_description")
  const clean = key.split(".").pop() || key;
  hit = questions.find((q) => q.key === clean);
  if (hit) return hit;

  // 3. Dot to underscore ("residence.card_expiry" -> "residence_card_expiry")
  const under = key.replace(/\./g, "_");
  hit = questions.find((q) => q.key === under);
  if (hit) return hit;

  // 4. Look up known aliases
  const aliases = [
    ...(FIELD_KEY_ALIASES[key] || []),
    ...(FIELD_KEY_ALIASES[clean] || []),
    ...(FIELD_KEY_ALIASES[under] || []),
  ];
  for (const alias of aliases) {
    hit = questions.find((q) => q.key === alias || q.key === alias.split(".").pop());
    if (hit) return hit;
  }

  // 5. Normalized fuzzy match (alphanumeric only)
  const norm = key.toLowerCase().replace(/[^a-z0-9]/g, "");
  hit = questions.find((q) => q.key.toLowerCase().replace(/[^a-z0-9]/g, "") === norm);
  if (hit) return hit;

  return undefined;
}

export type ResolvedFieldInfo = {
  targetKey: string;
  exactFieldName: string;
  displayName: string;
  prompt?: string;
  section?: string;
};

export function formatFieldLabel(key: string): string {
  const clean = key.split(".").pop() || key;
  return clean
    .replace(/_/g, " ")
    .replace(/\bjpy\b/gi, "(JPY)")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function resolveFieldInfo(
  field: string,
  questions: IntakeQuestion[] = []
): ResolvedFieldInfo {
  const q = findQuestionByKey(questions, field);
  if (q) {
    return {
      targetKey: q.key,
      exactFieldName: q.key,
      displayName: formatFieldLabel(q.key),
      prompt: q.prompt,
      section: q.section || undefined,
    };
  }

  const clean = field.split(".").pop() || field;
  return {
    targetKey: clean,
    exactFieldName: clean,
    displayName: formatFieldLabel(field),
  };
}

