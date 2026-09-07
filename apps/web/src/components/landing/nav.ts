"use client";

import { useLang } from "./i18n";
import { dictionary } from "./dictionary";

/**
 * The page's section navigation, defined once.
 *
 * The header and the footer render the same list of anchors. When each kept its own copy,
 * they drifted — removing a link from the header left it live in the footer, and the two
 * spelled the same section differently. This is the single list both read, and the labels
 * come from the dictionary rather than from inline `lang === "ja" ? … : …` ternaries.
 */
export const SECTION_IDS = ["how-it-works", "coverage", "pricing", "faq"] as const;

export type SectionId = (typeof SECTION_IDS)[number];

/** Dictionary key under `nav` that labels each section. */
const SECTION_LABEL_KEY: Record<SectionId, "howItWorks" | "coverage" | "pricing" | "faq"> = {
  "how-it-works": "howItWorks",
  coverage: "coverage",
  pricing: "pricing",
  faq: "faq",
};

export type NavLink = {
  id: SectionId;
  href: string;
  label: string;
};

export function useSectionNav(): NavLink[] {
  const { lang } = useLang();
  const t = dictionary[lang];

  return SECTION_IDS.map((id) => ({
    id,
    href: `#${id}`,
    label: t.nav[SECTION_LABEL_KEY[id]],
  }));
}
