import type { LucideIcon } from "lucide-react";
import { GitBranch, Link2, FileText, Save, Languages, UserCheck } from "lucide-react";

export type StageId = "scope" | "intake" | "eligibility" | "forms";

export const STAGE_ORDER: { id: StageId; step: string }[] = [
  { id: "scope", step: "01" },
  { id: "intake", step: "02" },
  { id: "eligibility", step: "03" },
  { id: "forms", step: "04" },
];

export type FeatureId = "sourced" | "forms" | "branching" | "save" | "language" | "escalate";

export const FEATURE_ICONS: Record<FeatureId, LucideIcon> = {
  branching: GitBranch,
  sourced: Link2,
  forms: FileText,
  save: Save,
  language: Languages,
  escalate: UserCheck,
};

/** Layout order: `sourced` and `forms` render as the two highlighted cards, the rest fill the grid. */
export const PLAIN_FEATURE_ORDER: FeatureId[] = ["branching", "save", "language", "escalate"];

export type FaqId =
  | "lawFirm"
  | "sourceOfGuidance"
  | "supportedJurisdictions"
  | "complexCase"
  | "saveResume"
  | "finalOutput";

export const FAQ_ORDER: FaqId[] = [
  "lawFirm",
  "sourceOfGuidance",
  "supportedJurisdictions",
  "complexCase",
  "saveResume",
  "finalOutput",
];

export type JurisdictionId = "jp" | "us" | "uk";

export const JURISDICTION_ORDER: { id: JurisdictionId; flag: string; live: boolean }[] = [
  { id: "jp", flag: "🇯🇵", live: true },
  { id: "us", flag: "🇺🇸", live: true },
  { id: "uk", flag: "🇬🇧", live: true },
];

export type PricingTierId = "scope" | "guided" | "review";

export const PRICING_TIER_ORDER: PricingTierId[] = ["scope", "guided", "review"];

export type BlogPostMeta = {
  slug: string;
  category: { en: string; ja: string };
  readTime: number;
};

export const BLOG_POST_ORDER: BlogPostMeta[] = [
  { slug: "what-sourced-eligibility-means", category: { en: "Product", ja: "プロダクト" }, readTime: 5 },
  { slug: "japan-work-visa-renewal-documents", category: { en: "Guides", ja: "ガイド" }, readTime: 7 },
  { slug: "when-to-escalate-to-a-lawyer", category: { en: "Guides", ja: "ガイド" }, readTime: 4 },
];
