"use client";

import { useLang } from "./i18n";
import { dictionary } from "./dictionary";

export const SECTION_IDS = ["how-it-works", "coverage", "faq"] as const;

export type SectionId = (typeof SECTION_IDS)[number];

const SECTION_LABEL_KEY: Record<SectionId, "howItWorks" | "coverage" | "faq"> = {
  "how-it-works": "howItWorks",
  coverage: "coverage",
  faq: "faq",
};

export type NavLink = {
  id: string;
  href: string;
  label: string;
};

export function useHeaderNav(): NavLink[] {
  const { lang } = useLang();
  const t = dictionary[lang];

  return [
    { id: "coverage", href: "/#coverage", label: t.nav.coverage },
    { id: "how-it-works", href: "/#how-it-works", label: t.nav.howItWorks },
    { id: "pricing", href: "/pricing", label: t.nav.pricing },
    { id: "blog", href: "/blog", label: t.nav.blog },
    { id: "about", href: "/about", label: t.nav.about },
  ];
}

export function useSectionNav(): NavLink[] {
  const { lang } = useLang();
  const t = dictionary[lang];

  return SECTION_IDS.map((id) => ({
    id,
    href: `/#${id}`,
    label: t.nav[SECTION_LABEL_KEY[id]],
  }));
}
