"use client";

import { usePathname } from "next/navigation";
import { NAV } from "./nav";
import { Topbar } from "./topbar";
import { useI18n } from "@/lib/i18n";

/** Derives the page title from the active nav item so section pages stay declarative. */
export function AdminHeader() {
  const pathname = usePathname();
  const { lang, t } = useI18n();
  const items = NAV.flatMap((g) => g.items);
  const active =
    items
      .filter((i) => (i.href === "/admin" ? pathname === "/admin" : pathname.startsWith(i.href)))
      .sort((a, b) => b.href.length - a.href.length)[0] ?? null;

  const title =
    lang === "ja" && active?.label_ja
      ? active.label_ja
      : active?.label ?? t("nav_dashboard", "Admin");

  return <Topbar title={title} />;
}
